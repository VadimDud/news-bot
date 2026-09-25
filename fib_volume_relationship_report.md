# Fibonacci / Volume Relationship: `T` / `15min`

## Method
- Data: 38144 candles, `2024-09-24 09:45:00` to `2026-09-24 12:00:00`.
- Fib anchors: causally confirmed fractal pivots with `swing_bars=10`; this matches the bot's `fib_pullback` methodology.
- Tested levels: 38.2%, 50.0%, 61.8%, 78.6% of the latest confirmed swing range.
- A level is considered near when the retracement fraction is within +/- 0.050 (5.0 percentage points).
- Volume event: SMA(20) ratio >= 2.5 OR Z-score(50) > 2.5.
- The golden zone is 50.0-61.8%, the same entry zone used by the bot. Adjacent events are not de-clustered.

## Result
- Volume events: **3896**; complete forward outcomes: **3895**.
- Valid confirmed Fib swing context: **37990** bars (99.6%).
- Golden-zone volume-event rate: **6.02%** (202/3355).
- Valid-swing-away event rate: **11.96%** (3157/26407).
- Golden-zone minus away event-rate difference: **-5.93%**, bootstrap 95% CI [-6.85%, -5.05%].
- Golden-zone continuation rate: **31.19%**; away: **36.25%**.
- Continuation-rate difference: **-5.06%**, bootstrap 95% CI [-11.56%, 1.54%].

## Breakdown
| Fib context | All bars | Volume events | Event rate | Mean ratio | Continuation | Flat | Reversal | Mean 60m close change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Golden zone 50-61.8% | 3355 | 202 | 6.02% | 4.27x | 31.19% | 33.17% | 35.64% | -0.03% |
| Near Fib level | 8228 | 523 | 6.36% | 4.33x | 36.14% | 27.34% | 36.52% | -0.03% |
| Valid swing, away from level | 26407 | 3157 | 11.96% | 4.76x | 36.25% | 32.32% | 31.43% | 0.04% |
| No confirmed swing | 154 | 14 | 9.09% | 27.51x | 28.57% | 50.00% | 21.43% | 0.64% |

### Individual Levels
| Nearest Fib level | All bars near level | Volume events | Event rate | Continuation | Flat | Reversal | Mean 60m close change |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 38.2% | 2814 | 158 | 5.61% | 35.44% | 36.08% | 28.48% | -0.05% |
| 50.0% | 2632 | 177 | 6.72% | 30.51% | 32.77% | 36.72% | -0.01% |
| 61.8% | 2914 | 178 | 6.11% | 35.96% | 22.47% | 41.57% | -0.03% |
| 78.6% | 2758 | 177 | 6.42% | 37.85% | 23.73% | 38.42% | -0.03% |

## Interpretation
- A relationship is plausible only if both event frequency and forward reaction differ from the away-from-level control; a high raw count near Fib is not evidence by itself.
- Individual-level rows are disjoint: each bar is assigned to its nearest Fib ratio, only when it is within the selected tolerance.
- The bootstrap interval is descriptive, not a multiple-testing-adjusted significance test. It does not remove intraday seasonality, news effects, or overlapping events.
- Small samples, especially for a single level, should not be used as a standalone trading rule.

## Volume Events With Fib Context
| Timestamp | Fib context | Nearest level | Retracement | Volume ratio | Reaction | 60m change | Outcome |
|---|---|---:|---:|---:|---|---:|---|
| 2025-03-31 07:00 | No confirmed swing | n/a | n/a | 297.89x | Flat / fading | 0.490% | Position building in range |
| 2026-04-17 10:00 | Valid swing, away from level | n/a | -188.7% | 110.20x | Flat / fading | 0.196% | Position building in range |
| 2025-11-10 07:00 | Valid swing, away from level | n/a | -476.5% | 64.99x | Flat / fading | -0.073% | Position building in range |
| 2026-06-14 18:45 | Valid swing, away from level | n/a | -962.5% | 64.91x | Impulse / continuation | 0.512% | True breakout |
| 2024-11-06 10:00 | Valid swing, away from level | n/a | -462.2% | 50.43x | Reversal | 0.415% | Liquidity sweep / reversal |
| 2025-06-01 10:00 | Valid swing, away from level | n/a | 406.5% | 48.18x | Flat / fading | -0.138% | Position building in range |
| 2025-05-10 18:30 | Valid swing, away from level | n/a | 242.9% | 47.08x | Reversal | 2.702% | Liquidity sweep / reversal |
| 2025-07-07 07:00 | Valid swing, away from level | 78.6% | 71.1% | 45.17x | Impulse / continuation | -0.118% | True breakout |
| 2026-04-17 09:45 | Valid swing, away from level | n/a | -5.0% | 40.16x | Impulse / continuation | 2.124% | True breakout |
| 2025-03-31 06:45 | No confirmed swing | n/a | n/a | 39.23x | Impulse / continuation | 2.260% | True breakout |
| 2026-05-04 07:00 | Valid swing, away from level | n/a | -114.9% | 39.02x | Impulse / continuation | 0.287% | True breakout |
| 2025-05-17 18:00 | Valid swing, away from level | n/a | -148.1% | 34.32x | Impulse / continuation | 0.939% | True breakout |
| 2026-08-24 07:00 | Valid swing, away from level | n/a | 276.3% | 34.29x | Flat / fading | 0.159% | Position building in range |
| 2025-01-09 10:00 | Valid swing, away from level | n/a | -41.1% | 32.79x | Flat / fading | -0.517% | Position building in range |
| 2025-06-29 16:15 | Valid swing, away from level | 38.2% | 0.0% | 32.42x | Reversal | -0.092% | Liquidity sweep / reversal |
| 2026-08-31 07:00 | Valid swing, away from level | 78.6% | 95.5% | 31.72x | Reversal | 0.361% | Liquidity sweep / reversal |
| 2026-02-03 10:00 | Valid swing, away from level | n/a | -385.4% | 31.41x | Impulse / continuation | 0.405% | True breakout |
| 2025-07-28 07:00 | Valid swing, away from level | n/a | -24.4% | 30.69x | Reversal | 0.167% | Liquidity sweep / reversal |
| 2026-04-06 07:00 | Valid swing, away from level | n/a | -125.8% | 30.31x | Flat / fading | -0.081% | Position building in range |
| 2026-05-18 07:00 | Valid swing, away from level | 38.2% | 2.4% | 28.40x | Reversal | -0.187% | Liquidity sweep / reversal |
| 2025-08-25 07:00 | Golden zone 50-61.8% | 50.0% | 52.6% | 25.99x | Impulse / continuation | -0.077% | True breakout |
| 2025-03-16 16:00 | Valid swing, away from level | n/a | -158.8% | 24.87x | Impulse / continuation | 0.919% | True breakout |
| 2024-09-30 10:00 | Valid swing, away from level | n/a | -141.0% | 24.43x | Impulse / continuation | -0.075% | True breakout |
| 2026-03-16 07:00 | Valid swing, away from level | n/a | -877.8% | 23.81x | Flat / fading | -0.100% | Position building in range |
| 2025-12-29 07:00 | Near Fib level | 78.6% | 81.3% | 23.74x | Impulse / continuation | 0.154% | True breakout |
| 2026-07-05 10:00 | Valid swing, away from level | 38.2% | 14.5% | 23.73x | Impulse / continuation | 0.134% | True breakout |
| 2025-12-22 07:00 | Near Fib level | 38.2% | 33.3% | 23.42x | Flat / fading | 0.119% | Position building in range |
| 2026-08-17 07:00 | Valid swing, away from level | n/a | 151.1% | 23.06x | Flat / fading | 0.063% | Weak move without breakout |
| 2025-10-13 07:00 | Valid swing, away from level | n/a | -218.2% | 22.26x | Impulse / continuation | 0.144% | True breakout |
| 2026-04-24 13:30 | Valid swing, away from level | n/a | 317.9% | 21.99x | Flat / fading | -0.093% | Position building in range |
| 2026-05-21 10:00 | Valid swing, away from level | n/a | 233.3% | 21.75x | Flat / fading | -0.200% | Weak move without breakout |
| 2025-09-08 07:00 | Valid swing, away from level | n/a | -95.7% | 21.71x | Flat / fading | 0.084% | Position building in range |
| 2025-09-01 07:00 | Valid swing, away from level | n/a | -13.9% | 21.63x | Impulse / continuation | 0.168% | True breakout |
| 2026-09-21 07:00 | Valid swing, away from level | n/a | -70.0% | 21.63x | Impulse / continuation | 0.655% | True breakout |
| 2025-07-14 07:00 | Near Fib level | 78.6% | 81.1% | 21.55x | Reversal | -0.214% | Liquidity sweep / reversal |
| 2026-02-13 13:30 | Valid swing, away from level | n/a | -125.6% | 21.49x | Flat / fading | 0.077% | Position building in range |
| 2025-11-20 10:00 | Valid swing, away from level | 38.2% | 14.0% | 21.38x | Reversal | -0.622% | Liquidity sweep / reversal |
| 2026-06-01 07:00 | Valid swing, away from level | n/a | -328.6% | 21.20x | Impulse / continuation | -0.040% | True breakout |
| 2025-08-18 07:00 | Valid swing, away from level | n/a | -102.3% | 20.95x | Impulse / continuation | 0.475% | True breakout |
| 2025-12-15 07:00 | Valid swing, away from level | n/a | -171.4% | 20.58x | Reversal | 0.150% | Liquidity sweep / reversal |
| 2026-01-19 07:00 | Valid swing, away from level | n/a | -33.3% | 20.32x | Impulse / continuation | 0.067% | True breakout |
| 2026-07-20 07:00 | Valid swing, away from level | 38.2% | 8.8% | 20.27x | Impulse / continuation | -0.911% | True breakout |
| 2026-06-15 07:00 | Valid swing, away from level | n/a | -2200.0% | 20.05x | Flat / fading | -0.033% | Weak move without breakout |
| 2026-02-09 07:00 | Valid swing, away from level | n/a | 132.7% | 19.63x | Flat / fading | -0.006% | Position building in range |
| 2026-02-26 09:45 | Valid swing, away from level | n/a | -125.0% | 19.62x | Flat / fading | -0.136% | Position building in range |
| 2026-04-22 07:30 | Valid swing, away from level | n/a | 155.7% | 19.31x | Reversal | 0.516% | Liquidity sweep / reversal |
| 2026-09-06 18:45 | Valid swing, away from level | n/a | 191.8% | 18.93x | Flat / fading | 0.408% | Position building in range |
| 2026-06-19 13:30 | Valid swing, away from level | n/a | 181.0% | 18.78x | Flat / fading | 0.183% | Position building in range |
| 2025-07-21 07:00 | Valid swing, away from level | n/a | -28.0% | 18.77x | Impulse / continuation | 0.208% | True breakout |
| 2025-09-29 07:00 | Valid swing, away from level | n/a | -142.9% | 18.65x | Reversal | 0.026% | Liquidity sweep / reversal |
| 2024-12-02 10:00 | Valid swing, away from level | n/a | -108.4% | 18.59x | Flat / fading | -0.512% | Position building in range |
| 2025-07-06 10:15 | Valid swing, away from level | n/a | 383.3% | 18.49x | Impulse / continuation | -0.106% | True breakout |
| 2025-10-24 13:30 | Valid swing, away from level | n/a | 115.6% | 18.44x | Impulse / continuation | 0.014% | True breakout |
| 2026-03-20 10:30 | Valid swing, away from level | n/a | -12.4% | 18.09x | Flat / fading | 0.113% | Position building in range |
| 2025-02-10 22:30 | Golden zone 50-61.8% | 61.8% | 57.3% | 18.06x | Impulse / continuation | 0.166% | True breakout |
| 2025-12-19 13:30 | Near Fib level | 78.6% | 81.7% | 18.05x | Flat / fading | 0.174% | Position building in range |
| 2025-07-25 13:30 | Valid swing, away from level | 61.8% | 68.7% | 17.92x | Reversal | -0.073% | Liquidity sweep / reversal |
| 2025-03-16 16:30 | Valid swing, away from level | n/a | -1627.3% | 17.87x | Impulse / continuation | 0.115% | True breakout |
| 2026-06-19 09:15 | Valid swing, away from level | n/a | 101.1% | 17.84x | Flat / fading | 0.000% | Position building in range |
| 2024-10-09 14:30 | Valid swing, away from level | n/a | -100.0% | 17.65x | Flat / fading | -0.272% | Position building in range |
| 2026-02-27 07:45 | Valid swing, away from level | n/a | 139.1% | 17.56x | Flat / fading | 0.278% | Position building in range |
| 2025-10-21 07:30 | Valid swing, away from level | n/a | 508.4% | 17.50x | Flat / fading | 0.508% | Position building in range |
| 2025-11-18 10:15 | Valid swing, away from level | n/a | -138.3% | 17.43x | Impulse / continuation | 1.443% | True breakout |
| 2026-06-08 07:00 | Valid swing, away from level | n/a | -182.6% | 17.38x | Impulse / continuation | 0.094% | True breakout |
| 2024-10-23 10:00 | Valid swing, away from level | n/a | 131.1% | 17.23x | Impulse / continuation | -0.216% | True breakout |
| 2026-07-24 13:30 | Near Fib level | 78.6% | 79.5% | 17.08x | Reversal | -1.080% | Liquidity sweep / reversal |
| 2026-01-29 10:00 | Valid swing, away from level | n/a | -83.9% | 17.05x | Impulse / continuation | 0.621% | True breakout |
| 2024-12-11 10:00 | Valid swing, away from level | n/a | 127.2% | 17.00x | Impulse / continuation | -0.197% | True breakout |
| 2024-11-12 10:00 | Valid swing, away from level | 78.6% | 89.5% | 16.98x | Impulse / continuation | -0.369% | True breakout |
| 2025-05-16 15:15 | Valid swing, away from level | n/a | 380.0% | 16.96x | Impulse / continuation | 0.231% | True breakout |
| 2026-07-26 10:00 | Valid swing, away from level | 38.2% | 17.0% | 16.93x | Flat / fading | 0.306% | Position building in range |
| 2026-01-12 07:00 | Valid swing, away from level | n/a | -28.6% | 16.82x | Flat / fading | -0.185% | Position building in range |
| 2026-06-12 16:45 | Near Fib level | 78.6% | 80.8% | 16.63x | Flat / fading | -0.034% | Position building in range |
| 2025-01-15 19:00 | Valid swing, away from level | n/a | -133.6% | 16.62x | Flat / fading | 0.155% | Position building in range |
| 2024-12-20 13:30 | Valid swing, away from level | n/a | -1253.4% | 16.16x | Flat / fading | 0.610% | Position building in range |
| 2025-12-03 07:00 | Valid swing, away from level | n/a | 194.5% | 15.74x | Flat / fading | 0.213% | Weak move without breakout |
| 2024-10-04 10:00 | Valid swing, away from level | 38.2% | 12.5% | 15.72x | Reversal | 0.892% | Liquidity sweep / reversal |
| 2025-11-17 07:00 | Valid swing, away from level | 38.2% | 27.6% | 15.69x | Flat / fading | -0.048% | Weak move without breakout |
| 2026-02-23 10:00 | Valid swing, away from level | 38.2% | 22.9% | 15.68x | Flat / fading | 0.028% | Position building in range |
| 2025-03-07 17:15 | Golden zone 50-61.8% | 61.8% | 60.1% | 15.54x | Flat / fading | -1.488% | Position building in range |
| 2026-09-21 07:30 | Valid swing, away from level | n/a | -580.0% | 15.53x | Impulse / continuation | 0.204% | True breakout |
| 2025-06-16 10:00 | Valid swing, away from level | n/a | -10.9% | 15.26x | Reversal | -0.559% | Liquidity sweep / reversal |
| 2026-05-01 17:15 | Near Fib level | 61.8% | 62.8% | 15.22x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2026-02-22 10:15 | Valid swing, away from level | n/a | -116.7% | 14.97x | Flat / fading | 0.063% | Weak move without breakout |
| 2026-04-27 09:00 | Valid swing, away from level | n/a | 413.3% | 14.94x | Flat / fading | 0.063% | Position building in range |
| 2024-10-11 10:00 | Near Fib level | 38.2% | 36.4% | 14.83x | Flat / fading | -0.020% | Position building in range |
| 2025-09-12 10:00 | Valid swing, away from level | n/a | 114.4% | 14.80x | Impulse / continuation | -0.049% | True breakout |
| 2025-01-10 10:00 | Near Fib level | 38.2% | 41.3% | 14.66x | Reversal | -0.247% | Liquidity sweep / reversal |
| 2025-11-20 20:45 | Valid swing, away from level | n/a | -17.3% | 14.51x | Flat / fading | -0.740% | Position building in range |
| 2025-09-12 13:30 | Valid swing, away from level | 78.6% | 84.3% | 14.44x | Flat / fading | -0.074% | Position building in range |
| 2024-10-16 10:00 | Valid swing, away from level | 38.2% | 27.3% | 14.40x | Flat / fading | 0.076% | Weak move without breakout |
| 2025-12-05 10:15 | Valid swing, away from level | n/a | -36.4% | 14.38x | Impulse / continuation | 0.580% | True breakout |
| 2026-02-18 10:45 | Valid swing, away from level | n/a | -37.7% | 14.37x | Impulse / continuation | 0.006% | True breakout |
| 2025-09-30 10:00 | Valid swing, away from level | 78.6% | 97.0% | 14.29x | Impulse / continuation | -0.019% | True breakout |
| 2024-09-27 10:00 | Valid swing, away from level | n/a | -35.7% | 14.23x | Flat / fading | -0.209% | Weak move without breakout |
| 2024-10-22 10:00 | Near Fib level | 61.8% | 63.5% | 14.22x | Impulse / continuation | -0.463% | True breakout |
| 2025-06-09 07:00 | Valid swing, away from level | n/a | 265.8% | 14.18x | Flat / fading | 0.118% | Position building in range |
| 2026-05-25 07:00 | Valid swing, away from level | n/a | -55.6% | 14.15x | Flat / fading | 0.033% | Position building in range |
| 2025-07-31 10:00 | Near Fib level | 38.2% | 40.2% | 14.10x | Reversal | -0.474% | Liquidity sweep / reversal |
| 2024-12-03 10:00 | Near Fib level | 78.6% | 75.0% | 14.10x | Impulse / continuation | -0.962% | True breakout |
| 2025-10-20 10:00 | Valid swing, away from level | n/a | -30.6% | 14.02x | Impulse / continuation | 0.121% | True breakout |
| 2026-07-27 07:00 | Valid swing, away from level | n/a | 105.1% | 13.98x | Reversal | 0.936% | Liquidity sweep / reversal |
| 2025-01-27 10:00 | Valid swing, away from level | n/a | 159.3% | 13.97x | Flat / fading | -0.140% | Weak move without breakout |
| 2024-12-16 10:00 | Valid swing, away from level | n/a | 106.5% | 13.93x | Impulse / continuation | -0.640% | True breakout |
| 2026-02-24 10:00 | Near Fib level | 61.8% | 64.1% | 13.93x | Reversal | 0.125% | Liquidity sweep / reversal |
| 2026-06-01 07:30 | Valid swing, away from level | n/a | -242.9% | 13.87x | Impulse -> reversal | 0.053% | False breakout |
| 2024-12-30 10:00 | Valid swing, away from level | n/a | -364.5% | 13.84x | Impulse / continuation | 0.015% | True breakout |
| 2026-03-02 07:00 | Golden zone 50-61.8% | 50.0% | 55.3% | 13.81x | Impulse / continuation | 0.064% | True breakout |
| 2025-04-28 07:00 | Near Fib level | 38.2% | 42.2% | 13.60x | Flat / fading | 0.054% | Position building in range |
| 2026-08-08 17:00 | Valid swing, away from level | n/a | -95.9% | 13.58x | Impulse / continuation | -0.029% | True breakout |
| 2026-04-27 07:00 | Valid swing, away from level | n/a | 173.3% | 13.55x | Reversal | 0.075% | Liquidity sweep / reversal |
| 2025-01-06 10:00 | Valid swing, away from level | n/a | 330.9% | 13.53x | Reversal | 0.693% | Liquidity sweep / reversal |
| 2025-06-16 07:00 | Valid swing, away from level | 38.2% | 13.8% | 13.44x | Flat / fading | -0.038% | Position building in range |
| 2025-04-07 07:00 | Valid swing, away from level | n/a | 1417.9% | 13.31x | Impulse / continuation | -0.603% | True breakout |
| 2024-10-21 10:00 | Valid swing, away from level | n/a | -15.8% | 13.28x | Impulse / continuation | 0.271% | True breakout |
| 2025-02-06 10:30 | Valid swing, away from level | n/a | -23.4% | 13.27x | Impulse / continuation | 0.193% | True breakout |
| 2024-10-01 10:00 | Valid swing, away from level | n/a | 186.7% | 13.16x | Impulse / continuation | -0.535% | True breakout |
| 2026-02-27 09:45 | Valid swing, away from level | n/a | 272.2% | 13.04x | Flat / fading | 0.296% | Position building in range |
| 2025-12-01 07:00 | Valid swing, away from level | n/a | -18.2% | 12.82x | Impulse / continuation | -0.198% | True breakout |
| 2025-03-16 16:15 | Valid swing, away from level | n/a | -261.8% | 12.82x | Impulse / continuation | 0.663% | True breakout |
| 2026-09-21 07:15 | Valid swing, away from level | n/a | -230.0% | 12.80x | Impulse / continuation | 0.426% | True breakout |
| 2025-10-19 10:00 | Valid swing, away from level | 78.6% | 96.4% | 12.77x | Impulse / continuation | -0.305% | True breakout |
| 2025-10-22 22:00 | Valid swing, away from level | n/a | 141.1% | 12.75x | Impulse / continuation | -0.204% | True breakout |
| 2024-10-07 10:00 | Near Fib level | 78.6% | 76.4% | 12.74x | Reversal | -0.605% | Liquidity sweep / reversal |
| 2025-03-18 07:00 | Valid swing, away from level | n/a | -65.6% | 12.72x | Impulse / continuation | 0.344% | True breakout |
| 2025-08-07 11:00 | Valid swing, away from level | n/a | -21.0% | 12.67x | Impulse / continuation | 0.934% | True breakout |
| 2025-07-26 15:45 | Valid swing, away from level | n/a | 104.1% | 12.64x | Flat / fading | 0.006% | Position building in range |
| 2025-12-09 22:00 | Valid swing, away from level | n/a | -6.9% | 12.61x | Flat / fading | 0.068% | Position building in range |
| 2025-12-16 10:45 | Valid swing, away from level | n/a | -57.9% | 12.60x | Flat / fading | -0.024% | Weak move without breakout |
| 2026-03-30 07:00 | Valid swing, away from level | n/a | -830.8% | 12.57x | Impulse / continuation | 0.068% | True breakout |
| 2025-07-07 20:45 | Valid swing, away from level | n/a | 133.6% | 12.53x | Flat / fading | -0.063% | Position building in range |
| 2026-06-09 10:30 | Valid swing, away from level | n/a | 332.6% | 12.43x | Reversal | 1.251% | Liquidity sweep / reversal |
| 2025-07-18 10:00 | Valid swing, away from level | n/a | -30.5% | 12.36x | Impulse / continuation | 0.199% | True breakout |
| 2025-04-13 10:00 | Valid swing, away from level | 38.2% | 0.0% | 12.34x | Reversal | -0.132% | Liquidity sweep / reversal |
| 2024-10-25 10:00 | Golden zone 50-61.8% | 50.0% | 51.7% | 12.33x | Impulse / continuation | 0.059% | True breakout |
| 2025-10-21 07:00 | Valid swing, away from level | n/a | 165.1% | 12.31x | Impulse / continuation | -1.668% | True breakout |
| 2026-04-05 10:15 | Valid swing, away from level | n/a | -51.3% | 12.26x | Flat / fading | -0.062% | Position building in range |
| 2025-03-20 10:00 | Valid swing, away from level | 38.2% | 22.6% | 12.24x | Impulse / continuation | -0.689% | True breakout |
| 2026-05-19 11:00 | Valid swing, away from level | n/a | -39.9% | 12.21x | Impulse / continuation | 0.527% | True breakout |
| 2024-12-10 10:00 | Valid swing, away from level | n/a | 123.0% | 12.19x | Impulse / continuation | -0.645% | True breakout |
| 2024-12-18 10:00 | Valid swing, away from level | n/a | -49.6% | 12.19x | Reversal | -0.529% | Liquidity sweep / reversal |
| 2026-06-05 18:15 | Valid swing, away from level | n/a | 177.8% | 12.19x | Flat / fading | -0.020% | Position building in range |
| 2025-03-03 07:00 | Valid swing, away from level | n/a | 172.4% | 12.18x | Impulse / continuation | -0.467% | True breakout |
| 2026-06-08 07:15 | Valid swing, away from level | n/a | -287.0% | 12.16x | Flat / fading | -0.067% | Position building in range |
| 2025-05-19 07:45 | Valid swing, away from level | n/a | 207.7% | 12.11x | Flat / fading | -0.403% | Position building in range |
| 2026-03-24 10:15 | Valid swing, away from level | n/a | -56.8% | 12.10x | Impulse / continuation | 0.595% | True breakout |
| 2024-10-25 13:30 | Valid swing, away from level | n/a | 172.4% | 12.02x | Reversal | 0.139% | Liquidity sweep / reversal |
| 2024-10-09 10:00 | Golden zone 50-61.8% | 61.8% | 57.9% | 11.95x | Reversal | 0.513% | Liquidity sweep / reversal |
| 2026-01-26 07:00 | Valid swing, away from level | 38.2% | 29.4% | 11.94x | Reversal | -0.066% | Liquidity sweep / reversal |
| 2026-03-18 09:45 | Valid swing, away from level | n/a | -39.1% | 11.94x | Impulse / continuation | 0.291% | True breakout |
| 2025-09-10 09:00 | Near Fib level | 61.8% | 62.7% | 11.90x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-08-04 07:15 | Valid swing, away from level | n/a | -84.3% | 11.88x | Flat / fading | -0.480% | Position building in range |
| 2025-04-07 17:15 | Valid swing, away from level | n/a | -24.2% | 11.88x | Flat / fading | 0.112% | Position building in range |
| 2025-10-30 10:00 | Valid swing, away from level | n/a | -116.0% | 11.76x | Flat / fading | -0.034% | Weak move without breakout |
| 2025-01-30 10:00 | Valid swing, away from level | 38.2% | 7.6% | 11.72x | Reversal | 0.059% | Liquidity sweep / reversal |
| 2025-01-13 10:00 | Valid swing, away from level | n/a | -48.7% | 11.68x | Reversal | -0.652% | Liquidity sweep / reversal |
| 2026-01-26 09:00 | Near Fib level | 61.8% | 65.1% | 11.66x | Flat / fading | -0.096% | Position building in range |
| 2025-05-14 16:30 | Valid swing, away from level | n/a | -105.3% | 11.65x | Flat / fading | -0.257% | Position building in range |
| 2025-10-31 20:00 | Valid swing, away from level | n/a | 139.0% | 11.52x | Flat / fading | 0.218% | Position building in range |
| 2026-06-09 10:15 | Valid swing, away from level | n/a | 188.8% | 11.43x | Impulse / continuation | 0.305% | True breakout |
| 2025-06-06 13:30 | Valid swing, away from level | n/a | -269.3% | 11.36x | Flat / fading | -0.689% | Position building in range |
| 2025-04-14 07:00 | Valid swing, away from level | 38.2% | 19.5% | 11.35x | Impulse / continuation | -0.365% | True breakout |
| 2025-01-31 10:00 | Valid swing, away from level | n/a | -141.0% | 11.29x | Impulse / continuation | 0.130% | True breakout |
| 2026-07-13 10:30 | Valid swing, away from level | n/a | -265.7% | 11.28x | Flat / fading | 0.443% | Weak move without breakout |
| 2026-04-27 08:30 | Valid swing, away from level | n/a | -220.0% | 11.22x | Reversal | -0.591% | Liquidity sweep / reversal |
| 2025-06-30 10:00 | Valid swing, away from level | n/a | -13.1% | 11.10x | Reversal | -0.579% | Liquidity sweep / reversal |
| 2026-06-29 07:00 | Near Fib level | 50.0% | 50.0% | 11.10x | Reversal | 0.045% | Liquidity sweep / reversal |
| 2026-03-12 10:00 | Valid swing, away from level | n/a | -7.5% | 11.10x | Flat / fading | 0.059% | Weak move without breakout |
| 2026-02-25 10:15 | Valid swing, away from level | n/a | -61.5% | 11.06x | Flat / fading | -0.028% | Position building in range |
| 2026-03-13 10:00 | Valid swing, away from level | n/a | -270.7% | 11.06x | Flat / fading | 0.047% | Position building in range |
| 2025-09-02 10:00 | Valid swing, away from level | n/a | 147.7% | 10.97x | Flat / fading | -0.199% | Weak move without breakout |
| 2024-11-22 17:45 | Valid swing, away from level | n/a | 483.1% | 10.95x | Flat / fading | 1.762% | Position building in range |
| 2026-03-03 09:30 | Valid swing, away from level | 78.6% | 89.0% | 10.92x | Impulse / continuation | -0.270% | True breakout |
| 2026-08-28 07:00 | Valid swing, away from level | n/a | -5.0% | 10.87x | Impulse / continuation | 0.261% | True breakout |
| 2026-09-11 13:30 | Valid swing, away from level | 78.6% | 98.5% | 10.86x | Flat / fading | 0.069% | Weak move without breakout |
| 2026-03-05 12:30 | Valid swing, away from level | 38.2% | 8.4% | 10.81x | Impulse / continuation | 0.230% | True breakout |
| 2025-01-08 10:00 | Valid swing, away from level | n/a | -8.9% | 10.81x | Impulse / continuation | 0.353% | True breakout |
| 2026-09-14 07:00 | Valid swing, away from level | n/a | -2.5% | 10.66x | Flat / fading | 0.076% | Weak move without breakout |
| 2026-04-20 07:00 | Valid swing, away from level | n/a | -120.7% | 10.64x | Flat / fading | 0.024% | Position building in range |
| 2024-12-10 10:15 | Valid swing, away from level | n/a | 175.9% | 10.63x | Impulse / continuation | -0.134% | True breakout |
| 2026-02-24 10:15 | Near Fib level | 50.0% | 49.5% | 10.62x | Flat / fading | 0.006% | Position building in range |
| 2024-12-04 10:00 | Valid swing, away from level | 38.2% | 26.7% | 10.61x | Reversal | 0.475% | Liquidity sweep / reversal |
| 2025-11-14 11:15 | Valid swing, away from level | n/a | 174.6% | 10.60x | Flat / fading | 0.109% | Weak move without breakout |
| 2025-03-04 19:00 | Valid swing, away from level | n/a | -106.3% | 10.59x | Flat / fading | -0.465% | Position building in range |
| 2025-07-14 09:45 | Valid swing, away from level | n/a | -210.8% | 10.56x | Impulse / continuation | 1.643% | True breakout |
| 2026-02-23 18:15 | Near Fib level | 50.0% | 47.1% | 10.53x | Impulse / continuation | 0.250% | True breakout |
| 2026-04-26 12:45 | Valid swing, away from level | n/a | 126.7% | 10.53x | Impulse / continuation | -0.012% | True breakout |
| 2026-01-16 11:00 | Valid swing, away from level | n/a | -189.3% | 10.52x | Flat / fading | 0.043% | Weak move without breakout |
| 2024-10-15 10:00 | Valid swing, away from level | 38.2% | 13.3% | 10.49x | Impulse / continuation | 0.786% | True breakout |
| 2025-12-23 10:30 | Golden zone 50-61.8% | 61.8% | 58.2% | 10.47x | Flat / fading | -0.241% | Weak move without breakout |
| 2026-05-18 09:00 | Valid swing, away from level | n/a | 251.2% | 10.46x | Impulse / continuation | -0.136% | True breakout |
| 2025-10-29 10:00 | Valid swing, away from level | n/a | -8.1% | 10.40x | Flat / fading | -0.041% | Position building in range |
| 2025-07-08 10:00 | Near Fib level | 78.6% | 75.1% | 10.39x | Reversal | 0.038% | Liquidity sweep / reversal |
| 2026-01-22 16:15 | Valid swing, away from level | n/a | 113.9% | 10.39x | Impulse / continuation | -0.372% | True breakout |
| 2025-10-21 07:15 | Valid swing, away from level | n/a | 316.9% | 10.39x | Impulse / continuation | -0.670% | True breakout |
| 2025-03-21 07:00 | Valid swing, away from level | 38.2% | 6.0% | 10.37x | Reversal | -0.329% | Liquidity sweep / reversal |
| 2025-11-17 07:30 | Valid swing, away from level | 78.6% | 93.1% | 10.37x | Flat / fading | 0.027% | Position building in range |
| 2025-06-06 10:15 | Valid swing, away from level | n/a | -33.5% | 10.34x | Impulse / continuation | 0.709% | True breakout |
| 2026-08-31 18:00 | Valid swing, away from level | n/a | -150.0% | 10.33x | Impulse / continuation | 0.118% | True breakout |
| 2025-01-20 10:00 | Valid swing, away from level | n/a | -33.0% | 10.28x | Reversal | -0.383% | Liquidity sweep / reversal |
| 2025-10-12 10:00 | Valid swing, away from level | n/a | -192.5% | 10.26x | Flat / fading | -0.021% | Position building in range |
| 2025-04-01 07:00 | Valid swing, away from level | n/a | -13.6% | 10.20x | Impulse / continuation | 0.260% | True breakout |
| 2026-01-14 11:30 | Valid swing, away from level | n/a | -9.2% | 10.13x | Flat / fading | 0.274% | Position building in range |
| 2025-10-21 18:00 | Valid swing, away from level | n/a | 385.5% | 10.10x | Flat / fading | 1.369% | Position building in range |
| 2024-11-20 10:00 | Golden zone 50-61.8% | 61.8% | 56.9% | 10.09x | Reversal | -0.390% | Liquidity sweep / reversal |
| 2025-12-11 19:00 | Valid swing, away from level | n/a | -29.9% | 10.09x | Flat / fading | -0.194% | Position building in range |
| 2025-06-15 10:15 | Valid swing, away from level | 78.6% | 100.0% | 10.09x | Flat / fading | 0.045% | Position building in range |
| 2026-01-31 18:30 | Valid swing, away from level | 38.2% | 20.8% | 10.07x | Reversal | -0.012% | Liquidity sweep / reversal |
| 2024-09-25 10:00 | Valid swing, away from level | 38.2% | 23.6% | 10.06x | Reversal | 0.057% | Liquidity sweep / reversal |
| 2026-08-24 09:15 | Valid swing, away from level | n/a | 600.0% | 10.05x | Flat / fading | 0.120% | Weak move without breakout |
| 2025-05-19 07:00 | Valid swing, away from level | n/a | 107.7% | 10.02x | Impulse / continuation | -0.427% | True breakout |
| 2026-08-10 07:00 | Valid swing, away from level | 38.2% | 17.2% | 10.01x | Flat / fading | -0.129% | Weak move without breakout |
| 2026-01-08 10:00 | Valid swing, away from level | n/a | 308.9% | 9.99x | Flat / fading | -0.221% | Weak move without breakout |
| 2026-01-15 13:00 | Golden zone 50-61.8% | 50.0% | 52.2% | 9.98x | Flat / fading | -0.019% | Weak move without breakout |
| 2024-10-08 10:00 | Near Fib level | 61.8% | 64.4% | 9.97x | Impulse / continuation | -0.534% | True breakout |
| 2025-06-08 10:00 | Valid swing, away from level | 38.2% | 17.1% | 9.94x | Impulse / continuation | -0.186% | True breakout |
| 2026-08-24 07:15 | Valid swing, away from level | n/a | 244.7% | 9.94x | Reversal | -0.175% | Liquidity sweep / reversal |
| 2025-08-21 10:00 | Valid swing, away from level | n/a | -26.6% | 9.91x | Impulse / continuation | -0.592% | True breakout |
| 2025-07-13 14:00 | Valid swing, away from level | n/a | 394.3% | 9.87x | Flat / fading | 0.240% | Weak move without breakout |
| 2024-12-25 10:15 | Valid swing, away from level | 78.6% | 84.1% | 9.86x | Reversal | 0.287% | Liquidity sweep / reversal |
| 2026-06-18 10:15 | Valid swing, away from level | n/a | 195.3% | 9.86x | Flat / fading | -0.211% | Position building in range |
| 2026-02-10 10:15 | Valid swing, away from level | n/a | -7.0% | 9.80x | Reversal | -0.380% | Liquidity sweep / reversal |
| 2025-05-10 17:00 | Golden zone 50-61.8% | 50.0% | 53.1% | 9.80x | Flat / fading | 0.026% | Position building in range |
| 2024-12-25 10:00 | Valid swing, away from level | 78.6% | 89.8% | 9.74x | Impulse / continuation | -0.023% | True breakout |
| 2026-06-29 09:15 | Valid swing, away from level | n/a | 212.5% | 9.72x | Impulse / continuation | -0.257% | True breakout |
| 2024-12-24 10:00 | Valid swing, away from level | n/a | 130.4% | 9.69x | Impulse / continuation | -0.684% | True breakout |
| 2025-03-17 14:45 | Valid swing, away from level | 38.2% | 18.3% | 9.65x | Flat / fading | 0.204% | Position building in range |
| 2025-11-05 07:00 | Valid swing, away from level | n/a | 169.6% | 9.63x | Flat / fading | 0.081% | Position building in range |
| 2025-08-08 23:30 | Valid swing, away from level | n/a | -47.9% | 9.59x | Impulse / continuation | 0.727% | True breakout |
| 2026-06-09 10:45 | Valid swing, away from level | n/a | 139.3% | 9.52x | Flat / fading | 0.062% | Weak move without breakout |
| 2024-10-10 10:15 | Valid swing, away from level | n/a | -28.9% | 9.52x | Reversal | -0.309% | Liquidity sweep / reversal |
| 2026-02-22 10:00 | Valid swing, away from level | n/a | -81.0% | 9.50x | Impulse / continuation | 0.165% | True breakout |
| 2025-03-07 10:30 | Valid swing, away from level | n/a | -200.6% | 9.49x | Flat / fading | -0.162% | Weak move without breakout |
| 2025-10-16 17:00 | Valid swing, away from level | n/a | -326.1% | 9.45x | Impulse / continuation | 0.576% | True breakout |
| 2025-05-22 10:00 | Valid swing, away from level | n/a | 178.9% | 9.44x | Impulse / continuation | 0.709% | True breakout |
| 2026-02-11 10:00 | Near Fib level | 78.6% | 78.7% | 9.42x | Flat / fading | 0.243% | Weak move without breakout |
| 2025-05-11 10:00 | Valid swing, away from level | n/a | -538.8% | 9.38x | Flat / fading | 0.409% | Weak move without breakout |
| 2026-08-30 10:00 | Golden zone 50-61.8% | 50.0% | 54.0% | 9.38x | Flat / fading | -0.032% | Position building in range |
| 2025-01-22 19:00 | Valid swing, away from level | n/a | 114.8% | 9.37x | Impulse / continuation | -0.582% | True breakout |
| 2024-10-17 10:00 | Valid swing, away from level | n/a | -16.7% | 9.34x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-12-05 10:30 | Valid swing, away from level | n/a | -81.8% | 9.34x | Impulse / continuation | 0.254% | True breakout |
| 2025-09-03 10:15 | Valid swing, away from level | 38.2% | 43.3% | 9.32x | Flat / fading | -0.139% | Weak move without breakout |
| 2025-12-11 09:30 | Valid swing, away from level | n/a | -49.5% | 9.29x | Impulse / continuation | 0.141% | True breakout |
| 2026-02-24 07:00 | Valid swing, away from level | n/a | -82.4% | 9.28x | Impulse / continuation | 0.096% | True breakout |
| 2024-10-30 10:00 | Valid swing, away from level | n/a | -21.9% | 9.27x | Impulse -> reversal | 0.167% | False breakout |
| 2025-03-21 13:30 | Golden zone 50-61.8% | 50.0% | 53.5% | 9.25x | Impulse / continuation | -0.654% | True breakout |
| 2024-11-06 10:15 | Valid swing, away from level | n/a | -376.7% | 9.24x | Reversal | 0.676% | Liquidity sweep / reversal |
| 2026-06-01 10:00 | Valid swing, away from level | n/a | -682.4% | 9.24x | Flat / fading | -0.158% | Position building in range |
| 2026-05-25 09:00 | Valid swing, away from level | n/a | -66.7% | 9.23x | Reversal | -0.026% | Liquidity sweep / reversal |
| 2025-11-18 07:00 | Valid swing, away from level | n/a | 141.7% | 9.21x | Reversal | -0.021% | Liquidity sweep / reversal |
| 2026-09-03 07:00 | Valid swing, away from level | 38.2% | 5.9% | 9.21x | Flat / fading | 0.212% | Position building in range |
| 2026-03-19 10:00 | Valid swing, away from level | 78.6% | 72.5% | 9.19x | Reversal | 0.305% | Liquidity sweep / reversal |
| 2025-09-05 11:45 | Valid swing, away from level | n/a | -27.8% | 9.19x | Flat / fading | -0.042% | Weak move without breakout |
| 2025-10-01 09:15 | Valid swing, away from level | 38.2% | 1.9% | 9.15x | Flat / fading | -0.045% | Weak move without breakout |
| 2024-09-25 12:15 | Valid swing, away from level | n/a | -196.3% | 9.14x | Impulse / continuation | 0.660% | True breakout |
| 2025-03-18 16:00 | Valid swing, away from level | n/a | -36.6% | 9.13x | Impulse / continuation | 0.715% | True breakout |
| 2025-03-13 19:00 | Valid swing, away from level | n/a | -10.7% | 9.12x | Flat / fading | 0.447% | Weak move without breakout |
| 2025-12-29 11:45 | Valid swing, away from level | n/a | -228.2% | 9.11x | Impulse / continuation | -0.380% | True breakout |
| 2026-02-09 09:00 | Valid swing, away from level | n/a | 185.7% | 9.10x | Impulse / continuation | -0.122% | True breakout |
| 2025-09-29 10:00 | Valid swing, away from level | n/a | -260.9% | 9.05x | Impulse / continuation | 0.326% | True breakout |
| 2024-12-04 10:15 | Valid swing, away from level | 61.8% | 67.9% | 9.00x | Reversal | 1.150% | Liquidity sweep / reversal |
| 2025-10-03 10:00 | Valid swing, away from level | n/a | -78.3% | 9.00x | Flat / fading | 0.059% | Position building in range |
| 2025-05-05 07:00 | Near Fib level | 78.6% | 76.4% | 8.99x | Impulse / continuation | -0.172% | True breakout |
| 2025-12-26 09:45 | Valid swing, away from level | n/a | -414.3% | 8.96x | Flat / fading | 0.188% | Position building in range |
| 2025-07-21 09:00 | Valid swing, away from level | n/a | -76.3% | 8.96x | Flat / fading | 0.107% | Position building in range |
| 2025-12-25 09:30 | Valid swing, away from level | n/a | 135.7% | 8.91x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-01-17 10:00 | Valid swing, away from level | 78.6% | 92.2% | 8.89x | Impulse -> reversal | 0.430% | False breakout |
| 2026-07-13 10:15 | Valid swing, away from level | n/a | -110.0% | 8.84x | Impulse / continuation | 0.926% | True breakout |
| 2024-10-10 10:00 | Valid swing, away from level | 38.2% | 1.0% | 8.84x | Reversal | 0.233% | Liquidity sweep / reversal |
| 2025-05-02 07:00 | Valid swing, away from level | n/a | 132.8% | 8.83x | Impulse / continuation | 0.217% | True breakout |
| 2026-02-24 07:15 | Valid swing, away from level | n/a | -132.4% | 8.82x | Flat / fading | 0.023% | Weak move without breakout |
| 2025-05-26 07:00 | Valid swing, away from level | n/a | 145.1% | 8.82x | Impulse / continuation | -0.262% | True breakout |
| 2025-06-16 10:45 | Valid swing, away from level | n/a | 118.7% | 8.82x | Flat / fading | 0.198% | Position building in range |
| 2025-10-20 10:30 | Valid swing, away from level | n/a | -101.8% | 8.79x | Flat / fading | -0.278% | Position building in range |
| 2025-03-11 21:00 | Near Fib level | 78.6% | 80.2% | 8.78x | Impulse / continuation | -0.432% | True breakout |
| 2026-03-17 16:00 | Valid swing, away from level | n/a | 305.7% | 8.77x | Flat / fading | 0.006% | Position building in range |
| 2024-10-02 10:00 | Valid swing, away from level | n/a | -13.2% | 8.76x | Flat / fading | -0.155% | Weak move without breakout |
| 2025-01-03 10:00 | Valid swing, away from level | n/a | -62.2% | 8.75x | Impulse / continuation | -0.306% | True breakout |
| 2024-12-26 10:00 | Valid swing, away from level | n/a | -5.6% | 8.70x | Reversal | 0.507% | Liquidity sweep / reversal |
| 2025-09-16 08:15 | Valid swing, away from level | n/a | -94.4% | 8.69x | Impulse / continuation | -0.132% | True breakout |
| 2025-02-26 10:00 | Valid swing, away from level | 78.6% | 94.6% | 8.67x | Flat / fading | 0.035% | Weak move without breakout |
| 2024-10-22 10:30 | Valid swing, away from level | 78.6% | 92.1% | 8.64x | Impulse / continuation | -0.213% | True breakout |
| 2025-10-16 10:00 | Near Fib level | 61.8% | 64.6% | 8.64x | Reversal | 0.345% | Liquidity sweep / reversal |
| 2026-06-04 10:15 | Near Fib level | 61.8% | 62.0% | 8.62x | Flat / fading | -0.171% | Position building in range |
| 2026-08-06 07:00 | Valid swing, away from level | n/a | -426.2% | 8.59x | Flat / fading | -0.545% | Position building in range |
| 2026-07-22 12:00 | Valid swing, away from level | 38.2% | 13.0% | 8.58x | Impulse / continuation | 1.008% | True breakout |
| 2024-11-15 10:00 | Valid swing, away from level | 38.2% | 17.8% | 8.53x | Reversal | -0.405% | Liquidity sweep / reversal |
| 2025-07-14 18:15 | Valid swing, away from level | n/a | -37.3% | 8.52x | Impulse / continuation | 0.980% | True breakout |
| 2025-04-11 09:00 | Valid swing, away from level | n/a | -4.2% | 8.52x | Impulse / continuation | 0.140% | True breakout |
| 2024-12-24 10:15 | Valid swing, away from level | n/a | 130.4% | 8.52x | Impulse / continuation | 0.046% | True breakout |
| 2026-02-02 07:00 | Near Fib level | 78.6% | 79.1% | 8.51x | Impulse / continuation | -0.072% | True breakout |
| 2026-08-25 17:30 | Valid swing, away from level | n/a | -93.7% | 8.46x | Impulse / continuation | 0.896% | True breakout |
| 2024-12-13 10:00 | Valid swing, away from level | n/a | 107.4% | 8.41x | Impulse / continuation | -0.165% | True breakout |
| 2025-03-27 10:00 | Valid swing, away from level | n/a | 389.2% | 8.40x | Impulse / continuation | -0.312% | True breakout |
| 2025-08-17 16:00 | Valid swing, away from level | n/a | 144.4% | 8.37x | Flat / fading | -0.024% | Position building in range |
| 2025-08-27 10:15 | Valid swing, away from level | n/a | -48.1% | 8.37x | Impulse / continuation | 0.171% | True breakout |
| 2025-12-13 18:00 | Near Fib level | 61.8% | 63.0% | 8.35x | Reversal | 0.038% | Liquidity sweep / reversal |
| 2026-05-29 23:00 | Valid swing, away from level | 78.6% | 85.5% | 8.35x | Reversal | 0.060% | Liquidity sweep / reversal |
| 2025-09-04 10:00 | Valid swing, away from level | n/a | -27.5% | 8.34x | Flat / fading | -0.072% | Position building in range |
| 2026-05-03 12:15 | Valid swing, away from level | n/a | -61.5% | 8.33x | Impulse / continuation | 0.065% | True breakout |
| 2026-04-28 09:30 | Valid swing, away from level | n/a | 118.2% | 8.32x | Flat / fading | -0.214% | Weak move without breakout |
| 2026-04-25 17:45 | Valid swing, away from level | n/a | 135.7% | 8.31x | Flat / fading | -0.012% | Weak move without breakout |
| 2026-05-29 09:15 | Valid swing, away from level | 61.8% | 67.3% | 8.30x | Reversal | -0.356% | Liquidity sweep / reversal |
| 2026-02-18 11:00 | Valid swing, away from level | n/a | -65.2% | 8.29x | Flat / fading | -0.120% | Weak move without breakout |
| 2025-04-22 10:00 | Valid swing, away from level | n/a | -7.4% | 8.29x | Impulse / continuation | -0.284% | True breakout |
| 2025-02-14 13:30 | Valid swing, away from level | 61.8% | 66.9% | 8.29x | Flat / fading | -0.041% | Weak move without breakout |
| 2025-06-30 10:30 | Valid swing, away from level | n/a | 129.5% | 8.28x | Impulse / continuation | -0.257% | True breakout |
| 2025-06-15 10:30 | Valid swing, away from level | n/a | 163.2% | 8.27x | Reversal | 0.109% | Liquidity sweep / reversal |
| 2025-07-28 08:30 | Valid swing, away from level | n/a | -256.1% | 8.26x | Reversal | -0.282% | Liquidity sweep / reversal |
| 2025-10-27 07:00 | Valid swing, away from level | n/a | 113.2% | 8.24x | Impulse / continuation | -0.443% | True breakout |
| 2025-02-06 10:45 | Valid swing, away from level | n/a | -41.0% | 8.24x | Reversal | -0.786% | Liquidity sweep / reversal |
| 2025-02-10 22:45 | Near Fib level | 61.8% | 66.4% | 8.22x | Reversal | 0.364% | Liquidity sweep / reversal |
| 2026-01-23 07:00 | Valid swing, away from level | 38.2% | 27.9% | 8.21x | Flat / fading | 0.102% | Weak move without breakout |
| 2026-07-06 16:45 | Valid swing, away from level | n/a | 366.2% | 8.19x | Reversal | 2.491% | Liquidity sweep / reversal |
| 2025-06-17 10:00 | Near Fib level | 50.0% | 49.4% | 8.17x | Impulse / continuation | 0.506% | True breakout |
| 2026-04-29 10:15 | Valid swing, away from level | n/a | 107.5% | 8.17x | Flat / fading | 0.058% | Weak move without breakout |
| 2026-07-20 07:15 | Near Fib level | 38.2% | 38.9% | 8.16x | Impulse / continuation | -0.185% | True breakout |
| 2025-08-08 23:15 | Valid swing, away from level | n/a | -13.2% | 8.14x | Impulse / continuation | 0.873% | True breakout |
| 2025-12-08 07:00 | Valid swing, away from level | n/a | -30.6% | 8.13x | Impulse / continuation | 0.168% | True breakout |
| 2025-04-28 14:15 | Valid swing, away from level | n/a | 127.6% | 8.13x | Flat / fading | 0.012% | Position building in range |
| 2026-04-07 08:45 | Valid swing, away from level | 78.6% | 96.8% | 8.10x | Flat / fading | -0.112% | Position building in range |
| 2026-01-21 13:15 | Valid swing, away from level | n/a | -135.7% | 8.09x | Impulse / continuation | 0.253% | True breakout |
| 2025-06-26 07:00 | Valid swing, away from level | n/a | -68.7% | 8.08x | Flat / fading | -0.147% | Weak move without breakout |
| 2025-02-07 10:00 | Near Fib level | 50.0% | 45.6% | 8.07x | Impulse -> reversal | 0.128% | False breakout |
| 2024-12-28 10:00 | Valid swing, away from level | n/a | -23.9% | 8.07x | Impulse / continuation | 0.530% | True breakout |
| 2026-04-28 10:00 | Valid swing, away from level | n/a | 129.1% | 8.05x | Reversal | -0.132% | Liquidity sweep / reversal |
| 2025-11-18 23:30 | Valid swing, away from level | n/a | 257.1% | 8.04x | Reversal | 1.306% | Liquidity sweep / reversal |
| 2026-07-29 10:45 | Valid swing, away from level | n/a | -32.2% | 8.04x | Impulse / continuation | -0.023% | True breakout |
| 2024-10-03 10:00 | Near Fib level | 61.8% | 62.9% | 8.03x | Reversal | -0.040% | Liquidity sweep / reversal |
| 2025-07-17 10:00 | Golden zone 50-61.8% | 61.8% | 58.9% | 7.98x | Flat / fading | -0.060% | Weak move without breakout |
| 2025-08-31 18:30 | Valid swing, away from level | 38.2% | 26.4% | 7.95x | Reversal | 0.294% | Liquidity sweep / reversal |
| 2026-08-31 18:15 | Valid swing, away from level | n/a | -172.0% | 7.95x | Impulse / continuation | -0.016% | True breakout |
| 2025-05-19 19:45 | Near Fib level | 78.6% | 77.4% | 7.95x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2024-10-23 22:00 | Valid swing, away from level | n/a | 300.0% | 7.93x | Flat / fading | 0.000% | Position building in range |
| 2025-10-09 09:00 | Valid swing, away from level | n/a | 161.4% | 7.90x | Impulse -> reversal | 1.335% | False breakout |
| 2025-11-18 08:15 | Valid swing, away from level | n/a | 183.3% | 7.90x | Flat / fading | 0.124% | Position building in range |
| 2026-02-10 07:00 | Near Fib level | 50.0% | 47.0% | 7.90x | Flat / fading | 0.042% | Weak move without breakout |
| 2026-03-09 07:00 | Valid swing, away from level | n/a | 117.2% | 7.88x | Reversal | 0.386% | Liquidity sweep / reversal |
| 2024-11-11 10:00 | Valid swing, away from level | n/a | -213.7% | 7.87x | Flat / fading | 0.622% | Weak move without breakout |
| 2025-08-01 07:00 | Valid swing, away from level | n/a | -30.5% | 7.86x | Impulse / continuation | 0.240% | True breakout |
| 2026-02-20 12:45 | Valid swing, away from level | n/a | 117.2% | 7.86x | Impulse / continuation | -0.086% | True breakout |
| 2025-07-09 09:45 | Valid swing, away from level | n/a | -27.5% | 7.84x | Reversal | -0.302% | Liquidity sweep / reversal |
| 2024-12-09 10:00 | Golden zone 50-61.8% | 50.0% | 51.6% | 7.83x | Flat / fading | 0.321% | Position building in range |
| 2025-03-25 11:00 | Valid swing, away from level | 38.2% | 5.6% | 7.83x | Reversal | -0.050% | Liquidity sweep / reversal |
| 2026-02-09 10:00 | Valid swing, away from level | n/a | 306.7% | 7.83x | Flat / fading | -0.159% | Weak move without breakout |
| 2025-11-03 09:00 | Valid swing, away from level | n/a | -128.7% | 7.82x | Impulse / continuation | 0.558% | True breakout |
| 2026-03-17 07:00 | Valid swing, away from level | n/a | -16.7% | 7.81x | Impulse / continuation | -0.024% | True breakout |
| 2025-07-02 09:30 | Valid swing, away from level | n/a | 110.2% | 7.80x | Reversal | -0.031% | Liquidity sweep / reversal |
| 2025-11-17 10:00 | Valid swing, away from level | 38.2% | 7.7% | 7.80x | Impulse / continuation | 0.445% | True breakout |
| 2025-10-15 10:15 | Valid swing, away from level | n/a | 123.5% | 7.80x | Flat / fading | 0.359% | Weak move without breakout |
| 2025-01-22 10:00 | Near Fib level | 78.6% | 77.7% | 7.78x | Flat / fading | 0.158% | Weak move without breakout |
| 2024-11-02 10:00 | Valid swing, away from level | n/a | -40.4% | 7.77x | Flat / fading | -0.179% | Position building in range |
| 2025-09-07 11:45 | Valid swing, away from level | n/a | -17.6% | 7.77x | Impulse / continuation | 0.042% | True breakout |
| 2025-04-21 10:30 | Valid swing, away from level | n/a | -42.5% | 7.75x | Flat / fading | 0.081% | Position building in range |
| 2025-11-12 10:00 | Valid swing, away from level | n/a | 122.0% | 7.74x | Flat / fading | -0.081% | Weak move without breakout |
| 2026-08-27 10:00 | Valid swing, away from level | 78.6% | 85.9% | 7.73x | Reversal | 0.298% | Liquidity sweep / reversal |
| 2026-07-03 10:45 | Valid swing, away from level | n/a | 946.2% | 7.73x | Flat / fading | 0.731% | Position building in range |
| 2025-07-24 10:30 | Valid swing, away from level | 61.8% | 67.6% | 7.71x | Impulse / continuation | -0.636% | True breakout |
| 2024-10-22 10:15 | Valid swing, away from level | 78.6% | 73.0% | 7.70x | Impulse / continuation | -0.445% | True breakout |
| 2025-11-03 10:00 | Valid swing, away from level | n/a | -217.0% | 7.69x | Impulse / continuation | 0.100% | True breakout |
| 2026-05-12 10:30 | Valid swing, away from level | n/a | -23.5% | 7.66x | Impulse / continuation | 0.199% | True breakout |
| 2026-03-15 17:45 | Near Fib level | 61.8% | 66.7% | 7.65x | Reversal | 0.154% | Liquidity sweep / reversal |
| 2025-08-28 20:00 | Valid swing, away from level | n/a | 202.0% | 7.64x | Impulse / continuation | -0.189% | True breakout |
| 2026-06-02 11:00 | Valid swing, away from level | n/a | -47.5% | 7.63x | Flat / fading | -0.059% | Weak move without breakout |
| 2025-07-29 10:00 | Near Fib level | 61.8% | 64.8% | 7.61x | Reversal | -0.313% | Liquidity sweep / reversal |
| 2025-02-12 20:30 | Valid swing, away from level | n/a | -372.6% | 7.57x | Flat / fading | -0.138% | Position building in range |
| 2024-11-29 10:00 | Valid swing, away from level | n/a | 133.6% | 7.56x | Reversal | 0.755% | Liquidity sweep / reversal |
| 2026-07-02 09:45 | Valid swing, away from level | n/a | 115.7% | 7.55x | Flat / fading | -0.030% | Position building in range |
| 2024-11-05 10:00 | Near Fib level | 38.2% | 36.2% | 7.55x | Reversal | -0.695% | Liquidity sweep / reversal |
| 2025-07-20 10:00 | Valid swing, away from level | 38.2% | 32.9% | 7.52x | Impulse / continuation | 0.042% | True breakout |
| 2025-10-30 09:45 | Valid swing, away from level | n/a | -143.9% | 7.52x | Impulse / continuation | 0.211% | True breakout |
| 2025-11-27 17:00 | Valid swing, away from level | n/a | 191.5% | 7.51x | Impulse / continuation | -0.555% | True breakout |
| 2025-10-08 10:00 | Near Fib level | 50.0% | 47.0% | 7.51x | Impulse / continuation | -0.237% | True breakout |
| 2026-05-22 10:15 | Valid swing, away from level | n/a | -61.4% | 7.50x | Impulse -> reversal | -0.115% | False breakout |
| 2024-10-04 10:30 | Valid swing, away from level | n/a | -20.2% | 7.49x | Flat / fading | -0.173% | Weak move without breakout |
| 2025-12-22 10:15 | Valid swing, away from level | n/a | 219.0% | 7.49x | Flat / fading | -0.013% | Weak move without breakout |
| 2026-02-16 10:00 | Valid swing, away from level | n/a | -506.7% | 7.47x | Flat / fading | 0.176% | Weak move without breakout |
| 2026-02-11 12:45 | Valid swing, away from level | n/a | -72.9% | 7.47x | Flat / fading | -0.169% | Position building in range |
| 2025-04-15 09:15 | Golden zone 50-61.8% | 50.0% | 55.7% | 7.47x | Flat / fading | 0.115% | Weak move without breakout |
| 2025-02-10 07:00 | Valid swing, away from level | n/a | -250.0% | 7.46x | Impulse / continuation | 0.440% | True breakout |
| 2025-01-09 10:30 | Valid swing, away from level | n/a | -18.7% | 7.46x | Impulse / continuation | -1.162% | True breakout |
| 2025-06-11 10:00 | Valid swing, away from level | n/a | -34.2% | 7.46x | Impulse / continuation | 0.296% | True breakout |
| 2024-12-20 10:00 | Valid swing, away from level | 38.2% | 24.0% | 7.45x | Reversal | 0.062% | Liquidity sweep / reversal |
| 2026-05-04 09:00 | Valid swing, away from level | n/a | -234.0% | 7.42x | Flat / fading | 0.058% | Weak move without breakout |
| 2025-01-09 10:15 | Valid swing, away from level | n/a | -24.1% | 7.42x | Impulse / continuation | -0.389% | True breakout |
| 2025-02-17 07:00 | Valid swing, away from level | n/a | -211.4% | 7.41x | Flat / fading | 0.041% | Position building in range |
| 2025-09-15 07:00 | Valid swing, away from level | n/a | -32.0% | 7.41x | Flat / fading | 0.038% | Weak move without breakout |
| 2026-07-06 16:30 | Valid swing, away from level | n/a | 241.0% | 7.41x | Impulse / continuation | 0.763% | True breakout |
| 2025-02-06 10:15 | Valid swing, away from level | n/a | -7.0% | 7.40x | Impulse / continuation | 0.860% | True breakout |
| 2025-11-07 10:00 | Valid swing, away from level | n/a | -19.8% | 7.39x | Flat / fading | -0.094% | Weak move without breakout |
| 2025-10-28 09:00 | Valid swing, away from level | n/a | -14.6% | 7.37x | Impulse / continuation | 0.049% | True breakout |
| 2025-05-14 22:45 | Valid swing, away from level | n/a | 124.5% | 7.37x | Impulse / continuation | -1.895% | True breakout |
| 2025-02-12 20:00 | Valid swing, away from level | n/a | -76.5% | 7.34x | Impulse / continuation | 3.176% | True breakout |
| 2025-12-19 10:15 | Valid swing, away from level | 38.2% | 18.5% | 7.34x | Reversal | -0.062% | Liquidity sweep / reversal |
| 2025-11-17 08:45 | Valid swing, away from level | n/a | 130.8% | 7.33x | Flat / fading | 0.069% | Weak move without breakout |
| 2025-07-21 07:15 | Valid swing, away from level | n/a | -44.0% | 7.30x | Impulse / continuation | 0.268% | True breakout |
| 2026-03-24 22:45 | Golden zone 50-61.8% | 50.0% | 52.6% | 7.29x | Flat / fading | -0.066% | Weak move without breakout |
| 2025-09-23 22:00 | Valid swing, away from level | n/a | 123.9% | 7.28x | Flat / fading | -0.240% | Weak move without breakout |
| 2025-12-25 10:30 | Valid swing, away from level | n/a | 135.7% | 7.28x | Impulse / continuation | 0.673% | True breakout |
| 2025-12-26 09:30 | Valid swing, away from level | n/a | -342.9% | 7.27x | Impulse / continuation | 0.213% | True breakout |
| 2025-07-03 10:00 | Near Fib level | 78.6% | 76.0% | 7.26x | Reversal | 0.337% | Liquidity sweep / reversal |
| 2025-12-11 18:00 | Valid swing, away from level | 38.2% | 22.6% | 7.26x | Reversal | 0.883% | Liquidity sweep / reversal |
| 2025-12-17 10:00 | Valid swing, away from level | n/a | 113.6% | 7.24x | Impulse / continuation | 0.160% | True breakout |
| 2025-07-29 21:00 | Valid swing, away from level | n/a | 190.9% | 7.23x | Flat / fading | 0.044% | Position building in range |
| 2025-08-06 10:30 | Valid swing, away from level | 38.2% | 30.3% | 7.22x | Flat / fading | 0.081% | Position building in range |
| 2025-01-24 10:00 | Valid swing, away from level | n/a | -17.9% | 7.22x | Reversal | 0.298% | Liquidity sweep / reversal |
| 2025-07-15 12:45 | Valid swing, away from level | n/a | -76.4% | 7.21x | Flat / fading | -0.168% | Position building in range |
| 2025-04-25 09:00 | Valid swing, away from level | n/a | -11.7% | 7.19x | Impulse / continuation | 0.160% | True breakout |
| 2024-10-01 10:15 | Valid swing, away from level | n/a | 171.7% | 7.18x | Reversal | -0.649% | Liquidity sweep / reversal |
| 2026-09-14 18:00 | Valid swing, away from level | 38.2% | 0.4% | 7.17x | Impulse / continuation | 0.204% | True breakout |
| 2025-08-25 10:15 | Valid swing, away from level | n/a | 135.3% | 7.17x | Impulse / continuation | -0.095% | True breakout |
| 2025-03-03 07:30 | Valid swing, away from level | n/a | 226.5% | 7.17x | Impulse / continuation | 0.018% | True breakout |
| 2026-04-01 10:00 | Valid swing, away from level | 38.2% | 43.4% | 7.17x | Impulse / continuation | -0.239% | True breakout |
| 2025-11-17 07:15 | Near Fib level | 38.2% | 34.5% | 7.16x | Flat / fading | -0.034% | Weak move without breakout |
| 2026-07-16 10:15 | Valid swing, away from level | n/a | 268.5% | 7.16x | Flat / fading | 0.643% | Position building in range |
| 2026-03-26 07:00 | Near Fib level | 78.6% | 79.4% | 7.16x | Reversal | 0.042% | Liquidity sweep / reversal |
| 2025-10-22 22:15 | Valid swing, away from level | n/a | 166.5% | 7.14x | Reversal | 0.777% | Liquidity sweep / reversal |
| 2025-12-04 07:00 | Valid swing, away from level | n/a | -58.4% | 7.13x | Reversal | -0.308% | Liquidity sweep / reversal |
| 2025-04-21 10:00 | Valid swing, away from level | n/a | -18.4% | 7.12x | Impulse / continuation | 0.195% | True breakout |
| 2025-08-15 10:00 | Valid swing, away from level | 78.6% | 70.7% | 7.12x | Flat / fading | -0.006% | Weak move without breakout |
| 2026-07-06 07:00 | Near Fib level | 38.2% | 35.6% | 7.11x | Flat / fading | -0.142% | Weak move without breakout |
| 2024-11-27 10:15 | Valid swing, away from level | n/a | 119.5% | 7.11x | Impulse / continuation | -0.278% | True breakout |
| 2025-03-03 07:15 | Valid swing, away from level | n/a | 172.4% | 7.11x | Reversal | -0.565% | Liquidity sweep / reversal |
| 2026-01-21 12:15 | Near Fib level | 38.2% | 37.1% | 7.11x | Impulse / continuation | 0.735% | True breakout |
| 2026-04-04 16:45 | Valid swing, away from level | 38.2% | 25.6% | 7.11x | Flat / fading | 0.025% | Weak move without breakout |
| 2025-09-09 12:30 | Valid swing, away from level | n/a | -4.2% | 7.09x | Impulse / continuation | -0.083% | True breakout |
| 2026-06-15 10:00 | Valid swing, away from level | n/a | -3612.5% | 7.09x | Flat / fading | -0.219% | Weak move without breakout |
| 2025-02-12 07:00 | Valid swing, away from level | n/a | -42.6% | 7.09x | Impulse / continuation | 0.138% | True breakout |
| 2025-11-13 09:00 | Golden zone 50-61.8% | 50.0% | 52.3% | 7.09x | Flat / fading | -0.081% | Weak move without breakout |
| 2024-11-12 10:30 | Valid swing, away from level | n/a | 139.2% | 7.07x | Flat / fading | 0.008% | Weak move without breakout |
| 2025-05-17 18:15 | Valid swing, away from level | n/a | -488.5% | 7.05x | Impulse / continuation | 0.996% | True breakout |
| 2024-10-14 10:15 | Valid swing, away from level | n/a | 117.1% | 7.04x | Flat / fading | -0.138% | Position building in range |
| 2025-06-15 10:00 | Valid swing, away from level | n/a | -10.5% | 7.03x | Impulse / continuation | -0.248% | True breakout |
| 2026-05-14 10:45 | Near Fib level | 38.2% | 43.0% | 7.03x | Impulse / continuation | -0.152% | True breakout |
| 2025-03-12 10:45 | Near Fib level | 78.6% | 80.8% | 7.03x | Flat / fading | -0.106% | Position building in range |
| 2026-08-17 09:15 | Valid swing, away from level | n/a | 252.6% | 7.02x | Reversal | 0.899% | Liquidity sweep / reversal |
| 2025-07-31 10:15 | Near Fib level | 61.8% | 63.6% | 7.02x | Flat / fading | -0.140% | Weak move without breakout |
| 2026-06-02 10:45 | Valid swing, away from level | n/a | -16.1% | 7.01x | Impulse / continuation | 0.223% | True breakout |
| 2026-07-02 09:00 | Near Fib level | 78.6% | 80.1% | 7.01x | Reversal | -0.605% | Liquidity sweep / reversal |
| 2025-08-28 20:30 | Valid swing, away from level | n/a | 232.8% | 7.01x | Flat / fading | 0.113% | Position building in range |
| 2026-02-21 17:45 | Golden zone 50-61.8% | 50.0% | 50.0% | 6.97x | Flat / fading | 0.029% | Position building in range |
| 2025-08-29 10:15 | Valid swing, away from level | 78.6% | 71.9% | 6.97x | Flat / fading | -0.012% | Weak move without breakout |
| 2026-07-20 15:45 | Valid swing, away from level | n/a | -103.1% | 6.96x | Impulse / continuation | 0.486% | True breakout |
| 2026-02-06 16:45 | Valid swing, away from level | n/a | 172.5% | 6.95x | Flat / fading | 0.006% | Weak move without breakout |
| 2025-05-12 07:00 | Valid swing, away from level | 38.2% | 16.9% | 6.94x | Reversal | 0.497% | Liquidity sweep / reversal |
| 2026-06-18 09:00 | Valid swing, away from level | 78.6% | 93.9% | 6.94x | Impulse / continuation | -0.426% | True breakout |
| 2026-09-14 18:15 | Valid swing, away from level | n/a | -35.0% | 6.94x | Flat / fading | -0.195% | Position building in range |
| 2025-03-02 10:45 | Near Fib level | 38.2% | 43.0% | 6.94x | Flat / fading | -0.031% | Weak move without breakout |
| 2026-06-08 10:30 | Valid swing, away from level | n/a | 113.4% | 6.94x | Impulse / continuation | -0.182% | True breakout |
| 2025-05-29 15:45 | Golden zone 50-61.8% | 50.0% | 54.6% | 6.92x | Flat / fading | -0.337% | Weak move without breakout |
| 2026-07-12 10:00 | Valid swing, away from level | 78.6% | 87.3% | 6.92x | Flat / fading | -0.073% | Position building in range |
| 2024-12-12 10:00 | Near Fib level | 38.2% | 35.1% | 6.92x | Reversal | 0.461% | Liquidity sweep / reversal |
| 2026-02-18 18:15 | Valid swing, away from level | n/a | -88.0% | 6.92x | Flat / fading | -0.164% | Position building in range |
| 2025-02-03 10:30 | Valid swing, away from level | 78.6% | 99.5% | 6.91x | Flat / fading | 0.013% | Position building in range |
| 2024-12-02 10:15 | Valid swing, away from level | n/a | -59.0% | 6.90x | Impulse / continuation | -0.356% | True breakout |
| 2026-09-14 16:00 | Valid swing, away from level | 38.2% | 43.8% | 6.90x | Flat / fading | -0.205% | Position building in range |
| 2026-06-01 19:30 | Near Fib level | 38.2% | 38.6% | 6.90x | Flat / fading | -0.013% | Position building in range |
| 2026-09-22 10:15 | Valid swing, away from level | n/a | -11.3% | 6.87x | Impulse / continuation | 0.178% | True breakout |
| 2026-09-11 07:00 | Golden zone 50-61.8% | 61.8% | 57.1% | 6.86x | Flat / fading | 0.008% | Position building in range |
| 2025-04-26 16:30 | Valid swing, away from level | 38.2% | 24.4% | 6.85x | Impulse / continuation | 0.103% | True breakout |
| 2025-03-17 07:00 | Valid swing, away from level | n/a | -2745.5% | 6.84x | Impulse / continuation | 0.684% | True breakout |
| 2024-11-18 10:00 | Golden zone 50-61.8% | 50.0% | 55.9% | 6.84x | Impulse / continuation | 0.793% | True breakout |
| 2026-09-01 21:15 | Valid swing, away from level | n/a | 154.3% | 6.84x | Flat / fading | -0.119% | Position building in range |
| 2025-12-05 11:15 | Valid swing, away from level | n/a | -139.8% | 6.83x | Impulse / continuation | 0.342% | True breakout |
| 2026-05-16 17:45 | Near Fib level | 61.8% | 64.9% | 6.83x | Impulse / continuation | -0.097% | True breakout |
| 2025-06-06 10:30 | Valid swing, away from level | n/a | -88.6% | 6.82x | Flat / fading | -0.036% | Weak move without breakout |
| 2026-06-09 09:00 | Valid swing, away from level | 38.2% | 12.4% | 6.82x | Flat / fading | -0.110% | Position building in range |
| 2024-10-08 10:15 | Near Fib level | 78.6% | 82.2% | 6.82x | Flat / fading | -0.377% | Weak move without breakout |
| 2026-01-23 20:30 | Valid swing, away from level | 38.2% | 5.8% | 6.81x | Impulse / continuation | 0.120% | True breakout |
| 2026-06-05 16:45 | Valid swing, away from level | n/a | 102.5% | 6.80x | Flat / fading | -0.167% | Position building in range |
| 2026-02-20 13:00 | Valid swing, away from level | n/a | 145.9% | 6.79x | Flat / fading | 0.218% | Position building in range |
| 2025-12-15 08:15 | Valid swing, away from level | n/a | -452.4% | 6.78x | Impulse / continuation | 0.293% | True breakout |
| 2025-02-25 09:45 | Valid swing, away from level | n/a | -14.5% | 6.78x | Flat / fading | -0.281% | Position building in range |
| 2026-06-24 07:00 | Valid swing, away from level | 38.2% | 17.2% | 6.77x | Flat / fading | 0.086% | Position building in range |
| 2024-11-12 10:15 | Valid swing, away from level | n/a | 107.7% | 6.76x | Impulse / continuation | -0.023% | True breakout |
| 2026-05-22 10:30 | Valid swing, away from level | n/a | -53.4% | 6.75x | Impulse / continuation | -0.235% | True breakout |
| 2025-02-21 14:15 | Valid swing, away from level | n/a | 204.7% | 6.74x | Flat / fading | 0.265% | Weak move without breakout |
| 2025-03-07 10:15 | Valid swing, away from level | n/a | -137.9% | 6.73x | Impulse / continuation | 0.430% | True breakout |
| 2025-07-07 07:30 | Valid swing, away from level | n/a | 111.1% | 6.72x | Flat / fading | -0.094% | Weak move without breakout |
| 2026-05-04 07:15 | Valid swing, away from level | n/a | -144.7% | 6.72x | Impulse / continuation | 0.007% | True breakout |
| 2026-09-04 09:00 | Valid swing, away from level | 38.2% | 0.9% | 6.71x | Flat / fading | -0.091% | Weak move without breakout |
| 2025-12-09 10:00 | Valid swing, away from level | 38.2% | 14.9% | 6.71x | Reversal | -0.088% | Liquidity sweep / reversal |
| 2025-05-04 10:00 | Valid swing, away from level | n/a | -6.6% | 6.71x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2025-04-17 11:15 | Valid swing, away from level | n/a | -53.8% | 6.70x | Flat / fading | -0.399% | Weak move without breakout |
| 2026-05-03 12:30 | Valid swing, away from level | n/a | -192.3% | 6.70x | Flat / fading | -0.072% | Position building in range |
| 2025-03-24 10:00 | Valid swing, away from level | n/a | 101.8% | 6.69x | Impulse / continuation | -0.022% | True breakout |
| 2026-01-29 09:30 | Valid swing, away from level | n/a | -3.2% | 6.69x | Impulse / continuation | 0.449% | True breakout |
| 2026-02-16 07:00 | Valid swing, away from level | n/a | -21.3% | 6.68x | Impulse / continuation | 0.165% | True breakout |
| 2025-06-19 10:30 | Valid swing, away from level | n/a | -42.1% | 6.68x | Flat / fading | -0.100% | Weak move without breakout |
| 2025-05-27 07:30 | Valid swing, away from level | n/a | 112.0% | 6.68x | Impulse -> reversal | 0.499% | False breakout |
| 2025-07-14 07:30 | Valid swing, away from level | n/a | 100.9% | 6.67x | Reversal | -0.123% | Liquidity sweep / reversal |
| 2025-07-09 10:00 | Valid swing, away from level | 38.2% | 11.0% | 6.67x | Impulse / continuation | -0.170% | True breakout |
| 2025-10-14 10:00 | Valid swing, away from level | n/a | 120.9% | 6.67x | Impulse / continuation | 0.214% | True breakout |
| 2026-06-08 15:45 | Valid swing, away from level | n/a | 381.4% | 6.67x | Flat / fading | -0.226% | Weak move without breakout |
| 2025-12-17 10:15 | Valid swing, away from level | n/a | 159.1% | 6.66x | Reversal | 0.197% | Liquidity sweep / reversal |
| 2025-10-02 10:00 | Valid swing, away from level | n/a | 220.2% | 6.66x | Flat / fading | 0.358% | Weak move without breakout |
| 2025-12-15 09:00 | Valid swing, away from level | n/a | -623.8% | 6.65x | Impulse -> reversal | -0.311% | False breakout |
| 2026-08-13 07:00 | Valid swing, away from level | n/a | 147.5% | 6.65x | Flat / fading | 0.022% | Position building in range |
| 2026-08-26 13:00 | Valid swing, away from level | 78.6% | 85.6% | 6.65x | Flat / fading | 0.104% | Position building in range |
| 2025-02-24 10:00 | Valid swing, away from level | n/a | -0.6% | 6.64x | Reversal | -0.087% | Liquidity sweep / reversal |
| 2025-12-09 14:15 | Valid swing, away from level | n/a | -92.5% | 6.64x | Impulse / continuation | 0.187% | True breakout |
| 2025-03-18 18:15 | Valid swing, away from level | n/a | -233.0% | 6.64x | Reversal | 0.441% | Liquidity sweep / reversal |
| 2026-01-16 10:30 | Valid swing, away from level | n/a | -70.7% | 6.63x | Impulse / continuation | 0.545% | True breakout |
| 2025-06-17 10:15 | Valid swing, away from level | 38.2% | 26.8% | 6.63x | Impulse / continuation | 0.316% | True breakout |
| 2025-04-11 09:15 | Valid swing, away from level | n/a | -6.6% | 6.62x | Flat / fading | 0.082% | Weak move without breakout |
| 2025-03-24 21:00 | Valid swing, away from level | 78.6% | 92.5% | 6.62x | Impulse / continuation | -0.033% | True breakout |
| 2024-10-09 10:15 | Near Fib level | 61.8% | 64.9% | 6.62x | Impulse -> reversal | 0.355% | False breakout |
| 2026-03-02 17:45 | Valid swing, away from level | n/a | 113.1% | 6.59x | Flat / fading | -0.053% | Weak move without breakout |
| 2025-06-29 16:30 | Valid swing, away from level | n/a | -61.9% | 6.59x | Reversal | -0.153% | Liquidity sweep / reversal |
| 2025-03-20 07:00 | Valid swing, away from level | n/a | -42.3% | 6.59x | Impulse / continuation | 0.147% | True breakout |
| 2025-03-16 17:00 | Valid swing, away from level | n/a | -1936.4% | 6.58x | Flat / fading | -0.109% | Weak move without breakout |
| 2026-08-25 07:15 | Valid swing, away from level | n/a | -5.0% | 6.58x | Flat / fading | 0.040% | Position building in range |
| 2026-09-18 07:00 | Near Fib level | 38.2% | 42.7% | 6.57x | Impulse / continuation | 0.323% | True breakout |
| 2024-11-26 10:00 | Near Fib level | 78.6% | 79.3% | 6.57x | Reversal | 1.232% | Liquidity sweep / reversal |
| 2024-09-30 10:15 | Valid swing, away from level | n/a | -141.0% | 6.56x | Flat / fading | -0.056% | Weak move without breakout |
| 2025-07-01 10:00 | Near Fib level | 38.2% | 35.0% | 6.56x | Reversal | 0.330% | Liquidity sweep / reversal |
| 2026-05-15 07:00 | Valid swing, away from level | n/a | 102.0% | 6.55x | Flat / fading | 0.083% | Weak move without breakout |
| 2025-07-07 12:30 | Valid swing, away from level | n/a | -81.0% | 6.55x | Flat / fading | -0.186% | Weak move without breakout |
| 2026-04-24 12:00 | Valid swing, away from level | n/a | 141.1% | 6.54x | Reversal | 0.080% | Liquidity sweep / reversal |
| 2025-12-22 10:00 | Valid swing, away from level | n/a | 146.4% | 6.54x | Impulse / continuation | -0.428% | True breakout |
| 2026-08-09 16:00 | Valid swing, away from level | 38.2% | 30.6% | 6.53x | Flat / fading | 0.007% | Position building in range |
| 2024-11-26 10:15 | Valid swing, away from level | 61.8% | 67.7% | 6.53x | Impulse / continuation | 0.990% | True breakout |
| 2026-03-02 10:15 | Valid swing, away from level | 38.2% | 11.2% | 6.53x | Flat / fading | 0.128% | Weak move without breakout |
| 2025-12-26 09:15 | Valid swing, away from level | n/a | -200.0% | 6.52x | Impulse / continuation | 0.540% | True breakout |
| 2026-06-02 10:30 | Valid swing, away from level | n/a | -5.9% | 6.52x | Impulse / continuation | 0.421% | True breakout |
| 2025-03-11 10:00 | Valid swing, away from level | 78.6% | 85.5% | 6.51x | Reversal | 0.674% | Liquidity sweep / reversal |
| 2025-05-17 17:45 | Valid swing, away from level | n/a | -7.4% | 6.50x | Impulse / continuation | 0.881% | True breakout |
| 2026-01-20 10:00 | Valid swing, away from level | 61.8% | 68.9% | 6.48x | Impulse / continuation | -0.170% | True breakout |
| 2025-04-09 20:15 | Valid swing, away from level | 38.2% | 12.2% | 6.48x | Impulse / continuation | 2.204% | True breakout |
| 2025-11-07 07:00 | Golden zone 50-61.8% | 61.8% | 59.6% | 6.48x | Impulse / continuation | -0.014% | True breakout |
| 2025-01-29 11:15 | Valid swing, away from level | n/a | -47.7% | 6.47x | Flat / fading | -0.093% | Weak move without breakout |
| 2026-08-20 13:00 | Valid swing, away from level | n/a | 190.1% | 6.47x | Impulse / continuation | -0.343% | True breakout |
| 2025-02-05 12:45 | Valid swing, away from level | n/a | -52.4% | 6.47x | Flat / fading | -0.257% | Position building in range |
| 2025-05-11 15:45 | Valid swing, away from level | 38.2% | 22.5% | 6.47x | Flat / fading | 0.264% | Position building in range |
| 2025-10-13 10:45 | Near Fib level | 38.2% | 40.7% | 6.47x | Impulse / continuation | -0.103% | True breakout |
| 2025-10-28 11:00 | Valid swing, away from level | n/a | -93.3% | 6.46x | Impulse / continuation | 1.366% | True breakout |
| 2026-03-26 10:45 | Valid swing, away from level | n/a | 139.5% | 6.46x | Impulse / continuation | -0.337% | True breakout |
| 2025-09-29 09:00 | Valid swing, away from level | n/a | -56.5% | 6.46x | Reversal | 0.301% | Liquidity sweep / reversal |
| 2025-07-07 09:00 | Valid swing, away from level | 61.8% | 68.9% | 6.46x | Impulse / continuation | 0.012% | True breakout |
| 2024-10-18 10:00 | Valid swing, away from level | n/a | 181.2% | 6.45x | Impulse / continuation | 0.233% | True breakout |
| 2025-05-28 10:00 | Valid swing, away from level | n/a | -61.2% | 6.45x | Impulse / continuation | 0.446% | True breakout |
| 2025-07-29 20:30 | Valid swing, away from level | n/a | 113.1% | 6.45x | Impulse / continuation | -0.783% | True breakout |
| 2026-01-09 07:00 | Near Fib level | 78.6% | 75.6% | 6.45x | Impulse / continuation | 0.352% | True breakout |
| 2026-08-25 17:45 | Valid swing, away from level | n/a | -219.0% | 6.44x | Reversal | -1.380% | Liquidity sweep / reversal |
| 2025-06-18 16:15 | Valid swing, away from level | n/a | 204.2% | 6.43x | Flat / fading | 0.100% | Position building in range |
| 2025-07-23 09:45 | Valid swing, away from level | n/a | -20.2% | 6.43x | Impulse / continuation | 0.292% | True breakout |
| 2025-02-25 10:00 | Valid swing, away from level | n/a | -12.5% | 6.42x | Flat / fading | -0.167% | Weak move without breakout |
| 2026-09-17 10:30 | Valid swing, away from level | n/a | 108.6% | 6.42x | Flat / fading | 0.291% | Position building in range |
| 2025-07-13 11:15 | Valid swing, away from level | n/a | 106.3% | 6.42x | Impulse / continuation | -0.328% | True breakout |
| 2026-08-24 09:00 | Valid swing, away from level | n/a | 510.7% | 6.42x | Impulse / continuation | -0.280% | True breakout |
| 2026-03-16 10:15 | Valid swing, away from level | 38.2% | 16.1% | 6.41x | Impulse / continuation | -0.182% | True breakout |
| 2025-07-21 08:15 | Valid swing, away from level | n/a | -134.0% | 6.40x | Reversal | -0.053% | Liquidity sweep / reversal |
| 2025-08-26 09:15 | Valid swing, away from level | n/a | -87.5% | 6.40x | Impulse / continuation | 0.125% | True breakout |
| 2026-07-15 08:30 | Valid swing, away from level | n/a | 119.4% | 6.40x | Flat / fading | 0.113% | Position building in range |
| 2025-05-21 09:30 | Valid swing, away from level | 38.2% | 17.7% | 6.39x | Reversal | -0.384% | Liquidity sweep / reversal |
| 2024-09-25 12:00 | Valid swing, away from level | n/a | -140.2% | 6.39x | Impulse / continuation | 1.739% | True breakout |
| 2026-06-18 09:15 | Valid swing, away from level | n/a | 114.8% | 6.39x | Impulse / continuation | -0.183% | True breakout |
| 2025-12-05 07:00 | Golden zone 50-61.8% | 50.0% | 51.1% | 6.39x | Reversal | 0.077% | Liquidity sweep / reversal |
| 2025-10-13 10:00 | Valid swing, away from level | n/a | -440.7% | 6.38x | Reversal | -0.811% | Liquidity sweep / reversal |
| 2025-07-07 10:00 | Valid swing, away from level | 38.2% | 27.0% | 6.38x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2026-05-15 10:00 | Golden zone 50-61.8% | 50.0% | 52.4% | 6.37x | Reversal | -0.304% | Liquidity sweep / reversal |
| 2026-02-02 09:00 | Valid swing, away from level | n/a | 218.6% | 6.37x | Flat / fading | -0.060% | Weak move without breakout |
| 2025-02-04 21:30 | Valid swing, away from level | n/a | 147.4% | 6.36x | Impulse / continuation | -0.127% | True breakout |
| 2026-07-02 15:15 | Valid swing, away from level | n/a | 673.0% | 6.36x | Flat / fading | 0.223% | Position building in range |
| 2026-06-29 11:00 | Valid swing, away from level | n/a | 177.4% | 6.36x | Impulse / continuation | 1.625% | True breakout |
| 2025-03-31 07:15 | No confirmed swing | n/a | n/a | 6.35x | Reversal | 0.932% | Liquidity sweep / reversal |
| 2026-01-21 12:30 | Valid swing, away from level | 38.2% | 18.6% | 6.35x | Impulse / continuation | 0.765% | True breakout |
| 2026-01-16 16:45 | Valid swing, away from level | n/a | -22.8% | 6.33x | Reversal | -0.196% | Liquidity sweep / reversal |
| 2026-08-14 07:00 | Valid swing, away from level | n/a | 159.6% | 6.33x | Impulse / continuation | 0.662% | True breakout |
| 2024-12-30 10:15 | Valid swing, away from level | n/a | -305.3% | 6.33x | Reversal | 0.583% | Liquidity sweep / reversal |
| 2025-04-07 07:30 | Valid swing, away from level | n/a | 1921.4% | 6.32x | Flat / fading | -0.243% | Weak move without breakout |
| 2025-06-03 10:15 | Valid swing, away from level | n/a | -45.5% | 6.31x | Flat / fading | -0.056% | Weak move without breakout |
| 2025-03-07 10:00 | Valid swing, away from level | n/a | -63.2% | 6.29x | Impulse / continuation | 1.319% | True breakout |
| 2026-02-05 10:00 | Golden zone 50-61.8% | 61.8% | 58.9% | 6.29x | Impulse / continuation | 0.360% | True breakout |
| 2025-07-12 16:45 | Valid swing, away from level | n/a | 103.7% | 6.29x | Flat / fading | 0.045% | Position building in range |
| 2025-12-21 12:30 | Valid swing, away from level | n/a | 132.0% | 6.29x | Reversal | 0.031% | Liquidity sweep / reversal |
| 2024-12-05 10:00 | Near Fib level | 61.8% | 64.4% | 6.29x | Impulse / continuation | 0.398% | True breakout |
| 2025-06-10 10:00 | Valid swing, away from level | 38.2% | 32.8% | 6.27x | Impulse / continuation | -0.237% | True breakout |
| 2025-11-03 10:30 | Valid swing, away from level | n/a | -258.5% | 6.27x | Flat / fading | -0.320% | Position building in range |
| 2026-07-20 07:30 | Valid swing, away from level | 78.6% | 72.2% | 6.25x | Flat / fading | 0.106% | Position building in range |
| 2026-05-08 21:00 | Near Fib level | 38.2% | 34.7% | 6.25x | Impulse / continuation | 0.599% | True breakout |
| 2024-10-14 10:00 | Valid swing, away from level | 78.6% | 92.7% | 6.25x | Impulse / continuation | -0.176% | True breakout |
| 2026-01-14 19:00 | Valid swing, away from level | 78.6% | 98.3% | 6.24x | Flat / fading | -0.119% | Weak move without breakout |
| 2024-11-25 10:00 | Valid swing, away from level | n/a | 121.6% | 6.24x | Flat / fading | -0.168% | Weak move without breakout |
| 2026-08-11 07:30 | Valid swing, away from level | n/a | -98.6% | 6.24x | Impulse / continuation | -0.007% | True breakout |
| 2024-12-17 10:00 | Valid swing, away from level | n/a | 122.6% | 6.23x | Flat / fading | -0.036% | Weak move without breakout |
| 2024-10-09 10:30 | Near Fib level | 78.6% | 80.7% | 6.23x | Reversal | 0.633% | Liquidity sweep / reversal |
| 2025-07-08 10:15 | Valid swing, away from level | 78.6% | 88.5% | 6.23x | Reversal | 0.257% | Liquidity sweep / reversal |
| 2026-08-21 11:30 | Valid swing, away from level | n/a | -13.7% | 6.22x | Flat / fading | 0.133% | Position building in range |
| 2025-04-22 20:30 | Valid swing, away from level | n/a | -14.2% | 6.22x | Impulse / continuation | 0.442% | True breakout |
| 2025-02-26 13:30 | Valid swing, away from level | n/a | 364.5% | 6.22x | Flat / fading | 0.510% | Position building in range |
| 2024-10-29 10:00 | Valid swing, away from level | 78.6% | 87.7% | 6.22x | Reversal | -0.278% | Liquidity sweep / reversal |
| 2026-03-23 09:45 | Valid swing, away from level | n/a | 136.8% | 6.22x | Reversal | 0.282% | Liquidity sweep / reversal |
| 2026-03-30 09:45 | Golden zone 50-61.8% | 61.8% | 57.4% | 6.22x | Impulse / continuation | -0.359% | True breakout |
| 2026-09-14 10:15 | Valid swing, away from level | n/a | -125.8% | 6.21x | Flat / fading | -0.174% | Weak move without breakout |
| 2026-01-12 10:00 | Valid swing, away from level | n/a | -13.1% | 6.20x | Reversal | -0.012% | Liquidity sweep / reversal |
| 2026-08-03 07:15 | Valid swing, away from level | n/a | -102.8% | 6.19x | Flat / fading | 0.260% | Weak move without breakout |
| 2026-01-19 07:15 | Valid swing, away from level | n/a | -20.8% | 6.19x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2025-08-14 11:45 | Valid swing, away from level | n/a | 121.8% | 6.19x | Flat / fading | 0.206% | Weak move without breakout |
| 2026-04-02 15:45 | Valid swing, away from level | 78.6% | 94.5% | 6.18x | Reversal | 0.533% | Liquidity sweep / reversal |
| 2025-07-14 07:15 | Valid swing, away from level | n/a | 107.4% | 6.18x | Flat / fading | -0.143% | Weak move without breakout |
| 2026-06-30 12:15 | Valid swing, away from level | n/a | -87.6% | 6.18x | Flat / fading | -0.015% | Weak move without breakout |
| 2024-11-01 10:15 | Near Fib level | 38.2% | 41.8% | 6.17x | Reversal | -0.437% | Liquidity sweep / reversal |
| 2025-04-25 13:30 | Valid swing, away from level | n/a | -60.3% | 6.17x | Reversal | 0.558% | Liquidity sweep / reversal |
| 2026-04-29 10:30 | Valid swing, away from level | n/a | 105.8% | 6.16x | Reversal | 0.271% | Liquidity sweep / reversal |
| 2025-09-07 13:30 | Valid swing, away from level | n/a | -135.3% | 6.16x | Impulse / continuation | 0.000% | True breakout |
| 2025-11-10 10:00 | Valid swing, away from level | n/a | -18.8% | 6.16x | Flat / fading | 0.100% | Weak move without breakout |
| 2025-11-30 18:45 | Valid swing, away from level | n/a | -3.9% | 6.15x | Impulse / continuation | 0.096% | True breakout |
| 2025-10-13 09:30 | Valid swing, away from level | n/a | -285.2% | 6.15x | Flat / fading | -0.082% | Weak move without breakout |
| 2026-03-15 10:15 | Valid swing, away from level | n/a | -72.0% | 6.15x | Flat / fading | -0.030% | Weak move without breakout |
| 2026-05-13 20:15 | Valid swing, away from level | n/a | -39.7% | 6.14x | Impulse / continuation | 0.195% | True breakout |
| 2025-10-22 22:30 | Valid swing, away from level | n/a | 122.0% | 6.14x | Impulse / continuation | 0.088% | True breakout |
| 2025-12-11 09:45 | Valid swing, away from level | n/a | -81.6% | 6.14x | Flat / fading | -0.074% | Weak move without breakout |
| 2026-09-21 18:00 | Valid swing, away from level | n/a | -33.8% | 6.13x | Flat / fading | -0.273% | Position building in range |
| 2024-10-15 10:30 | Valid swing, away from level | n/a | -2.4% | 6.13x | Impulse / continuation | 0.343% | True breakout |
| 2025-04-04 07:00 | Valid swing, away from level | 38.2% | 24.8% | 6.13x | Impulse / continuation | -0.651% | True breakout |
| 2026-09-10 11:00 | Valid swing, away from level | n/a | -71.4% | 6.13x | Impulse / continuation | 0.031% | True breakout |
| 2026-05-05 12:30 | Valid swing, away from level | n/a | -28.7% | 6.12x | Flat / fading | 0.340% | Weak move without breakout |
| 2024-12-03 10:15 | Valid swing, away from level | 78.6% | 86.1% | 6.12x | Impulse / continuation | -1.138% | True breakout |
| 2025-10-08 10:15 | Near Fib level | 78.6% | 77.1% | 6.12x | Impulse / continuation | -0.105% | True breakout |
| 2025-10-27 09:45 | Valid swing, away from level | n/a | 155.1% | 6.12x | Reversal | 0.702% | Liquidity sweep / reversal |
| 2026-07-13 10:00 | Valid swing, away from level | n/a | -18.6% | 6.11x | Impulse / continuation | 1.508% | True breakout |
| 2025-11-24 23:30 | Near Fib level | 61.8% | 65.5% | 6.10x | Impulse / continuation | -0.039% | True breakout |
| 2025-06-01 14:00 | Near Fib level | 78.6% | 75.6% | 6.10x | Impulse / continuation | -0.505% | True breakout |
| 2026-08-22 10:00 | Golden zone 50-61.8% | 50.0% | 51.6% | 6.10x | Flat / fading | -0.126% | Weak move without breakout |
| 2026-07-30 10:30 | Valid swing, away from level | n/a | -127.4% | 6.09x | Reversal | -0.677% | Liquidity sweep / reversal |
| 2025-05-19 16:45 | Valid swing, away from level | 78.6% | 95.5% | 6.07x | Impulse / continuation | 0.000% | True breakout |
| 2026-02-12 12:15 | Valid swing, away from level | n/a | -4.7% | 6.06x | Impulse / continuation | 0.312% | True breakout |
| 2024-09-26 10:00 | Near Fib level | 78.6% | 77.7% | 6.05x | Impulse / continuation | 0.997% | True breakout |
| 2025-08-26 10:00 | Valid swing, away from level | n/a | -162.5% | 6.05x | Flat / fading | -0.083% | Weak move without breakout |
| 2025-04-16 11:15 | Golden zone 50-61.8% | 50.0% | 55.2% | 6.05x | Flat / fading | 0.045% | Weak move without breakout |
| 2026-08-31 08:30 | Valid swing, away from level | n/a | -172.7% | 6.04x | Flat / fading | 0.104% | Weak move without breakout |
| 2026-09-04 23:30 | Valid swing, away from level | 38.2% | 1.5% | 6.03x | Impulse / continuation | 0.431% | True breakout |
| 2026-06-26 15:00 | Valid swing, away from level | n/a | -40.6% | 6.02x | Impulse / continuation | 0.558% | True breakout |
| 2025-07-23 10:00 | Valid swing, away from level | n/a | -33.0% | 6.02x | Impulse / continuation | 0.179% | True breakout |
| 2025-08-21 10:15 | Valid swing, away from level | 38.2% | 7.6% | 6.02x | Impulse / continuation | -0.241% | True breakout |
| 2025-11-28 16:00 | Valid swing, away from level | n/a | -2.9% | 6.01x | Flat / fading | 0.052% | Weak move without breakout |
| 2026-08-21 10:15 | Near Fib level | 78.6% | 82.4% | 6.01x | Flat / fading | 0.269% | Position building in range |
| 2026-05-25 16:30 | Valid swing, away from level | n/a | 126.2% | 6.00x | Impulse / continuation | -0.426% | True breakout |
| 2026-08-12 23:00 | Valid swing, away from level | n/a | 119.8% | 6.00x | Flat / fading | 0.115% | Position building in range |
| 2025-03-16 16:45 | Valid swing, away from level | n/a | -1636.4% | 5.99x | Impulse / continuation | 0.184% | True breakout |
| 2025-06-20 07:00 | Valid swing, away from level | 78.6% | 73.2% | 5.99x | Flat / fading | 0.025% | Position building in range |
| 2025-07-03 11:00 | Valid swing, away from level | n/a | -34.0% | 5.99x | Flat / fading | 0.018% | Weak move without breakout |
| 2024-10-02 15:45 | Valid swing, away from level | n/a | 193.7% | 5.97x | Reversal | 0.954% | Liquidity sweep / reversal |
| 2025-10-09 10:00 | Near Fib level | 38.2% | 35.9% | 5.96x | Flat / fading | -0.645% | Weak move without breakout |
| 2026-04-07 10:45 | Valid swing, away from level | n/a | -6.8% | 5.96x | Impulse / continuation | 0.255% | True breakout |
| 2025-02-03 10:00 | Near Fib level | 78.6% | 79.2% | 5.96x | Reversal | -0.469% | Liquidity sweep / reversal |
| 2025-10-11 18:30 | Valid swing, away from level | n/a | -7.5% | 5.96x | Impulse / continuation | 0.449% | True breakout |
| 2026-06-18 10:30 | Valid swing, away from level | n/a | 281.2% | 5.95x | Flat / fading | 0.171% | Weak move without breakout |
| 2025-05-20 10:00 | Near Fib level | 78.6% | 74.5% | 5.95x | Impulse / continuation | -0.506% | True breakout |
| 2024-11-05 10:15 | Golden zone 50-61.8% | 61.8% | 57.1% | 5.95x | Impulse / continuation | 0.060% | True breakout |
| 2025-02-14 07:00 | Valid swing, away from level | n/a | -61.4% | 5.95x | Flat / fading | -0.207% | Position building in range |
| 2025-11-03 21:45 | Valid swing, away from level | 78.6% | 73.2% | 5.95x | Flat / fading | -0.047% | Weak move without breakout |
| 2025-05-14 23:00 | Valid swing, away from level | n/a | 148.0% | 5.94x | Impulse / continuation | -1.627% | True breakout |
| 2025-02-10 10:00 | Valid swing, away from level | n/a | -603.0% | 5.94x | Reversal | 0.095% | Liquidity sweep / reversal |
| 2026-02-11 10:30 | Near Fib level | 38.2% | 33.7% | 5.94x | Flat / fading | 0.164% | Weak move without breakout |
| 2025-08-07 11:45 | Valid swing, away from level | n/a | -46.7% | 5.94x | Reversal | -0.617% | Liquidity sweep / reversal |
| 2026-09-03 13:45 | Valid swing, away from level | n/a | -25.0% | 5.94x | Flat / fading | 0.210% | Weak move without breakout |
| 2025-06-23 16:30 | Valid swing, away from level | n/a | -19.5% | 5.94x | Impulse / continuation | 0.252% | True breakout |
| 2026-02-12 10:00 | Valid swing, away from level | n/a | 102.1% | 5.94x | Impulse / continuation | -0.042% | True breakout |
| 2024-10-23 10:15 | Valid swing, away from level | n/a | 140.5% | 5.94x | Impulse / continuation | -0.256% | True breakout |
| 2026-01-14 10:15 | Valid swing, away from level | 78.6% | 94.7% | 5.94x | Flat / fading | 0.263% | Weak move without breakout |
| 2025-12-15 08:30 | Valid swing, away from level | n/a | -576.2% | 5.93x | Impulse / continuation | -0.044% | True breakout |
| 2025-10-06 10:00 | Valid swing, away from level | n/a | 234.9% | 5.93x | Impulse / continuation | 0.767% | True breakout |
| 2026-03-03 09:45 | Valid swing, away from level | n/a | 141.3% | 5.93x | Flat / fading | 0.165% | Weak move without breakout |
| 2026-04-03 09:00 | Valid swing, away from level | n/a | -42.7% | 5.93x | Reversal | -0.386% | Liquidity sweep / reversal |
| 2026-01-25 12:30 | Valid swing, away from level | n/a | -28.9% | 5.93x | Flat / fading | -0.114% | Weak move without breakout |
| 2026-07-26 10:15 | Valid swing, away from level | 38.2% | 16.1% | 5.92x | Impulse / continuation | 0.107% | True breakout |
| 2025-12-29 12:00 | Valid swing, away from level | n/a | -179.0% | 5.92x | Flat / fading | 0.061% | Weak move without breakout |
| 2025-09-17 09:15 | Valid swing, away from level | n/a | 110.3% | 5.92x | Impulse / continuation | 0.013% | True breakout |
| 2025-07-19 10:30 | Valid swing, away from level | n/a | -35.7% | 5.91x | Impulse / continuation | -0.208% | True breakout |
| 2025-11-13 11:00 | Near Fib level | 38.2% | 41.4% | 5.91x | Flat / fading | 0.067% | Weak move without breakout |
| 2025-12-04 07:45 | Valid swing, away from level | n/a | -27.3% | 5.91x | Impulse / continuation | -0.019% | True breakout |
| 2024-10-02 16:00 | Valid swing, away from level | n/a | 139.2% | 5.90x | Flat / fading | -0.237% | Weak move without breakout |
| 2025-03-13 10:30 | Valid swing, away from level | n/a | 297.3% | 5.89x | Impulse / continuation | -0.432% | True breakout |
| 2025-01-17 10:30 | Valid swing, away from level | 61.8% | 69.1% | 5.89x | Impulse / continuation | 0.624% | True breakout |
| 2026-03-06 11:00 | Valid swing, away from level | 38.2% | 7.4% | 5.89x | Reversal | -0.246% | Liquidity sweep / reversal |
| 2026-07-10 09:30 | Valid swing, away from level | 78.6% | 72.4% | 5.89x | Reversal | -0.259% | Liquidity sweep / reversal |
| 2025-05-16 16:30 | Valid swing, away from level | 78.6% | 72.9% | 5.88x | Flat / fading | -0.136% | Weak move without breakout |
| 2026-06-10 10:15 | Valid swing, away from level | 38.2% | 27.3% | 5.88x | Impulse -> reversal | -0.386% | False breakout |
| 2026-05-18 07:15 | Valid swing, away from level | n/a | -17.1% | 5.87x | Reversal | -0.290% | Liquidity sweep / reversal |
| 2026-03-31 12:00 | Valid swing, away from level | n/a | -347.3% | 5.87x | Impulse / continuation | 0.373% | True breakout |
| 2026-09-01 07:00 | Valid swing, away from level | 38.2% | 22.7% | 5.86x | Impulse / continuation | -0.361% | True breakout |
| 2025-11-17 10:45 | Valid swing, away from level | n/a | -133.3% | 5.86x | Impulse -> reversal | -0.239% | False breakout |
| 2025-09-10 10:00 | Near Fib level | 61.8% | 61.8% | 5.86x | Flat / fading | 0.018% | Weak move without breakout |
| 2025-07-11 18:15 | Valid swing, away from level | n/a | 131.3% | 5.86x | Flat / fading | 0.013% | Position building in range |
| 2026-07-19 16:30 | Valid swing, away from level | n/a | -14.8% | 5.85x | Flat / fading | 0.017% | Position building in range |
| 2025-07-14 10:15 | Valid swing, away from level | n/a | -378.3% | 5.85x | Impulse / continuation | 0.532% | True breakout |
| 2024-11-01 10:00 | Near Fib level | 38.2% | 33.3% | 5.85x | Reversal | -0.462% | Liquidity sweep / reversal |
| 2026-05-29 10:15 | Valid swing, away from level | 78.6% | 96.9% | 5.84x | Flat / fading | -0.020% | Position building in range |
| 2026-09-03 20:00 | Valid swing, away from level | n/a | -29.8% | 5.84x | Flat / fading | 0.253% | Weak move without breakout |
| 2025-07-16 10:45 | Valid swing, away from level | n/a | 116.8% | 5.84x | Reversal | 0.351% | Liquidity sweep / reversal |
| 2025-02-05 15:45 | Valid swing, away from level | 78.6% | 85.5% | 5.83x | Impulse / continuation | 0.113% | True breakout |
| 2025-11-25 15:30 | Valid swing, away from level | n/a | -33.0% | 5.83x | Reversal | -0.406% | Liquidity sweep / reversal |
| 2025-08-25 11:30 | Valid swing, away from level | n/a | 256.9% | 5.83x | Flat / fading | 0.018% | Position building in range |
| 2026-06-07 10:00 | Valid swing, away from level | 78.6% | 96.5% | 5.83x | Impulse / continuation | 0.121% | True breakout |
| 2025-10-09 09:15 | Valid swing, away from level | n/a | 141.2% | 5.82x | Reversal | 1.193% | Liquidity sweep / reversal |
| 2026-03-31 10:15 | Valid swing, away from level | n/a | -41.8% | 5.82x | Impulse / continuation | 0.291% | True breakout |
| 2026-07-27 07:15 | Valid swing, away from level | 78.6% | 72.7% | 5.81x | Impulse / continuation | 0.366% | True breakout |
| 2026-05-26 19:00 | Valid swing, away from level | n/a | 110.6% | 5.81x | Impulse / continuation | -0.066% | True breakout |
| 2025-10-20 10:15 | Valid swing, away from level | n/a | -37.8% | 5.81x | Impulse / continuation | 0.165% | True breakout |
| 2024-10-21 10:15 | Valid swing, away from level | n/a | -47.4% | 5.81x | Flat / fading | -0.058% | Position building in range |
| 2026-04-09 22:00 | Valid swing, away from level | n/a | 144.1% | 5.81x | Flat / fading | -0.013% | Weak move without breakout |
| 2025-09-18 10:00 | Valid swing, away from level | n/a | 126.2% | 5.81x | Reversal | 0.013% | Liquidity sweep / reversal |
| 2026-01-19 09:00 | Valid swing, away from level | n/a | -4.2% | 5.80x | Reversal | -0.031% | Liquidity sweep / reversal |
| 2024-12-11 10:15 | Valid swing, away from level | n/a | 136.9% | 5.79x | Impulse / continuation | -0.043% | True breakout |
| 2025-12-09 14:30 | Valid swing, away from level | n/a | -133.3% | 5.79x | Flat / fading | -0.118% | Weak move without breakout |
| 2026-07-16 07:00 | Valid swing, away from level | n/a | 108.5% | 5.79x | Impulse / continuation | -0.330% | True breakout |
| 2025-03-11 10:45 | Valid swing, away from level | 38.2% | 3.4% | 5.78x | Reversal | -0.291% | Liquidity sweep / reversal |
| 2026-07-07 12:00 | Valid swing, away from level | n/a | -56.5% | 5.78x | Impulse / continuation | 1.902% | True breakout |
| 2025-08-18 15:45 | Valid swing, away from level | n/a | -75.6% | 5.77x | Impulse / continuation | 0.453% | True breakout |
| 2025-02-12 10:00 | Valid swing, away from level | n/a | -162.3% | 5.77x | Flat / fading | 0.013% | Weak move without breakout |
| 2025-05-23 10:30 | Near Fib level | 38.2% | 38.3% | 5.77x | Reversal | -0.207% | Liquidity sweep / reversal |
| 2025-07-06 10:00 | Valid swing, away from level | n/a | 233.3% | 5.76x | Impulse / continuation | -0.230% | True breakout |
| 2025-06-19 07:00 | Near Fib level | 50.0% | 49.7% | 5.75x | Flat / fading | -0.056% | Weak move without breakout |
| 2026-05-18 07:30 | Valid swing, away from level | 78.6% | 73.2% | 5.75x | Flat / fading | -0.078% | Weak move without breakout |
| 2024-11-12 11:00 | Valid swing, away from level | n/a | 123.1% | 5.75x | Flat / fading | 0.139% | Position building in range |
| 2024-10-07 10:15 | Near Fib level | 78.6% | 83.3% | 5.75x | Impulse / continuation | -0.782% | True breakout |
| 2026-01-30 11:15 | Valid swing, away from level | n/a | 109.1% | 5.74x | Impulse / continuation | -0.430% | True breakout |
| 2024-10-11 10:15 | Near Fib level | 38.2% | 39.4% | 5.74x | Flat / fading | 0.039% | Weak move without breakout |
| 2025-06-06 10:45 | Valid swing, away from level | n/a | -72.5% | 5.74x | Reversal | 0.353% | Liquidity sweep / reversal |
| 2025-07-10 08:15 | Valid swing, away from level | n/a | -24.8% | 5.74x | Flat / fading | 0.119% | Position building in range |
| 2024-10-18 10:30 | Valid swing, away from level | n/a | 215.6% | 5.73x | Reversal | 0.369% | Liquidity sweep / reversal |
| 2026-09-17 10:00 | Near Fib level | 38.2% | 36.7% | 5.73x | Impulse / continuation | -0.577% | True breakout |
| 2025-10-27 07:15 | Valid swing, away from level | n/a | 129.8% | 5.73x | Flat / fading | 0.195% | Position building in range |
| 2025-04-25 12:30 | Valid swing, away from level | n/a | -57.5% | 5.73x | Flat / fading | 0.031% | Weak move without breakout |
| 2026-05-20 08:00 | Valid swing, away from level | 38.2% | 21.1% | 5.73x | Reversal | -0.317% | Liquidity sweep / reversal |
| 2026-09-09 12:15 | Valid swing, away from level | n/a | 117.5% | 5.73x | Impulse / continuation | -0.292% | True breakout |
| 2026-02-01 13:30 | Valid swing, away from level | 38.2% | 5.7% | 5.72x | Flat / fading | 0.024% | Weak move without breakout |
| 2026-06-24 09:15 | Valid swing, away from level | 61.8% | 68.3% | 5.72x | Impulse / continuation | -0.348% | True breakout |
| 2026-05-22 09:45 | Valid swing, away from level | 38.2% | 12.5% | 5.71x | Impulse / continuation | 0.332% | True breakout |
| 2024-09-30 10:30 | Valid swing, away from level | n/a | -125.6% | 5.71x | Impulse / continuation | 0.056% | True breakout |
| 2024-11-20 10:15 | Golden zone 50-61.8% | 50.0% | 51.9% | 5.71x | Reversal | -0.840% | Liquidity sweep / reversal |
| 2025-01-06 10:15 | Valid swing, away from level | n/a | 286.8% | 5.70x | Impulse / continuation | 0.556% | True breakout |
| 2025-08-18 08:00 | Valid swing, away from level | n/a | -281.8% | 5.69x | Reversal | -0.353% | Liquidity sweep / reversal |
| 2026-08-20 07:00 | Near Fib level | 38.2% | 41.8% | 5.68x | Flat / fading | -0.139% | Position building in range |
| 2026-07-04 18:30 | Valid swing, away from level | 78.6% | 86.7% | 5.68x | Reversal | 1.189% | Liquidity sweep / reversal |
| 2025-05-13 10:00 | Valid swing, away from level | n/a | -3.4% | 5.68x | Impulse / continuation | -0.221% | True breakout |
| 2025-10-23 18:30 | Valid swing, away from level | 38.2% | 2.2% | 5.67x | Flat / fading | -0.177% | Position building in range |
| 2026-05-30 17:45 | Near Fib level | 78.6% | 75.0% | 5.67x | Flat / fading | -0.013% | Weak move without breakout |
| 2025-10-28 07:00 | Valid swing, away from level | 78.6% | 72.5% | 5.67x | Reversal | 0.219% | Liquidity sweep / reversal |
| 2025-05-16 07:00 | Near Fib level | 78.6% | 78.1% | 5.66x | Flat / fading | -0.181% | Position building in range |
| 2024-11-22 18:00 | Valid swing, away from level | n/a | 327.7% | 5.66x | Flat / fading | -0.324% | Position building in range |
| 2026-02-26 17:15 | Valid swing, away from level | n/a | 142.4% | 5.66x | Impulse / continuation | -0.423% | True breakout |
| 2026-07-09 07:15 | Valid swing, away from level | 78.6% | 70.5% | 5.64x | Flat / fading | 0.141% | Position building in range |
| 2024-11-29 10:45 | Near Fib level | 50.0% | 45.7% | 5.64x | Impulse / continuation | 0.639% | True breakout |
| 2026-05-28 11:15 | Valid swing, away from level | n/a | -21.1% | 5.64x | Flat / fading | -0.105% | Weak move without breakout |
| 2026-06-17 10:30 | Valid swing, away from level | n/a | -22.7% | 5.64x | Impulse -> reversal | -0.455% | False breakout |
| 2026-07-13 09:15 | Valid swing, away from level | n/a | 105.3% | 5.64x | Impulse / continuation | 1.204% | True breakout |
| 2024-10-28 10:00 | Valid swing, away from level | n/a | 116.1% | 5.64x | Reversal | 0.190% | Liquidity sweep / reversal |
| 2025-07-11 07:00 | Golden zone 50-61.8% | 50.0% | 55.7% | 5.64x | Reversal | -0.300% | Liquidity sweep / reversal |
| 2024-10-31 10:00 | Valid swing, away from level | n/a | 222.9% | 5.63x | Flat / fading | 0.086% | Weak move without breakout |
| 2026-03-17 14:30 | Valid swing, away from level | n/a | 181.1% | 5.63x | Flat / fading | 0.047% | Weak move without breakout |
| 2026-08-20 10:15 | Valid swing, away from level | n/a | -2.5% | 5.62x | Impulse / continuation | 0.298% | True breakout |
| 2026-01-20 17:15 | Valid swing, away from level | 38.2% | 43.5% | 5.62x | Flat / fading | -0.073% | Weak move without breakout |
| 2026-03-31 10:30 | Valid swing, away from level | n/a | -67.3% | 5.62x | Reversal | 0.179% | Liquidity sweep / reversal |
| 2026-03-16 09:00 | Valid swing, away from level | n/a | -477.8% | 5.61x | Reversal | 0.159% | Liquidity sweep / reversal |
| 2025-07-14 10:45 | Valid swing, away from level | n/a | -520.5% | 5.61x | Flat / fading | -0.377% | Position building in range |
| 2025-11-21 15:15 | Valid swing, away from level | n/a | 104.8% | 5.61x | Flat / fading | -0.182% | Weak move without breakout |
| 2026-09-24 11:00 | Valid swing, away from level | 38.2% | 13.4% | 5.60x | Flat / fading | -0.177% | Position building in range |
| 2026-07-28 10:00 | Near Fib level | 61.8% | 64.4% | 5.60x | Impulse / continuation | -1.567% | True breakout |
| 2026-07-23 07:30 | Valid swing, away from level | 78.6% | 87.2% | 5.59x | Reversal | 0.332% | Liquidity sweep / reversal |
| 2026-03-09 07:30 | Valid swing, away from level | 78.6% | 97.8% | 5.59x | Flat / fading | 0.308% | Weak move without breakout |
| 2026-08-31 18:30 | Valid swing, away from level | n/a | -254.9% | 5.57x | Reversal | -0.454% | Liquidity sweep / reversal |
| 2026-08-03 07:00 | Valid swing, away from level | n/a | -73.8% | 5.57x | Impulse / continuation | 0.164% | True breakout |
| 2026-01-16 16:30 | Valid swing, away from level | n/a | -15.6% | 5.57x | Impulse / continuation | -0.074% | True breakout |
| 2026-03-09 09:00 | Valid swing, away from level | n/a | 112.1% | 5.56x | Flat / fading | 0.350% | Position building in range |
| 2025-07-20 18:30 | Near Fib level | 61.8% | 66.0% | 5.55x | Reversal | 0.328% | Liquidity sweep / reversal |
| 2026-06-08 10:00 | Near Fib level | 78.6% | 76.3% | 5.55x | Impulse / continuation | -0.027% | True breakout |
| 2026-08-11 10:00 | Valid swing, away from level | n/a | -214.5% | 5.54x | Flat / fading | -0.085% | Weak move without breakout |
| 2026-01-13 07:00 | Valid swing, away from level | n/a | -18.2% | 5.53x | Flat / fading | -0.043% | Position building in range |
| 2025-07-15 12:30 | Valid swing, away from level | n/a | -49.5% | 5.53x | Impulse / continuation | 0.655% | True breakout |
| 2025-06-08 15:30 | Valid swing, away from level | n/a | 165.8% | 5.52x | Impulse / continuation | 0.056% | True breakout |
| 2024-11-06 10:45 | Valid swing, away from level | n/a | -507.8% | 5.52x | Flat / fading | -0.273% | Weak move without breakout |
| 2025-06-20 10:15 | Valid swing, away from level | 78.6% | 89.6% | 5.52x | Reversal | 0.239% | Liquidity sweep / reversal |
| 2025-11-28 18:15 | Valid swing, away from level | n/a | -365.8% | 5.50x | Flat / fading | -0.404% | Position building in range |
| 2026-05-08 09:15 | Valid swing, away from level | n/a | 105.1% | 5.50x | Reversal | 0.221% | Liquidity sweep / reversal |
| 2026-03-27 19:30 | Valid swing, away from level | n/a | 115.2% | 5.49x | Flat / fading | 0.080% | Position building in range |
| 2025-08-18 22:00 | Valid swing, away from level | n/a | -15.7% | 5.49x | Flat / fading | -0.106% | Position building in range |
| 2026-02-20 10:15 | Valid swing, away from level | n/a | -54.7% | 5.49x | Impulse / continuation | -0.096% | True breakout |
| 2026-02-06 10:00 | Near Fib level | 38.2% | 39.3% | 5.49x | Impulse / continuation | -0.181% | True breakout |
| 2024-12-16 10:30 | Valid swing, away from level | n/a | 119.3% | 5.49x | Impulse / continuation | -0.695% | True breakout |
| 2025-03-13 11:00 | Valid swing, away from level | n/a | 405.5% | 5.49x | Impulse / continuation | -0.053% | True breakout |
| 2026-03-03 10:00 | Valid swing, away from level | n/a | 151.4% | 5.48x | Reversal | 0.230% | Liquidity sweep / reversal |
| 2025-05-14 15:15 | Valid swing, away from level | n/a | -5.3% | 5.48x | Flat / fading | -0.032% | Position building in range |
| 2025-09-11 11:30 | Valid swing, away from level | n/a | 208.3% | 5.48x | Reversal | 0.188% | Liquidity sweep / reversal |
| 2025-03-04 19:15 | Valid swing, away from level | n/a | -59.8% | 5.48x | Flat / fading | 0.409% | Weak move without breakout |
| 2025-05-15 07:00 | Valid swing, away from level | n/a | 183.5% | 5.48x | Flat / fading | -0.122% | Weak move without breakout |
| 2026-03-23 10:45 | Valid swing, away from level | 38.2% | 13.2% | 5.47x | Reversal | -0.144% | Liquidity sweep / reversal |
| 2026-09-22 07:15 | Valid swing, away from level | 38.2% | 3.3% | 5.47x | Flat / fading | -0.062% | Position building in range |
| 2025-08-24 10:00 | Valid swing, away from level | n/a | 157.1% | 5.47x | Impulse / continuation | -0.107% | True breakout |
| 2025-03-27 10:15 | Valid swing, away from level | n/a | 416.5% | 5.47x | Flat / fading | -0.290% | Position building in range |
| 2025-05-04 16:30 | Valid swing, away from level | n/a | -21.1% | 5.47x | Flat / fading | 0.020% | Weak move without breakout |
| 2025-09-15 09:00 | Valid swing, away from level | n/a | 375.0% | 5.46x | Flat / fading | 0.182% | Position building in range |
| 2025-12-02 18:00 | Valid swing, away from level | 50.0% | 44.8% | 5.45x | Flat / fading | 0.089% | Position building in range |
| 2026-08-31 08:00 | Valid swing, away from level | n/a | -109.1% | 5.44x | Impulse / continuation | 0.048% | True breakout |
| 2025-11-07 20:45 | Valid swing, away from level | 78.6% | 73.4% | 5.44x | Impulse / continuation | -0.188% | True breakout |
| 2026-09-05 12:30 | Valid swing, away from level | n/a | 106.5% | 5.44x | Flat / fading | 0.144% | Position building in range |
| 2025-02-25 07:00 | Valid swing, away from level | n/a | -23.9% | 5.44x | Reversal | 0.127% | Liquidity sweep / reversal |
| 2025-07-20 10:15 | Valid swing, away from level | 38.2% | 32.9% | 5.44x | Reversal | -0.012% | Liquidity sweep / reversal |
| 2026-05-31 18:30 | Valid swing, away from level | n/a | 114.3% | 5.43x | Impulse / continuation | 0.186% | True breakout |
| 2025-11-27 17:15 | Valid swing, away from level | n/a | 304.9% | 5.43x | Impulse / continuation | 0.164% | True breakout |
| 2026-07-24 10:15 | Valid swing, away from level | n/a | 119.4% | 5.43x | Impulse / continuation | -0.845% | True breakout |
| 2026-05-26 11:15 | Valid swing, away from level | n/a | 130.5% | 5.43x | Reversal | 0.463% | Liquidity sweep / reversal |
| 2026-07-22 09:00 | Near Fib level | 50.0% | 48.6% | 5.43x | Reversal | 0.662% | Liquidity sweep / reversal |
| 2025-06-03 18:00 | Valid swing, away from level | n/a | -7.9% | 5.43x | Impulse / continuation | 0.364% | True breakout |
| 2025-01-15 19:15 | Valid swing, away from level | n/a | -116.8% | 5.42x | Reversal | 0.216% | Liquidity sweep / reversal |
| 2025-07-21 08:00 | Valid swing, away from level | n/a | -98.0% | 5.42x | Impulse -> reversal | -0.119% | False breakout |
| 2026-01-12 14:00 | Valid swing, away from level | 78.6% | 95.5% | 5.42x | Impulse / continuation | -0.111% | True breakout |
| 2025-08-05 10:30 | Valid swing, away from level | n/a | -13.6% | 5.41x | Flat / fading | -0.093% | Weak move without breakout |
| 2026-06-24 17:30 | Valid swing, away from level | n/a | 257.3% | 5.41x | Impulse / continuation | -1.621% | True breakout |
| 2025-08-15 13:15 | Valid swing, away from level | n/a | -98.8% | 5.41x | Flat / fading | -0.107% | Position building in range |
| 2026-06-18 07:00 | Near Fib level | 78.6% | 82.2% | 5.41x | Impulse -> reversal | -0.047% | False breakout |
| 2025-12-02 11:45 | Valid swing, away from level | 38.2% | 25.4% | 5.40x | Flat / fading | 0.147% | Weak move without breakout |
| 2025-04-09 14:00 | Valid swing, away from level | n/a | 155.7% | 5.40x | Flat / fading | 1.205% | Weak move without breakout |
| 2025-01-15 10:00 | Near Fib level | 38.2% | 40.5% | 5.40x | Reversal | -0.130% | Liquidity sweep / reversal |
| 2026-07-06 09:00 | Valid swing, away from level | n/a | 109.6% | 5.40x | Reversal | 0.404% | Liquidity sweep / reversal |
| 2024-11-08 10:00 | Valid swing, away from level | n/a | -464.4% | 5.39x | Reversal | 1.416% | Liquidity sweep / reversal |
| 2026-02-04 10:00 | Near Fib level | 38.2% | 39.1% | 5.39x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-03-10 10:15 | Near Fib level | 38.2% | 35.0% | 5.38x | Flat / fading | 0.293% | Position building in range |
| 2024-09-24 18:15 | No confirmed swing | n/a | n/a | 5.38x | Flat / fading | 0.114% | Position building in range |
| 2026-06-24 10:15 | Valid swing, away from level | 78.6% | 95.0% | 5.38x | Impulse / continuation | -0.320% | True breakout |
| 2026-01-23 20:45 | Valid swing, away from level | 38.2% | 3.8% | 5.38x | Impulse / continuation | 0.066% | True breakout |
| 2026-06-16 15:30 | Valid swing, away from level | n/a | 452.2% | 5.38x | Impulse / continuation | -0.601% | True breakout |
| 2025-10-27 10:00 | Valid swing, away from level | n/a | 132.4% | 5.37x | Flat / fading | -0.091% | Weak move without breakout |
| 2025-02-26 07:00 | Golden zone 50-61.8% | 61.8% | 57.9% | 5.37x | Flat / fading | 0.192% | Weak move without breakout |
| 2026-03-05 07:00 | Valid swing, away from level | n/a | -41.9% | 5.37x | Flat / fading | -0.053% | Position building in range |
| 2026-01-29 10:15 | Valid swing, away from level | n/a | -141.9% | 5.37x | Impulse / continuation | 0.274% | True breakout |
| 2024-10-07 10:30 | Valid swing, away from level | 78.6% | 95.1% | 5.37x | Impulse / continuation | -0.059% | True breakout |
| 2026-07-06 11:00 | Valid swing, away from level | n/a | -3.7% | 5.37x | Flat / fading | 0.094% | Weak move without breakout |
| 2026-04-21 14:00 | Valid swing, away from level | 38.2% | 14.0% | 5.37x | Flat / fading | -0.141% | Position building in range |
| 2024-12-23 10:15 | Valid swing, away from level | n/a | -71.2% | 5.37x | Impulse / continuation | 0.605% | True breakout |
| 2026-01-13 17:00 | Valid swing, away from level | n/a | 109.2% | 5.37x | Flat / fading | -0.180% | Position building in range |
| 2026-07-27 07:45 | Near Fib level | 38.2% | 33.3% | 5.36x | Reversal | 0.244% | Liquidity sweep / reversal |
| 2025-01-30 11:00 | Valid swing, away from level | 38.2% | 0.0% | 5.36x | Reversal | -0.519% | Liquidity sweep / reversal |
| 2024-11-07 12:15 | Near Fib level | 50.0% | 46.6% | 5.36x | Impulse / continuation | -0.423% | True breakout |
| 2026-05-04 14:00 | Valid swing, away from level | n/a | 119.8% | 5.36x | Impulse / continuation | -0.362% | True breakout |
| 2025-08-06 10:00 | Valid swing, away from level | n/a | -28.9% | 5.36x | Reversal | -0.279% | Liquidity sweep / reversal |
| 2025-11-01 10:45 | Valid swing, away from level | 38.2% | 9.5% | 5.35x | Reversal | -0.156% | Liquidity sweep / reversal |
| 2026-02-19 10:30 | Valid swing, away from level | n/a | 183.7% | 5.35x | Flat / fading | 0.216% | Position building in range |
| 2026-04-10 10:45 | Valid swing, away from level | n/a | 115.1% | 5.35x | Flat / fading | 0.183% | Weak move without breakout |
| 2026-01-28 10:00 | Near Fib level | 61.8% | 64.3% | 5.35x | Impulse / continuation | -0.054% | True breakout |
| 2025-04-07 07:15 | Valid swing, away from level | n/a | 1250.0% | 5.35x | Reversal | -1.141% | Liquidity sweep / reversal |
| 2026-05-05 11:15 | Valid swing, away from level | 78.6% | 89.9% | 5.34x | Reversal | 1.000% | Liquidity sweep / reversal |
| 2026-06-25 09:00 | Valid swing, away from level | 61.8% | 70.2% | 5.34x | Reversal | 1.525% | Liquidity sweep / reversal |
| 2025-01-31 10:15 | Valid swing, away from level | n/a | -85.2% | 5.34x | Reversal | 0.578% | Liquidity sweep / reversal |
| 2025-06-08 15:45 | Valid swing, away from level | n/a | 213.2% | 5.33x | Reversal | 0.025% | Liquidity sweep / reversal |
| 2025-04-08 07:00 | Valid swing, away from level | 38.2% | 25.3% | 5.33x | Flat / fading | 0.403% | Weak move without breakout |
| 2026-07-13 09:00 | Valid swing, away from level | n/a | 105.3% | 5.33x | Reversal | 0.687% | Liquidity sweep / reversal |
| 2025-06-26 10:00 | Near Fib level | 38.2% | 34.6% | 5.32x | Impulse / continuation | -0.135% | True breakout |
| 2025-08-24 11:00 | Valid swing, away from level | n/a | 221.4% | 5.32x | Flat / fading | 0.059% | Weak move without breakout |
| 2024-10-22 10:45 | Valid swing, away from level | n/a | 107.9% | 5.32x | Flat / fading | 0.058% | Position building in range |
| 2025-02-03 07:00 | Valid swing, away from level | n/a | 134.1% | 5.31x | Flat / fading | 0.338% | Position building in range |
| 2024-09-25 12:30 | Valid swing, away from level | n/a | -413.0% | 5.31x | Impulse / continuation | -0.599% | True breakout |
| 2026-08-17 07:15 | Valid swing, away from level | n/a | 146.0% | 5.30x | Reversal | -0.531% | Liquidity sweep / reversal |
| 2024-10-02 15:30 | Valid swing, away from level | n/a | 150.6% | 5.29x | Impulse / continuation | 0.198% | True breakout |
| 2025-10-01 10:00 | Valid swing, away from level | 38.2% | 9.3% | 5.29x | Impulse / continuation | -0.253% | True breakout |
| 2024-11-13 10:00 | Valid swing, away from level | n/a | 211.9% | 5.29x | Impulse / continuation | 0.527% | True breakout |
| 2026-03-23 14:00 | Valid swing, away from level | n/a | 172.1% | 5.29x | Flat / fading | 0.115% | Weak move without breakout |
| 2026-06-01 07:15 | Valid swing, away from level | n/a | -285.7% | 5.29x | Impulse -> reversal | 0.086% | False breakout |
| 2025-12-28 10:00 | Valid swing, away from level | n/a | 135.1% | 5.29x | Impulse / continuation | -0.160% | True breakout |
| 2025-01-08 10:15 | Valid swing, away from level | n/a | -21.1% | 5.28x | Impulse / continuation | 0.456% | True breakout |
| 2025-10-16 17:30 | Valid swing, away from level | n/a | -537.7% | 5.28x | Impulse / continuation | -0.114% | True breakout |
| 2026-02-06 23:30 | Valid swing, away from level | n/a | 111.5% | 5.28x | Reversal | 0.231% | Liquidity sweep / reversal |
| 2026-01-22 07:00 | Valid swing, away from level | n/a | -36.4% | 5.28x | Reversal | -0.090% | Liquidity sweep / reversal |
| 2025-12-11 11:00 | Valid swing, away from level | n/a | -107.8% | 5.28x | Impulse / continuation | 0.153% | True breakout |
| 2026-01-30 20:45 | Valid swing, away from level | n/a | 125.1% | 5.27x | Flat / fading | 0.181% | Weak move without breakout |
| 2025-02-06 10:00 | Valid swing, away from level | n/a | -1.9% | 5.27x | Reversal | 1.289% | Liquidity sweep / reversal |
| 2026-01-15 07:00 | Near Fib level | 50.0% | 48.7% | 5.27x | Impulse / continuation | -0.069% | True breakout |
| 2025-07-28 08:15 | Valid swing, away from level | n/a | -182.9% | 5.27x | Impulse / continuation | -0.061% | True breakout |
| 2024-12-16 10:15 | Valid swing, away from level | n/a | 110.3% | 5.27x | Impulse / continuation | -0.500% | True breakout |
| 2025-04-02 19:00 | Valid swing, away from level | n/a | 126.2% | 5.26x | Reversal | 0.432% | Liquidity sweep / reversal |
| 2026-07-17 19:45 | Valid swing, away from level | n/a | 233.3% | 5.26x | Flat / fading | 0.538% | Position building in range |
| 2026-05-06 09:15 | Valid swing, away from level | n/a | 131.8% | 5.26x | Flat / fading | -0.110% | Weak move without breakout |
| 2025-11-20 21:00 | Valid swing, away from level | n/a | -18.2% | 5.25x | Reversal | -0.707% | Liquidity sweep / reversal |
| 2025-01-29 10:00 | Golden zone 50-61.8% | 50.0% | 54.6% | 5.25x | Reversal | 0.540% | Liquidity sweep / reversal |
| 2025-01-13 10:15 | Valid swing, away from level | n/a | -33.1% | 5.25x | Flat / fading | 0.285% | Position building in range |
| 2026-05-18 18:30 | Valid swing, away from level | n/a | -75.7% | 5.25x | Impulse / continuation | 0.168% | True breakout |
| 2025-07-19 17:45 | Near Fib level | 38.2% | 37.1% | 5.24x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2026-07-24 10:00 | Valid swing, away from level | n/a | 113.3% | 5.24x | Impulse / continuation | -0.836% | True breakout |
| 2024-11-21 10:30 | Valid swing, away from level | 78.6% | 87.6% | 5.24x | Impulse / continuation | -0.842% | True breakout |
| 2024-10-17 10:15 | Valid swing, away from level | n/a | -16.7% | 5.24x | Flat / fading | 0.058% | Weak move without breakout |
| 2025-08-25 10:00 | Valid swing, away from level | 78.6% | 70.6% | 5.24x | Impulse / continuation | -0.255% | True breakout |
| 2025-07-14 10:30 | Valid swing, away from level | n/a | -397.6% | 5.24x | Impulse / continuation | 0.095% | True breakout |
| 2026-01-06 10:15 | Valid swing, away from level | n/a | -147.3% | 5.24x | Flat / fading | 0.067% | Weak move without breakout |
| 2025-02-04 10:00 | Valid swing, away from level | 38.2% | 9.5% | 5.24x | Reversal | 0.079% | Liquidity sweep / reversal |
| 2025-08-24 10:45 | Valid swing, away from level | n/a | 178.6% | 5.23x | Impulse / continuation | -0.047% | True breakout |
| 2024-12-04 10:30 | Near Fib level | 38.2% | 37.4% | 5.23x | Impulse / continuation | 1.019% | True breakout |
| 2024-12-23 10:00 | Valid swing, away from level | n/a | -30.2% | 5.23x | Reversal | 1.375% | Liquidity sweep / reversal |
| 2025-07-03 09:45 | Valid swing, away from level | 61.8% | 68.0% | 5.23x | Flat / fading | 0.049% | Weak move without breakout |
| 2025-07-01 07:00 | Near Fib level | 50.0% | 48.7% | 5.22x | Impulse / continuation | 0.135% | True breakout |
| 2026-06-19 23:30 | Valid swing, away from level | n/a | 108.5% | 5.22x | Reversal | 0.679% | Liquidity sweep / reversal |
| 2025-05-22 08:15 | Valid swing, away from level | n/a | 134.4% | 5.22x | Reversal | -0.910% | Liquidity sweep / reversal |
| 2026-04-06 08:15 | Valid swing, away from level | 38.2% | 22.6% | 5.22x | Impulse / continuation | -0.099% | True breakout |
| 2026-07-07 10:45 | Valid swing, away from level | n/a | 231.3% | 5.22x | Flat / fading | 0.911% | Weak move without breakout |
| 2025-09-29 10:30 | Valid swing, away from level | n/a | -417.4% | 5.21x | Impulse / continuation | 0.204% | True breakout |
| 2025-06-26 20:00 | Valid swing, away from level | 78.6% | 93.5% | 5.20x | Flat / fading | -0.087% | Position building in range |
| 2025-12-11 08:00 | Valid swing, away from level | 38.2% | 2.9% | 5.20x | Impulse / continuation | 0.160% | True breakout |
| 2025-03-30 18:45 | No confirmed swing | n/a | n/a | 5.20x | Impulse / continuation | 0.037% | True breakout |
| 2026-07-09 07:00 | Golden zone 50-61.8% | 61.8% | 56.2% | 5.20x | Impulse / continuation | -0.430% | True breakout |
| 2025-03-21 10:00 | Valid swing, away from level | 38.2% | 21.2% | 5.20x | Reversal | 0.104% | Liquidity sweep / reversal |
| 2025-02-28 10:45 | Valid swing, away from level | 78.6% | 98.5% | 5.20x | Impulse / continuation | -0.161% | True breakout |
| 2025-05-14 07:00 | Near Fib level | 50.0% | 45.2% | 5.20x | Reversal | -0.082% | Liquidity sweep / reversal |
| 2025-02-12 10:30 | Valid swing, away from level | n/a | -182.0% | 5.20x | Flat / fading | -0.150% | Position building in range |
| 2025-02-14 09:15 | Valid swing, away from level | n/a | -130.7% | 5.20x | Flat / fading | -0.041% | Weak move without breakout |
| 2025-11-10 09:45 | Valid swing, away from level | 38.2% | 6.2% | 5.19x | Impulse / continuation | 0.407% | True breakout |
| 2025-06-23 10:15 | Valid swing, away from level | n/a | 288.6% | 5.18x | Flat / fading | 0.192% | Weak move without breakout |
| 2025-07-24 10:45 | Valid swing, away from level | 78.6% | 70.5% | 5.18x | Impulse / continuation | -0.264% | True breakout |
| 2025-10-09 11:30 | Valid swing, away from level | n/a | 242.9% | 5.18x | Impulse / continuation | 2.338% | True breakout |
| 2026-02-27 10:00 | Valid swing, away from level | n/a | 237.5% | 5.17x | Impulse / continuation | 0.180% | True breakout |
| 2024-11-27 10:00 | Valid swing, away from level | 78.6% | 95.5% | 5.16x | Impulse / continuation | -1.409% | True breakout |
| 2026-03-18 10:15 | Valid swing, away from level | n/a | -89.1% | 5.16x | Impulse / continuation | 0.048% | True breakout |
| 2025-02-05 10:00 | Near Fib level | 38.2% | 37.2% | 5.15x | Impulse / continuation | 0.020% | True breakout |
| 2026-03-02 07:15 | Golden zone 50-61.8% | 50.0% | 50.0% | 5.15x | Reversal | -0.029% | Liquidity sweep / reversal |
| 2026-09-06 17:45 | Near Fib level | 78.6% | 81.6% | 5.15x | Impulse / continuation | -0.824% | True breakout |
| 2024-10-09 11:00 | Valid swing, away from level | 38.2% | 12.3% | 5.15x | Flat / fading | -0.177% | Position building in range |
| 2025-09-11 10:45 | Valid swing, away from level | n/a | 134.7% | 5.15x | Impulse / continuation | -0.326% | True breakout |
| 2025-01-30 10:15 | Valid swing, away from level | 38.2% | 27.7% | 5.15x | Reversal | 0.112% | Liquidity sweep / reversal |
| 2025-06-17 17:45 | Valid swing, away from level | n/a | -37.6% | 5.15x | Flat / fading | 0.125% | Weak move without breakout |
| 2025-09-01 09:15 | Valid swing, away from level | n/a | -439.1% | 5.15x | Reversal | -0.262% | Liquidity sweep / reversal |
| 2025-06-29 15:45 | Golden zone 50-61.8% | 61.8% | 57.1% | 5.14x | Impulse / continuation | 0.067% | True breakout |
| 2026-01-24 15:45 | Near Fib level | 78.6% | 83.0% | 5.14x | Flat / fading | -0.132% | Position building in range |
| 2026-07-05 09:45 | Valid swing, away from level | 38.2% | 16.4% | 5.14x | Impulse / continuation | 0.190% | True breakout |
| 2025-12-01 22:45 | Near Fib level | 61.8% | 65.3% | 5.14x | Impulse / continuation | 0.141% | True breakout |
| 2025-07-03 10:45 | Golden zone 50-61.8% | 50.0% | 52.0% | 5.13x | Impulse / continuation | 0.300% | True breakout |
| 2025-12-23 10:15 | Valid swing, away from level | 78.6% | 84.6% | 5.13x | Impulse / continuation | 0.280% | True breakout |
| 2026-03-20 13:30 | Golden zone 50-61.8% | 61.8% | 58.6% | 5.13x | Flat / fading | 0.084% | Weak move without breakout |
| 2026-06-11 08:00 | Valid swing, away from level | 38.2% | 21.8% | 5.13x | Flat / fading | -0.074% | Position building in range |
| 2026-09-21 07:45 | Valid swing, away from level | n/a | -440.0% | 5.13x | Reversal | 0.283% | Liquidity sweep / reversal |
| 2026-07-22 07:00 | Valid swing, away from level | 38.2% | 23.9% | 5.12x | Flat / fading | -0.274% | Position building in range |
| 2026-04-20 17:15 | Valid swing, away from level | n/a | 156.3% | 5.12x | Reversal | 0.154% | Liquidity sweep / reversal |
| 2025-03-07 17:30 | Valid swing, away from level | 78.6% | 86.4% | 5.11x | Impulse / continuation | -0.457% | True breakout |
| 2026-07-02 14:45 | Valid swing, away from level | n/a | 536.0% | 5.11x | Impulse / continuation | -0.884% | True breakout |
| 2024-11-29 10:15 | Valid swing, away from level | n/a | 111.2% | 5.10x | Impulse / continuation | 1.117% | True breakout |
| 2026-09-23 10:00 | Near Fib level | 78.6% | 77.2% | 5.10x | Reversal | 0.062% | Liquidity sweep / reversal |
| 2025-09-25 18:15 | Valid swing, away from level | n/a | 158.6% | 5.09x | Impulse / continuation | -0.122% | True breakout |
| 2025-09-09 10:00 | Valid swing, away from level | n/a | -49.3% | 5.09x | Flat / fading | -0.036% | Weak move without breakout |
| 2026-03-09 22:30 | Valid swing, away from level | n/a | -1.4% | 5.09x | Impulse / continuation | 0.646% | True breakout |
| 2026-02-09 11:00 | Valid swing, away from level | n/a | 393.3% | 5.08x | Reversal | 0.177% | Liquidity sweep / reversal |
| 2026-02-01 14:00 | Valid swing, away from level | 38.2% | 11.4% | 5.08x | Flat / fading | 0.012% | Position building in range |
| 2025-10-20 07:00 | Valid swing, away from level | 38.2% | 25.0% | 5.07x | Impulse / continuation | -0.083% | True breakout |
| 2025-04-29 12:30 | Valid swing, away from level | n/a | 110.5% | 5.07x | Flat / fading | -0.024% | Position building in range |
| 2024-11-02 10:15 | Valid swing, away from level | 38.2% | 4.3% | 5.06x | Flat / fading | -0.017% | Weak move without breakout |
| 2026-06-28 11:00 | Valid swing, away from level | 38.2% | 16.1% | 5.06x | Flat / fading | -0.038% | Position building in range |
| 2025-07-16 10:15 | Near Fib level | 78.6% | 79.6% | 5.05x | Impulse -> reversal | 0.356% | False breakout |
| 2026-04-30 10:15 | Valid swing, away from level | 38.2% | 8.7% | 5.05x | Impulse / continuation | 0.007% | True breakout |
| 2026-07-06 16:00 | Valid swing, away from level | n/a | 122.6% | 5.05x | Impulse / continuation | -2.142% | True breakout |
| 2026-04-22 07:45 | Valid swing, away from level | 78.6% | 96.4% | 5.05x | Flat / fading | -0.043% | Position building in range |
| 2025-09-30 10:15 | Valid swing, away from level | n/a | 108.2% | 5.04x | Reversal | 0.202% | Liquidity sweep / reversal |
| 2025-07-14 10:00 | Valid swing, away from level | n/a | -216.9% | 5.04x | Impulse / continuation | 1.182% | True breakout |
| 2025-07-22 11:30 | Valid swing, away from level | n/a | 177.4% | 5.04x | Impulse / continuation | 0.173% | True breakout |
| 2025-02-26 13:15 | Valid swing, away from level | n/a | 225.5% | 5.04x | Impulse / continuation | -0.529% | True breakout |
| 2024-12-03 10:30 | Valid swing, away from level | n/a | 109.7% | 5.04x | Impulse / continuation | -0.570% | True breakout |
| 2025-08-06 20:00 | Valid swing, away from level | n/a | -66.3% | 5.03x | Impulse / continuation | 0.450% | True breakout |
| 2025-11-29 18:15 | Valid swing, away from level | n/a | 185.7% | 5.03x | Reversal | 0.083% | Liquidity sweep / reversal |
| 2026-04-03 10:15 | Near Fib level | 78.6% | 77.5% | 5.03x | Impulse / continuation | 0.056% | True breakout |
| 2025-08-06 17:00 | Valid swing, away from level | 78.6% | 71.4% | 5.03x | Impulse / continuation | -0.311% | True breakout |
| 2025-01-20 10:15 | Valid swing, away from level | n/a | -54.7% | 5.03x | Reversal | -0.956% | Liquidity sweep / reversal |
| 2025-03-24 21:15 | Valid swing, away from level | n/a | 110.1% | 5.02x | Reversal | 0.140% | Liquidity sweep / reversal |
| 2025-02-20 10:45 | Golden zone 50-61.8% | 61.8% | 61.5% | 5.02x | Flat / fading | -0.121% | Weak move without breakout |
| 2025-02-07 10:15 | Golden zone 50-61.8% | 50.0% | 51.8% | 5.02x | Reversal | 0.032% | Liquidity sweep / reversal |
| 2024-10-23 10:45 | Valid swing, away from level | n/a | 159.5% | 5.01x | Reversal | -0.020% | Liquidity sweep / reversal |
| 2024-12-18 19:00 | Valid swing, away from level | n/a | -193.2% | 5.01x | Reversal | 0.124% | Liquidity sweep / reversal |
| 2026-01-06 09:30 | Valid swing, away from level | n/a | -72.7% | 5.01x | Impulse / continuation | 0.317% | True breakout |
| 2026-09-15 13:15 | Valid swing, away from level | 38.2% | 25.7% | 5.01x | Flat / fading | -0.459% | Position building in range |
| 2025-01-31 09:30 | Valid swing, away from level | n/a | -55.7% | 5.00x | Impulse / continuation | 0.189% | True breakout |
| 2026-04-01 07:00 | Valid swing, away from level | 78.6% | 72.8% | 5.00x | Impulse / continuation | -0.025% | True breakout |
| 2026-04-10 13:45 | Valid swing, away from level | 38.2% | 14.7% | 5.00x | Impulse / continuation | 0.351% | True breakout |
| 2025-12-25 10:15 | Valid swing, away from level | n/a | 152.4% | 4.98x | Reversal | 0.585% | Liquidity sweep / reversal |
| 2026-08-05 10:15 | Valid swing, away from level | n/a | -110.5% | 4.98x | Reversal | -0.429% | Liquidity sweep / reversal |
| 2026-06-25 09:30 | Golden zone 50-61.8% | 61.8% | 61.2% | 4.98x | Impulse / continuation | 0.207% | True breakout |
| 2025-09-26 10:00 | Near Fib level | 38.2% | 36.6% | 4.98x | Impulse / continuation | -0.141% | True breakout |
| 2025-03-14 16:30 | Valid swing, away from level | n/a | -151.3% | 4.98x | Reversal | -0.627% | Liquidity sweep / reversal |
| 2025-02-04 10:30 | Valid swing, away from level | n/a | -4.0% | 4.98x | Reversal | -0.223% | Liquidity sweep / reversal |
| 2025-03-18 16:15 | Valid swing, away from level | n/a | -102.2% | 4.97x | Impulse / continuation | 0.312% | True breakout |
| 2025-02-21 09:45 | Valid swing, away from level | n/a | -23.0% | 4.97x | Impulse / continuation | 0.203% | True breakout |
| 2026-06-02 09:00 | Valid swing, away from level | 38.2% | 11.9% | 4.97x | Reversal | 0.020% | Liquidity sweep / reversal |
| 2025-10-30 10:15 | Valid swing, away from level | n/a | -123.4% | 4.97x | Reversal | -0.041% | Liquidity sweep / reversal |
| 2026-02-09 07:15 | Valid swing, away from level | n/a | 140.8% | 4.97x | Reversal | -0.018% | Liquidity sweep / reversal |
| 2026-05-21 09:15 | Golden zone 50-61.8% | 50.0% | 51.3% | 4.97x | Reversal | -0.876% | Liquidity sweep / reversal |
| 2026-03-26 09:15 | Valid swing, away from level | 38.2% | 18.4% | 4.96x | Reversal | -0.192% | Liquidity sweep / reversal |
| 2026-04-20 09:15 | Valid swing, away from level | 38.2% | 13.8% | 4.96x | Reversal | -0.135% | Liquidity sweep / reversal |
| 2026-03-18 07:00 | Near Fib level | 50.0% | 50.0% | 4.96x | Flat / fading | 0.149% | Position building in range |
| 2026-08-17 08:15 | Valid swing, away from level | n/a | 194.9% | 4.95x | Impulse / continuation | -0.630% | True breakout |
| 2025-09-05 10:00 | Valid swing, away from level | 38.2% | 29.1% | 4.95x | Flat / fading | -0.012% | Weak move without breakout |
| 2026-02-24 08:00 | Valid swing, away from level | n/a | -132.4% | 4.95x | Reversal | -0.119% | Liquidity sweep / reversal |
| 2025-05-14 10:15 | Near Fib level | 78.6% | 80.4% | 4.94x | Impulse / continuation | 0.133% | True breakout |
| 2026-06-14 10:00 | Golden zone 50-61.8% | 50.0% | 53.8% | 4.94x | Flat / fading | -0.014% | Position building in range |
| 2025-11-12 15:00 | Valid swing, away from level | n/a | 249.2% | 4.94x | Impulse / continuation | -0.223% | True breakout |
| 2025-03-13 09:00 | Valid swing, away from level | n/a | 157.6% | 4.94x | Impulse / continuation | 0.018% | True breakout |
| 2024-10-25 13:45 | Near Fib level | 38.2% | 37.9% | 4.93x | Flat / fading | -0.750% | Position building in range |
| 2024-11-27 10:30 | Valid swing, away from level | n/a | 113.8% | 4.93x | Reversal | -0.707% | Liquidity sweep / reversal |
| 2024-10-07 10:45 | Valid swing, away from level | 78.6% | 100.0% | 4.93x | Impulse / continuation | -0.020% | True breakout |
| 2024-12-12 10:45 | Valid swing, away from level | n/a | -24.3% | 4.93x | Flat / fading | -0.195% | Position building in range |
| 2024-11-12 10:45 | Valid swing, away from level | n/a | 146.9% | 4.92x | Reversal | 0.279% | Liquidity sweep / reversal |
| 2026-08-10 07:30 | Valid swing, away from level | 38.2% | 23.0% | 4.92x | Impulse -> reversal | 0.036% | False breakout |
| 2025-09-15 10:15 | Valid swing, away from level | n/a | 120.0% | 4.92x | Impulse / continuation | -0.685% | True breakout |
| 2026-05-04 07:30 | Valid swing, away from level | n/a | -146.8% | 4.91x | Impulse / continuation | 0.078% | True breakout |
| 2024-10-23 10:30 | Valid swing, away from level | n/a | 156.8% | 4.91x | Impulse / continuation | -0.059% | True breakout |
| 2026-04-17 10:15 | Valid swing, away from level | n/a | -192.5% | 4.91x | Reversal | -0.073% | Liquidity sweep / reversal |
| 2026-09-09 10:15 | Valid swing, away from level | n/a | 113.7% | 4.91x | Reversal | 0.077% | Liquidity sweep / reversal |
| 2025-10-14 10:45 | Near Fib level | 78.6% | 81.4% | 4.91x | Reversal | 0.193% | Liquidity sweep / reversal |
| 2026-01-22 10:30 | Valid swing, away from level | 38.2% | 2.0% | 4.90x | Reversal | -0.149% | Liquidity sweep / reversal |
| 2025-10-19 10:30 | Valid swing, away from level | n/a | 167.3% | 4.90x | Impulse / continuation | -0.165% | True breakout |
| 2026-03-02 09:00 | Near Fib level | 61.8% | 66.7% | 4.90x | Impulse / continuation | -0.058% | True breakout |
| 2025-12-28 10:45 | Valid swing, away from level | n/a | 214.0% | 4.90x | Reversal | 0.074% | Liquidity sweep / reversal |
| 2024-11-05 10:30 | Near Fib level | 61.8% | 64.1% | 4.90x | Reversal | 0.259% | Liquidity sweep / reversal |
| 2025-11-18 10:30 | Valid swing, away from level | n/a | -166.7% | 4.90x | Reversal | 1.339% | Liquidity sweep / reversal |
| 2026-06-22 22:30 | Valid swing, away from level | n/a | 161.3% | 4.90x | Impulse / continuation | 1.450% | True breakout |
| 2024-10-02 10:15 | Valid swing, away from level | n/a | -11.8% | 4.90x | Reversal | -0.232% | Liquidity sweep / reversal |
| 2025-05-19 17:00 | Valid swing, away from level | n/a | 141.9% | 4.90x | Reversal | 0.777% | Liquidity sweep / reversal |
| 2025-07-06 11:00 | Valid swing, away from level | n/a | 541.7% | 4.90x | Reversal | 0.162% | Liquidity sweep / reversal |
| 2025-09-03 16:45 | Golden zone 50-61.8% | 61.8% | 61.1% | 4.89x | Flat / fading | 0.182% | Position building in range |
| 2025-10-13 07:15 | Valid swing, away from level | n/a | -218.2% | 4.89x | Reversal | 0.089% | Liquidity sweep / reversal |
| 2026-01-19 11:30 | Valid swing, away from level | n/a | -101.8% | 4.89x | Flat / fading | -0.091% | Position building in range |
| 2025-12-22 09:00 | Near Fib level | 78.6% | 75.0% | 4.89x | Impulse / continuation | -0.320% | True breakout |
| 2026-04-05 17:30 | Valid swing, away from level | 38.2% | 29.0% | 4.88x | Reversal | -0.019% | Liquidity sweep / reversal |
| 2025-05-27 07:45 | Valid swing, away from level | n/a | 135.4% | 4.87x | Reversal | 0.620% | Liquidity sweep / reversal |
| 2026-06-29 11:15 | Valid swing, away from level | 38.2% | 28.3% | 4.87x | Impulse / continuation | 1.007% | True breakout |
| 2026-03-31 11:15 | Valid swing, away from level | n/a | -127.3% | 4.87x | Impulse / continuation | 0.647% | True breakout |
| 2024-10-11 19:45 | Valid swing, away from level | 38.2% | 23.9% | 4.87x | Flat / fading | -0.253% | Weak move without breakout |
| 2025-06-06 07:00 | Valid swing, away from level | 38.2% | 31.8% | 4.87x | Impulse / continuation | 0.121% | True breakout |
| 2025-04-27 16:15 | Valid swing, away from level | 38.2% | 23.6% | 4.87x | Flat / fading | 0.090% | Weak move without breakout |
| 2025-04-09 10:00 | Valid swing, away from level | 61.8% | 67.1% | 4.85x | Reversal | 0.935% | Liquidity sweep / reversal |
| 2026-06-05 11:15 | Valid swing, away from level | n/a | 103.8% | 4.85x | Flat / fading | 0.100% | Position building in range |
| 2026-09-21 08:00 | Valid swing, away from level | n/a | -900.0% | 4.85x | Impulse / continuation | -0.094% | True breakout |
| 2025-10-16 17:15 | Valid swing, away from level | n/a | -378.3% | 4.84x | Impulse / continuation | 0.432% | True breakout |
| 2026-06-29 09:00 | Valid swing, away from level | n/a | 137.5% | 4.84x | Impulse / continuation | -0.196% | True breakout |
| 2024-12-03 11:00 | Valid swing, away from level | n/a | 234.7% | 4.84x | Impulse / continuation | 0.338% | True breakout |
| 2024-09-27 11:45 | Valid swing, away from level | n/a | -160.0% | 4.84x | Flat / fading | 0.303% | Weak move without breakout |
| 2024-11-21 10:00 | Near Fib level | 78.6% | 74.8% | 4.83x | Reversal | -0.517% | Liquidity sweep / reversal |
| 2026-03-23 07:00 | Valid swing, away from level | n/a | 102.6% | 4.83x | Impulse -> reversal | 0.426% | False breakout |
| 2024-12-04 11:00 | Valid swing, away from level | n/a | -16.0% | 4.83x | Impulse / continuation | 0.017% | True breakout |
| 2025-12-22 09:15 | Valid swing, away from level | n/a | 120.8% | 4.83x | Impulse / continuation | -0.565% | True breakout |
| 2025-09-19 10:00 | Near Fib level | 50.0% | 47.5% | 4.83x | Reversal | -0.051% | Liquidity sweep / reversal |
| 2025-09-11 07:45 | Near Fib level | 78.6% | 76.0% | 4.83x | Impulse / continuation | 0.066% | True breakout |
| 2026-06-16 16:30 | Valid swing, away from level | n/a | 647.8% | 4.83x | Flat / fading | 0.208% | Position building in range |
| 2025-03-28 10:00 | Valid swing, away from level | 78.6% | 72.6% | 4.82x | Impulse / continuation | 0.984% | True breakout |
| 2025-11-16 10:30 | Valid swing, away from level | n/a | 353.8% | 4.82x | Flat / fading | 0.027% | Position building in range |
| 2025-07-04 09:00 | Valid swing, away from level | n/a | 220.9% | 4.82x | Flat / fading | 0.160% | Position building in range |
| 2026-07-04 17:45 | Valid swing, away from level | 78.6% | 73.3% | 4.81x | Impulse / continuation | -0.080% | True breakout |
| 2025-03-18 10:00 | Valid swing, away from level | n/a | -136.6% | 4.81x | Flat / fading | -0.112% | Weak move without breakout |
| 2025-02-28 21:15 | Valid swing, away from level | n/a | -34.1% | 4.80x | Flat / fading | 0.429% | Position building in range |
| 2024-10-29 10:30 | Valid swing, away from level | 78.6% | 85.4% | 4.80x | Reversal | -0.876% | Liquidity sweep / reversal |
| 2025-08-25 08:15 | Near Fib level | 50.0% | 47.4% | 4.80x | Reversal | -0.101% | Liquidity sweep / reversal |
| 2025-07-25 07:00 | Golden zone 50-61.8% | 50.0% | 51.4% | 4.80x | Flat / fading | -0.096% | Position building in range |
| 2026-09-17 07:00 | Valid swing, away from level | n/a | 112.1% | 4.80x | Impulse / continuation | 0.133% | True breakout |
| 2026-01-05 07:00 | Valid swing, away from level | n/a | 113.0% | 4.80x | Impulse / continuation | -0.189% | True breakout |
| 2026-07-15 07:00 | Valid swing, away from level | 78.6% | 85.5% | 4.79x | Reversal | -0.120% | Liquidity sweep / reversal |
| 2025-04-22 21:00 | Valid swing, away from level | n/a | -68.5% | 4.79x | Reversal | -0.274% | Liquidity sweep / reversal |
| 2025-06-23 10:00 | Valid swing, away from level | n/a | 215.7% | 4.79x | Impulse / continuation | -0.179% | True breakout |
| 2025-02-18 10:15 | Valid swing, away from level | n/a | 136.3% | 4.79x | Flat / fading | 0.284% | Weak move without breakout |
| 2026-05-06 17:45 | Valid swing, away from level | n/a | -32.2% | 4.78x | Flat / fading | -0.103% | Position building in range |
| 2024-12-05 10:15 | Valid swing, away from level | 61.8% | 69.8% | 4.78x | Reversal | 0.780% | Liquidity sweep / reversal |
| 2026-08-04 07:00 | Valid swing, away from level | n/a | -8.3% | 4.78x | Impulse / continuation | 0.395% | True breakout |
| 2025-07-22 10:15 | Golden zone 50-61.8% | 61.8% | 56.5% | 4.78x | Reversal | -0.238% | Liquidity sweep / reversal |
| 2024-12-20 10:15 | Near Fib level | 50.0% | 49.0% | 4.78x | Reversal | 0.273% | Liquidity sweep / reversal |
| 2025-10-31 10:30 | Valid swing, away from level | n/a | 104.9% | 4.78x | Flat / fading | -0.310% | Weak move without breakout |
| 2025-12-24 10:00 | Valid swing, away from level | n/a | 111.3% | 4.77x | Impulse / continuation | -0.227% | True breakout |
| 2026-09-22 10:30 | Valid swing, away from level | n/a | -12.5% | 4.77x | Flat / fading | 0.147% | Weak move without breakout |
| 2026-06-06 18:30 | Valid swing, away from level | 78.6% | 96.5% | 4.77x | Impulse -> reversal | 0.040% | False breakout |
| 2026-01-19 11:15 | Valid swing, away from level | n/a | -12.7% | 4.77x | Impulse / continuation | 0.165% | True breakout |
| 2025-04-01 10:00 | Valid swing, away from level | n/a | -28.0% | 4.77x | Flat / fading | -0.012% | Position building in range |
| 2025-10-01 10:45 | Near Fib level | 78.6% | 80.4% | 4.77x | Impulse / continuation | 0.104% | True breakout |
| 2025-07-04 11:00 | Valid swing, away from level | 78.6% | 92.7% | 4.77x | Flat / fading | -0.229% | Weak move without breakout |
| 2025-03-18 16:30 | Valid swing, away from level | n/a | -201.1% | 4.77x | Flat / fading | -0.066% | Weak move without breakout |
| 2025-04-25 10:00 | Valid swing, away from level | n/a | -26.3% | 4.76x | Reversal | -0.271% | Liquidity sweep / reversal |
| 2025-10-30 09:15 | Valid swing, away from level | n/a | -22.0% | 4.76x | Impulse / continuation | 0.730% | True breakout |
| 2025-07-09 10:15 | Valid swing, away from level | 38.2% | 18.7% | 4.76x | Impulse -> reversal | 0.057% | False breakout |
| 2024-11-18 10:15 | Near Fib level | 38.2% | 36.1% | 4.75x | Impulse / continuation | 0.814% | True breakout |
| 2026-01-29 11:00 | Valid swing, away from level | n/a | -251.6% | 4.75x | Flat / fading | -0.095% | Weak move without breakout |
| 2025-07-07 12:45 | Valid swing, away from level | n/a | -104.8% | 4.75x | Reversal | -0.316% | Liquidity sweep / reversal |
| 2026-06-01 09:15 | Valid swing, away from level | n/a | -329.4% | 4.74x | Impulse / continuation | 0.264% | True breakout |
| 2025-12-29 07:15 | Near Fib level | 61.8% | 64.0% | 4.74x | Impulse / continuation | 0.167% | True breakout |
| 2026-04-05 18:45 | Valid swing, away from level | 61.8% | 67.7% | 4.74x | Reversal | 0.317% | Liquidity sweep / reversal |
| 2025-04-26 16:45 | Valid swing, away from level | 38.2% | 25.1% | 4.74x | Reversal | -0.091% | Liquidity sweep / reversal |
| 2025-03-04 10:30 | Valid swing, away from level | n/a | -193.0% | 4.74x | Impulse / continuation | 0.592% | True breakout |
| 2025-06-18 07:00 | Valid swing, away from level | n/a | -4.0% | 4.74x | Reversal | -0.043% | Liquidity sweep / reversal |
| 2025-01-17 11:15 | Valid swing, away from level | n/a | -73.5% | 4.73x | Flat / fading | -0.253% | Weak move without breakout |
| 2025-12-17 09:00 | Valid swing, away from level | 38.2% | 28.4% | 4.73x | Impulse / continuation | -0.458% | True breakout |
| 2024-12-04 10:45 | Valid swing, away from level | 38.2% | 19.1% | 4.73x | Impulse / continuation | 0.796% | True breakout |
| 2025-10-01 15:00 | Valid swing, away from level | n/a | 110.2% | 4.72x | Flat / fading | 0.255% | Weak move without breakout |
| 2025-12-18 10:45 | Valid swing, away from level | 38.2% | 17.0% | 4.72x | Flat / fading | -0.123% | Weak move without breakout |
| 2025-09-03 10:00 | Valid swing, away from level | n/a | -7.5% | 4.72x | Impulse / continuation | -0.482% | True breakout |
| 2026-04-08 07:00 | Near Fib level | 78.6% | 82.8% | 4.72x | Flat / fading | 0.169% | Weak move without breakout |
| 2025-04-14 10:00 | Valid swing, away from level | n/a | 116.1% | 4.72x | Flat / fading | 0.210% | Weak move without breakout |
| 2026-04-28 16:45 | Valid swing, away from level | n/a | 320.1% | 4.72x | Flat / fading | 0.231% | Position building in range |
| 2024-12-13 10:30 | Valid swing, away from level | n/a | 106.9% | 4.72x | Reversal | -0.719% | Liquidity sweep / reversal |
| 2024-10-03 10:15 | Near Fib level | 78.6% | 77.6% | 4.72x | Reversal | 1.042% | Liquidity sweep / reversal |
| 2025-04-17 20:45 | Valid swing, away from level | 38.2% | 21.8% | 4.71x | Flat / fading | 0.669% | Weak move without breakout |
| 2025-07-07 10:15 | Near Fib level | 38.2% | 41.3% | 4.71x | Reversal | 0.137% | Liquidity sweep / reversal |
| 2026-05-31 11:15 | Valid swing, away from level | 38.2% | 25.0% | 4.71x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2024-11-18 10:30 | Valid swing, away from level | 38.2% | 12.2% | 4.71x | Flat / fading | 0.116% | Weak move without breakout |
| 2025-01-29 11:00 | Valid swing, away from level | n/a | -9.4% | 4.71x | Impulse / continuation | 0.232% | True breakout |
| 2025-06-06 13:15 | Valid swing, away from level | n/a | 233.0% | 4.70x | Reversal | 1.946% | Liquidity sweep / reversal |
| 2025-09-12 10:15 | Valid swing, away from level | n/a | 109.1% | 4.70x | Reversal | -0.166% | Liquidity sweep / reversal |
| 2025-07-23 07:00 | Near Fib level | 50.0% | 49.2% | 4.70x | Flat / fading | -0.090% | Weak move without breakout |
| 2024-12-19 11:15 | Valid swing, away from level | n/a | -1.0% | 4.70x | Impulse / continuation | 0.238% | True breakout |
| 2025-07-24 11:00 | Valid swing, away from level | n/a | 113.3% | 4.70x | Impulse / continuation | -0.181% | True breakout |
| 2025-12-18 07:00 | Valid swing, away from level | n/a | -15.6% | 4.70x | Reversal | -0.074% | Liquidity sweep / reversal |
| 2026-02-23 16:00 | Near Fib level | 38.2% | 41.2% | 4.70x | Flat / fading | -0.023% | Position building in range |
| 2025-09-08 08:15 | Valid swing, away from level | n/a | -208.7% | 4.69x | Impulse / continuation | 0.155% | True breakout |
| 2025-03-05 07:00 | Golden zone 50-61.8% | 61.8% | 56.6% | 4.69x | Flat / fading | -0.072% | Position building in range |
| 2024-12-26 10:15 | Valid swing, away from level | n/a | -38.5% | 4.68x | Impulse / continuation | -0.151% | True breakout |
| 2026-05-13 17:45 | Valid swing, away from level | 38.2% | 13.5% | 4.68x | Flat / fading | -0.044% | Position building in range |
| 2025-10-21 18:15 | Valid swing, away from level | n/a | 327.1% | 4.68x | Impulse / continuation | 0.804% | True breakout |
| 2025-12-28 10:30 | Valid swing, away from level | n/a | 207.0% | 4.68x | Impulse / continuation | 0.117% | True breakout |
| 2025-07-28 09:00 | Valid swing, away from level | n/a | -192.7% | 4.68x | Flat / fading | -0.141% | Weak move without breakout |
| 2025-10-21 07:45 | Valid swing, away from level | n/a | 1107.1% | 4.67x | Impulse / continuation | 0.266% | True breakout |
| 2026-01-06 11:45 | Valid swing, away from level | n/a | -250.9% | 4.67x | Reversal | -0.315% | Liquidity sweep / reversal |
| 2025-10-19 16:15 | Valid swing, away from level | n/a | 115.4% | 4.67x | Reversal | 0.096% | Liquidity sweep / reversal |
| 2025-02-20 15:45 | Golden zone 50-61.8% | 50.0% | 54.5% | 4.67x | Reversal | 0.104% | Liquidity sweep / reversal |
| 2025-12-17 07:00 | Valid swing, away from level | 38.2% | 17.0% | 4.67x | Impulse / continuation | 0.067% | True breakout |
| 2026-01-22 10:00 | Valid swing, away from level | 38.2% | 16.9% | 4.67x | Impulse / continuation | 0.030% | True breakout |
| 2026-05-06 09:00 | Valid swing, away from level | 78.6% | 88.2% | 4.67x | Impulse / continuation | -0.356% | True breakout |
| 2025-08-23 18:45 | Near Fib level | 50.0% | 50.0% | 4.66x | Reversal | -0.171% | Liquidity sweep / reversal |
| 2026-04-26 18:45 | Valid swing, away from level | n/a | 160.0% | 4.66x | Reversal | -0.031% | Liquidity sweep / reversal |
| 2026-09-06 11:00 | Valid swing, away from level | 78.6% | 85.3% | 4.66x | Flat / fading | 0.305% | Weak move without breakout |
| 2026-03-09 18:30 | Valid swing, away from level | 38.2% | 0.5% | 4.66x | Impulse / continuation | -0.094% | True breakout |
| 2026-03-30 12:15 | Golden zone 50-61.8% | 50.0% | 51.6% | 4.65x | Impulse / continuation | -0.025% | True breakout |
| 2025-07-25 10:00 | Golden zone 50-61.8% | 50.0% | 55.8% | 4.65x | Flat / fading | -0.085% | Position building in range |
| 2025-01-30 09:00 | Near Fib level | 38.2% | 37.8% | 4.65x | Impulse / continuation | 0.237% | True breakout |
| 2025-12-26 23:15 | Valid swing, away from level | n/a | -66.7% | 4.65x | Impulse / continuation | 0.326% | True breakout |
| 2026-09-21 10:00 | Valid swing, away from level | n/a | -287.5% | 4.65x | Impulse / continuation | -0.079% | True breakout |
| 2025-08-27 07:00 | Valid swing, away from level | 38.2% | 9.6% | 4.64x | Flat / fading | 0.065% | Position building in range |
| 2025-11-07 21:00 | Valid swing, away from level | n/a | 134.4% | 4.64x | Flat / fading | 0.047% | Weak move without breakout |
| 2026-02-26 09:15 | Valid swing, away from level | 38.2% | 17.5% | 4.64x | Impulse / continuation | 0.165% | True breakout |
| 2026-02-06 07:00 | Near Fib level | 78.6% | 73.9% | 4.64x | Flat / fading | -0.030% | Weak move without breakout |
| 2026-03-16 10:00 | Valid swing, away from level | 38.2% | 15.1% | 4.64x | Impulse / continuation | -0.141% | True breakout |
| 2025-08-01 19:45 | Valid swing, away from level | n/a | 136.8% | 4.63x | Impulse / continuation | 0.434% | True breakout |
| 2025-05-06 09:15 | Valid swing, away from level | n/a | 110.3% | 4.63x | Reversal | 1.372% | Liquidity sweep / reversal |
| 2026-06-04 19:15 | Valid swing, away from level | n/a | 193.3% | 4.63x | Flat / fading | 0.000% | Position building in range |
| 2025-06-24 10:15 | Valid swing, away from level | 78.6% | 86.2% | 4.63x | Impulse -> reversal | -0.266% | False breakout |
| 2026-08-11 10:15 | Valid swing, away from level | n/a | -243.5% | 4.63x | Reversal | 0.014% | Liquidity sweep / reversal |
| 2025-05-28 07:00 | Valid swing, away from level | n/a | -20.7% | 4.62x | Impulse / continuation | 0.205% | True breakout |
| 2026-03-19 10:15 | Near Fib level | 38.2% | 37.5% | 4.62x | Impulse / continuation | 0.179% | True breakout |
| 2026-01-26 16:15 | Near Fib level | 78.6% | 74.8% | 4.62x | Reversal | -0.235% | Liquidity sweep / reversal |
| 2026-03-15 18:30 | Valid swing, away from level | n/a | -66.7% | 4.62x | Impulse / continuation | 0.395% | True breakout |
| 2026-04-28 09:00 | Valid swing, away from level | 78.6% | 73.1% | 4.62x | Reversal | -0.258% | Liquidity sweep / reversal |
| 2026-08-09 18:15 | Near Fib level | 38.2% | 37.5% | 4.62x | Reversal | 0.079% | Liquidity sweep / reversal |
| 2025-11-11 10:00 | Near Fib level | 61.8% | 62.4% | 4.62x | Reversal | 0.128% | Liquidity sweep / reversal |
| 2025-03-25 17:45 | Near Fib level | 78.6% | 83.4% | 4.61x | Impulse / continuation | 0.279% | True breakout |
| 2025-01-28 10:00 | Golden zone 50-61.8% | 61.8% | 60.6% | 4.61x | Reversal | 0.184% | Liquidity sweep / reversal |
| 2026-01-30 11:30 | Valid swing, away from level | n/a | 127.9% | 4.61x | Impulse / continuation | -0.251% | True breakout |
| 2026-07-31 07:00 | Valid swing, away from level | 50.0% | 44.6% | 4.61x | Impulse / continuation | -0.421% | True breakout |
| 2025-11-05 11:15 | Valid swing, away from level | n/a | -18.9% | 4.61x | Flat / fading | -0.213% | Weak move without breakout |
| 2025-08-06 17:15 | Valid swing, away from level | n/a | 101.0% | 4.61x | Flat / fading | 0.156% | Weak move without breakout |
| 2026-05-15 17:00 | Valid swing, away from level | n/a | 134.5% | 4.60x | Impulse / continuation | -0.546% | True breakout |
| 2026-06-15 07:15 | Valid swing, away from level | n/a | -2012.5% | 4.59x | Impulse / continuation | 0.040% | True breakout |
| 2025-12-01 09:15 | Near Fib level | 78.6% | 75.3% | 4.59x | Reversal | -0.109% | Liquidity sweep / reversal |
| 2025-11-17 11:00 | Valid swing, away from level | n/a | -159.0% | 4.59x | Reversal | -0.184% | Liquidity sweep / reversal |
| 2025-05-26 07:30 | Valid swing, away from level | n/a | 166.3% | 4.59x | Impulse / continuation | -0.249% | True breakout |
| 2025-02-21 10:00 | Valid swing, away from level | n/a | -18.7% | 4.59x | Reversal | 0.220% | Liquidity sweep / reversal |
| 2025-09-29 18:15 | Valid swing, away from level | n/a | 155.2% | 4.59x | Flat / fading | -0.097% | Weak move without breakout |
| 2026-05-11 19:45 | Valid swing, away from level | 78.6% | 86.4% | 4.58x | Reversal | 0.174% | Liquidity sweep / reversal |
| 2025-04-15 10:00 | Near Fib level | 50.0% | 49.0% | 4.58x | Reversal | -0.556% | Liquidity sweep / reversal |
| 2024-10-16 10:15 | Valid swing, away from level | 38.2% | 29.1% | 4.58x | Reversal | 0.076% | Liquidity sweep / reversal |
| 2025-08-18 07:45 | Valid swing, away from level | n/a | -165.9% | 4.58x | Impulse / continuation | 0.228% | True breakout |
| 2026-02-13 12:30 | Valid swing, away from level | n/a | -5.6% | 4.57x | Reversal | 0.646% | Liquidity sweep / reversal |
| 2026-07-01 08:15 | Valid swing, away from level | n/a | -77.6% | 4.57x | Impulse / continuation | 0.080% | True breakout |
| 2026-03-31 07:00 | Valid swing, away from level | 38.2% | 12.6% | 4.57x | Flat / fading | 0.006% | Weak move without breakout |
| 2026-08-20 08:00 | Near Fib level | 50.0% | 49.4% | 4.57x | Impulse -> reversal | 0.324% | False breakout |
| 2024-11-28 10:00 | Valid swing, away from level | n/a | -35.2% | 4.57x | Reversal | 0.317% | Liquidity sweep / reversal |
| 2025-06-27 10:00 | Golden zone 50-61.8% | 61.8% | 56.7% | 4.57x | Flat / fading | 0.105% | Weak move without breakout |
| 2024-12-27 10:00 | Golden zone 50-61.8% | 61.8% | 59.2% | 4.56x | Flat / fading | 0.106% | Weak move without breakout |
| 2025-08-27 11:00 | Valid swing, away from level | n/a | -92.3% | 4.56x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-03-30 12:00 | Near Fib level | 78.6% | 77.4% | 4.56x | Impulse / continuation | 0.180% | True breakout |
| 2025-05-21 10:15 | Near Fib level | 61.8% | 65.1% | 4.56x | Reversal | -0.033% | Liquidity sweep / reversal |
| 2026-08-08 17:30 | Valid swing, away from level | n/a | -112.3% | 4.56x | Reversal | -0.258% | Liquidity sweep / reversal |
| 2025-09-08 09:00 | Valid swing, away from level | n/a | -343.5% | 4.56x | Flat / fading | -0.119% | Weak move without breakout |
| 2025-03-03 22:30 | Valid swing, away from level | n/a | -19.2% | 4.56x | Reversal | -0.655% | Liquidity sweep / reversal |
| 2025-12-19 13:15 | Valid swing, away from level | 38.2% | 2.4% | 4.56x | Reversal | -1.098% | Liquidity sweep / reversal |
| 2025-09-13 17:00 | Near Fib level | 78.6% | 82.6% | 4.55x | Impulse / continuation | -0.044% | True breakout |
| 2026-05-15 18:30 | Valid swing, away from level | n/a | 208.5% | 4.55x | Reversal | -0.052% | Liquidity sweep / reversal |
| 2026-03-09 19:00 | Valid swing, away from level | n/a | -2.1% | 4.55x | Reversal | -0.270% | Liquidity sweep / reversal |
| 2026-09-03 12:30 | Near Fib level | 38.2% | 39.5% | 4.55x | Impulse / continuation | 0.235% | True breakout |
| 2025-03-26 10:00 | Valid swing, away from level | 38.2% | 24.3% | 4.55x | Impulse / continuation | 0.066% | True breakout |
| 2025-08-29 13:30 | Valid swing, away from level | n/a | 142.4% | 4.54x | Impulse / continuation | -0.470% | True breakout |
| 2025-09-01 07:15 | Valid swing, away from level | n/a | -41.7% | 4.54x | Impulse / continuation | 0.066% | True breakout |
| 2025-09-09 07:00 | Valid swing, away from level | n/a | -33.8% | 4.54x | Impulse / continuation | 0.083% | True breakout |
| 2025-07-27 17:45 | Valid swing, away from level | n/a | -2.4% | 4.54x | Flat / fading | 0.006% | Position building in range |
| 2026-06-15 10:15 | Valid swing, away from level | n/a | -3175.0% | 4.54x | Flat / fading | -0.020% | Weak move without breakout |
| 2026-09-23 12:15 | Valid swing, away from level | n/a | 152.2% | 4.54x | Reversal | -0.297% | Liquidity sweep / reversal |
| 2026-04-03 07:00 | Valid swing, away from level | 38.2% | 17.8% | 4.54x | Impulse / continuation | 0.289% | True breakout |
| 2026-04-19 14:30 | Valid swing, away from level | n/a | -7.9% | 4.54x | Flat / fading | 0.025% | Weak move without breakout |
| 2026-08-31 07:30 | Valid swing, away from level | n/a | -54.5% | 4.53x | Impulse / continuation | 0.208% | True breakout |
| 2025-03-24 10:45 | Valid swing, away from level | n/a | 135.5% | 4.53x | Reversal | 0.217% | Liquidity sweep / reversal |
| 2025-10-15 13:00 | Valid swing, away from level | 38.2% | 10.2% | 4.53x | Reversal | -0.419% | Liquidity sweep / reversal |
| 2024-10-18 11:00 | Valid swing, away from level | n/a | 143.7% | 4.52x | Flat / fading | -0.097% | Position building in range |
| 2025-10-06 10:15 | Valid swing, away from level | n/a | 191.5% | 4.52x | Impulse / continuation | 0.302% | True breakout |
| 2025-05-22 09:15 | Valid swing, away from level | n/a | 195.9% | 4.52x | Reversal | 1.527% | Liquidity sweep / reversal |
| 2025-07-07 07:15 | Valid swing, away from level | n/a | 102.2% | 4.52x | Impulse / continuation | -0.094% | True breakout |
| 2025-12-15 09:15 | Valid swing, away from level | n/a | -676.2% | 4.52x | Reversal | -0.298% | Liquidity sweep / reversal |
| 2026-05-07 09:00 | Near Fib level | 38.2% | 37.7% | 4.52x | Flat / fading | -0.219% | Weak move without breakout |
| 2025-09-02 11:00 | Valid swing, away from level | n/a | 185.2% | 4.52x | Reversal | 0.078% | Liquidity sweep / reversal |
| 2024-12-23 11:00 | Valid swing, away from level | n/a | -92.0% | 4.52x | Flat / fading | -0.442% | Weak move without breakout |
| 2025-06-24 09:00 | Near Fib level | 50.0% | 48.4% | 4.51x | Impulse / continuation | -0.460% | True breakout |
| 2025-07-30 10:00 | Golden zone 50-61.8% | 50.0% | 53.0% | 4.51x | Impulse / continuation | 0.120% | True breakout |
| 2025-06-17 10:45 | Valid swing, away from level | 38.2% | 4.2% | 4.51x | Impulse / continuation | 0.315% | True breakout |
| 2025-10-11 17:45 | Valid swing, away from level | 38.2% | 13.4% | 4.51x | Impulse / continuation | 0.138% | True breakout |
| 2026-01-18 17:15 | Valid swing, away from level | 78.6% | 70.8% | 4.51x | Flat / fading | 0.006% | Weak move without breakout |
| 2026-05-07 13:00 | Valid swing, away from level | n/a | -6.8% | 4.51x | Flat / fading | -0.077% | Weak move without breakout |
| 2025-09-17 17:15 | Valid swing, away from level | n/a | -28.3% | 4.50x | Impulse / continuation | 0.335% | True breakout |
| 2026-07-23 07:00 | Near Fib level | 78.6% | 75.1% | 4.50x | Impulse / continuation | 0.205% | True breakout |
| 2025-06-27 10:30 | Near Fib level | 38.2% | 40.4% | 4.50x | Reversal | 0.025% | Liquidity sweep / reversal |
| 2025-02-12 19:00 | Valid swing, away from level | n/a | 128.5% | 4.50x | Impulse / continuation | 2.325% | True breakout |
| 2026-04-02 10:00 | Valid swing, away from level | 78.6% | 88.0% | 4.50x | Reversal | 0.328% | Liquidity sweep / reversal |
| 2026-01-28 16:30 | Golden zone 50-61.8% | 61.8% | 60.0% | 4.50x | Flat / fading | 0.036% | Weak move without breakout |
| 2025-11-01 23:15 | Valid swing, away from level | n/a | 101.8% | 4.50x | Impulse -> reversal | 0.578% | False breakout |
| 2026-01-29 18:15 | No confirmed swing | n/a | n/a | 4.49x | Flat / fading | -0.161% | Weak move without breakout |
| 2026-04-29 10:45 | Valid swing, away from level | n/a | 105.8% | 4.49x | Reversal | 0.716% | Liquidity sweep / reversal |
| 2026-04-21 17:15 | Valid swing, away from level | n/a | 162.0% | 4.49x | Flat / fading | 0.049% | Position building in range |
| 2026-06-19 23:15 | Valid swing, away from level | 78.6% | 93.7% | 4.49x | Impulse / continuation | -0.050% | True breakout |
| 2025-07-11 17:30 | Valid swing, away from level | n/a | 106.6% | 4.49x | Impulse / continuation | -0.348% | True breakout |
| 2026-09-20 18:45 | Valid swing, away from level | n/a | 110.0% | 4.49x | Reversal | 0.546% | Liquidity sweep / reversal |
| 2025-07-08 19:15 | Valid swing, away from level | 78.6% | 97.9% | 4.49x | Impulse / continuation | -0.565% | True breakout |
| 2025-02-12 18:00 | Valid swing, away from level | n/a | 144.7% | 4.48x | Impulse / continuation | 0.184% | True breakout |
| 2025-01-31 09:15 | Valid swing, away from level | n/a | -18.0% | 4.48x | Impulse / continuation | 0.267% | True breakout |
| 2025-08-29 10:45 | Valid swing, away from level | 61.8% | 67.5% | 4.48x | Flat / fading | -0.018% | Weak move without breakout |
| 2025-12-26 09:00 | Valid swing, away from level | n/a | -57.1% | 4.48x | Impulse / continuation | 0.813% | True breakout |
| 2025-09-16 09:00 | Valid swing, away from level | n/a | -33.3% | 4.48x | Impulse / continuation | 0.032% | True breakout |
| 2025-07-28 15:00 | Valid swing, away from level | n/a | 150.4% | 4.48x | Impulse / continuation | -1.182% | True breakout |
| 2025-05-20 10:45 | Valid swing, away from level | n/a | 106.8% | 4.47x | Flat / fading | 0.085% | Position building in range |
| 2026-06-04 14:00 | Near Fib level | 38.2% | 38.9% | 4.47x | Flat / fading | -0.277% | Position building in range |
| 2025-12-01 23:00 | Golden zone 50-61.8% | 61.8% | 56.3% | 4.47x | Reversal | 0.122% | Liquidity sweep / reversal |
| 2026-09-18 23:00 | Near Fib level | 78.6% | 79.0% | 4.47x | Flat / fading | 0.198% | Position building in range |
| 2025-11-06 07:00 | Near Fib level | 78.6% | 79.6% | 4.46x | Flat / fading | -0.007% | Position building in range |
| 2026-07-06 17:00 | Valid swing, away from level | n/a | 260.5% | 4.46x | Impulse / continuation | 0.854% | True breakout |
| 2026-08-19 07:00 | Valid swing, away from level | n/a | -15.3% | 4.46x | Impulse / continuation | -0.199% | True breakout |
| 2025-10-28 11:45 | Valid swing, away from level | n/a | -183.5% | 4.46x | Impulse / continuation | 0.329% | True breakout |
| 2025-02-20 10:00 | Valid swing, away from level | n/a | -5.8% | 4.45x | Reversal | -0.553% | Liquidity sweep / reversal |
| 2025-11-10 09:00 | Valid swing, away from level | n/a | -317.6% | 4.45x | Reversal | 0.415% | Liquidity sweep / reversal |
| 2024-10-08 10:30 | Valid swing, away from level | n/a | 108.9% | 4.45x | Flat / fading | -0.139% | Position building in range |
| 2025-01-31 11:45 | Valid swing, away from level | n/a | -24.6% | 4.45x | Flat / fading | 0.208% | Position building in range |
| 2026-09-14 07:15 | Valid swing, away from level | 38.2% | 1.1% | 4.45x | Reversal | 0.168% | Liquidity sweep / reversal |
| 2026-06-11 11:00 | Valid swing, away from level | 38.2% | 0.9% | 4.45x | Flat / fading | 0.107% | Weak move without breakout |
| 2025-10-24 13:45 | Valid swing, away from level | n/a | 145.2% | 4.44x | Flat / fading | 0.323% | Weak move without breakout |
| 2025-10-02 10:30 | Valid swing, away from level | n/a | 188.8% | 4.44x | Reversal | -0.516% | Liquidity sweep / reversal |
| 2026-07-20 09:45 | Golden zone 50-61.8% | 61.8% | 61.3% | 4.44x | Impulse -> reversal | -1.269% | False breakout |
| 2024-12-03 10:45 | Valid swing, away from level | n/a | 143.1% | 4.44x | Impulse / continuation | -0.504% | True breakout |
| 2026-07-05 10:15 | Valid swing, away from level | n/a | -3.6% | 4.44x | Flat / fading | -0.039% | Weak move without breakout |
| 2025-08-12 07:30 | Valid swing, away from level | n/a | 105.0% | 4.44x | Flat / fading | 0.200% | Position building in range |
| 2026-08-27 11:15 | Valid swing, away from level | n/a | -36.4% | 4.44x | Impulse / continuation | -0.024% | True breakout |
| 2025-03-31 08:30 | No confirmed swing | n/a | n/a | 4.44x | Flat / fading | 0.138% | Weak move without breakout |
| 2026-07-02 07:00 | Valid swing, away from level | 61.8% | 69.9% | 4.44x | Reversal | -0.044% | Liquidity sweep / reversal |
| 2025-07-14 09:30 | Valid swing, away from level | n/a | -47.0% | 4.43x | Impulse / continuation | 1.876% | True breakout |
| 2026-04-28 12:00 | Valid swing, away from level | n/a | 354.5% | 4.43x | Flat / fading | -0.013% | Position building in range |
| 2024-10-24 10:00 | Valid swing, away from level | n/a | 292.7% | 4.43x | Flat / fading | 0.362% | Weak move without breakout |
| 2024-11-27 12:30 | Golden zone 50-61.8% | 50.0% | 54.8% | 4.43x | Flat / fading | -0.451% | Weak move without breakout |
| 2025-11-27 10:30 | Golden zone 50-61.8% | 61.8% | 58.0% | 4.42x | Impulse / continuation | -0.187% | True breakout |
| 2024-09-27 10:15 | Valid swing, away from level | 38.2% | 11.9% | 4.42x | Impulse / continuation | 0.248% | True breakout |
| 2025-11-18 11:00 | Valid swing, away from level | n/a | -115.6% | 4.42x | Impulse / continuation | 1.157% | True breakout |
| 2025-07-25 13:45 | Near Fib level | 50.0% | 45.6% | 4.42x | Reversal | -0.296% | Liquidity sweep / reversal |
| 2025-05-08 09:45 | Valid swing, away from level | n/a | -14.8% | 4.41x | Flat / fading | -0.097% | Weak move without breakout |
| 2026-06-01 09:30 | Valid swing, away from level | n/a | -470.6% | 4.41x | Impulse / continuation | 0.040% | True breakout |
| 2025-04-23 19:30 | Valid swing, away from level | n/a | -11.9% | 4.41x | Impulse / continuation | 0.161% | True breakout |
| 2025-08-21 07:00 | Valid swing, away from level | n/a | -36.7% | 4.40x | Flat / fading | 0.047% | Weak move without breakout |
| 2025-06-13 19:15 | Valid swing, away from level | n/a | 128.4% | 4.40x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2026-04-20 10:15 | Valid swing, away from level | 78.6% | 96.3% | 4.39x | Flat / fading | 0.000% | Position building in range |
| 2026-05-28 16:00 | Valid swing, away from level | n/a | 145.4% | 4.39x | Flat / fading | 0.093% | Weak move without breakout |
| 2025-04-04 13:15 | Valid swing, away from level | n/a | 111.1% | 4.39x | Impulse / continuation | -0.699% | True breakout |
| 2026-08-25 07:00 | Valid swing, away from level | 38.2% | 12.5% | 4.39x | Impulse / continuation | 0.240% | True breakout |
| 2024-10-25 10:15 | Near Fib level | 61.8% | 65.5% | 4.39x | Reversal | 0.079% | Liquidity sweep / reversal |
| 2025-08-18 17:00 | Valid swing, away from level | n/a | -241.4% | 4.39x | Reversal | -0.231% | Liquidity sweep / reversal |
| 2025-01-30 12:00 | Near Fib level | 61.8% | 66.4% | 4.38x | Flat / fading | 0.059% | Position building in range |
| 2025-08-26 09:30 | Valid swing, away from level | n/a | -85.4% | 4.38x | Impulse / continuation | 0.154% | True breakout |
| 2025-04-28 08:45 | Valid swing, away from level | n/a | 145.3% | 4.38x | Flat / fading | 0.127% | Weak move without breakout |
| 2025-02-03 20:45 | Valid swing, away from level | n/a | -33.7% | 4.38x | Impulse / continuation | 0.238% | True breakout |
| 2024-09-25 10:15 | Valid swing, away from level | 38.2% | 0.0% | 4.38x | Reversal | -0.019% | Liquidity sweep / reversal |
| 2025-12-25 11:15 | Valid swing, away from level | n/a | -66.7% | 4.38x | Impulse / continuation | 0.278% | True breakout |
| 2025-01-27 10:15 | Valid swing, away from level | n/a | 163.0% | 4.38x | Reversal | -0.233% | Liquidity sweep / reversal |
| 2025-10-07 10:00 | Valid swing, away from level | 38.2% | 14.4% | 4.38x | Reversal | 0.622% | Liquidity sweep / reversal |
| 2026-02-03 07:45 | Valid swing, away from level | n/a | -100.0% | 4.38x | Reversal | 0.078% | Liquidity sweep / reversal |
| 2026-06-25 09:15 | Golden zone 50-61.8% | 50.0% | 55.0% | 4.37x | Impulse / continuation | 0.282% | True breakout |
| 2026-03-01 10:15 | Valid swing, away from level | 61.8% | 66.8% | 4.37x | Impulse / continuation | 0.145% | True breakout |
| 2024-11-27 10:45 | Valid swing, away from level | n/a | 128.3% | 4.37x | Reversal | 1.200% | Liquidity sweep / reversal |
| 2026-04-20 17:30 | Near Fib level | 78.6% | 81.2% | 4.37x | Impulse / continuation | 0.117% | True breakout |
| 2025-06-29 16:45 | Valid swing, away from level | 38.2% | 4.8% | 4.37x | Impulse / continuation | -0.055% | True breakout |
| 2025-11-11 07:00 | Valid swing, away from level | n/a | -16.0% | 4.37x | Reversal | -0.182% | Liquidity sweep / reversal |
| 2025-11-19 11:30 | Valid swing, away from level | n/a | -13.7% | 4.36x | Impulse / continuation | -0.453% | True breakout |
| 2025-11-28 09:30 | Valid swing, away from level | 78.6% | 73.5% | 4.36x | Impulse / continuation | 0.144% | True breakout |
| 2026-04-06 10:45 | Valid swing, away from level | n/a | 121.7% | 4.36x | Flat / fading | -0.069% | Position building in range |
| 2025-04-28 13:15 | Valid swing, away from level | n/a | 493.1% | 4.36x | Reversal | 1.296% | Liquidity sweep / reversal |
| 2025-12-22 22:00 | Valid swing, away from level | n/a | 175.9% | 4.36x | Flat / fading | 0.013% | Position building in range |
| 2025-04-11 09:30 | Valid swing, away from level | n/a | -14.9% | 4.36x | Flat / fading | -0.133% | Weak move without breakout |
| 2026-05-25 09:15 | Valid swing, away from level | n/a | -86.1% | 4.35x | Reversal | 0.059% | Liquidity sweep / reversal |
| 2025-12-01 10:15 | Valid swing, away from level | 78.6% | 98.5% | 4.35x | Reversal | 0.238% | Liquidity sweep / reversal |
| 2024-12-09 10:15 | Near Fib level | 38.2% | 39.5% | 4.35x | Flat / fading | -0.084% | Weak move without breakout |
| 2025-10-10 09:00 | Near Fib level | 61.8% | 64.7% | 4.35x | Reversal | -0.264% | Liquidity sweep / reversal |
| 2026-02-28 12:15 | Near Fib level | 78.6% | 76.7% | 4.35x | Impulse / continuation | 0.122% | True breakout |
| 2025-06-04 07:00 | Valid swing, away from level | n/a | -93.7% | 4.35x | Impulse / continuation | -0.288% | True breakout |
| 2025-02-28 20:30 | Valid swing, away from level | n/a | -167.7% | 4.34x | Reversal | -1.077% | Liquidity sweep / reversal |
| 2026-05-12 07:00 | Valid swing, away from level | n/a | -37.5% | 4.34x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2026-02-03 10:30 | Valid swing, away from level | n/a | -602.4% | 4.34x | Flat / fading | -0.266% | Weak move without breakout |
| 2026-05-05 11:00 | Near Fib level | 61.8% | 64.6% | 4.34x | Impulse -> reversal | 0.475% | False breakout |
| 2025-12-21 12:00 | Near Fib level | 61.8% | 66.7% | 4.34x | Impulse / continuation | -0.119% | True breakout |
| 2025-05-28 10:30 | Valid swing, away from level | n/a | -83.6% | 4.33x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2024-12-03 11:15 | Valid swing, away from level | n/a | 275.0% | 4.33x | Reversal | 0.449% | Liquidity sweep / reversal |
| 2026-04-06 12:15 | Valid swing, away from level | 78.6% | 98.8% | 4.33x | Flat / fading | 0.050% | Weak move without breakout |
| 2026-01-27 07:00 | Valid swing, away from level | 38.2% | 43.3% | 4.33x | Flat / fading | 0.018% | Position building in range |
| 2026-06-22 09:45 | Near Fib level | 78.6% | 81.9% | 4.33x | Impulse -> reversal | 0.873% | False breakout |
| 2025-08-04 10:30 | Valid swing, away from level | 38.2% | 2.9% | 4.33x | Flat / fading | 0.057% | Position building in range |
| 2026-04-17 10:30 | Valid swing, away from level | n/a | -214.4% | 4.33x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2026-03-16 10:30 | Near Fib level | 50.0% | 46.2% | 4.33x | Flat / fading | -0.012% | Position building in range |
| 2025-07-28 16:00 | Valid swing, away from level | n/a | 319.5% | 4.33x | Flat / fading | -0.144% | Weak move without breakout |
| 2026-03-25 12:00 | Valid swing, away from level | n/a | 107.2% | 4.33x | Flat / fading | 0.114% | Position building in range |
| 2025-10-13 09:00 | Valid swing, away from level | n/a | -25.9% | 4.32x | Reversal | 0.769% | Liquidity sweep / reversal |
| 2026-07-17 07:00 | Valid swing, away from level | n/a | 105.0% | 4.32x | Flat / fading | 0.388% | Weak move without breakout |
| 2025-08-28 07:00 | Valid swing, away from level | n/a | -27.8% | 4.32x | Flat / fading | -0.059% | Weak move without breakout |
| 2024-10-04 10:15 | Valid swing, away from level | 38.2% | 5.4% | 4.32x | Impulse / continuation | 0.542% | True breakout |
| 2025-03-25 12:15 | Near Fib level | 50.0% | 46.3% | 4.32x | Impulse / continuation | -0.401% | True breakout |
| 2025-07-03 10:30 | Valid swing, away from level | 78.6% | 92.0% | 4.32x | Impulse / continuation | 0.337% | True breakout |
| 2024-10-01 11:45 | Valid swing, away from level | n/a | 290.0% | 4.31x | Flat / fading | 0.039% | Weak move without breakout |
| 2026-08-29 14:30 | Golden zone 50-61.8% | 50.0% | 54.3% | 4.31x | Flat / fading | 0.008% | Position building in range |
| 2024-10-29 10:15 | Valid swing, away from level | 78.6% | 85.6% | 4.31x | Reversal | -0.577% | Liquidity sweep / reversal |
| 2025-11-05 09:00 | Near Fib level | 61.8% | 64.3% | 4.31x | Reversal | -0.355% | Liquidity sweep / reversal |
| 2025-10-07 11:15 | Valid swing, away from level | n/a | -45.6% | 4.31x | Flat / fading | -0.523% | Position building in range |
| 2025-11-17 10:30 | Valid swing, away from level | n/a | -51.3% | 4.30x | Impulse / continuation | 0.082% | True breakout |
| 2025-09-03 19:15 | Valid swing, away from level | n/a | -78.3% | 4.30x | Flat / fading | -0.036% | Weak move without breakout |
| 2025-11-14 10:15 | Valid swing, away from level | n/a | -25.4% | 4.30x | Reversal | -0.796% | Liquidity sweep / reversal |
| 2026-04-03 07:15 | Valid swing, away from level | n/a | -5.8% | 4.30x | Flat / fading | -0.061% | Weak move without breakout |
| 2025-12-09 22:15 | Valid swing, away from level | n/a | -53.5% | 4.30x | Reversal | -0.499% | Liquidity sweep / reversal |
| 2024-11-19 10:00 | Valid swing, away from level | 38.2% | 17.2% | 4.29x | Flat / fading | -0.060% | Position building in range |
| 2026-08-23 10:45 | Valid swing, away from level | 78.6% | 98.3% | 4.29x | Reversal | 0.032% | Liquidity sweep / reversal |
| 2026-05-22 11:15 | Valid swing, away from level | n/a | -40.9% | 4.29x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2026-08-18 07:00 | Valid swing, away from level | 38.2% | 19.7% | 4.29x | Flat / fading | -0.047% | Position building in range |
| 2026-09-11 11:00 | Near Fib level | 78.6% | 82.8% | 4.29x | Flat / fading | -0.238% | Weak move without breakout |
| 2026-03-23 13:30 | Valid swing, away from level | n/a | 198.4% | 4.29x | Impulse -> reversal | 0.424% | False breakout |
| 2025-02-19 17:30 | Valid swing, away from level | n/a | -76.3% | 4.28x | Flat / fading | -0.441% | Weak move without breakout |
| 2025-11-18 11:15 | Valid swing, away from level | n/a | -200.7% | 4.28x | Impulse / continuation | 0.248% | True breakout |
| 2026-02-17 11:00 | Near Fib level | 78.6% | 77.7% | 4.28x | Reversal | 0.628% | Liquidity sweep / reversal |
| 2025-02-10 16:45 | Valid swing, away from level | n/a | -9.3% | 4.28x | Flat / fading | -0.013% | Weak move without breakout |
| 2026-05-15 17:30 | Valid swing, away from level | n/a | 149.7% | 4.28x | Impulse / continuation | -0.624% | True breakout |
| 2025-08-12 10:00 | Valid swing, away from level | 38.2% | 32.4% | 4.28x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2025-04-28 10:15 | Valid swing, away from level | n/a | 246.6% | 4.28x | Reversal | 0.133% | Liquidity sweep / reversal |
| 2025-04-21 07:00 | Valid swing, away from level | 38.2% | 4.6% | 4.28x | Flat / fading | 0.095% | Position building in range |
| 2025-01-06 10:30 | Valid swing, away from level | n/a | 214.7% | 4.28x | Impulse / continuation | 0.457% | True breakout |
| 2026-07-30 11:00 | Valid swing, away from level | n/a | -21.7% | 4.27x | Flat / fading | -0.237% | Position building in range |
| 2025-10-03 19:15 | Valid swing, away from level | n/a | 169.0% | 4.27x | Impulse / continuation | -0.341% | True breakout |
| 2025-05-04 12:00 | Valid swing, away from level | n/a | -101.4% | 4.27x | Flat / fading | 0.013% | Weak move without breakout |
| 2025-10-02 10:15 | Valid swing, away from level | n/a | 211.2% | 4.27x | Reversal | -0.239% | Liquidity sweep / reversal |
| 2026-03-30 09:00 | Valid swing, away from level | n/a | -746.2% | 4.27x | Impulse / continuation | -0.382% | True breakout |
| 2025-06-23 09:15 | Valid swing, away from level | n/a | 123.9% | 4.27x | Impulse / continuation | -0.484% | True breakout |
| 2025-11-30 11:30 | Valid swing, away from level | n/a | -614.3% | 4.27x | Flat / fading | -0.019% | Position building in range |
| 2026-03-06 12:45 | Valid swing, away from level | n/a | 145.6% | 4.27x | Impulse / continuation | -0.265% | True breakout |
| 2025-10-01 07:45 | Valid swing, away from level | 38.2% | 17.8% | 4.27x | Reversal | -0.065% | Liquidity sweep / reversal |
| 2024-10-16 10:45 | Valid swing, away from level | 38.2% | 14.5% | 4.27x | Reversal | -0.190% | Liquidity sweep / reversal |
| 2025-11-21 17:45 | Near Fib level | 38.2% | 33.3% | 4.26x | Flat / fading | 0.090% | Position building in range |
| 2026-02-12 12:30 | Valid swing, away from level | n/a | -65.1% | 4.26x | Impulse / continuation | 0.078% | True breakout |
| 2025-12-30 07:00 | Near Fib level | 50.0% | 49.9% | 4.26x | Flat / fading | -0.097% | Position building in range |
| 2025-07-18 10:15 | Valid swing, away from level | n/a | -28.6% | 4.26x | Reversal | 0.586% | Liquidity sweep / reversal |
| 2025-06-13 07:00 | Valid swing, away from level | 38.2% | 21.1% | 4.25x | Reversal | -0.031% | Liquidity sweep / reversal |
| 2024-10-15 10:15 | Valid swing, away from level | 38.2% | 17.5% | 4.25x | Reversal | 1.113% | Liquidity sweep / reversal |
| 2026-09-23 18:30 | Valid swing, away from level | 38.2% | 13.1% | 4.25x | Flat / fading | -0.217% | Weak move without breakout |
| 2025-09-16 11:30 | Valid swing, away from level | 78.6% | 86.8% | 4.25x | Impulse / continuation | -0.608% | True breakout |
| 2024-11-08 10:45 | Valid swing, away from level | n/a | -593.9% | 4.25x | Reversal | -0.939% | Liquidity sweep / reversal |
| 2024-10-01 10:45 | Valid swing, away from level | n/a | 230.0% | 4.25x | Impulse / continuation | -0.692% | True breakout |
| 2025-08-07 11:15 | Valid swing, away from level | n/a | -19.3% | 4.25x | Reversal | 0.940% | Liquidity sweep / reversal |
| 2024-10-03 11:00 | Near Fib level | 61.8% | 63.7% | 4.25x | Flat / fading | 0.179% | Weak move without breakout |
| 2026-03-04 17:15 | Valid swing, away from level | n/a | 143.2% | 4.25x | Impulse / continuation | 0.024% | True breakout |
| 2025-08-21 08:45 | Valid swing, away from level | n/a | -102.5% | 4.24x | Reversal | -0.310% | Liquidity sweep / reversal |
| 2025-06-25 11:00 | Valid swing, away from level | n/a | -43.1% | 4.24x | Impulse / continuation | -0.143% | True breakout |
| 2025-01-14 10:00 | Valid swing, away from level | 78.6% | 84.6% | 4.24x | Impulse / continuation | -0.201% | True breakout |
| 2025-06-06 07:30 | Valid swing, away from level | 38.2% | 20.8% | 4.24x | Flat / fading | -0.036% | Position building in range |
| 2026-06-24 08:15 | Valid swing, away from level | n/a | -4.4% | 4.24x | Reversal | -0.940% | Liquidity sweep / reversal |
| 2026-05-24 16:45 | Valid swing, away from level | 38.2% | 22.2% | 4.23x | Flat / fading | 0.013% | Weak move without breakout |
| 2026-01-20 07:00 | Valid swing, away from level | 38.2% | 16.4% | 4.23x | Flat / fading | 0.085% | Weak move without breakout |
| 2025-04-18 16:00 | Valid swing, away from level | n/a | 123.0% | 4.23x | Flat / fading | 0.203% | Position building in range |
| 2025-09-12 10:45 | Valid swing, away from level | n/a | 140.2% | 4.23x | Reversal | 0.326% | Liquidity sweep / reversal |
| 2025-03-11 21:45 | Valid swing, away from level | n/a | 129.0% | 4.23x | Reversal | 0.235% | Liquidity sweep / reversal |
| 2026-03-15 18:00 | Valid swing, away from level | 38.2% | 22.2% | 4.23x | Reversal | 0.307% | Liquidity sweep / reversal |
| 2026-06-07 16:15 | Near Fib level | 38.2% | 39.1% | 4.23x | Impulse / continuation | 0.034% | True breakout |
| 2025-02-17 10:00 | Valid swing, away from level | n/a | -368.4% | 4.22x | Reversal | -0.214% | Liquidity sweep / reversal |
| 2026-05-28 07:00 | Valid swing, away from level | n/a | -37.7% | 4.22x | Impulse / continuation | 0.000% | True breakout |
| 2025-01-27 23:00 | Valid swing, away from level | n/a | 450.6% | 4.22x | Flat / fading | -0.178% | Position building in range |
| 2025-09-22 14:45 | Golden zone 50-61.8% | 50.0% | 52.6% | 4.22x | Flat / fading | -0.316% | Position building in range |
| 2025-12-12 21:45 | Valid swing, away from level | n/a | 301.0% | 4.22x | Flat / fading | 0.075% | Position building in range |
| 2026-03-09 18:15 | Valid swing, away from level | 38.2% | 2.2% | 4.22x | Impulse / continuation | 0.201% | True breakout |
| 2025-05-19 09:00 | Valid swing, away from level | n/a | 378.6% | 4.22x | Impulse / continuation | 0.225% | True breakout |
| 2025-04-13 16:45 | Valid swing, away from level | n/a | -16.2% | 4.21x | Flat / fading | 0.038% | Weak move without breakout |
| 2025-07-28 08:00 | Valid swing, away from level | n/a | -90.2% | 4.21x | Impulse / continuation | 0.259% | True breakout |
| 2025-07-03 10:15 | Valid swing, away from level | 78.6% | 98.0% | 4.21x | Reversal | 0.362% | Liquidity sweep / reversal |
| 2024-10-22 12:15 | Golden zone 50-61.8% | 61.8% | 56.3% | 4.21x | Reversal | -0.290% | Liquidity sweep / reversal |
| 2026-09-05 10:00 | Valid swing, away from level | n/a | -63.1% | 4.21x | Flat / fading | -0.008% | Position building in range |
| 2025-02-28 11:15 | Valid swing, away from level | n/a | 113.3% | 4.21x | Flat / fading | 0.231% | Weak move without breakout |
| 2024-09-25 11:45 | Valid swing, away from level | n/a | -65.9% | 4.21x | Impulse / continuation | 2.919% | True breakout |
| 2026-04-04 14:45 | Near Fib level | 38.2% | 34.7% | 4.20x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-05-19 11:45 | Valid swing, away from level | n/a | -53.5% | 4.20x | Reversal | -0.266% | Liquidity sweep / reversal |
| 2026-08-08 17:15 | Valid swing, away from level | n/a | -63.0% | 4.20x | Reversal | 0.151% | Liquidity sweep / reversal |
| 2026-08-24 17:45 | Valid swing, away from level | 61.8% | 66.9% | 4.20x | Impulse / continuation | -0.594% | True breakout |
| 2025-08-01 07:30 | Valid swing, away from level | n/a | -66.1% | 4.20x | Impulse / continuation | -0.050% | True breakout |
| 2025-03-03 09:00 | Valid swing, away from level | n/a | 291.8% | 4.20x | Reversal | -0.167% | Liquidity sweep / reversal |
| 2024-12-20 10:30 | Near Fib level | 38.2% | 38.5% | 4.20x | Impulse / continuation | 0.220% | True breakout |
| 2025-04-23 10:15 | Valid swing, away from level | n/a | 148.5% | 4.20x | Impulse / continuation | -0.231% | True breakout |
| 2025-03-14 16:15 | Valid swing, away from level | n/a | -89.0% | 4.20x | Impulse / continuation | -0.023% | True breakout |
| 2024-11-14 10:00 | Golden zone 50-61.8% | 50.0% | 55.1% | 4.20x | Flat / fading | 0.024% | Position building in range |
| 2026-02-25 18:15 | Golden zone 50-61.8% | 50.0% | 50.0% | 4.20x | Flat / fading | -0.103% | Weak move without breakout |
| 2025-06-09 10:45 | Valid swing, away from level | n/a | 670.3% | 4.20x | Flat / fading | -0.120% | Weak move without breakout |
| 2025-06-09 10:00 | Valid swing, away from level | n/a | 227.0% | 4.20x | Reversal | -1.165% | Liquidity sweep / reversal |
| 2025-09-11 10:15 | Valid swing, away from level | 78.6% | 85.4% | 4.19x | Impulse / continuation | -0.607% | True breakout |
| 2026-03-30 07:15 | Valid swing, away from level | n/a | -1000.0% | 4.19x | Flat / fading | 0.031% | Position building in range |
| 2025-11-25 11:30 | Valid swing, away from level | 78.6% | 94.4% | 4.19x | Impulse / continuation | -0.241% | True breakout |
| 2025-09-26 10:15 | Valid swing, away from level | 61.8% | 68.3% | 4.19x | Flat / fading | 0.013% | Weak move without breakout |
| 2026-07-13 09:45 | Valid swing, away from level | n/a | 101.4% | 4.19x | Reversal | 2.803% | Liquidity sweep / reversal |
| 2026-09-11 13:15 | Valid swing, away from level | n/a | -1.5% | 4.19x | Reversal | -0.601% | Liquidity sweep / reversal |
| 2025-01-16 10:00 | Valid swing, away from level | 38.2% | 6.8% | 4.19x | Impulse / continuation | -0.268% | True breakout |
| 2025-09-11 15:30 | Valid swing, away from level | n/a | 155.9% | 4.18x | Flat / fading | -0.238% | Weak move without breakout |
| 2026-05-13 21:00 | Valid swing, away from level | n/a | -75.2% | 4.18x | Flat / fading | -0.282% | Weak move without breakout |
| 2025-11-13 10:00 | Golden zone 50-61.8% | 61.8% | 57.0% | 4.18x | Reversal | 0.271% | Liquidity sweep / reversal |
| 2026-01-18 10:15 | Valid swing, away from level | 78.6% | 92.3% | 4.18x | Flat / fading | 0.025% | Weak move without breakout |
| 2025-11-28 09:45 | Near Fib level | 78.6% | 73.9% | 4.18x | Impulse / continuation | 0.124% | True breakout |
| 2026-01-28 09:45 | Valid swing, away from level | n/a | -38.1% | 4.18x | Reversal | -0.269% | Liquidity sweep / reversal |
| 2025-07-11 11:30 | Valid swing, away from level | n/a | 318.9% | 4.18x | Impulse / continuation | -0.258% | True breakout |
| 2025-09-19 17:45 | Valid swing, away from level | n/a | 124.5% | 4.18x | Impulse / continuation | -0.399% | True breakout |
| 2025-05-22 17:45 | Valid swing, away from level | n/a | -94.4% | 4.18x | Reversal | -0.497% | Liquidity sweep / reversal |
| 2025-11-25 09:15 | Valid swing, away from level | 38.2% | 43.3% | 4.18x | Flat / fading | 0.032% | Weak move without breakout |
| 2026-09-01 10:15 | Valid swing, away from level | n/a | -23.2% | 4.18x | Impulse / continuation | 0.469% | True breakout |
| 2025-09-08 08:30 | Valid swing, away from level | n/a | -295.7% | 4.18x | Flat / fading | -0.012% | Weak move without breakout |
| 2026-07-03 08:30 | Valid swing, away from level | n/a | 118.4% | 4.18x | Flat / fading | 0.743% | Weak move without breakout |
| 2026-08-19 10:15 | Valid swing, away from level | n/a | 151.9% | 4.18x | Impulse / continuation | -0.464% | True breakout |
| 2026-08-23 10:15 | Valid swing, away from level | n/a | 123.7% | 4.17x | Flat / fading | 0.024% | Weak move without breakout |
| 2025-11-27 10:00 | Valid swing, away from level | 38.2% | 16.0% | 4.17x | Impulse / continuation | -0.161% | True breakout |
| 2024-11-18 17:00 | Valid swing, away from level | n/a | -14.9% | 4.17x | Impulse / continuation | 0.680% | True breakout |
| 2025-06-09 07:15 | Valid swing, away from level | n/a | 136.8% | 4.17x | Flat / fading | -0.068% | Weak move without breakout |
| 2026-02-08 10:00 | Valid swing, away from level | n/a | -32.4% | 4.17x | Flat / fading | -0.073% | Weak move without breakout |
| 2024-12-23 11:15 | Valid swing, away from level | n/a | -98.6% | 4.17x | Reversal | -0.479% | Liquidity sweep / reversal |
| 2025-09-05 23:30 | Valid swing, away from level | 78.6% | 88.2% | 4.17x | Impulse / continuation | -0.060% | True breakout |
| 2025-06-11 09:45 | Valid swing, away from level | 38.2% | 10.8% | 4.17x | Impulse / continuation | 0.468% | True breakout |
| 2026-09-17 13:15 | Valid swing, away from level | n/a | 199.2% | 4.17x | Impulse / continuation | -0.238% | True breakout |
| 2025-07-11 10:00 | Valid swing, away from level | n/a | 141.5% | 4.17x | Reversal | -0.194% | Liquidity sweep / reversal |
| 2024-12-12 10:30 | Valid swing, away from level | 38.2% | 2.7% | 4.17x | Impulse / continuation | 0.136% | True breakout |
| 2025-12-12 11:45 | Valid swing, away from level | n/a | 155.8% | 4.16x | Flat / fading | 0.074% | Position building in range |
| 2025-04-21 10:15 | Valid swing, away from level | n/a | -12.1% | 4.16x | Reversal | 0.478% | Liquidity sweep / reversal |
| 2025-09-04 09:45 | Valid swing, away from level | n/a | -7.5% | 4.16x | Impulse / continuation | 0.168% | True breakout |
| 2026-01-25 18:45 | Valid swing, away from level | 38.2% | 29.4% | 4.16x | Impulse / continuation | -0.036% | True breakout |
| 2026-07-08 17:15 | Valid swing, away from level | 38.2% | 20.7% | 4.16x | Impulse / continuation | 0.884% | True breakout |
| 2025-04-12 18:45 | Valid swing, away from level | 38.2% | 1.6% | 4.15x | Impulse / continuation | -0.075% | True breakout |
| 2025-08-18 15:30 | Valid swing, away from level | n/a | -17.8% | 4.15x | Impulse / continuation | 0.772% | True breakout |
| 2026-01-09 14:00 | Valid swing, away from level | 38.2% | 19.1% | 4.15x | Impulse / continuation | 0.031% | True breakout |
| 2025-06-24 09:45 | Valid swing, away from level | 61.8% | 68.6% | 4.15x | Impulse / continuation | -0.044% | True breakout |
| 2026-03-13 10:15 | Valid swing, away from level | n/a | -263.4% | 4.15x | Reversal | 0.264% | Liquidity sweep / reversal |
| 2026-06-10 09:15 | Valid swing, away from level | 38.2% | 21.9% | 4.15x | Impulse / continuation | -0.243% | True breakout |
| 2025-07-04 07:00 | Valid swing, away from level | n/a | 280.6% | 4.14x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2025-06-30 11:15 | Valid swing, away from level | n/a | 229.5% | 4.14x | Flat / fading | 0.172% | Weak move without breakout |
| 2025-11-06 11:30 | Valid swing, away from level | n/a | 124.2% | 4.14x | Impulse / continuation | 0.034% | True breakout |
| 2026-03-23 07:15 | Golden zone 50-61.8% | 61.8% | 57.9% | 4.14x | Impulse / continuation | 0.384% | True breakout |
| 2026-05-25 07:15 | Valid swing, away from level | n/a | -61.1% | 4.13x | Reversal | 0.085% | Liquidity sweep / reversal |
| 2026-05-20 11:15 | Valid swing, away from level | n/a | 173.3% | 4.13x | Impulse / continuation | -0.390% | True breakout |
| 2025-10-27 23:30 | Near Fib level | 78.6% | 74.9% | 4.13x | Flat / fading | 0.106% | Weak move without breakout |
| 2024-10-11 10:30 | Near Fib level | 38.2% | 42.4% | 4.13x | Flat / fading | 0.078% | Position building in range |
| 2025-03-03 08:15 | Valid swing, away from level | n/a | 266.3% | 4.13x | Reversal | 0.173% | Liquidity sweep / reversal |
| 2026-07-13 07:15 | Valid swing, away from level | n/a | -26.8% | 4.13x | Flat / fading | -0.088% | Position building in range |
| 2026-02-25 10:00 | Valid swing, away from level | 38.2% | 2.6% | 4.13x | Impulse / continuation | 0.120% | True breakout |
| 2026-02-17 07:00 | Valid swing, away from level | n/a | -25.0% | 4.13x | Reversal | -0.441% | Liquidity sweep / reversal |
| 2026-07-10 09:15 | Valid swing, away from level | 61.8% | 67.5% | 4.12x | Impulse -> reversal | -0.644% | False breakout |
| 2026-05-18 10:15 | Valid swing, away from level | n/a | 315.0% | 4.12x | Flat / fading | 0.196% | Weak move without breakout |
| 2025-03-13 10:00 | Valid swing, away from level | n/a | 209.6% | 4.12x | Reversal | -0.843% | Liquidity sweep / reversal |
| 2024-12-06 10:30 | Valid swing, away from level | 38.2% | 5.5% | 4.12x | Flat / fading | -0.051% | Weak move without breakout |
| 2026-02-16 08:30 | Valid swing, away from level | n/a | -336.7% | 4.12x | Reversal | 0.018% | Liquidity sweep / reversal |
| 2026-01-19 10:00 | Valid swing, away from level | 38.2% | 16.7% | 4.12x | Impulse / continuation | 0.196% | True breakout |
| 2025-11-11 14:45 | Valid swing, away from level | 38.2% | 14.0% | 4.11x | Flat / fading | 0.081% | Position building in range |
| 2025-02-21 13:30 | Valid swing, away from level | n/a | 102.0% | 4.11x | Impulse / continuation | -0.653% | True breakout |
| 2026-09-07 17:45 | Valid swing, away from level | n/a | -52.1% | 4.11x | Flat / fading | -0.083% | Weak move without breakout |
| 2026-02-11 15:30 | Valid swing, away from level | n/a | -24.4% | 4.11x | Impulse / continuation | 0.048% | True breakout |
| 2026-02-20 07:00 | Valid swing, away from level | 78.6% | 70.8% | 4.11x | Flat / fading | 0.091% | Position building in range |
| 2025-11-13 21:00 | Golden zone 50-61.8% | 61.8% | 59.2% | 4.10x | Reversal | -0.095% | Liquidity sweep / reversal |
| 2026-05-22 11:00 | Valid swing, away from level | n/a | -10.2% | 4.10x | Flat / fading | 0.019% | Weak move without breakout |
| 2025-01-31 11:15 | Valid swing, away from level | n/a | -231.1% | 4.10x | Reversal | -0.491% | Liquidity sweep / reversal |
| 2026-07-01 12:15 | Valid swing, away from level | 38.2% | 0.0% | 4.10x | Flat / fading | -0.342% | Position building in range |
| 2025-04-03 07:00 | Valid swing, away from level | n/a | -20.5% | 4.10x | Flat / fading | -0.102% | Weak move without breakout |
| 2025-10-30 12:15 | Valid swing, away from level | n/a | -262.8% | 4.09x | Flat / fading | -0.309% | Position building in range |
| 2026-03-10 19:45 | Valid swing, away from level | n/a | 118.5% | 4.09x | Flat / fading | 0.213% | Weak move without breakout |
| 2026-03-31 11:45 | Valid swing, away from level | n/a | -189.1% | 4.09x | Impulse / continuation | 0.714% | True breakout |
| 2025-11-24 10:00 | Near Fib level | 38.2% | 35.8% | 4.09x | Impulse / continuation | -0.282% | True breakout |
| 2026-07-08 09:00 | Valid swing, away from level | 38.2% | 4.8% | 4.09x | Impulse / continuation | -0.616% | True breakout |
| 2024-10-07 11:00 | Valid swing, away from level | 78.6% | 97.9% | 4.08x | Reversal | -0.314% | Liquidity sweep / reversal |
| 2025-09-15 11:15 | Valid swing, away from level | n/a | 338.0% | 4.08x | Flat / fading | -0.044% | Position building in range |
| 2026-02-20 10:30 | Valid swing, away from level | n/a | -31.2% | 4.08x | Flat / fading | -0.085% | Weak move without breakout |
| 2026-05-21 10:15 | Valid swing, away from level | n/a | 266.7% | 4.08x | Flat / fading | 0.097% | Weak move without breakout |
| 2026-07-07 11:00 | Valid swing, away from level | n/a | 184.3% | 4.08x | Impulse / continuation | 2.264% | True breakout |
| 2026-05-20 10:00 | Valid swing, away from level | n/a | 132.1% | 4.08x | Flat / fading | -0.115% | Position building in range |
| 2026-04-06 09:15 | Valid swing, away from level | 78.6% | 100.0% | 4.08x | Flat / fading | -0.050% | Position building in range |
| 2026-09-21 17:15 | Valid swing, away from level | 38.2% | 31.7% | 4.08x | Impulse / continuation | 0.566% | True breakout |
| 2025-02-17 07:15 | Valid swing, away from level | n/a | -182.5% | 4.08x | Reversal | 0.287% | Liquidity sweep / reversal |
| 2024-12-20 13:45 | Valid swing, away from level | n/a | -1249.3% | 4.08x | Reversal | 0.447% | Liquidity sweep / reversal |
| 2026-05-07 12:30 | Valid swing, away from level | 38.2% | 14.8% | 4.08x | Impulse / continuation | 0.065% | True breakout |
| 2026-01-22 17:15 | Valid swing, away from level | n/a | 179.6% | 4.08x | Reversal | 0.440% | Liquidity sweep / reversal |
| 2025-09-28 10:00 | Valid swing, away from level | 38.2% | 9.1% | 4.08x | Flat / fading | -0.013% | Position building in range |
| 2025-04-30 09:00 | Valid swing, away from level | n/a | 119.5% | 4.07x | Reversal | -0.251% | Liquidity sweep / reversal |
| 2026-02-13 10:45 | Valid swing, away from level | 78.6% | 100.0% | 4.07x | Flat / fading | 0.018% | Weak move without breakout |
| 2026-05-20 20:30 | Near Fib level | 78.6% | 77.1% | 4.07x | Flat / fading | -0.032% | Position building in range |
| 2025-10-27 09:00 | Valid swing, away from level | n/a | 127.2% | 4.07x | Impulse / continuation | -0.167% | True breakout |
| 2025-11-15 16:00 | Golden zone 50-61.8% | 50.0% | 55.4% | 4.07x | Flat / fading | -0.021% | Weak move without breakout |
| 2025-09-08 07:45 | Valid swing, away from level | n/a | -108.7% | 4.07x | Reversal | 0.150% | Liquidity sweep / reversal |
| 2025-11-28 12:45 | Golden zone 50-61.8% | 61.8% | 59.9% | 4.07x | Flat / fading | 0.039% | Position building in range |
| 2026-04-23 07:00 | Valid swing, away from level | 38.2% | 0.9% | 4.07x | Flat / fading | 0.202% | Position building in range |
| 2026-02-12 11:00 | Valid swing, away from level | n/a | 118.6% | 4.06x | Reversal | 0.168% | Liquidity sweep / reversal |
| 2026-06-10 17:45 | Valid swing, away from level | n/a | -37.1% | 4.06x | Flat / fading | -0.633% | Position building in range |
| 2025-10-02 07:45 | Valid swing, away from level | 78.6% | 99.3% | 4.06x | Flat / fading | -0.283% | Position building in range |
| 2026-06-08 15:30 | Valid swing, away from level | n/a | 377.3% | 4.06x | Impulse / continuation | -0.343% | True breakout |
| 2025-08-22 11:30 | Golden zone 50-61.8% | 50.0% | 51.9% | 4.06x | Flat / fading | 0.059% | Position building in range |
| 2025-10-09 11:15 | Valid swing, away from level | n/a | 260.2% | 4.06x | Impulse -> reversal | 3.179% | False breakout |
| 2025-09-29 10:15 | Valid swing, away from level | n/a | -252.2% | 4.06x | Reversal | 0.537% | Liquidity sweep / reversal |
| 2026-07-21 09:00 | Valid swing, away from level | n/a | -4.3% | 4.05x | Reversal | -0.880% | Liquidity sweep / reversal |
| 2026-05-12 09:00 | Valid swing, away from level | 38.2% | 0.0% | 4.05x | Reversal | 0.225% | Liquidity sweep / reversal |
| 2026-06-08 15:15 | Valid swing, away from level | n/a | 334.0% | 4.05x | Impulse / continuation | -0.944% | True breakout |
| 2026-06-07 16:45 | Valid swing, away from level | n/a | -4.3% | 4.05x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-02-04 07:00 | Valid swing, away from level | 61.8% | 69.5% | 4.05x | Reversal | 0.125% | Liquidity sweep / reversal |
| 2024-10-22 11:00 | Valid swing, away from level | n/a | 101.6% | 4.05x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-05-22 08:00 | Valid swing, away from level | n/a | 142.5% | 4.05x | Impulse / continuation | -0.375% | True breakout |
| 2026-08-18 12:15 | Valid swing, away from level | n/a | -105.2% | 4.05x | Impulse / continuation | -0.239% | True breakout |
| 2026-06-03 15:30 | Valid swing, away from level | n/a | 113.2% | 4.05x | Flat / fading | -0.092% | Weak move without breakout |
| 2025-02-05 10:15 | Valid swing, away from level | 38.2% | 18.6% | 4.05x | Reversal | -0.497% | Liquidity sweep / reversal |
| 2024-12-13 11:30 | Valid swing, away from level | n/a | 150.8% | 4.05x | Impulse / continuation | -0.279% | True breakout |
| 2025-08-16 10:00 | Valid swing, away from level | n/a | 366.9% | 4.05x | Reversal | 0.309% | Liquidity sweep / reversal |
| 2024-12-16 11:00 | Valid swing, away from level | n/a | 129.3% | 4.04x | Impulse / continuation | -0.388% | True breakout |
| 2025-09-04 15:15 | Valid swing, away from level | 38.2% | 25.6% | 4.04x | Impulse / continuation | 0.078% | True breakout |
| 2025-04-17 17:15 | Valid swing, away from level | n/a | 121.2% | 4.04x | Impulse / continuation | 0.417% | True breakout |
| 2025-07-01 11:00 | Valid swing, away from level | n/a | -55.0% | 4.04x | Reversal | -0.238% | Liquidity sweep / reversal |
| 2026-03-10 20:00 | Valid swing, away from level | n/a | 116.1% | 4.03x | Flat / fading | 0.284% | Weak move without breakout |
| 2025-09-17 10:00 | Valid swing, away from level | n/a | 138.3% | 4.03x | Flat / fading | 0.032% | Weak move without breakout |
| 2026-08-24 10:15 | Valid swing, away from level | n/a | 546.4% | 4.03x | Reversal | -0.448% | Liquidity sweep / reversal |
| 2026-04-26 15:30 | Valid swing, away from level | n/a | 193.3% | 4.02x | Flat / fading | 0.019% | Position building in range |
| 2026-09-10 18:00 | Valid swing, away from level | n/a | -82.9% | 4.02x | Flat / fading | -0.030% | Weak move without breakout |
| 2026-05-25 16:45 | Valid swing, away from level | n/a | 152.3% | 4.02x | Impulse / continuation | -0.118% | True breakout |
| 2024-11-18 17:30 | Valid swing, away from level | n/a | -39.4% | 4.02x | Impulse / continuation | 0.652% | True breakout |
| 2026-01-23 21:15 | Valid swing, away from level | n/a | -78.8% | 4.02x | Reversal | -0.150% | Liquidity sweep / reversal |
| 2025-06-30 10:15 | Valid swing, away from level | 38.2% | 27.9% | 4.02x | Impulse / continuation | -0.750% | True breakout |
| 2026-08-26 07:00 | Golden zone 50-61.8% | 61.8% | 60.8% | 4.02x | Impulse / continuation | -0.261% | True breakout |
| 2025-11-25 10:15 | Valid swing, away from level | 38.2% | 0.0% | 4.02x | Reversal | -0.240% | Liquidity sweep / reversal |
| 2024-12-06 10:00 | Valid swing, away from level | 38.2% | 12.4% | 4.02x | Impulse / continuation | 0.262% | True breakout |
| 2026-09-16 07:00 | Valid swing, away from level | n/a | 105.4% | 4.02x | Reversal | 0.213% | Liquidity sweep / reversal |
| 2025-09-29 18:00 | Valid swing, away from level | n/a | 120.3% | 4.02x | Impulse / continuation | -0.560% | True breakout |
| 2025-09-22 10:15 | Valid swing, away from level | n/a | 113.3% | 4.01x | Reversal | 0.046% | Liquidity sweep / reversal |
| 2025-01-16 12:00 | Valid swing, away from level | n/a | -2.0% | 4.01x | Flat / fading | -0.133% | Weak move without breakout |
| 2026-01-21 07:00 | Golden zone 50-61.8% | 61.8% | 61.4% | 4.01x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-09-06 10:45 | Golden zone 50-61.8% | 61.8% | 61.1% | 4.01x | Impulse / continuation | -0.068% | True breakout |
| 2025-12-24 11:00 | Valid swing, away from level | n/a | 162.0% | 4.01x | Impulse / continuation | -0.019% | True breakout |
| 2025-03-11 11:00 | Valid swing, away from level | 38.2% | 6.2% | 4.01x | Impulse / continuation | -0.151% | True breakout |
| 2025-07-21 09:15 | Valid swing, away from level | n/a | -152.6% | 4.01x | Flat / fading | -0.125% | Weak move without breakout |
| 2026-06-04 16:45 | Valid swing, away from level | n/a | 125.6% | 4.01x | Impulse / continuation | -0.259% | True breakout |
| 2026-03-11 12:45 | Golden zone 50-61.8% | 61.8% | 58.7% | 4.00x | Flat / fading | -0.041% | Weak move without breakout |
| 2026-07-08 18:15 | Valid swing, away from level | n/a | -14.0% | 4.00x | Reversal | -0.869% | Liquidity sweep / reversal |
| 2024-11-29 11:15 | Valid swing, away from level | n/a | -2.6% | 4.00x | Impulse / continuation | 0.343% | True breakout |
| 2024-12-13 10:15 | Valid swing, away from level | n/a | 107.4% | 4.00x | Reversal | -0.520% | Liquidity sweep / reversal |
| 2026-07-13 17:00 | Near Fib level | 50.0% | 46.7% | 4.00x | Impulse / continuation | -0.740% | True breakout |
| 2025-05-21 10:00 | Golden zone 50-61.8% | 61.8% | 56.0% | 3.99x | Flat / fading | -0.059% | Weak move without breakout |
| 2026-05-26 19:45 | Valid swing, away from level | n/a | 135.5% | 3.99x | Reversal | 0.744% | Liquidity sweep / reversal |
| 2026-05-15 17:45 | Valid swing, away from level | n/a | 184.8% | 3.99x | Impulse / continuation | 0.026% | True breakout |
| 2026-06-22 14:45 | Valid swing, away from level | n/a | 144.6% | 3.99x | Impulse / continuation | 0.159% | True breakout |
| 2026-05-18 10:30 | Valid swing, away from level | n/a | 351.7% | 3.99x | Reversal | 0.294% | Liquidity sweep / reversal |
| 2026-01-27 10:30 | Valid swing, away from level | 78.6% | 87.5% | 3.99x | Flat / fading | -0.006% | Weak move without breakout |
| 2025-12-11 10:00 | Valid swing, away from level | n/a | -101.9% | 3.99x | Reversal | 0.037% | Liquidity sweep / reversal |
| 2026-07-01 09:00 | Valid swing, away from level | n/a | -93.1% | 3.99x | Reversal | -0.044% | Liquidity sweep / reversal |
| 2026-05-18 17:45 | Valid swing, away from level | n/a | -21.4% | 3.98x | Impulse / continuation | 0.486% | True breakout |
| 2025-04-02 10:00 | Golden zone 50-61.8% | 61.8% | 61.1% | 3.98x | Reversal | -0.322% | Liquidity sweep / reversal |
| 2024-11-13 19:00 | Near Fib level | 78.6% | 79.6% | 3.98x | Impulse / continuation | -0.928% | True breakout |
| 2026-03-27 11:00 | Near Fib level | 78.6% | 73.8% | 3.98x | Impulse / continuation | -0.157% | True breakout |
| 2025-03-05 19:00 | Valid swing, away from level | n/a | -15.8% | 3.98x | Impulse / continuation | -0.526% | True breakout |
| 2024-12-25 10:45 | Valid swing, away from level | 78.6% | 95.6% | 3.98x | Reversal | 0.444% | Liquidity sweep / reversal |
| 2025-06-13 09:15 | Valid swing, away from level | n/a | 106.0% | 3.97x | Flat / fading | -0.057% | Weak move without breakout |
| 2026-07-02 09:15 | Valid swing, away from level | 78.6% | 91.2% | 3.97x | Impulse / continuation | -0.133% | True breakout |
| 2024-10-30 10:15 | Valid swing, away from level | n/a | -8.8% | 3.97x | Reversal | 0.126% | Liquidity sweep / reversal |
| 2026-07-06 16:15 | Valid swing, away from level | n/a | 144.1% | 3.97x | Impulse / continuation | -0.543% | True breakout |
| 2025-12-25 11:00 | Valid swing, away from level | n/a | -16.7% | 3.97x | Impulse / continuation | 0.304% | True breakout |
| 2026-02-18 18:00 | Valid swing, away from level | n/a | -36.1% | 3.97x | Impulse / continuation | 0.199% | True breakout |
| 2026-02-10 17:00 | Valid swing, away from level | 38.2% | 29.0% | 3.97x | Reversal | -0.266% | Liquidity sweep / reversal |
| 2025-10-16 10:15 | Near Fib level | 38.2% | 40.4% | 3.96x | Impulse / continuation | 0.028% | True breakout |
| 2025-11-19 07:00 | Valid swing, away from level | n/a | -14.3% | 3.96x | Impulse / continuation | 0.495% | True breakout |
| 2025-02-18 15:15 | Valid swing, away from level | n/a | 123.5% | 3.96x | Impulse -> reversal | 0.023% | False breakout |
| 2025-04-23 10:30 | Valid swing, away from level | n/a | 187.2% | 3.96x | Reversal | 0.704% | Liquidity sweep / reversal |
| 2026-03-02 11:00 | Valid swing, away from level | n/a | -4.7% | 3.96x | Reversal | -0.017% | Liquidity sweep / reversal |
| 2026-02-03 07:30 | Valid swing, away from level | n/a | -136.6% | 3.96x | Impulse / continuation | 0.054% | True breakout |
| 2025-12-16 07:15 | Valid swing, away from level | n/a | -2.6% | 3.95x | Reversal | -0.086% | Liquidity sweep / reversal |
| 2025-08-30 18:45 | Valid swing, away from level | n/a | 125.0% | 3.95x | Impulse / continuation | 0.216% | True breakout |
| 2025-05-08 10:00 | Valid swing, away from level | n/a | -10.6% | 3.95x | Reversal | -0.052% | Liquidity sweep / reversal |
| 2025-07-02 11:15 | Valid swing, away from level | n/a | 133.9% | 3.95x | Reversal | -0.147% | Liquidity sweep / reversal |
| 2026-02-16 09:45 | Valid swing, away from level | n/a | -516.7% | 3.95x | Impulse / continuation | 0.147% | True breakout |
| 2025-08-28 18:00 | Valid swing, away from level | n/a | -14.0% | 3.95x | Flat / fading | -0.118% | Weak move without breakout |
| 2025-11-17 10:15 | Near Fib level | 61.8% | 64.1% | 3.95x | Reversal | 0.487% | Liquidity sweep / reversal |
| 2026-09-10 15:30 | Valid swing, away from level | 38.2% | 8.5% | 3.95x | Reversal | -0.207% | Liquidity sweep / reversal |
| 2025-04-17 17:30 | Valid swing, away from level | n/a | 102.5% | 3.95x | Flat / fading | 0.120% | Weak move without breakout |
| 2024-12-28 10:30 | Valid swing, away from level | n/a | -63.3% | 3.94x | Impulse / continuation | 0.204% | True breakout |
| 2025-10-16 11:00 | Valid swing, away from level | 38.2% | 14.1% | 3.94x | Reversal | -0.055% | Liquidity sweep / reversal |
| 2024-12-24 11:15 | Valid swing, away from level | n/a | 126.1% | 3.94x | Impulse / continuation | 0.729% | True breakout |
| 2025-04-16 07:00 | Valid swing, away from level | 78.6% | 70.6% | 3.94x | Reversal | 0.198% | Liquidity sweep / reversal |
| 2026-08-18 10:30 | Golden zone 50-61.8% | 50.0% | 54.6% | 3.94x | Reversal | 1.247% | Liquidity sweep / reversal |
| 2025-09-08 07:15 | Valid swing, away from level | n/a | -139.1% | 3.94x | Impulse / continuation | 0.096% | True breakout |
| 2025-12-10 19:00 | Valid swing, away from level | 78.6% | 89.5% | 3.94x | Flat / fading | 0.142% | Position building in range |
| 2026-08-24 10:00 | Valid swing, away from level | n/a | 635.7% | 3.94x | Reversal | -0.056% | Liquidity sweep / reversal |
| 2025-05-10 18:45 | Valid swing, away from level | n/a | 157.1% | 3.93x | Impulse / continuation | 2.361% | True breakout |
| 2025-06-04 10:00 | Valid swing, away from level | n/a | -184.3% | 3.93x | Reversal | -0.103% | Liquidity sweep / reversal |
| 2025-05-22 07:45 | Valid swing, away from level | n/a | 113.6% | 3.93x | Impulse / continuation | -0.641% | True breakout |
| 2025-09-01 07:30 | Valid swing, away from level | n/a | -62.5% | 3.93x | Flat / fading | 0.012% | Weak move without breakout |
| 2024-11-15 10:15 | Near Fib level | 38.2% | 35.1% | 3.93x | Flat / fading | -0.148% | Weak move without breakout |
| 2026-05-27 11:45 | Near Fib level | 38.2% | 38.8% | 3.93x | Flat / fading | -0.040% | Position building in range |
| 2025-01-22 19:15 | Valid swing, away from level | n/a | 160.2% | 3.93x | Impulse / continuation | -0.285% | True breakout |
| 2025-12-16 11:00 | Valid swing, away from level | n/a | -40.5% | 3.93x | Flat / fading | 0.116% | Weak move without breakout |
| 2025-07-13 11:45 | Valid swing, away from level | n/a | 109.7% | 3.93x | Impulse / continuation | -0.116% | True breakout |
| 2024-09-26 11:00 | Golden zone 50-61.8% | 61.8% | 60.8% | 3.93x | Flat / fading | -0.056% | Weak move without breakout |
| 2026-05-08 13:15 | Valid swing, away from level | n/a | 191.7% | 3.93x | Flat / fading | 0.111% | Weak move without breakout |
| 2025-09-18 20:45 | Valid swing, away from level | n/a | 121.8% | 3.93x | Flat / fading | 0.326% | Position building in range |
| 2026-04-06 14:45 | Valid swing, away from level | n/a | 113.7% | 3.92x | Flat / fading | 0.062% | Weak move without breakout |
| 2025-10-15 10:00 | Near Fib level | 61.8% | 64.3% | 3.92x | Impulse / continuation | -0.028% | True breakout |
| 2026-01-17 18:15 | Near Fib level | 78.6% | 74.4% | 3.92x | Impulse / continuation | 0.012% | True breakout |
| 2026-05-12 10:45 | Valid swing, away from level | n/a | -57.8% | 3.92x | Flat / fading | -0.045% | Weak move without breakout |
| 2025-05-05 10:00 | Near Fib level | 78.6% | 75.3% | 3.92x | Reversal | -0.145% | Liquidity sweep / reversal |
| 2025-02-07 11:00 | Near Fib level | 38.2% | 35.4% | 3.92x | Reversal | -0.455% | Liquidity sweep / reversal |
| 2025-08-05 07:00 | Valid swing, away from level | n/a | -269.8% | 3.91x | Reversal | 0.019% | Liquidity sweep / reversal |
| 2025-04-09 20:30 | Valid swing, away from level | n/a | -2.7% | 3.91x | Impulse / continuation | 0.958% | True breakout |
| 2026-06-29 09:30 | Valid swing, away from level | n/a | 169.8% | 3.91x | Reversal | -0.831% | Liquidity sweep / reversal |
| 2026-05-25 08:15 | Valid swing, away from level | n/a | -97.2% | 3.91x | Reversal | -0.026% | Liquidity sweep / reversal |
| 2026-06-17 10:45 | Valid swing, away from level | n/a | -58.0% | 3.91x | Reversal | -0.982% | Liquidity sweep / reversal |
| 2026-03-27 13:00 | Valid swing, away from level | n/a | 300.0% | 3.91x | Impulse / continuation | -0.024% | True breakout |
| 2026-04-03 09:15 | Valid swing, away from level | n/a | -9.0% | 3.91x | Impulse / continuation | -0.473% | True breakout |
| 2026-06-29 10:30 | Valid swing, away from level | n/a | 377.4% | 3.91x | Reversal | 2.042% | Liquidity sweep / reversal |
| 2025-04-23 20:00 | Valid swing, away from level | n/a | -30.8% | 3.91x | Flat / fading | -0.031% | Weak move without breakout |
| 2026-04-02 07:00 | Near Fib level | 50.0% | 45.9% | 3.90x | Impulse / continuation | -0.136% | True breakout |
| 2026-05-23 16:00 | Golden zone 50-61.8% | 50.0% | 53.2% | 3.90x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-11-28 10:30 | Near Fib level | 61.8% | 65.4% | 3.90x | Reversal | -0.170% | Liquidity sweep / reversal |
| 2025-02-10 09:45 | Valid swing, away from level | n/a | -678.8% | 3.90x | Impulse / continuation | 0.209% | True breakout |
| 2025-10-08 07:00 | Valid swing, away from level | 38.2% | 16.0% | 3.90x | Flat / fading | -0.020% | Position building in range |
| 2025-06-30 10:45 | Valid swing, away from level | n/a | 134.4% | 3.90x | Impulse / continuation | -0.343% | True breakout |
| 2026-06-29 11:30 | Valid swing, away from level | n/a | -128.3% | 3.90x | Flat / fading | -0.119% | Weak move without breakout |
| 2026-07-02 16:45 | Valid swing, away from level | n/a | 760.7% | 3.90x | Reversal | 0.898% | Liquidity sweep / reversal |
| 2025-11-25 15:45 | Valid swing, away from level | 38.2% | 23.9% | 3.90x | Flat / fading | 0.454% | Weak move without breakout |
| 2026-06-22 22:15 | Valid swing, away from level | n/a | 170.0% | 3.89x | Reversal | 1.628% | Liquidity sweep / reversal |
| 2025-10-16 20:15 | Valid swing, away from level | n/a | -1152.2% | 3.89x | Flat / fading | -0.117% | Position building in range |
| 2025-10-07 09:00 | Valid swing, away from level | n/a | -2.3% | 3.89x | Impulse / continuation | -0.336% | True breakout |
| 2025-01-22 10:15 | Golden zone 50-61.8% | 61.8% | 56.4% | 3.89x | Reversal | -0.217% | Liquidity sweep / reversal |
| 2024-10-25 19:45 | Valid swing, away from level | n/a | 654.3% | 3.89x | Flat / fading | 0.751% | Position building in range |
| 2025-03-03 08:00 | Valid swing, away from level | n/a | 250.0% | 3.89x | Impulse -> reversal | -0.253% | False breakout |
| 2025-05-16 16:15 | Valid swing, away from level | n/a | 330.0% | 3.89x | Impulse / continuation | 1.255% | True breakout |
| 2024-12-24 10:45 | Valid swing, away from level | n/a | 145.7% | 3.89x | Reversal | 0.285% | Liquidity sweep / reversal |
| 2026-08-18 11:45 | Valid swing, away from level | n/a | -49.3% | 3.89x | Impulse / continuation | 0.834% | True breakout |
| 2024-12-25 10:30 | Near Fib level | 78.6% | 82.9% | 3.89x | Reversal | 0.233% | Liquidity sweep / reversal |
| 2025-01-10 10:30 | Near Fib level | 38.2% | 35.4% | 3.88x | Impulse / continuation | -0.363% | True breakout |
| 2026-09-23 12:30 | Valid swing, away from level | n/a | 205.4% | 3.88x | Flat / fading | 0.149% | Weak move without breakout |
| 2025-01-27 10:30 | Valid swing, away from level | n/a | 157.4% | 3.88x | Reversal | -0.160% | Liquidity sweep / reversal |
| 2025-01-17 10:15 | Valid swing, away from level | n/a | 112.3% | 3.88x | Reversal | 0.942% | Liquidity sweep / reversal |
| 2026-03-31 09:15 | Valid swing, away from level | n/a | -23.6% | 3.88x | Impulse / continuation | 0.062% | True breakout |
| 2025-08-30 17:00 | Near Fib level | 78.6% | 75.0% | 3.87x | Impulse / continuation | -0.222% | True breakout |
| 2026-02-16 23:30 | Valid swing, away from level | 38.2% | 4.9% | 3.87x | Impulse / continuation | 0.229% | True breakout |
| 2025-04-11 10:00 | Valid swing, away from level | n/a | -9.0% | 3.87x | Reversal | 0.127% | Liquidity sweep / reversal |
| 2025-12-17 12:00 | Valid swing, away from level | n/a | 170.4% | 3.87x | Impulse / continuation | -0.209% | True breakout |
| 2025-05-20 10:15 | Valid swing, away from level | 78.6% | 92.6% | 3.87x | Impulse / continuation | -0.254% | True breakout |
| 2026-09-09 17:45 | Valid swing, away from level | 78.6% | 92.1% | 3.87x | Reversal | 0.410% | Liquidity sweep / reversal |
| 2025-12-03 17:15 | Valid swing, away from level | 38.2% | 5.1% | 3.87x | Impulse / continuation | 0.472% | True breakout |
| 2025-04-01 07:15 | Valid swing, away from level | n/a | -23.9% | 3.86x | Flat / fading | -0.288% | Weak move without breakout |
| 2026-07-28 10:45 | Valid swing, away from level | n/a | 243.7% | 3.86x | Impulse / continuation | -0.176% | True breakout |
| 2026-04-24 15:15 | Valid swing, away from level | n/a | 585.7% | 3.86x | Impulse / continuation | -0.424% | True breakout |
| 2025-11-13 10:30 | Near Fib level | 61.8% | 66.0% | 3.86x | Reversal | 0.440% | Liquidity sweep / reversal |
| 2026-06-08 08:00 | Valid swing, away from level | n/a | -243.5% | 3.86x | Impulse / continuation | -0.114% | True breakout |
| 2026-03-17 09:15 | Valid swing, away from level | 38.2% | 27.3% | 3.86x | Flat / fading | -0.035% | Weak move without breakout |
| 2026-09-11 09:30 | Near Fib level | 78.6% | 73.9% | 3.86x | Impulse / continuation | -0.008% | True breakout |
| 2026-06-22 10:30 | Near Fib level | 78.6% | 81.3% | 3.85x | Impulse / continuation | 0.496% | True breakout |
| 2025-02-19 09:15 | Near Fib level | 50.0% | 47.9% | 3.85x | Flat / fading | -0.321% | Weak move without breakout |
| 2025-11-14 10:45 | Valid swing, away from level | 38.2% | 5.1% | 3.85x | Reversal | -0.540% | Liquidity sweep / reversal |
| 2025-10-14 09:15 | Valid swing, away from level | 78.6% | 97.0% | 3.85x | Impulse / continuation | 0.048% | True breakout |
| 2025-05-12 20:15 | Valid swing, away from level | n/a | -24.8% | 3.85x | Flat / fading | -0.209% | Position building in range |
| 2024-12-16 11:30 | Valid swing, away from level | n/a | 143.9% | 3.85x | Flat / fading | -0.062% | Weak move without breakout |
| 2026-02-20 09:15 | Valid swing, away from level | 38.2% | 30.6% | 3.85x | Impulse / continuation | 0.324% | True breakout |
| 2025-01-28 22:00 | Valid swing, away from level | n/a | -5.8% | 3.85x | Flat / fading | -0.166% | Weak move without breakout |
| 2025-09-16 08:30 | Valid swing, away from level | n/a | -113.0% | 3.84x | Reversal | -0.101% | Liquidity sweep / reversal |
| 2025-12-04 10:00 | Valid swing, away from level | n/a | -33.8% | 3.84x | Reversal | 0.257% | Liquidity sweep / reversal |
| 2025-03-03 10:00 | Valid swing, away from level | n/a | 319.4% | 3.84x | Flat / fading | 0.019% | Weak move without breakout |
| 2024-12-18 10:15 | Valid swing, away from level | n/a | -26.0% | 3.84x | Impulse / continuation | -0.180% | True breakout |
| 2025-10-10 16:45 | Valid swing, away from level | n/a | 208.4% | 3.84x | Reversal | 0.255% | Liquidity sweep / reversal |
| 2025-03-03 10:15 | Valid swing, away from level | n/a | 332.7% | 3.84x | Reversal | -0.329% | Liquidity sweep / reversal |
| 2026-08-27 11:30 | Valid swing, away from level | n/a | -103.0% | 3.84x | Reversal | -0.429% | Liquidity sweep / reversal |
| 2025-01-27 17:00 | Valid swing, away from level | n/a | 110.7% | 3.84x | Flat / fading | -0.188% | Weak move without breakout |
| 2025-10-20 22:30 | Near Fib level | 78.6% | 78.3% | 3.84x | Flat / fading | -0.051% | Position building in range |
| 2025-02-10 23:00 | Valid swing, away from level | 78.6% | 71.0% | 3.84x | Reversal | 0.928% | Liquidity sweep / reversal |
| 2025-05-16 16:00 | Valid swing, away from level | n/a | 610.0% | 3.84x | Reversal | 2.730% | Liquidity sweep / reversal |
| 2026-07-28 07:15 | Valid swing, away from level | 38.2% | 7.3% | 3.83x | Flat / fading | -0.098% | Weak move without breakout |
| 2025-01-10 10:15 | Valid swing, away from level | 38.2% | 25.0% | 3.83x | Reversal | -0.608% | Liquidity sweep / reversal |
| 2025-07-03 11:15 | Valid swing, away from level | n/a | -20.0% | 3.83x | Reversal | 0.073% | Liquidity sweep / reversal |
| 2025-02-28 11:00 | Valid swing, away from level | n/a | 114.8% | 3.83x | Flat / fading | 0.162% | Weak move without breakout |
| 2025-09-25 09:00 | Near Fib level | 38.2% | 40.6% | 3.83x | Reversal | 0.102% | Liquidity sweep / reversal |
| 2026-07-30 09:30 | Valid swing, away from level | n/a | -34.0% | 3.83x | Impulse / continuation | 0.734% | True breakout |
| 2025-01-29 19:00 | Valid swing, away from level | 38.2% | 15.9% | 3.83x | Reversal | -0.211% | Liquidity sweep / reversal |
| 2026-05-25 12:00 | Valid swing, away from level | n/a | -76.1% | 3.83x | Flat / fading | -0.240% | Position building in range |
| 2026-03-15 10:00 | Valid swing, away from level | n/a | -28.0% | 3.83x | Flat / fading | 0.012% | Position building in range |
| 2025-09-23 09:30 | Valid swing, away from level | n/a | -94.7% | 3.82x | Flat / fading | -0.051% | Weak move without breakout |
| 2026-05-07 09:15 | Near Fib level | 38.2% | 38.6% | 3.82x | Reversal | -0.103% | Liquidity sweep / reversal |
| 2025-07-18 10:30 | Valid swing, away from level | n/a | -66.2% | 3.82x | Flat / fading | 0.204% | Weak move without breakout |
| 2026-03-02 09:30 | Near Fib level | 78.6% | 77.6% | 3.82x | Reversal | 0.384% | Liquidity sweep / reversal |
| 2026-07-31 07:15 | Near Fib level | 38.2% | 41.1% | 3.82x | Reversal | -0.638% | Liquidity sweep / reversal |
| 2026-04-09 09:15 | Valid swing, away from level | n/a | 108.3% | 3.82x | Flat / fading | 0.094% | Weak move without breakout |
| 2024-10-21 10:30 | Valid swing, away from level | n/a | -39.5% | 3.82x | Reversal | 0.058% | Liquidity sweep / reversal |
| 2026-08-10 07:15 | Valid swing, away from level | 38.2% | 21.3% | 3.82x | Impulse / continuation | -0.057% | True breakout |
| 2026-03-27 10:30 | Valid swing, away from level | n/a | -50.0% | 3.82x | Reversal | -0.447% | Liquidity sweep / reversal |
| 2026-03-13 08:30 | Valid swing, away from level | n/a | -133.9% | 3.81x | Flat / fading | -0.212% | Weak move without breakout |
| 2025-05-06 17:45 | Valid swing, away from level | n/a | -83.0% | 3.81x | Impulse / continuation | -0.131% | True breakout |
| 2025-08-04 10:00 | Valid swing, away from level | 38.2% | 15.6% | 3.81x | Impulse / continuation | 0.196% | True breakout |
| 2026-06-24 17:45 | Valid swing, away from level | n/a | 415.3% | 3.81x | Flat / fading | 0.513% | Position building in range |
| 2026-07-27 09:00 | Valid swing, away from level | 38.2% | 25.0% | 3.81x | Flat / fading | 0.030% | Weak move without breakout |
| 2025-10-16 09:00 | Valid swing, away from level | 78.6% | 73.5% | 3.81x | Impulse / continuation | -0.166% | True breakout |
| 2025-10-29 09:45 | Valid swing, away from level | 38.2% | 13.7% | 3.81x | Impulse / continuation | 0.185% | True breakout |
| 2026-01-18 17:45 | Near Fib level | 61.8% | 66.7% | 3.81x | Impulse / continuation | 0.012% | True breakout |
| 2025-03-11 09:45 | Near Fib level | 78.6% | 75.2% | 3.81x | Reversal | 0.609% | Liquidity sweep / reversal |
| 2025-08-04 12:15 | Valid swing, away from level | n/a | -25.5% | 3.81x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-06-17 10:30 | Valid swing, away from level | 38.2% | 26.2% | 3.81x | Impulse / continuation | 0.455% | True breakout |
| 2026-07-07 08:30 | Valid swing, away from level | n/a | 111.6% | 3.81x | Reversal | 0.399% | Liquidity sweep / reversal |
| 2025-10-29 09:00 | Valid swing, away from level | 38.2% | 10.6% | 3.81x | Impulse -> reversal | 0.205% | False breakout |
| 2025-06-18 10:15 | Valid swing, away from level | 38.2% | 33.0% | 3.80x | Flat / fading | 0.081% | Weak move without breakout |
| 2025-09-11 10:30 | Valid swing, away from level | 78.6% | 84.9% | 3.80x | Reversal | -0.685% | Liquidity sweep / reversal |
| 2025-11-24 07:00 | Valid swing, away from level | n/a | -24.2% | 3.80x | Flat / fading | -0.243% | Position building in range |
| 2026-07-27 09:15 | Near Fib level | 78.6% | 79.6% | 3.80x | Reversal | 0.329% | Liquidity sweep / reversal |
| 2026-07-21 09:15 | Valid swing, away from level | n/a | -7.3% | 3.80x | Reversal | -1.616% | Liquidity sweep / reversal |
| 2025-03-25 10:00 | Valid swing, away from level | 38.2% | 6.9% | 3.80x | Impulse / continuation | 0.017% | True breakout |
| 2026-06-16 12:45 | Valid swing, away from level | n/a | 145.8% | 3.79x | Flat / fading | -0.026% | Position building in range |
| 2025-03-25 12:45 | Valid swing, away from level | 61.8% | 67.6% | 3.79x | Flat / fading | -0.022% | Weak move without breakout |
| 2025-07-05 18:45 | Near Fib level | 61.8% | 66.7% | 3.79x | Reversal | -0.211% | Liquidity sweep / reversal |
| 2025-06-04 17:15 | Near Fib level | 38.2% | 40.5% | 3.79x | Flat / fading | -0.043% | Weak move without breakout |
| 2024-11-26 10:30 | Near Fib level | 50.0% | 45.6% | 3.79x | Impulse / continuation | 0.526% | True breakout |
| 2026-06-22 10:45 | Near Fib level | 61.8% | 62.9% | 3.79x | Flat / fading | -0.366% | Position building in range |
| 2025-02-21 22:45 | Valid swing, away from level | 38.2% | 25.8% | 3.79x | Reversal | 0.134% | Liquidity sweep / reversal |
| 2025-06-08 11:15 | Valid swing, away from level | 38.2% | 28.1% | 3.79x | Flat / fading | 0.025% | Position building in range |
| 2025-08-04 18:15 | Valid swing, away from level | n/a | -133.7% | 3.78x | Flat / fading | 0.031% | Position building in range |
| 2025-03-28 14:45 | Valid swing, away from level | n/a | 148.4% | 3.78x | Impulse / continuation | -0.174% | True breakout |
| 2024-12-24 10:30 | Valid swing, away from level | n/a | 147.1% | 3.78x | Impulse -> reversal | 0.285% | False breakout |
| 2025-04-28 09:00 | Valid swing, away from level | n/a | 160.9% | 3.78x | Reversal | -0.109% | Liquidity sweep / reversal |
| 2026-03-11 12:00 | Near Fib level | 78.6% | 77.2% | 3.78x | Impulse / continuation | -0.207% | True breakout |
| 2026-06-08 11:30 | Valid swing, away from level | n/a | 141.2% | 3.78x | Flat / fading | -0.263% | Weak move without breakout |
| 2025-11-14 11:00 | Near Fib level | 50.0% | 47.5% | 3.78x | Impulse / continuation | -0.460% | True breakout |
| 2026-02-11 08:30 | Valid swing, away from level | 38.2% | 11.2% | 3.78x | Reversal | -0.151% | Liquidity sweep / reversal |
| 2025-08-29 14:30 | Valid swing, away from level | n/a | 228.3% | 3.78x | Flat / fading | 0.114% | Position building in range |
| 2025-07-09 10:30 | Near Fib level | 38.2% | 42.9% | 3.77x | Reversal | 0.158% | Liquidity sweep / reversal |
| 2026-07-20 16:00 | Valid swing, away from level | n/a | -153.8% | 3.77x | Reversal | -1.498% | Liquidity sweep / reversal |
| 2025-09-14 15:00 | Valid swing, away from level | n/a | -26.0% | 3.77x | Flat / fading | 0.050% | Weak move without breakout |
| 2025-11-17 09:00 | Valid swing, away from level | n/a | 120.5% | 3.76x | Impulse / continuation | 0.302% | True breakout |
| 2025-10-31 10:00 | Near Fib level | 78.6% | 82.6% | 3.76x | Impulse / continuation | -0.181% | True breakout |
| 2025-02-19 19:00 | Valid swing, away from level | n/a | -129.1% | 3.76x | Reversal | 0.267% | Liquidity sweep / reversal |
| 2026-06-29 07:30 | Valid swing, away from level | 38.2% | 25.0% | 3.76x | Flat / fading | 0.038% | Weak move without breakout |
| 2025-12-24 07:00 | Valid swing, away from level | 38.2% | 22.0% | 3.76x | Impulse / continuation | -0.126% | True breakout |
| 2025-08-01 10:00 | Valid swing, away from level | n/a | -116.9% | 3.75x | Reversal | 0.082% | Liquidity sweep / reversal |
| 2025-03-11 20:45 | Near Fib level | 50.0% | 45.7% | 3.75x | Impulse / continuation | -0.786% | True breakout |
| 2026-04-03 11:30 | Valid swing, away from level | n/a | 114.6% | 3.75x | Impulse / continuation | -0.216% | True breakout |
| 2026-04-01 10:15 | Near Fib level | 38.2% | 38.8% | 3.75x | Reversal | -0.288% | Liquidity sweep / reversal |
| 2025-09-11 11:00 | Valid swing, away from level | n/a | 131.9% | 3.75x | Reversal | -0.332% | Liquidity sweep / reversal |
| 2025-02-04 21:45 | Valid swing, away from level | n/a | 172.2% | 3.75x | Flat / fading | -0.067% | Position building in range |
| 2025-10-12 18:15 | Valid swing, away from level | 78.6% | 90.9% | 3.75x | Reversal | 0.468% | Liquidity sweep / reversal |
| 2026-03-04 11:15 | Valid swing, away from level | n/a | -7.3% | 3.75x | Flat / fading | 0.012% | Weak move without breakout |
| 2024-10-17 10:30 | Valid swing, away from level | n/a | -12.5% | 3.75x | Impulse -> reversal | 0.019% | False breakout |
| 2026-09-24 11:15 | Valid swing, away from level | 38.2% | 19.9% | 3.75x | Insufficient data | n/a | Insufficient data |
| 2025-11-05 13:30 | Valid swing, away from level | n/a | -48.3% | 3.75x | Flat / fading | 0.100% | Weak move without breakout |
| 2024-11-22 10:00 | Valid swing, away from level | n/a | -33.0% | 3.75x | Flat / fading | -0.062% | Weak move without breakout |
| 2024-10-30 10:30 | Valid swing, away from level | n/a | -11.7% | 3.74x | Impulse / continuation | 0.042% | True breakout |
| 2024-12-12 10:15 | Valid swing, away from level | 38.2% | 27.0% | 3.74x | Impulse / continuation | 0.486% | True breakout |
| 2025-09-23 07:00 | Valid swing, away from level | n/a | -62.7% | 3.74x | Flat / fading | 0.058% | Weak move without breakout |
| 2026-07-27 10:45 | Valid swing, away from level | n/a | -17.5% | 3.74x | Flat / fading | -0.318% | Weak move without breakout |
| 2026-02-12 12:45 | Valid swing, away from level | n/a | -102.3% | 3.74x | Flat / fading | 0.060% | Weak move without breakout |
| 2026-03-26 10:00 | Near Fib level | 78.6% | 73.7% | 3.74x | Impulse / continuation | -0.258% | True breakout |
| 2025-03-20 07:15 | Valid swing, away from level | n/a | -66.2% | 3.74x | Flat / fading | -0.353% | Weak move without breakout |
| 2024-10-02 10:30 | Valid swing, away from level | n/a | -19.7% | 3.74x | Reversal | -0.503% | Liquidity sweep / reversal |
| 2025-03-13 07:45 | Valid swing, away from level | n/a | 138.2% | 3.74x | Flat / fading | 0.118% | Position building in range |
| 2026-07-09 10:15 | Near Fib level | 78.6% | 78.7% | 3.74x | Impulse / continuation | 0.110% | True breakout |
| 2025-12-25 10:00 | Valid swing, away from level | n/a | 147.6% | 3.73x | Impulse -> reversal | 0.438% | False breakout |
| 2025-02-26 19:00 | Valid swing, away from level | n/a | 493.6% | 3.73x | Reversal | 0.018% | Liquidity sweep / reversal |
| 2026-01-14 10:00 | Valid swing, away from level | n/a | 117.1% | 3.73x | Reversal | 0.220% | Liquidity sweep / reversal |
| 2026-08-10 11:00 | Near Fib level | 78.6% | 80.2% | 3.73x | Flat / fading | 0.137% | Weak move without breakout |
| 2025-10-13 09:15 | Valid swing, away from level | n/a | -211.1% | 3.73x | Impulse / continuation | 0.370% | True breakout |
| 2026-08-13 10:45 | Valid swing, away from level | 78.6% | 85.4% | 3.73x | Flat / fading | -0.094% | Weak move without breakout |
| 2025-09-05 12:00 | Valid swing, away from level | n/a | -13.9% | 3.73x | Flat / fading | 0.006% | Weak move without breakout |
| 2025-07-16 07:00 | Near Fib level | 61.8% | 63.3% | 3.73x | Reversal | 0.097% | Liquidity sweep / reversal |
| 2026-03-02 09:45 | Valid swing, away from level | 61.8% | 67.3% | 3.73x | Impulse / continuation | 0.425% | True breakout |
| 2026-09-07 07:00 | Valid swing, away from level | n/a | 151.0% | 3.73x | Reversal | -0.054% | Liquidity sweep / reversal |
| 2025-03-19 10:00 | Near Fib level | 78.6% | 81.3% | 3.72x | Flat / fading | 0.236% | Position building in range |
| 2025-07-28 16:15 | Valid swing, away from level | n/a | 315.0% | 3.72x | Reversal | -0.194% | Liquidity sweep / reversal |
| 2025-04-29 12:15 | Valid swing, away from level | 78.6% | 72.4% | 3.72x | Impulse / continuation | -0.220% | True breakout |
| 2025-06-04 09:45 | Valid swing, away from level | n/a | -177.4% | 3.72x | Impulse / continuation | 0.213% | True breakout |
| 2025-03-24 07:00 | Valid swing, away from level | 78.6% | 83.7% | 3.72x | Impulse / continuation | -0.017% | True breakout |
| 2024-12-26 10:30 | Valid swing, away from level | n/a | -56.6% | 3.72x | Reversal | -0.783% | Liquidity sweep / reversal |
| 2024-12-02 10:30 | Valid swing, away from level | n/a | -73.5% | 3.72x | Reversal | -0.372% | Liquidity sweep / reversal |
| 2025-10-19 10:15 | Valid swing, away from level | n/a | 116.4% | 3.72x | Impulse / continuation | -0.273% | True breakout |
| 2026-02-13 09:15 | Valid swing, away from level | n/a | 151.1% | 3.71x | Flat / fading | 0.036% | Weak move without breakout |
| 2025-05-28 10:15 | Valid swing, away from level | n/a | -78.0% | 3.71x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-11-01 23:30 | Valid swing, away from level | n/a | 103.5% | 3.71x | Reversal | 0.585% | Liquidity sweep / reversal |
| 2025-11-25 15:15 | Valid swing, away from level | 38.2% | 4.6% | 3.71x | Impulse / continuation | 0.045% | True breakout |
| 2025-09-29 07:30 | Valid swing, away from level | n/a | -14.3% | 3.71x | Reversal | 0.135% | Liquidity sweep / reversal |
| 2025-03-18 20:15 | Valid swing, away from level | n/a | -112.5% | 3.71x | Flat / fading | -0.111% | Weak move without breakout |
| 2025-08-08 17:00 | Near Fib level | 50.0% | 49.4% | 3.71x | Flat / fading | 0.217% | Weak move without breakout |
| 2026-02-17 11:15 | Valid swing, away from level | 61.8% | 69.7% | 3.71x | Impulse / continuation | 0.518% | True breakout |
| 2026-06-17 07:45 | Valid swing, away from level | n/a | 101.8% | 3.71x | Reversal | 0.310% | Liquidity sweep / reversal |
| 2025-07-01 11:15 | Valid swing, away from level | n/a | -55.0% | 3.71x | Impulse / continuation | -0.152% | True breakout |
| 2026-06-19 09:00 | Valid swing, away from level | 38.2% | 21.3% | 3.71x | Reversal | -0.349% | Liquidity sweep / reversal |
| 2025-02-10 10:15 | Valid swing, away from level | n/a | -787.9% | 3.71x | Flat / fading | -0.221% | Weak move without breakout |
| 2026-04-08 23:30 | Valid swing, away from level | n/a | 120.0% | 3.71x | Impulse / continuation | 0.113% | True breakout |
| 2025-05-18 10:00 | Valid swing, away from level | n/a | -1084.6% | 3.71x | Flat / fading | 0.115% | Position building in range |
| 2025-10-17 14:15 | Valid swing, away from level | 38.2% | 5.3% | 3.71x | Flat / fading | 0.044% | Position building in range |
| 2025-08-28 12:00 | Golden zone 50-61.8% | 50.0% | 55.4% | 3.70x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-11-20 10:15 | Near Fib level | 38.2% | 39.3% | 3.70x | Flat / fading | 0.059% | Weak move without breakout |
| 2026-08-03 07:30 | Valid swing, away from level | n/a | -126.2% | 3.70x | Reversal | 0.111% | Liquidity sweep / reversal |
| 2026-09-08 17:15 | Valid swing, away from level | 78.6% | 73.1% | 3.70x | Impulse / continuation | -0.259% | True breakout |
| 2025-11-18 22:00 | Valid swing, away from level | n/a | -49.2% | 3.70x | Flat / fading | -0.234% | Position building in range |
| 2026-04-27 20:30 | Valid swing, away from level | n/a | 131.1% | 3.70x | Flat / fading | 0.044% | Position building in range |
| 2025-07-01 07:30 | Valid swing, away from level | 38.2% | 15.8% | 3.70x | Reversal | -0.079% | Liquidity sweep / reversal |
| 2024-11-21 10:45 | Valid swing, away from level | 78.6% | 98.0% | 3.70x | Impulse / continuation | -0.592% | True breakout |
| 2026-07-06 09:15 | Valid swing, away from level | 78.6% | 72.6% | 3.69x | Impulse / continuation | 0.142% | True breakout |
| 2025-09-15 10:30 | Valid swing, away from level | n/a | 180.0% | 3.69x | Impulse / continuation | -0.510% | True breakout |
| 2025-06-08 13:30 | Valid swing, away from level | 38.2% | 20.5% | 3.69x | Flat / fading | -0.062% | Weak move without breakout |
| 2025-09-22 10:30 | Valid swing, away from level | n/a | 122.2% | 3.69x | Reversal | 0.163% | Liquidity sweep / reversal |
| 2024-12-18 11:00 | Valid swing, away from level | n/a | -1.6% | 3.69x | Flat / fading | -0.235% | Weak move without breakout |
| 2025-02-12 20:15 | Valid swing, away from level | n/a | -246.4% | 3.69x | Impulse / continuation | 1.641% | True breakout |
| 2026-04-30 10:45 | Valid swing, away from level | n/a | -23.7% | 3.69x | Reversal | -0.674% | Liquidity sweep / reversal |
| 2025-11-10 07:15 | Valid swing, away from level | n/a | -441.2% | 3.69x | Reversal | -0.040% | Liquidity sweep / reversal |
| 2024-09-27 10:30 | Valid swing, away from level | 38.2% | 9.5% | 3.69x | Impulse / continuation | 0.572% | True breakout |
| 2025-05-06 10:00 | Golden zone 50-61.8% | 50.0% | 50.0% | 3.69x | Impulse / continuation | 1.379% | True breakout |
| 2025-05-07 10:00 | Valid swing, away from level | n/a | 126.6% | 3.69x | Reversal | 0.874% | Liquidity sweep / reversal |
| 2025-07-04 10:00 | Near Fib level | 50.0% | 49.4% | 3.69x | Reversal | -0.658% | Liquidity sweep / reversal |
| 2025-11-28 10:00 | Near Fib level | 78.6% | 74.6% | 3.69x | Reversal | -0.098% | Liquidity sweep / reversal |
| 2026-01-29 18:00 | No confirmed swing | n/a | n/a | 3.69x | Impulse / continuation | -0.285% | True breakout |
| 2025-06-18 10:00 | Valid swing, away from level | n/a | -10.2% | 3.69x | Impulse / continuation | -0.193% | True breakout |
| 2025-07-23 10:30 | Valid swing, away from level | n/a | -49.5% | 3.69x | Flat / fading | 0.024% | Weak move without breakout |
| 2025-06-03 07:00 | Valid swing, away from level | 38.2% | 30.1% | 3.69x | Impulse / continuation | 0.287% | True breakout |
| 2025-06-09 10:30 | Valid swing, away from level | n/a | 518.9% | 3.68x | Impulse / continuation | -0.270% | True breakout |
| 2025-03-27 15:45 | Valid swing, away from level | n/a | 139.2% | 3.68x | Flat / fading | 0.466% | Weak move without breakout |
| 2025-11-18 23:15 | Valid swing, away from level | n/a | 115.9% | 3.68x | Impulse -> reversal | 0.552% | False breakout |
| 2025-04-29 18:00 | Valid swing, away from level | n/a | 123.9% | 3.68x | Reversal | 0.190% | Liquidity sweep / reversal |
| 2026-07-28 07:00 | Near Fib level | 38.2% | 33.6% | 3.68x | Impulse / continuation | 0.212% | True breakout |
| 2025-03-25 12:30 | Near Fib level | 50.0% | 47.2% | 3.68x | Impulse / continuation | -0.395% | True breakout |
| 2025-03-10 14:00 | Valid swing, away from level | 38.2% | 4.2% | 3.68x | Flat / fading | -0.191% | Position building in range |
| 2026-04-22 17:30 | Valid swing, away from level | n/a | -23.4% | 3.68x | Impulse / continuation | 0.172% | True breakout |
| 2025-04-01 14:30 | Valid swing, away from level | 38.2% | 13.1% | 3.68x | Impulse / continuation | -0.701% | True breakout |
| 2026-09-10 10:15 | Valid swing, away from level | 38.2% | 23.8% | 3.67x | Impulse / continuation | 0.208% | True breakout |
| 2026-03-04 10:00 | Golden zone 50-61.8% | 50.0% | 54.5% | 3.67x | Reversal | 0.348% | Liquidity sweep / reversal |
| 2025-11-19 07:30 | Valid swing, away from level | n/a | -14.0% | 3.67x | Impulse / continuation | 0.267% | True breakout |
| 2026-05-25 17:15 | Valid swing, away from level | n/a | 202.3% | 3.67x | Flat / fading | 0.211% | Weak move without breakout |
| 2025-08-30 15:15 | Valid swing, away from level | 61.8% | 69.7% | 3.67x | Flat / fading | -0.018% | Position building in range |
| 2026-03-24 10:45 | Valid swing, away from level | n/a | -101.4% | 3.67x | Impulse / continuation | 0.504% | True breakout |
| 2026-02-27 21:00 | Valid swing, away from level | 38.2% | 11.9% | 3.67x | Flat / fading | -0.046% | Weak move without breakout |
| 2025-08-25 11:00 | Valid swing, away from level | n/a | 154.9% | 3.67x | Reversal | -0.178% | Liquidity sweep / reversal |
| 2026-09-16 17:00 | Valid swing, away from level | n/a | 369.8% | 3.67x | Flat / fading | -0.489% | Weak move without breakout |
| 2025-02-04 10:45 | Valid swing, away from level | n/a | -10.3% | 3.66x | Reversal | -0.255% | Liquidity sweep / reversal |
| 2026-09-03 12:15 | Near Fib level | 50.0% | 47.9% | 3.66x | Impulse / continuation | 0.094% | True breakout |
| 2025-03-03 22:15 | Valid swing, away from level | 38.2% | 21.6% | 3.66x | Impulse / continuation | 0.043% | True breakout |
| 2026-08-07 23:30 | Valid swing, away from level | 38.2% | 0.0% | 3.66x | Impulse -> reversal | -1.239% | False breakout |
| 2025-12-15 07:15 | Valid swing, away from level | n/a | -219.0% | 3.66x | Impulse / continuation | 0.306% | True breakout |
| 2026-04-29 16:45 | Valid swing, away from level | n/a | 197.8% | 3.66x | Reversal | 0.276% | Liquidity sweep / reversal |
| 2025-09-14 12:00 | Valid swing, away from level | n/a | 191.3% | 3.66x | Impulse / continuation | 0.164% | True breakout |
| 2025-07-11 08:00 | Valid swing, away from level | n/a | 110.2% | 3.66x | Impulse / continuation | -0.200% | True breakout |
| 2025-07-22 10:00 | Golden zone 50-61.8% | 61.8% | 59.7% | 3.66x | Reversal | -0.119% | Liquidity sweep / reversal |
| 2024-10-21 11:00 | Valid swing, away from level | n/a | -52.6% | 3.66x | Reversal | -0.039% | Liquidity sweep / reversal |
| 2026-01-14 09:00 | Valid swing, away from level | n/a | 109.3% | 3.66x | Flat / fading | 0.031% | Weak move without breakout |
| 2025-05-16 14:00 | Valid swing, away from level | n/a | 102.0% | 3.65x | Reversal | -0.065% | Liquidity sweep / reversal |
| 2025-08-19 10:00 | Valid swing, away from level | n/a | -80.3% | 3.65x | Flat / fading | -0.012% | Position building in range |
| 2025-10-13 08:15 | Valid swing, away from level | n/a | -277.3% | 3.65x | Impulse / continuation | -0.027% | True breakout |
| 2025-08-17 15:45 | Near Fib level | 78.6% | 77.8% | 3.65x | Impulse / continuation | -0.097% | True breakout |
| 2026-05-20 17:45 | Golden zone 50-61.8% | 61.8% | 61.5% | 3.65x | Flat / fading | 0.013% | Weak move without breakout |
| 2025-07-30 10:15 | Near Fib level | 61.8% | 66.1% | 3.65x | Reversal | 0.108% | Liquidity sweep / reversal |
| 2026-05-05 16:45 | Valid swing, away from level | n/a | -129.0% | 3.65x | Impulse / continuation | 0.181% | True breakout |
| 2026-09-24 10:45 | Valid swing, away from level | n/a | -6.5% | 3.65x | Reversal | -0.552% | Liquidity sweep / reversal |
| 2025-09-28 17:45 | Golden zone 50-61.8% | 61.8% | 57.1% | 3.65x | Impulse / continuation | -0.071% | True breakout |
| 2024-12-05 10:30 | Near Fib level | 61.8% | 62.8% | 3.65x | Impulse / continuation | 0.086% | True breakout |
| 2025-06-25 10:00 | Valid swing, away from level | n/a | -1.2% | 3.65x | Impulse / continuation | 0.650% | True breakout |
| 2025-02-27 07:30 | Valid swing, away from level | 78.6% | 96.9% | 3.65x | Impulse / continuation | -0.680% | True breakout |
| 2026-09-03 07:15 | Valid swing, away from level | n/a | -26.3% | 3.64x | Flat / fading | 0.086% | Weak move without breakout |
| 2026-04-17 11:00 | Valid swing, away from level | n/a | -208.7% | 3.64x | Impulse / continuation | -0.354% | True breakout |
| 2025-12-08 11:00 | Valid swing, away from level | n/a | -50.4% | 3.64x | Reversal | -0.334% | Liquidity sweep / reversal |
| 2026-07-09 10:30 | Valid swing, away from level | 78.6% | 91.8% | 3.64x | Reversal | 0.971% | Liquidity sweep / reversal |
| 2025-02-05 19:00 | Valid swing, away from level | n/a | -40.4% | 3.64x | Flat / fading | 0.353% | Weak move without breakout |
| 2025-03-20 15:15 | Valid swing, away from level | n/a | 134.9% | 3.64x | Reversal | 1.028% | Liquidity sweep / reversal |
| 2025-11-06 10:00 | Near Fib level | 78.6% | 75.4% | 3.64x | Impulse / continuation | -0.376% | True breakout |
| 2025-08-18 09:30 | Valid swing, away from level | n/a | -58.1% | 3.64x | Flat / fading | 0.114% | Weak move without breakout |
| 2024-09-30 11:00 | Valid swing, away from level | n/a | -130.8% | 3.64x | Flat / fading | -0.187% | Weak move without breakout |
| 2025-08-21 09:45 | Valid swing, away from level | n/a | -35.4% | 3.64x | Impulse / continuation | -0.387% | True breakout |
| 2024-12-06 10:45 | Valid swing, away from level | n/a | -1.3% | 3.64x | Reversal | -0.648% | Liquidity sweep / reversal |
| 2025-07-16 08:30 | Valid swing, away from level | 38.2% | 29.2% | 3.64x | Flat / fading | -0.174% | Weak move without breakout |
| 2025-04-25 09:15 | Valid swing, away from level | 38.2% | 0.6% | 3.63x | Reversal | 0.191% | Liquidity sweep / reversal |
| 2025-01-21 17:30 | Valid swing, away from level | n/a | -28.7% | 3.63x | Impulse / continuation | 0.403% | True breakout |
| 2025-11-28 18:00 | Valid swing, away from level | n/a | -163.8% | 3.63x | Impulse / continuation | 0.284% | True breakout |
| 2024-11-29 10:30 | Valid swing, away from level | 61.8% | 69.0% | 3.63x | Impulse / continuation | 0.506% | True breakout |
| 2026-02-01 13:00 | Valid swing, away from level | 61.8% | 68.6% | 3.63x | Reversal | 0.120% | Liquidity sweep / reversal |
| 2025-03-07 10:45 | Valid swing, away from level | n/a | -179.3% | 3.63x | Flat / fading | 0.046% | Weak move without breakout |
| 2025-04-29 19:30 | Valid swing, away from level | n/a | 218.6% | 3.63x | Impulse / continuation | -0.050% | True breakout |
| 2026-03-13 20:30 | Valid swing, away from level | n/a | 112.7% | 3.63x | Flat / fading | -0.024% | Weak move without breakout |
| 2026-05-05 12:15 | Valid swing, away from level | 38.2% | 5.1% | 3.63x | Impulse / continuation | 0.308% | True breakout |
| 2025-10-06 10:30 | Valid swing, away from level | n/a | 167.4% | 3.63x | Impulse / continuation | 0.181% | True breakout |
| 2025-07-23 10:15 | Valid swing, away from level | n/a | -65.1% | 3.62x | Flat / fading | -0.024% | Weak move without breakout |
| 2024-11-02 17:30 | Valid swing, away from level | n/a | 308.3% | 3.62x | Impulse / continuation | -0.199% | True breakout |
| 2025-03-18 18:00 | Valid swing, away from level | n/a | -285.7% | 3.62x | Reversal | -0.495% | Liquidity sweep / reversal |
| 2025-04-27 13:45 | Valid swing, away from level | 38.2% | 23.6% | 3.62x | Impulse / continuation | -0.042% | True breakout |
| 2026-07-07 10:00 | Near Fib level | 38.2% | 36.5% | 3.61x | Reversal | -1.371% | Liquidity sweep / reversal |
| 2025-05-22 15:45 | Valid swing, away from level | n/a | -35.7% | 3.61x | Flat / fading | 0.118% | Weak move without breakout |
| 2026-07-23 09:15 | Near Fib level | 38.2% | 33.6% | 3.60x | Reversal | -0.898% | Liquidity sweep / reversal |
| 2026-05-06 10:00 | Valid swing, away from level | n/a | 138.2% | 3.60x | Reversal | 0.175% | Liquidity sweep / reversal |
| 2025-10-20 09:15 | Valid swing, away from level | 78.6% | 70.8% | 3.60x | Reversal | 0.754% | Liquidity sweep / reversal |
| 2026-03-27 10:15 | Valid swing, away from level | n/a | -21.4% | 3.60x | Reversal | -0.254% | Liquidity sweep / reversal |
| 2025-12-04 16:45 | Valid swing, away from level | 38.2% | 26.3% | 3.60x | Impulse / continuation | -0.269% | True breakout |
| 2024-11-20 10:30 | Near Fib level | 61.8% | 64.4% | 3.60x | Impulse / continuation | -0.353% | True breakout |
| 2026-06-15 09:00 | Valid swing, away from level | n/a | -2137.5% | 3.60x | Impulse / continuation | 0.790% | True breakout |
| 2025-09-28 12:15 | Golden zone 50-61.8% | 50.0% | 54.5% | 3.59x | Flat / fading | 0.026% | Weak move without breakout |
| 2025-12-28 17:30 | Valid swing, away from level | 38.2% | 14.7% | 3.59x | Flat / fading | 0.025% | Weak move without breakout |
| 2025-02-14 10:45 | Near Fib level | 38.2% | 42.9% | 3.59x | Flat / fading | 0.221% | Weak move without breakout |
| 2025-01-23 10:00 | Valid swing, away from level | 78.6% | 88.3% | 3.59x | Reversal | 0.467% | Liquidity sweep / reversal |
| 2025-08-24 11:30 | Valid swing, away from level | n/a | 178.6% | 3.59x | Flat / fading | -0.018% | Position building in range |
| 2025-05-19 16:00 | Near Fib level | 61.8% | 63.8% | 3.59x | Impulse / continuation | -0.911% | True breakout |
| 2026-07-10 09:00 | Near Fib level | 78.6% | 81.9% | 3.59x | Impulse -> reversal | -0.134% | False breakout |
| 2026-06-02 12:00 | Valid swing, away from level | n/a | -78.3% | 3.59x | Reversal | 0.203% | Liquidity sweep / reversal |
| 2026-02-04 09:45 | Near Fib level | 38.2% | 37.4% | 3.59x | Impulse / continuation | 0.018% | True breakout |
| 2026-05-16 18:30 | Valid swing, away from level | 78.6% | 87.7% | 3.59x | Reversal | 0.226% | Liquidity sweep / reversal |
| 2025-02-20 09:15 | Valid swing, away from level | n/a | -9.6% | 3.58x | Reversal | -0.242% | Liquidity sweep / reversal |
| 2024-12-04 11:30 | Valid swing, away from level | n/a | -54.2% | 3.58x | Reversal | -0.479% | Liquidity sweep / reversal |
| 2025-11-03 07:00 | Valid swing, away from level | n/a | -47.4% | 3.58x | Flat / fading | 0.237% | Weak move without breakout |
| 2026-03-13 09:00 | Valid swing, away from level | n/a | -109.8% | 3.58x | Reversal | 0.389% | Liquidity sweep / reversal |
| 2025-02-19 17:00 | Valid swing, away from level | n/a | -12.6% | 3.58x | Impulse / continuation | 0.584% | True breakout |
| 2025-07-10 10:00 | Valid swing, away from level | n/a | -50.4% | 3.58x | Reversal | -0.131% | Liquidity sweep / reversal |
| 2026-06-04 17:45 | Valid swing, away from level | n/a | 168.9% | 3.58x | Flat / fading | 0.140% | Weak move without breakout |
| 2025-07-09 12:15 | Valid swing, away from level | 38.2% | 9.9% | 3.58x | Flat / fading | 0.126% | Weak move without breakout |
| 2026-06-05 09:00 | Valid swing, away from level | 78.6% | 86.5% | 3.58x | Flat / fading | 0.000% | Position building in range |
| 2026-04-29 16:00 | Valid swing, away from level | n/a | 164.0% | 3.58x | Impulse / continuation | -0.392% | True breakout |
| 2025-05-11 10:15 | Valid swing, away from level | n/a | -598.0% | 3.58x | Flat / fading | 0.217% | Weak move without breakout |
| 2026-05-26 19:15 | Valid swing, away from level | n/a | 107.8% | 3.57x | Reversal | 0.159% | Liquidity sweep / reversal |
| 2025-07-18 09:00 | Golden zone 50-61.8% | 61.8% | 58.9% | 3.57x | Reversal | 0.492% | Liquidity sweep / reversal |
| 2025-11-11 16:00 | Valid swing, away from level | n/a | -19.3% | 3.57x | Flat / fading | -0.020% | Position building in range |
| 2026-03-14 17:45 | Valid swing, away from level | 38.2% | 32.0% | 3.57x | Flat / fading | 0.018% | Weak move without breakout |
| 2026-09-04 11:30 | Valid swing, away from level | n/a | -95.8% | 3.57x | Flat / fading | -0.271% | Position building in range |
| 2026-08-14 14:00 | Valid swing, away from level | n/a | 206.1% | 3.57x | Reversal | 0.210% | Liquidity sweep / reversal |
| 2024-09-26 11:15 | Near Fib level | 61.8% | 64.6% | 3.57x | Flat / fading | -0.075% | Position building in range |
| 2026-09-08 09:00 | Valid swing, away from level | n/a | 138.7% | 3.57x | Impulse / continuation | -0.076% | True breakout |
| 2026-07-29 19:00 | Valid swing, away from level | n/a | -10.7% | 3.57x | Reversal | -0.194% | Liquidity sweep / reversal |
| 2025-04-24 11:00 | Valid swing, away from level | 61.8% | 68.6% | 3.57x | Reversal | 0.323% | Liquidity sweep / reversal |
| 2025-07-22 12:30 | Valid swing, away from level | n/a | 130.6% | 3.56x | Flat / fading | 0.185% | Weak move without breakout |
| 2025-09-18 15:15 | Valid swing, away from level | n/a | 208.2% | 3.56x | Flat / fading | -0.210% | Weak move without breakout |
| 2026-04-06 07:15 | Valid swing, away from level | n/a | -106.5% | 3.56x | Impulse / continuation | -0.248% | True breakout |
| 2024-09-25 12:45 | Valid swing, away from level | n/a | -388.9% | 3.56x | Impulse / continuation | -1.091% | True breakout |
| 2025-11-01 22:45 | Near Fib level | 61.8% | 64.9% | 3.56x | Reversal | -0.027% | Liquidity sweep / reversal |
| 2026-02-25 16:15 | Valid swing, away from level | 78.6% | 94.1% | 3.56x | Reversal | -0.006% | Liquidity sweep / reversal |
| 2025-03-31 09:00 | No confirmed swing | n/a | n/a | 3.56x | Flat / fading | 0.012% | Weak move without breakout |
| 2025-11-30 18:00 | Valid swing, away from level | 38.2% | 2.6% | 3.56x | Impulse / continuation | 0.224% | True breakout |
| 2026-07-27 07:30 | Valid swing, away from level | 38.2% | 27.8% | 3.56x | Impulse / continuation | 0.434% | True breakout |
| 2026-05-14 10:00 | Valid swing, away from level | 38.2% | 25.1% | 3.56x | Reversal | -0.094% | Liquidity sweep / reversal |
| 2025-12-14 11:45 | Valid swing, away from level | n/a | 165.9% | 3.56x | Impulse / continuation | -0.138% | True breakout |
| 2025-11-28 07:00 | Valid swing, away from level | 78.6% | 73.4% | 3.56x | Reversal | -0.157% | Liquidity sweep / reversal |
| 2025-10-08 11:00 | Valid swing, away from level | 78.6% | 90.4% | 3.56x | Flat / fading | -0.263% | Weak move without breakout |
| 2025-12-12 14:30 | Valid swing, away from level | n/a | 138.7% | 3.55x | Impulse / continuation | -0.093% | True breakout |
| 2025-05-30 10:00 | Valid swing, away from level | 38.2% | 44.0% | 3.55x | Flat / fading | -0.188% | Weak move without breakout |
| 2025-09-19 14:45 | Valid swing, away from level | 78.6% | 73.5% | 3.55x | Flat / fading | -0.045% | Weak move without breakout |
| 2026-02-10 10:00 | Near Fib level | 38.2% | 42.6% | 3.55x | Impulse / continuation | 0.000% | True breakout |
| 2025-09-15 10:45 | Valid swing, away from level | n/a | 280.0% | 3.55x | Impulse / continuation | -0.183% | True breakout |
| 2026-03-12 10:15 | Valid swing, away from level | n/a | -41.8% | 3.54x | Flat / fading | -0.100% | Weak move without breakout |
| 2026-01-29 07:00 | Near Fib level | 38.2% | 38.7% | 3.54x | Impulse / continuation | 0.060% | True breakout |
| 2026-01-14 17:00 | Valid swing, away from level | 38.2% | 23.4% | 3.54x | Reversal | -0.149% | Liquidity sweep / reversal |
| 2024-11-29 11:30 | Valid swing, away from level | 38.2% | 17.2% | 3.54x | Reversal | 0.503% | Liquidity sweep / reversal |
| 2025-04-25 07:00 | Near Fib level | 50.0% | 49.7% | 3.54x | Impulse / continuation | 0.347% | True breakout |
| 2025-01-10 13:00 | Valid swing, away from level | 38.2% | 14.5% | 3.54x | Impulse / continuation | 1.106% | True breakout |
| 2025-11-05 11:00 | Valid swing, away from level | n/a | -22.8% | 3.54x | Impulse / continuation | -0.053% | True breakout |
| 2026-06-15 09:45 | Valid swing, away from level | n/a | -2987.5% | 3.54x | Impulse / continuation | 0.180% | True breakout |
| 2025-07-21 10:00 | Valid swing, away from level | n/a | -123.7% | 3.54x | Impulse / continuation | -0.410% | True breakout |
| 2025-12-11 10:15 | Valid swing, away from level | n/a | -95.1% | 3.54x | Reversal | -0.074% | Liquidity sweep / reversal |
| 2025-03-10 10:00 | Valid swing, away from level | n/a | -10.7% | 3.54x | Impulse / continuation | -0.349% | True breakout |
| 2025-12-10 17:45 | Valid swing, away from level | n/a | 118.9% | 3.54x | Flat / fading | 0.025% | Position building in range |
| 2025-10-09 12:15 | Valid swing, away from level | n/a | -20.5% | 3.54x | Flat / fading | -0.436% | Weak move without breakout |
| 2025-06-10 09:00 | Valid swing, away from level | n/a | -12.3% | 3.54x | Flat / fading | -0.100% | Weak move without breakout |
| 2025-07-15 11:30 | Valid swing, away from level | n/a | -10.1% | 3.54x | Impulse / continuation | 1.347% | True breakout |
| 2025-12-21 10:00 | Golden zone 50-61.8% | 61.8% | 59.3% | 3.53x | Impulse / continuation | -0.013% | True breakout |
| 2025-04-04 13:45 | Valid swing, away from level | n/a | 144.7% | 3.53x | Flat / fading | -0.241% | Weak move without breakout |
| 2025-02-28 10:00 | Valid swing, away from level | 61.8% | 67.5% | 3.53x | Impulse / continuation | -1.978% | True breakout |
| 2024-12-04 11:15 | Valid swing, away from level | n/a | -35.1% | 3.53x | Impulse / continuation | -0.084% | True breakout |
| 2025-04-30 10:00 | Valid swing, away from level | n/a | 129.0% | 3.53x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-05-16 17:30 | Near Fib level | 50.0% | 47.4% | 3.53x | Reversal | -0.149% | Liquidity sweep / reversal |
| 2025-11-13 10:45 | Near Fib level | 61.8% | 65.2% | 3.53x | Impulse / continuation | 0.616% | True breakout |
| 2025-07-03 16:15 | Near Fib level | 50.0% | 49.0% | 3.53x | Flat / fading | 0.122% | Weak move without breakout |
| 2025-09-17 07:00 | Valid swing, away from level | 38.2% | 28.3% | 3.53x | Flat / fading | -0.051% | Position building in range |
| 2024-12-20 11:15 | Valid swing, away from level | 38.2% | 19.2% | 3.53x | Reversal | 0.088% | Liquidity sweep / reversal |
| 2025-12-21 12:15 | Valid swing, away from level | 78.6% | 96.3% | 3.53x | Impulse / continuation | -0.019% | True breakout |
| 2026-01-18 10:00 | Valid swing, away from level | 61.8% | 69.2% | 3.52x | Impulse / continuation | -0.043% | True breakout |
| 2025-11-06 20:45 | Valid swing, away from level | n/a | -36.0% | 3.52x | Flat / fading | -0.013% | Position building in range |
| 2026-03-20 10:15 | Valid swing, away from level | 38.2% | 18.4% | 3.52x | Impulse / continuation | 0.502% | True breakout |
| 2026-01-06 07:00 | Valid swing, away from level | n/a | -39.6% | 3.52x | Flat / fading | -0.049% | Position building in range |
| 2026-07-28 11:00 | Valid swing, away from level | n/a | 302.3% | 3.52x | Reversal | 0.315% | Liquidity sweep / reversal |
| 2024-12-11 11:00 | Valid swing, away from level | n/a | 149.5% | 3.52x | Impulse / continuation | 0.163% | True breakout |
| 2026-07-24 11:30 | Valid swing, away from level | n/a | 112.9% | 3.52x | Flat / fading | -0.568% | Position building in range |
| 2026-03-31 10:00 | Valid swing, away from level | 38.2% | 29.1% | 3.52x | Reversal | 0.322% | Liquidity sweep / reversal |
| 2026-07-05 10:30 | Valid swing, away from level | 38.2% | 0.0% | 3.52x | Impulse / continuation | -0.032% | True breakout |
| 2024-12-03 11:30 | Valid swing, away from level | n/a | 204.2% | 3.52x | Flat / fading | 0.025% | Position building in range |
| 2026-01-08 20:30 | Valid swing, away from level | 78.6% | 94.9% | 3.52x | Reversal | 0.019% | Liquidity sweep / reversal |
| 2025-02-06 11:45 | Valid swing, away from level | n/a | -17.2% | 3.52x | Flat / fading | 0.084% | Weak move without breakout |
| 2024-10-10 10:30 | Valid swing, away from level | n/a | -9.3% | 3.52x | Impulse / continuation | 0.078% | True breakout |
| 2025-07-25 13:15 | Golden zone 50-61.8% | 61.8% | 59.9% | 3.52x | Impulse / continuation | 0.024% | True breakout |
| 2026-04-26 17:30 | Valid swing, away from level | n/a | 146.7% | 3.52x | Flat / fading | -0.044% | Position building in range |
| 2025-09-23 10:45 | Valid swing, away from level | n/a | -49.3% | 3.51x | Impulse -> reversal | 0.180% | False breakout |
| 2026-04-02 09:00 | Near Fib level | 78.6% | 82.5% | 3.51x | Impulse / continuation | -0.099% | True breakout |
| 2025-06-25 10:15 | Valid swing, away from level | n/a | -16.5% | 3.51x | Impulse / continuation | 0.530% | True breakout |
| 2025-06-24 07:00 | Near Fib level | 38.2% | 39.5% | 3.51x | Impulse / continuation | 0.447% | True breakout |
| 2025-03-05 12:00 | Valid swing, away from level | 38.2% | 12.3% | 3.51x | Reversal | -0.306% | Liquidity sweep / reversal |
| 2026-03-10 15:45 | Near Fib level | 50.0% | 49.6% | 3.51x | Impulse / continuation | -0.380% | True breakout |
| 2026-08-21 07:00 | Golden zone 50-61.8% | 61.8% | 58.5% | 3.51x | Reversal | 0.079% | Liquidity sweep / reversal |
| 2025-04-02 07:00 | Valid swing, away from level | n/a | 129.7% | 3.51x | Flat / fading | -0.097% | Weak move without breakout |
| 2025-11-16 13:30 | Near Fib level | 61.8% | 64.9% | 3.51x | Flat / fading | -0.021% | Position building in range |
| 2026-07-21 07:00 | Valid swing, away from level | 38.2% | 7.1% | 3.50x | Reversal | -0.548% | Liquidity sweep / reversal |
| 2026-08-12 10:15 | Valid swing, away from level | 61.8% | 69.7% | 3.50x | Flat / fading | -0.064% | Weak move without breakout |
| 2025-11-05 17:15 | Near Fib level | 61.8% | 65.2% | 3.50x | Impulse / continuation | -0.342% | True breakout |
| 2026-09-06 11:30 | Valid swing, away from level | 78.6% | 73.2% | 3.50x | Reversal | 0.183% | Liquidity sweep / reversal |
| 2025-11-30 11:00 | Valid swing, away from level | n/a | -500.0% | 3.50x | Impulse / continuation | 0.058% | True breakout |
| 2025-10-19 10:45 | Valid swing, away from level | n/a | 198.2% | 3.50x | Flat / fading | -0.025% | Weak move without breakout |
| 2025-05-02 10:00 | Valid swing, away from level | n/a | 215.5% | 3.50x | Impulse / continuation | -0.686% | True breakout |
| 2025-09-17 09:00 | Valid swing, away from level | 78.6% | 72.2% | 3.50x | Impulse / continuation | -0.285% | True breakout |
| 2025-11-11 10:15 | Near Fib level | 38.2% | 36.6% | 3.50x | Impulse / continuation | 0.061% | True breakout |
| 2026-09-23 12:00 | Valid swing, away from level | n/a | 153.3% | 3.50x | Impulse / continuation | -0.320% | True breakout |
| 2025-04-30 07:45 | Valid swing, away from level | n/a | 148.5% | 3.49x | Reversal | 0.701% | Liquidity sweep / reversal |
| 2025-12-05 10:00 | Near Fib level | 38.2% | 38.6% | 3.49x | Reversal | 0.672% | Liquidity sweep / reversal |
| 2025-03-28 07:00 | Valid swing, away from level | n/a | 119.2% | 3.49x | Reversal | 0.597% | Liquidity sweep / reversal |
| 2026-06-02 11:30 | Valid swing, away from level | n/a | -118.3% | 3.49x | Reversal | 0.007% | Liquidity sweep / reversal |
| 2025-10-16 17:45 | Valid swing, away from level | n/a | -487.0% | 3.49x | Flat / fading | 0.081% | Weak move without breakout |
| 2025-06-09 09:15 | Valid swing, away from level | n/a | 383.8% | 3.49x | Reversal | 0.213% | Liquidity sweep / reversal |
| 2026-07-07 09:00 | Valid swing, away from level | n/a | 101.3% | 3.49x | Reversal | 0.641% | Liquidity sweep / reversal |
| 2024-12-04 18:15 | Valid swing, away from level | n/a | 147.0% | 3.49x | Impulse / continuation | -1.662% | True breakout |
| 2026-08-22 18:30 | Near Fib level | 78.6% | 74.3% | 3.49x | Reversal | -0.543% | Liquidity sweep / reversal |
| 2026-09-23 09:15 | Golden zone 50-61.8% | 61.8% | 60.4% | 3.49x | Impulse / continuation | 0.000% | True breakout |
| 2026-06-10 11:00 | Near Fib level | 38.2% | 35.8% | 3.49x | Flat / fading | 0.421% | Weak move without breakout |
| 2025-08-25 10:30 | Valid swing, away from level | n/a | 123.5% | 3.49x | Reversal | -0.403% | Liquidity sweep / reversal |
| 2026-07-23 10:00 | Near Fib level | 78.6% | 81.9% | 3.48x | Impulse / continuation | -0.647% | True breakout |
| 2025-12-05 12:30 | Valid swing, away from level | n/a | -205.7% | 3.48x | Reversal | -0.057% | Liquidity sweep / reversal |
| 2024-10-04 10:45 | Valid swing, away from level | n/a | -14.3% | 3.48x | Reversal | 0.288% | Liquidity sweep / reversal |
| 2026-05-17 10:15 | Valid swing, away from level | 38.2% | 26.3% | 3.48x | Flat / fading | -0.045% | Position building in range |
| 2026-03-27 08:45 | Valid swing, away from level | 78.6% | 95.7% | 3.48x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2025-11-12 15:30 | Valid swing, away from level | n/a | 271.2% | 3.48x | Flat / fading | -0.081% | Weak move without breakout |
| 2025-08-04 17:45 | Valid swing, away from level | n/a | -54.7% | 3.48x | Reversal | 0.365% | Liquidity sweep / reversal |
| 2025-10-15 10:30 | Valid swing, away from level | 78.6% | 90.8% | 3.48x | Flat / fading | -0.014% | Weak move without breakout |
| 2025-10-21 09:00 | Valid swing, away from level | n/a | 1125.0% | 3.48x | Reversal | 0.292% | Liquidity sweep / reversal |
| 2026-01-06 10:00 | Valid swing, away from level | n/a | -80.0% | 3.47x | Reversal | 0.304% | Liquidity sweep / reversal |
| 2026-04-17 10:45 | Valid swing, away from level | n/a | -218.1% | 3.47x | Reversal | -0.390% | Liquidity sweep / reversal |
| 2025-07-30 17:00 | Valid swing, away from level | n/a | 117.2% | 3.47x | Flat / fading | -0.089% | Position building in range |
| 2025-04-16 10:00 | Valid swing, away from level | n/a | 106.7% | 3.47x | Flat / fading | -0.071% | Weak move without breakout |
| 2026-02-11 09:30 | Near Fib level | 38.2% | 39.3% | 3.47x | Impulse / continuation | 0.030% | True breakout |
| 2024-11-13 11:00 | Valid swing, away from level | n/a | 167.5% | 3.47x | Impulse / continuation | 0.500% | True breakout |
| 2026-08-13 16:30 | Valid swing, away from level | n/a | 238.9% | 3.47x | Flat / fading | -0.512% | Weak move without breakout |
| 2026-04-21 23:15 | Valid swing, away from level | 78.6% | 92.1% | 3.47x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2026-03-28 18:30 | Valid swing, away from level | n/a | 100.2% | 3.46x | Flat / fading | 0.025% | Weak move without breakout |
| 2026-07-06 09:30 | Near Fib level | 50.0% | 45.9% | 3.46x | Flat / fading | -0.299% | Position building in range |
| 2025-02-04 13:15 | Valid swing, away from level | 38.2% | 14.1% | 3.46x | Impulse / continuation | -0.230% | True breakout |
| 2025-01-06 11:30 | Valid swing, away from level | n/a | 125.0% | 3.46x | Impulse / continuation | 0.194% | True breakout |
| 2025-06-01 14:45 | Valid swing, away from level | 78.6% | 87.2% | 3.46x | Flat / fading | 0.340% | Weak move without breakout |
| 2026-07-19 10:15 | Valid swing, away from level | n/a | -38.0% | 3.46x | Flat / fading | -0.219% | Position building in range |
| 2024-12-12 11:00 | Valid swing, away from level | n/a | -13.5% | 3.46x | Flat / fading | -0.170% | Weak move without breakout |
| 2025-01-29 12:30 | Valid swing, away from level | n/a | -123.9% | 3.46x | Flat / fading | -0.329% | Weak move without breakout |
| 2024-11-07 12:30 | Valid swing, away from level | 61.8% | 67.6% | 3.46x | Impulse / continuation | -0.102% | True breakout |
| 2025-08-06 10:15 | Valid swing, away from level | n/a | -15.8% | 3.46x | Impulse / continuation | -0.124% | True breakout |
| 2025-12-21 17:45 | Valid swing, away from level | 78.6% | 85.4% | 3.45x | Flat / fading | 0.069% | Weak move without breakout |
| 2025-07-01 10:15 | Valid swing, away from level | 38.2% | 5.0% | 3.45x | Impulse / continuation | 0.220% | True breakout |
| 2025-07-16 11:15 | Valid swing, away from level | 38.2% | 18.7% | 3.45x | Impulse / continuation | 0.217% | True breakout |
| 2026-07-07 08:15 | Valid swing, away from level | 78.6% | 99.8% | 3.45x | Impulse / continuation | -0.284% | True breakout |
| 2025-12-14 11:15 | Valid swing, away from level | n/a | 138.6% | 3.45x | Impulse / continuation | -0.081% | True breakout |
| 2025-09-25 10:30 | Near Fib level | 38.2% | 41.0% | 3.45x | Reversal | 0.032% | Liquidity sweep / reversal |
| 2025-01-03 10:15 | Valid swing, away from level | n/a | -75.7% | 3.45x | Reversal | -0.459% | Liquidity sweep / reversal |
| 2025-12-09 10:15 | Valid swing, away from level | 38.2% | 29.8% | 3.45x | Flat / fading | 0.088% | Weak move without breakout |
| 2024-10-21 13:15 | Valid swing, away from level | n/a | -233.3% | 3.45x | Reversal | -0.231% | Liquidity sweep / reversal |
| 2026-08-13 12:15 | Valid swing, away from level | n/a | 110.5% | 3.45x | Flat / fading | -0.015% | Position building in range |
| 2024-12-19 11:45 | Valid swing, away from level | n/a | -20.3% | 3.45x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2026-05-23 17:30 | Valid swing, away from level | 61.8% | 69.4% | 3.45x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2025-07-29 10:45 | Near Fib level | 78.6% | 80.2% | 3.45x | Reversal | 0.290% | Liquidity sweep / reversal |
| 2026-05-26 11:00 | Valid swing, away from level | 78.6% | 94.7% | 3.45x | Impulse -> reversal | 0.092% | False breakout |
| 2025-01-17 10:45 | Valid swing, away from level | 61.8% | 67.6% | 3.44x | Impulse / continuation | 0.577% | True breakout |
| 2026-02-06 13:15 | Valid swing, away from level | 38.2% | 2.5% | 3.44x | Reversal | -0.325% | Liquidity sweep / reversal |
| 2025-03-28 10:45 | Near Fib level | 50.0% | 48.1% | 3.44x | Reversal | -0.649% | Liquidity sweep / reversal |
| 2025-06-02 10:00 | Near Fib level | 38.2% | 34.8% | 3.44x | Flat / fading | 0.158% | Weak move without breakout |
| 2026-04-21 15:15 | Valid swing, away from level | n/a | 129.8% | 3.44x | Impulse / continuation | -0.351% | True breakout |
| 2025-03-28 10:15 | Near Fib level | 61.8% | 63.0% | 3.44x | Impulse / continuation | 0.507% | True breakout |
| 2025-08-13 11:00 | Golden zone 50-61.8% | 61.8% | 56.0% | 3.44x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2026-07-29 11:00 | Valid swing, away from level | n/a | -60.2% | 3.44x | Reversal | -0.203% | Liquidity sweep / reversal |
| 2025-10-10 09:15 | Near Fib level | 78.6% | 76.5% | 3.44x | Reversal | -0.163% | Liquidity sweep / reversal |
| 2025-12-05 12:15 | Valid swing, away from level | n/a | -201.1% | 3.44x | Impulse / continuation | -0.044% | True breakout |
| 2025-02-10 08:00 | Valid swing, away from level | n/a | -388.0% | 3.44x | Flat / fading | -0.140% | Weak move without breakout |
| 2025-06-25 11:15 | Valid swing, away from level | n/a | -50.8% | 3.44x | Reversal | -0.087% | Liquidity sweep / reversal |
| 2026-06-17 07:00 | Near Fib level | 78.6% | 82.5% | 3.44x | Reversal | -0.335% | Liquidity sweep / reversal |
| 2025-02-21 14:00 | Valid swing, away from level | n/a | 152.7% | 3.44x | Impulse / continuation | -0.205% | True breakout |
| 2026-03-20 23:30 | Valid swing, away from level | 78.6% | 96.2% | 3.43x | Impulse / continuation | 0.042% | True breakout |
| 2026-09-16 14:15 | Valid swing, away from level | n/a | 244.2% | 3.43x | Reversal | 0.077% | Liquidity sweep / reversal |
| 2025-10-03 08:00 | Valid swing, away from level | n/a | -19.6% | 3.43x | Reversal | -0.046% | Liquidity sweep / reversal |
| 2026-09-21 11:15 | Valid swing, away from level | n/a | 108.3% | 3.43x | Flat / fading | 0.238% | Position building in range |
| 2024-12-11 10:45 | Valid swing, away from level | n/a | 163.1% | 3.43x | Impulse / continuation | 0.111% | True breakout |
| 2025-07-28 07:15 | Valid swing, away from level | n/a | -19.5% | 3.43x | Reversal | 0.414% | Liquidity sweep / reversal |
| 2024-11-21 20:00 | Valid swing, away from level | n/a | 118.4% | 3.43x | Reversal | 1.289% | Liquidity sweep / reversal |
| 2026-01-29 09:45 | Valid swing, away from level | 38.2% | 6.5% | 3.43x | Reversal | 0.515% | Liquidity sweep / reversal |
| 2026-09-10 09:00 | Valid swing, away from level | n/a | 111.8% | 3.43x | Flat / fading | 0.216% | Weak move without breakout |
| 2024-10-03 10:45 | Valid swing, away from level | 61.8% | 68.6% | 3.43x | Impulse / continuation | 0.678% | True breakout |
| 2025-11-18 11:30 | Valid swing, away from level | n/a | -202.0% | 3.43x | Reversal | -0.470% | Liquidity sweep / reversal |
| 2025-01-06 17:00 | Valid swing, away from level | n/a | -30.8% | 3.43x | Flat / fading | -0.037% | Weak move without breakout |
| 2024-09-26 16:15 | Valid swing, away from level | n/a | 121.1% | 3.42x | Flat / fading | 0.000% | Position building in range |
| 2024-10-28 10:15 | Valid swing, away from level | n/a | 119.0% | 3.42x | Reversal | 0.634% | Liquidity sweep / reversal |
| 2025-06-25 07:00 | Valid swing, away from level | n/a | -42.0% | 3.42x | Flat / fading | -0.081% | Weak move without breakout |
| 2025-08-15 13:00 | Valid swing, away from level | n/a | -32.9% | 3.42x | Impulse / continuation | 0.227% | True breakout |
| 2025-04-12 17:45 | Valid swing, away from level | 38.2% | 1.6% | 3.42x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-01-14 07:00 | Valid swing, away from level | 61.8% | 67.4% | 3.42x | Reversal | -0.169% | Liquidity sweep / reversal |
| 2026-09-23 22:00 | Valid swing, away from level | n/a | -26.0% | 3.42x | Flat / fading | 0.131% | Weak move without breakout |
| 2025-06-01 10:45 | Valid swing, away from level | n/a | 1670.0% | 3.42x | Reversal | 0.095% | Liquidity sweep / reversal |
| 2024-10-29 10:45 | Valid swing, away from level | 78.6% | 86.0% | 3.41x | Impulse / continuation | -0.812% | True breakout |
| 2025-11-20 21:15 | Valid swing, away from level | 38.2% | 20.0% | 3.41x | Flat / fading | 0.331% | Weak move without breakout |
| 2026-08-05 19:00 | Valid swing, away from level | n/a | -110.0% | 3.41x | Impulse / continuation | 0.368% | True breakout |
| 2025-04-28 10:00 | Valid swing, away from level | n/a | 198.3% | 3.41x | Impulse / continuation | 0.103% | True breakout |
| 2025-03-24 11:00 | Valid swing, away from level | n/a | 105.5% | 3.41x | Impulse / continuation | 0.317% | True breakout |
| 2025-07-24 13:15 | Valid swing, away from level | n/a | 220.0% | 3.41x | Flat / fading | -0.145% | Weak move without breakout |
| 2026-03-24 11:00 | Valid swing, away from level | n/a | -154.1% | 3.41x | Impulse / continuation | 0.168% | True breakout |
| 2025-03-05 18:15 | Valid swing, away from level | n/a | -11.5% | 3.41x | Impulse / continuation | -0.304% | True breakout |
| 2025-04-26 17:00 | Valid swing, away from level | 38.2% | 27.6% | 3.41x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2026-09-22 07:00 | Valid swing, away from level | 38.2% | 15.9% | 3.41x | Impulse / continuation | 0.211% | True breakout |
| 2025-12-08 07:15 | Valid swing, away from level | n/a | -29.4% | 3.41x | Reversal | 0.174% | Liquidity sweep / reversal |
| 2025-01-15 10:30 | Valid swing, away from level | 38.2% | 19.8% | 3.41x | Reversal | -0.564% | Liquidity sweep / reversal |
| 2025-07-08 07:00 | Valid swing, away from level | n/a | 152.2% | 3.40x | Reversal | -0.163% | Liquidity sweep / reversal |
| 2025-06-11 10:30 | Valid swing, away from level | n/a | -47.7% | 3.40x | Flat / fading | 0.120% | Weak move without breakout |
| 2026-08-30 18:30 | Golden zone 50-61.8% | 50.0% | 50.0% | 3.40x | Reversal | -0.008% | Liquidity sweep / reversal |
| 2024-10-18 10:15 | Valid swing, away from level | n/a | 200.0% | 3.40x | Reversal | 0.253% | Liquidity sweep / reversal |
| 2024-12-18 10:30 | Valid swing, away from level | n/a | -44.7% | 3.40x | Reversal | -0.305% | Liquidity sweep / reversal |
| 2026-01-24 13:15 | Valid swing, away from level | n/a | 204.3% | 3.40x | Flat / fading | 0.217% | Position building in range |
| 2025-10-30 09:30 | Valid swing, away from level | n/a | -80.5% | 3.40x | Impulse / continuation | 0.674% | True breakout |
| 2025-08-14 21:15 | Valid swing, away from level | n/a | -13.8% | 3.40x | Flat / fading | -0.042% | Position building in range |
| 2026-08-20 10:30 | Valid swing, away from level | n/a | -15.9% | 3.40x | Flat / fading | -0.152% | Weak move without breakout |
| 2025-04-17 10:00 | Near Fib level | 61.8% | 63.5% | 3.40x | Reversal | 0.346% | Liquidity sweep / reversal |
| 2024-11-06 10:30 | Valid swing, away from level | n/a | -450.0% | 3.40x | Impulse / continuation | 0.357% | True breakout |
| 2025-08-14 10:15 | Valid swing, away from level | 78.6% | 91.1% | 3.39x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2026-07-15 12:00 | Valid swing, away from level | n/a | 556.0% | 3.39x | Flat / fading | 0.246% | Position building in range |
| 2025-07-28 15:30 | Valid swing, away from level | n/a | 221.2% | 3.39x | Impulse / continuation | -0.715% | True breakout |
| 2025-12-30 23:15 | Valid swing, away from level | n/a | 118.5% | 3.39x | Reversal | 0.018% | Liquidity sweep / reversal |
| 2025-08-06 22:00 | Valid swing, away from level | n/a | -272.4% | 3.39x | Reversal | -0.764% | Liquidity sweep / reversal |
| 2025-08-13 10:15 | Near Fib level | 38.2% | 33.3% | 3.39x | Impulse / continuation | -0.084% | True breakout |
| 2025-05-21 07:15 | Valid swing, away from level | 38.2% | 11.4% | 3.38x | Flat / fading | -0.234% | Weak move without breakout |
| 2025-01-21 18:00 | Valid swing, away from level | n/a | -53.7% | 3.38x | Flat / fading | 0.039% | Weak move without breakout |
| 2025-10-20 09:45 | Valid swing, away from level | 78.6% | 72.1% | 3.38x | Reversal | 0.882% | Liquidity sweep / reversal |
| 2025-02-19 10:00 | Golden zone 50-61.8% | 50.0% | 54.6% | 3.38x | Impulse / continuation | -0.701% | True breakout |
| 2026-02-09 10:45 | Valid swing, away from level | n/a | 313.3% | 3.38x | Impulse / continuation | -0.110% | True breakout |
| 2025-12-29 11:30 | Valid swing, away from level | n/a | -54.0% | 3.38x | Impulse / continuation | 0.826% | True breakout |
| 2026-06-28 16:15 | Valid swing, away from level | 78.6% | 91.2% | 3.38x | Impulse -> reversal | 0.120% | False breakout |
| 2025-12-25 22:00 | Valid swing, away from level | 38.2% | 23.9% | 3.38x | Impulse / continuation | 0.013% | True breakout |
| 2024-12-11 19:00 | Valid swing, away from level | 38.2% | 10.0% | 3.38x | Flat / fading | -0.017% | Weak move without breakout |
| 2024-11-07 12:45 | Golden zone 50-61.8% | 61.8% | 59.5% | 3.38x | Reversal | -0.356% | Liquidity sweep / reversal |
| 2025-05-08 09:00 | Valid swing, away from level | 38.2% | 2.6% | 3.38x | Impulse / continuation | 0.163% | True breakout |
| 2025-02-19 11:15 | Valid swing, away from level | 78.6% | 73.1% | 3.38x | Reversal | -0.035% | Liquidity sweep / reversal |
| 2026-04-21 07:00 | Golden zone 50-61.8% | 61.8% | 57.7% | 3.37x | Impulse / continuation | -0.018% | True breakout |
| 2026-06-03 07:45 | Valid swing, away from level | n/a | -36.4% | 3.37x | Flat / fading | -0.097% | Weak move without breakout |
| 2026-02-20 09:45 | Valid swing, away from level | 38.2% | 15.6% | 3.37x | Reversal | 0.199% | Liquidity sweep / reversal |
| 2025-09-11 16:45 | Valid swing, away from level | n/a | 172.3% | 3.37x | Reversal | 0.018% | Liquidity sweep / reversal |
| 2026-09-23 18:15 | Near Fib level | 38.2% | 34.1% | 3.37x | Impulse / continuation | 0.217% | True breakout |
| 2025-12-21 16:45 | Valid swing, away from level | 78.6% | 93.8% | 3.37x | Flat / fading | 0.025% | Weak move without breakout |
| 2026-04-10 07:00 | Valid swing, away from level | 38.2% | 16.4% | 3.37x | Flat / fading | -0.044% | Position building in range |
| 2025-05-13 07:00 | Valid swing, away from level | 38.2% | 14.0% | 3.37x | Reversal | 0.297% | Liquidity sweep / reversal |
| 2025-02-24 10:30 | Valid swing, away from level | 38.2% | 23.7% | 3.37x | Reversal | -0.041% | Liquidity sweep / reversal |
| 2026-04-03 11:00 | Valid swing, away from level | 78.6% | 92.1% | 3.37x | Impulse -> reversal | -0.377% | False breakout |
| 2025-05-30 12:00 | Valid swing, away from level | 38.2% | 19.4% | 3.37x | Impulse / continuation | 0.401% | True breakout |
| 2025-10-29 10:15 | Valid swing, away from level | n/a | -13.7% | 3.37x | Reversal | -0.102% | Liquidity sweep / reversal |
| 2025-09-15 09:15 | Valid swing, away from level | n/a | 200.0% | 3.36x | Flat / fading | -0.038% | Weak move without breakout |
| 2025-05-28 19:15 | Valid swing, away from level | n/a | -12.2% | 3.36x | Flat / fading | -0.105% | Weak move without breakout |
| 2025-07-17 10:15 | Golden zone 50-61.8% | 50.0% | 55.8% | 3.36x | Reversal | -0.006% | Liquidity sweep / reversal |
| 2026-02-18 11:15 | Valid swing, away from level | n/a | -49.3% | 3.36x | Impulse / continuation | -0.200% | True breakout |
| 2025-02-20 09:30 | Near Fib level | 38.2% | 33.7% | 3.36x | Flat / fading | 0.144% | Weak move without breakout |
| 2025-06-03 10:00 | Valid swing, away from level | 38.2% | 17.5% | 3.36x | Impulse / continuation | 0.530% | True breakout |
| 2025-08-22 09:00 | Near Fib level | 61.8% | 62.3% | 3.36x | Reversal | -0.030% | Liquidity sweep / reversal |
| 2026-03-24 23:15 | Near Fib level | 78.6% | 74.4% | 3.36x | Reversal | 0.150% | Liquidity sweep / reversal |
| 2026-08-04 18:15 | Valid swing, away from level | 78.6% | 71.7% | 3.36x | Flat / fading | 0.243% | Weak move without breakout |
| 2026-06-02 17:30 | Valid swing, away from level | n/a | -235.0% | 3.36x | Flat / fading | 0.098% | Weak move without breakout |
| 2025-05-14 11:15 | Near Fib level | 38.2% | 42.9% | 3.36x | Reversal | -0.063% | Liquidity sweep / reversal |
| 2026-03-02 08:00 | Near Fib level | 50.0% | 47.0% | 3.36x | Reversal | -0.151% | Liquidity sweep / reversal |
| 2025-11-09 10:00 | Golden zone 50-61.8% | 50.0% | 50.0% | 3.36x | Flat / fading | 0.027% | Position building in range |
| 2025-06-10 10:15 | Near Fib level | 50.0% | 47.4% | 3.35x | Impulse / continuation | -0.069% | True breakout |
| 2024-11-07 15:15 | Valid swing, away from level | n/a | -21.7% | 3.35x | Flat / fading | 0.059% | Weak move without breakout |
| 2025-07-24 11:30 | Valid swing, away from level | n/a | 168.6% | 3.35x | Reversal | 0.242% | Liquidity sweep / reversal |
| 2024-10-16 12:45 | Valid swing, away from level | n/a | 103.6% | 3.35x | Flat / fading | 0.038% | Weak move without breakout |
| 2026-08-03 10:00 | Valid swing, away from level | n/a | -200.0% | 3.35x | Impulse / continuation | 0.532% | True breakout |
| 2025-10-14 09:45 | Valid swing, away from level | n/a | 119.8% | 3.35x | Impulse / continuation | 0.228% | True breakout |
| 2024-10-10 10:45 | Valid swing, away from level | 38.2% | 3.1% | 3.35x | Reversal | 0.311% | Liquidity sweep / reversal |
| 2025-08-27 10:45 | Valid swing, away from level | n/a | -98.1% | 3.35x | Impulse / continuation | 0.024% | True breakout |
| 2026-03-26 09:00 | Valid swing, away from level | 38.2% | 28.9% | 3.35x | Flat / fading | -0.102% | Weak move without breakout |
| 2024-12-16 10:45 | Valid swing, away from level | n/a | 114.0% | 3.35x | Reversal | -0.729% | Liquidity sweep / reversal |
| 2025-08-01 20:00 | Valid swing, away from level | n/a | 115.3% | 3.35x | Impulse / continuation | 0.198% | True breakout |
| 2025-10-22 23:00 | Valid swing, away from level | n/a | 155.5% | 3.35x | Reversal | -1.293% | Liquidity sweep / reversal |
| 2026-02-28 12:30 | Near Fib level | 78.6% | 83.2% | 3.35x | Reversal | 0.134% | Liquidity sweep / reversal |
| 2026-07-13 17:45 | Golden zone 50-61.8% | 61.8% | 56.1% | 3.35x | Impulse / continuation | -0.391% | True breakout |
| 2025-08-13 09:15 | Near Fib level | 38.2% | 37.4% | 3.35x | Flat / fading | -0.072% | Weak move without breakout |
| 2025-05-16 10:30 | Valid swing, away from level | 78.6% | 83.8% | 3.35x | Flat / fading | 0.084% | Weak move without breakout |
| 2024-10-18 10:45 | Valid swing, away from level | n/a | 178.1% | 3.35x | Impulse / continuation | 0.097% | True breakout |
| 2026-05-21 17:30 | Valid swing, away from level | 38.2% | 9.2% | 3.34x | Reversal | 0.250% | Liquidity sweep / reversal |
| 2026-04-07 11:15 | Valid swing, away from level | n/a | -84.5% | 3.34x | Flat / fading | -0.296% | Position building in range |
| 2025-01-17 16:45 | Valid swing, away from level | n/a | -10.9% | 3.34x | Impulse / continuation | 0.524% | True breakout |
| 2025-11-15 17:45 | Valid swing, away from level | 78.6% | 85.7% | 3.34x | Reversal | -0.110% | Liquidity sweep / reversal |
| 2025-01-23 19:45 | Valid swing, away from level | 61.8% | 68.4% | 3.34x | Flat / fading | 0.180% | Weak move without breakout |
| 2025-07-15 23:30 | Near Fib level | 78.6% | 74.7% | 3.34x | Impulse / continuation | 0.042% | True breakout |
| 2026-06-13 18:30 | Near Fib level | 78.6% | 76.9% | 3.34x | Reversal | 0.054% | Liquidity sweep / reversal |
| 2026-09-15 10:00 | Valid swing, away from level | 38.2% | 43.3% | 3.34x | Reversal | -0.654% | Liquidity sweep / reversal |
| 2025-11-27 13:00 | Valid swing, away from level | n/a | 157.1% | 3.34x | Reversal | 0.188% | Liquidity sweep / reversal |
| 2025-01-30 09:30 | Valid swing, away from level | 38.2% | 4.2% | 3.34x | Flat / fading | -0.224% | Weak move without breakout |
| 2026-03-19 10:45 | Golden zone 50-61.8% | 50.0% | 50.0% | 3.34x | Reversal | 0.114% | Liquidity sweep / reversal |
| 2026-05-20 09:00 | Valid swing, away from level | n/a | 100.9% | 3.34x | Impulse / continuation | -0.223% | True breakout |
| 2025-08-08 10:00 | Valid swing, away from level | 38.2% | 32.7% | 3.34x | Impulse / continuation | -0.350% | True breakout |
| 2026-02-23 17:45 | Near Fib level | 61.8% | 64.7% | 3.34x | Reversal | 0.045% | Liquidity sweep / reversal |
| 2025-07-22 10:45 | Valid swing, away from level | n/a | 101.6% | 3.33x | Impulse / continuation | -0.197% | True breakout |
| 2025-06-24 10:00 | Valid swing, away from level | 78.6% | 87.2% | 3.33x | Reversal | 0.266% | Liquidity sweep / reversal |
| 2024-10-15 11:00 | Valid swing, away from level | n/a | -11.4% | 3.33x | Flat / fading | -0.133% | Weak move without breakout |
| 2025-07-11 08:15 | Valid swing, away from level | n/a | 114.8% | 3.33x | Impulse / continuation | -0.094% | True breakout |
| 2026-08-31 18:45 | Valid swing, away from level | n/a | -222.0% | 3.33x | Impulse / continuation | -0.564% | True breakout |
| 2025-09-22 10:45 | Valid swing, away from level | n/a | 104.8% | 3.33x | Flat / fading | -0.136% | Position building in range |
| 2026-02-16 07:45 | Valid swing, away from level | n/a | -300.0% | 3.33x | Impulse / continuation | 0.012% | True breakout |
| 2026-02-04 19:00 | Valid swing, away from level | 78.6% | 97.1% | 3.33x | Impulse / continuation | -0.382% | True breakout |
| 2026-05-18 10:00 | Valid swing, away from level | n/a | 238.3% | 3.33x | Impulse / continuation | -0.247% | True breakout |
| 2024-11-26 10:45 | Near Fib level | 50.0% | 47.0% | 3.33x | Reversal | 0.221% | Liquidity sweep / reversal |
| 2025-05-14 10:00 | Valid swing, away from level | 78.6% | 87.5% | 3.33x | Impulse / continuation | 0.063% | True breakout |
| 2026-06-08 09:15 | Valid swing, away from level | n/a | -143.5% | 3.33x | Reversal | -0.215% | Liquidity sweep / reversal |
| 2025-06-20 16:00 | Valid swing, away from level | 78.6% | 72.2% | 3.33x | Impulse / continuation | -0.176% | True breakout |
| 2025-06-01 14:15 | Valid swing, away from level | 78.6% | 87.2% | 3.33x | Impulse / continuation | 0.244% | True breakout |
| 2025-06-17 18:00 | Valid swing, away from level | n/a | -39.6% | 3.32x | Flat / fading | 0.050% | Position building in range |
| 2025-10-03 19:30 | Valid swing, away from level | n/a | 206.2% | 3.32x | Flat / fading | 0.054% | Position building in range |
| 2025-12-30 13:45 | Valid swing, away from level | 78.6% | 93.3% | 3.32x | Impulse / continuation | 0.337% | True breakout |
| 2026-06-16 09:00 | Valid swing, away from level | 78.6% | 72.7% | 3.32x | Flat / fading | -0.092% | Weak move without breakout |
| 2026-08-28 07:15 | Valid swing, away from level | n/a | -26.2% | 3.32x | Impulse / continuation | 0.458% | True breakout |
| 2025-04-18 07:00 | Near Fib level | 50.0% | 45.4% | 3.32x | Reversal | -0.176% | Liquidity sweep / reversal |
| 2025-10-01 09:00 | Valid swing, away from level | 38.2% | 16.8% | 3.32x | Impulse / continuation | 0.052% | True breakout |
| 2026-02-12 22:15 | Golden zone 50-61.8% | 50.0% | 52.8% | 3.32x | Flat / fading | -0.024% | Position building in range |
| 2025-03-12 11:15 | Valid swing, away from level | 78.6% | 73.1% | 3.32x | Reversal | -0.006% | Liquidity sweep / reversal |
| 2025-04-29 09:00 | Valid swing, away from level | n/a | 102.9% | 3.32x | Flat / fading | 0.067% | Position building in range |
| 2025-11-27 17:45 | Valid swing, away from level | n/a | 306.1% | 3.32x | Flat / fading | 0.269% | Weak move without breakout |
| 2026-08-12 10:30 | Golden zone 50-61.8% | 50.0% | 50.0% | 3.32x | Reversal | -0.381% | Liquidity sweep / reversal |
| 2025-06-27 16:30 | Valid swing, away from level | n/a | -53.8% | 3.32x | Impulse / continuation | 0.080% | True breakout |
| 2025-05-26 19:15 | Valid swing, away from level | n/a | 102.0% | 3.32x | Flat / fading | 0.338% | Position building in range |
| 2024-10-03 10:30 | Near Fib level | 78.6% | 75.5% | 3.32x | Impulse / continuation | 1.281% | True breakout |
| 2026-02-02 09:45 | Valid swing, away from level | n/a | 195.5% | 3.32x | Reversal | 0.090% | Liquidity sweep / reversal |
| 2026-07-30 12:30 | Valid swing, away from level | n/a | 103.8% | 3.32x | Flat / fading | 0.405% | Position building in range |
| 2025-05-18 18:45 | Valid swing, away from level | 38.2% | 28.8% | 3.32x | Reversal | -0.146% | Liquidity sweep / reversal |
| 2025-01-20 18:00 | Valid swing, away from level | 78.6% | 99.6% | 3.31x | Reversal | -0.100% | Liquidity sweep / reversal |
| 2025-10-14 15:45 | Valid swing, away from level | 61.8% | 66.9% | 3.31x | Reversal | -0.289% | Liquidity sweep / reversal |
| 2025-05-16 15:45 | Valid swing, away from level | n/a | 494.3% | 3.31x | Impulse -> reversal | 2.192% | False breakout |
| 2025-12-17 09:45 | Golden zone 50-61.8% | 50.0% | 52.3% | 3.31x | Impulse / continuation | -0.465% | True breakout |
| 2025-03-31 07:45 | No confirmed swing | n/a | n/a | 3.31x | Impulse / continuation | 1.230% | True breakout |
| 2026-07-12 13:45 | Valid swing, away from level | n/a | -65.1% | 3.31x | Flat / fading | -0.097% | Position building in range |
| 2025-08-20 14:00 | Near Fib level | 38.2% | 35.7% | 3.31x | Impulse / continuation | -0.012% | True breakout |
| 2025-06-17 07:00 | Valid swing, away from level | 61.8% | 68.9% | 3.31x | Reversal | 0.127% | Liquidity sweep / reversal |
| 2024-11-11 10:15 | Valid swing, away from level | n/a | -223.7% | 3.31x | Impulse / continuation | 0.728% | True breakout |
| 2025-04-26 10:00 | Valid swing, away from level | n/a | -30.8% | 3.31x | Impulse / continuation | 0.422% | True breakout |
| 2025-02-18 15:00 | Valid swing, away from level | n/a | 111.7% | 3.31x | Impulse / continuation | 0.263% | True breakout |
| 2026-03-18 16:15 | Valid swing, away from level | n/a | 122.0% | 3.30x | Impulse / continuation | -0.078% | True breakout |
| 2025-05-20 16:00 | Golden zone 50-61.8% | 50.0% | 54.0% | 3.30x | Flat / fading | -0.085% | Position building in range |
| 2025-01-17 16:30 | Valid swing, away from level | 38.2% | 17.4% | 3.30x | Impulse / continuation | 0.753% | True breakout |
| 2025-11-24 11:45 | Valid swing, away from level | n/a | 120.0% | 3.30x | Flat / fading | 0.013% | Position building in range |
| 2026-09-23 17:30 | Near Fib level | 61.8% | 65.9% | 3.30x | Reversal | 0.945% | Liquidity sweep / reversal |
| 2025-08-18 22:15 | Valid swing, away from level | n/a | -8.0% | 3.30x | Flat / fading | -0.094% | Position building in range |
| 2024-10-23 11:00 | Valid swing, away from level | n/a | 145.9% | 3.30x | Flat / fading | -0.138% | Weak move without breakout |
| 2025-12-21 10:15 | Near Fib level | 78.6% | 77.8% | 3.30x | Flat / fading | 0.019% | Weak move without breakout |
| 2025-09-29 07:45 | Valid swing, away from level | n/a | -142.9% | 3.30x | Flat / fading | -0.026% | Weak move without breakout |
| 2026-01-05 16:00 | Valid swing, away from level | n/a | -7.8% | 3.30x | Flat / fading | 0.043% | Weak move without breakout |
| 2025-11-12 07:00 | Valid swing, away from level | 38.2% | 27.3% | 3.30x | Flat / fading | 0.034% | Position building in range |
| 2026-08-26 14:30 | Valid swing, away from level | 78.6% | 98.0% | 3.30x | Flat / fading | 0.056% | Position building in range |
| 2025-09-19 12:15 | Valid swing, away from level | 78.6% | 84.2% | 3.30x | Flat / fading | -0.108% | Position building in range |
| 2025-12-08 07:30 | Valid swing, away from level | n/a | -32.8% | 3.29x | Flat / fading | -0.043% | Weak move without breakout |
| 2025-06-19 15:15 | Valid swing, away from level | 78.6% | 91.4% | 3.29x | Reversal | -0.088% | Liquidity sweep / reversal |
| 2025-08-21 09:00 | Valid swing, away from level | n/a | -77.2% | 3.29x | Impulse / continuation | -0.234% | True breakout |
| 2026-07-30 17:45 | Near Fib level | 61.8% | 63.8% | 3.29x | Reversal | -0.652% | Liquidity sweep / reversal |
| 2026-06-02 23:30 | Valid swing, away from level | n/a | -18.2% | 3.29x | Reversal | -0.104% | Liquidity sweep / reversal |
| 2026-04-30 20:30 | Near Fib level | 78.6% | 75.1% | 3.29x | Flat / fading | -0.013% | Position building in range |
| 2025-12-10 12:15 | Valid swing, away from level | 38.2% | 25.7% | 3.29x | Reversal | -0.333% | Liquidity sweep / reversal |
| 2025-03-18 08:45 | Valid swing, away from level | n/a | -162.4% | 3.29x | Flat / fading | 0.112% | Weak move without breakout |
| 2024-12-17 10:15 | Valid swing, away from level | n/a | 115.1% | 3.29x | Reversal | -0.597% | Liquidity sweep / reversal |
| 2025-05-02 18:15 | Valid swing, away from level | n/a | 250.5% | 3.29x | Impulse / continuation | -0.765% | True breakout |
| 2025-12-15 06:45 | Valid swing, away from level | n/a | -181.0% | 3.29x | Impulse / continuation | 0.106% | True breakout |
| 2026-08-03 07:45 | Valid swing, away from level | n/a | -114.0% | 3.29x | Reversal | 0.186% | Liquidity sweep / reversal |
| 2026-03-20 10:45 | Valid swing, away from level | n/a | -24.4% | 3.28x | Flat / fading | 0.208% | Weak move without breakout |
| 2025-11-26 10:30 | Near Fib level | 38.2% | 40.3% | 3.28x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-11-24 10:15 | Near Fib level | 38.2% | 34.9% | 3.28x | Reversal | -0.263% | Liquidity sweep / reversal |
| 2025-04-07 17:00 | Valid swing, away from level | n/a | -76.6% | 3.28x | Impulse / continuation | -1.773% | True breakout |
| 2026-08-07 07:00 | Valid swing, away from level | 38.2% | 13.9% | 3.28x | Impulse / continuation | 0.242% | True breakout |
| 2026-09-16 10:30 | Near Fib level | 78.6% | 75.3% | 3.28x | Reversal | -0.289% | Liquidity sweep / reversal |
| 2026-07-15 07:30 | Near Fib level | 78.6% | 78.5% | 3.28x | Reversal | -0.609% | Liquidity sweep / reversal |
| 2024-10-24 10:15 | Golden zone 50-61.8% | 61.8% | 60.7% | 3.28x | Flat / fading | 0.080% | Position building in range |
| 2026-03-16 15:45 | Valid swing, away from level | n/a | 131.4% | 3.28x | Impulse / continuation | -0.148% | True breakout |
| 2026-02-20 11:15 | Valid swing, away from level | n/a | -28.1% | 3.28x | Impulse / continuation | -0.227% | True breakout |
| 2026-04-23 15:15 | Valid swing, away from level | 38.2% | 21.3% | 3.28x | Reversal | 0.245% | Liquidity sweep / reversal |
| 2025-06-10 07:00 | Valid swing, away from level | n/a | -21.6% | 3.28x | Impulse / continuation | 0.118% | True breakout |
| 2025-10-14 09:00 | Valid swing, away from level | 61.8% | 68.7% | 3.28x | Impulse / continuation | -0.268% | True breakout |
| 2025-09-07 16:15 | Valid swing, away from level | n/a | -100.0% | 3.28x | Flat / fading | -0.012% | Weak move without breakout |
| 2025-05-22 07:00 | Valid swing, away from level | 61.8% | 67.4% | 3.28x | Reversal | -1.100% | Liquidity sweep / reversal |
| 2025-06-25 17:00 | Valid swing, away from level | n/a | -66.5% | 3.28x | Impulse / continuation | 0.118% | True breakout |
| 2026-07-14 09:00 | Valid swing, away from level | 38.2% | 6.8% | 3.28x | Reversal | 0.519% | Liquidity sweep / reversal |
| 2025-08-08 14:45 | Valid swing, away from level | 38.2% | 23.3% | 3.28x | Reversal | -0.354% | Liquidity sweep / reversal |
| 2026-07-13 17:15 | Near Fib level | 50.0% | 47.1% | 3.28x | Reversal | -0.867% | Liquidity sweep / reversal |
| 2026-09-23 07:00 | Valid swing, away from level | 38.2% | 20.8% | 3.28x | Flat / fading | -0.162% | Position building in range |
| 2026-08-14 13:45 | Valid swing, away from level | n/a | 226.7% | 3.28x | Flat / fading | -0.039% | Weak move without breakout |
| 2026-03-15 10:30 | Valid swing, away from level | n/a | -56.0% | 3.28x | Impulse / continuation | 0.006% | True breakout |
| 2025-08-31 11:30 | Valid swing, away from level | n/a | -16.4% | 3.27x | Flat / fading | -0.018% | Weak move without breakout |
| 2025-08-21 10:45 | Near Fib level | 50.0% | 48.1% | 3.27x | Impulse / continuation | -0.018% | True breakout |
| 2026-02-05 10:15 | Valid swing, away from level | 38.2% | 17.8% | 3.27x | Impulse / continuation | 0.419% | True breakout |
| 2024-11-15 11:30 | Valid swing, away from level | 38.2% | 27.9% | 3.27x | Flat / fading | 0.203% | Weak move without breakout |
| 2025-12-03 10:30 | Valid swing, away from level | 78.6% | 90.8% | 3.27x | Impulse / continuation | -0.045% | True breakout |
| 2026-08-20 09:00 | Valid swing, away from level | 38.2% | 31.8% | 3.27x | Flat / fading | 0.238% | Weak move without breakout |
| 2024-12-10 10:45 | Valid swing, away from level | n/a | 358.3% | 3.27x | Impulse / continuation | -0.135% | True breakout |
| 2026-05-07 10:15 | Golden zone 50-61.8% | 50.0% | 52.6% | 3.27x | Reversal | -0.187% | Liquidity sweep / reversal |
| 2026-04-28 07:00 | Near Fib level | 50.0% | 46.9% | 3.27x | Flat / fading | -0.031% | Position building in range |
| 2026-07-17 16:30 | Near Fib level | 61.8% | 65.4% | 3.27x | Reversal | -0.572% | Liquidity sweep / reversal |
| 2026-03-24 08:30 | Near Fib level | 38.2% | 33.3% | 3.27x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-07-16 10:00 | Valid swing, away from level | 61.8% | 69.3% | 3.27x | Impulse / continuation | -0.271% | True breakout |
| 2026-01-19 15:15 | Valid swing, away from level | n/a | -21.5% | 3.27x | Flat / fading | 0.055% | Weak move without breakout |
| 2025-11-14 15:00 | Valid swing, away from level | n/a | 216.1% | 3.27x | Flat / fading | -0.171% | Weak move without breakout |
| 2025-01-21 10:00 | Valid swing, away from level | 61.8% | 70.0% | 3.27x | Impulse / continuation | 0.649% | True breakout |
| 2025-12-24 11:30 | Valid swing, away from level | n/a | 176.1% | 3.26x | Flat / fading | 0.070% | Position building in range |
| 2026-01-15 10:30 | Near Fib level | 78.6% | 80.4% | 3.26x | Reversal | 0.025% | Liquidity sweep / reversal |
| 2025-12-02 10:00 | Near Fib level | 50.0% | 47.8% | 3.26x | Reversal | -0.153% | Liquidity sweep / reversal |
| 2025-02-26 10:30 | Valid swing, away from level | 78.6% | 91.8% | 3.26x | Reversal | -0.285% | Liquidity sweep / reversal |
| 2024-11-13 19:30 | Valid swing, away from level | n/a | 119.6% | 3.26x | Flat / fading | 0.222% | Weak move without breakout |
| 2026-02-27 10:15 | Valid swing, away from level | n/a | 225.0% | 3.26x | Flat / fading | 0.081% | Weak move without breakout |
| 2024-11-01 10:30 | Valid swing, away from level | 38.2% | 28.4% | 3.26x | Reversal | -0.693% | Liquidity sweep / reversal |
| 2024-12-04 19:00 | Valid swing, away from level | n/a | 229.8% | 3.26x | Flat / fading | 0.079% | Position building in range |
| 2026-02-22 13:00 | Valid swing, away from level | n/a | -520.0% | 3.26x | Flat / fading | -0.051% | Weak move without breakout |
| 2026-01-16 10:45 | Valid swing, away from level | n/a | -97.3% | 3.26x | Impulse / continuation | 0.501% | True breakout |
| 2025-04-24 10:00 | Golden zone 50-61.8% | 61.8% | 56.9% | 3.26x | Reversal | -0.198% | Liquidity sweep / reversal |
| 2026-01-31 13:15 | Near Fib level | 61.8% | 63.6% | 3.26x | Flat / fading | -0.036% | Position building in range |
| 2026-01-23 16:45 | Valid swing, away from level | 78.6% | 89.5% | 3.26x | Flat / fading | 0.042% | Position building in range |
| 2025-07-30 10:30 | Golden zone 50-61.8% | 61.8% | 61.8% | 3.26x | Impulse / continuation | -0.070% | True breakout |
| 2025-12-24 11:15 | Valid swing, away from level | n/a | 218.3% | 3.26x | Flat / fading | 0.159% | Weak move without breakout |
| 2026-08-24 08:00 | Valid swing, away from level | n/a | 223.7% | 3.26x | Reversal | -0.541% | Liquidity sweep / reversal |
| 2026-03-04 16:15 | Valid swing, away from level | 61.8% | 68.5% | 3.25x | Impulse / continuation | -0.489% | True breakout |
| 2025-05-27 09:45 | Valid swing, away from level | n/a | -24.7% | 3.25x | Flat / fading | 0.151% | Weak move without breakout |
| 2025-05-14 16:45 | Valid swing, away from level | n/a | -92.0% | 3.25x | Flat / fading | -0.207% | Weak move without breakout |
| 2025-06-05 10:00 | Valid swing, away from level | 38.2% | 3.1% | 3.25x | Flat / fading | -0.223% | Weak move without breakout |
| 2025-05-17 15:45 | Valid swing, away from level | 38.2% | 12.3% | 3.25x | Reversal | -0.058% | Liquidity sweep / reversal |
| 2026-03-13 11:15 | Valid swing, away from level | n/a | -373.2% | 3.25x | Flat / fading | -0.135% | Position building in range |
| 2024-12-10 10:30 | Valid swing, away from level | n/a | 162.1% | 3.25x | Reversal | -0.327% | Liquidity sweep / reversal |
| 2025-04-29 17:45 | Valid swing, away from level | n/a | 103.7% | 3.25x | Impulse / continuation | -0.055% | True breakout |
| 2026-06-16 15:45 | Valid swing, away from level | n/a | 521.7% | 3.25x | Reversal | -0.301% | Liquidity sweep / reversal |
| 2026-09-08 11:45 | Valid swing, away from level | n/a | 166.0% | 3.25x | Impulse / continuation | 0.304% | True breakout |
| 2025-02-24 23:30 | Valid swing, away from level | n/a | -8.5% | 3.25x | Impulse / continuation | 0.133% | True breakout |
| 2025-10-31 07:15 | Near Fib level | 38.2% | 36.0% | 3.25x | Flat / fading | -0.100% | Weak move without breakout |
| 2026-09-09 08:30 | Valid swing, away from level | n/a | 106.1% | 3.25x | Impulse / continuation | -0.214% | True breakout |
| 2024-12-24 11:00 | Valid swing, away from level | n/a | 194.9% | 3.25x | Reversal | 1.021% | Liquidity sweep / reversal |
| 2025-10-15 09:45 | Golden zone 50-61.8% | 61.8% | 61.2% | 3.24x | Reversal | -0.262% | Liquidity sweep / reversal |
| 2026-09-05 14:45 | Near Fib level | 50.0% | 47.6% | 3.24x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-04-25 10:30 | Valid swing, away from level | n/a | -19.6% | 3.24x | Reversal | -0.148% | Liquidity sweep / reversal |
| 2025-03-04 10:00 | Valid swing, away from level | n/a | -87.3% | 3.24x | Impulse / continuation | 1.654% | True breakout |
| 2026-08-14 12:15 | Valid swing, away from level | n/a | 139.9% | 3.24x | Impulse / continuation | -0.903% | True breakout |
| 2025-06-11 07:00 | Valid swing, away from level | 38.2% | 29.9% | 3.24x | Reversal | -0.563% | Liquidity sweep / reversal |
| 2025-12-12 14:45 | Valid swing, away from level | n/a | 150.0% | 3.24x | Flat / fading | -0.025% | Position building in range |
| 2025-09-03 16:15 | Valid swing, away from level | n/a | -7.4% | 3.24x | Reversal | -0.157% | Liquidity sweep / reversal |
| 2025-01-20 21:15 | Valid swing, away from level | n/a | 110.5% | 3.24x | Flat / fading | 0.392% | Position building in range |
| 2026-03-14 18:45 | Valid swing, away from level | 38.2% | 20.0% | 3.24x | Impulse / continuation | 0.112% | True breakout |
| 2025-11-25 12:00 | Valid swing, away from level | n/a | 145.6% | 3.24x | Reversal | 0.046% | Liquidity sweep / reversal |
| 2025-04-17 11:30 | Valid swing, away from level | n/a | -35.9% | 3.24x | Reversal | -0.025% | Liquidity sweep / reversal |
| 2026-01-30 20:30 | Valid swing, away from level | n/a | 104.6% | 3.24x | Impulse / continuation | -0.072% | True breakout |
| 2025-11-25 11:45 | Valid swing, away from level | n/a | 136.7% | 3.24x | Impulse / continuation | 0.176% | True breakout |
| 2026-05-20 09:45 | Valid swing, away from level | n/a | 120.5% | 3.23x | Flat / fading | -0.166% | Weak move without breakout |
| 2025-05-05 13:45 | Valid swing, away from level | 78.6% | 93.8% | 3.23x | Impulse / continuation | -0.571% | True breakout |
| 2025-06-09 09:00 | Valid swing, away from level | n/a | 294.7% | 3.23x | Reversal | 0.168% | Liquidity sweep / reversal |
| 2025-08-05 12:00 | Valid swing, away from level | 38.2% | 8.8% | 3.23x | Impulse / continuation | -0.199% | True breakout |
| 2025-08-11 18:30 | Valid swing, away from level | 78.6% | 88.1% | 3.23x | Impulse / continuation | -0.090% | True breakout |
| 2024-09-25 11:30 | Valid swing, away from level | n/a | -12.2% | 3.23x | Impulse / continuation | 4.019% | True breakout |
| 2025-11-11 10:45 | Valid swing, away from level | 38.2% | 9.7% | 3.23x | Reversal | -0.148% | Liquidity sweep / reversal |
| 2026-01-27 11:00 | Valid swing, away from level | n/a | 119.6% | 3.23x | Reversal | 0.139% | Liquidity sweep / reversal |
| 2025-06-28 10:00 | Valid swing, away from level | n/a | -59.1% | 3.23x | Flat / fading | 0.031% | Position building in range |
| 2025-03-11 10:30 | Valid swing, away from level | 38.2% | 20.0% | 3.23x | Impulse / continuation | -0.035% | True breakout |
| 2025-02-14 11:00 | Near Fib level | 38.2% | 42.9% | 3.23x | Reversal | -0.244% | Liquidity sweep / reversal |
| 2025-12-01 10:00 | Golden zone 50-61.8% | 61.8% | 58.5% | 3.23x | Impulse / continuation | 0.038% | True breakout |
| 2025-03-28 15:00 | Valid swing, away from level | n/a | 170.1% | 3.23x | Flat / fading | 0.224% | Position building in range |
| 2026-08-20 13:15 | Valid swing, away from level | n/a | 143.2% | 3.23x | Reversal | -0.303% | Liquidity sweep / reversal |
| 2026-05-27 10:00 | Valid swing, away from level | 38.2% | 10.3% | 3.22x | Reversal | -0.586% | Liquidity sweep / reversal |
| 2026-02-03 07:00 | Valid swing, away from level | n/a | -37.1% | 3.22x | Impulse / continuation | 0.276% | True breakout |
| 2026-05-22 18:30 | Valid swing, away from level | n/a | 148.1% | 3.22x | Flat / fading | 0.045% | Position building in range |
| 2026-04-20 08:45 | Valid swing, away from level | n/a | -124.1% | 3.22x | Reversal | -0.306% | Liquidity sweep / reversal |
| 2025-12-15 09:30 | Valid swing, away from level | n/a | -542.9% | 3.22x | Flat / fading | -0.062% | Weak move without breakout |
| 2026-04-06 09:00 | Valid swing, away from level | n/a | -21.7% | 3.22x | Impulse / continuation | -0.155% | True breakout |
| 2025-10-24 09:00 | Valid swing, away from level | n/a | -3.8% | 3.22x | Flat / fading | -0.149% | Weak move without breakout |
| 2025-09-23 10:00 | Valid swing, away from level | n/a | -92.0% | 3.22x | Reversal | -0.416% | Liquidity sweep / reversal |
| 2025-11-07 17:15 | Valid swing, away from level | 38.2% | 4.9% | 3.22x | Flat / fading | -0.141% | Position building in range |
| 2026-06-10 10:30 | Valid swing, away from level | 38.2% | 21.9% | 3.22x | Reversal | -0.466% | Liquidity sweep / reversal |
| 2026-08-18 12:30 | Valid swing, away from level | n/a | -118.3% | 3.22x | Reversal | 0.015% | Liquidity sweep / reversal |
| 2024-11-26 15:15 | Valid swing, away from level | n/a | 144.9% | 3.22x | Flat / fading | -0.451% | Weak move without breakout |
| 2026-07-06 15:15 | Near Fib level | 78.6% | 82.6% | 3.22x | Impulse / continuation | -0.950% | True breakout |
| 2025-07-31 09:15 | Near Fib level | 61.8% | 63.6% | 3.21x | Impulse / continuation | 0.000% | True breakout |
| 2026-03-25 07:00 | Golden zone 50-61.8% | 61.8% | 58.3% | 3.21x | Reversal | 0.348% | Liquidity sweep / reversal |
| 2025-12-19 11:00 | Valid swing, away from level | 38.2% | 15.3% | 3.21x | Flat / fading | 0.000% | Position building in range |
| 2025-09-13 17:30 | Valid swing, away from level | n/a | 110.1% | 3.21x | Flat / fading | 0.031% | Weak move without breakout |
| 2026-06-17 11:45 | Valid swing, away from level | n/a | 109.1% | 3.21x | Flat / fading | 0.108% | Weak move without breakout |
| 2026-02-13 12:15 | Valid swing, away from level | 38.2% | 31.1% | 3.21x | Impulse -> reversal | -0.180% | False breakout |
| 2024-09-26 10:15 | Valid swing, away from level | 78.6% | 73.2% | 3.21x | Reversal | 0.507% | Liquidity sweep / reversal |
| 2026-03-25 15:30 | Golden zone 50-61.8% | 50.0% | 50.6% | 3.21x | Reversal | -0.054% | Liquidity sweep / reversal |
| 2026-07-15 10:15 | Valid swing, away from level | n/a | 280.0% | 3.20x | Impulse / continuation | -0.381% | True breakout |
| 2025-03-25 17:00 | Valid swing, away from level | n/a | 128.7% | 3.20x | Impulse -> reversal | 0.870% | False breakout |
| 2026-07-10 11:15 | Valid swing, away from level | n/a | 146.1% | 3.20x | Impulse / continuation | -0.223% | True breakout |
| 2026-08-22 12:30 | Valid swing, away from level | 78.6% | 89.0% | 3.20x | Reversal | 0.016% | Liquidity sweep / reversal |
| 2025-06-27 07:00 | Near Fib level | 38.2% | 38.2% | 3.20x | Flat / fading | -0.031% | Weak move without breakout |
| 2025-02-17 18:30 | Valid swing, away from level | 38.2% | 0.4% | 3.20x | Flat / fading | -0.103% | Weak move without breakout |
| 2026-05-08 09:00 | Valid swing, away from level | 78.6% | 92.4% | 3.20x | Impulse / continuation | -0.052% | True breakout |
| 2024-12-25 11:15 | Valid swing, away from level | 78.6% | 72.4% | 3.20x | Impulse / continuation | 0.589% | True breakout |
| 2026-09-09 09:30 | Valid swing, away from level | n/a | 120.3% | 3.20x | Flat / fading | 0.092% | Weak move without breakout |
| 2026-01-06 22:45 | Valid swing, away from level | n/a | -8.9% | 3.20x | Impulse / continuation | 0.261% | True breakout |
| 2025-09-17 09:30 | Valid swing, away from level | n/a | 127.7% | 3.19x | Impulse -> reversal | -0.006% | False breakout |
| 2025-09-02 09:30 | Valid swing, away from level | 78.6% | 96.6% | 3.19x | Impulse / continuation | -0.318% | True breakout |
| 2024-11-26 11:00 | Valid swing, away from level | 38.2% | 28.8% | 3.19x | Flat / fading | -0.380% | Weak move without breakout |
| 2026-03-15 18:45 | Valid swing, away from level | n/a | -222.2% | 3.19x | Impulse / continuation | 0.271% | True breakout |
| 2025-09-24 10:00 | Near Fib level | 38.2% | 34.1% | 3.19x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-08-07 08:00 | Valid swing, away from level | n/a | -13.9% | 3.19x | Reversal | -0.569% | Liquidity sweep / reversal |
| 2025-06-19 10:00 | Valid swing, away from level | 38.2% | 31.6% | 3.19x | Impulse / continuation | 0.450% | True breakout |
| 2026-03-17 16:15 | Valid swing, away from level | n/a | 290.6% | 3.19x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2026-07-28 09:15 | Valid swing, away from level | n/a | -55.2% | 3.19x | Reversal | -1.231% | Liquidity sweep / reversal |
| 2026-04-21 10:15 | Valid swing, away from level | n/a | -2.0% | 3.19x | Reversal | -0.172% | Liquidity sweep / reversal |
| 2026-02-05 10:30 | Valid swing, away from level | n/a | -17.8% | 3.19x | Impulse / continuation | 0.347% | True breakout |
| 2025-10-08 14:00 | Valid swing, away from level | n/a | 425.3% | 3.18x | Impulse / continuation | -0.349% | True breakout |
| 2026-04-02 23:00 | Near Fib level | 38.2% | 40.3% | 3.18x | Flat / fading | 0.123% | Weak move without breakout |
| 2026-08-21 11:45 | Valid swing, away from level | 38.2% | 2.5% | 3.18x | Reversal | 0.314% | Liquidity sweep / reversal |
| 2026-07-20 10:00 | Near Fib level | 61.8% | 65.8% | 3.18x | Reversal | -1.112% | Liquidity sweep / reversal |
| 2026-08-25 10:15 | Near Fib level | 38.2% | 41.0% | 3.18x | Impulse / continuation | -0.048% | True breakout |
| 2025-11-28 17:45 | Valid swing, away from level | n/a | -108.6% | 3.18x | Impulse / continuation | 0.692% | True breakout |
| 2025-03-21 14:15 | Valid swing, away from level | n/a | 119.4% | 3.18x | Impulse / continuation | -0.166% | True breakout |
| 2026-04-28 09:45 | Valid swing, away from level | n/a | 138.2% | 3.18x | Flat / fading | -0.069% | Weak move without breakout |
| 2026-03-26 11:15 | Valid swing, away from level | n/a | 213.2% | 3.18x | Impulse -> reversal | 0.018% | False breakout |
| 2026-03-17 16:45 | Valid swing, away from level | n/a | 269.8% | 3.18x | Reversal | -0.184% | Liquidity sweep / reversal |
| 2025-11-10 10:15 | Valid swing, away from level | n/a | -34.8% | 3.18x | Flat / fading | -0.040% | Weak move without breakout |
| 2026-01-18 18:30 | Near Fib level | 61.8% | 66.7% | 3.18x | Impulse / continuation | 0.129% | True breakout |
| 2025-12-08 15:30 | Valid swing, away from level | n/a | 138.2% | 3.18x | Reversal | 0.225% | Liquidity sweep / reversal |
| 2025-06-13 18:15 | Near Fib level | 78.6% | 83.2% | 3.18x | Impulse / continuation | -0.273% | True breakout |
| 2024-10-24 11:30 | Near Fib level | 50.0% | 47.9% | 3.18x | Reversal | -0.679% | Liquidity sweep / reversal |
| 2025-04-21 13:15 | Valid swing, away from level | n/a | -87.9% | 3.18x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-11-14 10:00 | Valid swing, away from level | 38.2% | 1.7% | 3.18x | Reversal | -0.182% | Liquidity sweep / reversal |
| 2025-12-25 10:45 | Valid swing, away from level | 78.6% | 71.4% | 3.17x | Impulse / continuation | 0.564% | True breakout |
| 2026-06-24 10:45 | Valid swing, away from level | n/a | 137.3% | 3.17x | Reversal | 0.212% | Liquidity sweep / reversal |
| 2025-03-18 07:15 | Valid swing, away from level | n/a | -121.5% | 3.17x | Flat / fading | 0.101% | Weak move without breakout |
| 2024-11-14 11:15 | Valid swing, away from level | 38.2% | 43.2% | 3.17x | Impulse / continuation | 0.446% | True breakout |
| 2025-12-08 10:30 | Valid swing, away from level | n/a | -37.8% | 3.17x | Impulse / continuation | 0.143% | True breakout |
| 2024-12-24 11:30 | Valid swing, away from level | n/a | 120.3% | 3.17x | Impulse / continuation | 0.399% | True breakout |
| 2026-08-25 18:00 | Valid swing, away from level | n/a | -185.9% | 3.17x | Impulse / continuation | -0.755% | True breakout |
| 2026-02-26 10:00 | Valid swing, away from level | n/a | -70.0% | 3.17x | Flat / fading | 0.091% | Weak move without breakout |
| 2025-08-06 11:45 | Near Fib level | 50.0% | 48.7% | 3.17x | Flat / fading | 0.068% | Position building in range |
| 2025-09-23 11:00 | Valid swing, away from level | n/a | -5.3% | 3.17x | Reversal | 0.483% | Liquidity sweep / reversal |
| 2026-03-02 10:00 | Valid swing, away from level | 61.8% | 68.2% | 3.17x | Impulse / continuation | 0.454% | True breakout |
| 2025-11-06 11:00 | Valid swing, away from level | 78.6% | 95.1% | 3.17x | Reversal | -0.505% | Liquidity sweep / reversal |
| 2026-05-22 10:00 | Valid swing, away from level | n/a | -26.1% | 3.17x | Impulse / continuation | -0.089% | True breakout |
| 2025-03-07 17:45 | Near Fib level | 78.6% | 75.9% | 3.17x | Reversal | -0.798% | Liquidity sweep / reversal |
| 2025-08-24 10:15 | Valid swing, away from level | n/a | 164.3% | 3.17x | Impulse / continuation | -0.071% | True breakout |
| 2026-07-08 16:00 | Near Fib level | 78.6% | 78.1% | 3.17x | Flat / fading | 0.425% | Position building in range |
| 2025-05-13 11:00 | Valid swing, away from level | 38.2% | 32.0% | 3.17x | Impulse / continuation | -0.342% | True breakout |
| 2025-04-07 09:30 | Valid swing, away from level | n/a | 410.7% | 3.17x | Reversal | 3.014% | Liquidity sweep / reversal |
| 2026-02-04 12:30 | Near Fib level | 50.0% | 46.4% | 3.16x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-05-22 17:45 | Valid swing, away from level | n/a | 132.1% | 3.16x | Impulse / continuation | -0.135% | True breakout |
| 2026-07-22 08:45 | Near Fib level | 38.2% | 38.5% | 3.16x | Impulse / continuation | -0.187% | True breakout |
| 2025-04-01 13:45 | Valid swing, away from level | n/a | -12.5% | 3.16x | Impulse / continuation | -1.133% | True breakout |
| 2025-09-23 09:45 | Valid swing, away from level | n/a | -93.3% | 3.16x | Reversal | -0.211% | Liquidity sweep / reversal |
| 2024-10-21 10:45 | Valid swing, away from level | n/a | -47.4% | 3.16x | Flat / fading | -0.058% | Weak move without breakout |
| 2025-08-20 10:30 | Valid swing, away from level | n/a | -65.5% | 3.16x | Flat / fading | 0.035% | Weak move without breakout |
| 2024-12-23 10:45 | Valid swing, away from level | n/a | -67.4% | 3.16x | Impulse / continuation | 0.383% | True breakout |
| 2026-03-01 17:00 | Near Fib level | 50.0% | 46.2% | 3.16x | Flat / fading | -0.035% | Weak move without breakout |
| 2025-05-02 15:30 | Valid swing, away from level | n/a | 104.1% | 3.16x | Flat / fading | 0.032% | Position building in range |
| 2025-08-24 10:30 | Valid swing, away from level | n/a | 153.6% | 3.16x | Reversal | -0.041% | Liquidity sweep / reversal |
| 2025-03-26 10:15 | Valid swing, away from level | 38.2% | 27.6% | 3.16x | Reversal | 0.139% | Liquidity sweep / reversal |
| 2025-08-06 20:15 | Valid swing, away from level | n/a | -117.8% | 3.16x | Flat / fading | 0.197% | Position building in range |
| 2025-08-22 09:30 | Near Fib level | 61.8% | 62.8% | 3.16x | Flat / fading | -0.089% | Weak move without breakout |
| 2024-10-23 20:30 | Valid swing, away from level | n/a | 190.2% | 3.16x | Flat / fading | -0.160% | Weak move without breakout |
| 2025-01-23 12:30 | Valid swing, away from level | 78.6% | 98.8% | 3.15x | Flat / fading | 0.441% | Position building in range |
| 2025-08-18 21:45 | Valid swing, away from level | n/a | -3.4% | 3.15x | Impulse / continuation | 0.171% | True breakout |
| 2025-10-14 09:30 | Valid swing, away from level | n/a | 141.8% | 3.15x | Reversal | 0.221% | Liquidity sweep / reversal |
| 2025-07-16 12:15 | Valid swing, away from level | n/a | -15.0% | 3.15x | Impulse / continuation | 0.786% | True breakout |
| 2026-05-31 10:00 | Valid swing, away from level | 38.2% | 12.5% | 3.15x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2025-08-21 11:00 | Valid swing, away from level | n/a | 101.3% | 3.15x | Reversal | 0.401% | Liquidity sweep / reversal |
| 2026-02-05 07:00 | Near Fib level | 78.6% | 81.6% | 3.15x | Impulse / continuation | -0.120% | True breakout |
| 2024-12-06 10:15 | Valid swing, away from level | 38.2% | 19.7% | 3.15x | Reversal | 0.365% | Liquidity sweep / reversal |
| 2026-08-06 07:30 | Valid swing, away from level | n/a | -332.5% | 3.15x | Impulse / continuation | -0.100% | True breakout |
| 2026-06-15 09:30 | Valid swing, away from level | n/a | -2575.0% | 3.15x | Impulse / continuation | 0.294% | True breakout |
| 2026-07-02 08:15 | Valid swing, away from level | 78.6% | 84.9% | 3.15x | Impulse / continuation | -0.125% | True breakout |
| 2026-06-13 18:45 | Valid swing, away from level | 61.8% | 69.2% | 3.15x | Impulse / continuation | 0.034% | True breakout |
| 2025-01-30 16:00 | Valid swing, away from level | n/a | -27.3% | 3.15x | Impulse / continuation | -0.059% | True breakout |
| 2025-11-25 07:00 | Golden zone 50-61.8% | 61.8% | 61.5% | 3.15x | Reversal | 0.117% | Liquidity sweep / reversal |
| 2025-05-12 09:00 | Valid swing, away from level | n/a | -0.8% | 3.14x | Flat / fading | 0.038% | Weak move without breakout |
| 2026-09-01 20:45 | Valid swing, away from level | 78.6% | 96.0% | 3.14x | Impulse / continuation | -0.643% | True breakout |
| 2025-07-30 16:30 | Valid swing, away from level | n/a | 154.5% | 3.14x | Reversal | 0.217% | Liquidity sweep / reversal |
| 2025-02-27 23:00 | Valid swing, away from level | n/a | 121.7% | 3.14x | Impulse / continuation | -0.772% | True breakout |
| 2026-01-09 07:30 | Valid swing, away from level | n/a | -68.9% | 3.14x | Flat / fading | 0.080% | Weak move without breakout |
| 2025-04-08 19:45 | Valid swing, away from level | n/a | 163.6% | 3.14x | Reversal | 0.893% | Liquidity sweep / reversal |
| 2025-10-16 20:00 | Valid swing, away from level | n/a | -933.3% | 3.14x | Impulse / continuation | 0.843% | True breakout |
| 2025-10-13 07:45 | Valid swing, away from level | n/a | -336.4% | 3.14x | Reversal | -0.260% | Liquidity sweep / reversal |
| 2025-09-18 10:15 | Near Fib level | 78.6% | 75.4% | 3.14x | Reversal | -0.139% | Liquidity sweep / reversal |
| 2026-07-01 07:00 | Valid swing, away from level | 38.2% | 9.5% | 3.14x | Reversal | 0.125% | Liquidity sweep / reversal |
| 2025-10-14 15:30 | Valid swing, away from level | 78.6% | 84.4% | 3.14x | Flat / fading | 0.035% | Weak move without breakout |
| 2025-04-21 19:30 | Valid swing, away from level | n/a | -41.9% | 3.14x | Flat / fading | -0.303% | Position building in range |
| 2025-02-27 23:15 | Valid swing, away from level | n/a | 132.9% | 3.14x | Impulse / continuation | 0.123% | True breakout |
| 2025-10-03 19:00 | Valid swing, away from level | n/a | 115.5% | 3.14x | Impulse / continuation | -0.573% | True breakout |
| 2025-02-18 15:30 | Valid swing, away from level | n/a | 146.2% | 3.14x | Reversal | 1.153% | Liquidity sweep / reversal |
| 2026-07-11 18:45 | Valid swing, away from level | 78.6% | 97.8% | 3.14x | Reversal | 0.194% | Liquidity sweep / reversal |
| 2026-08-27 10:30 | Valid swing, away from level | n/a | 115.2% | 3.14x | Reversal | 1.744% | Liquidity sweep / reversal |
| 2025-12-03 17:30 | Valid swing, away from level | n/a | -24.5% | 3.14x | Impulse / continuation | 0.368% | True breakout |
| 2025-08-25 08:30 | Golden zone 50-61.8% | 50.0% | 50.9% | 3.14x | Reversal | -0.053% | Liquidity sweep / reversal |
| 2026-02-07 18:15 | Valid swing, away from level | 38.2% | 22.1% | 3.14x | Reversal | 0.225% | Liquidity sweep / reversal |
| 2025-10-30 07:15 | Valid swing, away from level | n/a | 138.7% | 3.14x | Flat / fading | 0.096% | Weak move without breakout |
| 2024-11-18 17:15 | Valid swing, away from level | n/a | -28.5% | 3.14x | Impulse / continuation | 1.164% | True breakout |
| 2025-07-28 10:00 | Valid swing, away from level | n/a | -311.1% | 3.14x | Impulse / continuation | 0.074% | True breakout |
| 2024-11-28 10:15 | Valid swing, away from level | n/a | -12.5% | 3.13x | Reversal | 1.388% | Liquidity sweep / reversal |
| 2025-08-08 13:30 | Near Fib level | 78.6% | 75.0% | 3.13x | Impulse / continuation | 0.260% | True breakout |
| 2025-03-30 13:00 | No confirmed swing | n/a | n/a | 3.13x | Flat / fading | 0.000% | Position building in range |
| 2026-07-08 10:00 | Valid swing, away from level | 38.2% | 28.3% | 3.13x | Impulse / continuation | 0.102% | True breakout |
| 2026-06-22 22:00 | Valid swing, away from level | n/a | 169.6% | 3.13x | Impulse / continuation | 1.297% | True breakout |
| 2026-07-17 07:15 | Valid swing, away from level | 78.6% | 98.4% | 3.13x | Flat / fading | 0.146% | Weak move without breakout |
| 2026-05-21 17:45 | Valid swing, away from level | n/a | -15.6% | 3.13x | Flat / fading | 0.070% | Weak move without breakout |
| 2025-04-07 17:30 | Valid swing, away from level | n/a | -54.4% | 3.13x | Flat / fading | -0.643% | Weak move without breakout |
| 2025-01-09 10:45 | Valid swing, away from level | n/a | -14.7% | 3.13x | Impulse / continuation | -0.679% | True breakout |
| 2026-04-26 18:30 | Valid swing, away from level | n/a | 193.3% | 3.13x | Reversal | 0.012% | Liquidity sweep / reversal |
| 2024-10-31 10:15 | Valid swing, away from level | n/a | 235.4% | 3.13x | Reversal | 0.514% | Liquidity sweep / reversal |
| 2026-05-11 20:30 | Near Fib level | 38.2% | 42.0% | 3.13x | Impulse / continuation | 0.206% | True breakout |
| 2025-04-01 14:45 | Valid swing, away from level | 38.2% | 28.2% | 3.13x | Flat / fading | 0.048% | Weak move without breakout |
| 2026-04-10 13:15 | Valid swing, away from level | 50.0% | 44.6% | 3.12x | Impulse / continuation | 0.433% | True breakout |
| 2024-11-11 12:00 | Valid swing, away from level | n/a | -252.6% | 3.12x | Flat / fading | 0.275% | Position building in range |
| 2025-07-14 19:00 | Valid swing, away from level | n/a | -77.2% | 3.12x | Flat / fading | -0.229% | Weak move without breakout |
| 2026-07-19 10:00 | Valid swing, away from level | n/a | -10.0% | 3.12x | Impulse / continuation | 0.185% | True breakout |
| 2025-07-10 15:45 | Valid swing, away from level | 38.2% | 15.8% | 3.12x | Impulse / continuation | 0.213% | True breakout |
| 2025-09-26 09:00 | Golden zone 50-61.8% | 50.0% | 53.9% | 3.12x | Flat / fading | -0.186% | Weak move without breakout |
| 2026-04-27 15:00 | Near Fib level | 78.6% | 74.0% | 3.12x | Flat / fading | -0.106% | Weak move without breakout |
| 2025-12-10 17:00 | Golden zone 50-61.8% | 61.8% | 56.8% | 3.12x | Reversal | -0.235% | Liquidity sweep / reversal |
| 2025-10-22 10:00 | Golden zone 50-61.8% | 50.0% | 51.4% | 3.12x | Reversal | -0.033% | Liquidity sweep / reversal |
| 2026-02-22 18:45 | Near Fib level | 50.0% | 45.7% | 3.12x | Impulse / continuation | 0.080% | True breakout |
| 2026-06-10 13:00 | Valid swing, away from level | 38.2% | 10.3% | 3.11x | Flat / fading | -0.275% | Position building in range |
| 2025-09-29 11:00 | Valid swing, away from level | n/a | -482.6% | 3.11x | Impulse / continuation | 0.274% | True breakout |
| 2026-05-28 14:45 | Valid swing, away from level | 38.2% | 13.4% | 3.11x | Impulse / continuation | -0.518% | True breakout |
| 2024-12-25 12:00 | Golden zone 50-61.8% | 61.8% | 60.6% | 3.11x | Impulse / continuation | 0.201% | True breakout |
| 2024-11-02 10:45 | Valid swing, away from level | n/a | -23.4% | 3.11x | Reversal | -0.281% | Liquidity sweep / reversal |
| 2026-03-29 17:15 | Valid swing, away from level | n/a | -284.6% | 3.11x | Flat / fading | 0.019% | Weak move without breakout |
| 2025-02-17 18:00 | Valid swing, away from level | n/a | -14.9% | 3.11x | Impulse / continuation | -0.034% | True breakout |
| 2025-05-19 20:30 | Near Fib level | 50.0% | 49.1% | 3.11x | Reversal | -0.965% | Liquidity sweep / reversal |
| 2025-11-07 10:15 | Valid swing, away from level | n/a | -32.1% | 3.11x | Reversal | -0.389% | Liquidity sweep / reversal |
| 2025-07-08 19:30 | Valid swing, away from level | n/a | 131.7% | 3.11x | Impulse / continuation | -0.302% | True breakout |
| 2025-05-19 08:45 | Valid swing, away from level | n/a | 328.8% | 3.11x | Flat / fading | 0.302% | Weak move without breakout |
| 2025-09-03 19:00 | Valid swing, away from level | n/a | -40.7% | 3.11x | Flat / fading | 0.078% | Weak move without breakout |
| 2024-12-20 15:15 | Valid swing, away from level | n/a | -1821.9% | 3.11x | Flat / fading | 0.668% | Weak move without breakout |
| 2025-01-29 10:15 | Valid swing, away from level | 38.2% | 30.5% | 3.11x | Impulse / continuation | 0.666% | True breakout |
| 2026-05-01 17:00 | Near Fib level | 61.8% | 62.8% | 3.11x | Impulse / continuation | -0.013% | True breakout |
| 2026-04-27 07:30 | Valid swing, away from level | n/a | 193.3% | 3.11x | Reversal | 0.387% | Liquidity sweep / reversal |
| 2025-01-06 10:45 | Valid swing, away from level | n/a | 220.6% | 3.11x | Reversal | 1.004% | Liquidity sweep / reversal |
| 2025-09-17 13:45 | Valid swing, away from level | 38.2% | 43.6% | 3.11x | Reversal | -0.095% | Liquidity sweep / reversal |
| 2025-06-24 11:15 | Valid swing, away from level | n/a | 108.4% | 3.10x | Flat / fading | 0.178% | Position building in range |
| 2025-05-22 09:30 | Valid swing, away from level | n/a | 330.0% | 3.10x | Impulse / continuation | 1.972% | True breakout |
| 2025-06-16 10:30 | Valid swing, away from level | 38.2% | 23.4% | 3.10x | Impulse / continuation | -0.280% | True breakout |
| 2025-07-23 11:00 | Valid swing, away from level | n/a | -60.6% | 3.10x | Flat / fading | -0.095% | Weak move without breakout |
| 2026-03-18 10:00 | Valid swing, away from level | n/a | -15.2% | 3.10x | Reversal | 0.268% | Liquidity sweep / reversal |
| 2025-10-08 12:00 | Valid swing, away from level | n/a | 138.6% | 3.10x | Impulse / continuation | -0.442% | True breakout |
| 2026-03-06 10:00 | Valid swing, away from level | 38.2% | 10.5% | 3.10x | Impulse / continuation | 0.170% | True breakout |
| 2025-09-29 07:15 | Valid swing, away from level | n/a | -71.4% | 3.10x | Reversal | 0.083% | Liquidity sweep / reversal |
| 2025-03-04 07:00 | Valid swing, away from level | n/a | -37.1% | 3.10x | Flat / fading | 0.290% | Weak move without breakout |
| 2026-04-20 18:30 | Near Fib level | 38.2% | 41.7% | 3.10x | Flat / fading | 0.018% | Weak move without breakout |
| 2025-01-17 11:00 | Valid swing, away from level | n/a | -14.7% | 3.10x | Impulse / continuation | 0.341% | True breakout |
| 2024-12-16 13:45 | Valid swing, away from level | n/a | 177.6% | 3.10x | Flat / fading | -0.143% | Weak move without breakout |
| 2025-07-22 12:00 | Valid swing, away from level | n/a | 230.6% | 3.10x | Reversal | 0.461% | Liquidity sweep / reversal |
| 2025-03-03 22:45 | Valid swing, away from level | n/a | -18.3% | 3.10x | Impulse / continuation | -0.630% | True breakout |
| 2026-04-24 11:45 | Valid swing, away from level | n/a | 130.4% | 3.09x | Impulse / continuation | -0.031% | True breakout |
| 2026-01-15 12:45 | Valid swing, away from level | n/a | 122.8% | 3.09x | Reversal | 0.288% | Liquidity sweep / reversal |
| 2026-06-02 10:00 | Near Fib level | 38.2% | 34.7% | 3.09x | Reversal | 0.639% | Liquidity sweep / reversal |
| 2025-03-12 10:00 | Near Fib level | 38.2% | 36.9% | 3.09x | Reversal | -0.620% | Liquidity sweep / reversal |
| 2026-07-29 18:15 | Valid swing, away from level | 38.2% | 1.1% | 3.09x | Impulse / continuation | -0.037% | True breakout |
| 2026-07-21 07:15 | Valid swing, away from level | 38.2% | 15.9% | 3.09x | Impulse / continuation | 0.125% | True breakout |
| 2026-06-01 08:15 | Valid swing, away from level | n/a | -471.4% | 3.09x | Impulse / continuation | 0.152% | True breakout |
| 2025-10-20 08:15 | Valid swing, away from level | 38.2% | 20.8% | 3.09x | Reversal | -0.382% | Liquidity sweep / reversal |
| 2026-06-26 15:30 | Valid swing, away from level | n/a | -107.6% | 3.09x | Flat / fading | -0.561% | Weak move without breakout |
| 2025-08-05 12:15 | Valid swing, away from level | 38.2% | 29.0% | 3.09x | Flat / fading | 0.150% | Weak move without breakout |
| 2025-10-08 09:45 | Near Fib level | 38.2% | 42.2% | 3.09x | Impulse / continuation | -0.204% | True breakout |
| 2025-03-28 10:30 | Golden zone 50-61.8% | 61.8% | 57.5% | 3.09x | Flat / fading | 0.041% | Weak move without breakout |
| 2026-01-06 23:30 | Valid swing, away from level | n/a | -62.5% | 3.09x | Reversal | -1.321% | Liquidity sweep / reversal |
| 2025-03-05 10:00 | Golden zone 50-61.8% | 50.0% | 53.1% | 3.09x | Impulse -> reversal | 0.262% | False breakout |
| 2026-01-30 11:45 | Valid swing, away from level | n/a | 156.4% | 3.09x | Flat / fading | 0.204% | Weak move without breakout |
| 2026-09-10 12:00 | Valid swing, away from level | n/a | -56.7% | 3.08x | Flat / fading | -0.069% | Position building in range |
| 2026-04-27 09:15 | Valid swing, away from level | n/a | 513.3% | 3.08x | Reversal | 0.295% | Liquidity sweep / reversal |
| 2025-06-13 09:00 | Golden zone 50-61.8% | 61.8% | 59.4% | 3.08x | Impulse / continuation | -0.536% | True breakout |
| 2024-10-17 10:45 | Valid swing, away from level | n/a | -16.7% | 3.08x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-09-26 10:45 | Valid swing, away from level | 61.8% | 68.3% | 3.08x | Flat / fading | 0.026% | Weak move without breakout |
| 2024-10-14 13:30 | Valid swing, away from level | n/a | -9.1% | 3.08x | Flat / fading | 0.058% | Position building in range |
| 2026-07-14 10:15 | Valid swing, away from level | n/a | -41.7% | 3.08x | Impulse / continuation | -0.167% | True breakout |
| 2026-08-19 07:15 | Valid swing, away from level | n/a | -22.3% | 3.08x | Reversal | -0.450% | Liquidity sweep / reversal |
| 2026-05-28 15:00 | Valid swing, away from level | 78.6% | 71.1% | 3.08x | Impulse / continuation | -0.474% | True breakout |
| 2025-06-20 16:15 | Valid swing, away from level | 78.6% | 98.7% | 3.08x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-02-11 10:15 | Near Fib level | 61.8% | 66.3% | 3.07x | Impulse / continuation | 0.164% | True breakout |
| 2026-07-15 08:45 | Valid swing, away from level | n/a | 115.1% | 3.07x | Reversal | -0.056% | Liquidity sweep / reversal |
| 2026-08-31 08:45 | Valid swing, away from level | n/a | -163.6% | 3.07x | Reversal | 0.008% | Liquidity sweep / reversal |
| 2025-03-13 19:15 | Valid swing, away from level | n/a | -33.3% | 3.07x | Flat / fading | -0.170% | Weak move without breakout |
| 2024-10-16 11:30 | Near Fib level | 38.2% | 41.8% | 3.07x | Impulse / continuation | -0.247% | True breakout |
| 2026-02-05 11:00 | Valid swing, away from level | n/a | -23.3% | 3.07x | Reversal | 0.239% | Liquidity sweep / reversal |
| 2026-04-10 18:00 | Valid swing, away from level | 61.8% | 67.3% | 3.07x | Flat / fading | 0.252% | Weak move without breakout |
| 2025-09-25 10:00 | Valid swing, away from level | 38.2% | 22.1% | 3.07x | Impulse / continuation | -0.369% | True breakout |
| 2025-12-03 18:15 | Valid swing, away from level | n/a | -69.4% | 3.07x | Impulse / continuation | 0.013% | True breakout |
| 2025-10-13 11:15 | Valid swing, away from level | n/a | 303.7% | 3.07x | Flat / fading | -0.193% | Position building in range |
| 2025-12-08 20:45 | Valid swing, away from level | 78.6% | 96.6% | 3.07x | Impulse / continuation | -0.395% | True breakout |
| 2026-01-14 10:30 | Valid swing, away from level | n/a | 103.9% | 3.07x | Reversal | 0.539% | Liquidity sweep / reversal |
| 2024-10-14 13:15 | Valid swing, away from level | 38.2% | 12.1% | 3.07x | Flat / fading | 0.175% | Weak move without breakout |
| 2026-07-15 09:00 | Valid swing, away from level | n/a | 119.9% | 3.06x | Reversal | -0.032% | Liquidity sweep / reversal |
| 2025-08-07 11:30 | Valid swing, away from level | n/a | -30.6% | 3.06x | Impulse / continuation | 0.101% | True breakout |
| 2025-03-10 10:30 | Valid swing, away from level | 38.2% | 24.9% | 3.06x | Flat / fading | -0.129% | Weak move without breakout |
| 2025-05-07 19:00 | Valid swing, away from level | 38.2% | 22.6% | 3.06x | Reversal | -0.431% | Liquidity sweep / reversal |
| 2025-09-02 21:45 | Valid swing, away from level | 78.6% | 93.3% | 3.06x | Impulse / continuation | 0.315% | True breakout |
| 2026-01-26 10:00 | Near Fib level | 78.6% | 75.2% | 3.06x | Reversal | -0.054% | Liquidity sweep / reversal |
| 2025-09-18 15:00 | Valid swing, away from level | n/a | 282.0% | 3.06x | Reversal | 0.159% | Liquidity sweep / reversal |
| 2026-06-25 11:00 | Valid swing, away from level | 38.2% | 43.4% | 3.06x | Flat / fading | -0.228% | Weak move without breakout |
| 2025-10-07 08:45 | Valid swing, away from level | n/a | -15.7% | 3.06x | Reversal | -0.572% | Liquidity sweep / reversal |
| 2026-07-16 07:30 | Valid swing, away from level | n/a | 115.5% | 3.06x | Impulse / continuation | -0.091% | True breakout |
| 2025-09-23 10:30 | Valid swing, away from level | n/a | -84.0% | 3.06x | Impulse / continuation | -0.154% | True breakout |
| 2026-01-15 19:30 | Valid swing, away from level | 38.2% | 27.6% | 3.06x | Flat / fading | 0.100% | Position building in range |
| 2024-11-08 11:00 | Valid swing, away from level | n/a | -598.5% | 3.06x | Reversal | -1.065% | Liquidity sweep / reversal |
| 2024-12-28 11:45 | Valid swing, away from level | n/a | -102.8% | 3.06x | Reversal | -0.113% | Liquidity sweep / reversal |
| 2026-06-03 10:30 | Valid swing, away from level | n/a | 108.7% | 3.06x | Impulse / continuation | -0.157% | True breakout |
| 2025-11-30 11:15 | Valid swing, away from level | n/a | -557.1% | 3.06x | Impulse / continuation | 0.038% | True breakout |
| 2025-07-23 19:00 | Valid swing, away from level | 78.6% | 71.3% | 3.05x | Impulse / continuation | -0.168% | True breakout |
| 2026-09-16 13:00 | Valid swing, away from level | n/a | 164.0% | 3.05x | Impulse / continuation | -0.321% | True breakout |
| 2026-06-01 10:15 | Valid swing, away from level | n/a | -564.7% | 3.05x | Impulse / continuation | 0.033% | True breakout |
| 2025-08-20 10:00 | Valid swing, away from level | n/a | -29.8% | 3.05x | Reversal | 0.105% | Liquidity sweep / reversal |
| 2025-02-21 13:45 | Valid swing, away from level | 78.6% | 95.3% | 3.05x | Reversal | -0.548% | Liquidity sweep / reversal |
| 2025-07-14 09:00 | Valid swing, away from level | n/a | 115.7% | 3.05x | Reversal | 1.795% | Liquidity sweep / reversal |
| 2024-10-29 22:00 | Valid swing, away from level | n/a | -24.8% | 3.05x | Reversal | -0.605% | Liquidity sweep / reversal |
| 2026-06-05 10:15 | Valid swing, away from level | 78.6% | 86.5% | 3.05x | Impulse / continuation | -0.227% | True breakout |
| 2026-07-07 12:30 | Valid swing, away from level | n/a | -242.6% | 3.05x | Reversal | -0.857% | Liquidity sweep / reversal |
| 2024-10-14 12:45 | Near Fib level | 50.0% | 48.5% | 3.05x | Impulse / continuation | 0.529% | True breakout |
| 2026-04-23 08:15 | Valid swing, away from level | n/a | -9.0% | 3.05x | Flat / fading | -0.055% | Weak move without breakout |
| 2025-11-27 07:00 | Valid swing, away from level | 78.6% | 91.5% | 3.05x | Flat / fading | 0.065% | Weak move without breakout |
| 2026-06-26 12:30 | Valid swing, away from level | 78.6% | 72.5% | 3.05x | Reversal | -1.346% | Liquidity sweep / reversal |
| 2025-12-26 10:00 | Valid swing, away from level | n/a | -425.7% | 3.05x | Impulse / continuation | 0.319% | True breakout |
| 2026-01-23 11:15 | Valid swing, away from level | 38.2% | 6.6% | 3.05x | Impulse / continuation | 0.072% | True breakout |
| 2026-04-03 11:15 | Valid swing, away from level | 61.8% | 67.4% | 3.05x | Reversal | -0.567% | Liquidity sweep / reversal |
| 2025-07-10 14:00 | Near Fib level | 61.8% | 64.2% | 3.05x | Reversal | -0.170% | Liquidity sweep / reversal |
| 2025-03-31 10:00 | Valid swing, away from level | n/a | -160.6% | 3.05x | Reversal | -0.789% | Liquidity sweep / reversal |
| 2025-09-15 11:30 | Valid swing, away from level | n/a | 342.0% | 3.05x | Reversal | -0.082% | Liquidity sweep / reversal |
| 2024-09-27 10:45 | Valid swing, away from level | n/a | -14.3% | 3.04x | Impulse / continuation | 0.647% | True breakout |
| 2026-04-02 11:00 | Near Fib level | 50.0% | 48.1% | 3.04x | Flat / fading | -0.228% | Weak move without breakout |
| 2025-04-13 17:00 | Valid swing, away from level | n/a | -22.7% | 3.04x | Reversal | -0.094% | Liquidity sweep / reversal |
| 2026-02-16 13:15 | Valid swing, away from level | n/a | -1163.3% | 3.04x | Reversal | -0.481% | Liquidity sweep / reversal |
| 2026-08-21 10:00 | Near Fib level | 61.8% | 63.9% | 3.04x | Impulse / continuation | -0.236% | True breakout |
| 2025-12-22 12:45 | Valid swing, away from level | n/a | 178.6% | 3.04x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-12-22 10:30 | Valid swing, away from level | n/a | 225.0% | 3.04x | Reversal | 0.051% | Liquidity sweep / reversal |
| 2025-05-23 10:00 | Near Fib level | 61.8% | 63.6% | 3.04x | Reversal | 0.241% | Liquidity sweep / reversal |
| 2025-05-26 07:15 | Valid swing, away from level | n/a | 157.7% | 3.04x | Impulse / continuation | -0.458% | True breakout |
| 2025-08-25 09:30 | Near Fib level | 61.8% | 62.7% | 3.04x | Reversal | -0.184% | Liquidity sweep / reversal |
| 2025-01-31 16:45 | Valid swing, away from level | n/a | 106.5% | 3.04x | Impulse / continuation | -0.249% | True breakout |
| 2026-02-10 10:45 | Valid swing, away from level | 38.2% | 29.6% | 3.04x | Impulse / continuation | -0.206% | True breakout |
| 2025-02-05 11:15 | Valid swing, away from level | 78.6% | 70.3% | 3.04x | Flat / fading | 0.187% | Weak move without breakout |
| 2025-09-13 17:15 | Valid swing, away from level | 78.6% | 89.9% | 3.04x | Impulse / continuation | 0.006% | True breakout |
| 2025-12-12 11:30 | Valid swing, away from level | n/a | 118.6% | 3.04x | Impulse / continuation | -0.049% | True breakout |
| 2026-03-04 11:45 | Valid swing, away from level | n/a | -13.6% | 3.04x | Flat / fading | -0.035% | Weak move without breakout |
| 2025-03-27 10:30 | Valid swing, away from level | n/a | 424.5% | 3.04x | Reversal | -0.188% | Liquidity sweep / reversal |
| 2026-05-26 20:15 | Valid swing, away from level | 78.6% | 90.8% | 3.04x | Impulse / continuation | 0.278% | True breakout |
| 2026-07-29 09:30 | Valid swing, away from level | 38.2% | 15.1% | 3.04x | Reversal | 0.129% | Liquidity sweep / reversal |
| 2025-04-01 07:30 | Valid swing, away from level | n/a | -23.1% | 3.03x | Impulse / continuation | -0.100% | True breakout |
| 2026-03-17 16:30 | Valid swing, away from level | n/a | 313.2% | 3.03x | Reversal | 0.024% | Liquidity sweep / reversal |
| 2025-09-08 15:15 | Valid swing, away from level | n/a | -15.0% | 3.03x | Impulse / continuation | 0.018% | True breakout |
| 2025-07-14 11:00 | Valid swing, away from level | n/a | -270.4% | 3.03x | Flat / fading | 0.290% | Weak move without breakout |
| 2025-10-23 07:00 | Valid swing, away from level | n/a | 182.3% | 3.03x | Flat / fading | -0.362% | Position building in range |
| 2025-02-20 09:45 | Valid swing, away from level | 38.2% | 8.7% | 3.03x | Reversal | -0.317% | Liquidity sweep / reversal |
| 2026-08-27 07:00 | Near Fib level | 78.6% | 81.2% | 3.03x | Reversal | -0.200% | Liquidity sweep / reversal |
| 2026-03-19 09:00 | Valid swing, away from level | n/a | -1.9% | 3.03x | Impulse / continuation | -0.185% | True breakout |
| 2026-05-29 14:30 | Near Fib level | 78.6% | 75.2% | 3.03x | Reversal | -0.212% | Liquidity sweep / reversal |
| 2026-02-02 10:00 | Valid swing, away from level | n/a | 238.6% | 3.03x | Reversal | -0.024% | Liquidity sweep / reversal |
| 2026-03-31 12:15 | Valid swing, away from level | n/a | -318.2% | 3.03x | Reversal | 0.576% | Liquidity sweep / reversal |
| 2026-01-20 10:15 | Valid swing, away from level | 78.6% | 83.8% | 3.03x | Impulse / continuation | -0.170% | True breakout |
| 2025-06-19 15:00 | Valid swing, away from level | 78.6% | 92.7% | 3.03x | Flat / fading | 0.019% | Weak move without breakout |
| 2025-06-04 10:15 | Valid swing, away from level | n/a | -186.2% | 3.03x | Reversal | 0.049% | Liquidity sweep / reversal |
| 2025-10-22 23:15 | Valid swing, away from level | n/a | 112.0% | 3.03x | Reversal | -0.995% | Liquidity sweep / reversal |
| 2025-12-09 14:00 | Valid swing, away from level | n/a | -47.3% | 3.03x | Impulse / continuation | 0.424% | True breakout |
| 2026-01-12 09:30 | Valid swing, away from level | 38.2% | 16.2% | 3.03x | Impulse / continuation | 0.117% | True breakout |
| 2025-05-12 08:15 | Valid swing, away from level | 38.2% | 1.9% | 3.03x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-01-27 13:45 | Valid swing, away from level | n/a | -6.3% | 3.02x | Impulse / continuation | 0.138% | True breakout |
| 2025-04-17 07:00 | Near Fib level | 50.0% | 49.5% | 3.02x | Impulse / continuation | 0.113% | True breakout |
| 2025-06-19 10:45 | Valid swing, away from level | n/a | -27.4% | 3.02x | Reversal | -0.044% | Liquidity sweep / reversal |
| 2026-08-11 07:00 | Valid swing, away from level | n/a | -37.7% | 3.02x | Impulse / continuation | 0.430% | True breakout |
| 2026-02-04 16:15 | Near Fib level | 61.8% | 65.2% | 3.02x | Reversal | 0.065% | Liquidity sweep / reversal |
| 2026-01-19 08:00 | Valid swing, away from level | n/a | -79.2% | 3.02x | Reversal | -0.110% | Liquidity sweep / reversal |
| 2026-03-30 17:00 | Valid swing, away from level | n/a | 173.0% | 3.02x | Reversal | 1.014% | Liquidity sweep / reversal |
| 2026-02-03 10:15 | Valid swing, away from level | n/a | -473.2% | 3.02x | Impulse / continuation | 0.237% | True breakout |
| 2025-07-16 09:00 | Near Fib level | 38.2% | 43.1% | 3.02x | Impulse / continuation | -0.217% | True breakout |
| 2026-04-07 21:00 | Valid swing, away from level | n/a | 103.8% | 3.02x | Flat / fading | 0.019% | Position building in range |
| 2025-11-27 09:00 | Valid swing, away from level | n/a | -4.3% | 3.02x | Reversal | -0.064% | Liquidity sweep / reversal |
| 2025-12-05 10:45 | Valid swing, away from level | n/a | -84.1% | 3.02x | Reversal | 0.242% | Liquidity sweep / reversal |
| 2026-01-19 09:30 | Valid swing, away from level | n/a | -58.3% | 3.02x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-09-15 07:30 | Valid swing, away from level | n/a | -6.0% | 3.01x | Flat / fading | 0.094% | Position building in range |
| 2026-02-12 07:00 | Golden zone 50-61.8% | 50.0% | 54.1% | 3.01x | Flat / fading | 0.000% | Position building in range |
| 2026-03-31 07:15 | Valid swing, away from level | 38.2% | 17.4% | 3.01x | Reversal | 0.099% | Liquidity sweep / reversal |
| 2025-06-24 21:15 | Valid swing, away from level | 38.2% | 5.7% | 3.01x | Flat / fading | 0.220% | Weak move without breakout |
| 2025-09-30 12:15 | Valid swing, away from level | n/a | 345.5% | 3.01x | Flat / fading | -0.079% | Weak move without breakout |
| 2026-02-16 23:15 | Near Fib level | 38.2% | 34.7% | 3.01x | Impulse / continuation | 0.494% | True breakout |
| 2025-05-16 13:15 | Near Fib level | 78.6% | 82.4% | 3.01x | Impulse / continuation | 0.032% | True breakout |
| 2026-08-31 07:15 | Golden zone 50-61.8% | 50.0% | 54.5% | 3.01x | Impulse / continuation | 0.208% | True breakout |
| 2026-05-24 17:15 | Valid swing, away from level | 38.2% | 22.2% | 3.01x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-12-25 19:00 | Near Fib level | 38.2% | 37.3% | 3.01x | Flat / fading | 0.063% | Weak move without breakout |
| 2024-10-01 11:00 | Valid swing, away from level | n/a | 233.3% | 3.01x | Reversal | -0.826% | Liquidity sweep / reversal |
| 2024-11-08 19:00 | Valid swing, away from level | n/a | -40.5% | 3.01x | Flat / fading | 0.016% | Position building in range |
| 2025-01-14 12:00 | Valid swing, away from level | 38.2% | 32.4% | 3.01x | Flat / fading | 0.723% | Weak move without breakout |
| 2025-06-06 11:15 | Valid swing, away from level | n/a | -104.2% | 3.01x | Flat / fading | -0.036% | Weak move without breakout |
| 2026-08-28 17:45 | Valid swing, away from level | n/a | 112.5% | 3.01x | Flat / fading | 0.161% | Weak move without breakout |
| 2025-07-24 11:15 | Valid swing, away from level | n/a | 127.6% | 3.01x | Impulse -> reversal | -0.024% | False breakout |
| 2025-05-30 13:00 | Valid swing, away from level | n/a | -14.1% | 3.01x | Flat / fading | -0.025% | Position building in range |
| 2026-04-21 22:45 | Valid swing, away from level | 78.6% | 93.6% | 3.01x | Impulse / continuation | 0.037% | True breakout |
| 2025-11-05 08:45 | Valid swing, away from level | n/a | 139.3% | 3.00x | Impulse / continuation | 0.208% | True breakout |
| 2026-02-09 10:15 | Valid swing, away from level | n/a | 286.7% | 3.00x | Reversal | -0.171% | Liquidity sweep / reversal |
| 2024-10-11 10:45 | Near Fib level | 38.2% | 33.3% | 3.00x | Flat / fading | 0.058% | Weak move without breakout |
| 2026-03-10 07:00 | Valid swing, away from level | n/a | -44.4% | 3.00x | Reversal | 0.246% | Liquidity sweep / reversal |
| 2025-09-09 10:45 | Valid swing, away from level | n/a | -45.1% | 3.00x | Reversal | 0.071% | Liquidity sweep / reversal |
| 2026-09-06 18:15 | Near Fib level | 78.6% | 74.5% | 3.00x | Reversal | -0.572% | Liquidity sweep / reversal |
| 2026-08-14 11:45 | Valid swing, away from level | 78.6% | 99.4% | 3.00x | Impulse / continuation | -0.924% | True breakout |
| 2026-06-10 09:45 | Valid swing, away from level | 38.2% | 25.6% | 3.00x | Reversal | 0.291% | Liquidity sweep / reversal |
| 2026-05-04 07:45 | Valid swing, away from level | n/a | -219.1% | 3.00x | Flat / fading | -0.208% | Weak move without breakout |
| 2026-05-25 10:15 | Valid swing, away from level | 38.2% | 14.6% | 3.00x | Flat / fading | 0.039% | Weak move without breakout |
| 2025-09-28 18:00 | Valid swing, away from level | n/a | 135.7% | 3.00x | Reversal | 0.122% | Liquidity sweep / reversal |
| 2026-08-14 13:00 | Valid swing, away from level | n/a | 175.0% | 3.00x | Impulse / continuation | -0.709% | True breakout |
| 2025-09-30 10:30 | Valid swing, away from level | n/a | 102.7% | 3.00x | Impulse -> reversal | -0.429% | False breakout |
| 2026-05-06 10:30 | Valid swing, away from level | n/a | 196.3% | 3.00x | Reversal | 1.081% | Liquidity sweep / reversal |
| 2024-12-27 16:30 | Near Fib level | 78.6% | 76.3% | 3.00x | Impulse / continuation | -0.076% | True breakout |
| 2025-11-09 14:45 | Near Fib level | 50.0% | 45.7% | 3.00x | Reversal | 0.007% | Liquidity sweep / reversal |
| 2026-03-03 09:00 | Near Fib level | 61.8% | 63.9% | 3.00x | Impulse / continuation | -0.585% | True breakout |
| 2025-03-31 07:30 | No confirmed swing | n/a | n/a | 3.00x | Reversal | 2.223% | Liquidity sweep / reversal |
| 2026-08-31 17:45 | Near Fib level | 50.0% | 48.8% | 3.00x | Impulse / continuation | 1.771% | True breakout |
| 2025-04-28 21:45 | Near Fib level | 78.6% | 80.9% | 2.99x | Flat / fading | 0.092% | Weak move without breakout |
| 2025-01-28 15:45 | Valid swing, away from level | n/a | -72.2% | 2.99x | Flat / fading | -0.067% | Weak move without breakout |
| 2025-11-08 15:00 | Valid swing, away from level | 38.2% | 29.1% | 2.99x | Reversal | -0.047% | Liquidity sweep / reversal |
| 2026-04-19 14:45 | Valid swing, away from level | n/a | -26.3% | 2.99x | Flat / fading | -0.018% | Position building in range |
| 2026-01-15 10:00 | Near Fib level | 78.6% | 74.8% | 2.99x | Impulse / continuation | 0.050% | True breakout |
| 2025-12-04 09:00 | Valid swing, away from level | n/a | -70.1% | 2.99x | Flat / fading | -0.179% | Position building in range |
| 2026-09-09 12:30 | Valid swing, away from level | n/a | 127.5% | 2.99x | Flat / fading | -0.123% | Weak move without breakout |
| 2026-01-22 17:00 | Valid swing, away from level | n/a | 166.3% | 2.99x | Reversal | 0.319% | Liquidity sweep / reversal |
| 2025-03-14 10:00 | Near Fib level | 50.0% | 49.9% | 2.99x | Flat / fading | -0.030% | Weak move without breakout |
| 2026-04-07 14:45 | Valid swing, away from level | n/a | 100.4% | 2.99x | Flat / fading | 0.131% | Weak move without breakout |
| 2026-08-10 08:00 | Valid swing, away from level | 38.2% | 32.0% | 2.99x | Reversal | 0.057% | Liquidity sweep / reversal |
| 2025-05-19 18:00 | Golden zone 50-61.8% | 61.8% | 60.8% | 2.99x | Reversal | -0.128% | Liquidity sweep / reversal |
| 2025-04-22 20:45 | Valid swing, away from level | n/a | -32.9% | 2.99x | Impulse / continuation | -0.086% | True breakout |
| 2026-01-14 09:45 | Valid swing, away from level | n/a | 114.5% | 2.99x | Impulse / continuation | 0.132% | True breakout |
| 2024-11-15 15:45 | Valid swing, away from level | 38.2% | 28.7% | 2.99x | Flat / fading | 0.055% | Position building in range |
| 2026-09-08 07:00 | Valid swing, away from level | 38.2% | 10.8% | 2.99x | Reversal | -0.219% | Liquidity sweep / reversal |
| 2025-09-08 15:30 | Valid swing, away from level | n/a | -15.0% | 2.99x | Reversal | -0.036% | Liquidity sweep / reversal |
| 2025-12-23 14:45 | Valid swing, away from level | n/a | -10.2% | 2.99x | Flat / fading | -0.208% | Weak move without breakout |
| 2025-10-20 11:00 | Valid swing, away from level | n/a | -47.7% | 2.99x | Reversal | -0.273% | Liquidity sweep / reversal |
| 2024-12-20 14:00 | Valid swing, away from level | n/a | -1367.1% | 2.98x | Flat / fading | 0.589% | Weak move without breakout |
| 2026-02-13 14:00 | Valid swing, away from level | n/a | -158.9% | 2.98x | Flat / fading | -0.047% | Position building in range |
| 2026-03-24 10:30 | Valid swing, away from level | n/a | -79.7% | 2.98x | Impulse / continuation | 0.463% | True breakout |
| 2025-08-20 12:00 | Valid swing, away from level | n/a | -60.7% | 2.98x | Flat / fading | -0.029% | Weak move without breakout |
| 2025-12-29 18:15 | Near Fib level | 50.0% | 49.8% | 2.98x | Impulse / continuation | -0.201% | True breakout |
| 2025-06-17 11:00 | Valid swing, away from level | 38.2% | 1.8% | 2.98x | Impulse / continuation | 0.208% | True breakout |
| 2026-06-19 07:00 | Valid swing, away from level | 38.2% | 26.0% | 2.98x | Impulse / continuation | 0.254% | True breakout |
| 2025-02-19 17:45 | Valid swing, away from level | n/a | -82.1% | 2.98x | Reversal | -0.504% | Liquidity sweep / reversal |
| 2025-05-22 10:30 | Valid swing, away from level | 38.2% | 5.6% | 2.98x | Flat / fading | 0.033% | Position building in range |
| 2025-10-24 13:15 | Valid swing, away from level | 38.2% | 43.7% | 2.98x | Reversal | -1.282% | Liquidity sweep / reversal |
| 2026-02-02 08:30 | Valid swing, away from level | n/a | 130.2% | 2.98x | Impulse / continuation | -0.132% | True breakout |
| 2025-07-08 10:30 | Valid swing, away from level | 78.6% | 72.7% | 2.98x | Flat / fading | 0.088% | Weak move without breakout |
| 2024-12-27 10:15 | Golden zone 50-61.8% | 50.0% | 52.8% | 2.98x | Flat / fading | 0.023% | Weak move without breakout |
| 2025-01-23 20:00 | Golden zone 50-61.8% | 50.0% | 52.6% | 2.98x | Flat / fading | 0.013% | Position building in range |
| 2025-09-04 10:30 | Valid swing, away from level | n/a | -27.5% | 2.98x | Reversal | -0.096% | Liquidity sweep / reversal |
| 2026-03-04 17:30 | Valid swing, away from level | n/a | 173.0% | 2.97x | Reversal | 0.202% | Liquidity sweep / reversal |
| 2026-03-04 07:15 | Valid swing, away from level | n/a | -60.0% | 2.97x | Impulse / continuation | 0.236% | True breakout |
| 2025-06-09 11:15 | Valid swing, away from level | n/a | 718.9% | 2.97x | Reversal | -0.176% | Liquidity sweep / reversal |
| 2025-08-18 10:15 | Valid swing, away from level | n/a | -48.4% | 2.97x | Reversal | 0.277% | Liquidity sweep / reversal |
| 2026-01-09 23:30 | Valid swing, away from level | n/a | 154.3% | 2.97x | Reversal | 0.383% | Liquidity sweep / reversal |
| 2025-07-15 13:00 | Valid swing, away from level | n/a | -69.4% | 2.97x | Flat / fading | -0.096% | Weak move without breakout |
| 2024-12-19 11:30 | Valid swing, away from level | n/a | -4.9% | 2.97x | Impulse / continuation | -0.026% | True breakout |
| 2026-08-03 10:30 | Valid swing, away from level | n/a | -289.7% | 2.97x | Flat / fading | 0.117% | Weak move without breakout |
| 2025-07-28 15:15 | Valid swing, away from level | n/a | 193.8% | 2.97x | Impulse / continuation | -0.851% | True breakout |
| 2026-03-27 11:30 | Valid swing, away from level | n/a | 126.2% | 2.97x | Flat / fading | -0.115% | Position building in range |
| 2026-01-22 17:30 | Valid swing, away from level | n/a | 138.8% | 2.97x | Flat / fading | 0.144% | Weak move without breakout |
| 2024-11-21 11:30 | Valid swing, away from level | n/a | 110.8% | 2.97x | Impulse / continuation | -0.143% | True breakout |
| 2026-03-09 16:30 | Valid swing, away from level | 38.2% | 4.2% | 2.97x | Reversal | -0.148% | Liquidity sweep / reversal |
| 2025-09-26 09:45 | Valid swing, away from level | 38.2% | 26.0% | 2.97x | Reversal | -0.334% | Liquidity sweep / reversal |
| 2026-01-19 09:45 | Valid swing, away from level | 38.2% | 25.0% | 2.97x | Impulse -> reversal | 0.153% | False breakout |
| 2026-03-28 11:30 | Valid swing, away from level | n/a | 172.7% | 2.97x | Flat / fading | 0.180% | Position building in range |
| 2026-05-11 12:30 | Valid swing, away from level | n/a | -7.9% | 2.97x | Reversal | -0.295% | Liquidity sweep / reversal |
| 2025-06-01 13:45 | Golden zone 50-61.8% | 61.8% | 59.4% | 2.97x | Impulse / continuation | -0.789% | True breakout |
| 2024-11-21 20:15 | Golden zone 50-61.8% | 61.8% | 56.1% | 2.97x | Flat / fading | 0.325% | Weak move without breakout |
| 2026-01-24 15:30 | Valid swing, away from level | n/a | 183.0% | 2.97x | Impulse / continuation | 0.193% | True breakout |
| 2025-12-08 08:45 | Valid swing, away from level | n/a | -40.2% | 2.97x | Flat / fading | -0.105% | Weak move without breakout |
| 2026-07-23 08:45 | Near Fib level | 61.8% | 64.5% | 2.96x | Impulse / continuation | 0.039% | True breakout |
| 2024-12-23 10:30 | Valid swing, away from level | n/a | -64.6% | 2.96x | Reversal | 0.253% | Liquidity sweep / reversal |
| 2026-09-22 17:45 | Near Fib level | 38.2% | 34.7% | 2.96x | Flat / fading | 0.155% | Weak move without breakout |
| 2025-06-30 09:45 | Valid swing, away from level | 38.2% | 8.2% | 2.96x | Impulse -> reversal | -0.469% | False breakout |
| 2025-12-19 07:00 | Near Fib level | 50.0% | 47.2% | 2.96x | Impulse / continuation | -0.031% | True breakout |
| 2026-07-03 14:30 | Valid swing, away from level | n/a | 441.0% | 2.96x | Flat / fading | -0.430% | Position building in range |
| 2026-01-13 18:15 | Valid swing, away from level | n/a | 155.6% | 2.96x | Impulse / continuation | -0.119% | True breakout |
| 2026-07-02 15:00 | Valid swing, away from level | n/a | 543.8% | 2.96x | Impulse / continuation | -0.793% | True breakout |
| 2025-10-30 07:00 | Valid swing, away from level | 78.6% | 96.0% | 2.96x | Impulse / continuation | -0.068% | True breakout |
| 2026-05-07 18:15 | Valid swing, away from level | n/a | 116.5% | 2.96x | Flat / fading | 0.110% | Position building in range |
| 2026-07-23 11:15 | Valid swing, away from level | n/a | 165.3% | 2.95x | Flat / fading | 0.498% | Position building in range |
| 2026-05-06 11:15 | Near Fib level | 38.2% | 34.6% | 2.95x | Impulse / continuation | -0.342% | True breakout |
| 2026-03-24 11:45 | Valid swing, away from level | n/a | -214.9% | 2.95x | Reversal | -0.227% | Liquidity sweep / reversal |
| 2025-11-11 20:45 | Valid swing, away from level | 38.2% | 30.1% | 2.95x | Reversal | -0.060% | Liquidity sweep / reversal |
| 2025-10-24 10:45 | Golden zone 50-61.8% | 61.8% | 61.1% | 2.95x | Flat / fading | 0.123% | Position building in range |
| 2025-10-28 11:15 | Valid swing, away from level | n/a | -117.1% | 2.95x | Impulse / continuation | 0.816% | True breakout |
| 2026-09-14 08:15 | Valid swing, away from level | n/a | -22.6% | 2.95x | Reversal | 0.030% | Liquidity sweep / reversal |
| 2025-07-18 11:15 | Valid swing, away from level | n/a | -74.8% | 2.95x | Flat / fading | -0.054% | Weak move without breakout |
| 2026-07-29 09:45 | Valid swing, away from level | 38.2% | 26.3% | 2.95x | Reversal | 0.522% | Liquidity sweep / reversal |
| 2025-01-31 10:45 | Valid swing, away from level | n/a | -149.2% | 2.95x | Impulse -> reversal | -0.493% | False breakout |
| 2026-08-13 22:30 | Valid swing, away from level | n/a | 113.7% | 2.95x | Impulse / continuation | -0.346% | True breakout |
| 2026-05-11 16:00 | Valid swing, away from level | 38.2% | 23.4% | 2.95x | Flat / fading | -0.006% | Position building in range |
| 2025-09-19 11:15 | Valid swing, away from level | 61.8% | 67.7% | 2.95x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2025-09-30 11:30 | Valid swing, away from level | n/a | 120.8% | 2.95x | Impulse / continuation | -0.993% | True breakout |
| 2026-02-12 11:30 | Golden zone 50-61.8% | 50.0% | 51.2% | 2.95x | Impulse / continuation | 0.300% | True breakout |
| 2025-04-30 19:00 | Valid swing, away from level | n/a | 111.6% | 2.95x | Flat / fading | 0.272% | Position building in range |
| 2025-08-07 10:30 | Valid swing, away from level | 38.2% | 20.8% | 2.95x | Impulse / continuation | 1.797% | True breakout |
| 2025-04-28 08:30 | Valid swing, away from level | 78.6% | 89.1% | 2.94x | Impulse / continuation | -0.223% | True breakout |
| 2025-09-15 07:15 | Valid swing, away from level | n/a | -50.0% | 2.94x | Reversal | -0.050% | Liquidity sweep / reversal |
| 2025-08-06 21:45 | Valid swing, away from level | n/a | -283.5% | 2.94x | Impulse / continuation | -0.315% | True breakout |
| 2025-07-11 09:00 | Valid swing, away from level | n/a | 146.6% | 2.94x | Flat / fading | 0.119% | Weak move without breakout |
| 2025-05-27 07:00 | Golden zone 50-61.8% | 50.0% | 53.2% | 2.94x | Reversal | -0.806% | Liquidity sweep / reversal |
| 2025-09-08 09:15 | Valid swing, away from level | n/a | -321.7% | 2.94x | Impulse / continuation | -0.173% | True breakout |
| 2024-12-10 11:00 | Valid swing, away from level | n/a | 369.4% | 2.94x | Reversal | -0.118% | Liquidity sweep / reversal |
| 2026-05-18 17:15 | Valid swing, away from level | 38.2% | 30.7% | 2.94x | Impulse / continuation | 0.690% | True breakout |
| 2025-03-10 20:30 | Near Fib level | 61.8% | 64.4% | 2.94x | Flat / fading | 0.146% | Weak move without breakout |
| 2026-08-10 09:00 | Valid swing, away from level | 38.2% | 25.4% | 2.94x | Reversal | 0.179% | Liquidity sweep / reversal |
| 2025-10-13 08:45 | Valid swing, away from level | n/a | -133.3% | 2.94x | Impulse -> reversal | 0.349% | False breakout |
| 2026-01-13 18:30 | Valid swing, away from level | n/a | 162.7% | 2.94x | Flat / fading | -0.063% | Weak move without breakout |
| 2025-10-11 10:00 | Valid swing, away from level | n/a | 103.8% | 2.94x | Flat / fading | -0.035% | Position building in range |
| 2025-04-06 11:30 | Valid swing, away from level | n/a | -22.7% | 2.94x | Flat / fading | 0.208% | Weak move without breakout |
| 2025-11-19 14:45 | Valid swing, away from level | n/a | -16.8% | 2.93x | Impulse / continuation | 0.427% | True breakout |
| 2025-01-08 11:15 | Valid swing, away from level | n/a | -90.0% | 2.93x | Reversal | -0.139% | Liquidity sweep / reversal |
| 2026-02-13 07:00 | Near Fib level | 50.0% | 46.0% | 2.93x | Reversal | -0.030% | Liquidity sweep / reversal |
| 2025-01-17 17:00 | Valid swing, away from level | n/a | -21.7% | 2.93x | Flat / fading | 0.278% | Weak move without breakout |
| 2024-12-27 16:45 | Valid swing, away from level | n/a | 104.4% | 2.93x | Flat / fading | 0.137% | Weak move without breakout |
| 2026-07-19 18:00 | Valid swing, away from level | n/a | -29.6% | 2.93x | Flat / fading | -0.139% | Position building in range |
| 2025-05-06 10:30 | Valid swing, away from level | n/a | -11.1% | 2.93x | Flat / fading | 0.067% | Weak move without breakout |
| 2025-12-12 13:15 | Valid swing, away from level | n/a | 115.1% | 2.93x | Flat / fading | -0.264% | Weak move without breakout |
| 2026-07-03 11:00 | Valid swing, away from level | n/a | 794.9% | 2.93x | Flat / fading | -0.016% | Weak move without breakout |
| 2026-01-13 16:15 | Valid swing, away from level | 78.6% | 72.5% | 2.93x | Impulse / continuation | -0.453% | True breakout |
| 2026-05-28 11:00 | Valid swing, away from level | 38.2% | 21.1% | 2.93x | Impulse / continuation | 0.125% | True breakout |
| 2025-10-10 13:30 | Near Fib level | 78.6% | 81.7% | 2.93x | Impulse / continuation | -0.116% | True breakout |
| 2025-04-24 10:30 | Golden zone 50-61.8% | 50.0% | 51.1% | 2.93x | Impulse / continuation | -0.161% | True breakout |
| 2026-08-17 09:00 | Valid swing, away from level | n/a | 207.3% | 2.93x | Reversal | 0.711% | Liquidity sweep / reversal |
| 2025-08-24 11:45 | Valid swing, away from level | n/a | 207.1% | 2.93x | Reversal | 0.036% | Liquidity sweep / reversal |
| 2025-08-26 07:00 | Near Fib level | 38.2% | 38.1% | 2.93x | Flat / fading | 0.071% | Weak move without breakout |
| 2025-09-16 16:45 | Golden zone 50-61.8% | 61.8% | 56.5% | 2.93x | Impulse / continuation | 0.247% | True breakout |
| 2026-07-09 16:45 | Near Fib level | 38.2% | 41.6% | 2.93x | Reversal | 0.203% | Liquidity sweep / reversal |
| 2025-03-30 17:00 | No confirmed swing | n/a | n/a | 2.93x | Flat / fading | 0.000% | Position building in range |
| 2025-12-03 10:00 | Valid swing, away from level | 78.6% | 72.2% | 2.93x | Impulse / continuation | -0.775% | True breakout |
| 2025-06-02 17:30 | Valid swing, away from level | n/a | -8.7% | 2.93x | Impulse / continuation | 0.439% | True breakout |
| 2026-06-04 08:30 | Valid swing, away from level | 78.6% | 94.4% | 2.93x | Impulse / continuation | 0.125% | True breakout |
| 2026-01-05 09:00 | Valid swing, away from level | n/a | 278.0% | 2.93x | Flat / fading | -0.147% | Weak move without breakout |
| 2026-08-19 07:30 | Valid swing, away from level | n/a | -22.8% | 2.93x | Reversal | -0.305% | Liquidity sweep / reversal |
| 2025-08-29 10:00 | Golden zone 50-61.8% | 61.8% | 61.1% | 2.93x | Impulse / continuation | -0.101% | True breakout |
| 2024-11-20 10:45 | Valid swing, away from level | 61.8% | 68.6% | 2.93x | Impulse / continuation | -0.069% | True breakout |
| 2025-12-28 10:15 | Valid swing, away from level | n/a | 136.8% | 2.93x | Impulse / continuation | -0.129% | True breakout |
| 2025-11-19 15:00 | Valid swing, away from level | n/a | -27.3% | 2.93x | Impulse / continuation | 1.180% | True breakout |
| 2025-05-13 09:45 | Valid swing, away from level | n/a | -10.7% | 2.92x | Flat / fading | -0.032% | Weak move without breakout |
| 2025-09-19 10:15 | Valid swing, away from level | 38.2% | 22.0% | 2.92x | Reversal | -0.324% | Liquidity sweep / reversal |
| 2025-11-12 10:15 | Valid swing, away from level | n/a | 125.4% | 2.92x | Reversal | -0.088% | Liquidity sweep / reversal |
| 2025-07-02 10:00 | Valid swing, away from level | n/a | 159.3% | 2.92x | Flat / fading | 0.061% | Position building in range |
| 2025-11-24 10:45 | Golden zone 50-61.8% | 61.8% | 59.5% | 2.92x | Impulse / continuation | -0.837% | True breakout |
| 2024-12-02 11:00 | Valid swing, away from level | n/a | -33.7% | 2.92x | Impulse / continuation | -0.614% | True breakout |
| 2025-09-22 11:00 | Valid swing, away from level | n/a | 114.6% | 2.92x | Impulse / continuation | -0.163% | True breakout |
| 2026-03-27 07:00 | Valid swing, away from level | n/a | 126.9% | 2.92x | Reversal | -0.121% | Liquidity sweep / reversal |
| 2026-06-03 10:00 | Near Fib level | 61.8% | 65.2% | 2.92x | Impulse / continuation | -0.391% | True breakout |
| 2026-02-24 13:15 | Valid swing, away from level | n/a | 138.7% | 2.92x | Flat / fading | 0.057% | Position building in range |
| 2025-03-13 12:00 | Valid swing, away from level | n/a | 417.8% | 2.92x | Impulse / continuation | 0.505% | True breakout |
| 2025-03-26 14:30 | Valid swing, away from level | n/a | 105.8% | 2.92x | Flat / fading | -0.200% | Weak move without breakout |
| 2025-12-23 10:45 | Golden zone 50-61.8% | 61.8% | 56.3% | 2.92x | Reversal | -0.234% | Liquidity sweep / reversal |
| 2026-08-26 16:00 | Golden zone 50-61.8% | 50.0% | 54.8% | 2.92x | Impulse / continuation | -0.080% | True breakout |
| 2024-12-25 11:00 | Valid swing, away from level | 78.6% | 90.8% | 2.92x | Impulse / continuation | 0.739% | True breakout |
| 2025-09-12 15:30 | Valid swing, away from level | n/a | 168.0% | 2.92x | Impulse / continuation | -0.708% | True breakout |
| 2025-09-07 10:15 | Valid swing, away from level | n/a | -17.6% | 2.92x | Reversal | -0.006% | Liquidity sweep / reversal |
| 2026-08-05 07:00 | Valid swing, away from level | 38.2% | 26.0% | 2.91x | Reversal | 0.360% | Liquidity sweep / reversal |
| 2024-12-19 12:00 | Valid swing, away from level | n/a | -26.6% | 2.91x | Reversal | -0.018% | Liquidity sweep / reversal |
| 2025-06-10 10:45 | Golden zone 50-61.8% | 50.0% | 50.2% | 2.91x | Reversal | 0.131% | Liquidity sweep / reversal |
| 2026-06-17 08:15 | Valid swing, away from level | 78.6% | 88.4% | 2.91x | Reversal | -0.222% | Liquidity sweep / reversal |
| 2026-02-24 10:45 | Near Fib level | 38.2% | 40.8% | 2.91x | Flat / fading | -0.119% | Weak move without breakout |
| 2026-07-10 11:00 | Valid swing, away from level | n/a | 114.9% | 2.91x | Impulse / continuation | -0.768% | True breakout |
| 2025-03-18 19:45 | Valid swing, away from level | n/a | -233.9% | 2.91x | Flat / fading | -1.279% | Weak move without breakout |
| 2025-03-11 10:15 | Golden zone 50-61.8% | 61.8% | 61.4% | 2.91x | Impulse / continuation | 0.433% | True breakout |
| 2026-07-16 07:15 | Valid swing, away from level | 78.6% | 95.3% | 2.91x | Reversal | -0.569% | Liquidity sweep / reversal |
| 2025-09-11 11:15 | Valid swing, away from level | n/a | 191.7% | 2.91x | Impulse / continuation | -0.018% | True breakout |
| 2026-03-06 10:45 | Near Fib level | 38.2% | 33.8% | 2.91x | Impulse / continuation | -0.076% | True breakout |
| 2026-08-26 19:00 | Valid swing, away from level | 78.6% | 92.4% | 2.91x | Flat / fading | -0.177% | Position building in range |
| 2025-12-23 07:00 | Valid swing, away from level | n/a | 141.7% | 2.91x | Flat / fading | 0.000% | Position building in range |
| 2025-01-27 09:15 | Valid swing, away from level | n/a | 129.6% | 2.91x | Impulse / continuation | -0.120% | True breakout |
| 2025-05-04 12:15 | Valid swing, away from level | n/a | -118.3% | 2.91x | Reversal | -0.125% | Liquidity sweep / reversal |
| 2025-05-20 10:30 | Valid swing, away from level | 78.6% | 92.9% | 2.91x | Flat / fading | -0.117% | Weak move without breakout |
| 2026-02-13 13:15 | Near Fib level | 50.0% | 48.9% | 2.90x | Reversal | 1.002% | Liquidity sweep / reversal |
| 2026-06-27 18:45 | Valid swing, away from level | 38.2% | 22.6% | 2.90x | Reversal | 0.098% | Liquidity sweep / reversal |
| 2025-10-07 10:30 | Valid swing, away from level | n/a | -8.9% | 2.90x | Impulse / continuation | 0.448% | True breakout |
| 2025-05-16 23:00 | Valid swing, away from level | 61.8% | 69.3% | 2.90x | Reversal | 0.156% | Liquidity sweep / reversal |
| 2025-09-28 18:30 | Valid swing, away from level | n/a | 128.6% | 2.90x | Reversal | 0.180% | Liquidity sweep / reversal |
| 2025-01-06 11:45 | Valid swing, away from level | 38.2% | 23.5% | 2.90x | Reversal | -0.653% | Liquidity sweep / reversal |
| 2025-11-05 10:00 | Near Fib level | 50.0% | 49.4% | 2.90x | Reversal | 0.873% | Liquidity sweep / reversal |
| 2024-11-21 18:00 | Valid swing, away from level | 38.2% | 12.8% | 2.90x | Flat / fading | -0.457% | Position building in range |
| 2026-09-09 09:00 | Valid swing, away from level | n/a | 106.6% | 2.90x | Reversal | -0.084% | Liquidity sweep / reversal |
| 2026-08-31 07:45 | Valid swing, away from level | 38.2% | 22.7% | 2.90x | Reversal | 0.328% | Liquidity sweep / reversal |
| 2026-06-08 09:30 | Valid swing, away from level | n/a | -213.0% | 2.90x | Reversal | -0.570% | Liquidity sweep / reversal |
| 2026-03-18 11:30 | Valid swing, away from level | n/a | -134.8% | 2.90x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-02-13 10:00 | Valid swing, away from level | 38.2% | 32.2% | 2.90x | Impulse / continuation | -0.848% | True breakout |
| 2025-02-06 17:00 | Valid swing, away from level | 38.2% | 18.4% | 2.90x | Flat / fading | -0.097% | Weak move without breakout |
| 2025-12-02 13:00 | Valid swing, away from level | n/a | -6.7% | 2.90x | Flat / fading | 0.057% | Weak move without breakout |
| 2026-03-13 15:30 | Golden zone 50-61.8% | 61.8% | 60.2% | 2.90x | Impulse / continuation | -0.024% | True breakout |
| 2026-09-08 09:15 | Valid swing, away from level | n/a | 138.7% | 2.89x | Reversal | -0.373% | Liquidity sweep / reversal |
| 2026-09-17 07:15 | Near Fib level | 78.6% | 81.8% | 2.89x | Flat / fading | -0.125% | Weak move without breakout |
| 2025-08-04 17:30 | Valid swing, away from level | n/a | -54.7% | 2.89x | Impulse / continuation | 0.384% | True breakout |
| 2025-03-26 15:45 | Valid swing, away from level | n/a | 169.8% | 2.89x | Impulse / continuation | -0.017% | True breakout |
| 2025-02-24 14:00 | Near Fib level | 61.8% | 62.6% | 2.89x | Flat / fading | -0.117% | Weak move without breakout |
| 2025-07-17 10:45 | Near Fib level | 38.2% | 37.2% | 2.89x | Reversal | -0.335% | Liquidity sweep / reversal |
| 2026-06-30 08:15 | Valid swing, away from level | n/a | -3.4% | 2.89x | Reversal | -0.602% | Liquidity sweep / reversal |
| 2025-08-30 17:30 | Valid swing, away from level | n/a | 130.6% | 2.89x | Impulse / continuation | -0.072% | True breakout |
| 2025-03-02 11:15 | Valid swing, away from level | 50.0% | 44.4% | 2.89x | Reversal | 0.220% | Liquidity sweep / reversal |
| 2025-05-04 10:30 | Valid swing, away from level | n/a | -53.5% | 2.89x | Flat / fading | 0.000% | Position building in range |
| 2025-03-14 16:00 | Valid swing, away from level | n/a | -81.2% | 2.89x | Impulse / continuation | 0.310% | True breakout |
| 2025-11-18 08:00 | Valid swing, away from level | n/a | 146.7% | 2.89x | Impulse / continuation | -0.110% | True breakout |
| 2026-03-09 22:45 | Valid swing, away from level | n/a | -40.1% | 2.89x | Impulse / continuation | 0.445% | True breakout |
| 2025-06-25 10:30 | Valid swing, away from level | n/a | -28.6% | 2.89x | Impulse / continuation | 0.268% | True breakout |
| 2025-05-29 10:00 | Valid swing, away from level | 61.8% | 67.9% | 2.89x | Flat / fading | 0.075% | Weak move without breakout |
| 2026-07-22 13:00 | Valid swing, away from level | n/a | -21.2% | 2.89x | Reversal | 0.317% | Liquidity sweep / reversal |
| 2026-04-26 13:30 | Valid swing, away from level | n/a | 153.3% | 2.89x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-07-27 18:00 | Valid swing, away from level | 38.2% | 4.9% | 2.89x | Reversal | 0.062% | Liquidity sweep / reversal |
| 2026-07-24 07:15 | Valid swing, away from level | n/a | 111.7% | 2.89x | Reversal | 0.428% | Liquidity sweep / reversal |
| 2026-06-29 10:15 | Valid swing, away from level | n/a | 249.1% | 2.89x | Impulse -> reversal | 0.887% | False breakout |
| 2024-11-13 10:15 | Valid swing, away from level | n/a | 190.1% | 2.88x | Impulse / continuation | 0.298% | True breakout |
| 2025-03-04 10:15 | Valid swing, away from level | n/a | -166.2% | 2.88x | Impulse / continuation | 0.594% | True breakout |
| 2026-02-02 07:45 | Valid swing, away from level | 78.6% | 88.4% | 2.88x | Impulse / continuation | -0.174% | True breakout |
| 2025-04-13 11:30 | Valid swing, away from level | n/a | -4.2% | 2.88x | Flat / fading | -0.044% | Weak move without breakout |
| 2026-09-16 23:30 | Valid swing, away from level | n/a | 116.7% | 2.88x | Impulse -> reversal | 0.180% | False breakout |
| 2026-02-16 13:00 | Valid swing, away from level | n/a | -1096.7% | 2.88x | Flat / fading | -0.221% | Weak move without breakout |
| 2025-02-14 10:00 | Golden zone 50-61.8% | 50.0% | 55.2% | 2.88x | Reversal | 0.897% | Liquidity sweep / reversal |
| 2025-08-06 22:15 | Valid swing, away from level | n/a | -280.3% | 2.88x | Reversal | -0.491% | Liquidity sweep / reversal |
| 2026-06-10 15:00 | Valid swing, away from level | 78.6% | 90.0% | 2.88x | Flat / fading | 0.190% | Weak move without breakout |
| 2025-11-27 08:15 | Near Fib level | 38.2% | 34.0% | 2.88x | Impulse / continuation | 0.084% | True breakout |
| 2025-04-15 17:00 | Valid swing, away from level | n/a | -17.6% | 2.88x | Reversal | -0.623% | Liquidity sweep / reversal |
| 2025-07-06 17:30 | Near Fib level | 61.8% | 64.4% | 2.88x | Impulse / continuation | 0.006% | True breakout |
| 2025-10-02 09:45 | Valid swing, away from level | n/a | 129.2% | 2.88x | Impulse / continuation | -0.488% | True breakout |
| 2025-09-15 10:00 | Near Fib level | 61.8% | 64.0% | 2.88x | Reversal | -0.658% | Liquidity sweep / reversal |
| 2026-05-14 18:30 | Valid swing, away from level | 78.6% | 96.1% | 2.87x | Flat / fading | -0.057% | Weak move without breakout |
| 2026-02-01 13:15 | Golden zone 50-61.8% | 61.8% | 57.1% | 2.87x | Impulse / continuation | 0.150% | True breakout |
| 2025-07-12 14:15 | Valid swing, away from level | 78.6% | 98.1% | 2.87x | Flat / fading | 0.026% | Position building in range |
| 2026-09-09 07:00 | Valid swing, away from level | 78.6% | 94.9% | 2.87x | Flat / fading | -0.008% | Weak move without breakout |
| 2025-12-15 19:15 | Valid swing, away from level | n/a | -110.9% | 2.87x | Flat / fading | -0.025% | Weak move without breakout |
| 2026-06-10 10:45 | Valid swing, away from level | 38.2% | 19.2% | 2.87x | Reversal | -0.418% | Liquidity sweep / reversal |
| 2025-12-11 08:30 | Valid swing, away from level | n/a | -19.4% | 2.87x | Impulse / continuation | 0.191% | True breakout |
| 2026-04-07 16:15 | Valid swing, away from level | 78.6% | 95.6% | 2.87x | Reversal | -0.213% | Liquidity sweep / reversal |
| 2026-02-25 07:00 | Valid swing, away from level | 78.6% | 86.9% | 2.87x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-07-22 12:45 | Valid swing, away from level | n/a | -22.8% | 2.87x | Flat / fading | -0.024% | Weak move without breakout |
| 2026-07-15 11:45 | Valid swing, away from level | n/a | 580.0% | 2.87x | Flat / fading | 0.435% | Weak move without breakout |
| 2025-04-05 15:30 | Valid swing, away from level | 78.6% | 86.2% | 2.87x | Flat / fading | 0.369% | Weak move without breakout |
| 2025-04-15 10:15 | Golden zone 50-61.8% | 50.0% | 52.2% | 2.87x | Impulse / continuation | -0.550% | True breakout |
| 2026-03-11 09:45 | Valid swing, away from level | 61.8% | 68.7% | 2.87x | Flat / fading | 0.065% | Weak move without breakout |
| 2026-02-09 09:45 | Valid swing, away from level | n/a | 196.7% | 2.87x | Impulse / continuation | -0.213% | True breakout |
| 2026-02-05 11:15 | Valid swing, away from level | n/a | -78.1% | 2.87x | Flat / fading | 0.095% | Weak move without breakout |
| 2026-08-05 10:30 | Valid swing, away from level | n/a | -77.6% | 2.87x | Impulse / continuation | -0.480% | True breakout |
| 2025-08-13 09:00 | Golden zone 50-61.8% | 50.0% | 52.5% | 2.87x | Impulse / continuation | 0.150% | True breakout |
| 2025-03-20 10:45 | Near Fib level | 38.2% | 40.5% | 2.87x | Reversal | -0.072% | Liquidity sweep / reversal |
| 2026-07-03 11:15 | Valid swing, away from level | n/a | 679.5% | 2.87x | Reversal | 0.016% | Liquidity sweep / reversal |
| 2025-06-20 10:30 | Valid swing, away from level | 78.6% | 85.1% | 2.87x | Impulse / continuation | 0.176% | True breakout |
| 2025-08-25 07:45 | Valid swing, away from level | 78.6% | 89.5% | 2.86x | Reversal | 0.142% | Liquidity sweep / reversal |
| 2026-04-30 09:00 | Near Fib level | 78.6% | 80.2% | 2.86x | Reversal | 0.762% | Liquidity sweep / reversal |
| 2026-08-28 08:15 | Valid swing, away from level | n/a | -98.7% | 2.86x | Flat / fading | 0.055% | Position building in range |
| 2025-05-06 22:00 | Valid swing, away from level | n/a | -29.0% | 2.86x | Impulse / continuation | -0.182% | True breakout |
| 2025-05-26 10:15 | Valid swing, away from level | n/a | 233.1% | 2.86x | Reversal | 0.462% | Liquidity sweep / reversal |
| 2025-10-02 07:00 | Near Fib level | 78.6% | 82.7% | 2.86x | Impulse / continuation | -0.361% | True breakout |
| 2026-01-06 23:45 | Valid swing, away from level | n/a | -85.7% | 2.86x | Reversal | -1.478% | Liquidity sweep / reversal |
| 2026-04-19 11:30 | Golden zone 50-61.8% | 50.0% | 51.1% | 2.86x | Flat / fading | 0.049% | Weak move without breakout |
| 2026-05-30 15:15 | Valid swing, away from level | 38.2% | 3.7% | 2.86x | Reversal | -0.033% | Liquidity sweep / reversal |
| 2026-03-20 09:15 | Valid swing, away from level | 38.2% | 27.8% | 2.86x | Impulse / continuation | 0.132% | True breakout |
| 2025-04-11 11:00 | Valid swing, away from level | n/a | -13.4% | 2.86x | Flat / fading | -0.576% | Weak move without breakout |
| 2025-09-26 07:00 | Near Fib level | 50.0% | 47.4% | 2.86x | Reversal | -0.436% | Liquidity sweep / reversal |
| 2025-10-07 07:00 | Valid swing, away from level | 38.2% | 13.6% | 2.86x | Reversal | -0.040% | Liquidity sweep / reversal |
| 2026-07-20 16:30 | Valid swing, away from level | n/a | -118.8% | 2.86x | Flat / fading | 0.059% | Weak move without breakout |
| 2025-11-06 10:15 | Valid swing, away from level | 78.6% | 85.6% | 2.86x | Impulse / continuation | -0.256% | True breakout |
| 2026-05-20 09:15 | Near Fib level | 78.6% | 82.1% | 2.86x | Reversal | -0.426% | Liquidity sweep / reversal |
| 2026-08-05 09:15 | Valid swing, away from level | n/a | -5.9% | 2.85x | Reversal | 0.519% | Liquidity sweep / reversal |
| 2026-03-30 12:30 | Valid swing, away from level | 38.2% | 43.9% | 2.85x | Reversal | 0.136% | Liquidity sweep / reversal |
| 2025-08-18 09:00 | Valid swing, away from level | n/a | -147.7% | 2.85x | Impulse / continuation | -0.180% | True breakout |
| 2025-10-16 10:45 | Valid swing, away from level | 38.2% | 31.3% | 2.85x | Reversal | 0.062% | Liquidity sweep / reversal |
| 2025-07-16 10:30 | Valid swing, away from level | n/a | 105.1% | 2.85x | Impulse -> reversal | 0.363% | False breakout |
| 2026-03-30 11:00 | Valid swing, away from level | 78.6% | 94.2% | 2.85x | Impulse / continuation | 0.161% | True breakout |
| 2026-07-01 11:00 | Valid swing, away from level | n/a | -56.0% | 2.85x | Reversal | -0.665% | Liquidity sweep / reversal |
| 2025-10-09 12:00 | Valid swing, away from level | 78.6% | 88.2% | 2.85x | Impulse / continuation | 1.628% | True breakout |
| 2025-07-10 07:45 | Valid swing, away from level | n/a | -63.6% | 2.85x | Reversal | -0.294% | Liquidity sweep / reversal |
| 2025-07-25 07:30 | Golden zone 50-61.8% | 50.0% | 54.7% | 2.85x | Flat / fading | -0.072% | Position building in range |
| 2025-03-13 10:15 | Valid swing, away from level | n/a | 217.8% | 2.85x | Impulse / continuation | -0.967% | True breakout |
| 2026-04-20 09:00 | Valid swing, away from level | n/a | -10.3% | 2.85x | Impulse / continuation | 0.031% | True breakout |
| 2025-07-28 11:45 | Valid swing, away from level | 38.2% | 15.8% | 2.85x | Flat / fading | -0.074% | Position building in range |
| 2026-04-21 07:45 | Near Fib level | 50.0% | 45.1% | 2.85x | Reversal | -0.111% | Liquidity sweep / reversal |
| 2024-11-07 15:00 | Valid swing, away from level | 38.2% | 0.0% | 2.85x | Impulse / continuation | 0.412% | True breakout |
| 2025-12-15 14:30 | Valid swing, away from level | n/a | -37.3% | 2.85x | Flat / fading | 0.012% | Position building in range |
| 2025-10-02 11:30 | Valid swing, away from level | n/a | 276.4% | 2.85x | Reversal | 0.253% | Liquidity sweep / reversal |
| 2025-04-22 18:00 | Valid swing, away from level | 38.2% | 28.3% | 2.85x | Reversal | 0.234% | Liquidity sweep / reversal |
| 2025-06-01 10:30 | Valid swing, away from level | n/a | 1310.0% | 2.85x | Impulse / continuation | 0.000% | True breakout |
| 2026-03-11 17:45 | Valid swing, away from level | 78.6% | 89.4% | 2.85x | Reversal | -0.047% | Liquidity sweep / reversal |
| 2026-02-05 13:15 | Valid swing, away from level | 38.2% | 25.0% | 2.85x | Flat / fading | -0.054% | Weak move without breakout |
| 2026-03-26 18:30 | Golden zone 50-61.8% | 61.8% | 56.4% | 2.85x | Reversal | -0.181% | Liquidity sweep / reversal |
| 2025-06-23 17:00 | Valid swing, away from level | n/a | -48.6% | 2.85x | Flat / fading | -0.094% | Position building in range |
| 2025-03-21 07:15 | Near Fib level | 38.2% | 34.6% | 2.84x | Flat / fading | -0.066% | Weak move without breakout |
| 2025-05-12 17:30 | Valid swing, away from level | 38.2% | 27.3% | 2.84x | Flat / fading | 0.025% | Weak move without breakout |
| 2026-08-04 08:45 | Valid swing, away from level | 38.2% | 9.9% | 2.84x | Reversal | 0.103% | Liquidity sweep / reversal |
| 2025-04-24 12:45 | Near Fib level | 38.2% | 33.2% | 2.84x | Flat / fading | -0.074% | Weak move without breakout |
| 2026-03-20 09:00 | Valid swing, away from level | 38.2% | 32.9% | 2.84x | Impulse / continuation | 0.054% | True breakout |
| 2025-05-05 18:00 | Valid swing, away from level | n/a | 413.2% | 2.84x | Flat / fading | -0.585% | Weak move without breakout |
| 2026-05-02 10:00 | Near Fib level | 78.6% | 81.4% | 2.84x | Reversal | 0.007% | Liquidity sweep / reversal |
| 2025-04-16 09:00 | Near Fib level | 78.6% | 79.1% | 2.84x | Reversal | -0.237% | Liquidity sweep / reversal |
| 2025-02-27 10:00 | Valid swing, away from level | 78.6% | 90.8% | 2.84x | Reversal | -0.503% | Liquidity sweep / reversal |
| 2026-09-09 10:45 | Valid swing, away from level | 78.6% | 93.4% | 2.84x | Flat / fading | -0.145% | Weak move without breakout |
| 2026-02-05 09:45 | Near Fib level | 78.6% | 79.5% | 2.84x | Reversal | 0.510% | Liquidity sweep / reversal |
| 2024-11-27 11:00 | Valid swing, away from level | n/a | 121.1% | 2.84x | Impulse / continuation | 1.258% | True breakout |
| 2025-04-18 12:45 | Valid swing, away from level | n/a | 129.0% | 2.84x | Impulse / continuation | -0.248% | True breakout |
| 2025-06-16 12:45 | Valid swing, away from level | 38.2% | 26.9% | 2.84x | Impulse / continuation | 0.114% | True breakout |
| 2026-04-24 10:45 | Valid swing, away from level | 78.6% | 73.6% | 2.84x | Impulse / continuation | -0.190% | True breakout |
| 2026-05-19 12:00 | Valid swing, away from level | n/a | -66.1% | 2.84x | Reversal | -1.086% | Liquidity sweep / reversal |
| 2025-07-27 10:30 | Valid swing, away from level | n/a | 108.2% | 2.84x | Flat / fading | 0.130% | Weak move without breakout |
| 2025-04-01 17:30 | Near Fib level | 38.2% | 39.5% | 2.84x | Reversal | -0.695% | Liquidity sweep / reversal |
| 2025-05-30 10:45 | Near Fib level | 61.8% | 64.1% | 2.84x | Impulse / continuation | -0.025% | True breakout |
| 2024-12-16 11:15 | Valid swing, away from level | n/a | 128.0% | 2.83x | Reversal | -0.353% | Liquidity sweep / reversal |
| 2025-04-22 16:15 | Valid swing, away from level | 38.2% | 31.5% | 2.83x | Flat / fading | 0.080% | Weak move without breakout |
| 2025-09-18 10:45 | Valid swing, away from level | n/a | 132.8% | 2.83x | Flat / fading | 0.032% | Weak move without breakout |
| 2026-05-21 17:15 | Valid swing, away from level | 38.2% | 3.5% | 2.83x | Impulse / continuation | 0.173% | True breakout |
| 2025-06-27 16:15 | Valid swing, away from level | n/a | -26.8% | 2.83x | Impulse / continuation | 0.327% | True breakout |
| 2026-04-28 11:15 | Valid swing, away from level | n/a | 149.1% | 2.83x | Reversal | -0.549% | Liquidity sweep / reversal |
| 2026-06-07 12:00 | Valid swing, away from level | 78.6% | 88.1% | 2.83x | Flat / fading | -0.061% | Weak move without breakout |
| 2025-12-11 09:00 | Valid swing, away from level | n/a | -22.3% | 2.83x | Reversal | 0.505% | Liquidity sweep / reversal |
| 2026-05-02 13:00 | Valid swing, away from level | 78.6% | 93.6% | 2.83x | Flat / fading | 0.033% | Position building in range |
| 2025-04-17 17:00 | Near Fib level | 78.6% | 77.8% | 2.83x | Impulse / continuation | -0.258% | True breakout |
| 2025-01-10 11:15 | Golden zone 50-61.8% | 61.8% | 60.0% | 2.83x | Reversal | -0.058% | Liquidity sweep / reversal |
| 2024-11-21 10:15 | Valid swing, away from level | 78.6% | 70.7% | 2.83x | Reversal | -0.978% | Liquidity sweep / reversal |
| 2025-05-02 18:00 | Valid swing, away from level | n/a | 193.7% | 2.83x | Impulse / continuation | -0.398% | True breakout |
| 2026-06-24 19:00 | Valid swing, away from level | n/a | 268.7% | 2.83x | Flat / fading | -0.633% | Weak move without breakout |
| 2025-03-11 17:00 | Valid swing, away from level | 38.2% | 4.4% | 2.83x | Flat / fading | -0.209% | Position building in range |
| 2025-02-07 20:15 | Valid swing, away from level | 38.2% | 30.1% | 2.83x | Flat / fading | 0.013% | Weak move without breakout |
| 2026-02-06 10:30 | Golden zone 50-61.8% | 61.8% | 61.8% | 2.83x | Reversal | -0.060% | Liquidity sweep / reversal |
| 2025-12-17 19:00 | Valid swing, away from level | n/a | 163.5% | 2.83x | Reversal | -0.179% | Liquidity sweep / reversal |
| 2025-03-03 08:30 | Valid swing, away from level | n/a | 223.5% | 2.83x | Reversal | -0.382% | Liquidity sweep / reversal |
| 2025-01-13 10:30 | Valid swing, away from level | n/a | -34.7% | 2.83x | Flat / fading | 0.305% | Weak move without breakout |
| 2025-05-26 07:45 | Valid swing, away from level | n/a | 177.1% | 2.83x | Impulse / continuation | -0.026% | True breakout |
| 2025-07-15 09:30 | Valid swing, away from level | n/a | -3.2% | 2.83x | Impulse / continuation | -0.179% | True breakout |
| 2026-07-10 12:00 | Valid swing, away from level | n/a | 185.3% | 2.83x | Reversal | 0.495% | Liquidity sweep / reversal |
| 2025-12-22 21:15 | Valid swing, away from level | n/a | 131.5% | 2.82x | Impulse / continuation | -0.330% | True breakout |
| 2026-03-02 17:30 | Valid swing, away from level | 78.6% | 91.1% | 2.82x | Impulse / continuation | -0.233% | True breakout |
| 2026-09-02 18:30 | Valid swing, away from level | 38.2% | 16.7% | 2.82x | Impulse / continuation | -0.055% | True breakout |
| 2025-09-17 17:30 | Valid swing, away from level | n/a | -61.3% | 2.82x | Flat / fading | 0.101% | Weak move without breakout |
| 2026-08-12 07:00 | Valid swing, away from level | 38.2% | 14.5% | 2.82x | Impulse / continuation | 0.387% | True breakout |
| 2026-02-06 12:30 | Golden zone 50-61.8% | 61.8% | 58.4% | 2.82x | Impulse / continuation | 0.224% | True breakout |
| 2025-10-06 10:45 | Valid swing, away from level | n/a | 116.3% | 2.82x | Flat / fading | -0.246% | Weak move without breakout |
| 2025-01-08 11:00 | Valid swing, away from level | n/a | -62.2% | 2.82x | Impulse / continuation | -0.007% | True breakout |
| 2026-07-08 10:15 | Near Fib level | 38.2% | 42.0% | 2.82x | Reversal | 1.023% | Liquidity sweep / reversal |
| 2026-03-05 14:45 | Valid swing, away from level | n/a | -104.1% | 2.82x | Reversal | -0.094% | Liquidity sweep / reversal |
| 2025-11-27 17:30 | Valid swing, away from level | n/a | 345.1% | 2.82x | Reversal | 0.355% | Liquidity sweep / reversal |
| 2025-06-01 14:30 | Valid swing, away from level | 78.6% | 96.6% | 2.82x | Reversal | 0.469% | Liquidity sweep / reversal |
| 2025-08-28 20:45 | Valid swing, away from level | n/a | 217.9% | 2.82x | Flat / fading | 0.130% | Weak move without breakout |
| 2026-08-18 11:30 | Valid swing, away from level | n/a | -14.0% | 2.82x | Impulse / continuation | 1.875% | True breakout |
| 2025-12-26 08:00 | Valid swing, away from level | 38.2% | 8.6% | 2.82x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2025-09-09 12:45 | Valid swing, away from level | 38.2% | 2.1% | 2.82x | Reversal | -0.089% | Liquidity sweep / reversal |
| 2025-02-04 10:15 | Valid swing, away from level | 38.2% | 5.6% | 2.82x | Impulse / continuation | 0.098% | True breakout |
| 2025-08-06 09:15 | Valid swing, away from level | n/a | -26.3% | 2.82x | Reversal | -0.050% | Liquidity sweep / reversal |
| 2024-10-30 10:45 | Valid swing, away from level | n/a | -16.8% | 2.82x | Impulse -> reversal | -0.209% | False breakout |
| 2025-04-30 22:30 | Valid swing, away from level | 78.6% | 70.4% | 2.82x | Flat / fading | -0.076% | Weak move without breakout |
| 2024-10-01 14:00 | Valid swing, away from level | n/a | 361.7% | 2.82x | Flat / fading | -0.215% | Weak move without breakout |
| 2025-03-06 10:00 | Near Fib level | 61.8% | 62.2% | 2.81x | Flat / fading | 0.006% | Weak move without breakout |
| 2026-09-16 15:00 | Valid swing, away from level | n/a | 209.3% | 2.81x | Flat / fading | -0.177% | Position building in range |
| 2026-05-25 08:30 | Valid swing, away from level | n/a | -100.0% | 2.81x | Reversal | -0.072% | Liquidity sweep / reversal |
| 2026-04-02 16:45 | Valid swing, away from level | n/a | -23.3% | 2.81x | Reversal | 0.031% | Liquidity sweep / reversal |
| 2024-11-29 11:00 | Golden zone 50-61.8% | 61.8% | 56.9% | 2.81x | Reversal | 0.690% | Liquidity sweep / reversal |
| 2025-07-17 12:00 | Near Fib level | 78.6% | 76.0% | 2.81x | Reversal | 0.138% | Liquidity sweep / reversal |
| 2024-11-07 14:45 | Valid swing, away from level | 38.2% | 18.9% | 2.81x | Impulse / continuation | 0.776% | True breakout |
| 2026-05-28 11:30 | Valid swing, away from level | n/a | -30.3% | 2.81x | Reversal | -0.007% | Liquidity sweep / reversal |
| 2025-06-24 17:15 | Near Fib level | 50.0% | 46.8% | 2.81x | Flat / fading | 0.240% | Weak move without breakout |
| 2026-01-28 10:15 | Valid swing, away from level | 38.2% | 19.0% | 2.81x | Reversal | -0.203% | Liquidity sweep / reversal |
| 2025-10-22 11:15 | Golden zone 50-61.8% | 61.8% | 60.0% | 2.81x | Reversal | 0.367% | Liquidity sweep / reversal |
| 2025-02-21 10:45 | Valid swing, away from level | n/a | -84.0% | 2.81x | Flat / fading | -0.110% | Weak move without breakout |
| 2025-10-10 10:15 | Valid swing, away from level | 78.6% | 96.6% | 2.81x | Impulse / continuation | 0.305% | True breakout |
| 2025-07-29 20:45 | Valid swing, away from level | n/a | 168.7% | 2.81x | Impulse / continuation | -0.215% | True breakout |
| 2025-07-02 09:15 | Valid swing, away from level | n/a | 102.8% | 2.80x | Impulse / continuation | -0.024% | True breakout |
| 2025-10-21 17:00 | Valid swing, away from level | n/a | 122.4% | 2.80x | Impulse / continuation | -2.785% | True breakout |
| 2025-03-20 10:30 | Near Fib level | 38.2% | 33.8% | 2.80x | Flat / fading | -0.154% | Weak move without breakout |
| 2025-03-05 10:15 | Golden zone 50-61.8% | 50.0% | 51.7% | 2.80x | Reversal | 0.463% | Liquidity sweep / reversal |
| 2026-08-05 10:00 | Valid swing, away from level | n/a | -75.0% | 2.80x | Impulse -> reversal | -0.189% | False breakout |
| 2025-05-22 07:30 | Valid swing, away from level | n/a | 104.5% | 2.80x | Impulse / continuation | -0.933% | True breakout |
| 2025-10-08 16:00 | Valid swing, away from level | n/a | 719.3% | 2.80x | Reversal | -0.266% | Liquidity sweep / reversal |
| 2024-12-28 11:00 | Valid swing, away from level | n/a | -88.1% | 2.80x | Impulse / continuation | 0.218% | True breakout |
| 2025-10-16 14:30 | Valid swing, away from level | n/a | -30.4% | 2.80x | Reversal | 0.027% | Liquidity sweep / reversal |
| 2025-10-14 10:15 | Valid swing, away from level | 78.6% | 89.5% | 2.80x | Flat / fading | 0.007% | Weak move without breakout |
| 2025-03-19 18:15 | Valid swing, away from level | n/a | -51.9% | 2.80x | Flat / fading | 0.249% | Weak move without breakout |
| 2024-12-13 10:45 | Valid swing, away from level | n/a | 112.7% | 2.80x | Impulse / continuation | -0.520% | True breakout |
| 2025-09-16 10:00 | Valid swing, away from level | n/a | -42.6% | 2.80x | Impulse / continuation | 0.126% | True breakout |
| 2026-09-15 11:45 | Valid swing, away from level | 78.6% | 94.9% | 2.80x | Reversal | 0.212% | Liquidity sweep / reversal |
| 2025-11-10 07:45 | Valid swing, away from level | n/a | -494.1% | 2.80x | Reversal | -0.100% | Liquidity sweep / reversal |
| 2026-05-16 11:00 | Near Fib level | 78.6% | 82.0% | 2.80x | Flat / fading | 0.052% | Position building in range |
| 2025-01-24 11:15 | Valid swing, away from level | n/a | -62.4% | 2.80x | Flat / fading | -0.145% | Weak move without breakout |
| 2025-09-04 15:45 | Golden zone 50-61.8% | 50.0% | 54.4% | 2.80x | Reversal | 0.337% | Liquidity sweep / reversal |
| 2025-05-05 07:45 | Valid swing, away from level | n/a | 103.8% | 2.80x | Impulse / continuation | 0.179% | True breakout |
| 2026-08-27 11:00 | Near Fib level | 50.0% | 48.5% | 2.80x | Impulse / continuation | 0.996% | True breakout |
| 2025-04-16 11:30 | Golden zone 50-61.8% | 61.8% | 58.2% | 2.80x | Reversal | 0.057% | Liquidity sweep / reversal |
| 2025-10-30 10:45 | Valid swing, away from level | n/a | -95.7% | 2.80x | Flat / fading | 0.258% | Weak move without breakout |
| 2026-07-06 07:45 | Valid swing, away from level | 38.2% | 26.0% | 2.80x | Impulse / continuation | -0.268% | True breakout |
| 2026-01-27 14:15 | Valid swing, away from level | n/a | -34.2% | 2.80x | Reversal | -0.078% | Liquidity sweep / reversal |
| 2025-06-27 16:45 | Valid swing, away from level | n/a | -98.1% | 2.80x | Flat / fading | 0.000% | Weak move without breakout |
| 2024-11-21 11:00 | Valid swing, away from level | 78.6% | 89.2% | 2.80x | Reversal | -0.906% | Liquidity sweep / reversal |
| 2025-04-03 14:15 | Valid swing, away from level | n/a | 102.7% | 2.80x | Flat / fading | -0.342% | Weak move without breakout |
| 2026-01-20 11:30 | Valid swing, away from level | n/a | 128.2% | 2.79x | Reversal | 0.134% | Liquidity sweep / reversal |
| 2025-02-27 19:15 | Near Fib level | 61.8% | 65.2% | 2.79x | Flat / fading | 0.067% | Position building in range |
| 2025-06-02 17:45 | Valid swing, away from level | n/a | -9.9% | 2.79x | Impulse / continuation | 0.483% | True breakout |
| 2026-05-06 13:00 | Valid swing, away from level | n/a | 187.7% | 2.79x | Reversal | 0.150% | Liquidity sweep / reversal |
| 2025-02-17 12:45 | Valid swing, away from level | n/a | -428.1% | 2.79x | Flat / fading | 0.098% | Weak move without breakout |
| 2026-01-12 14:15 | Valid swing, away from level | n/a | 109.8% | 2.79x | Flat / fading | -0.006% | Weak move without breakout |
| 2025-08-08 17:45 | Valid swing, away from level | 38.2% | 27.9% | 2.79x | Impulse / continuation | 0.096% | True breakout |
| 2026-02-26 07:00 | Valid swing, away from level | 38.2% | 25.0% | 2.79x | Flat / fading | -0.040% | Weak move without breakout |
| 2026-01-13 11:30 | Valid swing, away from level | n/a | 180.0% | 2.79x | Reversal | 0.087% | Liquidity sweep / reversal |
| 2025-01-06 11:15 | Valid swing, away from level | n/a | 177.9% | 2.79x | Impulse / continuation | 0.478% | True breakout |
| 2026-06-18 15:00 | Valid swing, away from level | n/a | 462.5% | 2.79x | Reversal | 0.358% | Liquidity sweep / reversal |
| 2025-08-13 07:00 | Near Fib level | 50.0% | 46.5% | 2.79x | Flat / fading | -0.030% | Weak move without breakout |
| 2025-10-07 10:15 | Valid swing, away from level | 38.2% | 8.9% | 2.79x | Impulse / continuation | 1.097% | True breakout |
| 2025-12-30 11:00 | Valid swing, away from level | 78.6% | 95.2% | 2.79x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-01-10 13:45 | Valid swing, away from level | n/a | -30.3% | 2.79x | Impulse / continuation | 0.086% | True breakout |
| 2025-10-08 07:15 | Valid swing, away from level | 38.2% | 17.3% | 2.79x | Reversal | -0.066% | Liquidity sweep / reversal |
| 2025-03-15 16:15 | Valid swing, away from level | 38.2% | 3.8% | 2.78x | Reversal | 0.029% | Liquidity sweep / reversal |
| 2026-01-28 17:15 | Near Fib level | 50.0% | 47.4% | 2.78x | Reversal | -0.138% | Liquidity sweep / reversal |
| 2026-09-10 17:45 | Valid swing, away from level | n/a | -47.1% | 2.78x | Reversal | 0.396% | Liquidity sweep / reversal |
| 2025-07-30 09:45 | Valid swing, away from level | 38.2% | 30.7% | 2.78x | Impulse / continuation | -0.390% | True breakout |
| 2025-10-06 11:00 | Valid swing, away from level | n/a | 146.5% | 2.78x | Flat / fading | 0.220% | Weak move without breakout |
| 2025-12-28 18:00 | Near Fib level | 38.2% | 38.7% | 2.78x | Reversal | 0.358% | Liquidity sweep / reversal |
| 2026-01-16 09:30 | Valid swing, away from level | n/a | -16.0% | 2.78x | Impulse / continuation | 0.255% | True breakout |
| 2026-09-18 08:00 | Valid swing, away from level | 38.2% | 23.3% | 2.78x | Reversal | -0.260% | Liquidity sweep / reversal |
| 2026-06-10 09:00 | Valid swing, away from level | 38.2% | 19.7% | 2.78x | Impulse / continuation | -0.452% | True breakout |
| 2025-07-01 09:15 | Valid swing, away from level | n/a | -14.5% | 2.78x | Impulse -> reversal | -0.085% | False breakout |
| 2025-07-14 08:15 | Valid swing, away from level | n/a | 145.8% | 2.78x | Reversal | 0.560% | Liquidity sweep / reversal |
| 2024-11-11 10:30 | Valid swing, away from level | n/a | -240.0% | 2.78x | Impulse / continuation | 0.604% | True breakout |
| 2024-12-09 16:45 | Valid swing, away from level | n/a | -65.6% | 2.78x | Reversal | -0.233% | Liquidity sweep / reversal |
| 2025-02-27 15:30 | Valid swing, away from level | n/a | -13.9% | 2.78x | Flat / fading | 0.126% | Weak move without breakout |
| 2026-01-06 09:15 | Valid swing, away from level | n/a | -29.1% | 2.78x | Impulse / continuation | 0.396% | True breakout |
| 2026-07-23 10:30 | Valid swing, away from level | n/a | 110.2% | 2.77x | Impulse / continuation | -1.214% | True breakout |
| 2026-01-30 21:00 | Valid swing, away from level | n/a | 114.9% | 2.77x | Flat / fading | 0.018% | Weak move without breakout |
| 2025-05-13 11:15 | Near Fib level | 38.2% | 40.6% | 2.77x | Impulse / continuation | -0.253% | True breakout |
| 2024-10-15 11:15 | Valid swing, away from level | n/a | -17.5% | 2.77x | Reversal | -0.418% | Liquidity sweep / reversal |
| 2026-07-02 14:30 | Valid swing, away from level | n/a | 448.3% | 2.77x | Impulse / continuation | -1.189% | True breakout |
| 2025-06-10 07:15 | Valid swing, away from level | n/a | -34.0% | 2.77x | Flat / fading | -0.056% | Weak move without breakout |
| 2025-11-28 12:00 | Near Fib level | 78.6% | 83.1% | 2.77x | Reversal | 0.465% | Liquidity sweep / reversal |
| 2026-05-11 13:00 | Valid swing, away from level | 38.2% | 5.9% | 2.77x | Flat / fading | 0.019% | Position building in range |
| 2026-05-02 14:00 | Near Fib level | 78.6% | 83.0% | 2.77x | Flat / fading | 0.007% | Weak move without breakout |
| 2026-05-04 08:00 | Valid swing, away from level | n/a | -208.5% | 2.77x | Impulse -> reversal | 0.078% | False breakout |
| 2025-10-01 17:15 | Valid swing, away from level | n/a | 158.5% | 2.77x | Flat / fading | 0.210% | Weak move without breakout |
| 2025-04-16 19:00 | Valid swing, away from level | n/a | -93.3% | 2.77x | Flat / fading | 0.038% | Weak move without breakout |
| 2026-04-01 07:30 | Near Fib level | 61.8% | 65.1% | 2.77x | Flat / fading | -0.154% | Weak move without breakout |
| 2025-04-08 19:30 | Valid swing, away from level | n/a | 127.8% | 2.77x | Impulse / continuation | 0.039% | True breakout |
| 2025-11-12 10:45 | Valid swing, away from level | n/a | 123.7% | 2.77x | Flat / fading | -0.027% | Weak move without breakout |
| 2026-02-01 14:45 | Valid swing, away from level | n/a | -5.7% | 2.77x | Flat / fading | -0.024% | Weak move without breakout |
| 2025-09-05 09:00 | Valid swing, away from level | 38.2% | 23.6% | 2.77x | Reversal | -0.072% | Liquidity sweep / reversal |
| 2026-08-18 08:00 | Valid swing, away from level | 38.2% | 22.3% | 2.77x | Reversal | -0.245% | Liquidity sweep / reversal |
| 2025-06-01 16:00 | Valid swing, away from level | 61.8% | 68.6% | 2.77x | Reversal | -0.057% | Liquidity sweep / reversal |
| 2026-03-03 12:15 | Valid swing, away from level | n/a | 171.6% | 2.77x | Flat / fading | -0.183% | Weak move without breakout |
| 2025-11-05 08:00 | Valid swing, away from level | n/a | 148.2% | 2.77x | Impulse / continuation | 0.315% | True breakout |
| 2024-11-27 12:45 | Valid swing, away from level | 61.8% | 67.3% | 2.77x | Impulse / continuation | 0.175% | True breakout |
| 2026-08-14 10:00 | Valid swing, away from level | 38.2% | 19.3% | 2.77x | Flat / fading | 0.082% | Weak move without breakout |
| 2025-09-10 12:15 | Valid swing, away from level | n/a | 113.7% | 2.77x | Flat / fading | 0.078% | Weak move without breakout |
| 2025-05-22 08:30 | Valid swing, away from level | n/a | 167.9% | 2.77x | Impulse / continuation | -0.383% | True breakout |
| 2026-09-04 09:45 | Valid swing, away from level | n/a | -4.8% | 2.77x | Reversal | -0.076% | Liquidity sweep / reversal |
| 2026-09-11 10:00 | Valid swing, away from level | 78.6% | 94.8% | 2.77x | Flat / fading | 0.123% | Weak move without breakout |
| 2025-12-04 23:30 | Valid swing, away from level | 78.6% | 71.6% | 2.77x | Impulse / continuation | 0.141% | True breakout |
| 2025-07-26 17:45 | Valid swing, away from level | n/a | 101.0% | 2.77x | Impulse / continuation | 0.000% | True breakout |
| 2025-09-22 10:00 | Valid swing, away from level | n/a | 107.3% | 2.77x | Flat / fading | -0.149% | Weak move without breakout |
| 2024-11-18 18:15 | Valid swing, away from level | n/a | -68.4% | 2.77x | Flat / fading | -0.474% | Position building in range |
| 2025-12-03 11:00 | Valid swing, away from level | n/a | 108.9% | 2.77x | Reversal | 0.449% | Liquidity sweep / reversal |
| 2024-11-07 13:00 | Valid swing, away from level | 78.6% | 83.8% | 2.77x | Flat / fading | 0.144% | Weak move without breakout |
| 2024-10-09 11:15 | Near Fib level | 38.2% | 33.3% | 2.77x | Impulse / continuation | -0.236% | True breakout |
| 2025-05-06 09:00 | Near Fib level | 78.6% | 83.3% | 2.77x | Impulse -> reversal | 0.533% | False breakout |
| 2024-11-22 17:30 | Valid swing, away from level | n/a | 201.1% | 2.77x | Reversal | -2.312% | Liquidity sweep / reversal |
| 2026-09-06 11:15 | Valid swing, away from level | 61.8% | 68.9% | 2.77x | Flat / fading | 0.175% | Weak move without breakout |
| 2025-09-16 12:00 | Valid swing, away from level | n/a | 127.9% | 2.77x | Impulse / continuation | -0.330% | True breakout |
| 2026-03-02 18:00 | Valid swing, away from level | n/a | 114.9% | 2.77x | Impulse / continuation | -0.356% | True breakout |
| 2026-01-29 10:30 | Valid swing, away from level | n/a | -124.2% | 2.76x | Reversal | 0.274% | Liquidity sweep / reversal |
| 2026-09-19 10:00 | Valid swing, away from level | 78.6% | 73.1% | 2.76x | Flat / fading | 0.016% | Position building in range |
| 2025-03-16 17:15 | Valid swing, away from level | n/a | -1854.5% | 2.76x | Reversal | 0.086% | Liquidity sweep / reversal |
| 2026-08-14 11:15 | Valid swing, away from level | 78.6% | 85.4% | 2.76x | Impulse / continuation | -1.299% | True breakout |
| 2025-06-08 17:00 | Valid swing, away from level | n/a | 210.5% | 2.76x | Reversal | 0.137% | Liquidity sweep / reversal |
| 2025-08-07 23:15 | Near Fib level | 38.2% | 39.9% | 2.76x | Flat / fading | 0.187% | Weak move without breakout |
| 2025-07-25 12:30 | Valid swing, away from level | n/a | 119.7% | 2.76x | Reversal | 0.456% | Liquidity sweep / reversal |
| 2025-07-28 09:45 | Valid swing, away from level | n/a | -477.8% | 2.76x | Reversal | -0.270% | Liquidity sweep / reversal |
| 2026-03-31 11:00 | Valid swing, away from level | n/a | -65.5% | 2.76x | Impulse / continuation | 0.958% | True breakout |
| 2025-12-08 17:15 | Valid swing, away from level | n/a | 156.1% | 2.76x | Flat / fading | 0.044% | Weak move without breakout |
| 2025-03-24 07:15 | Valid swing, away from level | 78.6% | 87.5% | 2.76x | Flat / fading | -0.011% | Weak move without breakout |
| 2024-09-27 12:00 | Valid swing, away from level | n/a | -188.0% | 2.76x | Reversal | -0.057% | Liquidity sweep / reversal |
| 2026-05-02 18:30 | Near Fib level | 78.6% | 83.0% | 2.76x | Impulse / continuation | 0.013% | True breakout |
| 2026-02-18 07:00 | Near Fib level | 50.0% | 47.8% | 2.76x | Impulse / continuation | -0.247% | True breakout |
| 2024-09-27 11:00 | Valid swing, away from level | n/a | -9.5% | 2.76x | Reversal | 0.819% | Liquidity sweep / reversal |
| 2025-03-12 10:30 | Golden zone 50-61.8% | 61.8% | 56.5% | 2.76x | Impulse / continuation | -0.311% | True breakout |
| 2025-04-17 21:00 | Valid swing, away from level | 38.2% | 25.4% | 2.75x | Reversal | 0.382% | Liquidity sweep / reversal |
| 2026-04-08 07:30 | Valid swing, away from level | 78.6% | 71.6% | 2.75x | Reversal | 0.081% | Liquidity sweep / reversal |
| 2025-10-15 14:30 | Valid swing, away from level | n/a | -10.9% | 2.75x | Impulse / continuation | 0.021% | True breakout |
| 2025-12-01 21:00 | Near Fib level | 38.2% | 34.6% | 2.75x | Flat / fading | -0.006% | Position building in range |
| 2026-01-29 09:15 | Valid swing, away from level | 38.2% | 11.3% | 2.75x | Impulse / continuation | 0.569% | True breakout |
| 2026-01-13 09:45 | Valid swing, away from level | n/a | 101.4% | 2.75x | Reversal | -0.136% | Liquidity sweep / reversal |
| 2026-01-19 11:00 | Valid swing, away from level | 38.2% | 5.5% | 2.75x | Impulse / continuation | 0.232% | True breakout |
| 2025-03-14 11:30 | Valid swing, away from level | 61.8% | 69.6% | 2.75x | Flat / fading | 0.196% | Weak move without breakout |
| 2026-09-18 21:45 | Golden zone 50-61.8% | 50.0% | 55.1% | 2.75x | Flat / fading | 0.024% | Position building in range |
| 2026-05-27 11:00 | Valid swing, away from level | 78.6% | 71.7% | 2.75x | Reversal | 0.133% | Liquidity sweep / reversal |
| 2025-11-05 16:45 | Valid swing, away from level | n/a | -8.9% | 2.75x | Impulse / continuation | -0.460% | True breakout |
| 2025-04-09 20:45 | Valid swing, away from level | n/a | -40.4% | 2.75x | Flat / fading | -2.083% | Weak move without breakout |
| 2026-06-10 10:00 | Valid swing, away from level | 38.2% | 29.7% | 2.75x | Reversal | -0.278% | Liquidity sweep / reversal |
| 2026-03-12 07:00 | Near Fib level | 78.6% | 73.9% | 2.75x | Flat / fading | -0.130% | Weak move without breakout |
| 2026-09-05 11:30 | Valid swing, away from level | n/a | -35.4% | 2.75x | Impulse / continuation | -0.747% | True breakout |
| 2025-04-02 16:45 | Near Fib level | 78.6% | 73.8% | 2.75x | Flat / fading | 0.300% | Position building in range |
| 2025-01-24 16:30 | Near Fib level | 38.2% | 38.3% | 2.75x | Impulse / continuation | -0.066% | True breakout |
| 2025-08-20 14:15 | Valid swing, away from level | 78.6% | 85.7% | 2.75x | Reversal | 0.130% | Liquidity sweep / reversal |
| 2025-04-08 10:00 | Valid swing, away from level | 38.2% | 27.4% | 2.75x | Impulse / continuation | -0.737% | True breakout |
| 2026-02-16 16:45 | Valid swing, away from level | n/a | -32.2% | 2.75x | Impulse / continuation | -0.081% | True breakout |
| 2026-04-22 17:45 | Valid swing, away from level | n/a | -31.1% | 2.74x | Flat / fading | -0.049% | Weak move without breakout |
| 2025-08-13 10:00 | Valid swing, away from level | 38.2% | 4.0% | 2.74x | Reversal | -0.150% | Liquidity sweep / reversal |
| 2025-09-12 16:30 | Valid swing, away from level | n/a | 361.1% | 2.74x | Flat / fading | 0.144% | Weak move without breakout |
| 2025-10-01 17:30 | Valid swing, away from level | n/a | 160.5% | 2.74x | Reversal | -0.059% | Liquidity sweep / reversal |
| 2026-07-03 09:15 | Valid swing, away from level | n/a | 106.1% | 2.74x | Flat / fading | 0.412% | Weak move without breakout |
| 2026-05-02 18:45 | Near Fib level | 78.6% | 78.7% | 2.74x | Flat / fading | 0.013% | Weak move without breakout |
| 2025-02-28 19:45 | Valid swing, away from level | n/a | -80.3% | 2.74x | Impulse / continuation | 1.090% | True breakout |
| 2025-07-22 18:00 | Valid swing, away from level | n/a | 114.1% | 2.74x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-03-23 09:30 | Near Fib level | 78.6% | 73.7% | 2.74x | Impulse / continuation | -0.006% | True breakout |
| 2025-07-02 18:30 | Valid swing, away from level | 78.6% | 84.2% | 2.74x | Reversal | 0.123% | Liquidity sweep / reversal |
| 2025-12-19 13:45 | Near Fib level | 78.6% | 74.8% | 2.74x | Flat / fading | 0.310% | Weak move without breakout |
| 2025-08-13 17:15 | Valid swing, away from level | 38.2% | 32.3% | 2.74x | Reversal | 0.162% | Liquidity sweep / reversal |
| 2026-05-26 20:30 | Near Fib level | 78.6% | 82.3% | 2.74x | Flat / fading | 0.165% | Weak move without breakout |
| 2025-12-22 08:00 | Valid swing, away from level | n/a | -6.2% | 2.74x | Reversal | -0.244% | Liquidity sweep / reversal |
| 2026-07-13 07:45 | Valid swing, away from level | n/a | -31.6% | 2.74x | Flat / fading | -0.088% | Weak move without breakout |
| 2025-03-26 07:00 | Valid swing, away from level | 38.2% | 1.3% | 2.74x | Reversal | 0.044% | Liquidity sweep / reversal |
| 2025-08-05 10:45 | Valid swing, away from level | n/a | -7.3% | 2.74x | Flat / fading | 0.031% | Weak move without breakout |
| 2025-09-25 19:15 | Valid swing, away from level | n/a | 177.8% | 2.74x | Flat / fading | -0.071% | Weak move without breakout |
| 2026-07-26 10:30 | Valid swing, away from level | 38.2% | 9.8% | 2.74x | Flat / fading | -0.517% | Weak move without breakout |
| 2026-07-30 08:15 | Valid swing, away from level | n/a | -28.3% | 2.74x | Flat / fading | -0.141% | Weak move without breakout |
| 2025-08-20 07:00 | Valid swing, away from level | 38.2% | 12.0% | 2.74x | Reversal | 0.241% | Liquidity sweep / reversal |
| 2026-03-20 10:00 | Valid swing, away from level | 38.2% | 29.1% | 2.74x | Reversal | 0.736% | Liquidity sweep / reversal |
| 2026-06-18 10:45 | Valid swing, away from level | n/a | 273.4% | 2.74x | Flat / fading | 0.109% | Weak move without breakout |
| 2026-03-18 22:45 | Golden zone 50-61.8% | 50.0% | 55.6% | 2.74x | Impulse / continuation | 0.000% | True breakout |
| 2025-02-07 10:30 | Golden zone 50-61.8% | 50.0% | 54.4% | 2.73x | Reversal | -0.032% | Liquidity sweep / reversal |
| 2024-11-02 17:45 | Valid swing, away from level | n/a | 273.6% | 2.73x | Reversal | -0.899% | Liquidity sweep / reversal |
| 2024-11-15 11:45 | Valid swing, away from level | 38.2% | 13.9% | 2.73x | Reversal | -0.288% | Liquidity sweep / reversal |
| 2026-02-28 12:45 | Near Fib level | 78.6% | 78.1% | 2.73x | Flat / fading | 0.035% | Weak move without breakout |
| 2024-10-07 12:30 | Valid swing, away from level | n/a | 200.0% | 2.73x | Flat / fading | 0.040% | Position building in range |
| 2026-08-06 11:45 | Near Fib level | 50.0% | 49.7% | 2.73x | Impulse / continuation | -0.014% | True breakout |
| 2024-10-09 14:45 | Valid swing, away from level | n/a | -115.7% | 2.73x | Reversal | -0.446% | Liquidity sweep / reversal |
| 2025-04-30 07:30 | Valid swing, away from level | n/a | 124.2% | 2.73x | Impulse / continuation | -0.038% | True breakout |
| 2026-07-01 09:45 | Valid swing, away from level | n/a | -77.6% | 2.73x | Reversal | -0.591% | Liquidity sweep / reversal |
| 2026-01-06 09:45 | Valid swing, away from level | n/a | -101.8% | 2.73x | Impulse / continuation | 0.219% | True breakout |
| 2025-09-10 07:00 | Valid swing, away from level | 38.2% | 27.3% | 2.73x | Impulse / continuation | -0.185% | True breakout |
| 2026-03-24 11:15 | Valid swing, away from level | n/a | -190.5% | 2.73x | Impulse / continuation | 0.167% | True breakout |
| 2025-12-26 11:00 | Valid swing, away from level | n/a | -571.4% | 2.73x | Reversal | -0.280% | Liquidity sweep / reversal |
| 2026-03-26 10:30 | Valid swing, away from level | 78.6% | 100.0% | 2.73x | Reversal | -0.349% | Liquidity sweep / reversal |
| 2025-04-30 15:00 | Near Fib level | 61.8% | 61.8% | 2.73x | Reversal | -0.684% | Liquidity sweep / reversal |
| 2025-07-14 18:00 | Valid swing, away from level | 38.2% | 19.8% | 2.73x | Impulse / continuation | 1.638% | True breakout |
| 2025-04-28 13:45 | Valid swing, away from level | n/a | 386.2% | 2.73x | Reversal | 0.938% | Liquidity sweep / reversal |
| 2025-06-06 10:00 | Valid swing, away from level | 38.2% | 29.9% | 2.73x | Reversal | 0.997% | Liquidity sweep / reversal |
| 2025-07-04 10:15 | Valid swing, away from level | 50.0% | 44.9% | 2.73x | Reversal | -0.695% | Liquidity sweep / reversal |
| 2026-04-20 15:45 | Valid swing, away from level | n/a | 107.0% | 2.73x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-05-16 15:30 | Valid swing, away from level | n/a | 340.0% | 2.72x | Reversal | 1.230% | Liquidity sweep / reversal |
| 2025-07-28 14:45 | Near Fib level | 78.6% | 74.3% | 2.72x | Impulse / continuation | -1.164% | True breakout |
| 2026-06-26 15:45 | Valid swing, away from level | n/a | -173.5% | 2.72x | Reversal | -1.587% | Liquidity sweep / reversal |
| 2024-10-25 14:15 | Valid swing, away from level | 78.6% | 72.4% | 2.72x | Flat / fading | -0.435% | Weak move without breakout |
| 2025-03-17 10:00 | Valid swing, away from level | n/a | -3145.5% | 2.72x | Flat / fading | 0.273% | Position building in range |
| 2024-11-08 10:30 | Valid swing, away from level | n/a | -550.8% | 2.72x | Impulse / continuation | -0.428% | True breakout |
| 2025-07-31 09:45 | Golden zone 50-61.8% | 61.8% | 59.0% | 2.72x | Impulse -> reversal | -0.120% | False breakout |
| 2025-06-05 09:15 | Valid swing, away from level | n/a | -5.2% | 2.72x | Flat / fading | -0.060% | Weak move without breakout |
| 2025-09-29 09:30 | Valid swing, away from level | n/a | -95.7% | 2.72x | Reversal | 0.474% | Liquidity sweep / reversal |
| 2025-07-19 10:00 | Valid swing, away from level | 38.2% | 18.6% | 2.72x | Impulse / continuation | 0.191% | True breakout |
| 2025-06-10 13:00 | Near Fib level | 78.6% | 73.7% | 2.72x | Impulse / continuation | -0.031% | True breakout |
| 2026-06-22 09:00 | Near Fib level | 78.6% | 76.7% | 2.72x | Impulse / continuation | -0.092% | True breakout |
| 2024-09-25 11:00 | Valid swing, away from level | 38.2% | 29.3% | 2.72x | Impulse / continuation | 2.640% | True breakout |
| 2026-03-12 07:15 | Near Fib level | 78.6% | 79.3% | 2.72x | Reversal | 0.036% | Liquidity sweep / reversal |
| 2026-02-17 07:30 | Near Fib level | 38.2% | 36.1% | 2.72x | Flat / fading | 0.058% | Weak move without breakout |
| 2026-01-06 23:00 | Valid swing, away from level | n/a | -33.9% | 2.72x | Impulse -> reversal | -0.977% | False breakout |
| 2025-01-08 10:45 | Valid swing, away from level | n/a | -44.4% | 2.72x | Impulse / continuation | 0.198% | True breakout |
| 2025-06-11 08:15 | Valid swing, away from level | n/a | 123.4% | 2.72x | Reversal | 0.345% | Liquidity sweep / reversal |
| 2026-07-10 08:45 | Valid swing, away from level | 78.6% | 87.7% | 2.72x | Impulse / continuation | 0.418% | True breakout |
| 2026-06-24 07:15 | Valid swing, away from level | 38.2% | 18.8% | 2.72x | Reversal | 0.469% | Liquidity sweep / reversal |
| 2025-09-01 10:45 | Valid swing, away from level | n/a | -208.7% | 2.72x | Flat / fading | 0.036% | Weak move without breakout |
| 2026-03-12 17:15 | Valid swing, away from level | n/a | -9.7% | 2.72x | Reversal | -0.431% | Liquidity sweep / reversal |
| 2025-05-30 12:30 | Valid swing, away from level | 38.2% | 18.8% | 2.72x | Reversal | 0.269% | Liquidity sweep / reversal |
| 2026-05-19 09:15 | Valid swing, away from level | 38.2% | 10.6% | 2.72x | Flat / fading | -0.128% | Weak move without breakout |
| 2026-01-05 17:00 | Valid swing, away from level | n/a | -14.7% | 2.72x | Reversal | 0.079% | Liquidity sweep / reversal |
| 2026-08-19 11:00 | Valid swing, away from level | n/a | 204.5% | 2.72x | Reversal | 0.505% | Liquidity sweep / reversal |
| 2026-01-28 23:30 | Valid swing, away from level | 78.6% | 100.0% | 2.71x | Impulse / continuation | 0.168% | True breakout |
| 2026-01-23 21:00 | Valid swing, away from level | n/a | -44.2% | 2.71x | Impulse / continuation | -0.030% | True breakout |
| 2026-01-21 13:30 | Valid swing, away from level | n/a | -161.4% | 2.71x | Flat / fading | 0.139% | Weak move without breakout |
| 2025-12-02 13:45 | Valid swing, away from level | n/a | -19.4% | 2.71x | Flat / fading | -0.146% | Weak move without breakout |
| 2025-03-18 16:45 | Valid swing, away from level | n/a | -141.9% | 2.71x | Reversal | 0.861% | Liquidity sweep / reversal |
| 2026-06-03 09:00 | Valid swing, away from level | 38.2% | 25.8% | 2.71x | Impulse / continuation | -0.169% | True breakout |
| 2026-05-06 11:30 | Valid swing, away from level | n/a | -8.6% | 2.71x | Reversal | -0.560% | Liquidity sweep / reversal |
| 2025-03-07 18:15 | Valid swing, away from level | n/a | 105.6% | 2.71x | Reversal | 0.836% | Liquidity sweep / reversal |
| 2025-05-26 10:00 | Valid swing, away from level | n/a | 224.0% | 2.71x | Flat / fading | 0.198% | Weak move without breakout |
| 2026-04-07 14:30 | Valid swing, away from level | 78.6% | 88.9% | 2.71x | Impulse / continuation | -0.150% | True breakout |
| 2025-12-02 23:30 | Valid swing, away from level | 78.6% | 73.3% | 2.71x | Impulse / continuation | -1.182% | True breakout |
| 2026-04-23 10:45 | Valid swing, away from level | 38.2% | 8.4% | 2.71x | Impulse / continuation | -0.202% | True breakout |
| 2025-07-21 08:45 | Valid swing, away from level | n/a | -252.6% | 2.71x | Reversal | -0.255% | Liquidity sweep / reversal |
| 2025-01-23 18:00 | Valid swing, away from level | n/a | 112.3% | 2.71x | Flat / fading | 0.134% | Weak move without breakout |
| 2025-02-10 10:30 | Valid swing, away from level | n/a | -818.2% | 2.71x | Reversal | -0.436% | Liquidity sweep / reversal |
| 2026-07-20 16:15 | Valid swing, away from level | n/a | -157.5% | 2.71x | Reversal | -0.933% | Liquidity sweep / reversal |
| 2025-10-24 10:00 | Valid swing, away from level | 38.2% | 10.2% | 2.71x | Impulse / continuation | -0.400% | True breakout |
| 2026-07-16 09:15 | Valid swing, away from level | n/a | 158.9% | 2.70x | Reversal | -0.655% | Liquidity sweep / reversal |
| 2026-07-04 11:45 | Valid swing, away from level | 78.6% | 96.2% | 2.70x | Reversal | 0.183% | Liquidity sweep / reversal |
| 2026-09-24 11:30 | Valid swing, away from level | 38.2% | 18.1% | 2.70x | Reversal | n/a | Liquidity sweep / reversal |
| 2025-05-23 09:45 | Golden zone 50-61.8% | 61.8% | 57.3% | 2.70x | Reversal | 0.319% | Liquidity sweep / reversal |
| 2025-05-28 12:45 | Valid swing, away from level | n/a | -147.8% | 2.70x | Impulse -> reversal | 0.208% | False breakout |
| 2026-05-08 21:15 | Valid swing, away from level | 38.2% | 16.4% | 2.70x | Impulse / continuation | 0.324% | True breakout |
| 2025-02-28 07:00 | Valid swing, away from level | n/a | 127.8% | 2.70x | Flat / fading | 0.000% | Weak move without breakout |
| 2025-05-05 17:15 | Valid swing, away from level | n/a | 332.5% | 2.70x | Impulse / continuation | -0.717% | True breakout |
| 2026-07-28 10:30 | Valid swing, away from level | n/a | 195.4% | 2.70x | Impulse / continuation | -0.176% | True breakout |
| 2026-03-06 23:30 | Valid swing, away from level | 78.6% | 97.8% | 2.70x | Reversal | -0.521% | Liquidity sweep / reversal |
| 2025-07-24 10:00 | Valid swing, away from level | 38.2% | 21.9% | 2.70x | Reversal | -0.574% | Liquidity sweep / reversal |
| 2025-01-28 14:15 | Valid swing, away from level | 38.2% | 5.4% | 2.70x | Impulse / continuation | 0.427% | True breakout |
| 2026-04-23 18:15 | Golden zone 50-61.8% | 61.8% | 58.7% | 2.70x | Reversal | 0.037% | Liquidity sweep / reversal |
| 2025-05-27 10:00 | Valid swing, away from level | n/a | -31.0% | 2.70x | Reversal | 0.131% | Liquidity sweep / reversal |
| 2026-09-11 14:15 | Golden zone 50-61.8% | 61.8% | 57.5% | 2.70x | Flat / fading | -0.459% | Weak move without breakout |
| 2026-07-02 13:00 | Valid swing, away from level | n/a | 244.9% | 2.69x | Impulse / continuation | -0.291% | True breakout |
| 2025-10-24 12:15 | Near Fib level | 78.6% | 78.9% | 2.69x | Reversal | 0.477% | Liquidity sweep / reversal |
| 2026-07-15 07:15 | Valid swing, away from level | 78.6% | 89.8% | 2.69x | Reversal | -0.032% | Liquidity sweep / reversal |
| 2025-09-25 10:15 | Near Fib level | 50.0% | 48.7% | 2.69x | Flat / fading | 0.026% | Weak move without breakout |
| 2026-06-11 23:30 | Valid swing, away from level | n/a | 105.2% | 2.69x | Reversal | 0.047% | Liquidity sweep / reversal |
| 2025-09-16 07:00 | Valid swing, away from level | 38.2% | 16.7% | 2.69x | Impulse / continuation | 0.082% | True breakout |
| 2025-12-02 09:00 | Golden zone 50-61.8% | 61.8% | 59.0% | 2.69x | Flat / fading | 0.096% | Weak move without breakout |
| 2025-10-31 10:45 | Valid swing, away from level | n/a | 110.5% | 2.69x | Reversal | -0.108% | Liquidity sweep / reversal |
| 2025-12-18 12:45 | Valid swing, away from level | 38.2% | 28.5% | 2.69x | Reversal | -0.074% | Liquidity sweep / reversal |
| 2026-04-29 07:00 | Valid swing, away from level | 78.6% | 91.9% | 2.69x | Impulse / continuation | 0.064% | True breakout |
| 2025-07-01 12:00 | Valid swing, away from level | 38.2% | 10.0% | 2.69x | Reversal | 0.061% | Liquidity sweep / reversal |
| 2026-01-23 10:15 | Valid swing, away from level | 38.2% | 31.4% | 2.69x | Reversal | 0.205% | Liquidity sweep / reversal |
| 2025-10-27 14:45 | Valid swing, away from level | 78.6% | 99.6% | 2.69x | Reversal | 0.537% | Liquidity sweep / reversal |
| 2026-09-02 18:45 | Valid swing, away from level | 38.2% | 16.7% | 2.69x | Flat / fading | -0.016% | Weak move without breakout |
| 2025-07-11 12:15 | Valid swing, away from level | n/a | 407.5% | 2.69x | Flat / fading | 0.164% | Weak move without breakout |
| 2025-01-27 11:15 | Valid swing, away from level | n/a | 227.8% | 2.69x | Impulse / continuation | -0.327% | True breakout |
| 2025-02-12 19:45 | Valid swing, away from level | 38.2% | 16.8% | 2.69x | Impulse / continuation | 3.985% | True breakout |
| 2026-01-28 07:15 | Valid swing, away from level | 38.2% | 25.8% | 2.69x | Flat / fading | 0.090% | Position building in range |
| 2024-12-30 10:30 | Valid swing, away from level | n/a | -334.2% | 2.69x | Impulse / continuation | 0.568% | True breakout |
| 2026-05-18 19:00 | Valid swing, away from level | n/a | -101.4% | 2.69x | Impulse / continuation | 0.148% | True breakout |
| 2024-11-07 12:00 | Near Fib level | 38.2% | 41.2% | 2.69x | Impulse / continuation | -0.533% | True breakout |
| 2025-03-31 10:45 | Valid swing, away from level | n/a | -50.2% | 2.69x | Reversal | 0.189% | Liquidity sweep / reversal |
| 2025-10-10 10:00 | Valid swing, away from level | 78.6% | 97.5% | 2.69x | Flat / fading | 0.061% | Weak move without breakout |
| 2026-02-02 10:15 | Valid swing, away from level | n/a | 159.1% | 2.68x | Reversal | -0.252% | Liquidity sweep / reversal |
| 2026-02-03 08:45 | Valid swing, away from level | n/a | -131.7% | 2.68x | Flat / fading | -0.084% | Position building in range |
| 2025-07-23 08:30 | Near Fib level | 50.0% | 46.7% | 2.68x | Reversal | -0.030% | Liquidity sweep / reversal |
| 2025-04-14 09:00 | Valid swing, away from level | 78.6% | 88.9% | 2.68x | Impulse / continuation | -0.342% | True breakout |
| 2025-08-11 07:30 | Valid swing, away from level | n/a | -165.5% | 2.68x | Flat / fading | 0.018% | Weak move without breakout |
| 2026-05-08 12:15 | Valid swing, away from level | 78.6% | 90.0% | 2.68x | Impulse / continuation | -0.397% | True breakout |
| 2025-12-08 13:45 | Valid swing, away from level | 78.6% | 92.4% | 2.68x | Flat / fading | 0.056% | Position building in range |
| 2026-01-19 09:15 | Near Fib level | 38.2% | 33.3% | 2.68x | Reversal | 0.092% | Liquidity sweep / reversal |
| 2026-07-15 08:00 | Valid swing, away from level | 78.6% | 93.5% | 2.68x | Impulse / continuation | -0.394% | True breakout |
| 2025-02-07 11:45 | Near Fib level | 78.6% | 74.4% | 2.68x | Flat / fading | -0.129% | Weak move without breakout |
| 2026-06-28 10:00 | Valid swing, away from level | 38.2% | 13.9% | 2.68x | Flat / fading | -0.038% | Weak move without breakout |
| 2025-12-18 11:00 | Valid swing, away from level | 38.2% | 24.2% | 2.68x | Impulse / continuation | -0.129% | True breakout |
| 2026-07-09 19:15 | Near Fib level | 50.0% | 46.7% | 2.68x | Flat / fading | -0.321% | Weak move without breakout |
| 2026-09-21 11:00 | Valid swing, away from level | n/a | -225.0% | 2.68x | Reversal | -0.268% | Liquidity sweep / reversal |
| 2026-08-08 10:00 | Valid swing, away from level | n/a | 284.2% | 2.68x | Flat / fading | -0.072% | Position building in range |
| 2026-02-06 17:00 | Valid swing, away from level | n/a | 153.7% | 2.68x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2025-12-13 17:45 | Golden zone 50-61.8% | 61.8% | 58.7% | 2.68x | Impulse / continuation | 0.025% | True breakout |
| 2025-02-12 18:30 | Valid swing, away from level | n/a | 168.7% | 2.68x | Reversal | 1.088% | Liquidity sweep / reversal |
| 2025-07-21 07:30 | Valid swing, away from level | n/a | -36.0% | 2.68x | Reversal | 0.452% | Liquidity sweep / reversal |
| 2026-07-29 07:15 | Valid swing, away from level | n/a | -7.9% | 2.67x | Flat / fading | -0.197% | Position building in range |
| 2026-05-18 10:45 | Valid swing, away from level | n/a | 321.7% | 2.67x | Flat / fading | 0.046% | Weak move without breakout |
| 2025-09-17 12:45 | Valid swing, away from level | n/a | 117.0% | 2.67x | Reversal | 0.440% | Liquidity sweep / reversal |
| 2026-09-15 18:45 | Valid swing, away from level | n/a | 101.9% | 2.67x | Flat / fading | -0.061% | Weak move without breakout |
| 2026-08-13 10:00 | Valid swing, away from level | 61.8% | 67.2% | 2.67x | Reversal | -0.675% | Liquidity sweep / reversal |
| 2026-07-16 23:45 | Valid swing, away from level | n/a | 143.3% | 2.67x | Reversal | 2.018% | Liquidity sweep / reversal |
| 2026-03-18 23:30 | Valid swing, away from level | 61.8% | 68.3% | 2.67x | Reversal | 0.299% | Liquidity sweep / reversal |
| 2026-05-22 23:30 | Near Fib level | 78.6% | 78.8% | 2.67x | Reversal | -1.142% | Liquidity sweep / reversal |
| 2025-08-06 16:45 | Golden zone 50-61.8% | 50.0% | 53.3% | 2.67x | Impulse / continuation | -0.317% | True breakout |
| 2026-02-05 09:15 | Valid swing, away from level | 78.6% | 88.1% | 2.67x | Reversal | 0.186% | Liquidity sweep / reversal |
| 2026-08-11 13:30 | Valid swing, away from level | n/a | -8.9% | 2.67x | Flat / fading | 0.035% | Weak move without breakout |
| 2025-04-14 07:30 | Near Fib level | 61.8% | 63.8% | 2.67x | Reversal | 0.019% | Liquidity sweep / reversal |
| 2025-11-14 09:30 | Valid swing, away from level | 38.2% | 1.7% | 2.67x | Impulse / continuation | 0.007% | True breakout |
| 2026-01-21 09:00 | Near Fib level | 78.6% | 78.4% | 2.67x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2025-10-08 12:15 | Valid swing, away from level | n/a | 188.0% | 2.67x | Impulse / continuation | -0.543% | True breakout |
| 2026-02-04 18:15 | Valid swing, away from level | 78.6% | 89.1% | 2.67x | Impulse / continuation | -0.334% | True breakout |
| 2025-03-07 09:00 | Valid swing, away from level | n/a | -18.4% | 2.67x | Impulse / continuation | 0.459% | True breakout |
| 2024-12-09 16:15 | Valid swing, away from level | n/a | -32.8% | 2.67x | Impulse / continuation | 0.167% | True breakout |
| 2025-01-31 15:45 | Near Fib level | 78.6% | 77.8% | 2.67x | Impulse / continuation | -0.405% | True breakout |
| 2025-12-11 11:15 | Valid swing, away from level | n/a | -83.5% | 2.67x | Reversal | 0.258% | Liquidity sweep / reversal |
| 2026-05-26 17:15 | Golden zone 50-61.8% | 50.0% | 51.6% | 2.67x | Flat / fading | -0.172% | Position building in range |
| 2025-01-09 11:30 | Near Fib level | 38.2% | 35.1% | 2.67x | Impulse / continuation | -0.365% | True breakout |
| 2026-08-10 09:45 | Valid swing, away from level | 38.2% | 1.6% | 2.67x | Reversal | -0.293% | Liquidity sweep / reversal |
| 2024-10-22 18:00 | Valid swing, away from level | n/a | 123.4% | 2.67x | Flat / fading | -0.039% | Position building in range |
| 2026-08-06 07:15 | Valid swing, away from level | n/a | -401.2% | 2.67x | Impulse / continuation | -0.646% | True breakout |
| 2026-06-24 09:00 | Near Fib level | 38.2% | 37.8% | 2.67x | Impulse / continuation | -0.635% | True breakout |
| 2025-08-27 10:00 | Valid swing, away from level | n/a | -7.7% | 2.67x | Impulse / continuation | 0.260% | True breakout |
| 2025-04-06 16:30 | Valid swing, away from level | n/a | -710.7% | 2.67x | Reversal | 0.090% | Liquidity sweep / reversal |
| 2025-03-18 10:30 | Valid swing, away from level | n/a | -130.1% | 2.67x | Flat / fading | -0.067% | Weak move without breakout |
| 2026-04-29 11:45 | Near Fib level | 78.6% | 83.5% | 2.67x | Impulse / continuation | 0.058% | True breakout |
| 2025-10-03 07:30 | Valid swing, away from level | 38.2% | 9.8% | 2.66x | Impulse / continuation | 0.132% | True breakout |
| 2024-12-25 11:30 | Valid swing, away from level | 78.6% | 73.3% | 2.66x | Reversal | 0.689% | Liquidity sweep / reversal |
| 2025-07-14 19:15 | Valid swing, away from level | n/a | -95.9% | 2.66x | Reversal | -0.649% | Liquidity sweep / reversal |
| 2025-06-15 10:45 | Valid swing, away from level | n/a | 105.3% | 2.66x | Flat / fading | 0.006% | Position building in range |
| 2026-03-18 10:30 | Valid swing, away from level | n/a | -132.6% | 2.66x | Flat / fading | 0.006% | Weak move without breakout |
| 2026-03-28 18:00 | Valid swing, away from level | 78.6% | 97.1% | 2.66x | Impulse / continuation | -0.050% | True breakout |
| 2024-10-25 16:45 | Valid swing, away from level | n/a | 389.1% | 2.66x | Impulse / continuation | -0.915% | True breakout |
| 2026-07-24 09:30 | Valid swing, away from level | n/a | 101.9% | 2.66x | Reversal | -0.790% | Liquidity sweep / reversal |
| 2026-03-18 09:00 | Valid swing, away from level | 38.2% | 21.0% | 2.66x | Reversal | 0.119% | Liquidity sweep / reversal |
| 2026-03-13 08:45 | Valid swing, away from level | n/a | -123.2% | 2.66x | Impulse / continuation | -0.053% | True breakout |
| 2026-04-29 16:15 | Valid swing, away from level | n/a | 148.7% | 2.66x | Reversal | -0.652% | Liquidity sweep / reversal |
| 2026-05-07 16:30 | Valid swing, away from level | n/a | 103.8% | 2.66x | Flat / fading | 0.065% | Position building in range |
| 2026-06-15 16:45 | Valid swing, away from level | n/a | -13.2% | 2.66x | Reversal | -0.428% | Liquidity sweep / reversal |
| 2024-10-30 11:00 | Valid swing, away from level | n/a | -27.7% | 2.66x | Reversal | -0.188% | Liquidity sweep / reversal |
| 2026-03-04 07:30 | Valid swing, away from level | n/a | -115.6% | 2.66x | Flat / fading | 0.000% | Position building in range |
| 2025-09-01 18:00 | Valid swing, away from level | n/a | 183.7% | 2.66x | Flat / fading | -0.006% | Position building in range |
| 2025-05-27 11:30 | Valid swing, away from level | n/a | -67.3% | 2.66x | Flat / fading | -0.377% | Weak move without breakout |
| 2026-05-04 08:15 | Valid swing, away from level | n/a | -146.8% | 2.66x | Reversal | 0.221% | Liquidity sweep / reversal |
| 2026-06-25 10:45 | Valid swing, away from level | 78.6% | 70.8% | 2.66x | Reversal | 0.260% | Liquidity sweep / reversal |
| 2024-11-25 17:30 | Valid swing, away from level | n/a | 199.2% | 2.65x | Flat / fading | 0.549% | Weak move without breakout |
| 2026-05-05 13:00 | Valid swing, away from level | n/a | -15.7% | 2.65x | Reversal | 0.314% | Liquidity sweep / reversal |
| 2025-05-26 08:15 | Valid swing, away from level | n/a | 197.7% | 2.65x | Flat / fading | 0.178% | Weak move without breakout |
| 2025-05-06 18:00 | Valid swing, away from level | n/a | -91.0% | 2.65x | Reversal | -0.033% | Liquidity sweep / reversal |
| 2025-04-30 15:45 | Near Fib level | 78.6% | 73.9% | 2.65x | Flat / fading | -0.419% | Weak move without breakout |
| 2025-12-29 11:00 | Valid swing, away from level | n/a | -6.5% | 2.65x | Impulse / continuation | 1.314% | True breakout |
| 2024-09-30 22:45 | Valid swing, away from level | n/a | 158.3% | 2.65x | Flat / fading | -0.038% | Position building in range |
| 2026-08-11 07:15 | Valid swing, away from level | n/a | -69.6% | 2.65x | Impulse / continuation | 0.093% | True breakout |
| 2025-11-06 11:45 | Valid swing, away from level | n/a | 126.0% | 2.65x | Reversal | 0.108% | Liquidity sweep / reversal |
| 2026-06-28 16:45 | Valid swing, away from level | 50.0% | 44.1% | 2.65x | Flat / fading | -0.008% | Position building in range |
| 2026-02-11 08:00 | Near Fib level | 38.2% | 40.4% | 2.65x | Impulse / continuation | 0.085% | True breakout |
| 2026-02-16 16:30 | Valid swing, away from level | n/a | -13.4% | 2.65x | Impulse / continuation | 0.312% | True breakout |
| 2026-09-24 07:00 | Valid swing, away from level | n/a | -8.3% | 2.65x | Flat / fading | 0.177% | Position building in range |
| 2026-06-09 07:00 | Near Fib level | 61.8% | 66.3% | 2.65x | Flat / fading | 0.034% | Weak move without breakout |
| 2026-07-16 12:00 | Valid swing, away from level | n/a | 408.7% | 2.65x | Flat / fading | 1.005% | Position building in range |
| 2025-09-09 10:15 | Valid swing, away from level | n/a | -45.1% | 2.65x | Reversal | 0.077% | Liquidity sweep / reversal |
| 2025-02-10 07:30 | Valid swing, away from level | n/a | -324.0% | 2.65x | Flat / fading | 0.185% | Weak move without breakout |
| 2025-10-31 11:30 | Valid swing, away from level | n/a | 137.1% | 2.65x | Flat / fading | 0.270% | Position building in range |
| 2026-07-28 10:15 | Valid swing, away from level | n/a | 133.3% | 2.65x | Impulse / continuation | -0.920% | True breakout |
| 2026-06-24 10:00 | Valid swing, away from level | 78.6% | 86.7% | 2.65x | Impulse / continuation | -0.232% | True breakout |
| 2026-06-08 09:00 | Valid swing, away from level | n/a | -169.6% | 2.65x | Impulse / continuation | -0.261% | True breakout |
| 2026-08-18 09:30 | Valid swing, away from level | 38.2% | 7.0% | 2.65x | Reversal | -0.858% | Liquidity sweep / reversal |
| 2025-08-04 07:00 | Near Fib level | 38.2% | 37.4% | 2.65x | Reversal | -0.044% | Liquidity sweep / reversal |
| 2026-03-23 10:00 | Valid swing, away from level | n/a | 105.3% | 2.65x | Impulse / continuation | 0.186% | True breakout |
| 2025-11-10 09:15 | Valid swing, away from level | n/a | -435.3% | 2.65x | Impulse / continuation | 0.401% | True breakout |
| 2024-11-29 11:45 | Valid swing, away from level | n/a | -19.8% | 2.65x | Flat / fading | 0.184% | Weak move without breakout |
| 2026-02-24 10:30 | Valid swing, away from level | 38.2% | 17.5% | 2.65x | Reversal | -0.198% | Liquidity sweep / reversal |
| 2024-11-27 12:00 | Valid swing, away from level | 78.6% | 98.6% | 2.65x | Impulse / continuation | 1.358% | True breakout |
| 2025-03-07 08:30 | Valid swing, away from level | n/a | -37.4% | 2.65x | Impulse / continuation | 0.247% | True breakout |
| 2025-10-28 11:30 | Valid swing, away from level | n/a | -142.7% | 2.64x | Impulse / continuation | 0.931% | True breakout |
| 2026-01-28 10:30 | Valid swing, away from level | 78.6% | 97.6% | 2.64x | Flat / fading | 0.000% | Weak move without breakout |
| 2026-02-05 14:30 | Valid swing, away from level | n/a | 161.8% | 2.64x | Impulse / continuation | -0.048% | True breakout |
| 2026-08-03 09:00 | Valid swing, away from level | n/a | -155.1% | 2.64x | Reversal | 0.356% | Liquidity sweep / reversal |
| 2025-07-20 17:30 | Near Fib level | 50.0% | 48.0% | 2.64x | Reversal | -0.054% | Liquidity sweep / reversal |
| 2024-12-26 11:15 | Valid swing, away from level | n/a | -24.5% | 2.64x | Impulse / continuation | -0.423% | True breakout |
| 2025-01-24 17:00 | Golden zone 50-61.8% | 50.0% | 55.0% | 2.64x | Reversal | 0.433% | Liquidity sweep / reversal |
| 2025-08-11 10:00 | Valid swing, away from level | 38.2% | 17.1% | 2.64x | Impulse / continuation | -0.142% | True breakout |
| 2026-01-15 11:00 | Valid swing, away from level | 61.8% | 67.3% | 2.64x | Flat / fading | -0.131% | Position building in range |
| 2025-04-17 18:00 | Valid swing, away from level | 78.6% | 98.4% | 2.64x | Flat / fading | -0.057% | Weak move without breakout |
| 2026-03-19 17:15 | Valid swing, away from level | n/a | 210.1% | 2.64x | Impulse / continuation | 0.193% | True breakout |
| 2026-06-25 10:00 | Valid swing, away from level | 50.0% | 44.5% | 2.64x | Reversal | 0.037% | Liquidity sweep / reversal |
| 2026-08-12 10:00 | Valid swing, away from level | 38.2% | 15.8% | 2.64x | Impulse / continuation | -0.458% | True breakout |
| 2025-04-14 15:45 | Valid swing, away from level | n/a | 106.3% | 2.64x | Impulse / continuation | -0.446% | True breakout |
| 2025-02-07 09:30 | Near Fib level | 50.0% | 48.7% | 2.64x | Reversal | -0.071% | Liquidity sweep / reversal |
| 2026-07-13 07:00 | Valid swing, away from level | 38.2% | 22.5% | 2.64x | Reversal | 0.177% | Liquidity sweep / reversal |
| 2026-05-14 09:30 | Valid swing, away from level | 38.2% | 14.3% | 2.64x | Impulse / continuation | 0.019% | True breakout |
| 2026-07-16 08:00 | Valid swing, away from level | n/a | 139.5% | 2.64x | Impulse / continuation | -0.389% | True breakout |
| 2025-08-15 15:15 | Valid swing, away from level | n/a | -60.0% | 2.64x | Reversal | 0.292% | Liquidity sweep / reversal |
| 2025-08-13 17:00 | Valid swing, away from level | 38.2% | 44.0% | 2.64x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2025-08-18 16:15 | Valid swing, away from level | n/a | -155.6% | 2.64x | Impulse / continuation | 0.386% | True breakout |
| 2026-09-08 10:30 | Valid swing, away from level | n/a | 260.0% | 2.64x | Reversal | 0.199% | Liquidity sweep / reversal |
| 2025-06-02 07:00 | Golden zone 50-61.8% | 50.0% | 55.2% | 2.64x | Impulse / continuation | 0.286% | True breakout |
| 2024-12-11 10:30 | Valid swing, away from level | n/a | 138.8% | 2.64x | Impulse / continuation | -0.009% | True breakout |
| 2026-06-29 10:45 | Valid swing, away from level | n/a | 335.8% | 2.64x | Impulse / continuation | 2.138% | True breakout |
| 2025-09-26 18:15 | Valid swing, away from level | 38.2% | 26.3% | 2.64x | Flat / fading | 0.250% | Weak move without breakout |
| 2025-04-23 09:00 | Valid swing, away from level | 78.6% | 96.7% | 2.64x | Impulse / continuation | -0.229% | True breakout |
| 2026-07-06 07:30 | Valid swing, away from level | 38.2% | 24.7% | 2.64x | Impulse / continuation | -0.260% | True breakout |
| 2025-07-10 16:00 | Valid swing, away from level | n/a | -5.8% | 2.63x | Impulse / continuation | 0.125% | True breakout |
| 2025-11-24 11:30 | Near Fib level | 78.6% | 78.1% | 2.63x | Impulse / continuation | -0.568% | True breakout |
| 2026-09-06 10:00 | Near Fib level | 38.2% | 38.9% | 2.63x | Impulse / continuation | -0.667% | True breakout |
| 2025-06-20 13:45 | Valid swing, away from level | 38.2% | 5.1% | 2.63x | Flat / fading | -0.144% | Weak move without breakout |
| 2025-05-30 11:15 | Near Fib level | 78.6% | 80.3% | 2.63x | Reversal | 0.642% | Liquidity sweep / reversal |
| 2026-03-26 10:15 | Valid swing, away from level | n/a | 102.6% | 2.63x | Impulse / continuation | -0.252% | True breakout |
| 2026-04-24 12:15 | Valid swing, away from level | n/a | 142.9% | 2.63x | Reversal | 0.153% | Liquidity sweep / reversal |
| 2025-12-18 17:30 | Valid swing, away from level | n/a | 138.0% | 2.63x | Impulse / continuation | -0.056% | True breakout |
| 2025-08-22 13:15 | Valid swing, away from level | 50.0% | 44.3% | 2.63x | Reversal | -0.306% | Liquidity sweep / reversal |
| 2026-01-30 07:00 | Near Fib level | 38.2% | 36.9% | 2.63x | Reversal | -0.337% | Liquidity sweep / reversal |
| 2025-06-30 13:00 | Valid swing, away from level | n/a | 140.5% | 2.63x | Impulse / continuation | 0.165% | True breakout |
| 2026-05-13 07:00 | Valid swing, away from level | n/a | -319.0% | 2.63x | Flat / fading | 0.044% | Weak move without breakout |
| 2025-12-15 10:00 | Valid swing, away from level | n/a | -385.7% | 2.63x | Flat / fading | 0.031% | Position building in range |
| 2025-06-16 22:00 | Valid swing, away from level | n/a | 109.5% | 2.63x | Flat / fading | 0.064% | Position building in range |
| 2025-06-24 08:00 | Valid swing, away from level | 38.2% | 3.1% | 2.63x | Reversal | -0.533% | Liquidity sweep / reversal |
| 2025-09-19 11:00 | Golden zone 50-61.8% | 50.0% | 52.0% | 2.63x | Flat / fading | -0.070% | Weak move without breakout |
| 2025-11-19 14:15 | Valid swing, away from level | 38.2% | 11.0% | 2.63x | Impulse / continuation | 1.423% | True breakout |
| 2026-04-10 14:30 | Valid swing, away from level | n/a | -14.7% | 2.63x | Reversal | -0.119% | Liquidity sweep / reversal |
| 2026-07-07 12:15 | Valid swing, away from level | n/a | -166.1% | 2.63x | Impulse / continuation | 0.404% | True breakout |
| 2025-08-26 09:00 | Valid swing, away from level | n/a | -4.2% | 2.62x | Impulse / continuation | 0.452% | True breakout |
| 2026-09-16 10:15 | Valid swing, away from level | 78.6% | 83.8% | 2.62x | Impulse / continuation | -0.091% | True breakout |
| 2025-07-01 16:45 | Valid swing, away from level | n/a | -39.1% | 2.62x | Flat / fading | -0.024% | Weak move without breakout |
| 2025-06-30 11:00 | Valid swing, away from level | n/a | 142.6% | 2.62x | Impulse / continuation | -0.214% | True breakout |
| 2025-12-30 12:30 | Valid swing, away from level | 78.6% | 95.2% | 2.62x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2024-11-21 12:00 | Valid swing, away from level | n/a | 114.1% | 2.62x | Impulse / continuation | 0.191% | True breakout |
| 2025-07-04 11:15 | Valid swing, away from level | 78.6% | 90.7% | 2.62x | Reversal | -0.291% | Liquidity sweep / reversal |
| 2025-07-02 19:00 | Golden zone 50-61.8% | 50.0% | 53.2% | 2.62x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-09-24 10:15 | Near Fib level | 50.0% | 46.4% | 2.62x | Reversal | 0.852% | Liquidity sweep / reversal |
| 2026-09-01 07:30 | Near Fib level | 38.2% | 36.4% | 2.62x | Flat / fading | 0.165% | Weak move without breakout |
| 2025-07-02 10:15 | Valid swing, away from level | n/a | 113.6% | 2.62x | Flat / fading | -0.073% | Weak move without breakout |
| 2024-10-09 10:45 | Near Fib level | 61.8% | 64.9% | 2.62x | Impulse / continuation | 0.355% | True breakout |
| 2025-09-03 09:45 | Valid swing, away from level | n/a | -15.8% | 2.62x | Impulse -> reversal | -0.368% | False breakout |
| 2026-07-15 11:15 | Valid swing, away from level | n/a | 374.0% | 2.62x | Impulse / continuation | -0.732% | True breakout |
| 2026-04-22 10:15 | Valid swing, away from level | 38.2% | 22.3% | 2.62x | Flat / fading | 0.080% | Position building in range |
| 2025-09-03 16:30 | Valid swing, away from level | n/a | -16.7% | 2.62x | Impulse / continuation | -0.145% | True breakout |
| 2025-07-02 12:00 | Valid swing, away from level | n/a | 186.4% | 2.62x | Reversal | -0.043% | Liquidity sweep / reversal |
| 2026-03-24 12:45 | Valid swing, away from level | n/a | -327.0% | 2.62x | Flat / fading | -0.138% | Weak move without breakout |
| 2025-02-13 10:30 | Near Fib level | 38.2% | 41.6% | 2.62x | Reversal | 0.983% | Liquidity sweep / reversal |
| 2026-07-13 18:00 | Valid swing, away from level | 61.8% | 69.7% | 2.62x | Flat / fading | 0.048% | Weak move without breakout |
| 2025-05-27 07:15 | Valid swing, away from level | n/a | 104.4% | 2.62x | Impulse / continuation | 0.213% | True breakout |
| 2025-07-18 11:45 | Valid swing, away from level | n/a | -81.0% | 2.62x | Reversal | -0.066% | Liquidity sweep / reversal |
| 2026-05-24 18:45 | Valid swing, away from level | n/a | -2.8% | 2.62x | Impulse / continuation | 0.091% | True breakout |
| 2026-06-25 07:00 | Golden zone 50-61.8% | 61.8% | 60.2% | 2.62x | Impulse / continuation | -0.082% | True breakout |
| 2026-05-06 09:30 | Valid swing, away from level | n/a | 123.6% | 2.62x | Reversal | -0.337% | Liquidity sweep / reversal |
| 2026-07-13 10:45 | Valid swing, away from level | n/a | -394.3% | 2.62x | Flat / fading | -0.299% | Weak move without breakout |
| 2025-09-19 13:30 | Valid swing, away from level | n/a | 127.5% | 2.62x | Flat / fading | 0.006% | Weak move without breakout |
| 2026-07-21 16:00 | Valid swing, away from level | 38.2% | 2.4% | 2.62x | Impulse / continuation | 1.611% | True breakout |
| 2025-09-10 09:15 | Golden zone 50-61.8% | 61.8% | 60.9% | 2.61x | Reversal | 0.024% | Liquidity sweep / reversal |
| 2025-10-19 17:15 | Valid swing, away from level | 78.6% | 92.3% | 2.61x | Flat / fading | 0.064% | Position building in range |
| 2025-06-03 10:30 | Valid swing, away from level | n/a | -22.7% | 2.61x | Flat / fading | 0.087% | Weak move without breakout |
| 2026-01-17 18:30 | Near Fib level | 78.6% | 74.4% | 2.61x | Reversal | -0.043% | Liquidity sweep / reversal |
| 2025-05-11 10:30 | Valid swing, away from level | n/a | -579.6% | 2.61x | Reversal | 0.147% | Liquidity sweep / reversal |
| 2025-05-21 11:00 | Golden zone 50-61.8% | 61.8% | 61.1% | 2.61x | Impulse / continuation | -0.556% | True breakout |
| 2026-01-13 09:30 | Valid swing, away from level | 78.6% | 97.1% | 2.61x | Impulse / continuation | -0.050% | True breakout |
| 2025-07-22 12:15 | Valid swing, away from level | n/a | 195.2% | 2.61x | Impulse / continuation | 0.407% | True breakout |
| 2025-01-22 10:30 | Valid swing, away from level | 78.6% | 73.4% | 2.61x | Flat / fading | 0.053% | Weak move without breakout |
| 2025-11-26 11:30 | Near Fib level | 38.2% | 42.4% | 2.61x | Flat / fading | 0.064% | Weak move without breakout |
| 2025-05-05 09:00 | Valid swing, away from level | n/a | 104.9% | 2.61x | Reversal | 0.358% | Liquidity sweep / reversal |
| 2026-05-25 10:00 | Near Fib level | 38.2% | 37.1% | 2.61x | Reversal | 0.072% | Liquidity sweep / reversal |
| 2025-09-05 10:15 | Near Fib level | 38.2% | 36.7% | 2.61x | Impulse / continuation | 0.024% | True breakout |
| 2025-08-01 14:45 | Valid swing, away from level | 78.6% | 86.4% | 2.61x | Impulse / continuation | -0.209% | True breakout |
| 2026-06-09 08:00 | Golden zone 50-61.8% | 61.8% | 60.7% | 2.61x | Impulse -> reversal | 0.296% | False breakout |
| 2026-03-19 11:00 | Valid swing, away from level | 38.2% | 8.8% | 2.61x | Flat / fading | -0.173% | Weak move without breakout |
| 2025-06-20 10:00 | Near Fib level | 78.6% | 82.7% | 2.61x | Reversal | 0.163% | Liquidity sweep / reversal |
| 2025-04-14 20:00 | Valid swing, away from level | n/a | 144.4% | 2.61x | Flat / fading | 0.110% | Weak move without breakout |
| 2026-07-02 15:30 | Valid swing, away from level | n/a | 624.7% | 2.61x | Flat / fading | -0.245% | Weak move without breakout |
| 2026-08-25 12:30 | Near Fib level | 50.0% | 49.7% | 2.61x | Flat / fading | 0.257% | Position building in range |
| 2025-06-10 10:30 | Golden zone 50-61.8% | 50.0% | 51.0% | 2.61x | Flat / fading | -0.025% | Weak move without breakout |
| 2025-02-21 11:00 | Valid swing, away from level | n/a | -69.3% | 2.61x | Flat / fading | 0.052% | Weak move without breakout |
| 2025-11-06 10:45 | Valid swing, away from level | 78.6% | 98.9% | 2.61x | Impulse / continuation | -0.519% | True breakout |
| 2025-09-02 10:15 | Valid swing, away from level | n/a | 137.5% | 2.60x | Reversal | -0.223% | Liquidity sweep / reversal |
| 2026-09-16 08:15 | Near Fib level | 50.0% | 45.5% | 2.60x | Reversal | -0.182% | Liquidity sweep / reversal |
| 2026-04-19 18:45 | Valid swing, away from level | n/a | -20.7% | 2.60x | Impulse / continuation | 0.184% | True breakout |
| 2025-10-30 09:00 | Near Fib level | 38.2% | 34.1% | 2.60x | Impulse / continuation | 0.841% | True breakout |
| 2025-07-15 10:45 | Valid swing, away from level | 38.2% | 9.7% | 2.60x | Reversal | 0.656% | Liquidity sweep / reversal |
| 2026-01-06 17:45 | Golden zone 50-61.8% | 61.8% | 60.7% | 2.60x | Reversal | 0.207% | Liquidity sweep / reversal |
| 2025-06-20 16:30 | Valid swing, away from level | n/a | 106.7% | 2.60x | Flat / fading | -0.019% | Weak move without breakout |
| 2025-04-29 19:45 | Valid swing, away from level | n/a | 238.5% | 2.60x | Reversal | 0.193% | Liquidity sweep / reversal |
| 2025-11-30 17:30 | Valid swing, away from level | 38.2% | 7.8% | 2.60x | Flat / fading | 0.038% | Weak move without breakout |
| 2025-10-22 09:30 | Valid swing, away from level | 38.2% | 14.1% | 2.60x | Reversal | -0.265% | Liquidity sweep / reversal |
| 2026-03-18 16:00 | Near Fib level | 78.6% | 82.7% | 2.60x | Impulse / continuation | -0.334% | True breakout |
| 2024-12-26 11:30 | Valid swing, away from level | 38.2% | 16.1% | 2.60x | Impulse / continuation | 0.213% | True breakout |
| 2025-08-28 17:30 | Near Fib level | 38.2% | 40.0% | 2.60x | Impulse / continuation | 0.094% | True breakout |
| 2026-05-19 07:00 | Valid swing, away from level | 38.2% | 7.4% | 2.60x | Flat / fading | 0.148% | Position building in range |
| 2026-03-11 23:15 | Valid swing, away from level | 78.6% | 87.5% | 2.60x | Impulse / continuation | 0.024% | True breakout |
| 2026-08-24 16:45 | Valid swing, away from level | n/a | 104.8% | 2.60x | Reversal | 0.899% | Liquidity sweep / reversal |
| 2025-09-30 12:30 | Valid swing, away from level | n/a | 396.1% | 2.60x | Reversal | 0.251% | Liquidity sweep / reversal |
| 2026-05-04 11:30 | Valid swing, away from level | n/a | -72.3% | 2.60x | Flat / fading | -0.189% | Weak move without breakout |
| 2026-03-26 11:45 | Valid swing, away from level | n/a | 291.9% | 2.60x | Reversal | 0.109% | Liquidity sweep / reversal |
| 2026-03-03 09:15 | Near Fib level | 78.6% | 82.8% | 2.60x | Impulse / continuation | -0.422% | True breakout |
| 2026-08-20 17:30 | Valid swing, away from level | n/a | 116.2% | 2.60x | Flat / fading | 0.095% | Weak move without breakout |
| 2025-01-14 11:45 | Near Fib level | 50.0% | 45.6% | 2.60x | Impulse / continuation | 0.616% | True breakout |
| 2025-07-19 10:45 | Valid swing, away from level | n/a | -27.1% | 2.60x | Impulse / continuation | -0.054% | True breakout |
| 2025-05-02 10:30 | Valid swing, away from level | n/a | 258.1% | 2.60x | Flat / fading | -0.322% | Weak move without breakout |
| 2026-02-06 23:00 | Valid swing, away from level | 78.6% | 89.7% | 2.60x | Impulse / continuation | -0.055% | True breakout |
| 2025-10-11 18:45 | Valid swing, away from level | n/a | -22.5% | 2.60x | Impulse / continuation | 0.463% | True breakout |
| 2025-05-14 23:30 | Valid swing, away from level | n/a | 215.0% | 2.60x | Impulse -> reversal | 0.386% | False breakout |
| 2025-02-24 10:15 | Valid swing, away from level | 38.2% | 13.6% | 2.60x | Flat / fading | -0.012% | Weak move without breakout |
| 2024-10-11 13:15 | Valid swing, away from level | n/a | 119.0% | 2.60x | Impulse / continuation | -0.313% | True breakout |
| 2024-11-20 19:00 | Valid swing, away from level | n/a | 224.9% | 2.60x | Reversal | 0.016% | Liquidity sweep / reversal |
| 2026-02-23 12:00 | Near Fib level | 38.2% | 41.9% | 2.60x | Flat / fading | 0.006% | Weak move without breakout |
| 2025-05-08 16:00 | Golden zone 50-61.8% | 50.0% | 55.5% | 2.59x | Flat / fading | 0.026% | Position building in range |
| 2026-02-11 07:00 | Golden zone 50-61.8% | 50.0% | 50.6% | 2.59x | Flat / fading | 0.055% | Weak move without breakout |
| 2025-11-13 11:15 | Near Fib level | 38.2% | 37.5% | 2.59x | Flat / fading | -0.088% | Weak move without breakout |
| 2026-07-09 09:00 | Near Fib level | 78.6% | 77.5% | 2.59x | Reversal | 0.314% | Liquidity sweep / reversal |
| 2026-04-06 07:30 | Valid swing, away from level | n/a | -96.8% | 2.59x | Impulse / continuation | -0.217% | True breakout |
| 2025-01-13 10:45 | Valid swing, away from level | n/a | -38.6% | 2.59x | Flat / fading | 0.034% | Weak move without breakout |
| 2026-07-28 07:30 | Valid swing, away from level | n/a | -18.2% | 2.59x | Reversal | -0.346% | Liquidity sweep / reversal |
| 2026-07-17 17:45 | Valid swing, away from level | n/a | 127.3% | 2.59x | Impulse / continuation | 0.228% | True breakout |
| 2025-07-23 12:30 | Valid swing, away from level | n/a | -15.8% | 2.59x | Impulse / continuation | -0.292% | True breakout |
| 2025-12-24 10:15 | Valid swing, away from level | n/a | 111.3% | 2.59x | Reversal | -0.480% | Liquidity sweep / reversal |
| 2026-02-13 23:45 | Valid swing, away from level | 38.2% | 3.7% | 2.59x | Impulse / continuation | 0.438% | True breakout |
| 2025-10-08 13:45 | Valid swing, away from level | n/a | 379.5% | 2.59x | Impulse / continuation | -0.816% | True breakout |
| 2025-02-03 12:00 | Valid swing, away from level | n/a | 114.2% | 2.59x | Flat / fading | 0.354% | Weak move without breakout |
| 2025-03-07 09:15 | Valid swing, away from level | n/a | -54.0% | 2.59x | Impulse / continuation | 0.857% | True breakout |
| 2026-01-12 07:15 | Valid swing, away from level | n/a | -22.9% | 2.59x | Impulse / continuation | -0.166% | True breakout |
| 2025-10-08 10:45 | Near Fib level | 78.6% | 79.5% | 2.59x | Impulse / continuation | -0.165% | True breakout |
| 2025-10-27 10:15 | Valid swing, away from level | n/a | 138.0% | 2.59x | Flat / fading | 0.014% | Weak move without breakout |
| 2025-12-01 07:15 | Valid swing, away from level | n/a | -23.4% | 2.59x | Reversal | -0.140% | Liquidity sweep / reversal |
| 2026-07-29 11:15 | Valid swing, away from level | n/a | -57.6% | 2.59x | Flat / fading | -0.150% | Weak move without breakout |
| 2024-12-19 10:00 | Valid swing, away from level | n/a | -219.2% | 2.59x | Impulse / continuation | -0.071% | True breakout |
| 2025-09-02 15:45 | Valid swing, away from level | n/a | 237.5% | 2.59x | Flat / fading | -0.060% | Weak move without breakout |
| 2025-11-10 11:30 | Valid swing, away from level | n/a | -0.9% | 2.58x | Flat / fading | -0.154% | Weak move without breakout |
| 2025-11-28 11:00 | Near Fib level | 78.6% | 80.1% | 2.58x | Flat / fading | -0.052% | Weak move without breakout |
| 2025-03-26 16:30 | Valid swing, away from level | n/a | 166.9% | 2.58x | Flat / fading | -0.167% | Weak move without breakout |
| 2025-01-22 14:15 | Valid swing, away from level | n/a | -6.8% | 2.58x | Reversal | -0.439% | Liquidity sweep / reversal |
| 2026-06-09 16:30 | Valid swing, away from level | n/a | -60.1% | 2.58x | Impulse / continuation | 0.202% | True breakout |
| 2026-08-07 23:45 | Valid swing, away from level | n/a | -22.8% | 2.58x | Reversal | -1.366% | Liquidity sweep / reversal |
| 2026-05-12 10:00 | Valid swing, away from level | 38.2% | 2.9% | 2.58x | Impulse / continuation | 0.423% | True breakout |
| 2025-03-31 08:00 | No confirmed swing | n/a | n/a | 2.58x | Reversal | 1.920% | Liquidity sweep / reversal |
| 2024-12-11 11:15 | Valid swing, away from level | n/a | 141.7% | 2.58x | Reversal | 0.411% | Liquidity sweep / reversal |
| 2025-05-23 23:30 | Near Fib level | 78.6% | 81.7% | 2.58x | Reversal | -0.864% | Liquidity sweep / reversal |
| 2025-08-25 11:45 | Valid swing, away from level | n/a | 219.6% | 2.58x | Flat / fading | -0.113% | Weak move without breakout |
| 2025-01-14 10:30 | Valid swing, away from level | 78.6% | 73.2% | 2.58x | Impulse -> reversal | 0.248% | False breakout |
| 2024-12-28 10:15 | Valid swing, away from level | n/a | -46.8% | 2.58x | Impulse / continuation | 0.325% | True breakout |
| 2026-05-15 11:30 | Valid swing, away from level | 78.6% | 73.3% | 2.58x | Reversal | 0.134% | Liquidity sweep / reversal |
| 2025-01-27 16:45 | Valid swing, away from level | n/a | 104.8% | 2.58x | Impulse / continuation | -0.188% | True breakout |
| 2025-10-02 08:00 | Valid swing, away from level | n/a | 102.5% | 2.58x | Flat / fading | -0.138% | Weak move without breakout |
| 2026-05-26 21:00 | Golden zone 50-61.8% | 61.8% | 60.3% | 2.58x | Flat / fading | -0.099% | Weak move without breakout |
| 2024-10-25 10:30 | Near Fib level | 78.6% | 75.9% | 2.58x | Reversal | 0.040% | Liquidity sweep / reversal |
| 2026-08-17 17:00 | Valid swing, away from level | 38.2% | 4.0% | 2.58x | Reversal | -1.112% | Liquidity sweep / reversal |
| 2025-11-03 07:45 | Valid swing, away from level | n/a | -107.0% | 2.58x | Flat / fading | 0.034% | Position building in range |
| 2025-12-17 08:00 | Valid swing, away from level | 38.2% | 4.5% | 2.58x | Impulse / continuation | -0.128% | True breakout |
| 2025-10-10 11:15 | Near Fib level | 38.2% | 40.0% | 2.57x | Flat / fading | -0.068% | Weak move without breakout |
| 2025-11-05 07:15 | Valid swing, away from level | n/a | 216.1% | 2.57x | Reversal | 0.114% | Liquidity sweep / reversal |
| 2025-06-13 10:00 | Valid swing, away from level | n/a | 117.0% | 2.57x | Reversal | -0.025% | Liquidity sweep / reversal |
| 2025-01-20 11:00 | Valid swing, away from level | n/a | -19.6% | 2.57x | Flat / fading | -0.267% | Weak move without breakout |
| 2026-03-27 09:45 | Valid swing, away from level | 38.2% | 28.6% | 2.57x | Reversal | 0.024% | Liquidity sweep / reversal |
| 2025-06-29 13:15 | Valid swing, away from level | 78.6% | 70.8% | 2.57x | Flat / fading | 0.006% | Weak move without breakout |
| 2025-10-19 18:30 | Golden zone 50-61.8% | 50.0% | 52.3% | 2.57x | Impulse -> reversal | -0.325% | False breakout |
| 2025-03-03 09:15 | Valid swing, away from level | n/a | 237.8% | 2.57x | Reversal | -0.574% | Liquidity sweep / reversal |
| 2025-05-06 16:00 | Valid swing, away from level | n/a | -7.2% | 2.57x | Flat / fading | 0.080% | Weak move without breakout |
| 2025-11-24 17:15 | Valid swing, away from level | 78.6% | 86.0% | 2.57x | Flat / fading | -0.039% | Weak move without breakout |
| 2024-12-13 13:30 | Valid swing, away from level | n/a | 131.2% | 2.57x | Reversal | -0.104% | Liquidity sweep / reversal |
| 2025-10-20 10:45 | Valid swing, away from level | n/a | -52.3% | 2.57x | Flat / fading | 0.032% | Weak move without breakout |
| 2026-07-28 16:45 | Near Fib level | 61.8% | 65.4% | 2.57x | Impulse -> reversal | 0.382% | False breakout |
| 2024-10-03 15:15 | Near Fib level | 50.0% | 48.8% | 2.57x | Impulse / continuation | 1.220% | True breakout |
| 2024-11-02 18:15 | Valid swing, away from level | n/a | 329.2% | 2.57x | Impulse / continuation | -0.043% | True breakout |
| 2025-06-05 23:15 | Valid swing, away from level | 78.6% | 98.2% | 2.57x | Reversal | 0.601% | Liquidity sweep / reversal |
| 2024-11-26 11:15 | Valid swing, away from level | 38.2% | 27.0% | 2.57x | Reversal | -0.380% | Liquidity sweep / reversal |
| 2026-02-09 18:00 | Valid swing, away from level | n/a | -14.2% | 2.57x | Impulse / continuation | -0.091% | True breakout |
| 2025-11-05 09:30 | Valid swing, away from level | 38.2% | 30.0% | 2.57x | Flat / fading | 0.007% | Weak move without breakout |
| 2026-09-11 13:45 | Valid swing, away from level | n/a | 117.9% | 2.57x | Reversal | 0.523% | Liquidity sweep / reversal |
| 2025-09-28 12:00 | Golden zone 50-61.8% | 50.0% | 54.5% | 2.57x | Reversal | 0.026% | Liquidity sweep / reversal |
| 2025-05-02 19:00 | Valid swing, away from level | n/a | 257.9% | 2.57x | Reversal | -0.517% | Liquidity sweep / reversal |
| 2026-06-24 10:30 | Valid swing, away from level | n/a | 106.7% | 2.57x | Impulse / continuation | -0.167% | True breakout |
| 2025-01-10 14:00 | Valid swing, away from level | n/a | -50.9% | 2.56x | Impulse / continuation | 0.687% | True breakout |
| 2025-09-08 15:45 | Valid swing, away from level | n/a | -27.1% | 2.56x | Reversal | -0.184% | Liquidity sweep / reversal |
| 2024-11-18 16:45 | Valid swing, away from level | 38.2% | 8.4% | 2.56x | Impulse / continuation | 1.315% | True breakout |
| 2024-12-10 12:15 | Valid swing, away from level | n/a | 627.8% | 2.56x | Flat / fading | 0.204% | Weak move without breakout |
| 2025-03-17 07:45 | Valid swing, away from level | n/a | -3854.5% | 2.56x | Flat / fading | -0.164% | Position building in range |
| 2025-04-23 12:30 | Valid swing, away from level | n/a | 170.1% | 2.56x | Reversal | 0.808% | Liquidity sweep / reversal |
| 2025-10-10 10:30 | Valid swing, away from level | 78.6% | 97.5% | 2.56x | Reversal | 0.448% | Liquidity sweep / reversal |
| 2025-02-05 12:00 | Near Fib level | 78.6% | 77.2% | 2.56x | Reversal | 0.980% | Liquidity sweep / reversal |
| 2026-08-24 10:30 | Valid swing, away from level | n/a | 657.1% | 2.56x | Flat / fading | 0.032% | Weak move without breakout |
| 2026-09-16 12:30 | Valid swing, away from level | n/a | 146.5% | 2.56x | Impulse / continuation | -0.199% | True breakout |
| 2025-12-29 18:00 | Near Fib level | 50.0% | 49.4% | 2.56x | Flat / fading | -0.329% | Weak move without breakout |
| 2026-07-16 08:15 | Valid swing, away from level | n/a | 148.8% | 2.56x | Reversal | -0.108% | Liquidity sweep / reversal |
| 2025-03-07 20:15 | Near Fib level | 38.2% | 40.7% | 2.56x | Flat / fading | -0.176% | Weak move without breakout |
| 2026-05-05 12:00 | Valid swing, away from level | 38.2% | 24.2% | 2.55x | Impulse / continuation | 0.467% | True breakout |
| 2025-02-19 07:00 | Golden zone 50-61.8% | 61.8% | 61.5% | 2.55x | Flat / fading | 0.123% | Weak move without breakout |
| 2025-06-17 07:45 | Golden zone 50-61.8% | 61.8% | 58.3% | 2.55x | Flat / fading | 0.114% | Weak move without breakout |
| 2025-09-26 07:45 | Near Fib level | 78.6% | 83.2% | 2.55x | Reversal | 0.148% | Liquidity sweep / reversal |
| 2026-06-26 10:15 | Valid swing, away from level | 78.6% | 84.6% | 2.55x | Impulse / continuation | -0.664% | True breakout |
| 2025-10-16 15:15 | Valid swing, away from level | n/a | -37.7% | 2.55x | Impulse / continuation | 0.254% | True breakout |
| 2025-11-19 16:00 | Valid swing, away from level | n/a | -123.7% | 2.55x | Flat / fading | -0.272% | Weak move without breakout |
| 2025-09-18 13:00 | Valid swing, away from level | n/a | 206.6% | 2.55x | Reversal | -0.121% | Liquidity sweep / reversal |
| 2024-10-28 11:15 | Valid swing, away from level | n/a | 109.2% | 2.55x | Impulse / continuation | -0.063% | True breakout |
| 2025-04-30 12:15 | Valid swing, away from level | 78.6% | 92.8% | 2.55x | Reversal | 0.385% | Liquidity sweep / reversal |
| 2024-12-25 12:15 | Near Fib level | 50.0% | 48.3% | 2.55x | Flat / fading | -0.162% | Position building in range |
| 2025-02-19 10:45 | Valid swing, away from level | 61.8% | 69.6% | 2.55x | Impulse / continuation | -0.370% | True breakout |
| 2025-07-13 11:00 | Valid swing, away from level | 78.6% | 97.4% | 2.55x | Impulse / continuation | -0.443% | True breakout |
| 2025-09-16 17:00 | Valid swing, away from level | 38.2% | 25.6% | 2.55x | Flat / fading | -0.391% | Position building in range |
| 2026-04-21 15:45 | Valid swing, away from level | n/a | 184.2% | 2.55x | Impulse / continuation | -0.191% | True breakout |
| 2024-11-19 17:15 | Valid swing, away from level | n/a | 189.2% | 2.55x | Reversal | 1.062% | Liquidity sweep / reversal |
| 2026-09-15 10:30 | Golden zone 50-61.8% | 61.8% | 56.7% | 2.55x | Impulse / continuation | -0.384% | True breakout |
| 2025-05-29 09:00 | Golden zone 50-61.8% | 61.8% | 55.9% | 2.55x | Reversal | -0.188% | Liquidity sweep / reversal |
| 2025-08-18 07:30 | Valid swing, away from level | n/a | -122.7% | 2.55x | Impulse / continuation | 0.288% | True breakout |
| 2025-09-11 10:00 | Near Fib level | 78.6% | 77.0% | 2.54x | Impulse / continuation | -0.468% | True breakout |
| 2025-04-07 16:45 | Valid swing, away from level | n/a | -21.2% | 2.54x | Impulse / continuation | 1.183% | True breakout |
| 2026-08-21 07:15 | Golden zone 50-61.8% | 61.8% | 57.1% | 2.54x | Reversal | -0.157% | Liquidity sweep / reversal |
| 2024-11-07 17:30 | Valid swing, away from level | n/a | -125.0% | 2.54x | Impulse / continuation | 0.589% | True breakout |
| 2025-12-17 07:45 | Valid swing, away from level | n/a | -11.4% | 2.54x | Reversal | -0.110% | Liquidity sweep / reversal |
| 2025-07-24 10:15 | Near Fib level | 38.2% | 34.3% | 2.54x | Impulse / continuation | -0.587% | True breakout |
| 2024-10-29 12:15 | Valid swing, away from level | 78.6% | 89.9% | 2.54x | Flat / fading | -0.215% | Position building in range |
| 2026-04-07 10:00 | Valid swing, away from level | n/a | 113.6% | 2.54x | Impulse / continuation | 0.630% | True breakout |
| 2025-05-19 19:30 | Golden zone 50-61.8% | 61.8% | 56.2% | 2.54x | Impulse / continuation | 0.103% | True breakout |
| 2026-06-13 10:00 | Near Fib level | 50.0% | 45.0% | 2.54x | Reversal | -0.047% | Liquidity sweep / reversal |
| 2026-01-13 10:15 | Valid swing, away from level | 78.6% | 97.1% | 2.54x | Reversal | -0.309% | Liquidity sweep / reversal |
| 2025-12-24 14:15 | Near Fib level | 38.2% | 42.6% | 2.54x | Flat / fading | 0.013% | Position building in range |
| 2026-07-28 09:45 | Valid swing, away from level | 38.2% | 8.0% | 2.54x | Impulse / continuation | -1.546% | True breakout |
| 2025-10-21 17:45 | Valid swing, away from level | n/a | 201.2% | 2.54x | Impulse / continuation | -1.017% | True breakout |
| 2026-09-21 08:45 | Valid swing, away from level | n/a | -800.0% | 2.54x | Impulse / continuation | -0.157% | True breakout |
| 2026-04-24 10:15 | Golden zone 50-61.8% | 50.0% | 54.7% | 2.54x | Impulse / continuation | -0.135% | True breakout |
| 2025-05-21 07:30 | Valid swing, away from level | 38.2% | 5.1% | 2.54x | Reversal | -0.305% | Liquidity sweep / reversal |
| 2026-06-11 10:00 | Golden zone 50-61.8% | 50.0% | 53.5% | 2.54x | Reversal | 0.275% | Liquidity sweep / reversal |
| 2026-04-10 11:00 | Valid swing, away from level | n/a | 121.6% | 2.54x | Reversal | 0.348% | Liquidity sweep / reversal |
| 2025-11-01 10:00 | Valid swing, away from level | 78.6% | 70.5% | 2.54x | Impulse / continuation | 0.231% | True breakout |
| 2026-03-19 10:30 | Near Fib level | 50.0% | 48.7% | 2.54x | Reversal | 0.036% | Liquidity sweep / reversal |
| 2026-09-22 09:00 | Valid swing, away from level | 38.2% | 6.5% | 2.54x | Flat / fading | -0.125% | Weak move without breakout |
| 2025-02-03 21:00 | Valid swing, away from level | n/a | -72.3% | 2.54x | Flat / fading | -0.026% | Position building in range |
| 2025-04-26 10:30 | Valid swing, away from level | n/a | -41.5% | 2.54x | Impulse / continuation | 0.638% | True breakout |
| 2025-04-03 17:00 | Valid swing, away from level | n/a | 213.2% | 2.54x | Flat / fading | -0.285% | Weak move without breakout |
| 2025-06-13 12:45 | Near Fib level | 78.6% | 83.5% | 2.54x | Flat / fading | -0.189% | Weak move without breakout |
| 2024-11-29 12:00 | Valid swing, away from level | n/a | -13.8% | 2.54x | Reversal | -0.042% | Liquidity sweep / reversal |
| 2025-07-07 07:45 | Valid swing, away from level | n/a | 111.1% | 2.54x | Flat / fading | -0.050% | Weak move without breakout |
| 2026-03-04 07:00 | Valid swing, away from level | n/a | -13.3% | 2.54x | Impulse / continuation | 0.277% | True breakout |
| 2026-05-07 09:30 | Golden zone 50-61.8% | 61.8% | 57.9% | 2.54x | Reversal | -0.013% | Liquidity sweep / reversal |
| 2026-05-14 09:45 | Valid swing, away from level | 38.2% | 20.6% | 2.53x | Reversal | -0.315% | Liquidity sweep / reversal |
| 2025-06-16 14:15 | Valid swing, away from level | n/a | -10.2% | 2.53x | Flat / fading | 0.171% | Weak move without breakout |
| 2025-06-03 11:00 | Valid swing, away from level | n/a | -37.7% | 2.53x | Flat / fading | 0.292% | Weak move without breakout |
| 2026-09-01 11:15 | Valid swing, away from level | n/a | -86.3% | 2.53x | Flat / fading | -0.241% | Weak move without breakout |
| 2025-09-26 17:45 | Valid swing, away from level | 38.2% | 15.8% | 2.53x | Flat / fading | 0.064% | Weak move without breakout |
| 2026-04-23 13:00 | Valid swing, away from level | 38.2% | 21.3% | 2.53x | Flat / fading | 0.074% | Position building in range |
| 2026-08-28 16:45 | Golden zone 50-61.8% | 61.8% | 58.2% | 2.53x | Reversal | -1.104% | Liquidity sweep / reversal |
| 2026-04-10 10:30 | Near Fib level | 78.6% | 78.4% | 2.53x | Impulse / continuation | -0.195% | True breakout |
| 2024-12-06 11:00 | Valid swing, away from level | 38.2% | 5.7% | 2.53x | Impulse / continuation | -0.430% | True breakout |
| 2026-03-16 19:00 | Valid swing, away from level | n/a | 118.6% | 2.53x | Flat / fading | -0.041% | Position building in range |
| 2026-09-09 08:45 | Valid swing, away from level | n/a | 106.6% | 2.53x | Flat / fading | -0.076% | Weak move without breakout |
| 2026-08-05 09:00 | Valid swing, away from level | n/a | -11.4% | 2.53x | Impulse / continuation | 0.233% | True breakout |
| 2024-12-02 11:15 | Valid swing, away from level | n/a | -7.2% | 2.53x | Impulse / continuation | -0.449% | True breakout |
| 2025-09-02 16:00 | Valid swing, away from level | n/a | 284.1% | 2.53x | Flat / fading | 0.212% | Weak move without breakout |
| 2026-05-08 21:45 | Valid swing, away from level | 38.2% | 0.4% | 2.53x | Flat / fading | -0.006% | Weak move without breakout |
| 2024-12-28 11:15 | Valid swing, away from level | n/a | -86.2% | 2.53x | Reversal | 0.181% | Liquidity sweep / reversal |
| 2025-07-08 19:45 | Valid swing, away from level | n/a | 164.8% | 2.53x | Impulse / continuation | -0.379% | True breakout |
| 2025-08-27 14:45 | Valid swing, away from level | 38.2% | 19.3% | 2.53x | Flat / fading | 0.094% | Weak move without breakout |
| 2025-04-26 11:45 | Valid swing, away from level | n/a | -64.0% | 2.53x | Flat / fading | -0.060% | Weak move without breakout |
| 2025-11-27 11:00 | Near Fib level | 61.8% | 66.0% | 2.53x | Reversal | -0.291% | Liquidity sweep / reversal |
| 2024-11-14 12:00 | Valid swing, away from level | 38.2% | 24.1% | 2.53x | Flat / fading | 0.210% | Weak move without breakout |
| 2026-01-05 10:00 | Valid swing, away from level | n/a | 336.6% | 2.53x | Flat / fading | -0.018% | Weak move without breakout |
| 2026-03-09 08:45 | Near Fib level | 78.6% | 81.9% | 2.53x | Flat / fading | -0.307% | Weak move without breakout |
| 2026-05-08 11:00 | Valid swing, away from level | 38.2% | 12.5% | 2.53x | Reversal | -0.194% | Liquidity sweep / reversal |
| 2026-06-24 08:30 | Valid swing, away from level | 38.2% | 4.4% | 2.53x | Impulse / continuation | -0.725% | True breakout |
| 2025-06-02 09:00 | Near Fib level | 50.0% | 46.4% | 2.53x | Flat / fading | 0.374% | Weak move without breakout |
| 2026-01-29 17:00 | Valid swing, away from level | n/a | -414.5% | 2.52x | Reversal | -0.660% | Liquidity sweep / reversal |
| 2026-03-03 18:15 | Valid swing, away from level | 78.6% | 99.2% | 2.52x | Reversal | 0.006% | Liquidity sweep / reversal |
| 2026-03-27 09:00 | Valid swing, away from level | 78.6% | 92.8% | 2.52x | Reversal | 0.170% | Liquidity sweep / reversal |
| 2025-04-23 19:00 | Valid swing, away from level | 38.2% | 14.2% | 2.52x | Reversal | 0.708% | Liquidity sweep / reversal |
| 2026-05-06 07:00 | Near Fib level | 38.2% | 36.1% | 2.52x | Flat / fading | -0.006% | Weak move without breakout |
| 2026-02-02 12:45 | Valid swing, away from level | 78.6% | 93.2% | 2.52x | Reversal | -0.210% | Liquidity sweep / reversal |
| 2024-11-27 19:15 | Valid swing, away from level | n/a | -62.8% | 2.52x | Flat / fading | -0.076% | Weak move without breakout |
| 2025-01-30 09:15 | Near Fib level | 38.2% | 39.5% | 2.52x | Reversal | 0.092% | Liquidity sweep / reversal |
| 2026-05-16 10:45 | Near Fib level | 78.6% | 78.6% | 2.52x | Flat / fading | -0.039% | Position building in range |
| 2025-08-19 18:00 | Golden zone 50-61.8% | 50.0% | 53.8% | 2.52x | Impulse / continuation | -0.225% | True breakout |
| 2025-02-04 14:00 | Near Fib level | 38.2% | 41.9% | 2.52x | Flat / fading | 0.066% | Position building in range |
| 2025-07-28 10:15 | Valid swing, away from level | n/a | -283.3% | 2.52x | Reversal | -0.012% | Liquidity sweep / reversal |
| 2025-10-28 09:45 | Valid swing, away from level | n/a | -23.2% | 2.52x | Reversal | 0.063% | Liquidity sweep / reversal |
| 2026-02-02 08:45 | Valid swing, away from level | n/a | 155.8% | 2.52x | Impulse / continuation | -0.108% | True breakout |
| 2025-02-14 09:00 | Valid swing, away from level | n/a | -101.7% | 2.52x | Impulse / continuation | 0.418% | True breakout |
| 2026-01-26 14:30 | Valid swing, away from level | 78.6% | 97.5% | 2.52x | Flat / fading | -0.066% | Weak move without breakout |
| 2025-11-11 07:15 | Near Fib level | 50.0% | 48.0% | 2.51x | Flat / fading | 0.081% | Position building in range |
| 2025-01-09 11:00 | Valid swing, away from level | n/a | -17.1% | 2.51x | Reversal | -1.148% | Liquidity sweep / reversal |
| 2025-09-29 18:30 | Valid swing, away from level | n/a | 166.9% | 2.51x | Flat / fading | 0.045% | Position building in range |
| 2025-08-28 10:30 | Near Fib level | 78.6% | 80.4% | 2.51x | Impulse / continuation | 0.083% | True breakout |
| 2026-05-06 19:00 | Valid swing, away from level | n/a | -26.8% | 2.51x | Reversal | -0.400% | Liquidity sweep / reversal |
| 2026-03-25 23:30 | Valid swing, away from level | 78.6% | 97.1% | 2.51x | Reversal | 0.048% | Liquidity sweep / reversal |
| 2024-12-24 12:15 | Valid swing, away from level | 38.2% | 18.1% | 2.51x | Reversal | -0.579% | Liquidity sweep / reversal |
| 2025-08-13 10:45 | Valid swing, away from level | 61.8% | 68.0% | 2.51x | Reversal | 0.042% | Liquidity sweep / reversal |
| 2024-10-08 12:30 | Valid swing, away from level | n/a | -2.9% | 2.51x | Impulse / continuation | 0.394% | True breakout |
| 2026-01-16 23:15 | Valid swing, away from level | 38.2% | 3.6% | 2.51x | Reversal | 0.000% | Liquidity sweep / reversal |
| 2025-05-21 17:00 | Valid swing, away from level | n/a | 100.7% | 2.51x | Impulse / continuation | -0.496% | True breakout |
| 2025-02-26 12:30 | Valid swing, away from level | n/a | 159.1% | 2.51x | Impulse / continuation | -1.322% | True breakout |
| 2026-01-05 23:45 | Valid swing, away from level | 78.6% | 100.0% | 2.51x | Reversal | 0.386% | Liquidity sweep / reversal |
| 2026-01-30 09:15 | Golden zone 50-61.8% | 61.8% | 57.0% | 2.51x | Flat / fading | 0.160% | Weak move without breakout |
| 2026-03-30 10:00 | Valid swing, away from level | 61.8% | 69.0% | 2.51x | Impulse / continuation | -0.241% | True breakout |
| 2026-03-24 09:00 | Golden zone 50-61.8% | 61.8% | 56.0% | 2.51x | Flat / fading | 0.109% | Weak move without breakout |
| 2025-12-12 11:00 | Valid swing, away from level | 78.6% | 97.7% | 2.51x | Reversal | -0.251% | Liquidity sweep / reversal |
| 2025-07-29 09:00 | Near Fib level | 78.6% | 74.1% | 2.51x | Reversal | 0.320% | Liquidity sweep / reversal |
| 2025-11-25 10:00 | Near Fib level | 38.2% | 34.4% | 2.51x | Impulse / continuation | -0.143% | True breakout |
| 2025-08-27 09:15 | Valid swing, away from level | 38.2% | 17.3% | 2.50x | Reversal | 0.201% | Liquidity sweep / reversal |
| 2026-02-16 12:15 | Valid swing, away from level | n/a | -746.7% | 2.50x | Impulse / continuation | 0.730% | True breakout |
| 2025-03-20 07:30 | Valid swing, away from level | n/a | -60.5% | 2.50x | Reversal | -0.223% | Liquidity sweep / reversal |
| 2026-07-29 10:00 | Near Fib level | 50.0% | 45.8% | 2.50x | Reversal | 0.948% | Liquidity sweep / reversal |
| 2026-01-27 14:00 | Valid swing, away from level | n/a | -29.1% | 2.50x | Impulse / continuation | -0.084% | True breakout |
| 2026-07-15 14:15 | Valid swing, away from level | n/a | 346.0% | 2.50x | Flat / fading | -0.536% | Weak move without breakout |
| 2025-10-22 10:30 | Valid swing, away from level | 38.2% | 32.3% | 2.50x | Reversal | -0.040% | Liquidity sweep / reversal |
| 2024-11-22 10:15 | Valid swing, away from level | n/a | -27.7% | 2.50x | Reversal | -0.125% | Liquidity sweep / reversal |
| 2026-03-20 09:30 | Valid swing, away from level | 38.2% | 25.6% | 2.50x | Reversal | 0.532% | Liquidity sweep / reversal |
| 2025-08-06 22:30 | Valid swing, away from level | n/a | -318.9% | 2.50x | Reversal | -0.895% | Liquidity sweep / reversal |
| 2025-08-25 09:15 | Near Fib level | 78.6% | 77.2% | 2.50x | Reversal | -0.184% | Liquidity sweep / reversal |
| 2026-03-01 10:30 | Golden zone 50-61.8% | 50.0% | 55.6% | 2.50x | Impulse / continuation | -0.012% | True breakout |
| 2026-08-24 07:30 | Valid swing, away from level | n/a | 305.3% | 2.50x | Reversal | 0.008% | Liquidity sweep / reversal |
| 2025-02-24 17:00 | Near Fib level | 78.6% | 80.0% | 2.49x | Flat / fading | 0.064% | Weak move without breakout |
| 2026-04-02 16:00 | Valid swing, away from level | n/a | -24.7% | 2.49x | Impulse / continuation | 0.123% | True breakout |
| 2026-05-04 14:45 | Valid swing, away from level | n/a | 168.7% | 2.49x | Reversal | 0.615% | Liquidity sweep / reversal |
| 2026-09-21 10:45 | Valid swing, away from level | n/a | -62.5% | 2.49x | Reversal | 0.047% | Liquidity sweep / reversal |
| 2025-05-28 12:30 | Valid swing, away from level | n/a | -150.4% | 2.48x | Flat / fading | 0.063% | Weak move without breakout |
| 2025-06-02 18:15 | Valid swing, away from level | n/a | -25.1% | 2.48x | Flat / fading | 0.006% | Position building in range |
| 2026-06-18 14:45 | Valid swing, away from level | n/a | 471.9% | 2.48x | Flat / fading | 0.138% | Weak move without breakout |
| 2025-07-16 13:00 | Valid swing, away from level | n/a | -141.1% | 2.48x | Flat / fading | -0.149% | Weak move without breakout |
| 2025-09-11 16:00 | Valid swing, away from level | n/a | 206.8% | 2.48x | Reversal | 0.564% | Liquidity sweep / reversal |
| 2025-04-04 14:00 | Valid swing, away from level | n/a | 133.8% | 2.48x | Reversal | -1.153% | Liquidity sweep / reversal |
| 2025-03-03 10:30 | Valid swing, away from level | n/a | 358.2% | 2.47x | Reversal | -0.050% | Liquidity sweep / reversal |
| 2025-04-03 19:15 | Valid swing, away from level | n/a | 268.6% | 2.47x | Reversal | 0.274% | Liquidity sweep / reversal |
| 2026-08-31 10:00 | Valid swing, away from level | n/a | -156.4% | 2.47x | Flat / fading | 0.096% | Position building in range |
| 2024-12-09 17:00 | Valid swing, away from level | n/a | -33.9% | 2.47x | Flat / fading | 0.367% | Position building in range |
| 2026-07-15 10:30 | Valid swing, away from level | n/a | 242.0% | 2.47x | Reversal | -0.882% | Liquidity sweep / reversal |
| 2026-05-25 11:15 | Valid swing, away from level | 38.2% | 7.9% | 2.47x | Impulse / continuation | 0.332% | True breakout |
| 2025-02-26 16:15 | Valid swing, away from level | n/a | 510.0% | 2.47x | Reversal | 0.796% | Liquidity sweep / reversal |
| 2026-03-30 17:15 | Valid swing, away from level | n/a | 121.1% | 2.46x | Impulse / continuation | 0.374% | True breakout |
| 2026-04-03 16:15 | Valid swing, away from level | n/a | 205.8% | 2.46x | Impulse / continuation | -0.069% | True breakout |
| 2025-01-09 16:45 | Near Fib level | 50.0% | 46.1% | 2.46x | Impulse / continuation | -0.421% | True breakout |
| 2025-04-16 16:45 | Valid swing, away from level | n/a | -116.7% | 2.46x | Flat / fading | 0.232% | Weak move without breakout |
| 2026-04-09 10:45 | Valid swing, away from level | n/a | -6.8% | 2.46x | Flat / fading | -0.119% | Weak move without breakout |
| 2025-09-14 15:30 | Valid swing, away from level | n/a | -32.0% | 2.46x | Flat / fading | 0.006% | Weak move without breakout |
| 2025-08-08 18:00 | Valid swing, away from level | 38.2% | 26.2% | 2.46x | Reversal | 0.078% | Liquidity sweep / reversal |
| 2025-02-18 14:45 | Near Fib level | 38.2% | 40.6% | 2.46x | Reversal | -1.798% | Liquidity sweep / reversal |
| 2026-07-24 13:15 | Valid swing, away from level | n/a | 127.0% | 2.45x | Impulse / continuation | 0.521% | True breakout |
| 2026-04-09 16:00 | Valid swing, away from level | n/a | 127.0% | 2.45x | Flat / fading | 0.056% | Position building in range |
| 2025-12-01 12:30 | Valid swing, away from level | n/a | -14.6% | 2.45x | Flat / fading | -0.235% | Position building in range |
| 2026-06-22 15:00 | Valid swing, away from level | n/a | 140.8% | 2.44x | Reversal | 0.173% | Liquidity sweep / reversal |
| 2024-10-25 17:00 | Valid swing, away from level | n/a | 504.3% | 2.44x | Flat / fading | 0.555% | Position building in range |
| 2025-08-18 17:30 | Valid swing, away from level | n/a | -205.7% | 2.44x | Impulse / continuation | -0.131% | True breakout |
| 2025-10-14 16:00 | Near Fib level | 78.6% | 76.9% | 2.44x | Reversal | 0.145% | Liquidity sweep / reversal |
| 2025-11-27 16:30 | Near Fib level | 61.8% | 62.7% | 2.44x | Impulse / continuation | -1.624% | True breakout |
| 2026-06-22 12:45 | Valid swing, away from level | 78.6% | 96.6% | 2.43x | Reversal | 0.493% | Liquidity sweep / reversal |
| 2025-01-28 12:00 | Near Fib level | 61.8% | 62.3% | 2.42x | Reversal | 0.578% | Liquidity sweep / reversal |
| 2025-01-28 16:00 | Valid swing, away from level | n/a | -63.7% | 2.42x | Reversal | 0.040% | Liquidity sweep / reversal |
| 2025-06-09 11:00 | Valid swing, away from level | n/a | 732.4% | 2.41x | Reversal | -0.170% | Liquidity sweep / reversal |
| 2026-04-21 14:45 | Near Fib level | 38.2% | 35.1% | 2.41x | Impulse / continuation | -0.522% | True breakout |
| 2025-05-05 14:00 | Valid swing, away from level | n/a | 118.6% | 2.41x | Impulse / continuation | 0.020% | True breakout |
| 2026-08-11 13:15 | Valid swing, away from level | n/a | -14.0% | 2.41x | Flat / fading | -0.085% | Weak move without breakout |
| 2026-03-19 17:00 | Valid swing, away from level | n/a | 241.6% | 2.41x | Reversal | 0.380% | Liquidity sweep / reversal |
| 2025-05-05 17:00 | Valid swing, away from level | n/a | 290.4% | 2.40x | Impulse / continuation | -0.944% | True breakout |
| 2025-02-12 19:15 | Valid swing, away from level | 78.6% | 97.8% | 2.40x | Impulse / continuation | 3.889% | True breakout |
| 2026-08-14 16:15 | Valid swing, away from level | n/a | 258.4% | 2.40x | Reversal | 0.683% | Liquidity sweep / reversal |
| 2025-06-17 12:00 | Valid swing, away from level | n/a | -17.9% | 2.40x | Reversal | 0.132% | Liquidity sweep / reversal |
| 2025-03-27 16:00 | Valid swing, away from level | n/a | 136.0% | 2.40x | Impulse / continuation | 0.471% | True breakout |
| 2024-12-06 15:00 | Valid swing, away from level | n/a | -2.3% | 2.40x | Reversal | -0.647% | Liquidity sweep / reversal |
| 2025-03-05 22:30 | Valid swing, away from level | n/a | 150.9% | 2.40x | Flat / fading | -0.419% | Weak move without breakout |
| 2026-03-30 11:15 | Valid swing, away from level | n/a | 104.5% | 2.39x | Reversal | 0.509% | Liquidity sweep / reversal |
| 2025-06-27 17:30 | Valid swing, away from level | n/a | -78.8% | 2.39x | Reversal | 0.191% | Liquidity sweep / reversal |
| 2025-12-18 15:00 | Near Fib level | 38.2% | 33.8% | 2.39x | Flat / fading | -0.105% | Weak move without breakout |
| 2025-07-23 13:00 | Valid swing, away from level | n/a | 123.7% | 2.39x | Flat / fading | -0.042% | Weak move without breakout |
| 2025-02-12 14:30 | Near Fib level | 38.2% | 43.0% | 2.38x | Impulse / continuation | -0.157% | True breakout |
| 2025-12-15 13:00 | Valid swing, away from level | n/a | -8.2% | 2.38x | Flat / fading | -0.006% | Weak move without breakout |
| 2025-10-14 18:00 | Valid swing, away from level | 38.2% | 20.6% | 2.38x | Reversal | -0.384% | Liquidity sweep / reversal |
| 2025-07-28 10:45 | Valid swing, away from level | n/a | -233.3% | 2.38x | Impulse / continuation | 0.450% | True breakout |
| 2026-07-07 13:00 | Valid swing, away from level | n/a | -263.5% | 2.37x | Impulse / continuation | -0.133% | True breakout |
| 2026-01-05 10:45 | Valid swing, away from level | n/a | 356.1% | 2.37x | Flat / fading | 0.209% | Weak move without breakout |
| 2026-07-20 10:45 | Valid swing, away from level | n/a | 104.2% | 2.37x | Flat / fading | 0.616% | Weak move without breakout |
| 2025-12-15 15:45 | Valid swing, away from level | 38.2% | 7.8% | 2.36x | Impulse / continuation | 0.155% | True breakout |
| 2026-02-19 15:00 | Valid swing, away from level | n/a | 106.8% | 2.36x | Flat / fading | -0.091% | Weak move without breakout |
| 2026-03-06 13:45 | Valid swing, away from level | n/a | 201.3% | 2.36x | Impulse / continuation | -0.242% | True breakout |
| 2026-04-29 17:30 | Valid swing, away from level | n/a | 164.9% | 2.36x | Reversal | -0.379% | Liquidity sweep / reversal |
| 2025-07-28 15:45 | Valid swing, away from level | n/a | 241.6% | 2.36x | Impulse / continuation | -0.511% | True breakout |
| 2026-06-25 13:15 | Valid swing, away from level | n/a | 112.3% | 2.36x | Flat / fading | -0.286% | Weak move without breakout |
| 2025-07-23 13:15 | Valid swing, away from level | n/a | 178.9% | 2.36x | Reversal | 0.234% | Liquidity sweep / reversal |
| 2025-11-19 10:45 | Valid swing, away from level | n/a | -35.8% | 2.35x | Reversal | -0.119% | Liquidity sweep / reversal |
| 2026-04-09 19:00 | Valid swing, away from level | n/a | 206.8% | 2.35x | Flat / fading | -0.094% | Weak move without breakout |
| 2026-03-19 15:45 | Valid swing, away from level | n/a | 144.9% | 2.34x | Impulse / continuation | -0.336% | True breakout |
| 2026-08-12 14:30 | Valid swing, away from level | n/a | 122.3% | 2.34x | Impulse / continuation | -0.007% | True breakout |
| 2025-07-28 11:00 | Near Fib level | 50.0% | 45.6% | 2.34x | Impulse / continuation | 0.258% | True breakout |
| 2024-10-14 16:00 | Valid swing, away from level | n/a | -47.0% | 2.34x | Flat / fading | 0.271% | Weak move without breakout |
| 2025-05-27 11:00 | Valid swing, away from level | n/a | -25.9% | 2.34x | Impulse / continuation | 0.883% | True breakout |
| 2025-06-19 16:30 | Valid swing, away from level | n/a | 119.2% | 2.34x | Flat / fading | 0.151% | Position building in range |
| 2024-11-02 17:15 | Valid swing, away from level | n/a | 222.2% | 2.33x | Impulse / continuation | -0.663% | True breakout |
| 2025-06-10 15:00 | Valid swing, away from level | n/a | 127.9% | 2.33x | Impulse / continuation | -0.507% | True breakout |
| 2025-05-21 12:15 | Valid swing, away from level | n/a | 116.3% | 2.33x | Flat / fading | -0.290% | Weak move without breakout |
| 2025-04-07 10:00 | Valid swing, away from level | n/a | 308.5% | 2.33x | Impulse / continuation | 1.621% | True breakout |
| 2025-11-19 10:00 | Valid swing, away from level | n/a | -4.9% | 2.33x | Reversal | 0.634% | Liquidity sweep / reversal |
| 2026-03-23 13:15 | Valid swing, away from level | n/a | 150.8% | 2.33x | Impulse / continuation | -0.157% | True breakout |
| 2025-03-03 13:15 | Valid swing, away from level | n/a | 460.2% | 2.32x | Flat / fading | 0.206% | Weak move without breakout |
| 2025-05-05 14:45 | Valid swing, away from level | n/a | 160.5% | 2.32x | Reversal | -0.094% | Liquidity sweep / reversal |
| 2025-10-10 16:30 | Valid swing, away from level | n/a | 209.1% | 2.32x | Impulse -> reversal | 0.420% | False breakout |
| 2025-12-02 16:00 | Valid swing, away from level | n/a | -46.3% | 2.32x | Reversal | -0.190% | Liquidity sweep / reversal |
| 2026-03-24 15:00 | Valid swing, away from level | 38.2% | 22.2% | 2.32x | Impulse / continuation | -0.377% | True breakout |
| 2025-05-05 16:30 | Valid swing, away from level | n/a | 213.2% | 2.32x | Reversal | -1.146% | Liquidity sweep / reversal |
| 2025-11-19 10:30 | Valid swing, away from level | n/a | -39.8% | 2.31x | Impulse / continuation | -0.391% | True breakout |
| 2025-01-03 13:45 | Valid swing, away from level | n/a | 147.8% | 2.31x | Impulse / continuation | -0.319% | True breakout |
| 2025-06-27 17:00 | Valid swing, away from level | n/a | -96.2% | 2.31x | Reversal | 0.191% | Liquidity sweep / reversal |
| 2026-05-20 12:15 | Valid swing, away from level | n/a | 244.2% | 2.30x | Reversal | 0.423% | Liquidity sweep / reversal |
| 2026-07-16 11:30 | Valid swing, away from level | n/a | 243.5% | 2.29x | Impulse / continuation | -0.633% | True breakout |
| 2026-08-19 15:00 | Golden zone 50-61.8% | 50.0% | 50.2% | 2.29x | Impulse / continuation | -0.092% | True breakout |
| 2026-09-16 14:30 | Valid swing, away from level | n/a | 248.8% | 2.29x | Reversal | 0.123% | Liquidity sweep / reversal |
| 2025-12-02 14:00 | Valid swing, away from level | n/a | -13.4% | 2.29x | Flat / fading | -0.102% | Weak move without breakout |
| 2025-09-17 17:45 | Valid swing, away from level | n/a | -81.1% | 2.28x | Reversal | -0.126% | Liquidity sweep / reversal |
| 2026-09-16 16:30 | Valid swing, away from level | n/a | 307.0% | 2.27x | Impulse / continuation | -0.479% | True breakout |
| 2024-11-13 11:45 | Valid swing, away from level | n/a | 121.9% | 2.26x | Flat / fading | -0.148% | Weak move without breakout |
| 2026-09-17 14:15 | Valid swing, away from level | n/a | 224.6% | 2.25x | Impulse / continuation | 0.644% | True breakout |
| 2025-04-04 15:00 | Valid swing, away from level | n/a | 174.2% | 2.25x | Reversal | 0.211% | Liquidity sweep / reversal |
| 2025-10-13 14:45 | Valid swing, away from level | 78.6% | 87.7% | 2.25x | Impulse / continuation | 0.550% | True breakout |
| 2026-02-16 17:15 | Valid swing, away from level | n/a | -39.2% | 2.25x | Reversal | -0.448% | Liquidity sweep / reversal |
| 2025-09-17 13:15 | Near Fib level | 78.6% | 75.5% | 2.25x | Impulse / continuation | 0.102% | True breakout |
| 2025-08-22 16:30 | Valid swing, away from level | n/a | 119.4% | 2.25x | Reversal | -0.047% | Liquidity sweep / reversal |
| 2026-05-08 16:30 | Valid swing, away from level | n/a | 302.7% | 2.25x | Flat / fading | 0.105% | Position building in range |
| 2026-01-19 10:45 | Valid swing, away from level | 38.2% | 21.8% | 2.23x | Impulse / continuation | 0.373% | True breakout |
| 2026-08-20 12:15 | Valid swing, away from level | n/a | -10.6% | 2.23x | Impulse / continuation | -1.945% | True breakout |
| 2025-07-01 14:45 | Valid swing, away from level | n/a | -10.9% | 2.23x | Impulse / continuation | 0.164% | True breakout |
| 2024-11-02 18:00 | Valid swing, away from level | n/a | 308.3% | 2.23x | Impulse / continuation | -0.303% | True breakout |
| 2026-02-16 17:00 | Valid swing, away from level | n/a | -33.0% | 2.23x | Impulse -> reversal | -0.115% | False breakout |
| 2025-04-09 07:00 | Valid swing, away from level | n/a | 220.8% | 2.22x | Flat / fading | 0.638% | Weak move without breakout |
| 2026-06-26 14:45 | Near Fib level | 61.8% | 64.7% | 2.22x | Impulse / continuation | 3.053% | True breakout |
| 2026-07-15 11:30 | Valid swing, away from level | n/a | 460.0% | 2.22x | Impulse / continuation | -0.465% | True breakout |
| 2025-04-16 17:00 | Valid swing, away from level | n/a | -93.3% | 2.22x | Reversal | 0.264% | Liquidity sweep / reversal |
| 2025-08-01 14:30 | Golden zone 50-61.8% | 61.8% | 60.4% | 2.21x | Impulse / continuation | -0.291% | True breakout |
| 2026-05-25 11:45 | Valid swing, away from level | n/a | -11.3% | 2.21x | Impulse / continuation | 0.078% | True breakout |
| 2025-10-10 13:45 | Valid swing, away from level | 78.6% | 89.1% | 2.21x | Flat / fading | -0.347% | Weak move without breakout |
| 2026-02-09 15:15 | Valid swing, away from level | 38.2% | 3.9% | 2.21x | Impulse / continuation | 0.140% | True breakout |
| 2026-09-16 14:45 | Valid swing, away from level | n/a | 248.8% | 2.20x | Impulse / continuation | 0.185% | True breakout |
| 2025-10-29 14:00 | Valid swing, away from level | 38.2% | 0.8% | 2.20x | Reversal | -0.054% | Liquidity sweep / reversal |
| 2026-05-08 15:45 | Valid swing, away from level | n/a | 219.2% | 2.20x | Impulse / continuation | -0.242% | True breakout |
| 2026-08-10 14:30 | Valid swing, away from level | n/a | 117.8% | 2.19x | Flat / fading | 0.224% | Weak move without breakout |
| 2025-03-13 15:45 | Valid swing, away from level | n/a | 128.2% | 2.18x | Flat / fading | 0.312% | Weak move without breakout |
| 2025-09-16 13:00 | Valid swing, away from level | n/a | 168.2% | 2.18x | Flat / fading | 0.159% | Weak move without breakout |
| 2024-11-07 18:15 | Valid swing, away from level | n/a | -208.3% | 2.18x | Flat / fading | 0.189% | Weak move without breakout |
| 2025-05-05 18:15 | Valid swing, away from level | n/a | 425.4% | 2.18x | Reversal | 0.054% | Liquidity sweep / reversal |
| 2025-08-01 14:15 | Golden zone 50-61.8% | 50.0% | 53.3% | 2.17x | Impulse / continuation | -0.329% | True breakout |
| 2025-03-27 14:15 | Valid swing, away from level | n/a | 404.3% | 2.16x | Reversal | -1.222% | Liquidity sweep / reversal |
| 2025-06-27 18:00 | Valid swing, away from level | n/a | -155.8% | 2.16x | Flat / fading | -0.074% | Weak move without breakout |
| 2024-10-11 14:00 | Valid swing, away from level | n/a | 228.6% | 2.14x | Flat / fading | 0.196% | Position building in range |
| 2026-08-07 16:45 | Near Fib level | 61.8% | 64.4% | 2.14x | Impulse / continuation | 0.021% | True breakout |
| 2025-03-27 15:00 | Valid swing, away from level | n/a | 104.5% | 2.14x | Impulse / continuation | -1.286% | True breakout |
| 2025-04-14 11:45 | Valid swing, away from level | 38.2% | 43.7% | 2.14x | Flat / fading | -0.076% | Weak move without breakout |
| 2026-08-18 15:30 | Valid swing, away from level | n/a | -131.1% | 2.13x | Flat / fading | 0.295% | Weak move without breakout |
| 2026-09-18 14:00 | Valid swing, away from level | 38.2% | 13.7% | 2.13x | Flat / fading | 0.000% | Position building in range |
| 2025-10-08 13:30 | Valid swing, away from level | n/a | 316.9% | 2.13x | Impulse / continuation | -0.533% | True breakout |
| 2026-09-01 15:45 | Valid swing, away from level | 38.2% | 12.6% | 2.13x | Reversal | 0.149% | Liquidity sweep / reversal |
| 2024-10-18 13:45 | Valid swing, away from level | n/a | 111.8% | 2.13x | Flat / fading | -0.078% | Weak move without breakout |
| 2026-04-02 15:00 | Valid swing, away from level | 38.2% | 8.2% | 2.12x | Impulse / continuation | 0.148% | True breakout |
| 2025-03-28 12:45 | Near Fib level | 78.6% | 77.2% | 2.12x | Reversal | 0.123% | Liquidity sweep / reversal |
| 2026-07-06 12:00 | Valid swing, away from level | n/a | -11.1% | 2.11x | Reversal | -0.455% | Liquidity sweep / reversal |
| 2026-04-29 15:30 | Valid swing, away from level | n/a | 128.5% | 2.11x | Impulse / continuation | -0.578% | True breakout |
| 2025-10-08 15:45 | Valid swing, away from level | n/a | 697.6% | 2.10x | Impulse / continuation | -0.395% | True breakout |
| 2025-04-08 20:30 | Valid swing, away from level | n/a | 126.2% | 2.10x | Reversal | -0.911% | Liquidity sweep / reversal |
| 2026-07-27 13:15 | Valid swing, away from level | n/a | -19.1% | 2.09x | Impulse / continuation | 0.508% | True breakout |
| 2026-07-29 15:30 | Valid swing, away from level | n/a | -13.5% | 2.09x | Reversal | -0.254% | Liquidity sweep / reversal |
| 2026-09-08 16:15 | Valid swing, away from level | 38.2% | 14.1% | 2.09x | Impulse / continuation | -0.568% | True breakout |
| 2026-05-04 11:15 | Valid swing, away from level | n/a | -106.4% | 2.09x | Impulse / continuation | -0.378% | True breakout |
| 2026-05-08 13:45 | Valid swing, away from level | n/a | 145.2% | 2.09x | Reversal | -0.059% | Liquidity sweep / reversal |
| 2026-09-08 13:00 | Valid swing, away from level | n/a | -3.2% | 2.07x | Flat / fading | 0.098% | Weak move without breakout |
| 2025-09-18 15:30 | Valid swing, away from level | n/a | 242.6% | 2.06x | Impulse / continuation | -0.013% | True breakout |
| 2025-10-08 14:15 | Valid swing, away from level | n/a | 431.3% | 2.06x | Reversal | -0.188% | Liquidity sweep / reversal |
| 2025-12-18 18:15 | Valid swing, away from level | n/a | 156.2% | 2.05x | Reversal | 0.137% | Liquidity sweep / reversal |
| 2025-12-24 15:30 | Golden zone 50-61.8% | 50.0% | 53.7% | 2.04x | Flat / fading | 0.025% | Weak move without breakout |
| 2025-09-17 15:30 | Near Fib level | 78.6% | 79.8% | 2.02x | Flat / fading | 0.025% | Weak move without breakout |
| 2025-10-22 14:00 | Valid swing, away from level | n/a | 111.2% | 2.02x | Flat / fading | -0.463% | Weak move without breakout |
| 2026-09-08 14:00 | Valid swing, away from level | n/a | -11.5% | 2.02x | Reversal | -0.068% | Liquidity sweep / reversal |
| 2026-08-10 15:00 | Valid swing, away from level | 78.6% | 93.3% | 2.01x | Flat / fading | 0.173% | Weak move without breakout |
| 2025-09-08 11:45 | Valid swing, away from level | 38.2% | 28.0% | 2.01x | Reversal | 0.072% | Liquidity sweep / reversal |
| 2026-09-08 13:45 | Valid swing, away from level | n/a | -16.7% | 2.00x | Flat / fading | -0.106% | Weak move without breakout |
| 2026-09-01 15:15 | Valid swing, away from level | n/a | -43.2% | 2.00x | Reversal | -0.062% | Liquidity sweep / reversal |
| 2025-10-31 14:15 | Valid swing, away from level | n/a | 106.6% | 1.99x | Flat / fading | 0.278% | Weak move without breakout |
| 2025-01-10 16:45 | Valid swing, away from level | n/a | -260.7% | 1.99x | Impulse / continuation | 1.048% | True breakout |
| 2024-11-07 17:45 | Valid swing, away from level | n/a | -162.1% | 1.99x | Flat / fading | 0.331% | Weak move without breakout |
| 2026-06-10 14:45 | Near Fib level | 78.6% | 77.5% | 1.99x | Impulse / continuation | -0.156% | True breakout |
| 2026-06-26 14:15 | Valid swing, away from level | n/a | 157.6% | 1.98x | Impulse / continuation | 2.625% | True breakout |
| 2024-11-07 17:00 | Valid swing, away from level | n/a | -80.3% | 1.97x | Impulse / continuation | 1.017% | True breakout |
| 2025-10-22 16:30 | Valid swing, away from level | 78.6% | 71.6% | 1.96x | Flat / fading | -0.354% | Weak move without breakout |
| 2026-06-22 14:00 | Near Fib level | 38.2% | 36.9% | 1.94x | Reversal | -1.909% | Liquidity sweep / reversal |
| 2024-12-19 15:00 | Valid swing, away from level | n/a | -99.2% | 1.93x | Flat / fading | -0.079% | Weak move without breakout |
| 2025-10-08 14:45 | Valid swing, away from level | n/a | 526.5% | 1.92x | Impulse / continuation | -0.958% | True breakout |
| 2025-10-08 18:15 | Valid swing, away from level | n/a | 924.1% | 1.89x | Reversal | 0.607% | Liquidity sweep / reversal |
| 2025-03-03 11:45 | Valid swing, away from level | n/a | 329.6% | 1.89x | Reversal | -0.298% | Liquidity sweep / reversal |
| 2025-05-28 15:15 | Valid swing, away from level | n/a | -190.5% | 1.88x | Flat / fading | 0.125% | Weak move without breakout |
| 2025-09-23 15:00 | Valid swing, away from level | n/a | -858.6% | 1.82x | Flat / fading | 0.228% | Weak move without breakout |
| 2026-06-26 14:30 | Valid swing, away from level | n/a | 115.3% | 1.76x | Impulse / continuation | 2.876% | True breakout |
