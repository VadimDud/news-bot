"""Fibonacci retracement (trend-continuation) signal notifier.

Ежедневно после закрытия рынка сканирует watchlist: на последней свече ищет
готовый setup — откат в зону 50–61.8 % от последнего импульса (swing low →
swing high) при восходящем тренде и конфлюэнции факторов. Найденный setup
отправляется админу в Telegram с уровнями Фибо и факторной оценкой.

Дедупликация: ``fib_signals`` (PK по тикеру) хранит setup_id и время;
сигнал уходит один раз на уникальную пару swing low → swing high.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

import pandas as pd

from . import config as trading_config
from . import fib_pullback
from . import storage

logger = logging.getLogger("moex_trader.fib_notifier")

MSK = timezone(timedelta(hours=3))

_RU_DIR = {"buy": "ПОКУПКА", "sell": "ПРОДАЖА"}


# ── Telegram (переиспользуем send_telegram_message из signal_notifier) ──────


async def _send_tg(text: str) -> bool:
    try:
        from .signal_notifier import send_telegram_message

        return await send_telegram_message(text)
    except ImportError:
        logger.error("signal_notifier недоступен — сообщение не отправлено")
        return False


# ── Форматирование ───────────────────────────────────────────────────────────


def _fmt_money(val: float | None) -> str:
    return "—" if val is None else f"{val:.2f} ₽"


def _pad_label(label: str, width: int = 12) -> str:
    return f"{label:<{width}}"


def format_fib_signal(
    ticker: str, info: dict, stale: bool = False,
) -> str:
    """Текст Telegram-сообщения о Fib-setup (прогнозное продолжение тренда)."""
    now_msk = datetime.now(MSK).strftime("%H:%M %d.%m.%Y")
    close = info.get("close")
    sw_low = info.get("swing_low")
    sw_high = info.get("swing_high")
    rsi = info.get("rsi")
    factors = info.get("factors")
    trend_up = info.get("trend_up")

    def _pct(a: float | None, b: float | None) -> str:
        if not a or not b or a <= 0:
            return "—"
        return f"{(b - a) / a * 100:+.1f}%"

    stale_warn = "⚠️ Данные устарели — MOEX недоступен\n" if stale else ""

    lines = [
        f"📐 СИГНАЛ ПОКУПКА — {ticker}",
        f"Фибоначчи-ретрейсмент (трендовое продолжение) • {now_msk} МСК",
        f"{stale_warn}",
        f"Цена: {_fmt_money(close)}",
        (
            f"Импульс: swing low {_fmt_money(sw_low)} → swing high "
            f"{_fmt_money(sw_high)} ({_pct(sw_low, sw_high)})"
        ),
        f"Откат: {_fmt_money(info.get('target_in_price'))} — в зоне 50–61.8 %",
        f"Тренд вверх: {'да' if trend_up else 'нет'} | RSI: "
        f"{'—' if rsi is None else f'{rsi:.1f}'} | Факторов: {factors}",
        "",
    ]

    levels = info.get("levels")
    if levels:
        lines.append("Уровни Фибо (от swing high):")
        for lbl, price in levels.items():
            lines.append(f"{_pad_label(lbl)}: {_fmt_money(price)}")

    lines += [
        "",
        f"План: вход по завершении отката в зону 50–61.8 % (конфлюэнция "
        f"зона+свеча+RSI). Стоп за swing low, цель — 0 % (swing high).",
        f"⚠️ Не является индивидуальной инвестиционной рекомендацией.",
    ]
    return "\n".join(lines)


# ── Скан ─────────────────────────────────────────────────────────────────────


def _load_daily_candles(ticker: str) -> pd.DataFrame | None:
    """Дневные свечи из БД как индексированный OHLCV или None."""
    df_raw = storage.get_candles(ticker, "1day")
    if df_raw.empty or len(df_raw) < 5:
        logger.info("Недостаточно свечей по %s (%d), пропуск", ticker, len(df_raw))
        return None
    try:
        return fib_pullback.prepare_ohlc(df_raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось подготовить свечи по %s: %s", ticker, exc)
        return None


def _load_htf(ticker: str) -> pd.DataFrame | None:
    """Старший таймфрейм (неделя) для фильтра глобального тренда, если есть."""
    df_raw = storage.get_candles(ticker, "1week")
    if df_raw.empty or len(df_raw) < 20:
        return None
    try:
        return fib_pullback.prepare_ohlc(df_raw)
    except Exception:  # noqa: BLE001
        return None


def _params_from_config() -> dict:
    return {
        "swing_bars": trading_config.TRADER_FIB_SWING_BARS,
        "fib_in_low": trading_config.TRADER_FIB_FIB_IN_LOW,
        "fib_in_high": trading_config.TRADER_FIB_FIB_IN_HIGH,
        "trend_period": trading_config.TRADER_FIB_TREND_PERIOD,
        "confluence_min": trading_config.TRADER_FIB_CONFLUENCE_MIN,
        "rsi_oversold": trading_config.TRADER_FIB_RSI_OVERSOLD,
        "regime_adx_min": trading_config.TRADER_FIB_REGIME_ADX_MIN,
        "regime_atr_vol_max": trading_config.TRADER_FIB_REGIME_ATR_VOL_MAX,
    }


def _is_stale(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    last_dt = df.index[-1]
    if isinstance(last_dt, pd.Timestamp):
        last_dt = last_dt.to_pydatetime()
    now = datetime.now(timezone.utc)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    return (now - last_dt).days > trading_config.TRADER_SIGNALS_MAX_STALE_DAYS


def _setup_id(info: dict) -> str | None:
    """Уникальный идентификатор setup-а (пара swing low → swing high)."""
    sw_low = info.get("swing_low")
    sw_high = info.get("swing_high")
    if sw_low is None or sw_high is None:
        return None
    return f"{float(sw_low):.4f}->{float(sw_high):.4f}"


async def _scan_ticker(ticker: str) -> dict | None:
    """Сканировать один тикер: детект setup-а, дедуп, отправка."""
    df = _load_daily_candles(ticker)
    if df is None:
        return None

    params = _params_from_config()
    htf = _load_htf(ticker) if int(trading_config.TRADER_FIB_USE_HTF) else None
    info = fib_pullback.detect_latest_setup(df, htf_df=htf, **params)
    if info is None:
        logger.debug("Нет завершённого Fib-setup по %s", ticker)
        return None

    setup_id = _setup_id(info)
    if setup_id is None:
        return None
    prev = storage.get_fib_signal(ticker)
    if prev["setup_id"] == setup_id:
        logger.debug("Сигнал для %s уже отправлен (setup_id=%s)", ticker, setup_id)
        return None

    # Детали для сообщения: retrace-зона и целевая цена.
    close = info.get("close")
    sw_high = info.get("swing_high")
    seg = info.get("segment")
    retrace_center = (trading_config.TRADER_FIB_FIB_IN_LOW + trading_config.TRADER_FIB_FIB_IN_HIGH) / 2.0
    info["target_in_price"] = (
        sw_high - retrace_center * seg
        if (sw_high is not None and seg is not None and seg > 0)
        else None
    )

    stale = _is_stale(df)
    msg = format_fib_signal(ticker, info, stale=stale)
    sent = await _send_tg(msg)

    if sent:
        storage.save_fib_signal(
            ticker, setup_id,
            swing_low=info.get("swing_low"), swing_high=info.get("swing_high"),
            retrace=info.get("retrace"), factors=info.get("factors"),
        )
        logger.info("Fib-сигнал отправлен: %s (setup_id=%s)", ticker, setup_id)
    return {"ticker": ticker, "sent": sent, "setup_id": setup_id}


def _watchlist() -> list[str]:
    tickers = storage.list_watchlist()
    if not tickers:
        return list(trading_config.WATCH_TICKERS)
    return list(tickers)


async def run_fib_scan() -> list[dict]:
    """Полный скан watchlist: детект setup → дедуп → Telegram."""
    sent: list[dict] = []
    for ticker in _watchlist():
        try:
            result = await _scan_ticker(ticker)
            if result and result["sent"]:
                sent.append(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скана Fib по %s: %s", ticker, exc)
    return sent


# ── Планировщик ─────────────────────────────────────────────────────────────


def _next_scan_delay(now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    target = datetime.combine(
        now.date(),
        time(trading_config.TRADER_FIB_SCAN_HOUR, trading_config.TRADER_FIB_SCAN_MINUTE),
        tzinfo=timezone.utc,
    )
    if now >= target:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 0.0)


async def fib_scan_loop() -> None:
    """Ежедневно вечером после закрытия рынка: sleep → run_fib_scan."""
    logger.info(
        "Сканер Fib-сигналов запущен: ежедневно %02d:%02d UTC%s",
        trading_config.TRADER_FIB_SCAN_HOUR,
        trading_config.TRADER_FIB_SCAN_MINUTE,
        ", стартовый прогон включён" if trading_config.TRADER_FIB_RUN_ON_STARTUP else "",
    )
    if trading_config.TRADER_FIB_RUN_ON_STARTUP:
        try:
            sent = await run_fib_scan()
            if sent:
                logger.info("Стартовый Fib-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Стартовый Fib-скан упал: %s", exc)

    while True:
        try:
            delay = _next_scan_delay()
            next_run = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info("Следующий Fib-скан: %s (через %.0f c)", next_run.isoformat(timespec="seconds"), delay)
            await asyncio.sleep(delay)
            sent = await run_fib_scan()
            if sent:
                logger.info("Fib-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            logger.info("Сканер Fib-сигналов остановлен")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла Fib-сканера: %s", exc)
            await asyncio.sleep(3600)
