"""MTF Confirmation: multi-timeframe candle-pattern signal notifier.

После закрытия каждого 4h-бара сканирует watchlist: ищет зон-пробой на LTF,
подтверждённый дневным зона-режимом (S·F > 0). Отправляет админу в Telegram
с планом входа/выхода (по бэктесту: open след. бара, close через 6 баров).

Если Elliott TP включён (TRADER_MTF_ELLIOTT_TP_ENABLED) и на wave TF найдена
волна 1-2 — в сообщении указывается TP-цена. Иначе — стандартный план close+6.

Режим работы: только уведомления (без автоторговли).
Дедупликация: PK (ticker, signal_ts, side) — повторный скан не шлёт тот же сигнал.
Время сигнала: разрешены только бары 4/8/12 UTC (07:00–15:00 MSK),
исключены вечер (16 UTC = 19:00 MSK) и ночь (20 UTC) — худший win-rate.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from . import config as trading_config
from . import mtf_confirm
from . import storage

logger = logging.getLogger("moex_trader.mtf_notifier")

MSK = timezone(timedelta(hours=3))


# ── Telegram ────────────────────────────────────────────────────────────────

async def _send_tg(text: str) -> bool:
    try:
        from .signal_notifier import send_telegram_message
        return await send_telegram_message(text)
    except ImportError:
        logger.error("signal_notifier недоступен — сообщение не отправлено")
        return False


# ── Форматирование ──────────────────────────────────────────────────────────

def format_mtf_signal(ticker: str, side: str, close_price: float,
                      htf_state: int, bar_dt: datetime,
                      wave_info: dict | None = None) -> str:
    """Текст Telegram-сообщения о MTF-сигнале.

    ``wave_info`` — dict с полями: wave1_amp, tp_price, k, wave_tf, time_cap
    или None (нет волны → стандартный план close+6).
    """
    now_msk = datetime.now(MSK).strftime("%H:%M %d.%m.%Y")
    direction = "ШОРТ" if side == "bear" else "ЛОНГ"
    signal_dir = "📉" if side == "bear" else "📈"
    htf_label = "БЫЧИЙ (close > max(H[20]))" if htf_state == 1 else "МЕДВЕЖЬИЙ (close < min(L[20]))"

    bar_msk = bar_dt.strftime("%H:%M %d.%m.%Y") + " МСК"
    entry_time = (bar_dt + timedelta(hours=4)).strftime("%H:%M") + " МСК"

    if wave_info is not None:
        tp = wave_info["tp_price"]
        k = wave_info["k"]
        w1amp = wave_info["wave1_amp"]
        wtf = wave_info["wave_tf"]
        cap = wave_info["time_cap"]
        cap_hours = cap * 4  # 4h bars → hours

        if side == "bear":
            plan_lines = [
                f"  Вход: ШОРТ на open {entry_time}",
                f"  Take-Profit: {tp:.2f} ₽ (−{k}× волна 1, амплитуда {w1amp:.2f})",
                f"  Стоп: нет (выход по времени — {cap} баров ≈ {cap_hours} ч)",
                f"  Время удержания: до {cap} 4h-баров",
                f"  Если TP не сработал → exit на close {cap}-го бара",
            ]
        else:
            plan_lines = [
                f"  Вход: ЛОНГ на open {entry_time}",
                f"  Take-Profit: {tp:.2f} ₽ (+{k}× волна 1, амплитуда {w1amp:.2f})",
                f"  Стоп: нет (выход по времени — {cap} баров ≈ {cap_hours} ч)",
                f"  Время удержания: до {cap} 4h-баров",
                f"  Если TP не сработал → exit на close {cap}-го бара",
            ]

        plan_header = f"📋 План (Elliott TP, волна {wtf}):"
    else:
        plan_lines = [
            f"  Вход: {'ЛОНГ' if side == 'bull' else 'ШОРТ'} на open {entry_time}",
            f"  Выход: на close через 6 баров (≈ 24 ч)",
        ]
        plan_header = "📋 План (baseline):"

    lines = [
        f"{signal_dir} MTF СИГНАЛ {direction} — {ticker}",
        f"Зон-пробой + дневная зона • {now_msk} МСК",
        "",
        f"Цена (close бара): {close_price:.2f} ₽",
        f"Дневной режим: {htf_label}",
        f"Сигнал на баре: {bar_msk} (4h)",
        "",
        plan_header,
        *plan_lines,
        "",
        f"Комиссия: 0.05%/сторона + 0.05% проскальзывание",
        "",
        f"⚠️ Не является индивидуальной инвестиционной рекомендацией.",
    ]
    return "\n".join(lines)


# ── Загрузка данных ─────────────────────────────────────────────────────────

def _load_candles(ticker: str, period: str) -> pd.DataFrame | None:
    df_raw = storage.get_candles(ticker, period)
    if df_raw.empty or len(df_raw) < 25:
        return None
    try:
        return mtf_confirm.prepare_ohlc(df_raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось подготовить свечи %s %s: %s", period, ticker, exc)
        return None


def _watchlist() -> list[str]:
    return list(trading_config.TRADER_MTF_TICKERS)


# ── Скан одного тикера ─────────────────────────────────────────────────────

async def _scan_ticker(ticker: str) -> dict | None:
    """Сканировать тикер: mtf_signal на последнем закрытом баре + фильтр часов."""
    ltf = _load_candles(ticker, "4h")
    htf = _load_candles(ticker, "1day")
    if ltf is None or htf is None or len(ltf) < 50 or len(htf) < 25:
        return None

    sig = mtf_confirm.mtf_signal(ltf, htf, pattern="zone_break",
                                  ltf_zone=20, htf_zone=20)
    if sig.empty or sig.iloc[-1] == 0:
        return None

    last_idx = len(sig) - 1
    last_bar_hour = ltf.index[last_idx].hour

    # Фильтр по часам: пропускаем бары вне разрешённых
    allowed_hours = trading_config.TRADER_MTF_SIGNAL_HOURS
    if last_bar_hour not in allowed_hours:
        logger.debug("Пропуск %s: бар %d UTC вне разрешённых %s",
                     ticker, last_bar_hour, allowed_hours)
        return None

    side_val = int(sig.iloc[last_idx])
    side = "bear" if side_val < 0 else "bull"
    bar_dt = ltf.index[last_idx].to_pydatetime()
    if bar_dt.tzinfo is None:
        bar_dt = bar_dt.replace(tzinfo=timezone.utc)
    signal_ts = bar_dt.isoformat()
    close_price = float(ltf["close"].iloc[last_idx])

    # Дедуп
    prev = storage.get_mtf_signal(ticker)
    if prev["signal_ts"] == signal_ts and prev["side"] == side:
        logger.debug("MTF-сигнал для %s уже отправлен (ts=%s, side=%s)", ticker, signal_ts, side)
        return None

    # Дневной режим для сообщения
    htf_state_series = mtf_confirm.htf_zone_state(htf, zone=20)
    htf_state_val = int(htf_state_series.iloc[-1]) if len(htf_state_series) > 0 else 0

    # Elliott TP: поиск волны 1-2 для определения Take-Profit
    wave_info = None
    if trading_config.TRADER_MTF_ELLIOTT_TP_ENABLED:
        try:
            from .elliott_candles import classify_candles, detect_waves

            wave_tf = trading_config.TRADER_MTF_ELLIOTT_WAVE_TF
            k = trading_config.TRADER_MTF_ELLIOTT_K
            time_cap = trading_config.TRADER_MTF_ELLIOTT_TIME_CAP

            # Классифицируем свечи wave TF
            if wave_tf == "4h":
                wave_df = classify_candles(ltf.copy())
            else:
                wave_df = classify_candles(htf.copy())

            signal_time = ltf.index[last_idx]
            if wave_tf == "4h":
                wave_pos = wave_df.index.searchsorted(signal_time, side="right") - 1
            else:
                completed_mask = wave_df.index < signal_time.normalize()
                wave_pos = int(completed_mask.sum()) - 1 if completed_mask.any() else -1

            if wave_pos >= 0:
                # Ищем wave 1-2 пару: две последовательные волны разного направления
                waves = detect_waves(wave_df)
                pairs = []
                for wi in range(len(waves) - 1):
                    w1 = waves[wi]
                    w2 = waves[wi + 1]
                    if w1.direction == w2.direction:
                        continue
                    direction = "long" if w1.direction == "bull" else "short"
                    w1_slice = wave_df.iloc[w1.start_idx:w1.end_idx + 1]
                    w1_amp = float(w1_slice["high"].max() - w1_slice["low"].min())
                    pairs.append({
                        "pair_end_idx": w2.end_idx,
                        "direction": direction,
                        "wave1_amp": w1_amp,
                    })

                # Ближайшая пара, завершённая до сигнала
                valid = [p for p in pairs if p["pair_end_idx"] < wave_pos]
                if valid:
                    pair = valid[-1]
                    pair_direction = pair["direction"]
                    # Проверяем соответствие: long → bull wave, short → bear wave
                    if (side == "bull" and pair_direction == "long") or \
                       (side == "bear" and pair_direction == "short"):
                        L = pair["wave1_amp"]
                        if L > 0:
                            if side == "bull":
                                tp_price = close_price + k * L
                            else:
                                tp_price = close_price - k * L
                            wave_info = {
                                "wave1_amp": L,
                                "tp_price": tp_price,
                                "k": k,
                                "wave_tf": wave_tf,
                                "time_cap": time_cap,
                            }
                            logger.info("Elliott TP для %s: wave1_amp=%.2f, tp=%.2f, k=%.3f, tf=%s",
                                        ticker, L, tp_price, k, wave_tf)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Elliott TP расчёт для %s не удался: %s", ticker, exc)

    msg = format_mtf_signal(ticker, side, close_price, htf_state_val, bar_dt, wave_info=wave_info)
    sent = await _send_tg(msg)

    if sent:
        storage.save_mtf_signal(ticker, signal_ts, side, close_price)
        logger.info("MTF-сигнал отправлен: %s %s price=%.2f (ts=%s)",
                    ticker, side, close_price, signal_ts)
    return {"ticker": ticker, "side": side, "sent": sent, "signal_ts": signal_ts}


# ── Полный скан ─────────────────────────────────────────────────────────────

async def run_mtf_scan() -> list[dict]:
    """Скан watchlist: mtf_signal → дедуп → Telegram."""
    sent: list[dict] = []
    for ticker in _watchlist():
        try:
            result = await _scan_ticker(ticker)
            if result and result["sent"]:
                sent.append(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скана MTF по %s: %s", ticker, exc)
    return sent


# ── Доскачивание данных (4h + 1day) ─────────────────────────────────────────

_MTF_SYNC_HOURS = 6  # период повторной синхронизации данных


def _needs_sync(ticker: str, period: str) -> bool:
    last = storage.last_candle_time(ticker, period)
    if last is None:
        return True
    last_dt = datetime.fromisoformat(last)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_dt) > timedelta(hours=_MTF_SYNC_HOURS)


async def mtf_data_sync_task() -> None:
    """Фоновая синхронизация 4h+1day свечей MTF-тикеров с MOEX."""
    from . import data as data_module

    while True:
        try:
            for ticker in _watchlist():
                for period in ("4h", "1day"):
                    if not _needs_sync(ticker, period):
                        continue
                    try:
                        end = date.today()
                        start = end - timedelta(days=400)
                        await asyncio.to_thread(data_module.fetch_history, ticker, period, start, end)
                        logger.info("Свечи синхронизированы: %s %s", ticker, period)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Синхронизация %s %s не удалась: %s", period, ticker, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла синхронизации MTF: %s", exc)
        await asyncio.sleep(3600)


# ── Планировщик ─────────────────────────────────────────────────────────────

def _next_scan_delay(now: datetime | None = None) -> float:
    """Секунды до следующего скана (время из TRADER_MTF_SCANS)."""
    now = now or datetime.now(timezone.utc)
    targets: list[datetime] = []
    for hour, minute in trading_config.TRADER_MTF_SCANS:
        t = datetime.combine(now.date(), time(hour, minute), tzinfo=timezone.utc)
        if now >= t:
            t += timedelta(days=1)
        targets.append(t)
    return max((min(targets) - now).total_seconds(), 0.0)


async def mtf_scan_loop() -> None:
    """Ежедневно после закрытия 4h-баров: sleep → run_mtf_scan."""
    scans_str = ", ".join(f"{h:02d}:{m:02d}" for h, m in trading_config.TRADER_MTF_SCANS)
    logger.info(
        "Сканер MTF-сигналов запущен: сканы в %s UTC, сигналы с баров %s UTC, тикеры=%s",
        scans_str,
        ",".join(str(h) for h in trading_config.TRADER_MTF_SIGNAL_HOURS),
        ",".join(trading_config.TRADER_MTF_TICKERS),
    )
    if trading_config.TRADER_MTF_RUN_ON_STARTUP:
        try:
            sent = await run_mtf_scan()
            if sent:
                logger.info("Стартовый MTF-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Стартовый MTF-скан упал: %s", exc)

    while True:
        try:
            delay = _next_scan_delay()
            next_run = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info("Следующий MTF-скан: %s (через %.0f c)",
                        next_run.isoformat(timespec="seconds"), delay)
            await asyncio.sleep(delay)
            sent = await run_mtf_scan()
            if sent:
                logger.info("MTF-скан: отправлено %d сигналов", len(sent))
        except asyncio.CancelledError:
            logger.info("Сканер MTF-сигналов остановлен")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла MTF-сканера: %s", exc)
            await asyncio.sleep(3600)
