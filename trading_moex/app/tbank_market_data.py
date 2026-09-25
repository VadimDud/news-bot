"""Read-only T-Bank market-data stream adapter.

The SDK is installed only in the trading Docker image.  Imports are lazy and
protobuf objects are mapped by attributes so SDK releases can be tested
without coupling the analytics layer to generated classes.  This adapter has
no order/execution code by design.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from .market_data import (
    BookSnapshot,
    QuoteEvent,
    TradeEvent,
    persist_events,
    validate_book,
    validate_quote,
    validate_trade,
)

logger = logging.getLogger(__name__)


def _quotation(value) -> float:
    if value is None:
        raise ValueError("missing quotation")
    return float(getattr(value, "units", 0)) + float(getattr(value, "nano", 0)) / 1_000_000_000


def _timestamp(value) -> datetime:
    if value is None:
        raise ValueError("missing market-data timestamp")
    if isinstance(value, datetime):
        result = value
    elif hasattr(value, "ToDatetime"):
        result = value.ToDatetime()
    else:
        raise ValueError("unsupported market-data timestamp")
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _enum_name(value) -> str:
    return str(getattr(value, "name", value)).upper()


def map_trade(message, ticker: str) -> TradeEvent:
    """Map a T-Bank Trade protobuf-like object to a validated event."""
    trade = getattr(message, "trade", message)
    direction = _enum_name(getattr(trade, "direction", "UNKNOWN"))
    aggressor = "BUY" if "BUY" in direction else "SELL" if "SELL" in direction else "UNKNOWN"
    return validate_trade(TradeEvent(
        ticker=ticker,
        timestamp=_timestamp(getattr(trade, "time", None)),
        price=_quotation(getattr(trade, "price", None)),
        quantity=float(getattr(trade, "quantity", 0)),
        aggressor=aggressor,
    ))


def _book_levels(levels) -> tuple[tuple[float, float], ...]:
    return tuple((_quotation(getattr(level, "price", None)), float(getattr(level, "quantity", 0))) for level in levels)


def map_order_book(message, ticker: str, levels: int = 5) -> BookSnapshot:
    """Map a T-Bank OrderBook protobuf-like object to a validated snapshot."""
    book = getattr(message, "order_book", message)
    return validate_book(BookSnapshot(
        ticker=ticker,
        timestamp=_timestamp(getattr(book, "time", None)),
        bids=_book_levels(getattr(book, "bids", ()))[:levels],
        asks=_book_levels(getattr(book, "asks", ()))[:levels],
    ), levels=levels)


def quote_from_book(book: BookSnapshot) -> QuoteEvent:
    """Build a top-of-book quote from a validated L2 snapshot."""
    bid, bid_size = book.bids[0]
    ask, ask_size = book.asks[0]
    return validate_quote(QuoteEvent(book.ticker, book.timestamp, bid, ask, bid_size, ask_size))


class TBankMarketDataAdapter:
    """Reconnectable, read-only stream facade for trades and order books."""

    def __init__(self, token: str, subscriptions: dict[str, str], *, reconnect_delay: float = 5.0) -> None:
        self._token = token
        self._subscriptions = dict(subscriptions)  # ticker -> FIGI
        self._reconnect_delay = max(1.0, reconnect_delay)
        self.status: dict[str, object] = {
            "state": "CREATED", "orders_enabled": False, "last_error": None,
        }

    async def events(self) -> AsyncIterator[TradeEvent | BookSnapshot]:
        """Yield validated events; retry transient stream failures with backoff."""
        if not self._token:
            self.status.update(state="UNAVAILABLE", last_error="T-Bank token is not configured")
            return
        try:
            from tinkoff.invest import AsyncClient  # type: ignore[import-not-found]
        except ImportError:
            self.status.update(state="UNAVAILABLE", last_error="tinkoff SDK is not installed")
            return
        self.status.update(state="CONNECTING")
        while True:
            try:
                async with AsyncClient(token=self._token, app_name="moex-adaptive-readonly") as client:
                    stream = client.market_data_stream.market_data_stream()
                    await self._subscribe(stream)
                    self.status.update(state="STREAMING", last_error=None)
                    async for message in stream:
                        event = self._map_message(message)
                        if event is not None:
                            yield event
            except asyncio.CancelledError:
                self.status.update(state="STOPPED")
                raise
            except Exception as exc:  # noqa: BLE001
                self.status.update(state="RECONNECTING", last_error=str(exc))
                logger.warning("T-Bank market-data stream failed: %s", exc)
                await asyncio.sleep(self._reconnect_delay)

    async def _subscribe(self, stream) -> None:
        from tinkoff.invest import (  # type: ignore[import-not-found]
            MarketDataRequest,
            SubscribeOrderBookRequest,
            SubscribeTradesRequest,
            SubscriptionAction,
            TradeSubscription,
            OrderBookSubscription,
        )

        figis = list(self._subscriptions.values())
        request = MarketDataRequest(
            subscribe_trades_request=SubscribeTradesRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                instruments=[TradeSubscription(figi=figi) for figi in figis],
            ),
            subscribe_order_book_request=SubscribeOrderBookRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                instruments=[OrderBookSubscription(figi=figi, depth=5) for figi in figis],
            ),
        )
        await stream.send(request)

    def _map_message(self, message):
        figi = getattr(message, "figi", None)
        if not figi:
            for field in ("trade", "order_book"):
                nested = getattr(message, field, None)
                figi = getattr(nested, "figi", None) if nested else None
                if figi:
                    break
        ticker = next((key for key, value in self._subscriptions.items() if value == figi), None)
        if not ticker:
            return None
        if getattr(message, "trade", None) is not None:
            return map_trade(message, ticker)
        if getattr(message, "order_book", None) is not None:
            return map_order_book(message, ticker)
        return None


async def stream_to_storage(
    adapter: TBankMarketDataAdapter,
    db_path: str,
    *,
    batch_size: int = 100,
    flush_seconds: float = 5.0,
) -> None:
    """Persist read-only stream events in bounded batches until cancelled."""
    if batch_size <= 0 or flush_seconds <= 0:
        raise ValueError("batch_size and flush_seconds must be positive")
    trades: list[TradeEvent] = []
    books: list[BookSnapshot] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + flush_seconds

    async def flush() -> None:
        nonlocal deadline
        if trades or books:
            persist_events(db_path, trades=tuple(trades), books=tuple(books))
            trades.clear()
            books.clear()
        deadline = loop.time() + flush_seconds

    try:
        async for event in adapter.events():
            if isinstance(event, TradeEvent):
                trades.append(event)
            elif isinstance(event, BookSnapshot):
                books.append(event)
            if len(trades) + len(books) >= batch_size or loop.time() >= deadline:
                await asyncio.to_thread(persist_events, db_path, trades=tuple(trades), books=tuple(books))
                trades.clear()
                books.clear()
                deadline = loop.time() + flush_seconds
    finally:
        if trades or books:
            await asyncio.to_thread(persist_events, db_path, trades=tuple(trades), books=tuple(books))
