"""Tests for ICT Liquidity Sweep + FVG (reversal) — synthetic data, no DB."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ict_sweep_fvg as ict  # noqa: E402
from app import signals as sig_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frame(rows, freq="4h"):
    """rows: list of (open, high, low, close, volume)."""
    idx = pd.date_range("2024-01-01", periods=len(rows), freq=freq)
    return pd.DataFrame(
        rows, columns=["open", "high", "low", "close", "volume"], index=idx
    )


def _flat(n=30, price=100.0):
    return _frame([(price, price + 0.2, price - 0.2, price, 1000.0)] * n)


# ---------------------------------------------------------------------------
# Session / external levels — causation
# ---------------------------------------------------------------------------

def test_prepare_ohlc_accepts_begin_column():
    df = _flat(5)
    raw = df.reset_index().rename(columns={"index": "begin"})
    out = ict.prepare_ohlc(raw)
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    assert isinstance(out.index, pd.DatetimeIndex)


def test_external_levels_ffill_and_shift():
    df = _flat(48)
    ext = ict._external_levels(df, None)
    assert {"pd_high", "pd_low", "pw_high", "pw_low"} <= set(ext.columns)
    # уровни становятся известны только со следующего периода (shift)
    assert ext["pd_high"].iloc[0] != ext["pd_high"].iloc[0] or np.isnan(ext["pd_high"].iloc[0])


# ---------------------------------------------------------------------------
# Sweep detection
# ---------------------------------------------------------------------------

def test_bullish_sweep_detected():
    # low пробил уровень 100, close вернулся выше, длинная нижняя тень
    assert ict._is_bullish_sweep(101.0, 102.0, 98.0, 101.5, 100.0, 0.5)


def test_bullish_sweep_rejects_close_below_level():
    # поглощающий пробой: close остался ниже уровня — не sweep
    assert not ict._is_bullish_sweep(101.0, 102.0, 98.0, 99.0, 100.0, 0.5)


def test_bullish_sweep_rejects_short_wick():
    # тень слишком короткая (wick_frac не выполняется)
    assert not ict._is_bullish_sweep(99.5, 100.1, 99.0, 99.9, 100.0, 0.5)


def test_bearish_sweep_detected_and_rejected():
    assert ict._is_bearish_sweep(99.0, 102.0, 98.0, 99.2, 100.0, 0.5)
    assert not ict._is_bearish_sweep(99.0, 102.0, 98.0, 101.0, 100.0, 0.5)


# ---------------------------------------------------------------------------
# Displacement + FVG
# ---------------------------------------------------------------------------

def test_fvg_bullish_requires_displacement():
    a = 1.0
    # свеча i-1: большое тело (open 100, close 103), диапазон плотный
    rows = [
        (99.0, 99.2, 98.8, 99.0, 1000.0),     # i-2
        (100.0, 103.2, 99.9, 103.0, 2000.0),  # i-1 displacement
        (103.5, 104.0, 102.5, 103.8, 1500.0), # i: low(102.5) > high(i-2)=99.2
    ]
    df = _frame(rows)
    f = ict._fvg_at(df, 2, a, 1.0, 0.6)
    assert f is not None and f["side"] == 1
    assert f["lo"] == pytest.approx(99.2)
    assert f["hi"] == pytest.approx(102.5)


def test_fvg_shadow_without_displacement_rejected():
    a = 1.0
    rows = [
        (99.0, 99.2, 98.8, 99.0, 1000.0),
        (100.0, 100.3, 99.9, 100.0, 1000.0),  # тело ~0 → нет displacement
        (103.5, 104.0, 102.5, 103.8, 1500.0),
    ]
    df = _frame(rows)
    assert ict._fvg_at(df, 2, a, 1.0, 0.6) is None


def test_fvg_bearish_template():
    a = 1.0
    rows = [
        (101.0, 101.2, 100.8, 101.0, 1000.0),  # i-2 high=101.2
        (100.0, 100.1, 97.0, 97.2, 2000.0),    # i-1 displacement вниз
        (96.5, 97.0, 95.0, 95.5, 1500.0),      # i: high(97.0) < low(i-2)? low(i-2)=100.8
    ]
    df = _frame(rows)
    f = ict._fvg_at(df, 2, a, 1.0, 0.6)
    assert f is not None and f["side"] == -1
    assert f["lo"] == pytest.approx(97.0)
    assert f["hi"] == pytest.approx(100.8)


# ---------------------------------------------------------------------------
# Order Block overlap
# ---------------------------------------------------------------------------

def test_order_block_and_overlap():
    fvg = {"lo": 99.2, "hi": 102.5, "side": 1, "create_idx": 2}
    # OB-уровень внутри зоны
    assert ict._fvg_ob_overlap(fvg, 101.0, 0.5)
    # OB на границе (касание)
    assert ict._fvg_ob_overlap(fvg, 99.2, 0.0)
    # OB в пределах допуска (доля высоты) за краем
    assert ict._fvg_ob_overlap(fvg, 98.0, 0.5)
    # OB далеко снаружи
    assert not ict._fvg_ob_overlap(fvg, 120.0, 0.5)
    assert not ict._fvg_ob_overlap(fvg, None, 0.1)


# ---------------------------------------------------------------------------
# MSS / kill zones
# ---------------------------------------------------------------------------

def test_mss_confirms_long():
    df = _frame([(100, 101, 99, 100, 1)] * 3)
    sl = np.array([np.nan, 99.0, 99.0])
    sh = np.array([np.nan, 100.5, 100.5])
    # close 100 < swing high 100.5 → нет MSS
    assert not ict._mss_confirms(df, 2, 1, sl, sh)
    df2 = _frame([(100, 101, 99, 100, 1), (100, 101, 99, 100, 1), (100, 103, 99, 102, 1)])
    assert ict._mss_confirms(df2, 2, 1, sl, sh)


def test_kill_zone_mask():
    df = _flat(24)
    df.index = pd.date_range("2024-01-01", periods=24, freq="h")
    mask = ict._kill_zone_mask(df)
    # 1h-бары: зоны MOEX (07–10 и 16–21 UTC)
    for ts, m in zip(df.index, mask):
        h = ts.hour
        expected = (7 <= h < 10) or (16 <= h < 21)
        assert bool(m) == expected, ts


def test_kill_zone_interval_overlap():
    # 4h-бар 16:00–20:00 UTC перекрывает вечернюю Kill Zone (16–21)
    assert ict._in_kill_zone(pd.Timestamp("2024-01-01 16:00"), duration_min=240)
    # 4h-бар 04:00–08:00 UTC перекрывает утреннюю (07–10) — начинается до неё
    assert ict._in_kill_zone(pd.Timestamp("2024-01-01 04:00"), duration_min=240)
    # 4h-бар 20:00–00:00 UTC начинается внутри 16–21 → перекрывает
    assert ict._in_kill_zone(pd.Timestamp("2024-01-01 20:00"), duration_min=240)
    # 4h-бар 12:00–16:00 UTC заканчивается ровно на границе 16 → не перекрывает
    assert not ict._in_kill_zone(pd.Timestamp("2024-01-01 12:00"), duration_min=240)


# ---------------------------------------------------------------------------
# Causation / no-lookahead
# ---------------------------------------------------------------------------

def test_compute_arrays_is_causal():
    """Сигналы на первых k барах не меняются при добавлении будущих данных."""
    rng = np.random.default_rng(42)
    n = 300
    close = 100 + np.cumsum(rng.normal(0, 0.6, n))
    open_ = np.append(close[0], close[:-1])
    high = np.maximum(open_, close) + rng.uniform(0, 0.4, n)
    low = np.minimum(open_, close) - rng.uniform(0, 0.4, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="4h")
    df = pd.DataFrame({"open": open_, "high": high, "low": low,
                       "close": close, "volume": np.arange(n) + 100}, index=idx)

    k = 200
    st_full = ict._compute_arrays(df)
    st_cut = ict._compute_arrays(df.iloc[:k])
    for key in ("entry_ok_long", "entry_ok_short", "sweep_side"):
        assert np.array_equal(st_full[key][:k], st_cut[key]), key


# ---------------------------------------------------------------------------
# Integration: signal + strategy parity is exercised in test_fib_pullback's
# harness; here we check the R:R gate and registry wiring.
# ---------------------------------------------------------------------------

def test_min_rr_gate_default_is_25():
    from app.strategies import _ICT_PARAMS_TUPLE
    d = dict(_ICT_PARAMS_TUPLE)
    assert d["min_rr"] == 2.5


def test_ict_not_in_signal_funcs():
    """ICT не должна быть доступна в live до подтверждения бэктестом."""
    assert "ict_sweep_fvg" not in sig_mod.SIGNAL_FUNCS


def test_strategy_registered():
    from app.strategies import STRATEGIES, IctSweepFvgStrategy
    assert "ict_sweep_fvg" in STRATEGIES
    assert STRATEGIES["ict_sweep_fvg"]["cls"] is IctSweepFvgStrategy


def test_rr_gate_rejects_below_min():
    """Гейт R:R: низкий reward не даёт сигнала."""
    # Тренд вниз, sweep вверх → шорт, но цель близко (RR < 2.5) → нет сигнала.
    rows = [(100, 100.2, 99.8, 100, 1000)] * 19
    rows += [(100, 101.0, 99.0, 99.5, 3000)]      # bearish sweep
    rows += [(99.0, 99.1, 95.0, 95.2, 4000)]      # displacement down
    rows += [(95.0, 95.1, 93.0, 93.5, 1500)]      # FVG
    df = _frame(rows)
    st = ict._compute_arrays(df, min_rr=2.5)
    # если сигнал появился — он обязан удовлетворять R:R >= 2.5
    for i in range(len(df)):
        if st["entry_ok_short"][i]:
            assert st["rr"][i] >= 2.5
