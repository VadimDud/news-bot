# ZB: Zone Break Continuation

## Status

**Rejected.** ZB-002 found that the 15-minute baseline rested on 59 trades,
which was too few to separate +1.16% from zero, and named more data as the
blocker. ZB-004 supplied that data: the same unchanged configuration on 5.7
years of daily candles (250 trades) is positive overall but **negative in the
largest half of the sample** and negative in the final two years. The edge does
not survive the test it was waiting for.

The unresolved blocker in ZB-002 was statistical power, not the sign of the
result. Once that blocker was removed, the sign went with it.

## Hypothesis

A 15-minute close breaking the prior 20-bar high (long only) with a "strong
candle" body (>= 1x ATR and >= 60% of bar range) continues far enough to reach
2R before the 1.5-ATR stop, after 0.05% commission and 0.05% slippage per side.

The mechanism claimed is momentum continuation after a range breakout, not mean
reversion. A break of a zone that closes outside it with an unusually large body
should attract follow-through rather than fade.

Falsifiable prediction: pooled profit factor above 1.0 and positive pooled
return in **both** chronological halves at realistic cost, on a sample large
enough for the estimate to be distinguishable from zero.

## Setup

- Strategy: `zone_break` (registry defaults, `direction=1` long only).
- Params: `zone=20`, `strong_candle=1`, `atr_k=1.0`, `body_ratio_min=0.6`,
  `atr_period=20`, `atr_stop_mult=1.5`, `rr_ratio=2.0`, `risk_pct=1.0`,
  `exit_zone=0`.
- Data: `data/trader_4h.db`, period `15min`, ten tickers, `cash_per_ticker=100_000`.
- Window: full `2025-08-28 .. 2026-09-21`; split at `2026-04-01` into
  train/test, never used for parameter selection.
- Costs: `commission=0.0005`, `slippage=0.0005` per side.
- Timezone contract: candles are UTC-naive in storage, market logic is
  `Europe/Moscow`; recorded in each manifest.

## Runs

All three runs are from clean commit `ba4217e`, `dirty: False`, checks passed,
ledger count matches metrics.

| split | return | PF | trades |
|-------|-------:|----:|-------:|
| full  | +1.16% | 1.325 | 59 |
| train | +0.09% | 1.222 | 8 |
| test  | +1.08% | 1.343 | 51 |

Artifacts: `artifacts/runs/zone_break/ZB-002-{full,train,test}-*` (local,
gitignored), each with `manifest.json`, `metrics.json`, `checks.json`,
`trades.csv.gz`.

## Why this is rejected despite a positive return

**The sample cannot distinguish the result from luck.** 59 trades with a 1.325
PF and a 1% risk per trade produces a return of +1.16% over thirteen months on
100k per ticker. That is within the noise band of a no-trade baseline.

**Train is nearly empty and breaks at higher cost.** 8 trades in train is not a
validation set; it is an anecdote. At `commission=0.001, slippage=0.001` train
turns negative (-0.03%).

**Six of ten tickers positive is consistent with chance.** Per-ticker:

| ticker | return | PF | trades |
|--------|-------:|----:|-------:|
| LKOH | +5.76% | 2.26 | 10 |
| GAZP | +1.46% | 1.83 | 4 |
| NVTK | +4.50% | 2.84 | 7 |
| TATN | +3.29% | 1.37 | 14 |
| MOEX | +2.05% | inf | 1 |
| NLMK | +0.68% | 1.11 | 9 |
| T | -0.04% | 0.98 | 4 |
| SBER | -1.30% | 0.00 | 1 |
| CHMF | -4.77% | 0.44 | 9 |
| MTSS | 0.00% | 0.00 | 0 |

MOEX rests on a single trade, SBER on a single losing trade, MTSS never
triggered. The two largest contributors (LKOH, NVTK) have 10 and 7 trades.

**The parameter surface is flat, which cuts both ways.** From the diagnostic
scan at realistic cost: `zone=10 +0.76%`, `zone=15 +0.95%`, `zone=20 +1.16%`,
`zone=30 +1.32%`, `zone=40 +1.17%`; `body_ratio 0.4/0.5/0.6/0.7` gives
`+1.75/+1.69/+1.16/+0.89%`; `rr 1.5/2.0/2.5/3.0` gives
`+0.04/+1.16/+1.03/+0.75%`. A genuine edge usually survives a smooth surface,
but so does a small-sample artefact when all variants share the same ~50-70
trades. The near-zero result at `rr=1.5` is the real warning: the strategy needs
a wide target to look positive, which is exactly the profile of a few lucky
large winners.

