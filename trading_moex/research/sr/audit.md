# SR-001 Audit Checklist

This checklist records implementation-audit work separately from performance
results. Mark each item with a test name, commit, and run ID when complete.

- [ ] long and short stop execution
- [ ] long and short target execution
- [ ] both stop and target touched on one candle
- [ ] gap through stop or target
- [ ] breakeven replacement and protection continuity
- [ ] OCO cancellation and no double exit/reversal
- [ ] EOD and final-bar liquidation without duplicate close
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
