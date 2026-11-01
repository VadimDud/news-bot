"""SR-001 execution audit: stops, targets, gaps, OCO and liquidation behaviour.

Every test drives the real ``SupportResistanceMtfStrategy`` through backtrader
on a controlled price path and inspects the recorded trade ledger.

Environment notes baked into these tests (they are the audit findings):
  * level 100 support, ATR pinned to 1, ``stop_buffer_atr=1`` -> the stop sits
    1 point under the 101.0 entry.
  * a long target needs a *lower* support than the entry, so SUPPORT carries a
    second support at 108 so the nearest opposing swing is a real resistance.
  * entry bars must not touch the level again, otherwise the strategy both
    closes the last bar and re-fires the signal on the same price path.
"""

import backtrader as bt
import pandas as pd

from app.backtest import run_backtest
from app.strategies import STRATEGIES, SupportResistanceMtfStrategy

WARMUP = [(100.0, 100.5, 99.5, 100.0)] * 20
SUPPORT = [(100.0, "support", 1, 5), (108.0, "resistance", 2, 5)]
RESISTANCE = [(100.0, "resistance", 1, 5), (92.0, "support", 2, 5)]
ENTRY = (100.6, 101.4, 100.2, 101.0)
STOP_PRICE = 99.0
TARGET_PRICE = 108.0


def _params(**overrides):
    params = {param["key"]: param["default"] for param in STRATEGIES["support_resistance_mtf"]["params"]}
    params.update({
        "session_start": 0,
        "session_end": 24,
        "close_at_eod": 0,
        "level_touches": 1,
        "scenario_mode": 1,
        "min_rr": 0.0,
        "min_room_r": 0.0,
        "breakeven_r": 100.0,
        "risk_pct": 1.0,
        "stop_buffer_atr": 1.0,
        "atr_period": 2,
        "volume_period": 2,
    })
    params.update(overrides)
    return params


def _frame(bars, start="2024-01-08 05:00", freq="15min"):
    index = pd.date_range(start, periods=len(bars), freq=freq)
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c, "volume": 1000} for o, h, l, c in bars],
        index=index,
    )


class _StubStrategy(SupportResistanceMtfStrategy):
    """Freeze ATR and levels so the signal fires deterministically."""

    params = (("fixed_atr", 1.0), ("fixed_levels", None))

    def __init__(self):
        self._fixed_atr = float(self.p.fixed_atr)
        self._fixed_levels = list(self.p.fixed_levels or [])
        super().__init__()

    def _atr_value(self):
        return self._fixed_atr

    def _update_levels(self):
        if not self._levels:
            self._levels = list(self._fixed_levels)


def _run(bars, levels, atr=1.0, slippage=0.0, cash=1_000_000, **overrides):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(_StubStrategy, fixed_atr=atr, fixed_levels=levels, **_params(**overrides))
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=0.0)
    if slippage:
        cerebro.broker.set_slippage_perc(
            perc=slippage, slip_open=True, slip_limit=True, slip_match=True, slip_out=False,
        )
    cerebro.adddata(bt.feeds.PandasData(dataname=_frame(bars)))
    return cerebro.run(runonce=False)[0]


def test_long_target_is_taken_and_leaves_flat_position():
    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
        (108.6, 109.5, 108.0, 109.0),
    ]
    strat = _run(bars, SUPPORT)
    trades = strat.recorded_trades
    assert trades, "expected the long to be closed by the bracket"
    assert strat.getposition(strat.data).size == 0
    assert trades[0]["exit_price"] >= TARGET_PRICE - 1e-6
    assert trades[0]["pnl"] > 0


