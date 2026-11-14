# PA-LEVELS-STRICT-007 / video clarification v3

Frozen before the v3 run on 2026-11-10. Separate, opt-in research variant.
Does not alter legacy, live, or default behaviour. Not a reconstruction of the
unavailable video. Dirty-worktree executions are diagnostic, never OOS.

## Written rules from the user (author-confirmed in this thread)

1. Trend context: determine direction on the higher timeframe (e.g. 1h) using
   closed candles only.
2. Levels: mark key levels on the higher timeframe where the market made strong
   reversals. Validate a level when the area was repeatedly confirmed by
   rebounds. Focus on **large zigzags only**; ignore noise.
3. Entry timeframe: switch to the working timeframe (e.g. 5m) for entries.
4. Watch price approach the level, then an **impulsive breakout** of the level,
   then an **impulsive return** back through it.
5. After the return, wait for a **range-compression (squeeze)** reversal model.
6. Enter when the reversal model forms. Stop: behind the breakout candle extreme
   OR behind a protected level. Take profit: nearest significant level OR 1:2.
7. Exit: if price turns toward the stop without reaching the target, close early.
8. A level that was broken does NOT automatically change role. It becomes the
   new S/R state only if price **retests it from the other side and bounces**;
   otherwise the level is **deleted**.
9. If the breakout is only a **wick/shadow**, the level is not broken — it stays
   valid and its significance **increases** (harder touch, false-break).
10. The nearest significant target level must not be a trivially close level; a
    target is only a level that has not been easily broken (else it is no longer
    a level).

## Operational assumptions (NOT attributed to the author)

- Zigzag threshold `zigzag_atr` (default 2.0 ATR) defines "large reversal".
  It is a detector parameter, not video text.
- Independent-touch count for validation defaults to 3; separation, cluster
  zone, reversal amplitude are detector choices.
- Impulse proxy: range >= `impulse_range_atr` ATR and directional body >=
  `impulse_body` of range, on both breakout and return candles.
- Compression proxy: ranges non-increasing over `compression_length` bars after
  the return, final range <= `compression_atr` ATR, body <= `compression_body`.
- Target rule: nearest significant opposite HTF level that is at least
  `min_target_atr` ATR away, but never closer than 2R; else 2R.
- Stop mode: `breakout` (behind breakout-candle extreme + buffer) or
  `protected` (nearest known adverse LTF extremum + buffer). One is frozen per
  run; both reported, not selected by profit.
- Bailout: adverse close vs entry, executed at next open, entry bar included.

## Causal state machine

- HTF levels are built only from HTF data via a causal zigzag; each pivot is
  confirmed only when the opposite leg completes, and made available at the
  confirming HTF close (no future median, no same-bar use).
- HTF trend uses only closed HTF candles vs EMA (EMA span is a detector choice).
- LTF: level crossing -> body breakout (close through) OR wick false-break
  (strengthens level) -> impulsive return through the same level -> compression
  strictly after the return -> entry at next open, trend-aligned.
- Broken-by-body levels enter a retest state: flip role only on a bounce from
  the other side within `retest_bars`; otherwise deleted permanently.
- Next-open execution, unit-risk net R, one position per ticker, OCO, costs and
  bailout use the corrected harness.

## Primary data pair and transfer

Primary pair is `60min` HTF / `5min` LTF, per ticker, only where both exist.
On the local DB this is **SBER only** (~1 year: 5411 HTF bars, 59834 LTF bars).
`4h`/`1day` is run only as a clearly-labelled hypothesis transfer, not the video
analogue. If a pair has too few trades, that is reported as insufficient data,
not as evidence of no edge.

Costs: commission 0.0005 and slippage 0.0005 per side, zero spread. Report n,
attrition funnel, mean/sum unit-risk R, win rate, PF, calendar cohorts and
leave-one-out where meaningful. No grid, no parameter search, no OOS claim.

## Limitations

- Video order-book liquidity and the exact named reversal candle are
  unavailable in OHLCV; compression/impulse are proxies.
- The primary pair has one ticker and about one year; strict sequence yields
  very few signals. This is a data-availability limitation, not a verdict.
- Timestamps stored UTC-naive; market calendar Europe/Moscow.

One next step: obtain a multi-ticker, multi-year `60min`/`5min` snapshot (or
timestamped annotated video setups) before any confirmatory inference.
