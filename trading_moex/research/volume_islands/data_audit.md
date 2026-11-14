# VOL-ISLAND-001 Data Audit

## Local sources checked

The following read-only SQLite files were inspected on 2026-11-12:

```text
data/trader.db       4,669,440 bytes
data/trader_4h.db  107,839,488 bytes
```

Both databases contain a `candles` table with these market columns:

```text
ticker, period, begin, open, high, low, close, volume
```

Neither database contains a trade tape, bid/ask quotes, aggressor side,
buy-volume, sell-volume, delta, order-book snapshots, or footprint records.
The `side` column found in `mtf_signals` is a strategy signal field, not market
order-flow data.

## Available 4H history

`data/trader_4h.db` has 4H rows for CHMF, GAZP, LKOH, MOEX, MTSS, NLMK, NVTK,
T and TATN. It has no SBER/4h series. SBER has lower-timeframe and daily rows,
but substituting another timeframe would change the registered hypothesis.

## Consequence

The study's green/red volume is necessarily the proxy:

```text
green = volume when close > open
red   = volume when close < open
neutral = volume when close == open
```

This cannot distinguish aggressive buying from passive absorption. A bearish
candle may contain heavy buying that was absorbed by resting sellers, and a
bullish candle may contain heavy selling absorbed by buyers.

## Stop rule

Do not run more OHLCV threshold grids, pullback-level grids, or entry
optimizations for `VOL-ISLAND-001` on these databases. The baseline, five-seed
placebo, pullback study, and 27-cell sensitivity gate did not establish a
stable edge before costs. The next permitted experiment requires a new data
source with trade direction or order-flow attribution and a new immutable data
snapshot.