def test_long_stop_is_taken_and_leaves_flat_position():
    bars = WARMUP + [
        ENTRY,
        (101.0, 101.1, 99.4, 99.6),
        (99.6, 99.8, 98.0, 98.2),
        (98.2, 98.6, 97.0, 97.4),
    ]
    strat = _run(bars, SUPPORT)
    trades = strat.recorded_trades
    assert trades, "expected the long to be stopped out"
    assert strat.getposition(strat.data).size == 0
    assert trades[0]["exit_price"] <= STOP_PRICE + 1e-6
    assert trades[0]["pnl"] < 0


def test_long_gap_through_stop_fills_at_gap_open_not_at_stop_price():
    gap_open = 96.0
    bars = WARMUP + [
        ENTRY,
        (gap_open, 96.4, 95.6, 95.8),
        (95.8, 96.0, 95.0, 95.2),
    ]
    strat = _run(bars, SUPPORT)
    trades = strat.recorded_trades
    assert trades
    assert trades[0]["exit_price"] <= gap_open + 1e-6
    assert trades[0]["exit_price"] < STOP_PRICE


def test_short_target_is_taken_and_leaves_flat_position():
    bars = WARMUP + [
        (99.4, 99.8, 98.6, 99.0),
        (99.0, 99.1, 97.0, 97.4),
        (97.4, 97.6, 94.0, 94.4),
        (94.4, 94.6, 91.0, 91.4),
        (91.4, 92.0, 90.5, 91.0),
    ]
    strat = _run(bars, RESISTANCE)
    trades = strat.recorded_trades
    assert trades, "expected the short to be closed by the bracket"
    assert strat.getposition(strat.data).size == 0
    assert trades[0]["exit_price"] <= 92.0 + 1e-6
    assert trades[0]["exit_price"] < trades[0]["entry_price"]
    assert trades[0]["pnl"] > 0


def test_bracket_is_oco_so_only_one_exit_order_fills_per_trade():
    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
        (108.6, 109.5, 108.0, 109.0),
        (109.0, 110.0, 108.5, 109.5),
    ]
    strat = _run(bars, SUPPORT)
    completed = [order for order in strat.broker.orders if order.status == bt.Order.Completed]
    assert len(strat.recorded_trades) == 1
    assert strat.getposition(strat.data).size == 0
    assert len(completed) == 2, "one entry + exactly one bracket exit"


def test_final_bar_liquidation_closes_open_position_once():
    bars = WARMUP + [ENTRY, (100.9, 101.4, 100.4, 100.9), (100.9, 101.2, 100.6, 100.8)]
    strat = _run(bars, SUPPORT)
    assert strat.getposition(strat.data).size == 0
    assert len(strat.recorded_trades) == 1
    assert strat.recorded_trades[0]["status"] == "closed"


def test_eod_close_liquidates_without_duplicate_close_orders():
    bars = WARMUP + [ENTRY, (100.9, 101.4, 100.4, 100.9), (100.9, 101.2, 100.6, 100.8)]
    bars = WARMUP + [ENTRY, (100.9, 101.4, 100.4, 100.9), (100.9, 101.2, 100.6, 100.8)]
    strat = _run(bars, SUPPORT, session_end=22, close_at_eod=1)
    assert strat.getposition(strat.data).size == 0
    assert len(strat.recorded_trades) == 1
    completed = [o for o in strat.broker.orders if o.status == bt.Order.Completed]
    assert len(completed) == 2, "one entry + exactly one liquidation, no re-entry"


def test_same_bar_touching_both_stop_and_target_executes_stop_only():
    """Backtrader's OCO resolves an ambiguous bar pessimistically: the stop fills
    first and the take-profit is cancelled, so at most one leg ever executes."""
    bars = [WARMUP[0]] * 60 + [
        ENTRY,
        (101.0, 109.5, 98.5, 104.0),
        (104.0, 104.5, 103.5, 104.0),
        (104.0, 104.5, 103.5, 104.0),
    ]
    strat = _run(bars, SUPPORT)
    first = strat.recorded_trades[0]
    assert first["exit_price"] == STOP_PRICE
    assert first["pnl"] < 0
    executed = [order for order in strat.broker.orders if order.status == bt.Order.Completed]
    stop_fills = [order for order in executed if order.exectype == bt.Order.Stop]
    assert len(stop_fills) == 1, "exactly one stop fill, the TP leg never executes on the same bar"


