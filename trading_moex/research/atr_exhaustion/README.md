# ATRX-001 / ATRX-002 / ATRX-003: ATR exhaustion with a reversal candle

## Hypothesis

After price has travelled far from its last swing point — measured in average
true range — a single reversal candle marks exhaustion, and the move retraces.

Two directions were built from the same construction:

- **ATRX-002 (short):** rise of at least `extension_mult` ATR above the most
  recent confirmed swing low, then a bearish candle → sell.
- **ATRX-003 (long):** fall of at least `extension_mult` ATR below the most
  recent confirmed swing high, then a bullish candle → buy.

Both were built and run. Both are rejected. The long mirror is rejected harder.

## Origin

`1day`, 11 tickers, zigzag swing detection (`swing_lookback` 3), daily ATR 14.
An event study on the first candidate form returned, per 3 bars after a bearish
engulfing candle:

| Variant | Mean forward move |
|---|---|
| 2–3 ATR extension | +0.58% |
| 3–4 ATR extension | −0.16% |
| 4+ ATR extension | −0.12% |

The first run of the study reported +0.62% mean over 945 events, a clean
dose-response in the opposite direction to the higher buckets, and looked like
the best result of the sequence: 10 of 11 tickers positive, surviving a 20 bp
cost.

**It was a look-ahead defect.** `_last_swing_low` used a pivot at bar `p` as
though it were known at bar `p`, but a fractal confirms only `k` bars later.
The original also searched back over a range that reached into `len(look)`
future bars. Both errors are the same kind: the swing extreme was read before
the market could have known it.

## The corrected study

`_last_swing_low` was rewritten so the newest usable pivot is
`len(lows) - 1 - look`, searched backward, returning the first valid one. Same
data, same parameters, no other change.

| Metric | Look-ahead (945 events) | Corrected (1834 events) |
|---|---|---|
| Mean forward move | +0.62% | **+0.18%** |
| Win rate | 58.7% | **51.0%** |
| Edge over control | +0.34% | **+0.13%** |
| 2–3 ATR bucket | +0.58% | +0.58% |
| 3–4 ATR bucket | −0.16% | **−0.16%** |
| 4+ ATR bucket | −0.12% | **−0.12%** |
| At 20 bp cost | positive | **−0.016%** |

The dose-response broke: the effect that justified the study was live only
inside the bucket that the defect inflated. Doubling the event count and
collapsing the edge to +0.13% — below any realistic cost — is the signature of
an artefact, not a weak signal.

## ATRX-002: short (full backtest)

Strategy `atr_exhaustion`, `direction=-1`, `weakness=engulf`, `extension_mult`
2.0, `max_hold_bars` 3. `1day`, 10 tickers, commission 0.05%, slippage 0.05%,
cash 100k per ticker.

| Tickers | Trades | Won | Profit factor | Return | Exposure |
|---|---|---|---|---|---|
| 10 | 1253 | 43% | **0.796** | **−7.83%** | 19.7% |

Positive on 1 of 10 tickers. Low exposure (19.7%) means the loss is not a
capital-allocation accident; the per-trade edge is negative.

## ATRX-003: long (full backtest)

Same strategy, `direction=1`. Run `ATRX-003-LONG`, capital 1,000,000 pooled.

| Tickers | Trades | Won | Profit factor | Return | Exposure |
|---|---|---|---|---|---|
| 10 | 1282 | 49% | **0.860** | **−5.90%** | 20.21% |

Fewer trades won than the short (49% vs 43%) yet a larger loss per trade: the
winners are small and the losers are large — the classic profile of buying into
a move that is not finished.

## Week after the signal

Price path over five trading days after entry (instrument return, not short
PnL), 1834 short signals and 1574 long signals, against random bars on the same
tickers.

| Day | Short signal | Random | Long signal | Random |
|---|---|---|---|---|
| +1 | −0.031% | −0.095% | −0.033% | +0.030% |
| +2 | −0.009% | −0.141% | −0.085% | +0.108% |
| +3 | −0.184% | −0.122% | −0.162% | +0.061% |
| +4 | −0.209% | −0.094% | −0.111% | +0.050% |
| +5 | −0.174% | −0.055% | −0.144% | +0.164% |

The short signal's edge over random at day 5 is `−0.12 pp`; it is *worse* than
random on days 1 and 2. The long signal underperforms random on every day, at
`−0.31 pp` by day 5. Both sides collapse once the random baseline is applied.

Week extremes after a short signal: `+3.25%` up (median +2.30%) versus `−3.79%`
down (median −2.64%). The range is ±3%, roughly 25× the edge. **ATR extension
forecasts volatility, not direction.** Entry lands in a high-variance window
whose sign is undetermined, and the spread is paid to enter it.

## Why the short looked positive at all

The short edge of +0.18% is not a signal. Mean buy-and-hold over the sample is
only +4.47%, concentrated in old SBER history, so a mild downward drift can make
a short appear to work. The control run removes it: random shorts return +0.05%
over 3 bars, so the genuine edge is +0.13% — and it flips negative at 20 bp.

The symmetry test is decisive. On identical construction, long returns
`−0.162%` and short returns `+0.184%`; the difference is `−0.35%`. A signal that
forecasts *reversal* should not treat the two directions asymmetrically. This
asymmetry is the market's drift leaking through, not the pattern.

## Conclusion

`rejected`. The strategy is kept in the registry so the result can be
reproduced, not because it works. The look-ahead defect is recorded because it
is the failure mode most likely to be repeated: a swing-extreme study will
always appear to work if the pivot is read before it is confirmed. Any future
construction of this shape must place the pivot at `len - 1 - look`.

The broader lesson — ATR extension is a volatility signal, not a direction
signal — is recorded in `research/README.md`.

## Limits

- `1day` history reaches 2021 for nine of ten tickers; only SBER goes to 2010.
  A single market regime dominates the sample.
- The random-bar control matches tickers and horizon but not the intraday path
  within a bar; daily OHLCV cannot resolve when within the day the entry filled.
- `swing_lookback=3` was fixed after the defect was found, not searched; a
  larger `k` changes the pivot set and was not swept here.
- OHLCV carries no open interest or order book, so "who was trapped" is not
  measurable on this feed.

## Next step

None on this hypothesis. The construction is closed in both directions. Before
any new swing-based study, re-derive the pivot timing from
`research/atr_exhaustion/README.md` so the same defect cannot re-enter.
