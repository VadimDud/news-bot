"""Tests for MTF + 2h Fibonacci correction diagnostic (backtest_mtf_fib).

Проверяем:
  1. причинность: добавление будущих 2h-баров не меняет подтверждение на
     прошлых 4h-барах;
  2. фильтр только отсекает: множество входов fib ⊆ baseline;
  3. выход неизменен: exit_bar == исходный signal+1+horizon;
  4. фичи не падают на недостатке данных.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import mtf_confirm as mtf  # noqa: E402
from scripts.backtest_mtf_fib import (  # noqa: E402
    honest_trades_fib,
    signal_hours_mask,
    _swing_levels,
    fib_zone_state,
    ZONES,
)


def _synth(n=400, seed=7, freq="4h"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq=freq)
    steps = rng.normal(0, 1, n).cumsum() * 0.5 + 100
    o = steps + rng.normal(0, 0.2, n)
    c = steps + rng.normal(0, 0.2, n)
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.3, n))
    lo = np.minimum(o, c) - np.abs(rng.normal(0, 0.3, n))
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c,
                         "volume": 1000 + rng.integers(0, 100, n)}, index=idx)


def _synth_2h(n=800, seed=11):
    return _synth(n=n, seed=seed, freq="2h")


def test_fib_variants_are_subset_of_baseline():
    ltf = _synth()
    htf = _synth_2h()
    common = dict(pattern="strong_body", ltf_zone=20, htf_zone=15,
                  horizon=6, direction=-1)
    em = signal_hours_mask(ltf, [4, 8, 12])
    base = honest_trades_fib(ltf, htf, htf, mode="baseline", event_mask=em, **common)
    base_entries = {(t["signal_bar"], t["exit_bar"]) for t in base}
    for mode in ("fib_382_618", "fib_50_618", "fib_618_786"):
        fib = honest_trades_fib(ltf, htf, htf, mode=mode, event_mask=em, **common)
        fib_entries = {(t["signal_bar"], t["exit_bar"]) for t in fib}
        # каждый fib-вход соответствует baseline-сделке (не больше сигналов)
        assert fib_entries <= base_entries, f"{mode} добавил новые входы"


def test_exit_bar_unchanged_for_fib():
    ltf = _synth()
    htf = _synth_2h()
    em = signal_hours_mask(ltf, [4, 8, 12])
    for mode in ("baseline", "fib_382_618", "fib_50_618"):
        tr = honest_trades_fib(ltf, htf, htf, pattern="strong_body", ltf_zone=20,
                               htf_zone=15, horizon=6, direction=-1,
                               mode=mode, event_mask=em)
        for t in tr:
            assert t["exit_bar"] == min(t["signal_bar"] + 1 + 6, len(ltf) - 1), \
                "выход должен быть на close исходного entry+horizon"
            assert t["entry_bar"] >= t["signal_bar"] + 1
            assert t["entry_bar"] < t["exit_bar"]


def test_no_lookahead_future_2h_does_not_change_past():
    ltf = _synth()
    htf = _synth_2h()
    em = signal_hours_mask(ltf, [4, 8, 12])
    tr1 = honest_trades_fib(ltf, htf, htf, pattern="strong_body", ltf_zone=20,
                            htf_zone=15, horizon=6, direction=-1,
                            mode="fib_50_618", event_mask=em)
    # добавляем будущие 2h-бары, которые не пересекают проверяемый период
    extra = _synth_2h(n=200, seed=99)
    extra.index = pd.date_range(htf.index[-1] + pd.Timedelta(hours=2),
                                periods=200, freq="2h")
    htf_future = pd.concat([htf, extra])
    tr2 = honest_trades_fib(ltf, htf_future, htf_future, pattern="strong_body",
                            ltf_zone=20, htf_zone=15, horizon=6, direction=-1,
                            mode="fib_50_618", event_mask=em)
    # число входов и их сигнальные бары не должны измениться
    assert [(t["signal_bar"], t["entry_bar"]) for t in tr1] == \
           [(t["signal_bar"], t["entry_bar"]) for t in tr2]


def test_swing_levels_on_short_window():
    df = _synth_2h(n=6)
    sl, sh = _swing_levels(df)
    assert sh >= sl


def test_fib_zone_state_no_crash_small():
    df = _synth_2h(n=3)
    in_zone, reversal = fib_zone_state(df, -1, ZONES["fib_50_618"])
    assert isinstance(in_zone, bool) and isinstance(reversal, bool)
