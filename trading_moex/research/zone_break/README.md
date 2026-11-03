# ZB-002: Zone Break Continuation

## Status

`rejected` as a tradeable strategy, `promising` as a hypothesis that was never
adequately tested. The baseline is positive but rests on 59 trades, and the
strategy is indistinguishable from a no-trade baseline at the 95% level.

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
