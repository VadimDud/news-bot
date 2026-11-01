# SR-001 Audit Checklist

This checklist records implementation-audit work separately from performance
results. Mark each item with a test name, commit, and run ID when complete.

- [x] long and short stop execution (`test_sr_execution.py::test_long_stop_is_taken_and_leaves_flat_position`)
- [x] long and short target execution (`test_sr_execution.py::test_long_target_is_taken_and_leaves_flat_position`, `test_short_target_is_taken_and_leaves_flat_position`)
- [x] both stop and target touched on one candle — resolves pessimistically to the stop, the TP leg is cancelled (`test_sr_execution.py::test_same_bar_touching_both_stop_and_target_executes_stop_only`)
- [x] gap through stop — fills at the gap open, worse than the stop trigger (`test_sr_execution.py::test_long_gap_through_stop_fills_at_gap_open_not_at_stop_price`)
- [ ] breakeven replacement and protection continuity
- [x] OCO cancellation and no double exit/reversal (`test_sr_execution.py::test_bracket_is_oco_so_only_one_exit_order_fills_per_trade`, `test_no_reversal_into_opposite_direction_after_stop`)
- [x] EOD and final-bar liquidation without duplicate close (`test_sr_execution.py::test_eod_close_liquidates_without_duplicate_close_orders`, `test_final_bar_liquidation_closes_open_position_once`)
- [x] broker slippage modelled per side (`test_sr_execution.py::test_slippage_worsens_entry_and_pnl`, `test_run_backtest_accepts_slippage_and_lowers_final_value`)
- [ ] rejected, margin, and insufficient-cash entry
- [ ] retest touch-count filtering and expiration
- [ ] retest invalidation and one-time consumption
- [ ] strict pivot confirmation and no lookahead
- [x] pivot unavailable until right confirmation bars complete (`test_sr_lookahead.py`)
- [ ] timezone-independent slow bucket and warmup (naive input timestamps still depend on host timezone)
- [ ] `runonce=False` agreement with the normal run

No new performance claim should be promoted to `promising` or `validated` while
an unchecked item can change the trade ledger materially.

The research runner now records broker positions left open at the end of a run
and fails its sanity checks when any are present. This detects, but does not
resolve, the final-bar and EOD liquidation risks above.

## Findings from the execution audit

- Entries use `broker.set_coc(True)`, so the entry fills at the *signal bar's*
  close and the stop/target bracket is only submitted on the following bar.
  A position therefore has one bar with no protective order. Both the
  "same-candle" and "gap" tests below account for this, but a real exchange would
  reject a fill at a close the strategy had not yet seen.
- The take-profit target is the nearest *confirmed* opposing swing. When the
  entry price sits exactly on a level, that same level can be selected as the
  target at zero distance and the position exits instantly at break-even. The
  audit tests avoid this by pinning a support and a distinct resistance, but the
  production level list can still produce a degenerate target.
- Backtrader's OCO resolves an ambiguous stop-and-target bar pessimistically
  (stop fills, target cancelled). This matches the intended risk-first behaviour
  and is now pinned by a test.
- A wider-than-bracket bar that also re-triggers `_signal()` after the bracket
  exits will immediately re-enter on the same bar's close. Observed in the
  `runonce=False` probe; not blocked by the strategy today.
- `run_backtest`/`_setup_cerebro` now accept `slippage` and the SR runner passes
  `ExperimentSpec.slippage` (default 0.0005) through to the broker, so the
  manifest no longer reports `"slippage": "not_modeled"`.
