# RSI-001: RSI Mean Reversion on Daily Candles

## Status

**Rejected.** Weakness is uniform across years rather than concentrated, which
distinguishes it from the breakout rejections. The study also produced a
benchmark finding that changes how the earlier results should be read.

## Why this study exists

ZB-004 and BBS-001 both rejected breakout variants and concluded that the next
attempt should come from a different family. `rsi` is the only genuinely
counter-trend rule in the registry, so it is the cheapest way to test that
conclusion before writing new code.

The diagnostic scan had already run `rsi` on 15min and reported -40% across
2644 trades. That number is not a test of mean reversion — it measures noise.
This study runs it on daily candles, where an RSI swing carries meaning, with
the registry defaults unchanged.

## Setup

`period=1day`, ten tickers, `cash_per_ticker=100_000`, `commission=0.0005`,
`slippage=0.0005`, split at `2024-01-01`. `RSIStrategy` buys below 30 and sells
above 70, with a 1.5-ATR stop and a 2R target, and no trend filter.

## Results

| split | return | PF | trades |
|-------|-------:|----:|-------:|
| full  | -5.21% | 0.769 | 316 |
| train | +0.43% | 1.034 | 123 |
| test  | -5.99% | 0.590 | 191 |

| year | return | PF | trades |
|------|-------:|----:|-------:|
| 2021 | +0.80% | 1.342 | 26 |
| 2022 | -0.25% | 0.906 | 47 |
| 2023 | +0.02% | 0.902 | 20 |
| 2024 | -1.32% | 0.737 | 70 |
| 2025 | -0.57% | 0.838 | 50 |

Profit factor is at or below 1.0 in four of five years, and the one positive
year rests on 26 trades. This is the opposite pattern from `zone_break`, whose
entire result came from 2023: here the weakness is spread evenly, which is what
an absent edge looks like rather than a window artefact.

## The benchmark finding

Running the numbers exposed a problem with how earlier results were read. Mean
buy-and-hold across the ten tickers:

| split | return |
|-------|-------:|
| full  | +6.28% |
| train (2021-2023) | **+32.37%** |
| test  (2024-2026) | **-28.30%** |

The market rose sharply in train and fell in test. Measured against that:

| strategy | train | vs buy&hold | test | vs buy&hold |
|----------|------:|------------:|-----:|------------:|
| zone_break | +3.22% | -29.15% | -1.59% | **+26.71%** |
| rsi | +0.43% | -31.94% | -5.99% | **+22.31%** |

Both strategies look better than buy-and-hold in the test half, and far worse
in the train half. Yearly, both show negative excess in rising years
(2021, 2023) and positive excess in falling years (2022, 2024, 2025).

That is not evidence of skill. Both strategies are in the market only 10-24% of
the time, so their returns are largely decoupled from the index. A mostly-flat
strategy mechanically "beats" buy-and-hold in a falling year and "loses" in a
rising one. The excess numbers are an artefact of low exposure, not selection.

The consequence for the programme: a raw return comparison against zero, which
is what ZB-002 and ZB-004 used, is the wrong test in a dataset split into a
+32% half and a -28% half. It happened to give the right answer for
`zone_break` for the right reason — the 2023 dependence is real — but the
reasoning needs to name exposure explicitly. A strategy that trades 10% of the
time cannot be judged by its total return against an uninvested baseline.

## What the evidence cannot establish

- Whether RSI mean reversion works on a longer sample. 5.7 years with one crash
  half is thin.
- Whether a wider stop or a trend filter would fix it. That would be parameter
  searching on a failed hypothesis.

## Decision

Rejected. Do not trade, do not promote.

## Next Step

Any future study in this repository must report **exposure-adjusted** results:
time in market, and return per unit of exposure, alongside the raw return. The
existing screens and studies compared raw returns over a dataset whose halves
differ by 60 percentage points, so their returns are not comparable across
halves without that correction. Fixing the reporting belongs in the harness,
not in the next strategy, and is the next piece of work.
