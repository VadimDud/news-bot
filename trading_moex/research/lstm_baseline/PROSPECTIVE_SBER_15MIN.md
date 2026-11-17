# Prospective SBER 15-Minute Paper Evaluation

Status: **not enrolled**. This document freezes the protocol; it does not
authorize live trading, automatic training, or model promotion.

## Objective

Evaluate the already frozen LSTM configuration on exactly 2,000 newly completed
SBER `15min` candles after enrollment. Historical rows may provide causal
sequence warmup only. The evaluation is paper-only and classification metrics
are not executable-return or profitability evidence.

## Enrollment Freeze

Before the first eligible candle is collected, record all of the following in
an immutable manifest:

- `freeze_time_utc`: actual UTC time when enrollment is frozen;
- `inspected_data_watermark_utc`: maximum candle timestamp already inspected
  across candles, dividend data, code, and prior artifacts;
- immutable OHLCV snapshot or durable snapshot hash;
- git commit and clean-worktree status;
- exact command, dependency versions, database identifier, and timezone
  contract;
- the Smartlab dividend-calendar rows and its canonical SHA-256 hash.

The first eligible candle must be strictly later than both the freeze time and
the inspected-data watermark. Do not enroll a historical range that was already
used in the frozen-window diagnostics. Do not inspect interim target metrics,
move the start boundary, retune parameters, or extend the evaluation period.

## Fixed Data Contract

- Ticker: `SBER`.
- Stored period: `15min`.
- Evaluation length: exactly 2,000 completed candles.
- Training prefix: exactly the last 500 completed historical candles before
  enrollment freeze; earlier rows are causal feature warmup only. The scaler is
  fitted on those 500 training rows only.
- Storage timestamps: UTC-naive SQLite values.
- Market calendar: `Europe/Moscow`.
- Historical rows before enrollment: feature warmup only.
- No forming or incomplete candle may enter the evaluation partition.
- Every decision and its five-candle outcome must be contained in the enrolled
  evaluation range. Samples whose outcome would cross the range boundary are
  excluded, not moved into another partition.

## Frozen Model Contract

Do not change these values during enrollment or evaluation:

- sequence length: `50`;
- horizon: `5` candles;
- threshold: `0.003`;
- cost rate used by the label: `0.001`;
- LSTM hidden size: `32`;
- LSTM layers: `2`;
- dropout: `0.2`;
- learning rate: `0.001`;
- batch size: `32`;
- epochs: `50`;
- seed: `42`.

The scaler is fitted only on the declared training prefix. No validation or
forward result may influence training, parameter choice, or feature changes.

## Dividend Contract

Smartlab is the trusted dividend-calendar source for this protocol. Its
`cutoff_date` is used as the ex-date. The label-only mask excludes a sample
when the Moscow calendar date of the cutoff lies in the decision-to-outcome
interval:

```text
decision_day < smartlab_cutoff_date <= outcome_day
```

The mask does not alter OHLCV, features, scaler fitting, or dividend cash
flows. The manifest must record the complete calendar, source values, hash,
date semantics, and excluded sample counts for every partition. An unavailable
or empty calendar is a failed enrollment, not an unmasked run.

## Required Outcome States

- `completed`: all 2,000 candles and required samples are present; all checks
  pass; metrics are finite.
- `inconclusive`: missing data, failed sanity checks, or a single-class
  evaluation partition. Keep the artifacts and do not move boundaries.
- `failed`: execution or artifact failure. Keep the failure manifest.

Neither `completed` nor `inconclusive` authorizes trading. A separate study is
required for execution simulation, costs, drawdown, uncertainty, and paper
position accounting.

## Implementation Gate

Enrollment must not start until one runner supports all of these together:

1. fixed timestamp/date enrollment after the freeze watermark;
2. exactly 2,000 completed forward candles;
3. Smartlab label masking with provenance;
4. causal warmup and boundary checks;
5. immutable manifest and snapshot hash;
6. no interim metric output that can guide retuning.

