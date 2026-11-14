# VOL-ISLAND-001

## Hypothesis

On 4H candles, a completed island with at least 60% dominance of green or red
volume predicts directional continuation more often than reversal. The study
also estimates the distribution of adverse correction before continuation.

Colour is an OHLCV proxy (`close > open` or `close < open`), not true aggressive
buy/sell volume. This study must not be promoted to live trading.

## Causal definition

An island is a consecutive sequence of non-separator bars. A separator is a bar
whose volume is below the 20-bar prior-volume 20th percentile. The separator
confirms the preceding island; entry observations start at the next bar open.
The island requires at least two bars, 60% directional-volume dominance, and at
most 30% neutral volume. All rolling features use prior bars only.

## Measurements

For horizons 1, 2, 4, 8, 12 and 20 bars, report MFE, MAE, net directional
change, correction percentage relative to the island move and range, correction
in ATR, continuation/reversal rates, and censoring. Compare immediate entry with 38.2%, 50% and 61.8% pullbacks,
boundary breakout and breakout-retest only after the event-study baseline is
complete.

## Protocol

Use the common `research/protocol.md`: chronological train/validation/test/
forward periods, explicit costs, controls using shuffled colours and matched
random events, no overlapping-event double counting, and complete run artifacts.
The existing `volume_effect` result is a prior negative baseline, not a reason
to skip this distinct sequence hypothesis.

## Stop rule

Stop if the colour-shuffled control matches the real result, or if the effect
does not survive costs and chronological test/forward evaluation. End the
report with exactly one next experiment or a reason to stop.
