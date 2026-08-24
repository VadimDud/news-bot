"""Тесты сканера ROE-сигналов (signal_notifier): пояснения, дедуп, расписание."""

import asyncio
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

import app.signal_notifier as sn
from app import storage
from app.signals import roe_score_breakdown


def _candle_df(closes: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    """Свечи в формате storage.get_candles: колонка begin (строка), OHLCV."""
    ds = pd.date_range(start, periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "begin": [ts.strftime("%Y-%m-%d %H:%M:%S") for ts in ds],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    )


def _fund_rows(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    """Отчётность в формате save_fundamentals: date, roe, book_value_per_share."""
    return pd.DataFrame(
        [{"date": d, "roe": roe, "book_value_per_share": bvps} for d, roe, bvps in rows]
    )


# Дешёвая качественная бумага: ROE 25% (>15/>12), BVPS 100, цена 70 → P/B 0.7 ≤ 0.8.
_CHEAP = _fund_rows([("2023-12-31", 25.0, 100.0)])
# Дорогая плохая: ROE 5%, BVPS 50, цена 200 → P/B 4.0.
_EXPENSIVE = _fund_rows([("2023-12-31", 5.0, 50.0)])


# ── Расписание ──────────────────────────────────────────────────────────────

def test_next_scan_delay_uses_config(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "TRADER_SIGNALS_SCAN_HOUR", 10)
    monkeypatch.setattr(config, "TRADER_SIGNALS_SCAN_MINUTE", 15)

    before = datetime(2026, 8, 24, 9, 0, tzinfo=timezone.utc)
    assert sn._next_scan_delay(before) == pytest.approx(75 * 60)  # до 10:15 UTC

    after = datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc)
    assert sn._next_scan_delay(after) == pytest.approx((23 * 60 + 15) * 60)  # завтра 10:15


# ── Скоринг ────────────────────────────────────────────────────────────────

def _enriched(ticker: str, fund_raw: pd.DataFrame, n_days: int = 150):
    """Отчётность, обогащённая как в проде (avg_roe + roe_stability)."""
    storage.save_fundamentals(ticker, fund_raw)
    from app import fundamentals as fm

    end = pd.Timestamp("2024-01-01") + pd.Timedelta(days=n_days - 1)
    return fm.prepare_fundamentals_series(
        ticker, pd.Timestamp("2024-01-01").date(), end.date()
    )


def test_score_breakdown_cheap_vs_expensive():
    ds = pd.date_range("2024-01-01", periods=150)
    cheap_prices = pd.Series([70.0] * 150, index=ds)
    fund = _enriched("CHP", _CHEAP)
    info = roe_score_breakdown(cheap_prices, fund)
    assert info["score"] >= 0.4  # проходит порог входа
    assert info["current_pb"] == pytest.approx(0.7, abs=0.01)

    expensive_prices = pd.Series([200.0] * 150, index=ds)
    bad = roe_score_breakdown(expensive_prices, _enriched("EXPS", _EXPENSIVE))
    assert bad["score"] < 0.4


# ── Пояснения сигналов ─────────────────────────────────────────────────────

def _prepared(ticker: str, fund_raw: pd.DataFrame, df: pd.DataFrame):
    storage.save_fundamentals(ticker, fund_raw)
    from app import fundamentals as fm

    return fm.prepare_fundamentals_series(
        ticker, pd.to_datetime(df["begin"]).min().date(), pd.to_datetime(df["begin"]).max().date()
    )


def test_buy_signal_message_contains_ticker_and_thresholds():
    ticker = "SBER"
    df = _candle_df([70.0] * 260)
    df_idx = df.copy()
    df_idx["begin"] = pd.to_datetime(df_idx["begin"])
    df_idx = df_idx.set_index("begin")
    fund = _prepared(ticker, _CHEAP, df)

    params = dict(
        scoring=1, min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8,
        pb_exit=1.5, roe_exit=12.0, rebalance_days=1, min_score=0.4,
        w_roe=1.0, w_pb=1.0, w_momentum=0.5, w_dividend=0.5, w_stability=0.5,
        momentum_months=6,
    )
    info = sn.compute_ticker_signal(ticker, df_idx, fund, prev_position=0, **params)
    # цена всё время дешёвая: позиция открыта (вход мог быть давно — сравнение
    # идёт с известным сканеру состоянием, а не с хвостом ряда)
    assert info["position"] == 1
    assert info["action"] == "buy"
    msg = info["message"]
    assert "ПОКУПКИ — SBER" in msg
    assert "✅" in msg
    assert "Score:" in msg
    assert "Средний ROE" in msg


def test_buy_then_sell_flip_messages():
    ticker = "TEST"
    # 300 дней по 70 (вход и удержание), затем 10 дней по 160 → P/B 1.6 ≥ 1.5 → выход.
    df = _candle_df([70.0] * 300 + [160.0] * 10)
    df_idx = df.copy()
    df_idx["begin"] = pd.to_datetime(df_idx["begin"])
    df_idx = df_idx.set_index("begin")
    fund = _prepared(ticker, _CHEAP, df)

    params = dict(
        scoring=1, min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8,
        pb_exit=1.5, roe_exit=12.0, rebalance_days=1, min_score=0.4,
        w_roe=1.0, w_pb=1.0, w_momentum=0.5, w_dividend=0.5, w_stability=0.5,
        momentum_months=6,
    )
    # Сканер знал позицию 0, ряд пока только дешёвый → ПОКУПКА.
    cheap_only = df_idx.iloc[:300]
    buy_info = sn.compute_ticker_signal(ticker, cheap_only, fund, prev_position=0, **params)
    assert buy_info["position"] == 1
    assert buy_info["action"] == "buy"
    assert "ПОКУПКИ — TEST" in buy_info["message"]
    assert "Score:" in buy_info["message"]

    # Теперь сканер знал позицию 1, а цена ушла выше pb_exit → ПРОДАЖА.
    sell_info = sn.compute_ticker_signal(ticker, df_idx, fund, prev_position=1, **params)
    assert sell_info["position"] == 0
    assert sell_info["action"] == "sell"
    msg = sell_info["message"]
    assert "ПРОДАЖИ — TEST" in msg
    assert "P/B" in msg  # причина выхода по цене капитала


def test_no_reentry_while_expensive():
    """После жёсткого выхода дорогая бумага не покупается обратно по score."""
    ticker = "OSC"
    df = _candle_df([70.0] * 300 + [160.0] * 10)
    df_idx = df.copy()
    df_idx["begin"] = pd.to_datetime(df_idx["begin"])
    df_idx = df_idx.set_index("begin")
    fund = _prepared(ticker, _CHEAP, df)
    params = dict(
        scoring=1, min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8,
        pb_exit=1.5, roe_exit=12.0, rebalance_days=1, min_score=0.4,
        w_roe=1.0, w_pb=1.0, w_momentum=0.5, w_dividend=0.5, w_stability=0.5,
        momentum_months=6,
    )
    pos = sn.signals.roe_pb_position(df_idx, fund, **{
        k: v for k, v in params.items() if k != "scoring"
    } | {"scoring": 1})
    tail = pos.iloc[-10:].tolist()
    assert all(p == 0 for p in tail), f"осцилляция в хвосте: {tail}"


# ── Дедупликация / run_daily_scan ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_first_run_records_baseline_silently(monkeypatch):
    """Первый прогон по flat-бумаге не шлёт «продажу», а пишет baseline."""
    import app.data as data_module

    monkeypatch.setattr(data_module, "fetch_history", lambda *a, **k: None)
    storage.add_watchlist("FLAT")
    # дорогая плохая бумага, данные свежие (иначе сработал бы алерт о протухании)
    storage.save_candles("FLAT", "1day", _fresh_candles())
    storage.save_fundamentals("FLAT", _fund_at(10))

    sent_messages: list[str] = []

    async def fake_send(text: str) -> bool:
        sent_messages.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)
    await sn.run_daily_scan()

    assert sent_messages == []
    state = storage.get_signal_state("FLAT")
    assert state["position"] == 0
    assert state["notified_at"] is not None


