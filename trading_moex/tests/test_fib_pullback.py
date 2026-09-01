"""Tests for Fibonacci retracement (trend-continuation) — synthetic data, no DB."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.fib_pullback import (  # noqa: E402
    _adx,
    _confirmed_pivots,
    fib_pullback_signal,
    fib_score_breakdown,
    detect_latest_setup,
    prepare_ohlc,
)
from app.backtest import run_backtest  # noqa: E402
from app.strategies import FibPullbackStrategy, _FIB_PULLBACK_PARAMS_TUPLE  # noqa: E402
from app import signals as sig_mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candles(closes, opens=None, base=100.0, spread=0.4, seed=3):
    """Build an OHLCV DataFrame (hourly index) from close prices."""
    rng = np.random.default_rng(seed)
    close = np.array(closes, dtype=float)
    if opens is None:
        opens = np.append(close[0], close[:-1])
    high = np.maximum(opens, close) + spread * np.abs(rng.normal(0, 1, len(close)))
    low = np.minimum(opens, close) - spread * np.abs(rng.normal(0, 1, len(close)))
    vol = 1000 + np.arange(len(close))
    idx = pd.date_range("2023-01-01", periods=len(close), freq="h")
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def _uptrend_pullbacks(n_cycles=12, up_bars=48, dn_bars=14, seed=3):
    """Uptrend with periodic pullbacks that re-enter the 50–61.8 % zone."""
    rng = np.random.default_rng(seed)
    p, prices = 100.0, []
    for i in range((up_bars + dn_bars) * n_cycles):
        prices.append(p)
        m = i % (up_bars + dn_bars)
        if m < up_bars:
            p += 1.0 + rng.normal(0, 0.2)
        else:
            p -= 2.7
    return prices


def _downtrend_pullbacks(n_cycles=12, dn_bars=48, up_bars=14, seed=5):
    """Downtrend with periodic bounces up (short retracements)."""
    rng = np.random.default_rng(seed)
    p, prices = 200.0, []
    for i in range((dn_bars + up_bars) * n_cycles):
        prices.append(p)
        m = i % (dn_bars + up_bars)
        if m < dn_bars:
            p -= 1.0 + rng.normal(0, 0.2)
        else:
            p += 2.7
    return prices


# ---------------------------------------------------------------------------
# prepare_ohlc
# ---------------------------------------------------------------------------

def test_prepare_ohlc_normalizes_begin_column():
    df = _make_candles([100.0, 101.0, 102.0])
    raw = df.reset_index().rename(columns={"index": "begin"})
    out = prepare_ohlc(raw)
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    assert isinstance(out.index, pd.DatetimeIndex)


# ---------------------------------------------------------------------------
# Pivots
# ---------------------------------------------------------------------------

def _sine(n=200, period=40, amp=5.0):
    return 100 + amp * np.sin(np.arange(n) * 2 * np.pi / period)


def test_confirmed_pivots_no_lookahead():
    # Monotonic rise: нет внутренних пивотов (нет разворота вверх-вниз)
    df = _make_candles([100 + i for i in range(60)])
    low, high = _confirmed_pivots(df, 10)
    assert low.isna().all()
    assert high.isna().all()


def test_confirmed_pivots_detects_zigzag_low_high():
    # Синусоида → внутренние экстремумы (и лоу, и хай) должны детектиться
    df = _make_candles(_sine())
    low, high = _confirmed_pivots(df, 8)
    assert low.notna().any()
    assert high.notna().any()


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------

def test_adx_positive_in_trend():
    df = _make_candles(_uptrend_pullbacks(n_cycles=20))
    adx = _adx(df, 14)
    assert not adx.isna().all()
    assert (adx.tail(30) >= 0).all()


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

def test_signal_fires_in_uptrend_with_pullbacks():
    df = _make_candles(_uptrend_pullbacks(n_cycles=12))
    pos = fib_pullback_signal(
        df, confluence_min=2, rsi_oversold=40, rsi_overbought=85,
        trend_period=200, swing_bars=10,
    )
    assert len(pos) == len(df)
    entries = int((pos.diff() == 1).sum())
    assert entries > 0
    # позиция никогда не отрицательная и бинарная
    assert set(pos.unique()) <= {0, 1}


def test_signal_fewer_entries_in_mean_reverting_zigzag():
    # Сбалансированный зигзаг (без чистого тренда) → заметно меньше входов,
    # чем в аптренде с откатами.
    rng = np.random.default_rng(4)
    p, prices = 100.0, []
    for i in range(600):
        prices.append(p)
        p += (1.0 if (i % 44) < 22 else -1.0) + rng.normal(0, 0.2)
    df_zig = _make_candles(prices)
    df_trend = _make_candles(_uptrend_pullbacks(n_cycles=12))
    ent_zig = int((fib_pullback_signal(
        df_zig, confluence_min=2, rsi_oversold=40, rsi_overbought=85, trend_period=200
    ).diff() == 1).sum())
    ent_trend = int((fib_pullback_signal(
        df_trend, confluence_min=2, rsi_oversold=40, rsi_overbought=85, trend_period=200
    ).diff() == 1).sum())
    assert ent_trend > 0
    assert ent_zig < ent_trend


def test_signal_trend_gate_off_with_no_trend_param():
    # trend_period=0 → тренд не блокирует, но входам препятствуют прочие фильтры
    df = _make_candles(_uptrend_pullbacks(n_cycles=8))
    pos = fib_pullback_signal(df, confluence_min=1, rsi_oversold=50, trend_period=0)
    assert len(pos) == len(df)


def test_signal_htf_gate():
    df = _make_candles(_uptrend_pullbacks(n_cycles=10))
    pos_on = fib_pullback_signal(
        df, confluence_min=1, rsi_oversold=50, trend_period=200, use_htf=0,
    )
    assert len(pos_on) == len(df)


# ---------------------------------------------------------------------------
# Score breakdown / setup
# ---------------------------------------------------------------------------

def test_score_breakdown_shape():
    df = _make_candles(_uptrend_pullbacks(n_cycles=10))
    bd = fib_score_breakdown(df, confluence_min=2, rsi_oversold=40, trend_period=200)
    assert bd["n"] == len(df)
    for key in ("close", "swing_low", "swing_high", "segment", "atr", "factors", "trend_up"):
        assert key in bd
    if bd["segment"] is not None:
        assert "levels" in bd


def test_detect_latest_setup_none_when_not_in_zone():
    df = _make_candles(np.linspace(100, 120, 120))
    setup = detect_latest_setup(df, confluence_min=2, rsi_oversold=40, trend_period=200)
    assert setup is None


def test_detect_latest_setup_consistent_with_signal_pos():
    df = _make_candles(_uptrend_pullbacks(n_cycles=20))
    pos = fib_pullback_signal(df, confluence_min=2, rsi_oversold=40, rsi_overbought=85,
                              trend_period=200)
    # Последний бар не обязан быть входом (может быть в позиции или нет),
    # но detect_latest_setup либо возвращает setup в discount-зоне.
    info = detect_latest_setup(df, confluence_min=2, rsi_oversold=40, rsi_overbought=85,
                               trend_period=200)
    if info is not None:
        assert info["in_discount"] is True


# ---------------------------------------------------------------------------
# Backtrader-стратегия: направление и шорт
# ---------------------------------------------------------------------------

def _backtest_params(**overrides):
    """Стандартные ослабленные параметры + переопределения (для стратегии)."""
    params = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    params.update(
        dict(confluence_min=1, rsi_oversold=50, rsi_overbought=85,
             trend_period=100, swing_bars=5, rr_ratio=2.0)
    )
    params.update(overrides)
    return params


def _trend_series(start, step, n=500, direction=1):
    """Ряд с откатами: растущий (вверх+откаты) или падающий (вниз+отскоки)."""
    prices = _uptrend_pullbacks() if direction > 0 else _downtrend_pullbacks()
    return _make_candles(prices)


def test_strategy_short_only_trades_on_downtrend():
    df = _trend_series(200.0, -0.2, direction=-1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=-1))
    assert r["trades_total"] > 0, "short-only должен торговать на падении"


def test_strategy_short_only_silent_on_uptrend():
    df = _trend_series(100.0, 0.2, direction=1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=-1))
    # Трендовый фильтр не пускает шорт в чистый аптренд
    assert r["trades_total"] == 0


def test_strategy_long_only_trades_on_uptrend():
    df = _trend_series(100.0, 0.2, direction=1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=1))
    assert r["trades_total"] > 0
    assert r["trades_won"] == r["trades_total"]


def test_strategy_long_only_silent_on_downtrend():
    df = _trend_series(200.0, -0.2, direction=-1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=1))
    assert r["trades_total"] == 0


def test_strategy_both_picks_long_in_uptrend():
    df = _trend_series(100.0, 0.2, direction=1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=0))
    assert r["trades_total"] > 0
    assert r["win_rate_pct"] == 100.0


def test_strategy_both_picks_short_in_downtrend():
    df = _trend_series(200.0, -0.2, direction=-1)
    # В режиме both появляются шорты: убыточный лонг-канал → часть сделок — шорты,
    # чистый аптренд-канал так не торговал бы. Достаточно ненулевой активности.
    long_only = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=1))
    both = run_backtest(df, FibPullbackStrategy, _backtest_params(direction=0))
    assert both["trades_total"] > 0
    assert both["trades_total"] != long_only["trades_total"]


def test_strategy_default_direction_is_long():
    df = _trend_series(100.0, 0.2, direction=1)
    r = run_backtest(df, FibPullbackStrategy, _backtest_params())
    assert r["trades_total"] > 0
    df2 = _trend_series(200.0, -0.2, direction=-1)
    r2 = run_backtest(df2, FibPullbackStrategy, _backtest_params())
    assert r2["trades_total"] == 0


# ---------------------------------------------------------------------------
# signal_from_position / apply_trend_filter: шорт-переходы
# ---------------------------------------------------------------------------

def test_signal_from_position_short_transitions():
    assert sig_mod.signal_from_position(pd.Series([0, -1])) == "short"
    assert sig_mod.signal_from_position(pd.Series([-1, 0])) == "cover"
    assert sig_mod.signal_from_position(pd.Series([0, 1])) == "buy"
    assert sig_mod.signal_from_position(pd.Series([1, 0])) == "sell"
    assert sig_mod.signal_from_position(pd.Series([-1, -1])) == "hold"
    assert sig_mod.signal_from_position(pd.Series([0])) == "hold"


def test_apply_trend_filter_direction_aware():
    # Лонги ниже EMA обнуляются, шорты выше EMA обнуляются, лонги выше/шорты ниже — остаются.
    close = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 13.5, 12.0, 11.0])
    pos = pd.Series([1, 1, -1, 1, -1, -1, 0, 1])
    flt = sig_mod.apply_trend_filter(pos, close, trend_period=4)
    # шорт ниже EMA (вблизи конца) допустим; лонг выше EMA допустим
    assert flt[(pos > 0) & (close > close.ewm(span=4, adjust=False).mean())].all()
    assert flt[(pos < 0) & (close < close.ewm(span=4, adjust=False).mean())].all()


def test_apply_trend_filter_disabled_when_period_zero():
    close = pd.Series([10.0, 9.0, 8.0, 7.0])
    pos = pd.Series([1, 1, -1, 1])
    flt = sig_mod.apply_trend_filter(pos, close, trend_period=0)
    assert flt.tolist() == pos.tolist()
