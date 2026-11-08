"""Tests for app.pa_levels — causal detectors and signal assembly (synthetic data)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pa_levels import (  # noqa: E402
    PALevelParams,
    detect_candlestick_patterns,
    find_liquidity_clusters,
    find_support_resistance,
    generate_signals,
    relative_volume,
)
from scripts.pa_levels_demo import synthetic_ohlcv  # noqa: E402


@pytest.fixture(scope="module")
def frame():
    return synthetic_ohlcv(n=400, seed=11)


def test_relative_volume_positive(frame):
    rv = relative_volume(frame, 20)
    assert rv.shape == (len(frame),)
    assert np.all(rv > 0)


def test_levels_are_causal(frame):
    # Уровни, известные до cut, не должны меняться при отрезании будущего.
    cut = 250
    p = PALevelParams()
    full = find_support_resistance(frame, p)
    part = find_support_resistance(frame.iloc[:cut], p)
    full_pre = full[full["known_at"] < frame.index[cut - 1]].reset_index(drop=True)
    part_all = part.reset_index(drop=True)
    # известные до разреза совпадают по цене и side
    n = min(len(full_pre), len(part_all))
    assert n > 0
    assert np.allclose(full_pre.loc[:n - 1, "price"], part_all.loc[:n - 1, "price"])
    assert (full_pre.loc[:n - 1, "side"].values == part_all.loc[:n - 1, "side"].values).all()


def test_signals_causal(frame):
    cut = 250
    p = PALevelParams()
    full = generate_signals(frame, p)
    part = generate_signals(frame.iloc[:cut], p)
    f = full[full["idx"] < cut - 1].reset_index(drop=True)
    q = part[part["idx"] < cut - 1].reset_index(drop=True)
    assert len(f) == len(q)
    if len(f):
        assert (f["idx"].values == q["idx"].values).all()
        assert (f["side"].values == q["side"].values).all()


def test_patterns_are_binary(frame):
    atr = np.full(len(frame), 1.0)
    pats = detect_candlestick_patterns(frame, atr)
    assert pats["bullish_reversal"].dtype == bool
    assert pats["bearish_reversal"].dtype == bool
    assert not (pats["bullish_reversal"] & pats["bearish_reversal"]).any()


def test_liquidity_clusters_present(frame):
    vp = find_liquidity_clusters(frame, 200, PALevelParams())
    assert vp["bsl"] is not None and vp["ssl"] is not None
    assert vp["bsl"] >= vp["ssl"]


def test_signal_bracket_direction(frame):
    sig = generate_signals(frame, PALevelParams())
    for _, s in sig.iterrows():
        if s["side"] == 1:
            assert s["stop"] < s["price"] < s["target"]
        else:
            assert s["target"] < s["price"] < s["stop"]


def test_direction_filter(frame):
    sig_long = generate_signals(frame, PALevelParams(direction=1))
    sig_short = generate_signals(frame, PALevelParams(direction=-1))
    assert all(sig_long["side"] == 1) or len(sig_long) == 0
    assert all(sig_short["side"] == -1) or len(sig_short) == 0
