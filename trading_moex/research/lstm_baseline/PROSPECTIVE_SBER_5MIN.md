# Prospective SBER 5-Minute Paper Evaluation

Status: **enrollment authorized**. The user authorized automated collection and
one terminal paper evaluation. Live trading and model promotion are prohibited.
The immutable enrollment manifest records whether and when enrollment occurred.

## Objective

Evaluate the already frozen LSTM configuration on exactly 2,000 newly completed
SBER `5min` candles after enrollment. Historical rows may provide causal
sequence warmup only. The evaluation is paper-only and classification metrics
are not executable-return or profitability evidence.

This is a separate prospective study for 5-minute bars. It mirrors the
15-minute study with a 75-minute (15-bar) prediction horizon. Bars do not
guarantee 75 minutes of elapsed time; gaps and session boundaries may
fragment the forward window.

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
- Stored period: `5min`.
- Evaluation length: exactly 2,000 completed candles.
- Training prefix: exactly the last 500 completed historical candles before
  enrollment freeze; earlier rows are causal feature warmup only. The scaler is
  fitted on those 500 training rows only.
- Storage timestamps: UTC-naive SQLite values.
- Market calendar: `Europe/Moscow`.
- Historical rows before enrollment: feature warmup only.
- No forming or incomplete candle may enter the evaluation partition.
- Every decision and its 15-candle outcome must be contained in the enrolled
  evaluation range. Samples whose outcome would cross the range boundary are
  excluded, not moved into another partition.

### Horizon and Session Gaps

The horizon is 15 bars, spanning nominally 75 minutes (15 × 5min). In practice,
gaps between market sessions and trading halts may fragment the forward window.
The sequence partition does not guarantee elapsed time; it counts completed bars
only. If a decision window ends before the market opens the next day, its outcome
 may fall on a later session. The interval metric
records only bar count.

## Frozen Model Contract

Do not change these values during enrollment or evaluation:

- sequence length: `50`;
- horizon: `15` candles (nominally 75 minutes);
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
Sequence and feature windows remain bar-based: 50 bars represent nominally
250 minutes rather than 750 minutes in the 15-minute study. Fit a separate
scaler. Report both studies independently; do not select a winner or retune
using either forward result. Their evaluation periods will differ.

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
6. no interim metric output that can guide retuning;
7. 5-minute candles with 15-bar horizon (75 minutes nominal).

The runner `scripts/run_lstm_prospective_5min.py` extends the 15-minute runner
with 5-minute support and the 15-bar horizon. No real enrollment has been made.

### Automated Collection

The enrolled run is collected by `scripts/run_lstm_sandbox_worker_5min.py` from
the T-Bank sandbox only. The user-level timer runs hourly and appends only new,
completed, immutable OHLCV rows to the separate research DB. It validates the
frozen checkout, records source-batch hashes, and runs `check` without metrics
until exactly 2,000 forward rows exist. A permanent enrollment claim and a
process lock make terminal evaluation single-use. Transient sandbox failures
retry on the next timer invocation; validation or calendar changes stop the
worker for review. No orders or live signals are enabled.

## Acceptance And Stop Rules

Before enrollment, predeclare the primary metric and baseline. The primary
classification metric is validation/forward log loss, compared with the frozen
logistic and prevalence baselines on the same retained samples. Report
balanced accuracy and confusion matrices as secondary diagnostics.

Stop and report inconclusive if any required artifact, timestamp boundary,
calendar hash, class check, or finite-metric check fails. Do not retry with a
different boundary or parameters. A result is not a trading gate even if the
LSTM beats a baseline.
