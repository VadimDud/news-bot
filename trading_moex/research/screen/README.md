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

Done, and concluded negatively. `zone_break` became study ZB-002 in
`research/zone_break/`, re-run through the committed harness and reproduced
exactly. ZB-002 rejected it for statistical power (59 trades, wide-`rr`
dependency). ZB-004 then supplied the missing data — same configuration, daily
candles, 250 trades — and the strategy failed: test PF 0.766 at -1.59%, with
the entire edge sitting in 2023.

The other positive row from this scan, `bollinger_breakout_short`, was checked
the same way as `BBS-001` and also rejected: its profit factor never reaches 1.0
in any quarter, and the positive return came from open positions marked to
market rather than from closed trades.

Both positive candidates are gone, and both fell for structural reasons rather
than bad luck: one earned everything in a single market year, the other never
cleared PF 1.0. That is the expected outcome of a multi-strategy scan and the
argument for not repeating one. Do not re-run this scan — the selection bias is
exactly what `research/protocol.md` warns against.

## Exposure-adjusted recheck (EXP-003)

RSI-001 concluded that raw return against zero is the wrong test when the
dataset halves differ by 60 percentage points. EXP-003 therefore re-read both
rejected strategies with exposure-aware metrics.

| strategy | split | return | exposure | return per exposure | buy&hold |
|----------|-------|-------:|---------:|--------------------:|---------:|
| zone_break | train | +3.22% | 13.5% | +23.84% | +32.37% |
| zone_break | test | -1.59% | 11.8% | -13.46% | -28.30% |
| rsi | train | +0.43% | 24.3% | +1.78% | +32.37% |
| rsi | test | -5.99% | 21.1% | -28.41% | -28.30% |

Both keep the same sign in both halves, so the exposure correction confirms
the rejections instead of overturning them. Note that neither strategy beats
buy-and-hold in the rising half by any interpretation.

The first attempt at this calculation was itself wrong: averaging per-ticker
return-on-exposure ratios gave rsi a meaningless +18.45% in 2023, because GAZP
at 1.6% exposure turned a +2.02% return into a +128.5% ratio. The pooled metric
is now exposure-weighted and computed from pooled PnL, guarded by a test.
