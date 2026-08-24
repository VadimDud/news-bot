"""Дневной сканер сигналов ROE+P/B и отправка в Telegram.

Работает без T-Bank API: берёт дневные свечи из локальной SQLite (MOEX ISS)
и отчётность fundamentals из той же БД. Скан запускается каждое утро после
открытия рынка (по умолчанию 08:30 UTC ≈ 30 мин после 07:00 UTC открытия MOEX).

Логика:
- позиция считается через signals.roe_pb_position (по умолчанию scoring=1 —
  мультифакторный скоринг; настройки из бэктестов);
- переворот позиции flat→long = ПОКУПКА, long→flat = ПРОДАЖА;
- первое наблюдение тикера фиксируется в БД молча (baseline), иначе при
  каждом рестарте контейнера шли бы ложные «продажи» по flat-бумагам;
- сообщение отправляется только при смене позиции (дедупликация).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import aiohttp
import pandas as pd

from . import config as trading_config
from . import fundamentals as fundamentals_module
from . import signals
from . import storage

logger = logging.getLogger("moex_trader.signal_notifier")

MSK = timezone(timedelta(hours=3))  # время биржи для метки в сообщении

DATA_ALERT_SETTING = "signals_data_alert_sent_on"  # дата последнего алерта (дедуп раз в сутки)


def _today() -> date:
    return datetime.now(timezone.utc).date()


# ── Telegram ───────────────────────────────────────────────────────────────

async def send_telegram_message(text: str) -> bool:
    """Отправить сообщение админу (BOT_TOKEN/ADMIN_ID из общего .env)."""
    token = trading_config.TELEGRAM_BOT_TOKEN
    chat_id = trading_config.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.warning("BOT_TOKEN/ADMIN_ID не заданы — сигнал не отправлен")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    # api.telegram.org из РФ часто недоступен напрямую — идём через локальный
    # прокси (как новостной бот). Пустая настройка = прямое соединение.
    proxy = trading_config.TRADER_TG_PROXY or None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30), proxy=proxy) as resp:
                if resp.status != 200:
                    logger.error("Telegram error %d: %s", resp.status, (await resp.text())[:200])
                    return False
                return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка отправки в Telegram: %s", exc)
        return False


# ── Форматирование ─────────────────────────────────────────────────────────

def _fmt_pct(val: float | None) -> str:
    return "—" if val is None else f"{val:.1f}%"


def _fmt_money(val: float | None) -> str:
    return "—" if val is None else f"{val:.2f} ₽"


def _check(ok: bool) -> str:
    return "✅" if ok else "❌"


def explain_roe_signal(
    ticker: str,
    df: pd.DataFrame,
    fund: pd.DataFrame,
    *,
    action: str,
    score_info: dict,
    min_avg_roe: float,
    min_single_roe: float,
    pb_entry: float,
    pb_exit: float,
    roe_exit: float,
    min_score: float,
    pb_exit_partial: float | None = None,
    momentum_months: int = 6,
) -> str:
    """Человекочитаемое пояснение сигнала ROE+P/B (plain text).

    ``fund`` — обогащённый ряд отчётности (prepare_fundamentals_series):
    колонки date, roe, book_value_per_share, avg_roe, roe_stability.
    """
    last_close = float(df["close"].iloc[-1])
    last_row = fund.iloc[-1]
    avg_roe = None if pd.isna(last_row.get("avg_roe")) else float(last_row["avg_roe"])
    latest_roe = None if pd.isna(last_row.get("roe")) else float(last_row["roe"])
    bvps = None if pd.isna(last_row.get("book_value_per_share")) else float(last_row["book_value_per_share"])

    pb = score_info.get("current_pb")
    score = score_info.get("score", 0.0)
    mom_pct = score_info.get("momentum_ret_pct")

    now_msk = datetime.now(MSK).strftime("%d.%m.%Y %H:%M")
    header = (
        f"📈 СИГНАЛ ПОКУПКИ — {ticker}"
        if action == "buy"
        else f"📉 СИГНАЛ ПРОДАЖИ — {ticker}"
    )
    lines = [
        header,
        f"Стратегия ROE+P/B • {now_msk} МСК",
        "",
        f"Цена: {last_close:.2f} ₽",
        f"{_check(avg_roe is not None and avg_roe >= min_avg_roe)} "
        f"Средний ROE (10 лет): {_fmt_pct(avg_roe)} (порог ≥{min_avg_roe}%)",
        f"{_check(latest_roe is not None and latest_roe >= min_single_roe)} "
        f"ROE последнего года: {_fmt_pct(latest_roe)} (порог ≥{min_single_roe}%)",
    ]
    if pb is not None:
        lines.append(
            f"{_check(pb <= pb_entry)} P/B: {pb:.2f} "
            f"(вход ≤{pb_entry:.2f}, BVPS {_fmt_money(bvps)})"
        )
    else:
        lines.append(f"❌ P/B: — (BVPS отсутствует)")
    lines.append(f"📊 Score: {score:.2f} (порог ≥{min_score:.2f})")
    lines.append(
        "   • Качество ROE: {:.2f} | Дешевизна P/B: {:.2f}".format(
            score_info.get("s_roe", 0.0), score_info.get("s_pb", 0.0)
        )
    )
    lines.append(
        "   • Моментум: {:.2f} | Стабильность ROE: {:.2f}".format(
            score_info.get("s_mom", 0.0), score_info.get("s_stab", 0.0)
        )
    )
    lines.append(f"📈 Моментум {momentum_months} мес: {_fmt_pct(mom_pct)}")
    lines.append("")

    partial = pb_exit_partial if pb_exit_partial is not None else trading_config.TRADER_ROE_PB_EXIT_PARTIAL
    if action == "buy":
        reason = (
            f"composite score {score:.2f} ≥ порога {min_score:.2f}: бизнес качественный"
            + (
                f" (ROE выше порогов)"
                if avg_roe is not None and avg_roe >= min_avg_roe and latest_roe is not None and latest_roe >= min_single_roe
                else ""
            )
            + (
                f", акция торгуется ниже балансовой стоимости (P/B {pb:.2f} ≤ {pb_entry:.2f})"
                if pb is not None and pb <= pb_entry
                else ""
            )
        )
        lines.append(f"Почему покупка: {reason}.")
    else:
        exit_reasons = []
        if pb is not None and pb >= pb_exit:
            exit_reasons.append(
                f"цена выросла до {pb:.2f} стоимости капитала (порог ≥{pb_exit:.2f})"
            )
        if latest_roe is not None and latest_roe < roe_exit:
            exit_reasons.append(f"ROE опустился до {_fmt_pct(latest_roe)} (порог <{roe_exit}%)")
        if score < min_score * 0.6:
            exit_reasons.append(f"score {score:.2f} ниже {min_score * 0.6:.2f}")
        reason = " или ".join(exit_reasons) if exit_reasons else "условия выхода выполнены"
        lines.append(f"Почему продажа: {reason}.")

    lines.append(
        f"Выход: частичная продажа при P/B ≥{partial:.2f}, полная при ≥{pb_exit:.2f}"
        f" или падении ROE ниже {roe_exit:.0f}%."
    )
    return "\n".join(lines)


# ── Скан одного тикера ─────────────────────────────────────────────────────

def compute_ticker_signal(
    ticker: str,
    df: pd.DataFrame,
    fund_enriched: pd.DataFrame,
    *,
    prev_position: int | None = None,
    scoring: int,
    min_avg_roe: float,
    min_single_roe: float,
    pb_entry: float,
    pb_exit: float,
    roe_exit: float,
    rebalance_days: int,
    min_score: float,
    w_roe: float,
    w_pb: float,
    w_momentum: float,
    w_dividend: float,
    w_stability: float,
    momentum_months: int,
    stop_loss_pct: float = 0.0,
    dividends: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Позиция на последнем баре + факторы + готовый текст пояснения.

    ``prev_position`` — позиция, известная сканеру с прошлого прогона (БД).
    Если задана, действие определяется относительно неё (правильный способ для
    ежедневного сканера: вход мог случиться много баров назад). Если None —
    по перевороту в последних двух барах ряда.
    """
    prices = df["close"]
    pos_series = signals.roe_pb_position(
        df,
        fund_enriched,
        min_avg_roe=min_avg_roe,
        min_single_roe=min_single_roe,
        pb_entry=pb_entry,
        pb_exit=pb_exit,
        roe_exit=roe_exit,
        rebalance_days=rebalance_days,
        scoring=scoring,
        w_roe=w_roe,
        w_pb=w_pb,
        w_momentum=w_momentum,
        w_dividend=w_dividend,
        w_stability=w_stability,
        min_score=min_score,
        momentum_months=momentum_months,
        stop_loss_pct=stop_loss_pct,
        dividends=dividends,
    )
    last_pos = int(pos_series.iloc[-1]) if not pos_series.empty else 0

    if prev_position is not None:
        base = int(prev_position)
    else:
        base = int(pos_series.iloc[-2]) if len(pos_series) >= 2 else 0
    action = "hold" if last_pos == base else ("buy" if last_pos == 1 else "sell")

    score_info = signals.roe_score_breakdown(
        prices,
        fund_enriched,
        w_roe=w_roe,
        w_pb=w_pb,
        w_momentum=w_momentum,
        w_dividend=w_dividend,
        w_stability=w_stability,
        momentum_months=momentum_months,
        dividends=dividends,
    )

    result: dict[str, Any] = {
        "ticker": ticker,
        "position": last_pos,
        "action": action,
        "score": score_info.get("score", 0.0),
    }
    if action != "hold":
        result["message"] = explain_roe_signal(
            ticker,
            df,
            fund_enriched,
            action=action,
            score_info=score_info,
            min_avg_roe=min_avg_roe,
            min_single_roe=min_single_roe,
            pb_entry=pb_entry,
            pb_exit=pb_exit,
            roe_exit=roe_exit,
            min_score=min_score,
            momentum_months=momentum_months,
        )
    return result


