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
| `ATRX-002` / `ATRX-003` | A move of N ATR from a swing plus a reversal candle is exhaustion; short after a rise, long after a fall | archived | rejected; a look-ahead defect inflated the swing study, corrected edge +0.13% is below costs, both directions lose (PF 0.796 / 0.860); extension forecasts volatility, not direction | `atr_exhaustion/` |
| `ICT-SWEEP-001` | A liquidity sweep + displacement + FVG retest reverses with a positive edge after costs | archived | rejected; originating +12.21% is a 20-trade fit (80%→40% wins across halves), best test cell is worst train cell, adaptive mode holds PF 1.04/1.06 but the edge lives in one third of the sample | `ict_sweep_fvg/` |
| `TA-ELEMENTS` | Elementary detectors (swing, level, breakout, retest, return, failure) can be verified individually and composed into systems | active (building) | library built and causally tested; recognition report on 6 tickers; not a strategy — trading layer is out of scope here | `ta_elements/` |
| `FIB-SHORT-FUT-LQDT-001` | The Fib short 1day loss is caused by stock borrow fees; a futures leg plus LQDT on free margin removes it | reviewed | borrow fully explains the stock loss (gross +16k, net -355k, 180 trades); futures+LQDT turns it positive (+19.9%) but almost all of the gain is the LQDT rate, signal-only leg PF 1.14 (noise) | `fib_short_futures_lqdt/` |
| `FIB-SR-001` | S/R levels from confirmed swing pivots improve a Fib-short TP/SL bracket | reviewed | supported: best sr_min_sl cuts 1day net loss (NET −126,625 vs −363,512, PF 1.41 vs 1.12) and, with carry removed, roughly 6x gross (+46,835 vs +7,628). Chrono split positive in both halves (+14,509 train, +8,666 test Δgross); random-level control p=0.05 | `fib_sr_bracket/` |
| `PA-LEVELS-001` | Price-action on volume-confirmed R/S levels (levels + patterns + sweep + volume profile + liquidity clusters) has a positive per-trade edge | reviewed | rejected: 1day 374 trades PF 0.83 avgR −0.112, 4h 972 trades PF 0.34 avgR −0.598; real levels indistinguishable from a random-level control (avgR −0.153, real inside the random distribution); reproduces LEVEL-TEST/ICT-SWEEP/VOL/SR rejections | `pa_levels/` |

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

`ATRX-002`/`ATRX-003` is the load-bearing result for self-criticism. It was the
strongest finding of the sequence — dose-response, 10 of 11 tickers, surviving a
20 bp cost — and it was wrong: the swing pivot was read before a fractal could
confirm it. Correcting the timing doubled the event count and collapsed the
edge. The lesson is not about ATR. It is that a convenient result is a suspect,
and that the riskiest error in this work is in one's own measurement code, not
in the market. ATR extension forecasts volatility, not direction: both the short
and the long lose once a random baseline is applied. Before any future
swing-based study, place the pivot at `len - 1 - look`.

`ICT-SWEEP-001` restates the cost corollary from a different angle. Unlike the
other studies it was not built from a scan: it was promoted from a single
web-UI run that happened to look good on twenty trades. When rebuilt and split
chronologically, the only surviving cell (adaptive thresholds plus a reachable
target) reaches PF 1.04/1.06 — indistinguishable from noise — and its profit
lives in one of three time thirds. The instructive part is the funnel: the
detector rejects 98% of sweeps, and relaxing that filter until it trades often
returns PF to 1.0 regardless of whether thresholds are measured in bars, ATR,
or R multiples. Changing the unit of a filter does not add information that is
not in the data. The same order-book limit that closed `LEVEL-TEST-001` closes
this one: a sweep is a claim about resting liquidity, and OHLCV cannot see it.

`TA-ELEMENTS` marks a change of method rather than another rejected strategy.
The studies above asked "is this system profitable" and answered no. That does
not show that price has no recognisable structure. `TA-ELEMENTS` instead builds
small, individually verified, causal detectors — swings, levels, breakouts,
retests, failures — so that systems can be assembled from parts each known to
detect what it claims. The distinction matters: an unprofitable backtest of a
full system says nothing about whether its building blocks are real. The first
recognition report already shows a usable fact (62.5% of breakouts of a swing
level return through it, 41.8% retest) computed without look-ahead, which is raw
material for a combination layer, not a trade signal.



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
