import numpy as np
import pandas as pd
import pytest

from app.pa_levels import PALevelParams, generate_signals, htf_trend_at
from scripts.backtest_pa_levels import simulate_trades


def fixture(side=1):
    df = pd.DataFrame(dict(open=[100., 100., 100., 97.],
                           high=[101., 101., 101., 99.],
                           low=[99., 99., 98., 96.],
                           close=[100., 100., 99., 98.], volume=1.),
                      index=pd.date_range("2024-01-01", periods=4))
    if side == -1:
        df[["open", "high", "low", "close"]] = 200 - df[["open", "low", "high", "close"]].to_numpy()
    sig = pd.DataFrame([dict(idx=0, side=side, price=100.,
                             stop=100 - side * 10, target=100 + side * 20,
                             reasons=[])])
    return df, sig


@pytest.mark.parametrize("side", [1, -1])
def test_stop_gap_and_cost_identity(side):
    df, sig = fixture(side)
    df.iloc[2, df.columns.get_loc("open")] = 100 - side * 15
    tr = simulate_trades(df, sig, PALevelParams(), .0005, .0005)[0]
    assert tr["reason"] == "stop_gap"
    assert tr["exit"] == 100 - side * 15
    assert tr["r_multiple"] == pytest.approx((tr["gross"] - tr["commission"] - tr["slippage"]) / 10)


@pytest.mark.parametrize("side", [1, -1])
def test_bailout_waits_for_next_open(side):
    df, sig = fixture(side)
    tr = simulate_trades(df, sig, PALevelParams(bailout_on_drawdown=1), 0, 0)[0]
    assert tr["reason"] == "bailout"
    assert tr["exit_idx"] == 3
    assert tr["exit"] == 100 - side * 3


@pytest.mark.parametrize("side", [1, -1])
def test_oco_stop_first_and_invalid_entry_target(side):
    df, sig = fixture(side)
    df.loc[df.index[1], ["high", "low"]] = [130, 70]
    tr = simulate_trades(df, sig, PALevelParams(), 0, 0)
    assert len(tr) == 1 and tr[0]["reason"] == "stop"
    df.loc[df.index[1], "open"] = 100 + side * 25
    assert simulate_trades(df, sig, PALevelParams(), 0, 0) == []


def test_missing_htf_is_not_silently_disabled():
    df, _ = fixture()
    with pytest.raises(ValueError, match="use_htf"):
        generate_signals(df, PALevelParams(use_htf=1))


def test_last_htf_not_assumed_closed_and_nontrivial_ema():
    df, _ = fixture()
    df["close"] = [100., 110., 50., 120.]
    at = pd.to_datetime(["2024-01-03", "2024-01-05"])
    assert htf_trend_at(df, at, 3).tolist() == [1, -1]
    assert htf_trend_at(df.iloc[:1], at, 3).tolist() == [0, 0]


def test_video_prefix_complete_rows():
    from scripts.pa_levels_demo import synthetic_ohlcv
    df = synthetic_ohlcv(n=400, seed=11)
    p = PALevelParams(require_compression=1, compress_after_return=1,
                      impulse_atr_min=.5, bailout_on_drawdown=1)
    full = generate_signals(df, p)
    for cut in (100, 200, 300):
        pd.testing.assert_frame_equal(
            full[full.idx < cut].reset_index(drop=True),
            generate_signals(df.iloc[:cut], p).reset_index(drop=True),
            check_dtype=False)