@pytest.mark.asyncio
async def test_position_change_sends_buy_after_baseline(monkeypatch):
    import app.data as data_module

    monkeypatch.setattr(data_module, "fetch_history", lambda *a, **k: None)
    storage.add_watchlist("AAA")
    # baseline: дорого (нет позиции), данные свежие
    storage.save_candles("AAA", "1day", _fresh_candles(close=200.0))
    storage.save_fundamentals("AAA", _fund_prev_year_end(roe=5.0, bvps=50.0))

    sent_messages: list[str] = []

    async def fake_send(text: str) -> bool:
        sent_messages.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)
    await sn.run_daily_scan()  # baseline
    assert sent_messages == []

    # рынок подешевел: цена плавно 100 → 70 при BVPS 100 и ROE 25.
    # Падающая цена = текущий P/B в нижнем перцентиле истории (дешевизна ~1.0),
    # composite score ≈ 0.67 ≥ порога 0.5 из конфига → вход.
    storage.save_candles(
        "AAA", "1day", _fresh_candles(n=260, close=list(np.linspace(100.0, 70.0, 260)))
    )
    storage.delete_fundamentals("AAA")
    storage.save_fundamentals("AAA", _fund_prev_year_end(roe=25.0, bvps=100.0))
    await sn.run_daily_scan()

    assert len(sent_messages) == 1
    assert "ПОКУПКИ — AAA" in sent_messages[0]
    assert storage.get_signal_state("AAA")["position"] == 1

    # повторный прогон без изменений — тишина
    await sn.run_daily_scan()
    assert len(sent_messages) == 1