## What the evidence cannot establish

- That the edge is positive at all. The confidence interval on 59 trades spans
  zero.
- Anything about out-of-sample behaviour. The "test" half was never held out
  from the diagnostic scan that nominated this strategy, so it is contaminated
  by the same selection.
- That the 15min/ten-ticker universe generalises. Ten liquid MOEX names over
  thirteen months is one market regime.

## Next Experiment

The blocker is statistical power, not parameter tuning, so the next step is not
another sweep on this data. Extend the candle history to at least five years and
re-run the identical `ZB-002` configuration through
`python -m scripts.research_strategy --strategy zone_break`, then check whether
pooled PF stays above 1.0 in both halves with trade count in the hundreds. If
the data cannot be extended, stop: repeating the sweep on this sample only
manufactures overfitting.

---

# ZB-004: Same Configuration on Daily Candles

## Why this run exists

ZB-002 closed with "extend history to five years and re-run the identical
configuration". This is that run. Nothing changed except the timeframe: no
parameter tuning, no re-selection, no new filters.

## Setup

Identical to ZB-002 in every parameter. Only two fields differ:

- period `1day` instead of `15min`;
- `split_at=2024-01-01` instead of `2026-04-01`.

The split moved because the default boundary would have put 243 of 250 trades
in train and left 6 in test, which tests nothing. `2024-01-01` gives 161 train
and 82 test trades.

Data: daily candles `2021-01-04 .. 2026-09-11`, ten tickers. The set is worth
noting — daily history starts in 2021, not 2010; only SBER reaches back to 2010,
so its `+17.14%` rests on a longer window than the other nine.

## Runs

Clean commit `b54be12`, `dirty: False`, `sanity_checks` correctly **fails** all
three runs because real positions remain open when the series ends (MTSS, SBER
on full/test; TATN on train). Those open positions are listed in
`checks.json` and were kept visible rather than closed artificially at the last
bar, which would have invented an exit price.

| split | return | PF | trades |
|-------|-------:|----:|-------:|
| full  | +1.85% | 1.102 | 250 |
| train (2021-01 .. 2023-12) | +3.22% | 1.281 | 161 |
| test  (2024-01 .. 2026-09) | **-1.59%** | **0.766** | 82 |

Per calendar year, same configuration:

| year | return | PF | trades |
|------|-------:|----:|-------:|
| 2021 | -0.34% | 0.895 | 40 |
| 2022 | +0.08% | 1.072 | 10 |
| 2023 | **+2.48%** | **1.720** | 56 |
| 2024 | +0.26% | 0.678 | 22 |
| 2025 | **-1.12%** | **0.469** | 27 |

## What this establishes

**The full-period positive return is one good year.** 2023 alone carries it.
Every year after 2023 is worse than the one before, ending at PF 0.469. A
strategy whose out-of-sample half is negative at PF 0.766 does not have a
forward edge; it has a backtest.

**The hypothesis is falsified on its own terms.** ZB-002 declared the success
criterion as pooled PF above 1.0 in *both* halves. Test delivers 0.766.

**SBER carries the result, and it carries it unfairly.** SBER contributes
`+17.14%` of a `+1.85%` pooled total, because it is the only ticker with 2010
history and thus competes on 68 trades from a different sample than the rest.
Excluding SBER, the pooled figure is negative. That is not a strategy property;
it is an artefact of uneven history depth.

## What the evidence cannot establish

- Whether the strategy ever worked before 2021. Only SBER has that history, so
  it cannot be checked on a representative cross-section.
- That 2023 was driven by continuation rather than the 2023 MOEX rally. The
  concentration of the whole edge into one year is consistent with a regime
  effect, not a repeatable mechanism.

## Decision

Rejected. Do not trade, do not promote, do not tune further on this sample.
Parameter tuning on a strategy that fails out of sample in its own test is
overfitting by construction.

## Next Experiment

None for this strategy. A defensible next step for the *programme* is to check
the screened negative results for the same year-concentration pattern
(`bollinger_breakout_short` is the obvious suspect, with its gain concentrated
in MOEX/MTSS/CHMF): if several strategies earn their whole return in 2023, the
shared signal is the market year, and the honest conclusion is that these
breakout rules have no edge on MOEX in this dataset. If instead the next study
must be attempted, it should be a fundamentally different family (e.g. carry,
mean reversion at a tested level) rather than another breakout variant.
