# LSTM-BASELINE-001: causal feature and dataset preparation

Status: diagnostic linear baseline completed; a separate PyTorch LSTM runner
is implemented with synthetic integration coverage. Neither model is approved
for trading. There is no live connection or automatic training scheduler.

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
- Candle OHLCV is raw and not dividend-adjusted. For a diagnostic comparison,
  `scripts/run_lstm_neural.py --exclude-dividend-labels` excludes a sample when
  its decision-to-outcome interval crosses an ex-date from the database's
  `dividends` table; timestamps are mapped from UTC-naive storage into
  `Europe/Moscow` calendar dates. Decision is at candle close, so an ex-date
  already completed before the decision is not masked. This masks labels only:
  it does not change features or simulate receiving dividend cash. The runner
  fails with an artifact if the requested calendar cannot be loaded or is empty.
  Calendar dates and sources plus excluded sample counts are recorded in the
  manifest. Smartlab is the trusted source for the current SBER dividend
  calendar, and its `cutoff_date` is used as the ex-date for this protocol.
  Results remain diagnostic only because the model still lacks executable return
  simulation and is not approved for trading.
- The manifest records the trusted Smartlab date semantics explicitly.
  The frozen 2026-11-16 SBER 15min windows had dividend exclusions only at
  offset 17000 (5 training samples); offsets 1000, 5000, 9000, and 13000 had
  no applicable exclusions. Offset 5000 still failed closed because validation
  contained one class. These are audit counts, not model results.
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
artifacts; the separate neural runner is described below. Failed recorded sanity checks now
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
- This mode does not select candidates; it persists a replayable diagnostic model
  artifact for one fixed configuration.
- Fail-closed: invalid scaler or partition constraints halt execution

## Validation and prospective gate

The finite validation selector is now implemented in
`scripts/select_lstm_baseline.py`. It is still a diagnostic screening tool, not
an OOS result or a trading approval.

- Keep the target, horizon, costs, sequence length, feature definitions, split
  boundaries and training algorithm fixed before comparing candidates. Do not
  compare different target definitions by their classification loss.
- Any future candidate list must be finite and recorded before execution.
  Rank candidates by validation log loss only, with the training-prevalence
  predictor as baseline. Ties retain the first predeclared candidate. Require
  finite metrics, both label classes and passing sanity checks; otherwise stop.
- A candidate must strictly improve validation log loss over the baseline to
  advance. This is an engineering screening gate, not statistical proof of edge.
- The selector requires a predeclared JSON list of at most 10 distinct positive
  finite `l2` values. It loads only train+validation rows, ranks by validation
  log loss, preserves declaration order on ties, and requires strict improvement
  over the training-prevalence baseline. No test/forward data is read.
- Optimizer settings are explicitly passed and recorded: learning rate 0.05,
  300 epochs. The manifest also records the selection metric, baseline,
  strict-improvement requirement and first-declared tie rule, including failures.
- Freeze the selected model, scaler, code commit and configuration before any
  final evaluation. Do not refit after inspecting evaluation outcomes. A
  rejected selector run is a valid result and produces no model artifact.
- Feature/scaler preparation and partition/class/baseline failures preserve
  failed-run artifacts; model-save
  failures clear the selected winner in manifest and metrics, and mark checks
  and the run log as failed. Candidate specifications are retained locally.

### Selector artifact replay compatibility

When a selector run selects a winner, it now persists:
- **model.json**: Serialized weights, bias, scaler (same format as runner)
- **predictions.jsonl**: Validation predictions ledger (line-delimited JSON)
- **manifest.json**: Run metadata with model_artifact and resolved_boundaries

Both runner and selector artifacts are compatible with `app.model_loader.load_and_predict()`:

```python
from pathlib import Path
from app.model_loader import load_and_predict

# Load selector artifact (same interface as runner)
run_dir = Path("artifacts/runs/lstm_baseline/<selector_run_id>")
probs, artifact, manifest = load_and_predict(run_dir)

# Probabilities exactly match validation predictions from predictions.jsonl
```

Rejected selector runs do not produce model artifacts or predictions ledgers. Model loader validates:
- Run was validation-only with zero exit status
- Model SHA256 matches manifest
- Data SHA256 matches consumed candles
- All numeric values are finite
- Dimensions and schema are compatible
- Ledger timestamps, labels and probabilities match reconstructed validation samples

Exact replay requires a compatible numerical environment. These integrity checks
do not authenticate artifacts or establish profitability. Argument/data-loading
errors still return before a run directory is created. A failed input's
fingerprint records consumed rows, not proof of data validity.
Artifact I/O errors return structured stderr and exit 1. Partial run directories
are preserved, not removed; a storage failure can prevent writing failure metadata.
Do not treat an incomplete directory or a nonzero-exit run as a successful freeze.

