# PA-LEVELS-DIAG-004: Execution Audit And Diagnostic Results

Follow-up: [STRICT-005](strict_results.md) addresses the detector mismatches
below in a separate opt-in research generator; this legacy diagnostic and its
results remain unchanged. Strict uses explicit completed weekly/daily HTF.

## Provenance

Completed run: `20261110T182004Z_PA-LEVELS-DIAG-004_a7da830` under
`artifacts/runs/pa_levels/`. Commit `a7da830a88c177b207b18eab448fb242c97136f3`,
dirty worktree recorded explicitly. Diagnostic, NOT true OOS.
Exact command from `trading_moex/`:

```bash
/usr/bin/python3 scripts/research_pa_levels_diagnostic.py --db data/trader_4h.db
pytest tests/test_pa_levels.py tests/test_pa_levels_execution.py -q
```

23 tests passed. Completed run includes manifest.json, metrics.json, checks.json,
trades.jsonl.gz (all cells and all control seeds), run.log and ten compressed
input OHLCV snapshots. Manifest contains source SHA256s, selected-data SHA256s,
exact parameters, versions, dates, dirty status, costs and time contract.
UTC-naive storage remains unchanged; calendar cohorts use Europe/Moscow.
Data are all available daily candles for the ten fixed tickers; SBER extends
to 2010, other histories are shorter. Per-ticker exact bounds are in manifest.

Earlier run `20261110T181626Z_PA-LEVELS-DIAG-004_a7da830` was killed by the
external 120-second timeout. Preserved with FAILURE.md and partial log/snapshots;
final metrics/ledger absent and manifest exit_status null: not a valid run.
Repeat used the same source/parameters and a 600-second timeout, exited 0.
Initial `python` command was unavailable; `python3` worked.

## Audit

- Stop orders incorrectly filled at the old stop through an opening gap.
  Corrected to opening price, tested on longs and shorts.
- Bailout decided from close and filled on that same close. Now schedules the
  next open; resting gap stop has priority. Entry-bar exemption retained.
- Entry beyond target was permitted after a gap. Reject nonpositive target
  distance as well as nonpositive initial risk. Intrabar OCO stays stop-first;
  opening target touch precedes later intrabar stop touch, limit fill is capped.
- Missing HTF previously silently disabled filtering. Now raises ValueError.
  Study explicitly sets use_htf=0, not a fabricated daily HTF substitute.
- Last HTF bar used inferred median duration (or zero with one bar), which
  cannot prove that bar closed. It is unavailable until a subsequent begin.
  Earlier HTF closes remain conservatively delayed until next begin; use at
  LTF begin is conservative, not an exact exchange-close calendar.
- Compression gating depended on whether any false breakout existed anywhere
  in the full dataset, including the future. Removed this global dependency;
  after-return pattern bypass is preserved rather than redesigned.
- Strong-level history retains prior snapshots; sweep events can be associated
  with a nearby strong level different from the swept level. Same-bar sweep
  volume checks use the preceding bar, and pattern entries bypass impulse and
  after-return compression. These semantics are NOT silently redesigned here;
  the frozen flags do not guarantee a pure video-sequence strategy.
- Detector events looking ahead to a return/compression are emitted at the
  return/compression time, not breakout time. Real-data full-row prefix checks
  pass at all video signal endpoints and two extra cuts per ticker.
- Legacy CLI `--oos-split` and per-share `metrics.net/max_dd` are still legacy
  diagnostics, NOT suitable for inference; the new harness does not use them.

## Fixed Cells

Commission and slippage each .05% per side; rr_min=2, HTF off in all cells.
Video compression=1, after_return=1, impulse=.5, bailout=1. Other defaults fixed.
No best selection, no parameter sweep, no currency NET aggregation.