# ── Здоровье данных: автообновление + алерты о протухании ─────────────────

def _refresh_ticker_candles(ticker: str) -> str | None:
    """Хвостовая догрузка дневных свечей с MOEX (moexalgo). Текст ошибки или None."""
    from . import data as data_module

    last = storage.last_candle_time(ticker, "1day")
    if last is None:
        return "нет истории свечей в БД — скачайте диапазон через дашборд (страница /data)"
    end = _today()
    start = min(pd.Timestamp(last).date(), end - timedelta(days=7))
    try:
        data_module.fetch_history(ticker, "1day", start, end, use_cache=True)
        return None
    except Exception as exc:  # noqa: BLE001
        return f"ошибка обновления свечей MOEX: {exc}"


def _refresh_ticker_dividends(ticker: str) -> str | None:
    """Загрузка дивидендов с T-Bank Invest API. Текст ошибки или None."""
    token = trading_config.TINKOFF_API_TOKEN
    if not token:
        return None  # токен не задан — тихий пропуск
    try:
        from tinkoff.invest import Client
        with Client(token=token, app_name="moex-trader") as client:
            resp = client.instruments.find_instrument(query=ticker)
            matches = [
                item for item in resp.instruments
                if item.ticker.upper() == ticker.upper()
                and getattr(item, "instrument_type", "") == "share"
                and item.figi
            ]
            if not matches and resp.instruments:
                matches = [resp.instruments[0]]
            if not matches:
                return f"T-Bank: инструмент {ticker} не найден"
            figi = matches[0].figi
            div_resp = client.instruments.get_dividends(
                instrument_id=figi,
            )
            rows = []
            for d in div_resp.dividends:
                rec = d.record_date
                lbb = d.last_buy_date
                amount = float(d.dividend_net.units) + float(d.dividend_net.nano) / 1e9
                if amount <= 0 or rec is None:
                    continue
                rows.append({
                    "date": rec.date().isoformat() if hasattr(rec, "date") else str(rec)[:10],
                    "dividend": amount,
                    "buy_before": lbb.date().isoformat() if hasattr(lbb, "date") and lbb is not None else None,
                    "period": str(getattr(d, "regularity", "")) or None,
                })
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows)
                storage.save_dividends(ticker, df, source="tinkoff")
                logger.info("T-Bank дивиденды %s: %d записей", ticker, len(rows))
            return None
    except Exception as exc:  # noqa: BLE001
        return f"ошибка загрузки дивидендов T-Bank {ticker}: {exc}"


