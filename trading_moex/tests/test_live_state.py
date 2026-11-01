"""Persistence tests for live settings and open positions."""

from app import settings
from app.live import LiveTrader


def test_live_entries_round_trip():
    entries = {
        "SBER": {
            "figi": "figi-sber",
            "entry_price": 250.1,
            "stop": 245.0,
            "target": 260.3,
            "size": 10,
            "direction": "long",
            "order_id": "order-123",
        }
    }

    settings.save_live_entries(entries)

    assert settings.load_live_entries() == entries


def test_invalid_live_entries_are_ignored():
    from app import storage

    storage.set_setting("live_entries", "not-json")
    assert settings.load_live_entries() == {}


def test_live_trader_restores_entries_after_restart():
    entries = {
        "LKOH": {
            "figi": "figi-lkoh",
            "entry_price": 7000.0,
            "stop": 6800.0,
            "target": 7400.0,
            "size": 2,
            "direction": "long",
            "order_id": "order-456",
        }
    }
    settings.save_live_entries(entries)

    restarted = LiveTrader()

    assert restarted.entries == entries
