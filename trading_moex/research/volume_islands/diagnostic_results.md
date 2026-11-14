# VOL-ISLAND-001 Diagnostic Results

## Run

The baseline was run on `data/trader_4h.db`, period `4h`, for nine available
tickers: CHMF, GAZP, LKOH, MOEX, MTSS, NLMK, NVTK, T and TATN. SBER was not
included because this database has no SBER/4h rows. The run was diagnostic and
used the existing dirty worktree; no immutable data snapshot was created.

Final run IDs after the causal gap-through-level fix:

```text
20261112T185841Z_VOL-ISLAND-001_a7da830_CHMF
20261112T185844Z_VOL-ISLAND-001_a7da830_GAZP
20261112T185848Z_VOL-ISLAND-001_a7da830_LKOH
20261112T185851Z_VOL-ISLAND-001_a7da830_MOEX
20261112T185854Z_VOL-ISLAND-001_a7da830_MTSS
20261112T185858Z_VOL-ISLAND-001_a7da830_NLMK
20261112T185901Z_VOL-ISLAND-001_a7da830_NVTK
20261112T185905Z_VOL-ISLAND-001_a7da830_T
20261112T185907Z_VOL-ISLAND-001_a7da830_TATN
```

Parameters were the proposed baseline: prior-volume 20th-percentile separator,
minimum island length 2, 60% directional-volume dominance, maximum neutral
share 30%, and horizons 1/2/4/8/12/20 bars. The placebo uses five fixed seeds
(`20261112` through `20261116`) and shuffles candle directions while retaining
timestamps and volumes.

## Results

Pooled 4H event results at the four-bar horizon:

| sample | events | mean directional change | positive events | median correction |
|---|---:|---:|---:|---:|
| real colour | 1,242 | -0.0340% | 46.9% | 0.2791% |
| shuffled colour placebo | 1,237 per seed | varies by seed/ticker | approximately 50% | not used for level selection |

Per-ticker real versus five-seed placebo mean directional change at four bars:

| ticker | real | placebo | real minus placebo |
|---|---:|---:|---:|
| CHMF | -0.0247% | -0.0379% | +0.0132% |
| GAZP | -0.0369% | +0.0655% | -0.1024% |
| LKOH | -0.0086% | -0.1267% | +0.1181% |
| MOEX | -0.0298% | +0.0988% | -0.1286% |
| MTSS | -0.0860% | -0.0035% | -0.0825% |
| NLMK | -0.0605% | +0.1476% | -0.2081% |
| NVTK | +0.0428% | -0.2844% | +0.3271% |
| T | -0.2214% | +0.0977% | -0.3190% |
| TATN | +0.0771% | +0.0939% | -0.0168% |

The real event has a positive difference versus the five-seed placebo mean for
only three of nine
tickers. Continuation rates do not show a stable cross-ticker advantage. The
pooled real result is not evidence of a tradeable edge and costs were not yet
applied.

## Checks

All nine runs passed sorted/unique timestamp checks, confirmation ordering, and
separator exclusion checks. Focused causal tests: 5 passed. Full repository
tests were not clean: 666 passed, 16 pre-existing `pa_levels_strict` failures,
and 1 skipped.

## Extended pullback study

The second diagnostic run used five fixed shuffled-colour seeds
(`20261112` through `20261116`) and evaluated the three pullback levels over
the same four-bar horizon. Pooled real pullback results were:

| pullback | filled events | mean directional change | positive events | median bars to fill |
|---|---:|---:|---:|---:|
| 38.2% | 1,183 | +0.0096% | 47.4% | 2 |
| 50.0% | 1,172 | +0.0154% | 50.4% | 3 |
| 61.8% | 1,156 | +0.0136% | 51.1% | 6 |

These are gross, before commission and slippage. The tiny pooled differences
and approximately 50% positive rates do not support selecting a pullback level.
The gap-through-level rule excludes fills where the candle opens beyond the
level and does not provide a causal executable touch.

## Conclusion

`inconclusive / stop for now` as a trading hypothesis. This baseline does not
demonstrate stable continuation beyond the colour-shuffled control, and the
pooled difference is small relative to likely 4H execution costs. It does not
prove that no volume-island effect exists because the colour proxy is weak and
five placebo seeds were used, but this remains diagnostic rather than a
confirmatory OOS study.

The data audit found no trade tape, bid/ask, aggressor-side, buy/sell-volume,
delta, order-book, or footprint data in either local SQLite database. Therefore
the green/red classification is only a candle-colour proxy. Further OHLCV
parameter optimization is stopped.

Next experiment: acquire or extract true trade-direction volume/order-flow data
for the same 4H windows; do not optimize island thresholds or select a pullback
level on this OHLCV sample.

## Sensitivity gate

The pre-registered 27-cell grid varied separator quantile (10%, 20%, 30%),
dominance threshold (50%, 60%, 70%), and minimum island length (2, 3, 4).
All cells were reported without selecting a best cell. Across the nine tickers,
the mean of ticker-level mean returns ranged from `-0.0629%` to `+0.1185%` at
the four-bar horizon. Grouped by separator quantile, the corresponding means
were `-0.0313%`, `-0.0148%`, and `+0.0604%`. Only 6 of 27 cells had a mean
ticker positive-rate at least 50%.

The sign change across nearby definitions fails the robustness gate. The grid is
diagnostic, not a parameter-selection exercise, and does not justify choosing
the positive cell.

Sensitivity run:

```text
20261112T191207Z_VOL-ISLAND-001-sensitivity
```
