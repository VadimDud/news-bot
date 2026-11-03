# DS-001 / SF-001: Departure Speed

## Hypothesis

If price leaves a level fast, the level holds; a slow drift predicts a break.
Turning that into a strategy: a fast one-sided push away from a local extreme is
either (DS-001) the start of a continuation, or (SF-001) exhaustion that fades
back to the origin.

Both were built and run. Both are rejected.

## Origin

The idea came from an event study on confirmed-by-touch fractal levels, `15min`:

- fast departures (top quartile of departure speed, measured in ATR per bar over
  4 bars) reached 3.78 ATR over the next 16 bars and broke the level 59.5% of
  the time;
- slow departures reached 1.21 ATR and broke the level 94.4% of the time;
- correlation between departure speed and eventual excursion: +0.594.

**This was not evidence of a level effect.** Random price lines produced the same
numbers (3.81 ATR / 60.0% vs 1.07 ATR / 94.0%, correlation +0.595). The measure
is volatility autocorrelation: distance and speed are read at different
horizons, so "it started fast, so it went further" holds for any series.

The useful residual was narrower: **fast pushes do not continue most of the
time** (59.5% did not break). That motivated SF-001.

## DS-001: momentum (bets on continuation)

Strategy `departure_speed`. Enters in the direction of a push whose speed
exceeds 0.35x the ticker's own median speed. Exit on ATR stop/target only.

`15min`, 10 tickers, split at `2026-04-01`, commission 0.05%, slippage 0.05%.

| Window | Trades | Won | Profit factor | Realised | Unrealised | Total |
|---|---|---|---|---|---|---|
| full | 194 | 4 | 0.023 | **-22.88%** | +32.67% | +9.79% |
| train | 189 | 4 | 0.024 | -22.4% | +11.4% | -11.0% |
| test | 60 | 0 | 0.0 | -7.8% | +34.4% | +26.7% |

The positive "total" is entirely unrealised PnL on ten open positions, one per
ticker, all short. Exposure is 99.1%: the strategy enters and never exits, so
the figure is a mark-to-market revaluation of held shorts in a falling year, not
a result. Realised PnL is negative in every window and in all 10 tickers.

This is a design defect in the strategy, not a property of the hypothesis: exit
was possible only via stop/target, and with R:R 2.0 against a 1.5-ATR stop the
stops fired unevenly (4 wins in 249 closed trades).

## SF-001: fade (bets on reversal)

Strategy `speed_fade`. Waits one bar after a fast push, then enters against it,
stop beyond the push extreme, target = 1.5R.

`15min`, same costs and split.

| Window | Trades | Won | Profit factor | Net |
|---|---|---|---|---|
| full | 5810 | 2108 | 0.730 | **-65.76%** |
| train | 2934 | 1028 | 0.678 | -50.87% |
| test | 2865 | 1074 | 0.830 | -29.51% |

Realised PnL is negative in all 10 tickers. Win rate 36.3%, average win +835 vs
average loss -655. Unrealised is ~0 because positions are actually closed.

Parameter variation did not rescue it, and the plateaus are not small:

| Configuration | Trades | Win rate | PF | Realised |
|---|---|---|---|---|
| baseline (R:R 1.5, stop 2.5 ATR, hold 48) | 5810 | 36.3% | 0.730 | -65.7% |
| R:R 3.0, stop 1.5 ATR | 6313 | 30.9% | 0.713 | -76.1% |
| R:R 0.8, stop 3.0 ATR, hold 16 | 11000 | 38.7% | 0.551 | -86.5% |

## Conclusion

`rejected` for both.

The event study's 59.5% "does not break" is not an edge. First, it is measured
without costs. Second, and more importantly, it does not distinguish the
*direction* of the return: price not breaking a level can sit still, drift, or
retrace — and the fade has to be right about which. Fading the push trades a
distribution the study never measured.

The result is consistent with the whole session: the apparent signal was real
as a statistic and was not tradeable as a strategy.

## What the evidence cannot establish

- Whether departure speed carries information on a tick or order-book footprint.
  Speed here is derived from OHLCV and is largely volatility autocorrelation.
- Whether the fade loses because the signal is absent or because the stop/target
  geometry on 15-minute bars is dominated by costs. Costs are 0.2% per trade and
  the average win is 0.8%; a geometry sweep at finer cost assumptions would
  separate these, and was not run.

## Next

Do not re-run either strategy on this data. If departure speed is revisited, do
it on daily bars, where the cost-to-move ratio is 5-10x smaller, and report
realised PnL only.

## Reproduce

Clean tree at `7636789` (strategies added in the follow-up commit).

```bash
python -m scripts.research_strategy --strategy departure_speed --study-id DS-001 \
  --period 15min --split full --run-dir artifacts/runs/departure_speed/DS-001-full
python -m scripts.research_strategy --strategy speed_fade --study-id SF-001 \
  --period 15min --split full --run-dir artifacts/runs/departure_speed/SF-001-full
```

Event-study scripts for this idea were one-off and were not committed; their
numbers are recorded above. They are diagnostic, not reproducible from the repo.
