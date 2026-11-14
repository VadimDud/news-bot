# LSTM-BASELINE-001: causal feature and dataset preparation

Status: diagnostic linear baseline completed; no neural model or strategy
promotion. This study prepares OHLCV inputs and evaluates a logistic baseline
only; it does not connect to live trading.

## Frozen setup

- Features: 10 scale-aware causal candle/volume features from
  `app/lstm_features.py`.
- Sequence length: 50 bars; forecast horizon: 5 bars.
- Label: one when the forward close return exceeds the specified threshold plus
  estimated round-trip cost. Threshold and cost are CLI/research parameters and
  must be frozen before each run.
- The scaler is fit on the training prefix only. Splits are chronological;
  windows may use historical context before a test decision, never future rows.
  Folds are assigned by decision time, and training labels whose outcomes cross
  the train boundary are purged. Results retain both decision and outcome times.
- Required baselines for a future model experiment: always-up prevalence,
  logistic regression, and buy-and-hold. The current diagnostic reports
  classification metrics only; executable returns, drawdown, calibration and
  buy-and-hold are not implemented yet.
- `scripts/run_lstm_baseline.py` runs the logistic baseline and majority-class
  comparison on chronological SQLite candle folds. It is diagnostic only and
  does not place orders.
- No shuffled time split, parameter selection on test/forward data, or live
  promotion.
- Walk-forward folds use a fixed training window by default, advance by one
  test block, and fit a new scaler inside each fold. Expanding windows are
  available explicitly but must be declared in the run manifest.
- `chronological_boundaries()` provides the required non-overlapping
  train/validation/test/forward row contract for a future confirmatory run.
  The partitioned CLI mode (`--validation-bars` and `--forward-bars`) writes
  `manifest.json`, `metrics.json`, `checks.json`, `predictions.jsonl`, and
  `run.log`. It currently evaluates fixed parameters on all three partitions;
  it does not select parameters on validation or claim forward performance.

The current runner evaluates validation and historical test/forward partitions,
but does not implement parameter selection or a prospective evaluation gate.
It does not provide executable return simulation or fully protocol-compliant
artifacts; no neural network is implemented. Failed recorded sanity checks now
produce a nonzero exit status while retaining diagnostic artifacts.

## Validation-only mode

Validation-only mode is a procedural step to isolate validation metrics before
deploying a candidate. Invocation:

```bash
python3 scripts/run_lstm_baseline.py \
  --db data/trader.db \
  --ticker SBER \
  --period 15m \
  --train-bars 500 \
  --validation-bars 100 \
  --sequence-length 50 \
  --horizon 5 \
  --threshold 0.003 \
  --cost-rate 0.001 \
  --validation-only \
  --artifacts-dir artifacts/runs/lstm_baseline
```

Key properties:

- Requires `--validation-bars > 0`; disallows explicit `--test-bars` and `--forward-bars`
- SQL LIMIT: loads only `train_bars + validation_bars` rows; no test/forward data consumed
- Fingerprints consumed rows only; appended rows have no effect
- Manifest records `evaluation_mode: "validation-only"` and `run_class: "diagnostic"`
- Fit scaler on train partition; evaluate validation partition only
- No model selection, candidate search, or persistence implemented
- Fail-closed: invalid scaler or partition constraints halt execution

## Validation and prospective gate

This is a procedural specification, not an implemented selection command.
No new historical sweep or model selection was performed when writing it.

- Keep the target, horizon, costs, sequence length, feature definitions, split
  boundaries and training algorithm fixed before comparing candidates. Do not
  compare different target definitions by their classification loss.
- Any future candidate list must be finite and recorded before execution.
  Rank candidates by validation log loss only, with the training-prevalence
  predictor as baseline. Ties retain the first predeclared candidate. Require
  finite metrics, both label classes and passing sanity checks; otherwise stop.
- A candidate must strictly improve validation log loss over the baseline to
  advance. This is an engineering screening gate, not statistical proof of edge.
- Implement a validation-only mode before selection: the current runner exposes
  test/forward results and must not be used for iterative parameter selection.
  Freeze the selected model, scaler, code commit and configuration before any
  final evaluation. Do not refit after inspecting evaluation outcomes.
- All previously explored historical blocks remain diagnostic, including those
  named `test` or `forward`. No clean commit can make that history untouched.
- Prospective enrollment is not yet active. Before enrollment, record an
  immutable snapshot/hash, the maximum timestamp already inspected across all
  sources, an actual UTC freeze time, and a fixed evaluation end rule. Choose a
  start strictly after both freeze time and the inspected-data watermark; only
  completed candles with decisions and outcomes inside that new period qualify.
- Freeze the evaluation length at 2,000 completed SBER 15-minute candles before
  enrollment. Historical rows may supply causal feature context only. Do not
  inspect interim target metrics or extend the period based on results. Missing
  data, invalid checks or single-class evaluation means inconclusive, not a
  license to move boundaries or retune. No dates are asserted as enrolled here.
- A prospective classification result is not a trading gate. Execution, costs,
  uncertainty and matched trading baselines still require a separate study.

## Diagnostic result: SBER, 2026-11-14

The following table is historical diagnostic evidence from earlier code, not
results for the current implementation. Split, RSI and regularization changes
invalidate direct comparisons; do not use it for model selection.

Using the server candle snapshot (15m: 39,797 rows; 60m: 10,689 rows), horizon
4, threshold 0.003, cost 0.001, fixed windows, and train-only scaling:

| Period | Folds | Logistic accuracy / balanced accuracy / log loss | Majority accuracy / balanced accuracy / log loss |
|---|---:|---|---|
| 15m | 10 | 0.9541 / 0.5002 / 0.1935 | 0.9548 / 0.5000 / 0.1945 |
| 60m | 8 | 0.8664 / 0.5183 / 0.3882 | 0.8730 / 0.5000 / 0.3915 |

The logistic model does not demonstrate a useful edge: accuracy is dominated by
the imbalanced negative class, balanced accuracy is near chance, and it does
not beat majority accuracy. These are diagnostic results, not an OOS trading
claim; the copied database snapshot and command provenance are not stored as a
reproducible committed run artifact.

## Limitations and next step

OHLCV direction labels do not represent executable orders, queue position,
spread, market impact, or regime shifts. Class balancing must not be performed
by duplicating/shuffling test examples. The model architecture itself is not
implemented until a chronological baseline experiment is specified.

Partitioned runs now use training labels for the prior baseline, encode undefined
metrics as JSON null, fingerprint the consumed OHLCV rows, and record actual
sample containment/order checks. The `forward` block is a historical holdout,
not untouched prospective data. These artifacts remain diagnostic, not a full
execution study or evidence of profitability.

Next step: implement and test validation-only selection with a persisted frozen
model/configuration before enrolling a new prospective period.
