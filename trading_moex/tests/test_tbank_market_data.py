from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.tbank_market_data import TBankMarketDataAdapter, map_order_book, map_trade, quote_from_book


def _quotation(value: float) -> SimpleNamespace:
    units = int(value)
    return SimpleNamespace(units=units, nano=int((value - units) * 1_000_000_000))


def test_map_trade_and_order_book_to_validated_events() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trade = map_trade(SimpleNamespace(trade=SimpleNamespace(
        time=timestamp, price=_quotation(100.25), quantity=3, direction="TRADE_DIRECTION_BUY",
    )), "T")
    book = map_order_book(SimpleNamespace(order_book=SimpleNamespace(
        time=timestamp,
        bids=[SimpleNamespace(price=_quotation(100.0), quantity=10)],
        asks=[SimpleNamespace(price=_quotation(100.5), quantity=12)],
    )), "T")
    quote = quote_from_book(book)

    assert trade.aggressor == "BUY"
    assert trade.price == pytest.approx(100.25)
    assert quote.bid == 100.0
    assert quote.ask == 100.5


def test_adapter_reports_unavailable_without_token() -> None:
    adapter = TBankMarketDataAdapter("", {"T": "figi"})

    async def read_first():
        async for event in adapter.events():
            return event
        return None

    assert asyncio.run(read_first()) is None
    assert adapter.status["state"] == "UNAVAILABLE"
    assert adapter.status["orders_enabled"] is False
