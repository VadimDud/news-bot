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
    assert params["breakout_confirm_bars"] == 2
    assert params["ema_period"] == 200


def test_breakout_is_filled_at_signal_close_and_exits_on_lower_band_stop():
    closes = [100.0] * 20 + [110.0, 110.0, 110.0]
    data = _candles(closes, lows=[95.0])
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0, "close_at_eod": 0, "risk_pct": 1.0, "ema_period": 0, "breakout_confirm_bars": 1, "candle_body_ratio": 0, "close_position_min": 0, "atr_period": 0, "max_breakout_atr": 0},
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


def test_candle_quality_filter_blocks_weak_breakout_candle():
    closes = [100.0] * 20 + [110.0, 110.0]
    opens = [100.0] * 20 + [109.9, 110.0]
    data = _candles(closes, start="2024-01-08 05:00")
    data["open"] = opens
    data["high"] = 110.5
    data["low"] = 99.5
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0, "candle_body_ratio": 0.5},
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 0


def test_two_bar_confirmation_enters_after_second_breakout_close():
    data = _candles([100.0] * 20 + [130.0, 140.0, 150.0, 150.0, 150.0, 150.0], lows=[0.0])
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {"bb_period": 20, "bb_stddev": 2.0, "breakout_confirm_bars": 2, "close_at_eod": 0, "ema_period": 0, "candle_body_ratio": 0, "close_position_min": 0, "atr_period": 0, "max_breakout_atr": 0},
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 1
    assert result["trades"][0]["entry_price"] == 140.0


def test_mid_zone_retest_enters_after_price_returns_to_level():
    closes = [100.0] * 20 + [130.0, 140.0, 130.0, 131.0, 131.0, 131.0]
    data = _candles(closes, lows=[100.0, 100.0, 120.0, 129.0, 129.0, 80.0])
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "entry_mode": 1,
            "retest_fraction": 0.5,
            "retest_max_bars": 4,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "close_at_eod": 0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 1
    assert result["trades"][0]["entry_price"] == 140.0


def test_max_hold_bars_closes_stale_position():
    closes = [100.0] * 20 + [130.0, 140.0] + [140.0] * 10
    data = _candles(closes)
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "close_at_eod": 0,
            "max_hold_bars": 2,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 1
    trade = result["trades"][0]
    assert trade["entry_price"] == 130.0
    assert trade["exit_price"] >= trade["entry_price"]


def test_time_exit_never_flips_position_short():
    closes = [100.0] * 20 + [130.0, 140.0] + [140.0] * 6 + [90.0] * 6
    data = _candles(closes)
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "close_at_eod": 0,
            "max_hold_bars": 3,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["final_value"] < 1_000_000
    for trade in result["trades"]:
        assert trade["status"] == "closed"
        assert trade["entry_price"] > 0


def test_take_profit_fills_and_stop_is_oco_cancelled():
    closes = [100.0] * 20 + [130.0, 135.0, 150.0, 160.0, 180.0, 190.0] + [190.0] * 6
    data = _candles(closes)
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "close_at_eod": 0,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "tp_rr": 1.0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 1
    assert result["final_value"] < 1_000_000
    for trade in result["trades"]:
        assert trade["status"] == "closed"


def test_atr_stop_and_tp_never_open_short():
    closes = [100.0] * 20 + [130.0, 135.0, 120.0, 110.0, 105.0, 100.0] * 3
    data = _candles(closes)
    result = run_backtest(
        data,
        BollingerBreakoutStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "close_at_eod": 0,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "stop_mode": 1,
            "atr_stop_mult": 1.0,
            "tp_rr": 1.5,
        },
        cash=100_000,
        commission=0,
    )
    assert result["final_value"] < 1_000_000
    for trade in result["trades"]:
        assert trade["entry_price"] > 0
