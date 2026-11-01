# Instructions For AI Agents

## Scope

This repository contains production bot code and experimental trading research.
Never promote a research strategy to live trading, production signals, or the
default strategy set without explicit approval and passing the study's gates.

## Required Reading

For any research task, read:

1. `research/README.md`;
2. `research/protocol.md`;
3. the selected study directory, such as `research/sr/`;
4. `RUNBOOK.md` before touching live or deployment code.

## Research Organization

- Keep hypotheses, specifications, decisions, and audit checklists in
  `research/`; commit these small text files.
- Put generated output in a new `artifacts/runs/<study>/<run-id>/` directory.
- Never overwrite a run. Save `manifest.json`, `metrics.json`, `checks.json`,
  a complete compressed trade ledger, and `run.log`.
- Record exact command, commit, dirty-worktree status, data fingerprint,
  parameters, periods, tickers, capital, commission, slippage, and execution
  assumptions.
- Preserve failed runs and explain their failure. Do not delete negative
  results to improve the apparent performance.
- Do not store secrets, credentials, unrelated database tables, or full
  environment dumps in research artifacts.
- Do not call a result reproducible when the code was run from a dirty worktree
  unless it is explicitly labelled diagnostic.

## Experiment Rules

- Define one falsifiable hypothesis, baseline, parameters, success criteria, and
  stop criteria before running.
- Separate train, validation, test, and forward periods chronologically.
- Never select parameters using test or forward results.
- Report pooled portfolio results separately from equal-cash per-ticker results.
- Include sanity checks for lookahead, data quality, open positions, stop/target
  direction, risk limits, OCO behavior, margin rejects, and duplicate exits.
- End every research report with limitations and exactly one concrete next step
  or a reason to stop.

## Cleanup And Collaboration

- Read `research/retention.md`; cleanup is dry-run by default.
- Show exact paths, sizes, ages, reasons, and replacement evidence before cleanup.
- Move approved candidates to `artifacts/quarantine/` before deletion.
- Never delete active runs, cited evidence, source databases, secrets, or files
  with unclear ownership. Never use `git clean` for housekeeping.
- Do not revert or overwrite another user's uncommitted changes.
- In a mixed worktree, stage only explicitly reviewed files; do not use
  `git add -A`.

## Completion Report

State what was checked, files changed, tests/commands run, run IDs created,
provenance status, limitations, and unresolved follow-ups. If the task changes
research methodology, update the relevant `research/` document in the same
change.