### Prospective limitations

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

### Artifact Atomicity and Manifest Guarantee

The selector writes manifest.json **only after ALL outputs are complete and verified**:

- **Early failures** (scaler/partition errors before fitting): diagnostics and a
  manifest with `exit_status=1` are written; loader rejects the run.
- **Model save or predictions write errors**: exception caught, error.json and a
  manifest with `exit_status=1` are written. Partial directory is preserved.
- **Successful selection**: all outputs written (model.json, predictions.jsonl,
  metrics.json, checks.json), then manifest.json written **atomically** via temp
  file + os.replace(). No intermediate success state if os.replace fails.
- **Rejected selection** (no winner passes baseline): manifest.json written atomically
  with selection.status="rejected", exit_status=0.

The loader validates exit_status=0 and presence of manifest.json before accepting
an artifact. A failed run directory is preserved with diagnostics but never passes
loader validation. This prevents incomplete artifacts from being used in production.

## PyTorch LSTM Neural Network Implementation

A PyTorch LSTM neural classifier is now available for comparison with the logistic
baseline. This implementation is **unvalidated research code** and must follow the
same protocols as the logistic baseline.

### Installation

PyTorch is an optional dependency. To run LSTM experiments, install CPU PyTorch:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

For GPU support (NVIDIA only):
```bash
pip install torch
```

### Key Properties

- **Optional dependency**: if PyTorch is not available, `app.lstm_neural` fails
  gracefully with `TORCH_AVAILABLE = False`; runner handles missing torch by
  reporting an error and exiting with status 1
- **Deterministic training**: fixed random seed (default 42) ensures reproducible
  model initialization and weight updates
- **Input validation**: model rejects non-finite data, wrong dimensions, mismatched
  label lengths, non-binary labels, and insufficient training data before training
- **Sequence-based**: model expects 3D input `(batch, sequence_length, n_features)`
  with consistent sequence length within training/validation batches
- **Binary classification**: outputs probabilities in [0, 1] for class 1; class
  probabilities are `[1 - prob, prob]`
- **Eval mode after training**: model is set to `torch.no_grad()` eval mode after
  training to ensure deterministic inference (no dropout)
- **Weights persistence**: trained state dictionaries saved as `lstm_weights.pt`;
  loading uses `torch.load(..., weights_only=True)`.

### Architecture

- **Input size**: 10 (causal OHLCV features from `app/lstm_features.py`)
- **Sequence length**: 50 bars (configurable)
- **Hidden size**: 32 units (configurable, default)
- **Layers**: 2 LSTM layers (configurable, default)
- **Dropout**: 0.2 (configurable, default; applied between LSTM layers)
- **Output**: single sigmoid neuron for binary classification

### Configuration and Hyperparameters

See `app/lstm_neural.py::LSTMConfig` for all tunable parameters:

```python
LSTMConfig(
    input_size=10,           # Fixed to feature count
    hidden_size=32,          # LSTM hidden dimension
    num_layers=2,            # Stacked LSTM layers
    dropout=0.2,             # Between-layer dropout (0 if single layer)
    learning_rate=0.001,     # Adam optimizer learning rate
    batch_size=32,           # Training batch size
    epochs=50,               # Training epochs
    seed=42,                 # Random seed for reproducibility
)
```

### Runner

`scripts/run_lstm_neural.py` runs the LSTM classifier on chronological validation
folds. Invocation:

```bash
python3 scripts/run_lstm_neural.py \
  --db data/trader.db \
  --ticker SBER \
  --period 15m \
  --train-bars 500 \
  --validation-bars 100 \
  --start-bar 0 \
  --sequence-length 50 \
  --horizon 5 \
  --threshold 0.003 \
  --cost-rate 0.001 \
  --artifacts-dir artifacts/runs/lstm_neural
```

**Output artifacts** (on success):

- `manifest.json`: Run metadata, command, commit, timestamp, exit_status
- `metrics.json`: ClassificationMetrics (accuracy, balanced_accuracy, log_loss,
  confusion matrix, precision, recall, f1)
- `checks.json`: Sanity checks (row count, both classes present, non-finite
  values, causality)
- `lstm_weights.pt`: Saved LSTM model weights (PyTorch format)
- `train_predictions.csv` and `validation_predictions.csv`: decision/outcome
  timestamps, labels, and probabilities from all three models
- `scaler.json`: FeatureScaler state and ordered feature names
- `run.log`: Training history and diagnostics

**Output artifacts** (on failure):

