"""Tests for Elliott micro-wave signal notifier (synthetic data + isolated DB)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config as trading_config
from app import storage
from app.elliott_candles import Wave, classify_candles, detect_waves, wave_quality_score, fibonacci_levels
from app.elliott_notifier import (
    detect_latest_completed_wave,
    format_elliott_signal,
    run_elliott_scan,
    _scan_ticker,
    _is_stale,
    _plural_candles,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(closes: list[float], opens: list[float] | None = None, dates=None) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame for testing."""
    n = len(closes)
    if opens is None:
        opens = [c - 0.5 for c in closes]
    if dates is None:
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
    highs = [max(o, c) + 0.3 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.3 for o, c in zip(opens, closes)]
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [1000] * n,
    }, index=dates)


def _bear_wave_df(n: int = 5, *, start: float = 100.0, drop: float = 1.5) -> pd.DataFrame:
    closes = [start - drop * (i + 1) for i in range(n)]
    opens = [c + drop for c in closes]
    return _make_df(closes, opens)


def _bull_wave_df(n: int = 5, *, start: float = 100.0, rise: float = 1.5) -> pd.DataFrame:
    closes = [start + rise * (i + 1) for i in range(n)]
    opens = [c - rise for c in closes]
    return _make_df(closes, opens)


def _save_candles(ticker: str, df: pd.DataFrame, period: str = "1day") -> None:
    df_out = df.copy()
    df_out["begin"] = [str(idx.date()) if hasattr(idx, "date") else str(idx) for idx in df_out.index]
    storage.save_candles(ticker, period, df_out)


# ---------------------------------------------------------------------------
# detect_latest_completed_wave
# ---------------------------------------------------------------------------

class TestDetectLatestCompletedWave:
    def test_returns_wave_when_last_candle_completes(self):
        df = _bear_wave_df(5)
        wave = detect_latest_completed_wave(df)
        assert wave is not None
        assert wave.direction == "bear"
        assert wave.candle_count == 5
        assert wave.end_idx == len(df) - 1

    def test_returns_none_when_incomplete(self):
        df = _bear_wave_df(5)
        extra = _make_df([95.0], [95.5], dates=[df.index[-1] + timedelta(days=1)])
        df = pd.concat([df, extra])
        wave = detect_latest_completed_wave(df)
        assert wave is None

    def test_returns_none_for_doji_last(self):
        df = _bear_wave_df(5)
        doji = _make_df([98.0], [98.0], dates=[df.index[-1] + timedelta(days=1)])
        df = pd.concat([df, doji])
        wave = detect_latest_completed_wave(df)
        assert wave is None

    def test_small_wave_not_returned(self):
        df = _bear_wave_df(2)
        wave = detect_latest_completed_wave(df, wave_min=3)
        assert wave is None

    def test_none_when_empty(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        wave = detect_latest_completed_wave(df)
        assert wave is None


# ---------------------------------------------------------------------------
# format_elliott_signal
# ---------------------------------------------------------------------------

class TestFormatElliotSignal:
    def test_buy_signal_content(self):
        df = _bear_wave_df(5, start=100, drop=1.0)
        classified = classify_candles(df, body_ratio_min=0.6, atr_k=0.5)
        waves = detect_waves(classified, wave_min=3, wave_max=5)
        wave = waves[-1]
        quality = wave_quality_score(wave)
        fib = fibonacci_levels(wave)
        msg = format_elliott_signal("SBER", wave, quality, fib, stale=False)
        assert "СИГНАЛ ПОКУПКА" in msg
        assert "SBER" in msg
        assert "Медвежья волна" in msg
        assert "Качество волны" in msg
        assert "от экстремума" in msg
        assert "мартингейл" in msg.lower()

    def test_sell_signal_content(self):
        df = _bull_wave_df(5, start=100, rise=1.0)
        classified = classify_candles(df, body_ratio_min=0.6, atr_k=0.5)
        waves = detect_waves(classified, wave_min=3, wave_max=5)
        wave = waves[-1]
        quality = wave_quality_score(wave)
        fib = fibonacci_levels(wave)
        msg = format_elliott_signal("LKOH", wave, quality, fib, stale=False)
        assert "СИГНАЛ ПРОДАЖА" in msg
        assert "Бычья волна" in msg

    def test_stale_warning(self):
        df = _bear_wave_df(5, start=100, drop=1.0)
        classified = classify_candles(df, body_ratio_min=0.6, atr_k=0.5)
        waves = detect_waves(classified, wave_min=3, wave_max=5)
        wave = waves[-1]
        quality = wave_quality_score(wave)
        fib = fibonacci_levels(wave)
        msg = format_elliott_signal("SBER", wave, quality, fib, stale=True)
        assert "устарели" in msg.lower()


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

class TestElliottStorage:
    def test_get_returns_empty(self):
        result = storage.get_elliott_signal("TEST")
        assert result["wave_end"] is None
        assert result["direction"] is None

    def test_save_and_get(self):
        storage.save_elliott_signal("TEST", "2024-06-15", "bear", 0.65)
        result = storage.get_elliott_signal("TEST")
        assert result["wave_end"] == "2024-06-15"
        assert result["direction"] == "bear"
        assert result["quality"] == 0.65
        assert result["notified_at"] is not None

    def test_upsert(self):
        storage.save_elliott_signal("TEST", "2024-06-15", "bear", 0.65)
        storage.save_elliott_signal("TEST", "2024-06-20", "bull", 0.80)
        result = storage.get_elliott_signal("TEST")
        assert result["wave_end"] == "2024-06-20"
        assert result["direction"] == "bull"
        assert result["quality"] == 0.80


# ---------------------------------------------------------------------------
# _scan_ticker (integration-ish: DB + detection + dedup)
# ---------------------------------------------------------------------------

class TestScanTicker:
    async def test_returns_none_when_no_candles(self):
        result = await _scan_ticker("NODATA")
        assert result is None

    async def test_detects_and_sends_first_signal(self, monkeypatch):
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.0)
        df = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TEST", df)

        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TEST")
            assert result is not None
            assert result["sent"] is True
            assert result["direction"] == "bear"
            mock_send.assert_called_once()

    async def test_dedup_same_wave_not_sent(self, monkeypatch):
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.0)
        df = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TEST", df)

        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            await _scan_ticker("TEST")
            assert mock_send.call_count == 1

            await _scan_ticker("TEST")
            assert mock_send.call_count == 1

    async def test_new_wave_sent_after_old(self, monkeypatch):
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.0)
        df1 = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TEST", df1)
        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            await _scan_ticker("TEST")
            assert mock_send.call_count == 1

        bull_dates = pd.date_range(df1.index[-1] + timedelta(days=1), periods=3, freq="B")
        new_bull = _bull_wave_df(3, start=float(df1["close"].iloc[-1]), rise=0.5)
        new_bull.index = bull_dates
        _save_candles("TEST", new_bull)

        df_full = pd.concat([df1, new_bull])
        with patch("app.elliott_notifier._load_daily_candles", return_value=df_full), \
             patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            await _scan_ticker("TEST")
            assert mock_send.call_count == 1


