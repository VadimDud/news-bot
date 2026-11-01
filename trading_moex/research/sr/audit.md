# SR-001 Audit Checklist

This checklist records implementation-audit work separately from performance
results. Mark each item with a test name, commit, and run ID when complete.

- [x] long and short stop execution (`test_sr_execution.py::test_long_stop_is_taken_and_leaves_flat_position`)
- [x] long and short target execution (`test_sr_execution.py::test_long_target_is_taken_and_leaves_flat_position`, `test_short_target_is_taken_and_leaves_flat_position`)
- [x] both stop and target touched on one candle — resolves pessimistically to the stop, the TP leg is cancelled (`test_sr_execution.py::test_same_bar_touching_both_stop_and_target_executes_stop_only`)
- [x] gap through stop — fills at the gap open, worse than the stop trigger (`test_sr_execution.py::test_long_gap_through_stop_fills_at_gap_open_not_at_stop_price`)
- [x] breakeven replacement and protection continuity (`test_sr_execution.py::test_breakeven_moves_stop_to_entry_after_r_multiple`, `test_breakeven_is_not_armed_below_the_r_multiple`)
- [x] OCO cancellation and no double exit/reversal (`test_sr_execution.py::test_bracket_is_oco_so_only_one_exit_order_fills_per_trade`, `test_no_reversal_into_opposite_direction_after_stop`)
- [x] EOD and final-bar liquidation without duplicate close (`test_sr_execution.py::test_eod_close_liquidates_without_duplicate_close_orders`, `test_final_bar_liquidation_closes_open_position_once`)
- [x] broker slippage modelled per side (`test_sr_execution.py::test_slippage_worsens_entry_and_pnl`, `test_run_backtest_accepts_slippage_and_lowers_final_value`)
- [x] rejected, margin, and insufficient-cash entry (`test_sr_execution.py::test_entry_is_skipped_when_cash_cannot_cover_minimum_position`)
- [x] retest touch-count filtering and expiration (`test_sr_execution.py::test_retest_zone_requires_enough_touches`, `test_retest_expires_after_max_wait_bars`)
- [x] retest invalidation and one-time consumption (`test_sr_execution.py::test_retest_arms_then_is_consumed_exactly_once`, `test_retest_is_cleared_after_it_fires`, `test_retest_does_not_fire_without_a_volume_confirmed_breakout`, `test_retest_is_invalidated_when_price_closes_through_the_zone_against_the_side`)
- [x] strict pivot confirmation and no lookahead (`test_sr_lookahead.py::test_a_pivot_never_appears_before_its_right_bars_exist`, `test_levels_are_monotonic_when_bars_are_appended_online`, `test_pivot_uses_only_completed_slow_bars_and_ignores_the_live_bar`)
- [x] pivot unavailable until right confirmation bars complete (`test_sr_lookahead.py`)
- [x] timezone-independent slow bucket and warmup (`test_sr_execution.py::test_slow_bucket_and_ledger_are_host_timezone_independent`; `_bucket` normalises via `app.timezones.as_utc`, verified under UTC/Moscow/New York)
- [x] `runonce=False` agreement with the normal run (`test_sr_execution.py::test_runonce_matches_next_based_ledger`)

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
- The retest arm/consume logic lives in `SupportResistanceMtfStrategy._signal`
  and only runs for `scenario_mode` 0 or 2. Mode 1 never arms or consumes a
  retest, so mode-1 results cannot be compared with mode-0/2 retest behaviour.
- Retest expiry is checked against `_retest_bars > retest_max_wait`, so the arm
  survives exactly `retest_max_wait` scans before it is dropped, and a bar that
  matches the retest zone consumes it even when it is the final bar.
- Retest arming requires a *volume-confirmed* breakout beyond the zone
  (`zone_atr_mult * ATR` wide). With a wide ATR the zone is wide too, so a close
  must clear `level + zone`; near-miss closes silently never arm a retest.
- A fired retest is cleared in the same `_signal` call that returns it, so the
  consumption is one-shot and verified without a position being open.
- Breakeven replacement re-creates the whole OCO bracket (cancel stop, cancel
  target, re-submit both). Observed working, but it briefly leaves the position
  unprotected between the cancel and the new submission.
- `run_backtest`/`_setup_cerebro` now accept `slippage` and the SR runner passes
  `ExperimentSpec.slippage` (default 0.0005) through to the broker, so the
  manifest no longer reports `"slippage": "not_modeled"`.
