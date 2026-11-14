# Order-flow scenarios

## Status

Proposed, data collection not yet started. This is an analysis layer only; it
does not create live signals or place orders.

## Hypothesis

On 15-minute bars, trade-flow direction and top-five-level book imbalance may
contain information about the next four-bar return beyond OHLCV.

## Fixed scenarios

- `CONTINUATION_LONG`: buy delta ratio >= 0.10 and book imbalance >= 0.20.
- `CONTINUATION_SHORT`: sell delta ratio <= -0.10 and book imbalance <= -0.20.
- `CONFLICT_BUY_FLOW_SELL_BOOK`: buy flow with sell-side book imbalance.
- `CONFLICT_SELL_FLOW_BUY_BOOK`: sell flow with buy-side book imbalance.

Only bars with flow coverage >= 80% are eligible. Results are grouped by
ticker and scenario, with sample count, mean forward return, win rate, and a
95% Wilson interval. No parameter selection is allowed from the final test
window.

## Data contract

The bot stores validated T-Bank events in `adaptive_trades` and
`adaptive_books`. OHLCV candles are read from `candles`. Event timestamps are
UTC-aware at ingestion; SQLite candle timestamps retain the project's existing
UTC-naive storage convention and are normalized at the analysis boundary.

## Current evidence

No `adaptive_trades` or `adaptive_books` rows exist in the checked local
databases, so no market statistic can be reported yet. The implementation and
synthetic causal tests are ready.

## One next step

Enable the read-only market-data stream and accumulate at least one complete
trading month before evaluating these fixed scenarios.