# ---------------------------------------------------------------------------
# _is_stale
# ---------------------------------------------------------------------------

class TestIsStale:
    def test_fresh_data(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        df = pd.DataFrame({"open": [1]*20, "high": [1]*20, "low": [1]*20, "close": [1]*20, "volume": [1]*20}, index=dates)
        with patch("app.elliott_notifier.trading_config") as mock_cfg:
            mock_cfg.TRADER_SIGNALS_MAX_STALE_DAYS = 1000
            assert _is_stale(df) is False

    def test_old_data(self):
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        df = pd.DataFrame({"open": [1]*5, "high": [1]*5, "low": [1]*5, "close": [1]*5, "volume": [1]*5}, index=dates)
        with patch("app.elliott_notifier.trading_config") as mock_cfg:
            mock_cfg.TRADER_SIGNALS_MAX_STALE_DAYS = 1
            assert _is_stale(df) is True

    def test_empty_is_stale(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        assert _is_stale(df) is True


# ---------------------------------------------------------------------------
# run_elliott_scan (integration: full loop with mocked TG)
# ---------------------------------------------------------------------------

class TestRunElliotScan:
    async def test_scan_empty_watchlist_and_env(self, monkeypatch):
        storage.set_watchlist([])
        monkeypatch.setattr(trading_config, "WATCH_TICKERS", [])
        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock) as mock_send:
            result = await run_elliott_scan()
            assert result == []
            mock_send.assert_not_called()

    async def test_scan_with_candles(self, monkeypatch):
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.0)
        storage.set_watchlist(["TEST"])
        df = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TEST", df)

        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await run_elliott_scan()
            assert len(result) == 1
            assert result[0]["ticker"] == "TEST"
            assert result[0]["sent"] is True

    async def test_scan_graceful_on_error(self):
        storage.set_watchlist(["TEST"])
        result = await run_elliott_scan()
        assert result == []


