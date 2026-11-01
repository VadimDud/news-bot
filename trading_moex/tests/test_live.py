"""Regression tests for live position and risk handling."""

from types import SimpleNamespace

from app.live import LiveTrader, _closed_candles


def _money(units: int, nano: int = 0):
    return SimpleNamespace(units=units, nano=nano)


def test_positions_preserve_short_direction_and_positive_close_quantity():
    trader = LiveTrader()
    portfolio = SimpleNamespace(
        positions=[
            SimpleNamespace(
                figi="short-figi",
                quantity=_money(-3),
                current_price=_money(100),
                expected_yield=_money(-2),
            )
        ]
    )

    assert trader._positions_from_portfolio(portfolio) == [
        {
            "figi": "short-figi",
            "quantity": 3,
            "direction": "short",
            "price": 100.0,
            "pnl": -2.0,
        }
    ]


def test_short_stop_distance_is_positive():
    trader = LiveTrader()
    trader._equity = 100_000
    trader.strategy_params = {"risk_pct": 1.0}

    # Short entry at 100 with a protective stop at 105 risks 5 per share.
    assert trader._risk_size(100.0, 105.0) == 200


def test_reconciliation_accepts_matching_long_and_short_positions():
    trader = LiveTrader()
    trader.entries = {
        "SBER": {"figi": "long-figi", "size": 10, "direction": "long"},
        "LKOH": {"figi": "short-figi", "size": 3, "direction": "short"},
    }

    result = trader._reconcile_positions(
        {"SBER": "long-figi", "LKOH": "short-figi"},
        [
            {"figi": "long-figi", "quantity": 10, "direction": "long"},
            {"figi": "short-figi", "quantity": 3, "direction": "short"},
        ],
    )

    assert result == {"ok": True, "issues": []}


def test_reconciliation_blocks_unknown_broker_position():
    trader = LiveTrader()
    trader.entries = {}

    result = trader._reconcile_positions(
        {"SBER": "long-figi"},
        [{"figi": "long-figi", "quantity": 1, "direction": "long"}],
    )

    assert result["ok"] is False
    assert "биржевая позиция отсутствует локально" in result["issues"][0]


def test_reconciliation_blocks_quantity_mismatch():
    trader = LiveTrader()
    trader.entries = {"SBER": {"figi": "figi", "size": 10, "direction": "long"}}

    result = trader._reconcile_positions(
        {"SBER": "figi"},
        [{"figi": "figi", "quantity": 4, "direction": "long"}],
    )

    assert result["ok"] is False
    assert "количество" in result["issues"][0]


def test_reconciliation_ignores_unwatched_broker_position():
    trader = LiveTrader()
    trader.entries = {}

    result = trader._reconcile_positions(
        {"SBER": "watched-figi"},
        [{"figi": "other-figi", "quantity": 1, "direction": "long"}],
    )

    assert result == {"ok": True, "issues": []}


def test_cap_position_size_limits_long_by_cash_and_equity(monkeypatch):
    trader = LiveTrader()
    trader._equity = 100_000
    trader._available_cash = 1_000
    monkeypatch.setattr("app.config.TRADER_MAX_POSITION_PCT", 50.0)

    # Cash allows 10 shares, despite the risk model requesting more.
    assert trader._cap_position_size(100, 100.0, "long") == 10


def test_cap_position_size_limits_short_by_equity():
    trader = LiveTrader()
    trader._equity = 100_000
    trader._available_cash = 0

    assert trader._cap_position_size(1_000, 1_000.0, "short") == 50


def test_cap_position_size_rejects_when_long_cash_is_empty():
    trader = LiveTrader()
    trader._equity = 100_000
    trader._available_cash = 0

    assert trader._cap_position_size(1, 100.0, "long") == 0