@pytest.mark.asyncio
async def test_missing_data_skipped(monkeypatch):
    """Тикер без данных не даёт сигнала, но попадает в алерт о проблемах данных."""
    storage.add_watchlist("NODATA")

    sent_messages: list[str] = []

    async def fake_send(text: str) -> bool:
        sent_messages.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)
    await sn.run_daily_scan()

    # Сигналов покупки/продажи нет...
    assert [m for m in sent_messages if "ПОКУПКИ" in m or "ПРОДАЖИ" in m] == []
    # ...но алерт о проблеме данных отправлен (это и есть цель мониторинга).
    alerts = [m for m in sent_messages if "ПРОБЛЕМА ДАННЫХ" in m]
    assert len(alerts) == 1
    assert "NODATA: нет истории свечей" in alerts[0]


# ── Здоровье данных: автообновление + алерты ───────────────────────────────

def _fresh_candles(n: int = 60, close: float | list[float] = 200.0) -> pd.DataFrame:
    """Свечи, заканчивающиеся сегодняшним днём (свежие)."""
    end = pd.Timestamp.now().normalize()
    ds = pd.date_range(end - pd.Timedelta(days=n - 1), periods=n)
    closes = list(close) if isinstance(close, (list, tuple)) else [close] * n
    return pd.DataFrame(
        {
            "begin": [d.strftime("%Y-%m-%d %H:%M:%S") for d in ds],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": 1000.0,
        }
    )


def _fund_at(days_ago: int, roe: float = 5.0, bvps: float = 50.0) -> pd.DataFrame:
    d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
    return pd.DataFrame([{"date": d, "roe": roe, "book_value_per_share": bvps}])


def _fund_prev_year_end(roe: float = 5.0, bvps: float = 50.0) -> pd.DataFrame:
    """Отчётность за прошлый год (дата 31.12): видна анти-look-ahead логикой."""
    y = datetime.now(timezone.utc).year - 1
    return pd.DataFrame([{"date": f"{y}-12-31", "roe": roe, "book_value_per_share": bvps}])


