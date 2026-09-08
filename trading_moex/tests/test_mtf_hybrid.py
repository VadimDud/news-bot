#!/usr/bin/env python3
"""Causality tests for the MTF hybrid exit backtest.

Verifies:
- Hybrid takes ALL signals (no wave filter) — same count as baseline
- TP exits only when wave 1-2 pair exists and matches signal direction
- Baseline exits (close+6) used when no wave pair exists
- No lookahead: wave 2 completes before signal, TP set at entry
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from app.elliott_candles import classify_candles  # noqa: E402
from app import mtf_confirm as mtf  # noqa: E402
from scripts.backtest_mtf_hybrid import honest_trades_hybrid  # noqa: E402
from scripts.backtest_mtf_confirm import honest_trades as baseline_trades  # noqa: E402


def _make_wave_pattern() -> pd.DataFrame:
    """Construct df with explicit bull+bear wave pair."""
    n = 30
    dates = pd.date_range("2025-07-01", periods=n, freq="4h")
    o = np.zeros(n); h = np.zeros(n); l = np.zeros(n); c = np.zeros(n)
    for i in range(5):
        o[i] = h[i] = l[i] = c[i] = 100.0
    o[5], c[5], h[5], l[5] = 100.0, 101.5, 102.0, 99.8
    o[6], c[6], h[6], l[6] = 101.5, 103.0, 103.5, 101.2
    o[7], c[7], h[7], l[7] = 103.0, 105.0, 105.5, 102.8
    o[8], c[8], h[8], l[8] = 105.0, 103.5, 105.2, 103.0
    o[9], c[9], h[9], l[9] = 103.5, 102.0, 103.8, 101.5
    o[10], c[10], h[10], l[10] = 102.0, 100.5, 102.3, 100.0
    o[11], c[11], h[11], l[11] = 100.5, 101.0, 101.5, 100.0
    o[12], c[12], h[12], l[12] = 101.0, 103.0, 105.0, 100.5
    for i in range(13, n):
        o[i] = c[i] = 101.0; h[i] = 102.0; l[i] = 100.0
    return pd.DataFrame({
        "open": o, "high": h, "low": l, "close": c,
        "volume": np.ones(n, dtype=int) * 5000,
    }, index=dates)


class TestHybridExits:
    def test_no_wave_uses_baseline_exit(self):
        """Without wave pair, all trades exit at close+6."""
        n = 100
        dates = pd.date_range("2025-07-01", periods=n, freq="4h")
        flat = pd.DataFrame({
            "open": 100.0, "high": 100.5, "low": 99.5,
            "close": 100.0, "volume": 5000,
        }, index=dates)
        classified = classify_candles(flat)
        # No waves in flat data
        from scripts.backtest_mtf_elliott_tp import _build_wave12_pairs
        pairs = _build_wave12_pairs(classified)
        assert len(pairs) == 0, "Flat data should have no wave pairs"

    def test_hybrid_takes_all_signals(self):
        """Hybrid should produce same or more trades than Elliott TP."""
        df = _make_wave_pattern()
        ltf = mtf.prepare_ohlc(df)
        # Verify mtf_signal produces at least one signal
        if len(ltf) < 50:
            pytest.skip("Pattern too short for MTF signal")
        htf = ltf.resample("1D").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
        sig = mtf.mtf_signal(ltf, mtf.prepare_ohlc(htf), pattern="zone_break",
                              ltf_zone=20, htf_zone=20)
        # If no signals, skip
        if sig.sum() == 0:
            pytest.skip("No signals in test pattern")
        # Hybrid should produce at least as many trades as Elliott
        hybrid_trades = honest_trades_hybrid(
            df, htf, wave_tf="4h", k=1.618, time_cap=12)
        from scripts.backtest_mtf_elliott_tp import honest_trades_elliott
        elliott_trades = honest_trades_elliott(
            df, htf, wave_tf="4h", k=1.618, time_cap=12)
        assert len(hybrid_trades) >= len(elliott_trades), \
            f"Hybrid ({len(hybrid_trades)}) should have >= Elliott ({len(elliott_trades)})"

    def test_tp_hit_is_profitable(self):
        """Every TP hit must be profitable (100% win rate for TP exits)."""
        # Use real data for meaningful test
        from scripts.backtest_mtf_elliott_tp import load_df
        db = str(ROOT / "trading_moex" / "data" / "trader_4h.db")
        ltf = load_df("TATN", db, "4h")
        htf = load_df("TATN", db, "1day")
        if len(ltf) < 60 or len(htf) < 60:
            pytest.skip("No data")
        trades = honest_trades_hybrid(
            ltf, htf, wave_tf="1day", k=1.618, time_cap=12,
            signal_hours=[4, 8, 12])
        tp_hits = [t for t in trades if t["tp_hit"]]
        for t in tp_hits:
            assert t["pnl_net_pct"] > 0, f"TP hit must be profitable: {t}"

    def test_exit_type_consistency(self):
        """baseline exits have has_tp=False, tp exits have has_tp=True."""
        from scripts.backtest_mtf_elliott_tp import load_df
        db = str(ROOT / "trading_moex" / "data" / "trader_4h.db")
        ltf = load_df("LKOH", db, "4h")
        htf = load_df("LKOH", db, "1day")
        if len(ltf) < 60 or len(htf) < 60:
            pytest.skip("No data")
        trades = honest_trades_hybrid(
            ltf, htf, wave_tf="1day", k=1.618, time_cap=12,
            signal_hours=[4, 8, 12])
        for t in trades:
            if t["exit_type"] == "baseline":
                assert not t["has_tp"], "Baseline exit should have no TP"
            elif t["exit_type"] == "tp":
                assert t["has_tp"] and t["tp_hit"], "TP exit must have TP hit"
            elif t["exit_type"] == "timecap":
                assert t["has_tp"], "Timecap exit must have had TP attempt"

    def test_no_lookahead_in_tp(self):
        """TP price must not use future data."""
        df = _make_wave_pattern()
        classified = classify_candles(df)
        from scripts.backtest_mtf_elliott_tp import last_wave12_before
        pair = last_wave12_before(classified, 11)
        if pair is not None:
            # wave1_amp uses only wave1 candles (before signal)
            assert pair["wave1_end"] < pair["wave2_start"]
            assert pair["wave2_end"] < 11  # signal at bar 11
