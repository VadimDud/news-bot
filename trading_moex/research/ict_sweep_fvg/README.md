# ICT-SWEEP-001: liquidity sweep + fair value gap reversal

## Hypothesis

Price sweeps a prior liquidity pool (session/external level), displaces away
with an imbalance, then returns to the fair value gap (FVG) and continues in the
reversal direction. Enter at the FVG equilibrium on the retest, stop beyond the
sweep extreme, target the opposite pool. The claim under test: this
construction has a positive per-trade edge after costs that survives a
chronological train/test split and does not depend on one parameter cell.

## Origin

The candidate came from the web UI, not from a fresh scan. 44 `ict_sweep_fvg`
runs were recorded on ticker `T` across 5min/60min/2h/4h/1day
(2025-10-02..2026-10-02). The best run reported **+12.21%, PF 2.36, 60% wins**
over 20 trades on `2h` (run id 370). That run was the starting point, not
evidence: 20 trades cannot separate an edge from variance.

## The funnel kills 98% of setups

Per-ticker on `2h` (10 tickers, `2025-08-04..2026-09-11`), counting survivors at
each stage from ~980 sweeps per ticker:

| Stage | Survivors |
|---|---|
| Sweep detected | 100% |
| FVG forms within `retest_bars=3` | **12–16%** |
| Retest of the FVG | 100% of those |
| Reaches `min_rr` ≥ 2.5 | ~65% |
| MSS / kill-zone filters | remainder |
| **Final entries** | **11–23 (2.1%)** |

The dominant filter is the FVG-within-3-bars wait. Widening the wait to 20 bars
roughly doubles entries on all ten tickers. That is why the original 60% win
rate is fragile: it is computed on a tiny, heavily filtered subset.

## Parameter fit is demonstrated, not suspected

The best run's config was split by halves:

| Half | Trades | Wins | Profit factor |
|---|---|---|---|
| First | 10 | 80% | **6.88** |
| Second | 10 | 40% | **1.15** |

An 80% → 40% collapse on ten trades each is the signature of fitting a small
sample. The config was then re-run on five tickers (SBER/GAZP/LKOH/TATN/T):

| Split | Return | Profit factor |
|---|---|---|
| Full | +2.95% | 1.31 |
| Train | +1.22% | 1.24 |
| Test | **−0.80%** | **0.77** |
| Registry default | +0.32% | 1.04 |

## The UI defect that produced the apparent edge

The best config sets `body_ratio_min=0.2` while `body_atr_k=1.0`. The
displacement gate only requires `body_ratio_min` when the
`body ≥ body_atr_k·ATR` test *fails*; with a 1.0-ATR body requirement the ratio
gate is never binding. Changing `body_ratio_min` from 0.2 upward and
`ob_overlap_min` from 0.5 to 2.5 produced no change in results across seven
runs. The UI presents a knob that does nothing at that setting, and the "tuned"
value it displays is inert.

## Widening the funnel does not create an edge

All rows are `2h`, 10 tickers, commission 0.05% + slippage 0.05% per side
(20 bp round trip), `--split-at 2026-04-01`.

| Config | Train | Test |
|---|---|---|
| registry default | — | +0.32% / PF 1.04 |
| `retest_bars=20` | — | +0.37% / PF 1.12 |
| `retest_bars=20, min_rr=1.5` | **−2.68% / PF 0.67** | −0.16% / PF 0.96 |
| `retest_bars=20, min_rr=1.0` | **−2.39% / PF 0.73** | +0.65% / PF 1.17 |

`min_rr=1.0` is the best test cell and the worst train cell: the sign flips
between halves. More entries are not better entries.

## Adaptive mode: relative thresholds

The fixed bar-window is the wrong unit if it is meant to generalise across
tickers: the 2h average range differs about twofold (`SBER 0.236%` vs
`NVTK 0.465%`), so a 3-bar wait expires sooner in ATR terms on a wide-range
name. An `adaptive` mode was added to `_compute_arrays` (registry default
unchanged):

- the FVG/retest window is measured in ATR travelled from the sweep extreme
  (`retest_atr`, default 6.0) instead of a fixed bar count;
- the R:R entry gate is lifted, because the target pool is often closer than
  2.5R and the fixed gate discards valid originals;
- an optional `rr_take_profit` sets the target to `min_rr × risk` (a reachable
  level) rather than the far pool;
- an optional `max_hold_bars` exits on time.

Results, `2h`, 10 tickers, honest train/test (no parameter selected on test):

| Config | Split | Trades | Won | PF | Return |
|---|---|---|---|---|---|
| adaptive | train | 157 | 41% | 0.905 | −0.69% |
| adaptive | test | 108 | 40% | 0.914 | −0.56% |
| adaptive + `rr_take_profit` | train | 147 | 44% | 1.040 | +0.42% |
| adaptive + `rr_take_profit` | test | 100 | 43% | 1.058 | +0.36% |

The only positive-on-both-sides cell (adaptive + reachable target) has a PF of
**1.04–1.06** — barely above break-even and already after costs only because
the target is nearer. Its stability was then tested on three equal time thirds
(`2025-08-04..2026-02-10`, `2026-02-10..2026-08-20`, `2026-08-20..2026-09-11`;
the last row covers three weeks and eleven trades):

| Third | Trades | PF | Return |
|---|---|---|---|
| 1 | 119 | 0.953 | −0.09% |
| 2 | 120 | 1.107 | +0.98% |
| 3 | 11 | 0.243 | −0.83% |

The apparent edge lives entirely in the middle third. The first is flat-negative,
the third is negative, and the "positive" pooled halves were an artefact of
which side of 2026-04-01 the strong stretch fell on.

## Conclusion

`rejected`. The original +12.21% is small-sample fit (80% → 40% wins across
halves) amplified by a UI gate that was inert. Rebuilding the detector on
relative thresholds and a reachable target replaces the broken absolute gate,
and the honest result is PF ≈ 1.0 with no segment that holds. The
registry default was left untouched so this negative result is reproducible;
`adaptive=1` and `rr_take_profit=1` are available for anyone re-checking.

## Limits

- All `2h` data is one year (2025-08 to 2026-09) and a single market regime.
- OHLCV carries no order book or open interest. "Liquidity sweep" and "trapped
  participants" are inferred from wick geometry, not observed. The claim that
  the deeper mechanism exists is untestable on this feed.
- The FVG retest is intrabar at `2h`; whether the 50% equilibrium actually
  filled within a bar is not resolvable, so entry timing has slack the fill
  logic does not model.
- `retest_atr=6.0` and the reachable-target choice were fixed before the
  confirmatory run, not swept. A sweep would invite the same fitting trap the
  original configuration already demonstrated.
- The eleven-trade third is too small to conclude much on its own; it is shown
  for completeness, not as evidence.

## Next step

None on this hypothesis. Sweep-based reversal on OHLCV has now failed its own
funnel test: widening it until it trades often produces PF ≈ 1.0 regardless of
threshold units. Any further sweep study must observe the sweep directly (order
book / tape), which this data does not provide.
