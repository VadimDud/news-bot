"""Tests for the elementary TA detector library (app.ta_lib).

The load-bearing test is causality: appending future bars must not change any
event that was already knowable. Each detector is checked with ``assert_causal``
plus a few structural assertions on hand-built frames.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app import ta_lib
from app.sr_research import load_candles
from pathlib import Path


DB = Path(__file__).resolve().parents[1] / "data" / "trader_4h.db"


def _frame(prices: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=len(prices), freq="2h")
    arr = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {
            "open": arr,
            "high": arr + 0.5,
            "low": arr - 0.5,
            "close": arr,
            "volume": np.ones(len(arr)),
        },
        index=idx,
    )


def _zigzag(n: int = 200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1, n)
    prices = 100 + np.cumsum(steps)
    idx = pd.date_range("2026-01-01", periods=n, freq="2h")
    high = prices + rng.uniform(0.1, 1.0, n)
    low = prices - rng.uniform(0.1, 1.0, n)
    return pd.DataFrame(
        {
            "open": prices,
            "high": np.maximum(high, prices),
            "low": np.minimum(low, prices),
            "close": prices,
            "volume": rng.uniform(1, 5, n),
        },
        index=idx,
    )


@pytest.fixture(scope="module")
def real_2h() -> pd.DataFrame:
    if not DB.exists():
        pytest.skip("research DB not available")
    df = load_candles(str(DB), "SBER", "2h")
    if df is None or len(df) < 100:
        pytest.skip("SBER 2h not available")
    return df


def test_swings_confirmation_lag():
    df = _frame([1, 1.2, 1.4, 2.0, 1.4, 1.2, 1])
    sw = ta_lib.swings(df, look=1)
    highs = sw[sw["side"] == "high"]
    assert not highs.empty
    top = highs.iloc[0]
    assert top["swing_idx"] == 3
    assert top["known_at"] == df.index[4]
    assert top["price"] == pytest.approx(float(df["high"].iloc[3]))


def test_swings_plateau_single_pivot():
    df = _frame([0, 1, 3, 3, 3, 3, 1, 0])
    sw = ta_lib.swings(df, look=1)
    highs = sw[sw["side"] == "high"]
    assert len(highs) == 1


def test_swings_causal(real_2h):
    for cut in (80, 150, 300):
        ta_lib.assert_causal(ta_lib.swings, real_2h, cut, look=3)


def test_levels_causal(real_2h):
    for cut in (160, 320):
        ta_lib.assert_causal(ta_lib.levels, real_2h, cut, look=3, merge_atr=0.5)


def test_breakouts_and_retests_causal(real_2h):
    lv = ta_lib.levels(real_2h, look=3, merge_atr=0.5)

    def _brk(d, **kw):
        lv2 = ta_lib.levels(d, look=3, merge_atr=0.5)
        return ta_lib.breakouts(d, lv2, **kw)

    for cut in (200, 400):
        ta_lib.assert_causal(_brk, real_2h[:cut + 200], 100, max_age_bars=100)

    br = ta_lib.breakouts(real_2h, lv)
    assert not br.empty
    assert set(br["direction"].unique()) <= {1, -1}


def test_retest_is_not_a_return(real_2h):
    lv = ta_lib.levels(real_2h, look=3, merge_atr=0.5)
    br = ta_lib.breakouts(real_2h, lv, max_age_bars=500)
    rt = ta_lib.retests(real_2h, br, max_wait_bars=10)
    rr = ta_lib.returns_to_level(real_2h, br, max_wait_bars=10)
    # A bar cannot be both: retest closes back in the direction, return closes out.
    key_rt = set(zip(rt["break_bar"], rt["bar"]))
    key_rr = set(zip(rr["break_bar"], rr["bar"]))
    assert key_rt.isdisjoint(key_rr)


def test_breakouts_have_positive_distance(real_2h):
    lv = ta_lib.levels(real_2h, look=3, merge_atr=0.5)
    br = ta_lib.breakouts(real_2h, lv, max_age_bars=500)
    assert (br["dist_atr"].dropna() > 0).all()


def test_failures_causal(real_2h):
    def _fail(d, **kw):
        lvl = ta_lib.levels(d, look=3, merge_atr=0.5)
        b = ta_lib.breakouts(d, lvl, max_age_bars=200)
        r = ta_lib.returns_to_level(d, b, max_wait_bars=10)
        return ta_lib.failures(d, r, look=3)

    for cut in (300, 500):
        ta_lib.assert_causal(_fail, real_2h[:cut + 300], 120)
