"""Tests for MTF Confirmation signal notifier (synthetic data + isolated DB)."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import storage  # noqa: E402
from app.mtf_notifier import (  # noqa: E402
    format_mtf_signal,
    run_mtf_scan,
    _scan_ticker,
    _watchlist,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_4h_closes(closes, freq="4h", start="2025-07-28 04:00"):
    n = len(closes)
    close = np.array(closes, dtype=float)
    opens = np.append(close[0], close[:-1])
    highs = np.maximum(opens, close) + 0.5
    lows = np.minimum(opens, close) - 0.5
    idx = pd.date_range(start, periods=n, freq=freq, tz=timezone.utc)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": close,
        "volume": [10000] * n,
    }, index=idx)


def _make_daily_closes(closes, start="2024-01-01"):
    n = len(closes)
    close = np.array(closes, dtype=float)
    opens = np.append(close[0], close[:-1])
    highs = np.maximum(opens, close) + 1.0
    lows = np.minimum(opens, close) - 1.0
    idx = pd.date_range(start, periods=n, freq="1D", tz=timezone.utc)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": close,
        "volume": [50000] * n,
    }, index=idx)


def _save_candles(ticker, df, period):
    out = df.copy()
    out["begin"] = [str(idx) for idx in out.index]
    storage.save_candles(ticker, period, out)


# ---------------------------------------------------------------------------
# format_mtf_signal
# ---------------------------------------------------------------------------

class TestFormat:
    def test_bull_message(self):
        msg = format_mtf_signal("LKOH", "bull", 6500.0, 1,
                                datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc))
        assert "ЛОНГ" in msg
        assert "LKOH" in msg
        assert "6500.00" in msg
        assert "БЫЧИЙ" in msg
        assert "не является" in msg.lower() or "не является" in msg

    def test_bear_message(self):
        msg = format_mtf_signal("GAZP", "bear", 145.5, -1,
                                datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc))
        assert "ШОРТ" in msg
        assert "GAZP" in msg
        assert "145.50" in msg
        assert "МЕДВЕЖЬИЙ" in msg


# ---------------------------------------------------------------------------
# Storage roundtrip
# ---------------------------------------------------------------------------

class TestStorage:
    def test_get_initial_none(self):
        result = storage.get_mtf_signal("TICK")
        assert result["signal_ts"] is None
        assert result["side"] is None

    def test_save_and_get(self):
        storage.save_mtf_signal("TEST", "2026-03-15T08:00:00+00:00", "bear", 123.45)
        result = storage.get_mtf_signal("TEST")
        assert result["signal_ts"] == "2026-03-15T08:00:00+00:00"
        assert result["side"] == "bear"
        assert result["close_price"] == 123.45

    def test_insert_or_ignore(self):
        storage.save_mtf_signal("T2", "2026-03-15T08:00:00+00:00", "bull", 100.0)
        storage.save_mtf_signal("T2", "2026-03-15T08:00:00+00:00", "bull", 999.0)
        result = storage.get_mtf_signal("T2")
        assert result["close_price"] == 100.0


# ---------------------------------------------------------------------------
# _watchlist
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_returns_config_tickers(self, monkeypatch):
        monkeypatch.setattr("app.mtf_notifier.trading_config", type("C", (), {
            "TRADER_MTF_TICKERS": ["AAA", "BBB"]
        })())
        assert _watchlist() == ["AAA", "BBB"]


# ---------------------------------------------------------------------------
# _scan_ticker: hour filter + dedup + end-to-end
# ---------------------------------------------------------------------------

class TestScanTicker:
    def _hour_dt(self, year=2026, month=3, day=15, hour=8):
        return datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_no_signal_when_bar_hour_not_allowed(self):
        """Бар с hour=16 (19:00 MSK) не отправляется."""
        # 4h-данные: 50+ баров, финальный на 16 UTC — zone_break bear на фоне downtrend
        closes_4h = list(np.linspace(200, 100, 70))
        closes_daily = list(np.linspace(220, 100, 200))

        ltf = _make_4h_closes(closes_4h)
        htf = _make_daily_closes(closes_daily)

        _save_candles("TEST", ltf, "4h")
        _save_candles("TEST", htf, "1day")

        with patch("app.mtf_notifier.trading_config") as mc:
            mc.TRADER_MTF_SIGNAL_HOURS = [4, 8, 12]
            with patch("app.mtf_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
                # Override ltf to end at 16 UTC bar
                ltf_16 = ltf.copy()
                # Rename last bar to 16 UTC
                ltf_16.index = ltf_16.index[:-1].append(
                    pd.DatetimeIndex([pd.Timestamp("2026-03-15 16:00", tzinfo=timezone.utc)])
                )
                with patch("app.mtf_notifier._load_candles") as mock_load:
                    def _load(ticker, period):
                        if period == "4h":
                            return ltf_16
                        return htf
                    mock_load.side_effect = _load
                    result = await _scan_ticker("TEST")
                    assert result is None
                    mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dedup_same_signal_not_resend(self):
        """Тот же сигнал (ts + side) не отправляется повторно."""
        closes_4h = list(np.linspace(200, 100, 70))
        closes_daily = list(np.linspace(220, 100, 200))

        ltf = _make_4h_closes(closes_4h)
        htf = _make_daily_closes(closes_daily)
        _save_candles("DEDUP", ltf, "4h")
        _save_candles("DEDUP", htf, "1day")

        signal_ts = "2026-03-15T08:00:00+00:00"
        storage.save_mtf_signal("DEDUP", signal_ts, "bear", 100.0)

        with patch("app.mtf_notifier.trading_config") as mc:
            mc.TRADER_MTF_SIGNAL_HOURS = [4, 8, 12]
            with patch("app.mtf_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
                with patch("app.mtf_notifier._load_candles") as mock_load:
                    def _load(ticker, period):
                        if period == "4h":
                            # Force last bar to match saved signal_ts
                            ltf2 = ltf.copy()
                            ltf2.index = ltf2.index[:-1].append(
                                pd.DatetimeIndex([pd.Timestamp(signal_ts)])
                            )
                            return ltf2
                        return htf
                    mock_load.side_effect = _load
                    result = await _scan_ticker("DEDUP")
                    assert result is None
                    mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# run_mtf_scan: full integration
# ---------------------------------------------------------------------------

class TestRunMtfScan:
    @pytest.mark.asyncio
    async def test_empty_watchlist(self, monkeypatch):
        monkeypatch.setattr("app.mtf_notifier.trading_config", type("C", (), {
            "TRADER_MTF_TICKERS": [],
        })())
        with patch("app.mtf_notifier._send_tg", new_callable=AsyncMock) as mock_send:
            assert await run_mtf_scan() == []
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_scan_graceful_on_missing_data(self, monkeypatch):
        monkeypatch.setattr("app.mtf_notifier.trading_config", type("C", (), {
            "TRADER_MTF_TICKERS": ["NODATA"],
        })())
        result = await run_mtf_scan()
        assert result == []
