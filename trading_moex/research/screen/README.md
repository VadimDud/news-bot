# Strategy Screen (dated, non-conclusive)

## Purpose

One-shot scan of the shipped default parameter sets across the strategy
registry, to see which strategies are worth a real study. **This is not
validation.** Picking the best result from many strategies on the same data is
selection bias; nothing here may be promoted on the strength of this table.

## Method

- `data/trader_4h.db`, `15min`, ten tickers, `2025-08-28 .. 2026-09-21`.
- Defaults from `STRATEGIES` registry; `cash_per_ticker = 100_000`.
- Full period at `commission=0.0005`, `slippage=0.0005`.
- Commit `d723724` lineage; helper scripts were throwaway and are not part of
  the repo, so these numbers are **diagnostic only**, not reproducible runs.

## Results (full period, 0.05% commission + 0.05% slippage per side)

| strategy | return | PF | trades |
|----------|-------:|----:|-------:|
| zone_break | +1.16% | 1.325 | 59 |
| bollinger_breakout_short | +0.73% | 0.587 | 135 |
| mtf_bollinger | -0.59% | 0.591 | 34 |
| bollinger_breakout | -2.17% | 0.430 | 108 |
| vol_breakdown | -6.88% | 0.552 | 336 |
| engulfing | -7.05% | 0.511 | 520 |
| pinbar | -9.03% | 0.570 | 692 |
| ma_trend | -10.41% | 0.572 | 590 |
| support_resistance_mtf | -14.94% | 0.459 | 795 |
| rsi | -40.35% | 0.594 | 2644 |
| donchian | -48.46% | 0.516 | 3325 |
| kinetic | -48.49% | 0.415 | 1600 |

Not scanned: `roe_portfolio` (needs multi-feed + fundamentals),
`elliott_candles` (custom engine, `cls` is None), `fib_pullback` and
`ict_sweep_fvg` (too slow to finish: one ticker exceeded 300 s for
`ict_sweep_fvg`, which looks like superlinear cost and deserves its own look).

## The two positive rows are not "profitable strategies"

### `bollinger_breakout_short` — positive return, PF below 1

Return is positive while profit factor is `0.587` (52 wins / 83 losses). The
whole gain sits in three tickers (MOEX `+7.84%`, MTSS `+9.24%`, CHMF `+3.91%`)
and one ticker (MTSS) has **zero** wins. Split halves:

| split | c=0 | c=0.0005 | c=0.001 |
|-------|----:|---------:|--------:|
| train | +0.09% | -0.34% | -1.06% |
| test | +0.70% | +0.17% | -0.70% |

It is negative at realistic cost on train, and turns negative on test at the
highest cost cell. This is a fragile, cost-sensitive artefact.

### `zone_break` — the one with an actual edge signal

PF above 1 in every cell, and positive in **both** split halves:

| split | c=0 | c=0.0005 | c=0.001 |
|-------|----:|---------:|--------:|
| train | +0.17% | +0.09% | -0.03% |
| test | +1.54% | +1.08% | +0.39% |

Caveats: only 8 train trades and ~51 test trades, and train breaks even at the
highest cost cell. The sample cannot support a claim stronger than "worth a
proper study".

## Next Step

Open `zone_break` as its own study with a predeclared hypothesis and gates, and
re-run it through a committed harness so the numbers are reproducible. Do not
trade it, and do not repeat this multi-strategy scan — the selection bias is
exactly what `research/protocol.md` warns against.
