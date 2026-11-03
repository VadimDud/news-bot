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