def test_slippage_worsens_entry_and_pnl():
    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
    ]
    plain = _run(bars, SUPPORT).recorded_trades
    slipped = _run(bars, SUPPORT, slippage=0.005).recorded_trades
    assert plain and slipped
    assert slipped[0]["entry_price"] >= plain[0]["entry_price"]
    assert slipped[0]["pnl"] <= plain[0]["pnl"]


def test_run_backtest_accepts_slippage_and_lowers_final_value():
    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
    ]
    base_params = dict(_params(), fixed_atr=1.0, fixed_levels=SUPPORT)
    result = run_backtest(_frame(bars), _StubStrategy, base_params, cash=1_000_000, commission=0.0, slippage=0.0)
    slipped = run_backtest(_frame(bars), _StubStrategy, base_params, cash=1_000_000, commission=0.0, slippage=0.002)
    assert result["trades_total"] >= 1
    assert slipped["trades_total"] == result["trades_total"]
    assert slipped["final_value"] < result["final_value"]


def test_no_reversal_into_opposite_direction_after_stop():
    bars = WARMUP + [
        ENTRY,
        (101.0, 101.1, 99.4, 99.6),
        (99.6, 99.8, 98.0, 98.2),
        (98.2, 98.6, 97.0, 97.4),
        (97.4, 97.8, 96.5, 97.0),
    ]
    strat = _run(bars, SUPPORT)
    assert strat.getposition(strat.data).size == 0
    assert strat.recorded_trades[0]["pnl"] < 0
    assert strat.recorded_trades[0]["exit_price"] == STOP_PRICE


FLAT_TAIL = [(100.9, 101.4, 100.4, 100.9)] * 4


def _breakeven_bars(follow):
    """A long opened after a long warmup, followed by the bars under test."""
    return [(100.0, 100.5, 99.5, 100.0)] * 60 + [ENTRY] + follow + FLAT_TAIL


def test_breakeven_moves_stop_to_entry_after_r_multiple():
    bars = _breakeven_bars(
        [(101.0, 102.6, 100.9, 102.4), (102.4, 102.9, 100.4, 100.6), (100.6, 100.8, 99.5, 99.6)]
        + [(99.6, 99.8, 99.0, 99.2)] * 3
    )
    strat = _run(bars, SUPPORT, breakeven_r=1.0)
    assert strat.recorded_trades, "the position must be closed"
    trade = strat.recorded_trades[0]
    assert trade["exit_price"] == 100.0, "the stop must have been moved to breakeven"
    assert trade["pnl"] >= 0
    assert strat.getposition(strat.data).size == 0


def test_breakeven_is_not_armed_below_the_r_multiple():
    bars = _breakeven_bars([(100.0, 100.2, 98.9, 99.1), (99.1, 99.3, 97.0, 97.2)])
    strat = _run(bars, SUPPORT, breakeven_r=100.0)
    assert strat.recorded_trades
    trade = strat.recorded_trades[0]
    assert trade["exit_price"] == STOP_PRICE
    assert trade["pnl"] < 0


def test_retest_zone_requires_enough_touches():
    support_1_touch = [(100.0, "support", 1, 1), (108.0, "resistance", 2, 5)]
    support_2_touches = [(100.0, "support", 1, 2), (108.0, "resistance", 2, 5)]

    class _Sig(_StubStrategy):
        seen: list = []

        def next(self):
            super().next()
            if len(self) == 21:
                _Sig.seen.append(self._signal())

    def signal_for(levels, touches):
        _Sig.seen = []
        cerebro = bt.Cerebro()
        cerebro.addstrategy(
            _Sig, fixed_atr=1.0, fixed_levels=levels, **_params(level_touches=touches)
        )
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.setcommission(commission=0.0)
        cerebro.adddata(bt.feeds.PandasData(dataname=_frame(WARMUP + [ENTRY])))
        cerebro.run(runonce=False)
        return _Sig.seen[0] if _Sig.seen else None

    assert signal_for(support_2_touches, 2) is not None
    assert signal_for(support_1_touch, 2) is None


