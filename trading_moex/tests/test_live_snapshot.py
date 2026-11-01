"""Regression tests for live dashboard snapshot consistency."""

from app.live import LiveTrader


def test_snapshot_reflects_strategy_change():
    trader = LiveTrader()

    trader.set_strategy("rsi")

    snapshot = trader.snapshot()
    assert snapshot["strategy"] == "rsi"
    assert snapshot["entries"] == {}


def test_snapshot_reflects_mode_change():
    trader = LiveTrader()
    target = not trader.dry_run

    trader.set_dry_run(target)

    assert trader.snapshot()["dry_run"] is target
