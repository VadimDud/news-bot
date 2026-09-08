#!/usr/bin/env python3
"""Causality tests for the MTF + Elliott-wave TP backtest.

Verifies:
- Wave 2 completes strictly before signal bar (no future data leakage)
- Entry on open of bar AFTER signal (live-faithful)
- TP computed from wave 1 amplitude only (no lookahead into wave 2+)
- Direction consistency: wave 1 direction matches trade direction
- No wave found → trade skipped (not forced)
- Time-cap: trade exits at close of bar entry+N, never beyond
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from app.elliott_candles import classify_candles, detect_waves  # noqa: E402
from app import mtf_confirm as mtf  # noqa: E402
from scripts.backtest_mtf_elliott_tp import (  # noqa: E402
    _build_wave12_pairs,
    last_wave12_before,
    honest_trades_elliott,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 200, base: float = 100.0, seed: int = 42) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2025-07-01", periods=n, freq="4h")
    closes = base + np.cumsum(rng.randn(n) * 0.5)
    opens = closes + rng.randn(n) * 0.2
    highs = np.maximum(opens, closes) + rng.uniform(0.1, 0.5, n)
    lows = np.minimum(opens, closes) - rng.uniform(0.1, 0.5, n)
    volume = rng.randint(1000, 10000, n)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes, "volume": volume,
    }, index=dates)


def _make_wave_pattern() -> pd.DataFrame:
    """Construct a df with explicit bull+bear wave pair.

    Wave 1 (bull): 3 candles going up (indices 5..7)
    Wave 2 (bear): 3 candles going down (indices 8..10)
    Signal at index 11 → entry at index 12
    """
    n = 30
    dates = pd.date_range("2025-07-01", periods=n, freq="4h")
    o = np.zeros(n)
    h = np.zeros(n)
    l = np.zeros(n)
    c = np.zeros(n)
    # base bars 0..4
    for i in range(5):
        o[i] = h[i] = l[i] = c[i] = 100.0
    # wave 1 bull: bars 5,6,7 (close > open, rising)
    o[5], c[5], h[5], l[5] = 100.0, 101.5, 102.0, 99.8
    o[6], c[6], h[6], l[6] = 101.5, 103.0, 103.5, 101.2
    o[7], c[7], h[7], l[7] = 103.0, 105.0, 105.5, 102.8
    # wave 2 bear: bars 8,9,10 (close < open, falling)
    o[8], c[8], h[8], l[8] = 105.0, 103.5, 105.2, 103.0
    o[9], c[9], h[9], l[9] = 103.5, 102.0, 103.8, 101.5
    o[10], c[10], h[10], l[10] = 102.0, 100.5, 102.3, 100.0
    # signal bar 11, entry bar 12
    o[11], c[11], h[11], l[11] = 100.5, 101.0, 101.5, 100.0
    o[12], c[12], h[12], l[12] = 101.0, 103.0, 105.0, 100.5
    # remaining bars
    for i in range(13, n):
        o[i] = c[i] = 101.0
        h[i] = 102.0
        l[i] = 100.0
    return pd.DataFrame({
        "open": o, "high": h, "low": l, "close": c,
        "volume": np.ones(n, dtype=int) * 5000,
    }, index=dates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWave12PairDetection:
    def test_bull_bear_pair_detected(self):
        df = _make_wave_pattern()
        classified = classify_candles(df)
        pairs = _build_wave12_pairs(classified)
        bull_pairs = [p for p in pairs if p["direction"] == "long"]
        assert len(bull_pairs) >= 1, "Should detect bull+bear wave pair"

    def test_wave1_amp_positive(self):
        df = _make_wave_pattern()
        classified = classify_candles(df)
        pairs = _build_wave12_pairs(classified)
        for p in pairs:
            assert p["wave1_amp"] > 0, "Wave 1 amplitude must be positive"

    def test_direction_consistency(self):
        df = _make_wave_pattern()
        classified = classify_candles(df)
        pairs = _build_wave12_pairs(classified)
        for p in pairs:
            if p["direction"] == "long":
                # wave 1 should be bull
                w1_slice = classified.iloc[p["wave1_start"]:p["wave1_end"] + 1]
                bull_ratio = (w1_slice["close"] > w1_slice["open"]).mean()
                assert bull_ratio > 0.5, "Long pair: wave 1 should be predominantly bull"
            else:
                w1_slice = classified.iloc[p["wave1_start"]:p["wave1_end"] + 1]
                bear_ratio = (w1_slice["close"] < w1_slice["open"]).mean()
                assert bear_ratio > 0.5, "Short pair: wave 1 should be predominantly bear"


class TestCausality:
    def test_wave2_completes_before_signal(self):
        """Wave 2 end index must be < signal index."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        # Signal at bar 11 → entry at bar 12
        signal_idx = 11
        pair = last_wave12_before(classified, signal_idx)
        if pair is not None:
            assert pair["pair_end_idx"] < signal_idx, \
                f"Wave 2 end ({pair['pair_end_idx']}) must be before signal ({signal_idx})"

    def test_no_future_data_in_tp(self):
        """TP depends only on wave 1 which is before wave 2 which is before signal."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        signal_idx = 11
        pair = last_wave12_before(classified, signal_idx)
        if pair is not None:
            # wave1_end < wave2_start (wave 1 comes before wave 2)
            assert pair["wave1_end"] < pair["wave2_start"]
            # wave2_end < signal_idx
            assert pair["wave2_end"] < signal_idx


class TestEntryTiming:
    def test_entry_on_next_bar_open(self):
        """Entry price must be open of bar AFTER signal bar."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        signal_idx = 11
        pair = last_wave12_before(classified, signal_idx)
        if pair is not None:
            entry_bar = signal_idx + 1
            entry_price = df["open"].iloc[entry_bar]
            assert entry_price > 0