@pytest.mark.asyncio
async def test_no_alert_when_data_fresh(monkeypatch):
    storage.add_watchlist("FRESH")
    storage.save_candles("FRESH", "1day", _fresh_candles())
    storage.save_fundamentals("FRESH", _fund_at(10))

    import app.data as data_module

    monkeypatch.setattr(data_module, "fetch_history", lambda *a, **k: None)

    sent_messages: list[str] = []

    async def fake_send(text: str) -> bool:
        sent_messages.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)
    await sn.run_daily_scan()
    assert [m for m in sent_messages if "ПРОБЛЕМА ДАННЫХ" in m] == []


@pytest.mark.asyncio
async def test_stale_and_update_failure_alert_sent_once(monkeypatch):
    storage.add_watchlist("STALE")
    storage.add_watchlist("FAIL")
    # STALE: свечи двухлетней давности + старая отчётность
    storage.save_candles("STALE", "1day", _candle_df([200.0] * 30))
    storage.save_fundamentals("STALE", _fund_at(600))
    # FAIL: данные свежие, но MOEX при обновлении падает
    storage.save_candles("FAIL", "1day", _fresh_candles())
    storage.save_fundamentals("FAIL", _fund_at(10))

    import app.data as data_module

    def boom(*a, **k):
        raise RuntimeError("MOEX API недоступен")

    monkeypatch.setattr(data_module, "fetch_history", boom)

    sent_messages: list[str] = []

    async def fake_send(text: str) -> bool:
        sent_messages.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)
    await sn.run_daily_scan()

    alerts = [m for m in sent_messages if "ПРОБЛЕМА ДАННЫХ" in m]
    assert len(alerts) == 1, f"ожидался ровно один алерт, пришло {len(alerts)}"
    assert "STALE: свечи устарели" in alerts[0]
    assert "FAIL: ошибка обновления свечей MOEX: MOEX API недоступен" in alerts[0]

    # Повторный прогон в тот же день — алерт не дублируется.
    before = len(sent_messages)
    await sn.run_daily_scan()
    assert len([m for m in sent_messages if "ПРОБЛЕМА ДАННЫХ" in m]) == 1
    assert len(sent_messages) == before


def test_freshness_issues_direct():
    assert sn._freshness_issues("UNKNOWN") != []  # нет ни свечей, ни отчётности


async def test_data_alert_interval_disabled(monkeypatch):
    """TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS=0 → алерты отключены."""
    from app import config as cfg
    monkeypatch.setattr(cfg, "TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS", 0)
    result = await sn._send_data_alert("test")
    assert result is False


async def test_data_alert_interval_respects_days(monkeypatch):
    """Алерт не отправляется, если прошло меньше N дней с последнего."""
    from datetime import date

    from app import config as cfg
    monkeypatch.setattr(cfg, "TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS", 7)

    sent = []

    async def fake_send(text):
        sent.append(text)
        return True

    monkeypatch.setattr(sn, "send_telegram_message", fake_send)

    # Первый алерт — отправляется
    assert await sn._send_data_alert("first")
    assert len(sent) == 1

    # Сегодня ещё раз — пропуск (прошло 0 дней < 7)
    sent.clear()
    assert await sn._send_data_alert("second") is False
    assert len(sent) == 0

    # Подменяем дату последнего алерта на 3 дня назад
    three_days_ago = (date.today() - timedelta(days=3)).isoformat()
    monkeypatch.setattr(storage, "get_setting", lambda key: three_days_ago)
    # (today - 3_days_ago).days == 3 < 7 → пропуск
    sent.clear()
    assert await sn._send_data_alert("third") is False
    assert len(sent) == 0

    # 8 дней назад → отправляется
    eight_days_ago = (date.today() - timedelta(days=8)).isoformat()
    monkeypatch.setattr(storage, "get_setting", lambda key: eight_days_ago)
    sent.clear()
    assert await sn._send_data_alert("fourth") is True
    assert len(sent) == 1
