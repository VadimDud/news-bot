# STRICT-005: Diagnostic Results

## Status

Implemented as an opt-in research generator, not registered in live/default.
This is the frozen operational interpretation in [strict_spec.md](strict_spec.md),
not exact recovery of unavailable video parameters. Conclusion: **inconclusive**.
No grid search, no best selection, no OOS claim. Existing uncommitted DIAG-004
changes were preserved; no commit or push performed.

## Evidence

Completed: `20261110T184025Z_PA-LEVELS-STRICT-005_a7da830` in
`artifacts/runs/pa_levels/`. Dirty diagnostic at commit
`a7da830a88c177b207b18eab448fb242c97136f3`.
Exact commands from `trading_moex/`:

```bash
pytest tests/test_pa_levels.py tests/test_pa_levels_execution.py tests/test_pa_levels_strict.py -q
/usr/bin/python3 scripts/research_pa_levels_strict.py --db data/trader_4h.db
```

Harness also executes `/usr/bin/python3 -m pytest` with the same three test
paths. 42 passed, including 19 new strict cases. Initial synthetic run found
a pandas microsecond/nanosecond search boundary mismatch; fixed by normalizing
HTF search index to nanoseconds, without changing strategy thresholds.

Initial diagnostic `20261110T183931Z_PA-LEVELS-STRICT-005_a7da830` stopped before
performance computation on unavailable 4h:SBER. Preserved with exit_status=1,
checks, empty metrics/ledger, input snapshots and traceback in run.log.
Availability handling was clarified before rerun; parameters unchanged.
Completed run has 10 daily and 9 four-hour selected OHLCV snapshots, source
SHA256 hashes, selected-input hashes/date bounds, manifest.json, metrics.json,
checks.json, trades.jsonl.gz and run.log. No unrelated DB tables or secrets.

## Results

Commission and slippage each .05% per side, additive once. Fixed SL/TP and
entry-bar-inclusive bailout for strict; legacy uses unchanged defaults.
HTF mandatory for strict, off for legacy. Daily uses completed Moscow-calendar
weeks; 4h uses conservative completed Moscow-calendar daily aggregates.

| Timeframe / cell | n | Mean net R | Median R | Sum R | PF_R | Max DD R |
|---|---:|---:|---:|---:|---:|---:|
| 1day strict | 5 | -0.181906 | -0.073728 | -0.909531 | 0.151805 | 0.998586 |
| 1day legacy | 105 | -0.225291 | -1.052556 | -23.655601 | 0.698503 | 30.571501 |
| 4h strict | 10 | -0.363504 | -0.278469 | -3.635044 | 0.085039 | 3.635044 |
| 4h legacy | 302 | -0.703633 | -1.177737 | -212.497114 | 0.281001 | 213.011545 |

Strict worst R: daily -0.642939, 4h -1.286237. Daily 1 long/4 shorts;
4h 5 longs/5 shorts. Daily trades all in 2025: GAZP 1, CHMF 2, NLMK 1,
MTSS 1. Calendar/ticker breakdown, descriptive IID bootstrap, largest-winner
removal, bar occupancy and buy/hold price reference are in metrics.json.
DD is exit-ordered additive unit-risk drawdown from zero, NOT portfolio DD.
Different trade counts/exposure prevent treating lower loss as proof of edge.

## Attrition

Counts are setup/level events, not independent market observations. Several
levels can be crossed by one candle. Stop invalidation includes both pending
return and post-return stages; intermediate stage counts are not disjoint.

| Stage / rejection | 1day | 4h |
|---|---:|---:|
| Validated level IDs | 360 | 314 |
| Crossings | 4427 | 3561 |
| Impulse rejection | 3565 | 2834 |
| Breakout volume rejection | 417 | 174 |
| Accepted impulses | 445 | 553 |
| Stop invalidation before signal | 340 | 352 |
| Return timeout | 42 | 87 |
| Return volume rejection | 16 | 22 |
| Accepted returns | 53 | 100 |
| Compression timeout | 20 | 26 |
| Recross rejection | 12 | 40 |
| Accepted compression | 12 | 26 |
| HTF rejection | 7 | 14 |
| Same-bar priority rejection | 0 | 1 |
| Signals | 5 | 11 |
| Pending at end | 3 | 0 |
| Executed | 5 | 10 |

One strict 4h entry rejected at next open beyond target. All other strict
signals executed. Per-ticker counters and legacy execution skips are saved.

## Audit

- No pattern bypass: a single forward state machine requires every stage.
- Sweep uses the same validated level ID/anchor snapshot as breakout, never
  another nearby strong level. Same-bar returns deliberately excluded.
- Stop is breakout candle extreme with fixed breakout-ATR buffer, not an
  arbitrary return-window extreme; later stop touch invalidates setup.
- Append-only snapshots, immutable anchor, separated significant rebounds;
  only latest known snapshot per ID used, strictly before breakout.
- Mandatory HTF fails closed. Explicit calendar/source close boundaries,
  EMA50 warmup, no future median or subsequent-timestamp inference.
- Full signal rows, level histories and HTF directions pass prefix tests at
  midpoint, 3/4 and every strict signal endpoint for all 19 input series.
- Synthetic both-side sequence/stop/target tests, gate failures, premature
  compression, distinct rebound snapshots, timezone equivalence, exact HTF
  boundary, future mutation, missing HTF and entry-bar bailout pass.
- Shared corrected simulator retains legacy defaults. Only new optional
  `bailout_entry_bar=False` keyword is added; strict opts in. Existing gap,
  OCO, costs, no-overlap tests remain green. `checks.all_passed=true`.

## Limits

Five/ten trades cannot establish absence or presence of edge. Data are reused,
not OOS. Calendar boundaries are conservative assumptions, not exchange-verified
session-close timestamps; UTC-naive storage is not reinterpreted as Moscow.
No corporate-action/missing-bar/borrow/funding/dividend audit, no portfolio,
margin, lot sizing or return-on-exposure model. MFE/MAE include whole exit bar
and are bounds. Bootstrap is descriptive, not a valid significance test here.
No extra random controls, no threshold tuning to rescue sparse/negative output.

One next step: audit this frozen interpretation against timestamped annotated
setups supplied by the user before any prospective confirmatory study.