| Cell | n | Mean net R | Sum R | PF_R | Realised max DD R |
|---|---:|---:|---:|---:|---:|
| baseline | 105 | -0.225291 | -23.655601 | 0.698503 | 30.571501 |
| video | 15 | +0.305988 | +4.589813 | 1.604577 | 4.579306 |
| video_no_bailout | 14 | +0.412598 | +5.776370 | 1.705901 | 5.636557 |
| video_no_impulse | 35 | +0.054758 | +1.916523 | 1.090762 | 8.457716 |

Video median -0.533552R, worst -1.360618R; 3 winners, 12 losers, 7 long/8 short.
DD is exit-ordered additive unit-risk accounting including initial zero, not a
marked-to-market portfolio drawdown. No capital/margin/equal-cash model claimed.

## Calendar Cohorts

Entry year in Moscow, not trade-count halves, not OOS:

| Year | Video n | Mean R | Sum R |
|---|---:|---:|---:|
| 2019 | 1 | -1.113404 | -1.113404 |
| 2022 | 2 | -0.806083 | -1.612165 |
| 2023 | 2 | -0.634865 | -1.269730 |
| 2024 | 2 | +2.355644 | +4.711288 |
| 2025 | 5 | +0.848260 | +4.241298 |
| 2026 (partial) | 3 | -0.122491 | -0.367473 |

Other years have no video trades. All cell/year/ticker breakdowns in metrics.

## Concentration And Controls

- Leave-ticker-out mean R ranges +0.049083 (without LKOH) to +0.480956
  (without MOEX). All ten removals recorded, including zero-trade tickers.
- Removing the largest R winner (NVTK +5.295295R) leaves n14, mean -0.050392R,
  sum -0.705481R, PF_R .907073. Removing LKOH's +4.155230R winner leaves mean
  +0.031042R; removing CHMF's +2.731071R winner leaves +0.132767R.
- Removing all three winners leaves n12, mean -0.632649R, sum -7.591782R.
  The largest currency winner was not the largest R winner.
- 2000 bootstrap replicates, seed 20261110: IID-trade percentile range
  [-0.580954, +1.395075] mean R; calendar-year cluster range
  [-0.743044, +1.171372]. Resamples include empty years from 2010 onward;
  unequal ticker coverage and only six active years weaken interpretation.
  These are descriptive intervals, not validated confidence or p-values.
- Random-entry seeds 0..19: mean of seed means -0.004659R, seed mean range
  [-0.600389, +0.653258]R. Video +0.305988R lies within this descriptive range.
  No percentile significance claim. Same ticker, entry year, side, signal
  risk/ATR and target/R per template; execution/costs identical. Realised
  gaps/overlap change counts and risks, recorded per seed in metrics/checks.
  This is random ENTRY, NOT random LEVEL; template matching is retrospective.

## Checks And Limits

checks.json all_passed=true: raw OHLCV order, uniqueness, finite positive prices,
OHLC consistency, nonnegative volume; positive risk/bracket direction, no overlap,
single exits, cost/R identity; full video signal prefix equivalence.
Synthetic tests cover both directions, gap stops, invalid entry targets, stop-first
OCO, next-open bailout, missing HTF and nontrivial EMA last-bar availability.
Terminal positions liquidate at final close. No margin/risk-budget model.
Only the video cell has real-data prefix checks; baseline has synthetic checks.

This does not audit corporate actions, adjusted prices, short borrow, funding,
dividends, tradability/lot sizing or timestamp provenance from the exchange.
No 4h rerun: priority was a verified compact daily diagnostic. No portfolio
returns: buy/hold price returns and bar occupancy are descriptive references,
not return-on-exposure or equal-cash evidence. Level/touch/zone/target-origin
metadata not exposed by the generator are explicitly null/unknown in ledgers;
MFE/MAE include full exit bar and are bounds, not exact pre-exit excursions.

**Conclusion: inconclusive.** Positive video sample mean is concentrated and
does not survive removal of its largest R winner. Neither this nor n15/n16
proves presence or absence of edge. No live promotion or best-cell choice.

**One next step:** collect a genuinely uninspected, timestamp-bounded forward
sample under this frozen specification before any confirmatory inference.