def test_retest_expires_after_max_wait_bars():
    support_2_touches = [(100.0, "support", 1, 2), (108.0, "resistance", 2, 5)]
    far_bars = [(120.0, 120.5, 119.5, 120.0)] * 6

    class _Sig(_StubStrategy):
        flagged: list = []

        def __init__(self):
            super().__init__()
            self._armed = False

        def next(self):
            super().next()
            if self.position:
                return
            if not self._armed and len(self) >= 3:
                self._armed = True
                self._retest = ("long", 100.0)
                self._retest_bars = 0
                return
            if self._armed:
                self._signal()
                _Sig.flagged.append((self._retest, self._retest_bars))

    _Sig.flagged = []
    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        _Sig,
        fixed_atr=1.0,
        fixed_levels=support_2_touches,
        **_params(retest_max_wait=3, scenario_mode=0),
    )
    cerebro.broker.setcash(1_000_000)
    cerebro.broker.setcommission(commission=0.0)
    cerebro.adddata(bt.feeds.PandasData(dataname=_frame(WARMUP + far_bars)))
    cerebro.run(runonce=False)
    assert _Sig.flagged, "the scan must be reached"
    assert _Sig.flagged[0][0] == ("long", 100.0)
    last_retest, last_bars = _Sig.flagged[-1]
    assert last_retest is None and last_bars == 0, "a retest past retest_max_wait must be cleared"


def test_entry_is_skipped_when_cash_cannot_cover_minimum_position():
    bars = WARMUP + [ENTRY, (101.0, 101.4, 100.9, 101.2), (101.2, 101.5, 101.0, 101.3)]
    strat = _run(bars, SUPPORT, cash=50.0)
    assert strat.getposition(strat.data).size == 0
    assert strat.recorded_trades == []
    assert all(order.status != bt.Order.Completed for order in strat.broker.orders)


def test_runonce_matches_next_based_ledger():
    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
        (108.6, 109.5, 108.0, 109.0),
    ]

    def ledger(runonce):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(_StubStrategy, fixed_atr=1.0, fixed_levels=SUPPORT, **_params())
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.setcommission(commission=0.0)
        cerebro.adddata(bt.feeds.PandasData(dataname=_frame(bars)))
        strat = cerebro.run(runonce=runonce)[0]
        return [(t["entry_price"], t["exit_price"], t["pnl"]) for t in strat.recorded_trades]

    assert ledger(runonce=False) == ledger(runonce=True)


def test_slow_bucket_and_ledger_are_host_timezone_independent():
    """The UTC-normalised slow bucket must not shift with the process timezone."""
    import os
    import time

    bars = WARMUP + [
        ENTRY,
        (101.0, 103.0, 100.9, 102.8),
        (102.8, 105.0, 102.7, 104.8),
        (104.8, 109.0, 104.7, 108.6),
        (108.6, 109.5, 108.0, 109.0),
    ]

    def ledger():
        cerebro = bt.Cerebro()
        cerebro.addstrategy(_StubStrategy, fixed_atr=1.0, fixed_levels=SUPPORT, **_params())
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.setcommission(commission=0.0)
        cerebro.adddata(bt.feeds.PandasData(dataname=_frame(bars)))
        strat = cerebro.run(runonce=False)[0]
        return [(t["opened"], t["entry_price"], t["exit_price"], t["pnl"]) for t in strat.recorded_trades]

    original = os.environ.get("TZ")
    try:
        results = []
        for zone in ("UTC", "Europe/Moscow", "America/New_York"):
            os.environ["TZ"] = zone
            time.tzset()
            results.append(ledger())
        assert results[0] == results[1] == results[2]
        assert results[0], "the reference run must produce at least one trade"
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


