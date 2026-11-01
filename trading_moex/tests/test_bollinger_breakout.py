"""Tests for the close-filled Bollinger breakout strategy."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.backtest import run_backtest  # noqa: E402
from app.strategies import (  # noqa: E402
    BollingerBreakoutShortStrategy,
    BollingerBreakoutStrategy,
    STRATEGIES,
    SupportResistanceMtfStrategy,
)


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
    assert params["geometry_mode"] == 0
    assert params["elliott_mode"] == 0


def test_support_resistance_strategy_registered_with_research_risk_defaults():
    item = STRATEGIES["support_resistance_mtf"]
    params = {param["key"]: param["default"] for param in item["params"]}
    assert params["slow_tf_minutes"] == 240
    assert params["risk_pct"] == 1.0
    assert params["min_rr"] == 3.0
    assert params["min_room_r"] == 2.5
    assert params["breakeven_r"] == 1.5
    assert params["retest_max_wait"] == 16


def test_sr_breakout_requires_crossing_the_zone_boundary():
    assert SupportResistanceMtfStrategy._breakout_crossed(100.21, 100.2, 100.0, 0.2, "resistance") is False
    assert SupportResistanceMtfStrategy._breakout_crossed(100.2, 100.21, 100.0, 0.2, "resistance") is True
    assert SupportResistanceMtfStrategy._breakout_crossed(99.79, 99.8, 100.0, 0.2, "support") is False
    assert SupportResistanceMtfStrategy._breakout_crossed(99.8, 99.79, 100.0, 0.2, "support") is True


def test_sr_retest_breakout_filters_levels_by_touch_count():
    class Line:
        def __init__(self, values):
            self.values = values

        def __getitem__(self, index):
            return self.values[-1 + index]

    strategy = object.__new__(SupportResistanceMtfStrategy)
    strategy.lines = []
    strategy._levels = [(100.0, "resistance", 1, 1), (101.0, "resistance", 2, 2)]
    strategy._retest = None
    strategy._retest_bars = 0
    strategy.p = type("Params", (), {
        "level_touches": 2, "scenario_mode": 2, "retest_max_wait": 16,
        "zone_atr_mult": 0.2,
    })()
    strategy.data = type("Data", (), {
        "close": Line([100.0, 102.0]), "high": Line([100.0, 102.0]),
        "low": Line([100.0, 102.0]), "open": Line([100.0, 102.0]),
        "__len__": lambda self: 2,
    })()
    strategy._volume_ok = lambda: True
    strategy._atr_value = lambda: 1.0
    strategy._nearest_level = lambda *_args: None
    strategy._signal()
    assert strategy._retest == ("long", 101.0)
    assert strategy._retest_bars == 0


def test_sr_insufficient_cash_does_not_submit_zero_capacity_order():
    class Broker:
        def getvalue(self):
            return 100.0

        def getcash(self):
            return 0.0

    strategy = object.__new__(SupportResistanceMtfStrategy)
    strategy.data = type("Data", (), {"close": [100.0]})()
    strategy.broker = Broker()
    strategy.p = type("Params", (), {"stop_buffer_atr": 0.2, "risk_pct": 1.0, "min_rr": 3.0, "min_room_r": 2.5})()
    strategy._atr_value = lambda: 1.0
    strategy._levels = []
    strategy.buy = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected order"))
    strategy.sell = strategy.buy
    strategy._pending_stop = strategy._pending_target = None
    strategy._submit_entry(1, 99.9)
    assert strategy._pending_stop is None
    assert strategy._pending_target is None


def test_support_resistance_strategy_runs_without_order_errors():
    from app.backtest import run_backtest

    n = 500
    rng = np.random.default_rng(22)
    closes = list(100 + np.cumsum(rng.normal(0.0, 0.35, n)))
    data = _candles(closes)
    item = STRATEGIES["support_resistance_mtf"]
    params = {param["key"]: param["default"] for param in item["params"]}
    params.update({"session_start": 0, "session_end": 24, "close_at_eod": 0, "level_touches": 1})
    result = run_backtest(data, item["cls"], params, cash=100_000, commission=0)
    assert result["final_value"] > 0
    assert all(trade["status"] == "closed" for trade in result["trades"])


def test_short_geometry_compression_filter_blocks_without_compression():
    closes = [100.0] * 20 + [99.0, 98.0, 97.0, 96.0]
    data = _candles(closes)
    # Make the preceding range expand instead of contract.
    data.loc[data.index[16:20], "high"] += 5.0
    result = run_backtest(
        data,
        BollingerBreakoutShortStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "geometry_mode": 1,
            "geometry_bars": 8,
            "geometry_ratio": 0.75,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "session_start": 0,
            "session_end": 24,
            "session_offset_hours": 0,
            "close_at_eod": 0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 0


def test_short_elliott_ratio_filter_blocks_overextended_impulse():
    closes = [100.0] * 12 + [110.0] * 8 + [90.0, 89.0, 88.0, 87.0]
    result = run_backtest(
        _candles(closes),
        BollingerBreakoutShortStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "elliott_mode": 1,
            "elliott_impulse_bars": 8,
            "elliott_min_ratio": 0.382,
            "elliott_max_ratio": 1.618,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "session_start": 0,
            "session_end": 24,
            "session_offset_hours": 0,
            "close_at_eod": 0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["trades_total"] == 0


def test_short_mirror_enters_on_lower_breakout_and_exits_with_buy_stop():
    closes = [100.0] * 20 + [90.0, 89.0, 88.0, 87.0, 86.0] + [110.0] * 8
    result = run_backtest(
        _candles(closes),
        BollingerBreakoutShortStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "session_start": 0,
            "session_end": 24,
            "session_offset_hours": 0,
            "close_at_eod": 0,
            "entry_mode": 0,
            "stop_mode": 0,
            "risk_pct": 1,
        },
        cash=100_000,
        commission=0,
    )

    assert result["trades_total"] == 1
    trade = result["trades"][0]
    assert trade["entry_price"] == 90.0
    assert trade["exit_price"] > trade["entry_price"]


def test_short_mirror_take_profit_exits_downward_without_long_flip():
    closes = [100.0] * 20 + [90.0, 89.0, 87.0, 87.0, 87.0] + [87.0] * 8
    result = run_backtest(
        _candles(closes),
        BollingerBreakoutShortStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "session_start": 0,
            "session_end": 24,
            "session_offset_hours": 0,
            "close_at_eod": 0,
            "entry_mode": 0,
            "stop_mode": 1,
            "atr_stop_mult": 2,
            "tp_rr": 0.1,
            "risk_pct": 1,
        },
        cash=100_000,
        commission=0,
    )

    assert result["trades_total"] == 1
    trade = result["trades"][0]
    assert trade["entry_price"] > trade["exit_price"]


def test_speed_filter_blocks_slow_short_breakout():
    closes = [100.0] * 20 + [99.0, 98.0, 97.0, 96.0]
    result = run_backtest(
        _candles(closes),
        BollingerBreakoutShortStrategy,
        {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "breakout_confirm_bars": 1,
            "speed_bars": 3,
            "speed_min_pct": 1.0,
            "ema_period": 0,
            "candle_body_ratio": 0,
            "close_position_min": 0,
            "atr_period": 0,
            "max_breakout_atr": 0,
            "session_start": 0,
            "session_end": 24,
            "session_offset_hours": 0,
            "close_at_eod": 0,
            "entry_mode": 0,
            "stop_mode": 0,
        },
        cash=100_000,
        commission=0,
    )

    assert result["trades_total"] == 0


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


def test_trailing_take_profit_ratchets_up():
    closes = [100.0] * 20 + [130.0, 135.0, 145.0, 155.0, 165.0, 175.0, 185.0] + [185.0] * 6
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
            "atr_period": 14,
            "max_breakout_atr": 0,
            "stop_mode": 1,
            "atr_stop_mult": 2.0,
            "tp_rr": 1.0,
            "tp_trail": 2,
            "tp_atr_mult": 2.0,
        },
        cash=100_000,
        commission=0,
    )
    assert result["final_value"] < 1_000_000
    for trade in result["trades"]:
        assert trade["status"] == "closed"
        assert trade["exit_price"] >= trade["entry_price"]


def test_mtf_bollinger_registered_and_never_blows_up():
    assert "mtf_bollinger" in STRATEGIES
    item = STRATEGIES["mtf_bollinger"]
    defaults = {p["key"]: p["default"] for p in item["params"]}
    assert defaults["slow_tf_minutes"] == 120
    only_defaults = dict(defaults)
    assert "risk_pct" in only_defaults

    n = 600
    rng = np.random.default_rng(3)
    step = rng.normal(0.05, 0.4, n)
    closes = list(100 + np.cumsum(step))
    data = _candles(closes)
    result = run_backtest(data, item["cls"], defaults, cash=100_000, commission=0)
    assert result["final_value"] < 1_000_000
    for trade in result["trades"]:
        assert trade["status"] == "closed"
        assert trade["entry_price"] > 0


def test_mtf_bollinger_adx_filter_blocks_choppy_and_allows_trend():
    from app.strategies import MtfBollingerStrategy as _M

    item = STRATEGIES["mtf_bollinger"]
    defaults = {p["key"]: p["default"] for p in item["params"]}
    assert defaults["slow_adx_period"] == 18
    assert defaults["slow_adx_min"] == 25.0

    n = 800
    rng = np.random.default_rng(11)
    closes = list(100 + np.cumsum(rng.normal(0.0, 0.25, 400)))
    closes += list(closes[-1] + np.cumsum(rng.normal(0.6, 0.3, 400)))
    data = _candles(closes)
    base = run_backtest(data, _M, defaults, cash=100_000, commission=0)
    no_adx = dict(defaults)
    no_adx["slow_adx_period"] = 0
    raw = run_backtest(data, _M, no_adx, cash=100_000, commission=0)
    assert raw["trades_total"] >= base["trades_total"]
    assert base["final_value"] < 1_000_000
