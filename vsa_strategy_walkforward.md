# VSA Strategy Walk-Forward: `T` / `15min`

## Contract
- Source: read-only SQLite `/tmp/tech_news_trader_analysis.db`.
- Candles: **38144**, `2024-09-24 09:45:00` to `2026-09-24 12:00:00`.
- Direction: long only; initial equity 1,000,000 RUB; leverage 1.0; risk 0.15% per trade.
- 4-hour context uses only completed 4-hour bars from the last 90 calendar days and EMA(20/50/200).
- Candidate matrix: M0/M1/M2/M3 x MARKET/LIMIT/STOP_LIMIT.
- Splits: chronological 60% train, 20% validation, 20% untouched OOS.

## Results
| Mode | Order | Segment | Trades | PF | Net PnL | Return % | Max DD % | Sharpe |
|---|---|---|---:|---:|---:|---:|---:|---:|
| M0 | MARKET | train | 1.0000 | 0.0000 | -423.1865 | -0.0423 | 0.0423 | -0.8209 |
| M0 | MARKET | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M0 | LIMIT | train | 1.0000 | 0.0000 | -277.7234 | -0.0278 | 0.0278 | -0.8209 |
| M0 | LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M0 | STOP_LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M0 | STOP_LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | MARKET | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | MARKET | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | STOP_LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M1 | STOP_LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | MARKET | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | MARKET | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | STOP_LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M2 | STOP_LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | MARKET | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | MARKET | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | STOP_LIMIT | train | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |
| M3 | STOP_LIMIT | validation | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | n/a |

## Selection
- Selected candidate: **NONE**.
- A candidate is eligible only with validation trades >= 50, PF >= 1.05, validation max DD <= 1.5%, and positive validation PnL.
- OOS performance is reported only after selection; it is never used for selection.
- `DEPLOYMENT_NOT_APPROVED` if no candidate is selected or if OOS gates in the strategy specification fail.
## Data Sufficiency
- Observed 4h periods in lookback: **381**.
- Required completed 4h periods: **200**.
- Lookback: **90 calendar days**.
- Status: **READY**.
