"""Elliott micro-wave signal notifier: daily scan + Telegram alerts.

Runs after MOEX close (default 19:10 MSK). Loads cached daily candles from
SQLite, detects newly completed waves, scores quality, and sends a
counter-trend signal with Fibonacci targets to the admin chat.

Dedup: each wave-end datetime is stored in ``elliott_signals`` table;
a signal is sent only once per unique wave completion.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

import pandas as pd

from . import config as trading_config
from . import elliott_candles
from . import storage

logger = logging.getLogger("moex_trader.elliott_notifier")

MSK = timezone(timedelta(hours=3))


# ── Telegram (reuse signal_notifier's function if available) ────────────────


async def _send_tg(text: str) -> bool:
    """Отправить сообщение админу (BOT_TOKEN/ADMIN_ID из общего .env)."""
    try:
        from .signal_notifier import send_telegram_message
        return await send_telegram_message(text)
    except ImportError:
        logger.error("signal_notifier недоступен — сообщение не отправлено")
        return False


# ── Форматирование ─────────────────────────────────────────────────────────

_RU_DIR = {"buy": "ПОКУПКА", "sell": "ПРОДАЖА"}

def _fmt_money(val: float | None) -> str:
    return "—" if val is None else f"{val:.2f} ₽"

def _wave_pct(wave: elliott_candles.Wave) -> str:
    """Процентное изменение от начала до конца волны."""
    sub = wave.sub_candles()
    start_price = float(sub["open"].iloc[0])
    end_price = float(sub["close"].iloc[wave.end_idx - wave.start_idx])
    if start_price == 0:
        return "—"
    pct = (end_price - start_price) / start_price * 100
    return f"{pct:+.1f}%"


def _quality_line(q: dict) -> str:
    """Однострочная сводка качества волны."""
    return (
        f"   • Растяжение: {q['extension']:.2f} | Не-короткая: {q['not_shortest']:.2f}\n"
        f"   • Чередование: {q['alternation']:.2f} | Чистота хода: {q['dominance']:.2f}"
    )


def format_elliott_signal(
    ticker: str,
    wave: elliott_candles.Wave,
    quality: dict,
    fib: dict,
    stale: bool = False,
) -> str:
    """Текст сигнала для Telegram."""
    direction_key = "buy" if wave.direction == "bear" else "sell"  # fade: bear wave → BUY
    title = f"🌊 СИГНАЛ {_RU_DIR[direction_key]} — {ticker}"
    now_msk = datetime.now(MSK).strftime("%H:%M %d.%m.%Y")

    wave_start = float(wave.sub_candles()["open"].iloc[0])
    wave_end = float(wave.df["close"].iloc[wave.end_idx])

    # Цели: абсолютные цены от текущего уровня
    if wave.direction == "bear":
        # Покупка: коррекция вверх
        entry = wave.next_open or wave_end
        fib_prices = {
            "38.2%": entry + fib["fib_382"],
            "50.0%": entry + fib["fib_500"],
            "61.8%": entry + fib["fib_618"],
        }
        plan = "вход на открытии следующей свечи (длинная позиция)"
    else:
        # Продажа: коррекция вниз
        entry = wave.next_open or wave_end
        fib_prices = {
            "38.2%": entry - fib["fib_382"],
            "50.0%": entry - fib["fib_500"],
            "61.8%": entry - fib["fib_618"],
        }
        plan = "вход на открытии следующей свечи (короткая позиция)"

    stale_warn = "\n⚠️ Данные устарели —_MOEX_недоступен" if stale else ""
    q_total = quality["total"]

    fib_lines = "\n".join(f"     • {k}: {_fmt_money(v)}" for k, v in fib_prices.items())

    return (
        f"{title}\n"
        f"Стратегия микро-волн Эллиотта • {now_msk} МСК\n"
        f"{stale_warn}\n"
        f"\n"
        f"Цена: {_fmt_money(wave_end)}\n"
        f"{'Медвежья' if wave.direction == 'bear' else 'Бычья'} волна: "
        f"{wave.candle_count} свечи ({_fmt_money(wave_start)} → {_fmt_money(wave_end)}, {_wave_pct(wave)})\n"
        f"Качество волны: {q_total:.2f}/1.00\n"
        f"{_quality_line(quality)}\n"
        f"\n"
        f"Цели коррекции (Фибо) от {_fmt_money(entry)}:\n"
        f"{fib_lines}\n"
        f"\n"
        f"План: {plan}.\n"
        f"При минусе — удвоение на след. свече, макс. 3 сделки (25→50→100%).\n"
        f"⚠️ Контртренд + мартингейл — высокий риск."
    )


# ── Скан ────────────────────────────────────────────────────────────────────


def _load_daily_candles(ticker: str) -> pd.DataFrame | None:
    """Загрузить дневные свечи из БД; вернуть DataFrame или None при ошибке."""
    df_raw = storage.get_candles(ticker, "1day")
    if df_raw.empty or len(df_raw) < 5:
        logger.info("Недостаточно свечей по %s (%d), пропуск", ticker, len(df_raw))
        return None
    df = df_raw.copy()
    df["begin"] = pd.to_datetime(df["begin"])
    df = df.set_index("begin").sort_index()[["open", "high", "low", "close", "volume"]]
    return df


def _is_stale(df: pd.DataFrame) -> bool:
    """Проверить, насколько стары данные."""
    if df.empty:
        return True
    last_dt = df.index[-1]
    if isinstance(last_dt, pd.Timestamp):
        last_dt = last_dt.to_pydatetime()
    now = datetime.now(timezone.utc)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    age_days = (now - last_dt).days
    return age_days > trading_config.TRADER_SIGNALS_MAX_STALE_DAYS


def detect_latest_completed_wave(
    df: pd.DataFrame,
    wave_min: int = 3,
    wave_max: int = 5,
    body_ratio_min: float = 0.6,
    atr_k: float = 0.5,
) -> elliott_candles.Wave | None:
    """Если последняя свеча завершает новую волну — вернуть её, иначе None."""
    classified = elliott_candles.classify_candles(df, body_ratio_min=body_ratio_min, atr_k=atr_k)
    waves = elliott_candles.detect_waves(classified, wave_min=wave_min, wave_max=wave_max)
    if not waves:
        return None
    last_wave = waves[-1]
    # Волна завершена, если end_idx == последний индекс df (свеча закрыта)
    if last_wave.end_idx == len(classified) - 1:
        return last_wave
    return None


async def _scan_ticker(ticker: str) -> dict | None:
    """Сканировать один тикер: детекция волны, дедуп, отправка."""
    df = _load_daily_candles(ticker)
    if df is None:
        return None

    wave = detect_latest_completed_wave(
        df,
        wave_min=trading_config.TRADER_ELLIOTT_WAVE_MIN,
        wave_max=trading_config.TRADER_ELLIOTT_WAVE_MAX,
        body_ratio_min=trading_config.TRADER_ELLIOTT_BODY_RATIO_MIN,
        atr_k=trading_config.TRADER_ELLIOTT_ATR_K,
    )
    if wave is None:
        logger.debug("Нет завершённой волны по %s", ticker)
        return None

    # Дедуп: wave_end время
    wave_end_str = str(wave.end_dt)
    prev = storage.get_elliott_signal(ticker)
    if prev["wave_end"] == wave_end_str:
        logger.debug("Сигнал для %s уже отправлен (wave_end=%s)", ticker, wave_end_str)
        return None

    # Скоринг качества
    quality = elliott_candles.wave_quality_score(wave)
    fib = elliott_candles.fibonacci_levels(wave)
    stale = _is_stale(df)

    msg = format_elliott_signal(ticker, wave, quality, fib, stale=stale)
    sent = await _send_tg(msg)

    if sent:
        storage.save_elliott_signal(ticker, wave_end_str, wave.direction, quality["total"])
        logger.info("Elliott-сигнал отправлен: %s %s q=%.2f", ticker, wave.direction, quality["total"])
    return {"ticker": ticker, "direction": wave.direction, "sent": sent, "quality": quality["total"]}


async def run_elliott_scan() -> list[dict]:
    """Полный скан watchlist: детект волны → дедуп → Telegram."""
    sent: list[dict] = []
    for ticker in storage.list_watchlist():
        try:
            result = await _scan_ticker(ticker)
            if result and result["sent"]:
                sent.append(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скана Elliott по %s: %s", ticker, exc)
    return sent


# ── Планировщик ─────────────────────────────────────────────────────────────

def _next_scan_delay(now: datetime | None = None) -> float:
    """Секунды до следующего скана (время из TRADER_ELLIOTT_SCAN_HOUR/MINUTE)."""
    now = now or datetime.now(timezone.utc)
    target = datetime.combine(
        now.date(),
        time(trading_config.TRADER_ELLIOTT_SCAN_HOUR, trading_config.TRADER_ELLIOTT_SCAN_MINUTE),
        tzinfo=timezone.utc,
    )
    if now >= target:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 0.0)


async def elliott_scan_loop() -> None:
    """Ежедневно вечером после закрытия рынка: sleep → run_elliott_scan."""
    logger.info(
        "Сканер Elliott-сигналов запущен: ежедневно %02d:%02d UTC%s",
        trading_config.TRADER_ELLIOTT_SCAN_HOUR,
        trading_config.TRADER_ELLIOTT_SCAN_MINUTE,
        ", стартовый прогон включён" if trading_config.TRADER_ELLIOTT_RUN_ON_STARTUP else "",
    )
    if trading_config.TRADER_ELLIOTT_RUN_ON_STARTUP:
        try:
            sent = await run_elliott_scan()
            if sent:
                logger.info("Стартовый Elliott-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Стартовый Elliott-скан упал: %s", exc)

    while True:
        try:
            delay = _next_scan_delay()
            next_run = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info("Следующий Elliott-скан: %s (через %.0f c)", next_run.isoformat(timespec="seconds"), delay)
            await asyncio.sleep(delay)
            sent = await run_elliott_scan()
            if sent:
                logger.info("Elliott-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            logger.info("Сканер Elliott-сигналов остановлен")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла Elliott-сканера: %s", exc)
            await asyncio.sleep(3600)
