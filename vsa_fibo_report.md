# VSA and Fibonacci Cycle Statistics: `T` / `15min`

## Data and Methodology
- Source: read-only SQLite database `/tmp/tech_news_trader_analysis.db`.
- History: **38144** candles, `2024-09-24 09:45:00` to `2026-09-24 12:00:00`.
- Anomalous volume: `Volume >= 2.5 * SMA_Volume(20)`; SMA excludes the signal candle.
- ATR(14) uses prior true ranges and excludes the signal candle from its mean.
- VSA categories use the exact thresholds from the research brief. Overlapping categories are assigned exclusively with momentum taking priority over rejection, and rejection over absorption; the final table has one row per event.
- Forward direction is measured from signal close in the direction of its close relative to open. Doji anomalies have no directional win/reversal classification.
- MFE uses the best high/low excursion in the favorable direction; MAE is the maximum adverse excursion, reported positive. Flat means all next four highs/lows remain inside the signal range.
- Cycle observations use consecutive close-to-close directional runs. The initial impulse and next opposite run must have exact lengths in `{1, 2, 3, 5, 8, 13}`; continuation means a close breaks the impulse endpoint in the original direction within 13 bars after correction and before the impulse start is invalidated.

## 1. VSA Comparison (8-bar horizon)
| Type of anomaly | Events | Reversal (%) | Continuation (%) | Flat (%) | Mean MFE (% / ATR) | Mean MAE (%) |
|---|---:|---:|---:|---:|---:|---:|
| Absorption / stopping volume | 21 | 53.85% | 46.15% | 9.52% | 0.44% / 2.49 ATR | 0.29% |
| Rejection / liquidity sweep | 507 | 45.89% | 53.05% | 11.83% | 0.41% / 2.51 ATR | 0.39% |
| Trend climax / pure momentum | 856 | 50.35% | 49.42% | 14.25% | 0.52% / 2.91 ATR | 0.43% |

### Reaction by Horizon
| Anomaly | Horizon | Events | Directional win | Reversal | Mean MFE % | Mean MFE ATR | Mean MAE % | Flat (4 bars) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Absorption / stopping volume | 1 | 13 | 61.54% | 38.46% | 0.23% | 0.81 ATR | 0.08% | 9.52% |
| Absorption / stopping volume | 3 | 13 | 92.31% | 7.69% | 0.30% | 1.13 ATR | 0.14% | 9.52% |
| Absorption / stopping volume | 5 | 13 | 76.92% | 23.08% | 0.43% | 2.39 ATR | 0.17% | 9.52% |
| Absorption / stopping volume | 8 | 13 | 46.15% | 53.85% | 0.44% | 2.49 ATR | 0.29% | 9.52% |
| Rejection / liquidity sweep | 1 | 476 | 50.21% | 46.43% | 0.16% | 0.92 ATR | 0.14% | 11.83% |
| Rejection / liquidity sweep | 3 | 475 | 51.79% | 46.74% | 0.26% | 1.50 ATR | 0.25% | 11.83% |
| Rejection / liquidity sweep | 5 | 475 | 52.42% | 47.16% | 0.33% | 1.91 ATR | 0.32% | 11.83% |
| Rejection / liquidity sweep | 8 | 475 | 53.05% | 45.89% | 0.41% | 2.51 ATR | 0.39% | 11.83% |
| Trend climax / pure momentum | 1 | 856 | 42.41% | 54.79% | 0.22% | 1.17 ATR | 0.18% | 14.25% |
| Trend climax / pure momentum | 3 | 856 | 49.77% | 48.60% | 0.37% | 2.01 ATR | 0.28% | 14.25% |
| Trend climax / pure momentum | 5 | 856 | 49.30% | 50.12% | 0.44% | 2.47 ATR | 0.35% | 14.25% |
| Trend climax / pure momentum | 8 | 856 | 49.42% | 50.35% | 0.52% | 2.91 ATR | 0.43% | 14.25% |

## 2. Fibonacci Time-Cycle Matrix
Cycle observations with exact Fib counts: **16124**; VSA-anchored observations: **506**.
Probability in each cell is the percentage of observations where the original direction later breaks the impulse endpoint.
| Impulse \ Correction | 1 | 2 | 3 | 5 | 8 | 13 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 59.27% | 31.24% | 14.35% | 1.90% | 4.55% | n/a |
| 2 | 67.71% | 42.51% | 24.91% | 3.09% | 11.11% | n/a |
| 3 | 71.50% | 52.12% | 33.18% | 10.87% | 0.00% | n/a |
| 5 | 78.80% | 50.51% | 34.55% | 25.00% | n/a | n/a |
| 8 | 75.86% | 77.78% | 0.00% | 0.00% | n/a | n/a |
| 13 | n/a | n/a | n/a | n/a | n/a | n/a |

### Correction Depth
| Correction depth | Events | Continuation | Mean depth | Interpretation |
|---|---:|---:|---:|---|
| >61.8% | 10071 | 32.51% | 445.44% | Deep correction / invalidation risk |
| <=38.2% | 3885 | 84.07% | 20.53% | Shallow correction |
| 38.2-50% | 1257 | 70.49% | 44.67% | Moderate correction |
| 50-61.8% | 911 | 67.18% | 55.84% | Golden-zone correction |

