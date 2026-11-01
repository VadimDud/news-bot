"""Project-wide time contract.

Market data is stored as UTC-naive timestamps in SQLite. User-facing times and
market session logic use Europe/Moscow (UTC+3, no DST for current data).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd


UTC = timezone.utc
MARKET_TZ_NAME = "Europe/Moscow"
MARKET_TZ = ZoneInfo(MARKET_TZ_NAME)
MARKET_OFFSET_HOURS = 3


def as_utc(value: datetime) -> datetime:
    """Interpret naive timestamps as UTC and return an aware UTC value."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_market(value: datetime) -> datetime:
    """Convert a timestamp to the configured Moscow market timezone."""
    return as_utc(value).astimezone(MARKET_TZ)


def as_utc_index(values, *, errors: str = "raise") -> pd.DatetimeIndex:
    """Return a pandas index explicitly normalized to UTC."""
    index = pd.DatetimeIndex(
        pd.to_datetime(values, errors=errors, utc=True, format="mixed")
    )
    return index.tz_convert(UTC)


def as_utc_naive_index(values, *, errors: str = "raise") -> pd.DatetimeIndex:
    """Return UTC timestamps without tzinfo for legacy SQLite/Backtrader APIs."""
    return as_utc_index(values, errors=errors).tz_localize(None)
