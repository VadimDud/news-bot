"""Fibonacci retracement (trend-continuation) signal notifier.

Ежедневно после закрытия рынка сканирует watchlist: на последней свече ищет
готовый setup — откат в зону 50–61.8 % от последнего импульса (swing low →
swing high) при восходящем тренде и конфлюэнции факторов для лонга, либо
откат вверх в премиальную зону при нисходящем тренде для шорта. Найденный
setup отправляется админу в Telegram с уровнями Фибо и факторной оценкой.

Дедупликация: ``fib_signals`` (long) и ``fib_short_signals`` (short) — PK по
тикеру, хранят setup_id и время; сигнал уходит один раз на уникальную пару
swing low → swing high.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from . import config as trading_config
from . import fib_pullback
from . import storage

logger = logging.getLogger("moex_trader.fib_notifier")

MSK = timezone(timedelta(hours=3))

_RU_DIR = {"buy": "ПОКУПКА", "sell": "ПРОДАЖА", "short": "ПРОДАЖА"}


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
    ticker: str, info: dict, stale: bool = False, short: bool = False,
) -> str:
    """Текст Telegram-сообщения о Fib-setup (прогнозное продолжение тренда)."""
    now_msk = datetime.now(MSK).strftime("%H:%M %d.%m.%Y")
    close = info.get("close")
    sw_low = info.get("swing_low")
    sw_high = info.get("swing_high")
    rsi = info.get("rsi")
    factors = info.get("factors_short") if short else info.get("factors")
    trend_up = info.get("trend_up")
    in_premium = bool(info.get("in_premium"))

    def _pct(a: float | None, b: float | None) -> str:
        if not a or not b or a <= 0:
            return "—"
        return f"{(b - a) / a * 100:+.1f}%"

    stale_warn = "⚠️ Данные устарели — MOEX недоступен\n" if stale else ""

    direction_word = "ПРОДАЖА" if short else "ПОКУПКА"
    signal_dir = "📉" if short else "📈"

    if short:
        # Лонг-импульс (swing low → swing high), шорт уходит в premium-зону.
        seg_price = info.get("segment")
        retrace_center = 0.5
        if seg_price is not None and sw_low is not None:
            zone_top = sw_low + retrace_center * seg_price
        else:
            zone_top = None
        zone_label = f"Откат вверх: ~{_fmt_money(zone_top)} — в премиальной зоне 50–61.8 %"
    else:
        zone_label = f"Откат: {_fmt_money(info.get('target_in_price'))} — в зоне 50–61.8 %"

    lines = [
        f"{signal_dir} СИГНАЛ {direction_word} — {ticker}",
        f"Фибоначчи-ретрейсмент (трендовое продолжение) • {now_msk} МСК",
        f"{stale_warn}",
        f"Цена: {_fmt_money(close)}",
        (
            f"Импульс: swing low {_fmt_money(sw_low)} → swing high "
            f"{_fmt_money(sw_high)} ({_pct(sw_low, sw_high)})"
        ),
        zone_label,
        f"Тренд вверх: {'да' if trend_up else 'нет'} | RSI: "
        f"{'—' if rsi is None else f'{rsi:.1f}'} | Факторов: {factors}",
        "",
    ]

    levels = info.get("levels_short") if short else info.get("levels")
    if levels:
        title = "Уровни Фибо (откат вверх, цель — swing low):" if short else "Уровни Фибо (от swing high):"
        lines.append(title)
        for lbl, price in levels.items():
            lines.append(f"{_pad_label(lbl)}: {_fmt_money(price)}")

    if short:
        plan = (
            f"План: шорт по завершении отката вверх в зону 50–61.8 % (конфлюэнция "
            f"зона+свеча+RSI). Стоп за swing high, цель — 0 % (swing low)."
        )
    else:
        plan = (
            f"План: вход по завершении отката в зону 50–61.8 % (конфлюэнция "
            f"зона+свеча+RSI). Стоп за swing low, цель — 0 % (swing high)."
        )
    lines += [
        "",
        plan,
        f"⚠️ Не является индивидуальной инвестиционной рекомендацией.",
    ]
    return "\n".join(lines)


# ── Скан ─────────────────────────────────────────────────────────────────────


def _load_candles(ticker: str, period: str = "4h") -> pd.DataFrame | None:
    """Свечи из БД как индексированный OHLCV или None.

    Рабочий таймфрейм сканера — ``4h`` (ресемпл из 1h); дефолт можно
    переопределить per-ticker настройкой ``timeframe`` (напр. ``1day``).
    """
    df_raw = storage.get_candles(ticker, period)
    if df_raw.empty or len(df_raw) < 5:
        logger.info("Недостаточно свечей %s по %s (%d), пропуск", period, ticker, len(df_raw))
        return None
    try:
        return fib_pullback.prepare_ohlc(df_raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось подготовить свечи по %s: %s", ticker, exc)
        return None


def _load_htf(ticker: str) -> pd.DataFrame | None:
    """Старший таймфрейм (день) для фильтра глобального тренда, если есть."""
    df_raw = storage.get_candles(ticker, "1day")
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


def ticker_settings(ticker: str) -> dict:
    """Настройки сканера для бумаги: {direction, params, timeframe}.

    Приоритет: сохранённые per-ticker настройки из БД → TICKER_OVERRIDES →
    глобальные параметры из конфига. Параметры сливаются поверх базовых.
    ``timeframe`` — рабочий таймфрейм сканера (по умолчанию ``4h``); в БД и
    кодовых оверрайдах можно задать per-ticker (напр. ``1day`` для SBER).
    """
    params = _params_from_config()
    direction = 0  # 0 — оба направления (лонг и шорт)
    timeframe = "4h"  # сканер по умолчанию работает на 4h

    from .strategies import TICKER_OVERRIDES as _TO

    over = _TO.get(("fib_pullback", ticker.upper()), {})
    if over:
        params = {**params, **{k: v for k, v in over.items() if k not in ("direction", "timeframe")}}
        direction = int(over.get("direction", direction))
        timeframe = str(over.get("timeframe", timeframe))

    saved = storage.get_fib_ticker_setting(ticker)
    if saved is not None:
        if saved.get("params"):
            params = {**params, **saved["params"]}
        direction = int(saved.get("direction", direction))
        timeframe = str(saved.get("timeframe", timeframe))

    return {"direction": direction, "params": params, "timeframe": timeframe}


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
    """Сканировать один тикер: детект setup-а (long и short), дедуп, отправка.

    Параметры и направление берутся из per-ticker настроек (БД →
    TICKER_OVERRIDES → глобальный конфиг), чтобы сигнал был уже настроен
    под характер бумаги.
    """
    settings = ticker_settings(ticker)
    params = settings["params"]
    direction = settings["direction"]
    timeframe = settings.get("timeframe", "4h")

    df = _load_candles(ticker, period=timeframe)
    if df is None:
        return None

    htf = _load_htf(ticker) if int(trading_config.TRADER_FIB_USE_HTF) else None
    retrace_center = (trading_config.TRADER_FIB_FIB_IN_LOW + trading_config.TRADER_FIB_FIB_IN_HIGH) / 2.0

    # Лонг-setup
    if direction >= 0:
        info = fib_pullback.detect_latest_setup(df, htf_df=htf, **params)
        if info is not None:
            result = await _dispatch_setup(ticker, df, info, params, short=False,
                                           retrace_center=retrace_center)
            if result is not None:
                return result

    # Шорт-setup
    if direction <= 0:
        info = fib_pullback.detect_latest_short_setup(df, htf_df=htf, **params)
        if info is not None:
            return await _dispatch_setup(ticker, df, info, params, short=True,
                                         retrace_center=retrace_center)

    logger.debug("Нет завершённого Fib-setup (long/short) по %s", ticker)
    return None


async def _dispatch_setup(ticker: str, df: pd.DataFrame, info: dict, params: dict, *,
                          short: bool, retrace_center: float) -> dict | None:
    """Дедупликация и отправка одного setup-а (long или short)."""
    setup_id = _setup_id(info)
    if setup_id is None:
        return None
    prev = (storage.get_fib_short_signal(ticker) if short
            else storage.get_fib_signal(ticker))
    if prev["setup_id"] == setup_id:
        logger.debug("Сигнал для %s уже отправлен (setup_id=%s)", ticker, setup_id)
        return None

    # Детали для сообщения: retrace-зона и целевая цена.
    close = info.get("close")
    sw_high = info.get("swing_high")
    sw_low = info.get("swing_low")
    seg = info.get("segment")
    if short:
        info["target_in_price"] = (
            sw_low + retrace_center * seg
            if (sw_low is not None and seg is not None and seg > 0)
            else None
        )
    else:
        info["target_in_price"] = (
            sw_high - retrace_center * seg
            if (sw_high is not None and seg is not None and seg > 0)
            else None
        )

    stale = _is_stale(df)
    msg = format_fib_signal(ticker, info, stale=stale, short=short)
    sent = await _send_tg(msg)

    if sent:
        save = storage.save_fib_short_signal if short else storage.save_fib_signal
        save(
            ticker, setup_id,
            swing_low=info.get("swing_low"), swing_high=info.get("swing_high"),
            retrace=info.get("retrace"),
            factors=info.get("factors_short") if short else info.get("factors"),
        )
        logger.info("Fib-%s сигнал отправлен: %s (setup_id=%s)",
                    "short" if short else "long", ticker, setup_id)
    return {"ticker": ticker, "sent": sent, "setup_id": setup_id, "short": short}


def _watchlist() -> list[str]:
    tickers = storage.list_watchlist()
    if not tickers:
        return list(trading_config.WATCH_TICKERS)
    return list(tickers)


# ── Доскачивание данных рабочего ТФ (4h) ─────────────────────────────────────

# Бумаги, для которых 4h-данные НЕ качаем (работают на другом ТФ, напр. SBER=1day)
_FIB_4H_EXCLUDE = frozenset({"SBER"})

_FIB_4H_SYNC_HOURS = 6  # период повторной синхронизации 4h-данных


def _ticker_timeframe(ticker: str) -> str:
    """Рабочий ТФ бумаги из per-ticker настроек (4h по умолчанию)."""
    return ticker_settings(ticker).get("timeframe", "4h")


def _needs_4h_sync(ticker: str, timeframe: str) -> bool:
    if timeframe != "4h" or ticker.upper() in _FIB_4H_EXCLUDE:
        return False
    last = storage.last_candle_time(ticker, "4h")
    if last is None:
        return True
    last_dt = datetime.fromisoformat(last)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_dt) > timedelta(hours=_FIB_4H_SYNC_HOURS)


async def fib_data_sync_task() -> None:
    """Фоновая синхронизация 4h-свечей watchlist с MOEX (кроме исключений)."""
    from . import data as data_module

    while True:
        try:
            for ticker in _watchlist():
                timeframe = _ticker_timeframe(ticker)
                if not _needs_4h_sync(ticker, timeframe):
                    continue
                try:
                    end = date.today()
                    start = end - timedelta(days=400)
                    await asyncio.to_thread(data_module.fetch_history, ticker, "4h", start, end)
                    logger.info("4h-свечи синхронизированы: %s", ticker)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Синхронизация 4h по %s не удалась: %s", ticker, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла синхронизации 4h: %s", exc)
        await asyncio.sleep(3600)


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
    """До ближайшего времени скана (основное + дополнительные 4h-бары)."""
    now = now or datetime.now(timezone.utc)
    targets: list[datetime] = []
    for hour, minute in [(trading_config.TRADER_FIB_SCAN_HOUR, trading_config.TRADER_FIB_SCAN_MINUTE), *trading_config.TRADER_FIB_EXTRA_SCANS]:
        t = datetime.combine(
            now.date(), time(hour, minute), tzinfo=timezone.utc
        )
        if now >= t:
            t += timedelta(days=1)
        targets.append(t)
    return max((min(targets) - now).total_seconds(), 0.0)


async def fib_scan_loop() -> None:
    """Скан после закрытия каждого бара рабочего ТФ (4h → несколько раз в день)."""
    logger.info(
        "Сканер Fib-сигналов запущен: основные %02d:%02d UTC%s, ТФ=%s%s",
        trading_config.TRADER_FIB_SCAN_HOUR,
        trading_config.TRADER_FIB_SCAN_MINUTE,
        f", доп. времена: {trading_config.TRADER_FIB_EXTRA_SCANS}" if trading_config.TRADER_FIB_EXTRA_SCANS else "",
        trading_config.TRADER_FIB_TIMEFRAME,
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
