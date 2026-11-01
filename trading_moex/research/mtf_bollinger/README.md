# MTF-BB-001: MTF Bollinger Breakout

## Hypothesis

The shipped default `MtfBollingerStrategy` — slow-timeframe upper-band breakout
bias plus a fast-timeframe pullback entry and an ATR OCO bracket — has positive
net expectancy on the ten-ticker H4/M15 pool after realistic costs.

## Current Status

- Lifecycle: `rejected` for the shipped defaults.
- Evidence: `negative`. See `experiments/MTF-BB-001-baseline.yaml` (commit
  `05f1840`, clean worktree).

## Result Summary

Run on `data/trader_4h.db`, `15min`, ten tickers, window `2025-08-28 .. 2026-09-21`.

| commission | slippage | pooled return | PF    | trades |
|-----------:|---------:|--------------:|------:|-------:|
|     0.0000 |   0.0005 |       -0.2709% | 0.770 |     34 |
|     0.0000 |   0.0010 |       -0.4740% | 0.651 |     34 |
|     0.0005 |   0.0005 |       -0.5869% | 0.591 |     34 |
|     0.0005 |   0.0010 |       -0.7890% | 0.512 |     34 |
|     0.0010 |   0.0005 |       -0.9025% | 0.467 |     34 |
|     0.0010 |   0.0010 |       -1.1027% | 0.411 |     34 |

Split halves at `commission=0.0005`, `slippage=0.0005`:

| split | pooled return | PF    | trades | wins |
|-------|--------------:|------:|-------:|-----:|
| train |       -0.0827% | 0.824 |     14 |    2 |
| test  |       -0.4661% | 0.498 |     19 |    4 |

Per ticker: MTSS `+2.09%`, TATN `+1.40%`, T `+0.26%`, NLMK `+0.24%`,
LKOH `+0.02%`, GAZP `-3.40%`, SBER `-2.25%`, NVTK `-1.94%`, MOEX `-1.18%`,
CHMF `-1.11%`.

Sanity checks: 10 series loaded, no empty series, no positions left open at the
end of any run.

## Limitations

- Only 34 trades across ten tickers; the sample is far too small for a
  confident claim in either direction.
- Defaults were taken as shipped, not tuned, so this measures the default
  configuration rather than the strategy family's ceiling.
- Slippage is modelled per side; spread, lot size, borrow and liquidity are not.
- Per-ticker equal-cash results are not a common-cash portfolio result.

## Next Step

Stop parameter work on `mtf_bollinger` defaults: negative at zero cost means
there is no gross edge to recover. If the family is revisited, change the
mechanism (entry timing or exit structure), not the numeric defaults.
