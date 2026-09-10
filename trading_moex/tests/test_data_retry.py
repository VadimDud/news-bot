"""Tests for MOEX data fetch retry logic (transient network failures)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import data  # noqa: E402


def _mk_batch(n=3):
    return pd.DataFrame({
        "begin": pd.date_range("2026-01-01", periods=n, freq="D"),
        "open": [1.0] * n, "close": [1.0] * n,
        "high": [1.0] * n, "low": [1.0] * n,
        "value": [1.0] * n, "volume": [1.0] * n,
    })


def test_retry_succeeds_after_transient_reset(monkeypatch):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionResetError(104, "Connection reset by peer")
        return _mk_batch()

    ticker_obj = MagicMock()
    ticker_obj.candles.side_effect = flaky

    monkeypatch.setattr(data, "MOEX_FETCH_BACKOFF_SEC", 0.0)  # без задержек в тесте
    out = data._fetch_batch_with_retry(
        ticker_obj, "SBER", "1D", pd.Timestamp("2026-01-01").date(),
        pd.Timestamp("2026-01-05").date(), 0,
    )
    assert out is not None and len(out) == 3
    assert calls["n"] == 2


def test_retry_returns_none_after_all_fail(monkeypatch):
    ticker_obj = MagicMock()
    ticker_obj.candles.side_effect = ConnectionResetError(104, "Connection reset by peer")

    monkeypatch.setattr(data, "MOEX_FETCH_BACKOFF_SEC", 0.0)
    out = data._fetch_batch_with_retry(
        ticker_obj, "SBER", "1D", pd.Timestamp("2026-01-01").date(),
        pd.Timestamp("2026-01-05").date(), 0,
    )
    assert out is None
    assert ticker_obj.candles.call_count == data.MOEX_FETCH_RETRIES


def test_fetch_raw_returns_partial_on_batch_failure(monkeypatch):
    """Первый батч ок, второй — окончательно падает: возвращаем частичные данные."""
    import moexalgo

    ticker_obj = MagicMock()
    full = _mk_batch(data._MAX_BATCH)  # полный батч → цикл запросит следующий

    def side(*a, **k):
        # первый offset=0 отдаёт полный батч, последующие offset>0 падают
        if k.get("offset", 0) == 0:
            return full
        raise ConnectionResetError(104, "reset")

    ticker_obj.candles.side_effect = side

    monkeypatch.setattr(moexalgo, "Ticker", lambda t: ticker_obj)
    monkeypatch.setattr(data, "MOEX_FETCH_BACKOFF_SEC", 0.0)

    rows = data._fetch_raw("SBER", "1D", pd.Timestamp("2026-01-01").date(),
                           pd.Timestamp("2026-01-05").date())
    assert len(rows) == data._MAX_BATCH