The current neural runner has Smartlab masking but only train/validation
windows. The current partitioned baseline runner has chronological partitions
but no Smartlab masking or prospective enrollment controls. Therefore this
protocol was not executable with those runners. The separate
`scripts/run_lstm_prospective.py` now implements `enroll`, `check`, and
`evaluate`; it has synthetic coverage but still needs a PyTorch-enabled
integration test before a real enrollment. No real enrollment has been made.

### Prospective Runner

- All commands require a clean committed worktree and recorded numpy, pandas,
  PyTorch and Python versions. Evaluation requires the same commit, environment,
  database path and unchanged Smartlab calendar as enrollment.
- `enroll --prior-inspected-watermark <aware-UTC-timestamp>` requires an audited
  maximum previously inspected candle timestamp. It combines this with the
  database watermark, freezes historical OHLCV, and records the actual freeze
  time. It does not require future candles or train a model. Operators must not
  create replacement enrollments to evade a failed evaluation.
- The final 500 completed historical rows define training decisions and scaler
  fitting. Earlier rows provide causal feature warmup. Training outcomes must
  remain within the frozen history. No forward tensors enter the training API;
  its required validation argument receives training tensors only, and the
  fixed-epoch history is discarded (no early stopping or selection).
- `check --enrollment <directory>` reports readiness without metrics.
  `evaluate --enrollment <directory>` waits until the first 2,000 completed
  rows strictly after both boundaries exist, then evaluates once. Session gaps
  do not count as rows. Later rows do not extend the evaluation window.
- All commands also require `--db` and `--artifacts-dir`. Each invocation writes
  a new output directory. A permanent exclusive `evaluation.claim` inside the
  enrollment directory prevents concurrent or repeated terminal evaluations,
  including retries after errors. Never remove that claim to rerun a study.
- An unchanged calendar is required; a new or revised dividend invalidates this
  implementation's run rather than silently changing labels. Missing forward
  rows produce `waiting`; invalid data/classes produce `inconclusive`; execution
  errors produce `failed`. Final classification metrics compare LSTM, logistic
  (learning rate 0.05, 300 epochs, L2 1.0) and training prevalence.
- This runner does not provide execution returns, trade ledgers, model promotion,
  or protection against deliberate editing/copying of enrollment artifacts.

## Resource And Token Budget

Use a two-stage workflow to avoid wasting computation and context:

1. `scripts/enroll_prospective_lstm.py` currently records only a diagnostic
   pre-enrollment snapshot (`status=snapshot_recorded`,
   `enrollment_authorized=false`, no enrollment freeze). It preserves OHLCV CSV
   and calendar hashes from one read-only SQLite transaction. Review only
   `manifest.json` and `checks.json`. Its watermark covers database candles,
   not an audit of prior artifacts. Actual enrollment remains blocked by the
   Implementation Gate above and requires a new freeze after that gate passes.
   The 2,000-candle requirement is future evaluation length, not a minimum
   historical row count. The future end timestamp cannot yet be determined.
2. Until all 2,000 candles are collected, perform only cheap checks: latest
   completed timestamp, row count, calendar hash, and database freshness.
3. Do not train, recompute historical windows, or ask agents to summarize the
   same artifacts repeatedly. Pass run IDs, hashes, and a small metrics table
   instead of raw logs.
4. After the evaluation end rule is reached, run the frozen command once and
   inspect `manifest.json`, `checks.json`, and `metrics.json` first. Read
   predictions or logs only when a check fails or a specific anomaly requires
   diagnosis.
5. Delegate bounded read-only reviews with exact paths and request concise
   findings; never include secrets, full database exports, or environment dumps.

## Acceptance And Stop Rules

Before enrollment, predeclare the primary metric and baseline. The primary
classification metric is validation/forward log loss, compared with the frozen
logistic and prevalence baselines on the same retained samples. Report
balanced accuracy and confusion matrices as secondary diagnostics.

Stop and report inconclusive if any required artifact, timestamp boundary,
calendar hash, class check, or finite-metric check fails. Do not retry with a
different boundary or parameters. A result is not a trading gate even if the
LSTM beats a baseline.
