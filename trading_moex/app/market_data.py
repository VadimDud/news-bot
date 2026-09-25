"""Broker-neutral validated market-data ingest for adaptive analytics.

The module deliberately does not import the T-Bank SDK.  An SDK adapter can
translate protobuf messages into these immutable records.  Invalid or stale
events are rejected before persistence; this layer never submits orders.
"""

from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


class MarketDataUnavailable(RuntimeError):
    """Raised when an optional broker market-data stream is not available."""


@dataclass(frozen=True)
class TradeEvent:
    ticker: str
    timestamp: datetime
    price: float
    quantity: float
    aggressor: Literal["BUY", "SELL", "UNKNOWN"]


@dataclass(frozen=True)
class QuoteEvent:
    ticker: str
    timestamp: datetime
    bid: float
    ask: float
    bid_size: float
    ask_size: float


@dataclass(frozen=True)
class BookSnapshot:
    ticker: str
    timestamp: datetime
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class MarketDataAggregate:
    ticker: str
    bar_start: datetime
    bar_end: datetime
    buy_volume: float
    sell_volume: float
    known_volume: float
    delta: float
    coverage: float
    book_imbalance: float | None
    spread_rate: float | None
    latest_event: datetime | None

    @property
    def stale(self) -> bool:
        return self.latest_event is None or self.latest_event < self.bar_end


