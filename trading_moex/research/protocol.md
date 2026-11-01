# Research Protocol

## Before Running

1. Read `research/README.md`, this file, and the selected study directory.
2. Create or update a study specification with one falsifiable hypothesis,
   baseline, parameters, costs, data window, success criteria, and stop criteria.
3. Do not change code or parameters between runs in one comparison.
4. Use a clean commit for confirmatory runs. Dirty-worktree runs are diagnostic
   and must be labelled as such.

## Time Convention

- Candle rows in SQLite are UTC-naive for backward compatibility.
- Session and user-facing time is `Europe/Moscow` (UTC+3).
- Normalize timestamps explicitly at data boundaries and record both zones in
  every research manifest.

## Required Provenance

Each run must save a manifest containing:

- run ID, study ID, UTC start/end time, exact command, and exit status;
- git commit, dirty-worktree flag, Python and dependency versions;
- database path identifier, selected table/columns, tickers, timeframe,
  date range, timezone, warmup and train/validation/test role;
- input OHLCV fingerprint and, for confirmatory runs, an immutable local data
  snapshot or a durable reference to one;
- strategy and resolved parameters, capital, commission, slippage, spread,
  sizing, and execution assumptions.

Do not store secrets, full environment dumps, unrelated database tables, or
credentials in manifests and logs.

## Required Outputs

Store all outputs in one new `artifacts/runs/<study>/<run-id>/` directory:

- `manifest.json`;
- `metrics.json`;
- `checks.json` with data and execution sanity checks;
- `trades.csv.gz` or `trades.jsonl.gz` with the complete trade ledger;
- `run.log` and, only when useful, generated figures.

At minimum the ledger should include ticker, side, setup, level, touches, zone,
entry, stop, target, initial R, exit, exit reason, commission, slippage, bars
held, MFE, MAE, and whether the target was real or synthetic.

## Analysis Rules

- Separate train, validation, test, and forward/paper periods chronologically.
- Do not select parameters using test or forward results.
- Compare against no-trade and relevant simple baselines.
- Report pooled portfolio metrics separately from equal-cash per-ticker metrics.
- Report costs, drawdown, trade count, median trade, worst trade, expectancy,
  exposure, per-ticker and per-window results, and uncertainty intervals.
- Run sanity checks for lookahead, data order/duplicates, open positions,
  stop/target direction, risk limits, OCO double exits, and margin rejects.
- Preserve failed runs and their failure reason.

## Agent Completion Report

Every research task must state:

1. hypothesis and exact data/parameters/costs;
2. run IDs and provenance status;
3. metrics and sanity-check results;
4. code and test changes;
5. what the evidence cannot establish;
6. one concrete next experiment or the reason to stop.
