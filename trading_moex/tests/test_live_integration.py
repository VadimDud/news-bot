"""Integration-style tests for the complete live action guard chain."""

from types import SimpleNamespace

import pytest

from app.live import LiveTrader


class _Trader(LiveTrader):
    async def _submit(self, client, account_id, figi, action, size, label):
        self.submitted = (figi, action, size, label)
        return None


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_entry_but_allows_stop_exit():
    trader = _Trader()
    trader.dry_run = True
    trader.entries = {
        "SBER": {
            "figi": "figi",
            "entry_price": 100.0,
            "stop": 95.0,
            "target": 110.0,
            "size": 2,
            "direction": "long",
        }
    }
    trader._circuit["tripped"] = True

    await trader._act(
        SimpleNamespace(),
        "account",
        {"SBER": "figi"},
        {"SBER": {"action": "buy", "stop": 95.0, "target": 110.0}},
        [{"figi": "figi", "quantity": 2, "direction": "long"}],
        [{"ticker": "SBER", "price": 94.0}],
        allow_entries=False,
    )

    assert trader.submitted[1] == "sell"
    assert "SBER" not in trader.entries


@pytest.mark.asyncio
async def test_invalid_price_blocks_entry_without_submitting():
    trader = _Trader()

    await trader._act(
        SimpleNamespace(),
        "account",
        {"SBER": "figi"},
        {"SBER": {"action": "buy", "stop": 95.0, "target": 110.0}},
        [],
        [{"ticker": "SBER", "price": 0.0}],
    )

    assert not hasattr(trader, "submitted")
