# SR-001: Support/Resistance MTF

## Hypothesis

A confirmed higher-timeframe level breakout followed by a lower-timeframe
retest may have more robust expectancy than a simple level rejection after
realistic costs and execution constraints.

The strategy is research-only. Do not enable it for live trading, production
signals, or the default strategy set before the validation gates pass.

## Current Status

- Lifecycle: `rejected`.
- Evidence: `negative`. The baseline re-run on committed code (`a9d3747`) is
  negative in every cost cell and in both split halves; see `decisions.md`
  "Baseline Re-Run Fails Gates".
- Historical test results are validation/diagnostic evidence, not an independent
  holdout. The period after `2026-04-01` has already been inspected.
- The execution/OCO/EOD audit is complete (15/15 gates, `audit.md`), but the
  clean baseline run now fails every declared gate, so the hypothesis is not
  supported by this implementation.

## Legacy Baseline

Historical runs used `data/trader_4h.db`, `15min`, and ten tickers:
`CHMF`, `GAZP`, `LKOH`, `MOEX`, `MTSS`, `NLMK`, `NVTK`, `SBER`, `T`, `TATN`.
The usual commission was `0.0005` per side. Existing figures are retained as
legacy validation notes only and must not be presented as current confirmation.

Reported scenario-mode-2 diagnostics were approximately `+4.87%` train and
`+0.99%` test when summing independent ticker runs. This is not portfolio
performance; results were unstable by period and sensitive to costs.

## Blocking Audit

Before new parameter searches, add deterministic tests and resolve or explicitly
accept the following:

- retest setup must filter touch count, require a new boundary crossing, expire,
  invalidate, and be consumed exactly once;
- level selection must not depend on list order or future bars;
- bracket replacement at breakeven must preserve protection and OCO semantics;
- EOD and final-bar liquidation must not submit duplicate closes or reverse;
- actual stop distance, sizing distance, initial R, target, and breakeven must agree;
- insufficient cash, short margin, rejected orders, and pending state must be safe;
- pivot confirmation, warmup, bucket timezone, and no-lookahead behavior must be tested.

## Known Model Limits

- M15 is aggregated into H4 inside the strategy; this is not a full D1/H4-level
  plus M15/H1 execution architecture.
- `level_touches` is currently a swing-candidate count, not confirmed candle
  reactions with cooldown and minimum displacement.
- Tick size, lot size, spread, slippage, borrow, short margin, and liquidity are
  not fully modeled by the current backtest.
- Synthetic targets and real opposing-level targets must be reported separately.
- Per-ticker equal-cash results are not a common-cash portfolio result.

## Study Rules

Use `research/protocol.md` for every run. The first approved comparison is a
baseline plus no more than twelve predeclared one-factor ablations. Do not
perform an unconstrained parameter grid. Do not interpret a positive result as
validated unless the predeclared out-of-sample and cost criteria pass.