def _freshness_issues(ticker: str) -> list[str]:
    """Проблемы свежести данных тикера (после попытки обновления)."""
    issues: list[str] = []
    last = storage.last_candle_time(ticker, "1day")
    if not last:
        issues.append("свечей в БД нет")
    else:
        age = (_today() - pd.Timestamp(last).date()).days
        if age > trading_config.TRADER_SIGNALS_MAX_STALE_DAYS:
            issues.append(f"свечи устарели на {age} дн. (последняя {last[:10]})")
    stats = storage.fundamentals_stats(ticker)
    if not stats.get("count"):
        issues.append("отчётности ROE/BVPS в БД нет")
    elif stats.get("max_date"):
        age = (_today() - date.fromisoformat(stats["max_date"])).days
        if age > trading_config.TRADER_SIGNALS_FUND_MAX_AGE_DAYS:
            issues.append(f"отчётность старая: {age} дн. (последняя {stats['max_date']}) — сигналы считаются по устаревшему ROE/BVPS")
    return issues


def _format_data_alert(issues_by_ticker: dict[str, list[str]]) -> str:
    now_msk = datetime.now(MSK).strftime("%d.%m.%Y %H:%M")
    lines = [f"⚠️ ПРОБЛЕМА ДАННЫХ ROE-сканера • {now_msk} МСК", ""]
    for ticker, issues in issues_by_ticker.items():
        for issue in issues:
            lines.append(f"• {ticker}: {issue}")
    lines += [
        "",
        "Сканер продолжает работать на имеющихся данных, но сигналы могут быть неверными.",
        "Свечи: moexalgo/MOEX, докачиваются автоматически; если не помогает — страница /data.",
        "Отчётность: conomy.ru через страницу /fundamentals.",
        "Алерт повторяется раз в сутки, пока проблема не исчезнет.",
    ]
    return "\n".join(lines)