def test_available_cash_uses_rub_balance_minus_blocked():
    trader = LiveTrader()

    class Operations:
        async def get_positions(self, **kwargs):
            return SimpleNamespace(
                money=[
                    SimpleNamespace(
                        currency="rub",
                        units=10_000,
                        nano=0,
                        blocked=_money(1_500),
                    )
                ]
            )

    class Client:
        operations = Operations()

    import asyncio

    available = asyncio.run(
        trader._available_cash_from_broker(Client(), "account", SimpleNamespace())
    )
    assert available == 8_500


def test_circuit_breaker_trips_on_daily_loss(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 10.0)

    from datetime import datetime, timezone

    trader._update_circuit(100_000, datetime(2026, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(97_900, datetime(2026, 1, 1, 1, tzinfo=timezone.utc))

    assert trader._circuit["tripped"] is True
    assert "дневной убыток" in trader._circuit["reason"]


def test_circuit_breaker_schedules_alert_only_once(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 0.0)
    scheduled = []
    monkeypatch.setattr(trader, "_send_circuit_alert", lambda reason: reason)

    class Loop:
        def create_task(self, task):
            scheduled.append(task)

    monkeypatch.setattr("asyncio.get_running_loop", lambda: Loop())

    from datetime import datetime, timezone

    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trader._update_circuit(100_000, at)
    trader._update_circuit(97_000, at)
    trader._update_circuit(96_000, at)

    assert len(scheduled) == 1
    assert trader._circuit["alert_sent"] is True


def test_circuit_alert_failure_does_not_raise():
    import asyncio
    from unittest.mock import AsyncMock

    trader = LiveTrader()
    trader._equity = 97_000

    failed_sender = AsyncMock(side_effect=RuntimeError("telegram unavailable"))
    import app.signal_notifier

    original = app.signal_notifier.send_telegram_message
    app.signal_notifier.send_telegram_message = failed_sender
    try:
        # Ошибка Telegram не должна выйти наружу в live-цикл.
        asyncio.run(trader._send_circuit_alert("test"))
    finally:
        app.signal_notifier.send_telegram_message = original


def test_circuit_breaker_resets_on_new_day(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 0.0)

    from datetime import datetime, timezone

    trader._update_circuit(100_000, datetime(2026, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(97_000, datetime(2026, 1, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(97_000, datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert trader._circuit["tripped"] is False
    assert trader._circuit["day_start_equity"] == 97_000


def test_circuit_breaker_keeps_historical_peak_across_days(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 0.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 10.0)

    from datetime import datetime, timezone

    trader._update_circuit(100_000, datetime(2026, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(95_000, datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert trader._circuit["peak_equity"] == 100_000
    assert trader._circuit["tripped"] is False


def test_persistent_drawdown_stays_blocked_after_day_rollover(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 10.0)
    scheduled = []

    def schedule(reason, key=None):
        if not trader._circuit["alert_sent"]:
            scheduled.append(key)
            trader._circuit["alert_sent"] = True

    monkeypatch.setattr(trader, "_schedule_circuit_alert", schedule)

    from datetime import datetime, timezone

    trader._update_circuit(100_000, datetime(2026, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(89_000, datetime(2026, 1, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(89_000, datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert trader._circuit["tripped"] is True
    assert trader._circuit["alert_key"] == "drawdown"
    assert scheduled == ["drawdown"]


def test_daily_loss_resets_when_drawdown_is_not_exceeded(monkeypatch):
    trader = LiveTrader()
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 10.0)

    from datetime import datetime, timezone

    trader._update_circuit(100_000, datetime(2026, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(97_000, datetime(2026, 1, 1, 1, tzinfo=timezone.utc))
    trader._update_circuit(97_000, datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert trader._circuit["tripped"] is False
    assert trader._circuit["alert_key"] is None


def test_reset_circuit_breaker_clears_state(monkeypatch):
    trader = LiveTrader()
    trader._circuit.update({
        "day": "2026-01-01",
        "day_start_equity": 100_000,
        "peak_equity": 100_000,
        "tripped": True,
        "reason": "test",
        "alert_sent": True,
    })
    trader.reset_circuit_breaker()

    assert trader._circuit == {
        "day": None,
        "day_start_equity": None,
        "peak_equity": None,
        "tripped": False,
        "reason": None,
        "alert_sent": False,
        "alert_key": None,
    }


def test_reset_circuit_breaker_requires_stopped_live():
    trader = LiveTrader()
    trader.running = True

    import pytest

    with pytest.raises(RuntimeError, match="остановите live-цикл"):
        trader.reset_circuit_breaker()


def test_strategy_change_requires_stopped_live():
    trader = LiveTrader()
    trader.running = True

    import pytest

    with pytest.raises(RuntimeError, match="сменой стратегии"):
        trader.set_strategy("rsi")


def test_mode_change_requires_stopped_live():
    trader = LiveTrader()
    trader.running = True

    import pytest

    with pytest.raises(RuntimeError, match="сменой режима"):
        trader.set_dry_run(not trader.dry_run)


def test_same_mode_can_be_saved_while_live():
    trader = LiveTrader()
    trader.running = True
    current = trader.dry_run

    trader.set_dry_run(current)

    assert trader.dry_run is current


def test_risk_snapshot_reports_loss_and_drawdown(monkeypatch):
    trader = LiveTrader()
    trader._equity = 95_000
    trader._available_cash = 40_000
    trader._circuit.update({"day_start_equity": 100_000, "peak_equity": 110_000})
    monkeypatch.setattr("app.config.TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr("app.config.TRADER_MAX_DRAWDOWN_PCT", 10.0)

    snapshot = trader._risk_snapshot()

    assert snapshot["equity"] == 95_000
    assert snapshot["available_cash"] == 40_000
    assert snapshot["daily_loss_pct"] == 5.0
    assert snapshot["drawdown_pct"] == round(15_000 / 110_000 * 100, 2)


def test_open_last_candle_is_excluded_from_live_data():
    import pandas as pd

    index = pd.to_datetime(["2026-01-01 10:00", "2026-01-01 11:00"], utc=True)
    df = pd.DataFrame({"close": [100.0, 101.0]}, index=index)

    closed = _closed_candles(df, "HOUR", pd.Timestamp("2026-01-01 11:30", tz="UTC"))

    assert list(closed["close"]) == [100.0]


def test_closed_last_candle_is_kept():
    import pandas as pd

    index = pd.to_datetime(["2026-01-01 10:00", "2026-01-01 11:00"], utc=True)
    df = pd.DataFrame({"close": [100.0, 101.0]}, index=index)

    closed = _closed_candles(df, "HOUR", pd.Timestamp("2026-01-01 12:01", tz="UTC"))

    assert list(closed["close"]) == [100.0, 101.0]


def test_failed_order_does_not_starve_other_ticker_stops():
    """A rejected order must not skip stop checks for the remaining tickers."""
    import asyncio

    trader = LiveTrader()
    trader.dry_run = False
    trader._save_entries = lambda: None
    trader.entries = {
        "AAA": {"figi": "F1", "size": 10, "direction": "long", "stop": 100.0},
        "BBB": {"figi": "F2", "size": 10, "direction": "long", "stop": 50.0},
    }
    submitted = []

    async def failing_submit(client, account_id, figi, action, size, label):
        submitted.append(figi)
        if figi == "F1":
            raise RuntimeError("Заявка не исполнена полностью: lots=0/10")
        return "order-ok"

    trader._submit = failing_submit
    signals = {
        "AAA": {"action": "hold", "stop": 100.0},
        "BBB": {"action": "hold", "stop": 50.0},
    }
    prices = [{"ticker": "AAA", "price": 95.0}, {"ticker": "BBB", "price": 40.0}]

    asyncio.run(
        trader._act(None, "account", {"AAA": "F1", "BBB": "F2"}, signals, [], prices)
    )

    assert submitted == ["F1", "F2"], "BBB's stop must still be evaluated"
    assert "AAA" in trader.entries, "a failed close must keep the local entry"
    assert "BBB" not in trader.entries, "a filled close must clear the local entry"
