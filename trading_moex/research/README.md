# Research Registry

This directory stores research decisions and experiment specifications. Generated
run outputs belong under `artifacts/runs/` and are intentionally not committed.

## Studies

| Study | Hypothesis | Status | Current conclusion | Source |
|---|---|---|---|---|
| `SR-001` | Higher-timeframe support/resistance breakout with lower-timeframe retest is robust after costs | active | inconclusive; execution audit and independent validation remain required | `sr/` |

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