def _timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("market-data timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def validate_trade(event: TradeEvent) -> TradeEvent:
    if not event.ticker or event.price <= 0 or event.quantity <= 0:
        raise ValueError("trade ticker, price, and quantity must be positive")
    if event.aggressor not in {"BUY", "SELL", "UNKNOWN"}:
        raise ValueError("unknown trade aggressor")
    return TradeEvent(event.ticker.upper(), _timestamp(event.timestamp), event.price, event.quantity, event.aggressor)


def validate_quote(event: QuoteEvent) -> QuoteEvent:
    if not event.ticker or event.bid <= 0 or event.ask <= 0 or event.bid >= event.ask:
        raise ValueError("quote requires 0 < bid < ask")
    if event.bid_size < 0 or event.ask_size < 0:
        raise ValueError("quote sizes cannot be negative")
    return QuoteEvent(event.ticker.upper(), _timestamp(event.timestamp), event.bid, event.ask, event.bid_size, event.ask_size)


def validate_book(event: BookSnapshot, levels: int = 5) -> BookSnapshot:
    if not event.ticker or levels <= 0:
        raise ValueError("book ticker and levels are required")
    bids = tuple(event.bids[:levels])
    asks = tuple(event.asks[:levels])
    if not bids or not asks:
        raise ValueError("book must contain both bids and asks")
    if any(price <= 0 or size < 0 for price, size in (*bids, *asks)):
        raise ValueError("book prices must be positive and sizes nonnegative")
    if bids[0][0] >= asks[0][0]:
        raise ValueError("best bid must be below best ask")
    return BookSnapshot(event.ticker.upper(), _timestamp(event.timestamp), bids, asks)


def ensure_schema(db_path: str | Path) -> None:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS adaptive_trades (
                ticker TEXT NOT NULL, event_ts TEXT NOT NULL, price REAL NOT NULL,
                quantity REAL NOT NULL, aggressor TEXT NOT NULL,
                PRIMARY KEY (ticker, event_ts, price, quantity, aggressor)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS adaptive_books (
                ticker TEXT NOT NULL, event_ts TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (ticker, event_ts)
            )
            """
        )


def persist_events(
    db_path: str | Path,
    *,
    trades: tuple[TradeEvent, ...] = (),
    books: tuple[BookSnapshot, ...] = (),
) -> dict[str, int]:
    """Persist validated events idempotently and return inserted row counts."""
    import json

    valid_trades = [validate_trade(event) for event in trades]
    valid_books = [validate_book(event) for event in books]
    ensure_schema(db_path)
    with sqlite3.connect(Path(db_path).expanduser()) as connection:
        trade_cursor = connection.executemany(
            "INSERT OR IGNORE INTO adaptive_trades VALUES (?, ?, ?, ?, ?)",
            [(event.ticker, event.timestamp.isoformat(), event.price, event.quantity, event.aggressor) for event in valid_trades],
        )
        book_cursor = connection.executemany(
            "INSERT OR IGNORE INTO adaptive_books VALUES (?, ?, ?)",
            [(event.ticker, event.timestamp.isoformat(), json.dumps({"bids": event.bids, "asks": event.asks})) for event in valid_books],
        )
        return {"trades": trade_cursor.rowcount, "books": book_cursor.rowcount}


def stream_status() -> dict[str, object]:
    """Describe optional stream availability without attempting a secret-auth call."""
    try:
        import tinkoff.invest  # type: ignore[import-not-found]
    except ImportError:
        return {"status": "UNAVAILABLE", "reason": "tinkoff SDK is not installed", "orders_enabled": False}
    return {"status": "ADAPTER_REQUIRED", "reason": "SDK adapter has not been configured", "orders_enabled": False}


def aggregate_bar_market_data(
    db_path: str | Path,
    ticker: str,
    bar_start: datetime,
    *,
    bar_seconds: int = 900,
    candle_volume: float | None = None,
) -> MarketDataAggregate:
    """Aggregate validated events in one closed bar; missing feeds remain None/zero."""
    start = _timestamp(bar_start)
    end = start + pd_timedelta_seconds(bar_seconds)
    ensure_schema(db_path)
    with sqlite3.connect(Path(db_path).expanduser()) as connection:
        trades = connection.execute(
            "SELECT event_ts, quantity, aggressor FROM adaptive_trades WHERE ticker = ? AND event_ts >= ? AND event_ts < ?",
            (ticker.upper(), start.isoformat(), end.isoformat()),
        ).fetchall()
        books = connection.execute(
            "SELECT event_ts, payload FROM adaptive_books WHERE ticker = ? AND event_ts >= ? AND event_ts < ? ORDER BY event_ts DESC LIMIT 1",
            (ticker.upper(), start.isoformat(), end.isoformat()),
        ).fetchall()
    buy = sum(float(row[1]) for row in trades if row[2] == "BUY")
    sell = sum(float(row[1]) for row in trades if row[2] == "SELL")
    known = buy + sell
    imbalance = None
    spread = None
    if books:
        payload = json.loads(books[0][1])
        bids = payload["bids"]
        asks = payload["asks"]
        bid_size = sum(float(level[1]) for level in bids)
        ask_size = sum(float(level[1]) for level in asks)
        if bid_size + ask_size > 0:
            imbalance = (bid_size - ask_size) / (bid_size + ask_size)
        bid = float(bids[0][0])
        ask = float(asks[0][0])
        mid = (bid + ask) / 2
        spread = (ask - bid) / mid if mid > 0 else None
    timestamps = [pd_timestamp(row[0]) for row in trades] + [pd_timestamp(row[0]) for row in books]
    latest = max(timestamps) if timestamps else None
    return MarketDataAggregate(
        ticker=ticker.upper(), bar_start=start, bar_end=end, buy_volume=buy,
        sell_volume=sell, known_volume=known, delta=buy - sell,
        coverage=known / candle_volume if candle_volume and candle_volume > 0 else 0.0,
        book_imbalance=imbalance,
        spread_rate=spread, latest_event=latest,
    )


def pd_timedelta_seconds(seconds: int):
    from datetime import timedelta

    if seconds <= 0:
        raise ValueError("bar_seconds must be positive")
    return timedelta(seconds=seconds)


def pd_timestamp(value: str) -> datetime:
    from datetime import datetime

    parsed = datetime.fromisoformat(value)
    return _timestamp(parsed)
