# VOL-001: Does Volume Predict Continuation or Reversal?

## Hypothesis

A breakout or a fast push on high volume should continue; on low volume it
should fail. The question was put plainly: volume on the move — continuation or
reversal?

Answer: **neither, consistently.** The sign of the effect flips between
timeframes, and on `15min` it does not clear costs.

## Method

Event study, no strategy wrapper, so costs can be subtracted explicitly. For a
breakout of the previous 20-bar high/low at bar `i`:

- volume z-score of bar `i` against its own 20-bar mean/std;
- outcome over the next 16 bars (`15min`) or 10 bars (`1day`), in the direction
  of the break;
- cost deducted per trade: 0.05% commission + 0.05% slippage, on entry and exit
  = 0.2% total.

High volume is `z >= 1.5`, low volume is `z <= 0`.

Controls: (1) placebo — volume z-scores permuted across bars, so the split is
made on noise; (2) split-half stability; (3) the ticker as the unit of evidence.

## Results: 15min, 10 tickers

| Volume bucket | Continuation | Move over horizon |
|---|---|---|
| Low (z <= 0) | 42.5% | -0.201 ATR |
| High (z >= 1.5) | 46.7% | -0.142 ATR |
| Difference | **+4.2 pp** | **+0.059 ATR** |

Seven of ten tickers favour high volume. The direction matches the conventional
claim. But net of 0.2% costs:

| Half | Difference |
|---|---|
| H1 | +0.060% |
| H2 | -0.026% |

**The sign flips between halves**, and only 3 of 10 tickers are positive in both.
Placebo gives -0.023%, so the real split is not noise — but it is a third of the
cost and unstable.

## Results: 1day, 8 usable tickers

Daily bars, where the move is 5-10x the cost:

| Volume bucket | Net per trade |
|---|---|
| High (z >= 1.5) | +0.309% |
| Low (z <= 0) | +0.549% |
| Difference | **-0.240%** |

Three of eight tickers favour high volume; both halves are negative (-0.65%,
-0.17%). On daily bars **high-volume breakouts are worse**, the opposite of the
intraday result.

Note: only 8 tickers reach the sample threshold on daily bars, and `SBER` alone
contributes 504 of ~1800 events because it has history back to 2010 while the
other nine start in 2021. The daily sample is thin and unbalanced.

## On fast departures

Same question at a fast push away from a local extreme: continuation is 46.5% on
low volume and 47.2% on high volume. A 0.7 pp difference is noise. Volume adds
nothing here.

## Conclusion

`rejected` as a signal.

The three tests agree on one thing only: volume is not a stable predictor on
these instruments at these timeframes. Intraday it points the conventional way
but is too small to trade; on daily bars it points the other way.

This independently reproduces a result already in the repo: `zone_break` with a
volume filter (`volume_mult`) lost net profit, and the shipped `zone_break`
defaults set `strong_candle` but not volume. The negative sign here is that same
finding measured directly.

## What the evidence cannot establish

- Why the sign flips. A plausible reading is that on `15min` high volume marks
  real order flow while on daily bars an outsized volume bar is more often a
  one-off block trade or an index/settlement event than sustained interest.
  Nothing here tests that.
- Whether volume matters on shorter horizons (1-5 min), where the effect could
  be larger relative to cost. Data exists for 1 ticker only (`1min`, 297k rows,
  one instrument), which is not enough to generalise.
- Whether the result holds on other instruments. Ten MOEX names over one year is
  a single market regime.

## Next

If volume is revisited: use the `1min` single-ticker set purely to estimate
effect size relative to cost at high frequency, then decide whether broader
high-frequency data is worth acquiring. Do not re-run on `15min` or `1day`.

## Reproduce

One-off event-study scripts were not committed; numbers recorded above are
diagnostic. No strategy was added to the registry for this study.