- `manifest.json`: Run metadata with exit_status=1
- `run.log`: Diagnostics when execution reached feature preparation
- Other partial artifacts as available

### Validation-Only Mode

Same as logistic baseline:

```bash
python3 scripts/run_lstm_neural.py \
  --db data/trader.db \
  --ticker SBER \
  --period 15m \
  --train-bars 500 \
  --validation-bars 100 \
  --sequence-length 50 \
  --horizon 5 \
  --threshold 0.003 \
  --cost-rate 0.001 \
  --artifacts-dir artifacts/runs/lstm_neural
```

- Loads only `train_bars + validation_bars` rows
- `--start-bar` selects a later chronological window; earlier rows are feature
  warmup only, and the fingerprint covers the selected train+validation candles.
- Fits scaler on training partition only
- Evaluates on validation partition only
- Records mode as `validation-only` in manifest
- Does not select or promote candidates

### Research Protocols

The LSTM implementation is **unvalidated and must not be promoted to live
trading**:

- **No profitability claim**: classification accuracy does not imply executable
  returns. Missing: commission simulation, slippage, queue position, spread,
  market impact, regime detection.
- **Validation-only**: run on held-out validation data using the same protocol
  as the logistic baseline before any comparative claims. Test/forward data
  remain historical diagnostics.
- **Parameter freeze**: before evaluation, freeze all hyperparameters (learning
  rate, hidden size, layers, dropout, training epochs, batch size, seed).
  Do not refit or retune after inspecting results.
- **Sanity checks**: verify sufficient samples, both classes present, no
  lookahead, non-finite values detected, timestamp causality preserved.
- **Finite metrics required**: log loss, accuracy, balanced accuracy must be
  finite and properly computed before comparing to baseline.
- **Baseline comparison**: compare log loss (primary metric) against
  training-prevalence majority-class predictor. Strict improvement required to
  advance. Tied metrics favor declared order.
- **Comparison scope**: train on same data, use same features, same scaler
  (fit on training only), same split boundaries, same target definition,
  predeclared regularization (LSTM dropout versus logistic L2 penalty).

### Limitations

- **Neural network does not guarantee edge**: LSTM is more expressive than
  logistic regression but overfits more readily on small datasets. Validation
  metrics may not transfer to held-out prospective data.
- **Not a trading strategy**: direction predictions do not include execution
  cost, risk, or market microstructure. A profitable LSTM classifier on
  historical validation folds is not evidence of executable returns.
- **Determinism assumes CPU PyTorch**: GPU training may introduce
  non-deterministic numerical behavior even with fixed seeds (cuDNN).
- **Sequence assumptions**: model expects fixed sequence length and sufficient
  historical context (50 bars). Sparse or gappy data may require preprocessing.
- **No class balancing**: model trains on imbalanced labels without
  resampling/weighting. If labels are highly skewed, validation metrics may
  be dominated by the majority class.

### Next Step

After running LSTM validation and logistic baseline on the same data:

1. Compare validation log loss, balanced accuracy, and confusion matrices
2. Verify both models pass sanity checks (causality, sufficient data, both
   classes, finite metrics)
3. If LSTM strictly improves log loss over majority baseline and logistic
   baseline, record the freeze point (commit, hyperparameters, data boundaries)
4. **Do not** inspect test/forward metrics before freezing
5. If no improvement, stop and document why the neural model did not help

This is a diagnostic comparison, not proof of profitability or edge.

### Frozen Multi-Window Diagnostic (2026-11-16)

To assess stability without retuning, run five chronologically spaced,
non-overlapping 600-row windows at offsets 1000, 5000, 9000, 13000, and
17000 from the ordered SBER `15min` history. Each window uses 500 train bars
followed by 100 validation bars. Keep every model/target parameter above fixed;
do not select epochs or other parameters from validation results. The runner's
`--start-bar` treats earlier rows only as causal feature warmup and fingerprints
the selected window. Each run is diagnostic; repeated historical validation is
not prospective evidence, and no profitability claim is possible from these
classification metrics.

## Limitations and next step

OHLCV direction labels do not represent executable orders, queue position,
spread, market impact, or regime shifts. Class balancing must not be performed
by duplicating/shuffling test examples.

Partitioned runs now use training labels for the prior baseline, encode undefined
metrics as JSON null, fingerprint the consumed OHLCV rows, and record actual
sample containment/order checks. The `forward` block is a historical holdout,
not untouched prospective data. These artifacts remain diagnostic, not a full
execution study or evidence of profitability.

Next step: run LSTM validation experiment on SBER 15m with 500-bar training and
100-bar validation; compare log loss and balanced accuracy against logistic
baseline and majority predictor. Record all three run artifacts and document
whether neural model justifies further investigation.