async def _send_data_alert(text: str) -> bool:
    """Отправить алерт о данных с интервалом из TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS.

    0 = алерты отключены; 1 = раз в сутки; N = раз в N дней.
    Дата хранится в settings (переживает рестарты).
    """
    interval = trading_config.TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS
    if interval <= 0:
        return False
    today_iso = _today().isoformat()
    raw = storage.get_setting(DATA_ALERT_SETTING)
    if raw:
        try:
            last = date.fromisoformat(raw)
        except ValueError:
            last = None
        if last is not None and (_today() - last).days < interval:
            logger.info("Алерт о данных: интервал %d дн. — пропуск (последний %s)", interval, raw)
            return False
    if await send_telegram_message(text):
        storage.set_setting(DATA_ALERT_SETTING, today_iso)
        return True
    return False


# ── Ежедневный скан ────────────────────────────────────────────────────────

def _watchlist() -> list[str]:
    stored = storage.list_watchlist()
    if stored:
        return stored
    return list(trading_config.WATCH_TICKERS)


async def run_daily_scan() -> list[dict]:
    """Один проход по watchlist: детект смены позиции и отправка сигналов.

    Возвращает список отправленных сигналов [{ticker, action}].
    """
    cfg = trading_config
    params = dict(
        scoring=cfg.TRADER_ROE_SCORING,
        min_avg_roe=cfg.TRADER_ROE_MIN_AVG_ROE,
        min_single_roe=cfg.TRADER_ROE_MIN_SINGLE_ROE,
        pb_entry=cfg.TRADER_ROE_PB_ENTRY,
        pb_exit=cfg.TRADER_ROE_PB_EXIT,
        roe_exit=cfg.TRADER_ROE_ROE_EXIT,
        # Прибыльный вариант бэктеста на SBER 2020–2026: scoring s=0.5/rebal=21д
        # дал +80.5% (DD 9%, PF 5.77) против +68.4%/PF 1.43 у rebal=2.
        rebalance_days=21,
        min_score=cfg.TRADER_ROE_MIN_SCORE,
        w_roe=cfg.TRADER_ROE_W_ROE,
        w_pb=cfg.TRADER_ROE_W_PB,
        w_momentum=cfg.TRADER_ROE_W_MOMENTUM,
        w_dividend=cfg.TRADER_ROE_W_DIVIDEND,
        w_stability=cfg.TRADER_ROE_W_STABILITY,
        momentum_months=6,
        stop_loss_pct=cfg.TRADER_ROE_STOP_LOSS_PCT,
    )

    sent: list[dict] = []
    data_issues: dict[str, list[str]] = {}
    for ticker in _watchlist():
        try:
            # 0) Здоровье данных: догрузить хвост свечей и проверить свежесть.
            issues: list[str] = []
            if cfg.TRADER_SIGNALS_AUTO_UPDATE:
                err = await asyncio.to_thread(_refresh_ticker_candles, ticker)
                if err:
                    issues.append(err)
                if cfg.TRADER_SIGNALS_AUTO_DIVIDENDS:
                    div_err = await asyncio.to_thread(_refresh_ticker_dividends, ticker)
                    if div_err:
                        issues.append(div_err)
            issues.extend(_freshness_issues(ticker))
            data_issues[ticker] = issues

            df_raw = storage.get_candles(ticker, "1day")
            if df_raw.empty or len(df_raw) < 3:
                logger.info("Нет свечей по %s — пропуск", ticker)
                continue
            # индекс-даты нужны сигнальным функциям (prices.index)
            df = df_raw.copy()
            df["begin"] = pd.to_datetime(df["begin"])
            df = df.set_index("begin").sort_index()[["open", "high", "low", "close", "volume"]]

            raw_fund = storage.load_fundamentals(ticker)
            if raw_fund.empty:
                logger.info("Нет отчётности по %s — пропуск", ticker)
                continue
            fund = fundamentals_module.prepare_fundamentals_series(
                ticker, df.index.min().date(), df.index.max().date()
            )
            if fund.empty:
                fund = raw_fund  # fallback: без avg_roe/stability (скоринг их пересчитает)

            div_df = storage.load_dividends(ticker, df.index.min().date(), df.index.max().date())
            div_param = div_df if not div_df.empty else None

            prev = storage.get_signal_state(ticker)
            known_prev: int | None = (
                int(prev["position"]) if prev["notified_at"] is not None else None
            )
            info = compute_ticker_signal(
                ticker, df, fund, prev_position=known_prev,
                dividends=div_param, **params,
            )

            now_iso = datetime.now(timezone.utc).isoformat()
            if known_prev is None:
                # Первое наблюдение: фиксируем baseline молча, чтобы после
                # рестартов не сыпались ложные «продажи» по flat-бумагам.
                storage.set_signal_state(ticker, info["position"], now_iso)
                logger.info("Baseline %s: position=%d", ticker, info["position"])
                continue
            if info["position"] == known_prev:
                continue

            message = info.get("message")
            if message and await send_telegram_message(message):
                storage.set_signal_state(ticker, info["position"], now_iso)
                sent.append({"ticker": ticker, "action": info["action"]})
                logger.info("Сигнал отправлен: %s %s", info["action"].upper(), ticker)
            else:
                logger.warning("Не удалось отправить сигнал по %s", ticker)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка скана %s: %s", ticker, exc)

    # Сводный алерт о проблемах данных — не чаще раза в сутки.
    problems = {t: i for t, i in data_issues.items() if i}
    if problems:
        if await _send_data_alert(_format_data_alert(problems)):
            logger.warning("Отправлен алерт о данных: %s", {t: len(i) for t, i in problems.items()})
        else:
            logger.info("Алерт о данных не отправлен (дедуп или ошибка сети)")
    return sent