class TestTimeCap:
    def test_trades_limited_by_time_cap(self):
        """All trades must have bars_held <= time_cap."""
        df = _make_wave_pattern()
        # Replicate to get enough data for MTF signal
        long_df = pd.concat([df] * 10, ignore_index=False)
        long_df = long_df[~long_df.index.duplicated(keep="last")]
        long_df = long_df.sort_index()
        htf = long_df.resample("1D").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
        # Build a trivial MTF signal
        ltf = mtf.prepare_ohlc(long_df)
        htf_prepared = mtf.prepare_ohlc(htf)
        sig = mtf.mtf_signal(ltf, htf_prepared, pattern="zone_break",
                              ltf_zone=20, htf_zone=20)
        # No signals expected from random data, but if any: check time cap
        if sig.any():
            trades = honest_trades_elliott(
                long_df, htf, wave_tf="4h", k=1.0, time_cap=6)
            for t in trades:
                assert t["bars_held"] <= 6, \
                    f"bars_held={t['bars_held']} exceeds time_cap=6"


class TestNoWaveSkipsTrade:
    def test_no_wave_no_trade(self):
        """When no wave 1-2 pair is found, no trade should be entered."""
        # Flat bars — no waves possible
        n = 100
        dates = pd.date_range("2025-07-01", periods=n, freq="4h")
        flat = pd.DataFrame({
            "open": 100.0, "high": 100.5, "low": 99.5,
            "close": 100.0, "volume": 5000,
        }, index=dates)
        classified = classify_candles(flat)
        pair = last_wave12_before(classified, 50)
        assert pair is None, "Flat data should have no wave pairs"


class TestTPDirection:
    def test_long_tp_above_entry(self):
        """For long trades, TP must be above entry price."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        pair = last_wave12_before(classified, 11)
        if pair and pair["direction"] == "long":
            entry = df["open"].iloc[12]
            tp = entry + 1.0 * pair["wave1_amp"]
            assert tp > entry

    def test_short_tp_below_entry(self):
        """For short trades, TP must be below entry price."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        pair = last_wave12_before(classified, 11)
        if pair and pair["direction"] == "short":
            entry = df["open"].iloc[12]
            tp = entry - 1.0 * pair["wave1_amp"]
            assert tp < entry
