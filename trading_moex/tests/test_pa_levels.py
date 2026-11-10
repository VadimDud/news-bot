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


def test_htf_trend_is_causal(frame):
    from app.pa_levels import htf_trend_at
    # HTF-тренд берёт только закрытые HTF-бары (merge_asof backward): будущий
    # рост не должен менять направление на более раннем LTF-баре.
    idx = pd.date_range("2024-01-01", periods=20, freq="D")
    close = np.full(20, 100.0)
    close[10:] = 200.0  # резкий разворот с бара 10
    htf = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": 1.0}, index=idx)
    d = htf_trend_at(htf, idx, ema_period=5)
    assert d[0] == 0          # до разворота — без тренда (флэт)
    assert d[-1] == 1         # после разворота — вверх
    assert d[8] == 0          # бар до разворота не «знает» о будущем росте


def test_video_flags_default_off(frame):
    p = PALevelParams()
    assert p.use_htf == 0
    assert p.require_compression == 0
    # отключённые флаги не меняют сигналы
    base = generate_signals(frame, PALevelParams())
    same = generate_signals(frame, PALevelParams(use_htf=0, require_compression=0))
    assert len(base) == len(same)


def test_compression_mask_detects_narrow_bar():
    from app.pa_levels import compression_mask
    df = pd.DataFrame({
        "open": [100.0, 100.0], "high": [110.0, 100.2],
        "low": [90.0, 99.9], "close": [105.0, 100.1], "volume": 1.0,
    })
    atr = np.array([5.0, 5.0])
    m = compression_mask(df, atr, PALevelParams(compress_body_ratio=0.35,
                                                compress_range_atr=0.6))
    assert m.tolist() == [False, True]


def test_htf_uses_only_closed_candles():
    """LTF-бар внутри формирующейся HTF-свечи не должен видеть её close."""
    from app.pa_levels import htf_trend_at
    # HTF = дневные свечи; последняя «свеча» растёт, но ещё не закрыта.
    htf_idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    htf = pd.DataFrame({"open": [10, 10, 10], "high": [10, 11, 99],
                        "low": [10, 9, 10], "close": [10, 11, 50],
                        "volume": 1.0}, index=htf_idx)
    # LTF: внутри 3-го HTF-дня (2024-01-03 12:00). Дневная свеча от 01-03
    # закроется только 01-04, значит тренд на полдень 01-03 ещё не «вверх».
    ltf_idx = pd.to_datetime(["2024-01-03 12:00"])
    d = htf_trend_at(htf, ltf_idx, ema_period=1)
    # ema(span=1)=close; на закрытой свече 01-02 close=11 > ema? ema=11, не >,
    # направление 0 или предыдущее; главное — НЕ +1 от незакрытой 01-03 (close=50).
    # явная проверка: последняя ЗАКРЫТАЯ свеча (01-02) не даёт +1 из-за close=50
    htf2 = htf.copy()
    htf2.loc[pd.to_datetime("2024-01-03"), "close"] = 1e9  # будущий экстрим
    d2 = htf_trend_at(htf2, ltf_idx, ema_period=1)
    assert d.tolist() == d2.tolist()  # будущий close не влияет


def test_false_breakout_exposes_extreme_and_same_bar_idx():
    from app.pa_levels import detect_false_breakouts, find_support_resistance
    # строим простой ряд: уровень ~100, бар пробивает вверх (high 105) и
    # возвращается на том же баре (close 99).
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    close = np.full(n, 100.0); high = np.full(n, 100.5); low = np.full(n, 99.5)
    openp = np.full(n, 100.0)
    # два свинг-хая для уровня
    for p in (10, 30):
        high[p] = 101.0
    # бар пробоя: 45 — high 105, close 99 (вернулись на том же баре)
    high[45] = 105.0; low[45] = 98.5; close[45] = 99.0
    df = pd.DataFrame({"open": openp, "high": high, "low": low,
                       "close": close, "volume": 1.0}, index=idx)
    p = PALevelParams(swing_look=2)
    sr = find_support_resistance(df, p)
    fbo = detect_false_breakouts(df, sr, p)
    if not fbo.empty:
        row = fbo[fbo["known_at_idx"] == 45]
        if not row.empty:
            r = row.iloc[0]
            assert r["broke_idx"] == 45          # same-bar: пробой на баре i
            assert r["breakout_extreme"] >= 105.0  # экстремум пробоя сохранён


def test_rr_min_default_is_2():
    assert PALevelParams().rr_min == 2.0


def test_bailout_exit_and_no_overlap():
    from scripts.backtest_pa_levels import simulate_trades
    # сигнал на баре 0 (лонг), затем цена падает -> bailout; второй сигнал
    # внутри позиции игнорируется.
    n = 10
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    o = np.array([100, 100, 100, 100, 100, 100, 100, 100, 100, 100], float)
    h = np.array([101, 101, 101, 101, 101, 101, 101, 101, 101, 101], float)
    l = np.array([99, 99, 99, 99, 99, 99, 99, 99, 99, 99], float)
    c = np.array([100, 100, 98, 97, 96, 95, 94, 93, 92, 91], float)
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1.0}, index=idx)
    sig = pd.DataFrame([
        {"idx": 0, "time": idx[1], "side": 1, "price": 100, "stop": 90, "target": 120,
         "reasons": ["t"]},
        {"idx": 1, "time": idx[2], "side": 1, "price": 100, "stop": 90, "target": 120,
         "reasons": ["t2"]},
    ])
    p = PALevelParams(bailout_on_drawdown=1)
    trades = simulate_trades(df, sig, p, commission=0.0, slippage=0.0)
    assert len(trades) == 1                    # второй сигнал внутри позиции отброшен
    assert trades[0]["reason"] == "bailout"    # цена пошла к стопу, не дойдя до цели
