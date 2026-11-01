from datetime import datetime, timezone

import pandas as pd

from app.timezones import (
    MARKET_OFFSET_HOURS,
    MARKET_TZ_NAME,
    as_utc,
    as_utc_index,
    as_utc_naive_index,
    to_market,
)


def test_market_timezone_contract_is_moscow_utc_plus_three():
    assert MARKET_TZ_NAME == "Europe/Moscow"
    assert MARKET_OFFSET_HOURS == 3
    assert to_market(datetime(2026, 1, 1, 7, tzinfo=timezone.utc)).hour == 10


def test_naive_storage_timestamp_is_interpreted_as_utc():
    converted = as_utc(datetime(2026, 1, 1, 7))
    assert converted.tzinfo == timezone.utc
    assert converted.hour == 7


def test_timestamp_indexes_normalize_aware_and_naive_values_to_utc():
    values = ["2026-01-01T07:00:00", "2026-01-01T11:00:00+04:00"]
    aware = as_utc_index(values)
    naive = as_utc_naive_index(values)
    assert list(aware) == [pd.Timestamp("2026-01-01T07:00:00Z")] * 2
    assert naive.tz is None
    assert list(naive) == [pd.Timestamp("2026-01-01 07:00:00")] * 2