def _retest_trace(bars, levels, **overrides):
    """Trace ``_signal`` on real (unpinned-ATR) bars with a stable level list."""

    class _Sig(SupportResistanceMtfStrategy):
        trace: list = []

        def next(self):
            self._levels = list(levels)
            signal = self._signal()
            _Sig.trace.append((len(self), signal, tuple(self._retest) if self._retest else None))

    _Sig.trace = []
    cerebro = bt.Cerebro()
    cerebro.addstrategy(_Sig, **_params(**overrides))
    cerebro.broker.setcash(1_000_000)
    cerebro.broker.setcommission(commission=0.0)
    cerebro.adddata(bt.feeds.PandasData(dataname=_frame(bars)))
    cerebro.run(runonce=False)
    return _Sig.trace


BIG_SUPPORT = [(100.0, "support", 1, 2), (108.0, "resistance", 2, 5)]
SCRIPTED_RETEST = (
    [(100.0, 100.5, 99.5, 100.0)] * 70
    + [(109.5, 110.0, 109.2, 109.8), (109.8, 110.0, 109.0, 109.2), (109.2, 109.4, 108.0, 108.2)]
    + [(108.0, 108.2, 107.9, 108.1)] * 4
)


def test_retest_arms_then_is_consumed_exactly_once():
    trace = _retest_trace(SCRIPTED_RETEST, BIG_SUPPORT, scenario_mode=0, level_touches=1, volume_mult=0.5)
    rearmed = [entry for entry in trace if entry[2] == ("long", 108.0)]
    assert rearmed, "a volume-confirmed breakout must arm a long retest"
    fires = [entry for entry in trace if entry[1] == (1, 108.0)]
    assert len(fires) == 1, "the armed retest must fire exactly once"


def test_retest_is_cleared_after_it_fires():
    trace = _retest_trace(SCRIPTED_RETEST, BIG_SUPPORT, scenario_mode=0, level_touches=1, volume_mult=0.5)
    fire_index = next(i for i, entry in enumerate(trace) if entry[1] == (1, 108.0))
    _, _, state_after = trace[fire_index]
    assert state_after is None, "the retest must be consumed in the same scan that fires it"


def test_retest_does_not_fire_without_a_volume_confirmed_breakout():
    trace = _retest_trace(SCRIPTED_RETEST, BIG_SUPPORT, scenario_mode=0, level_touches=1, volume_mult=50.0)
    assert all(entry[2] is None for entry in trace), "no breakout means no armed retest"


def test_retest_is_invalidated_when_price_closes_through_the_zone_against_the_side():
    support_2_touches = [(100.0, "support", 1, 2), (108.0, "resistance", 2, 5)]

    class _Sig(_StubStrategy):
        seen: list = []

        def __init__(self):
            super().__init__()
            self._armed = False

        def next(self):
            super().next()
            if self.position:
                return
            if not self._armed:
                self._armed = True
                self._retest = ("long", 100.0)
                self._retest_bars = 0
                return
            _Sig.seen.append(self._signal())

    _Sig.seen = []
    breakdown = (99.5, 99.8, 96.0, 96.2)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(
        _Sig,
        fixed_atr=1.0,
        fixed_levels=support_2_touches,
        **_params(scenario_mode=0),
    )
    cerebro.broker.setcash(1_000_000)
    cerebro.broker.setcommission(commission=0.0)
    cerebro.adddata(bt.feeds.PandasData(dataname=_frame(WARMUP + [breakdown] * 3)))
    cerebro.run(runonce=False)
    assert _Sig.seen, "the scan must run"
    assert all(signal is None for signal in _Sig.seen), "a close below the zone must not trigger the long retest"