## 3. Practical Conclusions
- Highest simple MFE-minus-MAE expectancy proxy at 8 bars: **Absorption / stopping volume** (0.15%); this is descriptive and excludes fees, slippage and position sizing.
- Best observed correction-depth bucket: **<=38.2%** with 84.07% continuation (3885 observations).
- Highest observed impulse/correction ratio bucket: **5.00** with 78.8% continuation (n=217); do not treat a small cell as a stable edge.
- The bot should treat VSA category and cycle count as filters or context, not standalone entries. The cycle matrix is vulnerable to overlapping events and multiple testing.
- A production rule should be validated with walk-forward splits, costs, non-overlapping trades, and a minimum sample size per cell before deployment.

## Top VSA Events
| Timestamp | Anomaly | Volume ratio | Direction | Range/ATR | Body/range | Win 8 | MFE 8 | MAE 8 |
|---|---|---:|---|---:|---:|---:|---:|---:|
| 2025-11-10 07:00 | Trend climax / pure momentum | 64.99x | bullish | 18.40x | 83.70% | 0.00% | 0.03% | 0.21% |
| 2026-06-14 18:45 | Trend climax / pure momentum | 64.91x | bullish | 29.05x | 97.59% | 100.00% | 0.79% | 0.00% |
| 2025-06-01 10:00 | Rejection / liquidity sweep | 48.18x | bearish | 61.89x | 18.57% | 100.00% | 0.50% | 0.06% |
| 2025-05-10 18:30 | Rejection / liquidity sweep | 47.08x | bearish | 55.03x | 18.00% | 0.00% | 0.05% | 3.13% |
| 2026-04-17 09:45 | Absorption / stopping volume | 40.16x | doji | 0.00x | 0.00% | n/a | 2.56% | 0.00% |
| 2025-03-31 06:45 | Absorption / stopping volume | 39.23x | doji | n/ax | 0.00% | n/a | 3.89% | 0.00% |
| 2026-05-04 07:00 | Trend climax / pure momentum | 39.02x | bullish | 17.56x | 73.91% | 100.00% | 0.41% | 0.01% |
| 2025-05-17 18:00 | Trend climax / pure momentum | 34.32x | bullish | 15.97x | 74.03% | 100.00% | 1.22% | 0.14% |
| 2025-06-29 16:15 | Rejection / liquidity sweep | 32.42x | bullish | 12.25x | 16.33% | 0.00% | 0.17% | 0.13% |
| 2025-03-16 16:00 | Trend climax / pure momentum | 24.87x | bullish | 36.31x | 75.90% | 100.00% | 1.04% | 0.05% |
| 2024-09-30 10:00 | Trend climax / pure momentum | 24.43x | bullish | 6.88x | 73.21% | 0.00% | 0.32% | 0.58% |
| 2026-03-16 07:00 | Trend climax / pure momentum | 23.81x | bullish | 4.28x | 75.68% | 0.00% | 0.01% | 0.25% |
| 2025-12-29 07:00 | Trend climax / pure momentum | 23.74x | bearish | 7.91x | 86.54% | 0.00% | 0.16% | 0.53% |
| 2026-07-05 10:00 | Rejection / liquidity sweep | 23.73x | bullish | 4.28x | 21.43% | 100.00% | 0.49% | 0.03% |
| 2025-12-22 07:00 | Rejection / liquidity sweep | 23.42x | doji | 8.75x | 0.00% | n/a | 0.28% | 0.00% |
| 2026-08-17 07:00 | Trend climax / pure momentum | 23.06x | bearish | 7.96x | 82.56% | 100.00% | 1.06% | 0.50% |
| 2026-09-21 07:00 | Rejection / liquidity sweep | 21.63x | bullish | 7.00x | 20.83% | 100.00% | 0.77% | 0.02% |
| 2025-08-18 07:00 | Trend climax / pure momentum | 20.95x | bullish | 7.79x | 71.30% | 100.00% | 0.62% | 0.13% |
| 2025-12-15 07:00 | Rejection / liquidity sweep | 20.58x | bearish | 4.47x | 1.89% | 0.00% | -0.00% | 0.64% |
| 2026-02-09 07:00 | Trend climax / pure momentum | 19.63x | bearish | 10.63x | 75.00% | 100.00% | 0.26% | 0.09% |
| 2026-02-26 09:45 | Trend climax / pure momentum | 19.62x | bullish | 7.43x | 86.96% | 0.00% | -0.01% | 0.29% |
| 2026-09-06 18:45 | Trend climax / pure momentum | 18.93x | bearish | 9.01x | 83.47% | 0.00% | -0.15% | 0.59% |
| 2026-06-19 13:30 | Trend climax / pure momentum | 18.78x | bearish | 12.58x | 75.91% | 0.00% | 0.36% | 0.68% |
| 2026-03-20 10:30 | Rejection / liquidity sweep | 18.09x | bullish | 14.88x | 26.30% | 100.00% | 0.47% | 0.04% |
| 2025-02-10 22:30 | Trend climax / pure momentum | 18.06x | bearish | 18.21x | 89.95% | 0.00% | 0.74% | 1.21% |
