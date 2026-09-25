from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.market_data import (
    BookSnapshot,
    QuoteEvent,
    TradeEvent,
    persist_events,
    stream_status,
    validate_book,
    validate_quote,
    validate_trade,
    aggregate_bar_market_data,
)


def test_trade_quote_and_book_validation() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trade = validate_trade(TradeEvent("t", timestamp, 100, 2, "BUY"))
    quote = validate_quote(QuoteEvent("t", timestamp, 99, 101, 10, 12))
    book = validate_book(BookSnapshot("t", timestamp, ((99, 10),), ((101, 12),)))

    assert trade.ticker == "T"
    assert quote.bid < quote.ask
    assert book.bids[0][0] < book.asks[0][0]


def test_invalid_market_data_is_rejected() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        validate_trade(TradeEvent("T", timestamp, 0, 1, "BUY"))
    with pytest.raises(ValueError):
        validate_quote(QuoteEvent("T", timestamp, 101, 100, 1, 1))
    with pytest.raises(ValueError):
        validate_book(BookSnapshot("T", timestamp, ((101, 1),), ((100, 1),)))


def test_events_persist_idempotently(tmp_path) -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trade = TradeEvent("T", timestamp, 100, 2, "BUY")
    book = BookSnapshot("T", timestamp, ((99, 10),), ((101, 12),))
    path = tmp_path / "market.db"

    assert persist_events(path, trades=(trade,), books=(book,)) == {"trades": 1, "books": 1}
    assert persist_events(path, trades=(trade,), books=(book,)) == {"trades": 0, "books": 0}


def test_stream_status_is_explicit_when_sdk_missing() -> None:
    status = stream_status()

    assert status["status"] in {"UNAVAILABLE", "ADAPTER_REQUIRED"}
    assert status["orders_enabled"] is False


def test_bar_aggregate_keeps_missing_feed_explicit(tmp_path) -> None:
    from datetime import timedelta

    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    trade = TradeEvent("T", timestamp + timedelta(minutes=1), 100, 2, "BUY")
    persist_events(tmp_path / "data.db", trades=(trade,))
    aggregate = aggregate_bar_market_data(tmp_path / "data.db", "T", timestamp, candle_volume=10)

    assert aggregate.delta == 2
    assert aggregate.coverage == pytest.approx(0.2)
    assert aggregate.book_imbalance is None