# ---------------------------------------------------------------------------
# Quality filter (TRADER_ELLIOTT_MIN_QUALITY)
# ---------------------------------------------------------------------------

class TestQualityFilter:
    async def test_low_quality_blocked(self, monkeypatch):
        """Плоская волна (q≈0.05) ниже порога 0.4: без отправки и без записи в дедуп."""
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.4)
        df = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TESTQ", df)

        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TESTQ")
            assert result is None
            mock_send.assert_not_called()
            # в дедуп ничего не записано — будущий порог не заблокирован навсегда
            assert storage.get_elliott_signal("TESTQ")["wave_end"] is None

    async def test_same_wave_passes_with_zero_threshold(self, monkeypatch):
        monkeypatch.setattr(trading_config, "TRADER_ELLIOTT_MIN_QUALITY", 0.0)
        df = _bear_wave_df(5, start=100, drop=1.0)
        _save_candles("TESTQ0", df)

        with patch("app.elliott_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TESTQ0")
            assert result is not None
            assert result["sent"] is True
            mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# Fibonacci anchoring on wave extreme
# ---------------------------------------------------------------------------

class TestFibAnchor:
    async def test_bear_targets_from_low(self):
        opens = [104.0, 103.0, 102.0, 101.0, 100.0]
        closes = [o - 1.0 for o in opens]
        df = _make_df(closes, opens)
        wave = detect_waves(classify_candles(df), 3, 5)[-1]
        quality = wave_quality_score(wave)
        fib = fibonacci_levels(wave)

        anchor = float(min(df["low"]))   # 98.70
        total = 104.0 - anchor           # 5.30
        expected = {
            "38.2%": anchor + total * 0.382,
            "50.0%": anchor + total * 0.5,
            "61.8%": anchor + total * 0.618,
        }
        msg = format_elliott_signal("SBER", wave, quality, fib, stale=False)

        assert f"от экстремума волны ({anchor:.2f} ₽)" in msg
        for lvl, price in expected.items():
            assert f"{lvl}: {price:.2f} ₽" in msg

    async def test_bull_targets_from_high(self):
        opens = [97.0, 98.0, 99.0, 100.0, 101.0]
        closes = [o + 1.0 for o in opens]
        df = _make_df(closes, opens)
        wave = detect_waves(classify_candles(df), 3, 5)[-1]
        quality = wave_quality_score(wave)
        fib = fibonacci_levels(wave)

        anchor = float(max(df["high"]))  # 102 + 0.3 = 102.30
        total = anchor - 97.0            # 5.30
        expected_618 = anchor - total * 0.618

        msg = format_elliott_signal("LKOH", wave, quality, fib, stale=False)
        assert "СИГНАЛ ПРОДАЖА" in msg
        assert f"от экстремума волны ({anchor:.2f} ₽)" in msg
        assert f"61.8%: {expected_618:.2f} ₽" in msg


# ---------------------------------------------------------------------------
# Plural forms
# ---------------------------------------------------------------------------

class TestPluralCandles:
    def test_forms(self):
        assert _plural_candles(1) == "свеча"
        assert _plural_candles(3) == "свечи"
        assert _plural_candles(4) == "свечи"
        assert _plural_candles(5) == "свечей"
        assert _plural_candles(11) == "свечей"
        assert _plural_candles(21) == "свеча"


# ---------------------------------------------------------------------------
# Watchlist fallback (DB → WATCH_TICKERS)
# ---------------------------------------------------------------------------

class TestWatchlistFallback:
    async def test_empty_db_falls_back_to_env(self, monkeypatch):
        storage.set_watchlist([])
        monkeypatch.setattr(trading_config, "WATCH_TICKERS", ["ENVTK"])

        called: list[str] = []

        async def fake_scan(ticker):
            called.append(ticker)
            return None

        with patch("app.elliott_notifier._scan_ticker", side_effect=fake_scan):
            await run_elliott_scan()

        assert called == ["ENVTK"]

    async def test_db_watchlist_preferred_over_env(self, monkeypatch):
        storage.set_watchlist(["DBT"])
        monkeypatch.setattr(trading_config, "WATCH_TICKERS", ["ENVTK"])

        called: list[str] = []

        async def fake_scan(ticker):
            called.append(ticker)
            return None

        with patch("app.elliott_notifier._scan_ticker", side_effect=fake_scan):
            await run_elliott_scan()

        assert called == ["DBT"]
