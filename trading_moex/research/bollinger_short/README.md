# BBS-001: Bollinger Band Breakout Short

## Status

**Rejected.** The strategy never achieves a profit factor above 1.0 in any
quarter, and the positive full-period return is an artefact of positions that
were never closed.

## Question

ZB-004 rejected `zone_break` after discovering its entire edge sat in 2023. The
obvious follow-up: does `bollinger_breakout_short`, the other positive name from
the diagnostic scan, depend on a single market window in the same way?

## Setup

Registry defaults, no tuning. `period=15min`, ten tickers, `cash_per_ticker=100_000`,
`commission=0.0005`, `slippage=0.0005` per side, window
`2025-08-28 .. 2026-09-21`.

A daily test was attempted first and is impossible: the strategy is intraday by
construction (`session_start=10`, `session_end=19`, `session_offset_hours=3`,
`close_at_eod=1`), so on `1day` candles it opens **zero** trades in every year
2021-2025. Reporting that as "no edge" would have been a false negative caused
by the wrong timeframe, not a finding. With only 13 months of 15min data,
yearly buckets are unavailable, so the decomposition is quarterly.

## Quarterly results

| window | return | PF | trades |
|--------|-------:|----:|-------:|
| 2025-08-28 .. 2025-11-01 | -0.66% | 0.401 | 25 |
| 2025-11-01 .. 2026-02-01 | +0.12% | 1.223 | 19 |
| 2026-02-01 .. 2026-05-01 | +0.25% | 0.829 | 29 |
| 2026-05-01 .. 2026-08-01 | +1.00% | 0.744 | 50 |
| 2026-08-01 .. 2026-10-01 | -0.07% | 0.867 | 17 |

**Profit factor is below 1.0 in four of five quarters.** One quarter edges just
above at 1.223 on 19 trades.

## The positive quarters are not profit

This is where the study turned into a bug hunt. The 2026-05..08 quarter returns
+1.00% with PF 0.744 — a quarter cannot be profitable with a losing profit
factor unless something outside closed trades is contributing.

`MTSS` in that quarter is the clearest case:

| metric | value |
|--------|------:|
| closed trades | 7 |
| winning trades | **0** |
| closed PnL | -2,703.61 |
| unrealized PnL | **+11,940.92** |
| reported return | **+9.24%** |

Seven losing trades and an open short marked to market produced a +9.24%
"return". The position never exited; the gain is entirely paper. `MOEX`
(+7.84%, PF 0.12, 4 trades) and `CHMF` (+3.91%) have the same shape.

## The fix this exposed

`total_return_pct` in `app/backtest.py` was computed from broker value at the
last bar, which includes open positions marked to market. Nothing in the report
said so, and the only clue was an `open_positions` list a careless reader would
skip.

The metrics now carry `realized_pnl`, `unrealized_pnl` and
`includes_unrealized_pnl`, and a test reconciles the three against
`final_value - initial_cash`. This is not cosmetic: 32 stored results across
`zone_break` and `bollinger_breakout_short` had unclosed positions at the period
end.

The ZB-004 conclusion was re-verified after the fix and does not change — there
unrealized PnL is within ±1,600 on totals of tens of thousands, so the rejection
stands on realized numbers.

## What the evidence cannot establish

- Long-run behaviour. Thirteen months of intraday data is one regime; the
  quarterly decomposition is the finest split the data permits.
- That the one quarter at PF 1.223 is meaningful. It rests on 19 trades.

## Decision

Rejected. Do not trade, do not promote, do not tune.

## Next Step

Stop testing breakout variants against MOEX intraday data. `zone_break` and
`bollinger_breakout_short` now reach the same verdict from different angles —
one earns everything in a single year, the other never clears PF 1.0 at all. A
future attempt should start from a different family with a stated mechanism
(carry, or mean reversion at a level that is tested rather than assumed),
because another breakout rule on this data will reproduce this result.