# ── Расписание ─────────────────────────────────────────────────────────────

def _next_scan_delay(now: datetime | None = None) -> float:
    """Секунды до следующего скана (время из TRADER_SIGNALS_SCAN_HOUR/MINUTE)."""
    now = now or datetime.now(timezone.utc)
    target = datetime.combine(
        now.date(),
        time(trading_config.TRADER_SIGNALS_SCAN_HOUR, trading_config.TRADER_SIGNALS_SCAN_MINUTE),
        tzinfo=timezone.utc,
    )
    if now >= target:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 0.0)


async def scan_loop() -> None:
    """Каждое утро после открытия рынка: sleep → run_daily_scan."""
    logger.info(
        "Сканер ROE-сигналов запущен: ежедневно %02d:%02d UTC%s",
        trading_config.TRADER_SIGNALS_SCAN_HOUR,
        trading_config.TRADER_SIGNALS_SCAN_MINUTE,
        ", стартовый прогон включён" if trading_config.TRADER_SIGNALS_RUN_ON_STARTUP else "",
    )
    if trading_config.TRADER_SIGNALS_RUN_ON_STARTUP:
        try:
            await run_daily_scan()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Стартовый скан упал: %s", exc)

    while True:
        try:
            delay = _next_scan_delay()
            next_run = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info("Следующий скан: %s (через %.0f c)", next_run.isoformat(timespec="seconds"), delay)
            await asyncio.sleep(delay)
            await run_daily_scan()
        except asyncio.CancelledError:
            logger.info("Сканер ROE-сигналов остановлен")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка цикла сканера: %s", exc)
            await asyncio.sleep(3600)
