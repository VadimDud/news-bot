"""Tests for confirmation of broker order execution."""

from types import SimpleNamespace

import pytest

from app.live import LiveTrader


class _Orders:
    def __init__(self, status, lots_executed):
        self.status = status
        self.lots_executed = lots_executed

    async def post_order(self, **kwargs):
        return SimpleNamespace(order_id="order-1")

    async def get_order_state(self, **kwargs):
        return SimpleNamespace(
            execution_report_status=self.status,
            lots_executed=self.lots_executed,
        )


class _EventuallyFilledOrders(_Orders):
    def __init__(self):
        super().__init__("EXECUTION_REPORT_STATUS_EXECUTION_STARTED", 0)
        self.calls = 0

    async def get_order_state(self, **kwargs):
        self.calls += 1
        if self.calls >= 2:
            return SimpleNamespace(
                execution_report_status="EXECUTION_REPORT_STATUS_EXECUTION_COMPLETE",
                lots_executed=3,
            )
        return SimpleNamespace(
            execution_report_status="EXECUTION_REPORT_STATUS_EXECUTION_STARTED",
            lots_executed=0,
        )


class _Client:
    def __init__(self, status, lots_executed):
        self.orders = _Orders(status, lots_executed)


async def _fake_post_market_order(client, account_id, figi, quantity, action):
    return await client.orders.post_order(
        account_id=account_id, instrument_id=figi, quantity=quantity, action=action
    )


@pytest.mark.asyncio
async def test_submit_accepts_fully_filled_order():
    trader = LiveTrader()
    trader.dry_run = False
    trader._post_market_order = _fake_post_market_order

    order_id = await trader._submit(
        _Client("EXECUTION_REPORT_STATUS_EXECUTION_COMPLETE", 3),
        "account",
        "figi",
        "buy",
        3,
        "BUY SBER x3",
    )

    assert order_id == "order-1"


@pytest.mark.asyncio
async def test_submit_polls_until_order_is_filled():
    trader = LiveTrader()
    trader.dry_run = False
    trader._post_market_order = _fake_post_market_order
    client = _Client("EXECUTION_REPORT_STATUS_EXECUTION_COMPLETE", 3)
    client.orders = _EventuallyFilledOrders()

    order_id = await trader._submit(client, "account", "figi", "buy", 3, "BUY SBER x3")

    assert order_id == "order-1"
    assert client.orders.calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "lots"),
    [
        ("EXECUTION_REPORT_STATUS_EXECUTION_REJECTED", 0),
        ("EXECUTION_REPORT_STATUS_EXECUTION_STARTED", 3),
        ("EXECUTION_REPORT_STATUS_EXECUTION_COMPLETE", 1),
    ],
)
async def test_submit_rejects_unfinished_or_partial_order(monkeypatch, status, lots):
    trader = LiveTrader()
    trader.dry_run = False
    trader._post_market_order = _fake_post_market_order
    monkeypatch.setattr("app.live._ORDER_CONFIRM_DELAY", 0)

    with pytest.raises(RuntimeError, match="не исполнена полностью"):
        await trader._submit(
            _Client(status, lots), "account", "figi", "buy", 3, "BUY SBER x3"
        )
