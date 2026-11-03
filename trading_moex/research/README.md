# Research Registry

This directory stores research decisions and experiment specifications. Generated
run outputs belong under `artifacts/runs/` and are intentionally not committed.

## Studies

| Study | Hypothesis | Status | Current conclusion | Source |
|---|---|---|---|---|
| `SR-001` | Higher-timeframe support/resistance breakout with lower-timeframe retest is robust after costs | archived | rejected; negative in every cost cell including zero commission | `sr/` |
| `MTF-BB-001` | Multi-timeframe Bollinger direction with lower-timeframe entry is robust after costs | archived | rejected; -0.59% full, negative in both halves | `mtf_bollinger/` |
| `SCREEN-001` | Shipped defaults of the registry contain a profitable strategy | archived | diagnostic only; found two positive candidates, both later rejected | `screen/` |
| `ZB-002` / `ZB-004` | A strong-body breakout of a 20-bar zone continues to 2R | archived | rejected; full-period gain is 2023 alone, test half is -1.59% at PF 0.766 | `zone_break/` |
| `BBS-001` | Bollinger band breakdown short is profitable intraday | archived | rejected; PF below 1.0 in four of five quarters, gains are unrealised | `bollinger_short/` |
| `RSI-001` | Daily RSI oversold/overbought mean reversion is profitable after costs | archived | rejected; uniform weakness across years, test half -5.99% | `rsi_meanrev/` |
| `LEVEL-TEST-001` | Price levels exist in OHLCV beyond what random price lines produce | archived | rejected; seven formulations, every apparent effect failed a matched control | `levels_event_study/` |
| `DS-001` / `SF-001` | A fast departure from a level, as momentum or as exhaustion, is tradeable | archived | rejected; momentum -22.88% realised, fade -65.76% net, all 10 tickers | `departure_speed/` |
| `VOL-001` | Breakout volume predicts continuation (or reversal) | archived | rejected; sign flips by timeframe, intraday effect below costs and unstable | `volume_effect/` |

## Overall State

No strategy in the registry has demonstrated an edge on the available data.
Every study above reached `rejected` for a structural reason rather than bad
luck: dependence on a single market year, profit factor that never clears 1.0,
or uniform weakness. Read `screen/README.md` before proposing a new study — the
diagnostic scan that started this sequence is a selection-bias trap and must not
be repeated.

The next attempt requires a new hypothesis and, ideally, deeper history (daily
candles only reach 2021 for nine of ten tickers; only SBER goes back to 2010),
not another parameter sweep on this sample.

`LEVEL-TEST-001` is the load-bearing result for the whole sequence. Ten studies
tested strategies built on levels; that study tested the prerequisite, that the
levels exist. They do not, at least not in a way observable in OHLCV. Reading it
first would have made `SR-001`, `ZB-002`, `ZB-004` and `DS-001`/`SF-001` cheaper
to decide: the phenomenon they trade is absent from the data, so how they are
built matters less than usual.

The corollary for cost: absorption and resting-order execution are only visible
in the order book and the trade tape. Either acquire that data, or stop working
on level-based intraday ideas on this feed.

## Required Files

- `protocol.md` defines the common experiment protocol.
- `retention.md` defines storage and cleanup rules.
- Each study directory contains its hypothesis, audit status, known limits,
  decisions, and experiment specifications.

## Run Naming

Every execution gets a new UTC run ID:

`YYYYMMDDTHHMMSSZ_<study-id>_<git-short-sha>_<suffix>`

Never overwrite a prior run. A run is reproducible only when its manifest,
code state, input-data fingerprint, parameters, and execution model are recorded.

## Status Vocabulary

Study lifecycle: `proposed`, `active`, `reviewed`, `archived`.

Evidence conclusion: `inconclusive`, `rejected`, `promising`, `validated`.

Successful program execution is not evidence that a hypothesis is validated.
