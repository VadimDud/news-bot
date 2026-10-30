"""Tests for the close-filled Bollinger breakout strategy."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.backtest import run_backtest  # noqa: E402
from app.strategies import BollingerBreakoutStrategy, STRATEGIES  # noqa: E402


def _candles(closes, lows=None, start="2024-01-08 05:00", freq="15min"):
    close = np.asarray(closes, dtype=float)
    opens = np.r_[close[0], close[:-1]]
    low = np.minimum(opens, close) - 0.1
    if lows is not None:
        low[-len(lows):] = lows
    high = np.maximum(opens, close) + 0.1
    index = pd.date_range(start, periods=len(close), freq=freq)
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": 1000},
        index=index,
    )


def test_strategy_is_registered_with_requested_parameters():
    item = STRATEGIES["bollinger_breakout"]
    assert item["cls"] is BollingerBreakoutStrategy
    params = {param["key"]: param["default"] for param in item["params"]}
    assert params["bb_period"] == 20
    assert params["bb_stddev"] == 2.0
    assert params["session_start"] == 10
    assert params["session_end"] == 19
    assert params["close_at_eod"] == 1


def test_breakout_is_filled_at_signal_close_and_exits_on_lower_band_stop():
    closes = [100.0] * 20 + [110.0, 110.0, 110.0]
    data = _candles(closes, lows=[95.0])
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0, "close_at_eod": 0, "risk_pct": 1.0},
        cash=100_000,
        commission=0,
    )

    assert result["trades_total"] == 1
    trade = result["trades"][0]
    assert trade["entry_price"] == 110.0
    assert trade["exit_price"] < trade["entry_price"]


def test_weekend_breakout_does_not_open_position():
    data = _candles(
        [100.0] * 20 + [110.0],
        start="2024-01-13 05:00",  # Saturday
    )
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0},
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 0


def test_width_expansion_filter_can_block_breakout():
    data = _candles([100.0] * 20 + [110.0, 110.0, 110.0])
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0, "width_expansion": 1},
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 0
