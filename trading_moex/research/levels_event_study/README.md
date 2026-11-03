# LEVEL-TEST: Do Price Levels Exist in the Data?

## Hypothesis

Trader practice says price sticks at levels: it rejects them, wicks terminate
there, a large resting order absorbs flow at a fixed price, and a level migrates
when a new fractal prints near it but beyond it.

This study asks the prior question before any strategy: **is there a level
effect at all** in the available OHLCV, beyond what random price lines produce?

Answer: **no**, in seven independent formulations.

## Why this matters

`SR-001` (`support_resistance_mtf`) and `ZB-002`/`ZB-004` already rejected level
trading on this data. A negative strategy result leaves open whether the strategy
was built badly or whether the phenomenon is absent. This study separates the two.
The conclusion is the second one.

## Method

Every formulation is compared against a control that is built the same way but
from non-structural prices, matched on count and on distance from structure.
Effect is judged on the ticker as the unit, and on split halves.

## Formulations tested

### 1. Levels as swing clusters vs random bars

Fast test: bars near a swing-cluster level were compared with bars far from any
level. Levels showed 20% less movement (4.34% vs 5.42% over 10 days).

**Rejected as circular.** Bars are selected *because* price is near a level, and
a level is by construction the mean of swing pivots — a centre price passes
through. Control matched on distance-from-line (same levels shifted to the
midpoint between neighbours):

| | Move (10d) | Bar range |
|---|---|---|
| Real levels | 4.106% | 2.400% |
| Midpoint control | 4.078% | 2.367% |
| Ratio | **1.007** | 1.014 |

Five of eleven tickers show *more* movement at real levels.

### 2. Wick tips

Wick tips clustered on 0.827 against 0.837 for random prices from the same
ticker, and real tips beat control in only 3 of 11 tickers.

### 3. Absorption (large order being filled)

Bars with a long tail, a small body and high volume, i.e. the classic "money
changes hands, price does not move" footprint:

| | Forward move (5d) |
|---|---|
| Absorption bars | 3.598% |
| Ordinary high-volume bars | 3.645% |

Ratio 0.987; mean reversal after the absorption bar -0.043%. No footprint.

### 4. Fractal peaks in a flat regime, 4h

Restricting to ranging markets, with fractals as levels: hit rate 0.561, bounce
+0.253%, 9 of 9 tickers, both halves matching, and beating a control of flat-bar
midpoints by +0.081.

**Rejected: the "flat" threshold was forced, not chosen.** The window was
`width < 4 ATR` over 20 bars. At 2.5 ATR the flat share is 0.2% and the sample is
empty (1-11 fractals per ticker); at 3.0 it is 1.9%. Only 4.0 has mass. On
`15min` the same rule yields **0.0% flat bars**, because 20 bars there is 20
hours and the range is almost never under 4 ATR.

So the test measured the length of the lookback window in days, not a market
regime. The apparent edge is an artifact of where the sample first becomes
non-empty.

### 5. Level migration (new fractal near an old level, beyond it, moves the level)

Same data, causal book, migrating vs static levels:

| | Hit rate |
|---|---|
| Migrating | 0.494 |
| Static | 0.495 |
| Difference | **-0.001** |

### 6. Confirmation by touch (a level exists only once other fractals touch it)

Causal, no lookahead: a fractal becomes known only `left+right` bars later; a
level is tradeable after a minimum number of touches; it expires without touches.

First run looked positive: hit 0.517, 9 of 10 tickers, bounce +0.017%.

**Rejected: the control was not matched.** The real levels were filtered by an
activity window (`first_touch <= i <= last_touch`) while the control had no such
filter — different samples, not different levels. Under an identical filter:

| | Hit rate | Bounce |
|---|---|---|
| Confirmed levels | 0.495 | +0.003% |
| Control: random price lines | 0.494 | +0.003% |
| Control: random fractals | 0.494 | -0.003% |

Additionally, a level was active on **83.8% of bars**, so "price is at a level"
carries almost no information by itself.

### 7. Bounce quality measured by departure speed

At a level: fast departures reached 3.78 ATR and broke 59.5% of the time; slow
departures reached 1.21 ATR and broke 94.4%; correlation +0.594.

**Not a level effect.** Random price lines reproduce it exactly (4.31 ATR / 60.0%,
1.07 ATR / 94.0%, correlation +0.595). Speed and distance are read at different
horizons (4 bars vs 16), so the relation is volatility autocorrelation and holds
for any series.

## Conclusion

`rejected`. No formulation produced an effect distinguishable from random price
lines once the control was built the same way.

Three times during this study a result looked positive (0.920, 0.561, 0.517) and
each time failed against a properly matched control. The failures were mine:
a threshold that guaranteed clustering, a regime filter that measured window
length, and an activity filter applied to only one side of the comparison. They
are recorded so the same tests are not repeated.

## What the evidence cannot establish

This study does **not** show that order-book levels do not exist. It shows that
OHLCV does not contain the information. Absorption and resting-order execution
live in the order book and the trade tape; neither is in this dataset. The
mechanism described — a large order that cannot be filled at once, so price sits
while it works off — is not testable here, and its absence here says nothing
about its absence in the market.

## Next

Do not repeat these tests on OHLCV. The only informative extension is tick or
order-book data. If acquired: measure the same absorption footprint (long tail,
small body, high volume, no displacement) on the tape, not on bars.

## Reproduce

One-off event-study scripts were not committed. Numbers are diagnostic. The
shipped `support_resistance_mtf` strategy implements formulation 1 plus the
touch and migration rules; its rejection is `research/sr/`.
