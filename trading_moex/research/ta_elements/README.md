# TA-ELEMENTS: elementary technical-analysis detector library

## Why this exists

Earlier studies (`LEVEL-TEST-001`, `ICT-SWEEP-001`) rejected **strategies** built
on levels and sweeps. They did not prove that price, measured correctly, lacks
structure. This directory takes the opposite approach: build a library of
elementary, individually verifiable detectors — swings, levels, breakouts,
retests, failures — from which systems can later be assembled like LEGO.

The unit of work is a **detector**, not a strategy. A detector is judged on:

1. whether it finds the thing it claims (recognition quality);
2. whether it is *causal* (a bar's event uses only bars at or before it);
3. how price behaves afterward, as a property — not as a PnL.

Trading rules, stops and position sizing are explicitly out of scope here and
belong to a separate layer.

## The build so far

`app/ta_lib.py` implements the first vertical chain:

| Element | Function | Emits |
|---|---|---|
| Swing | `swings` | Confirmed fractal highs/lows |
| Level | `levels` | Horizontal lines from swings, causally merged |
| Breakout | `breakouts` | Fresh close beyond a level |
| Return | `returns_to_level` | Close back through the broken level |
| Retest | `retests` | Touch of the broken level without closing back |
| Failure | `failures` | Return that then undercuts the prior opposite swing |

## Formal definitions

Parameters default to `look=3` (fractal half-width), `merge_atr=0.5`,
`max_age_bars=500`, `retest_wait=10`, `fail_wait=20`.

**Swing.** Bar `j` is a swing high when `high[j] > high[j-look : j]` and
`high[j] >= high[j+1 : j+look+1]` (the first bar of a plateau; mirror for lows).
It is **confirmed at bar `j+look`** — the first bar at which the right-hand
neighbours exist. The event row records `swing_idx = j` (physical bar, for
drawing) and `known_at = index[j+look]` (earliest honest use). `amp_atr` is the
swing's stand-out height over the opposite extreme of the window, in ATR.

**Level.** One horizontal line per confirmed swing at its price. A new swing of
the same side within `merge_atr` ATR of an existing level is folded into it
(running mean, `touches` incremented), *in confirmation order*, so a level never
depends on a swing the market did not yet know. The library emits a row per
update; the catalog keeps the last version per level.

**Breakout.** For each level, the first bar `i` with `close[i] > price` and
`close[i-1] <= price` (mirror for downside), with the level known at `i-1`. If
two near-equal levels fire on the same bar, that is one market fact: the
breakout that cleared by the most is kept (`dist_atr` recorded).

**Return.** A bar after the breakout that closes back through the level within
`retest_wait` bars. A returned long breakout is a *failed breakout candidate*.

**Retest.** A bar whose `low` reaches the level and closes back above it (mirror
for shorts), with no prior close through the level. Mutually exclusive with a
return: the same bar cannot be both.

**Failure.** A returned breakout confirmed as false only when a swing that
existed *before* the breakout is undercut by a close within `fail_wait` bars.
The window is essential: an open-ended search labels ~94% of returns a failure
by sheer passage of time (median 21 bars but p90 of 974). With `fail_wait=20`
the rate settles near 45%.

## Causal contract

Every detector is checked with `assert_causal`, which runs it on the full frame
and on `df.iloc[:cut]` and asserts that events with `known_at < index[cut]` are
byte-identical. Tests in `tests/test_ta_lib.py` exercise this at several cut
points per detector. Two real defects were caught this way during the build:

- `levels` originally merged a swing with *later* swings, so an early level's
  price depended on a future confirmation;
- `breakouts` emitted duplicate events for near-equal levels on the same bar,
  which then leaked into `retests` and `returns` and produced the same bar in
  both.

## Recognition quality

`2h`, six tickers (SBER, T, GAZP, LKOH, MTSS, NVTK), `2025-08..2026-09`,
`python3 scripts/ta_elements_report.py --period 2h --tickers ...`:

| Measure | Value |
|---|---|
| Bars per ticker | ~3051 |
| Swings per ticker | ~620 (316 highs / 316 lows on SBER) |
| Levels per ticker | ~604 (≈76% have `touches > 1`) |
| Breakouts per ticker | ~308 |
| Retests / breakouts | 41.8% |
| Returns / breakouts | 62.5% |
| Failures / returns | 43.8% |
| Median swing amplitude | 2.5 ATR |
| Median breakout overrun | 0.42 ATR |
| Median retest wait | 1 bar |
| Median return wait | 2 bars |

Interpretation: more breakouts are returned (62.5%) than are retested (41.8%)
— on this sample a close beyond a swing level fails more often than it holds.
That is a property of the data, computed causally, and is the first thing a
combination layer should exploit or guard against. It is **not** a trading
signal by itself: it says nothing about what an entry/exit would earn.

## Event catalog

`scripts/ta_elements_report.py --cat-dir <dir>` writes one CSV per ticker and
element (`<TICKER>_swings.csv`, `_levels.csv`, `_breakouts.csv`, `_retests.csv`,
`_returns.csv`, `_failures.csv`) with the full event columns, including
`known_at`. These are the raw material for a chart overlay: plot swings, levels,
and the breakout → retest/return → failure chain to confirm the detectors
recognise the constructions a human would name.

Declared equal but should verify on charts: whether `merge_atr=0.5` merges the
levels you would call "the same level", and whether "failure" matches a visual
false breakout. These are the open recognition questions.

## Limits

- Sweeps are still on OHLCV only: no order book, so "who was trapped" remains
  unobservable. This library detects *price geometry*, not resting liquidity.
- `look=3`, `merge_atr=0.5`, `fail_wait=20` are fixed after diagnosing cost and
  timing, not swept for performance. They are recognition parameters.
- The `2h` sample is one year, one regime.
- `levels` emits updates, not one row per level; consumers must dedupe by
  `level_idx` (the catalog script does).
- Intrabar path is unknown at `2h`; a "retest touch" is a wick fact, not an
  observed fill.

## Next step

Extend the chain with the next primitives — candle confirmations attached to a
level (`engulfing`/`pinbar` at a retest) and compression/expansion (range
contraction before a breakout) — and add a **chart overlay** for visual
confirmation, before any combination is backtested. The immediate open question
is recognition agreement with you on the catalog: does the algorithm mark the
same swings, levels and false breakouts you would?
