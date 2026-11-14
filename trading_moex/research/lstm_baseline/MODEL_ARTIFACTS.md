# LSTM Baseline Model Artifacts

## Overview

The LSTM baseline research now supports persisting trained models as JSON artifacts in validation-only mode. This enables exact replay and reproducibility of validation probabilities without retraining.

## Running Validation-Only Mode with Artifact Persistence

```bash
python scripts/run_lstm_baseline.py \
  --db data/trader.db \
  --ticker SBER \
  --period 1h \
  --train-bars 500 \
  --validation-bars 100 \
  --sequence-length 50 \
  --horizon 5 \
  --threshold 0.003 \
  --cost-rate 0.001 \
  --validation-only \
  --artifacts-dir artifacts/runs/lstm_baseline
```

**Note**: `--validation-only` mode is required to generate model artifacts. Other modes (walk-forward, partitioned) do not persist model files.

## Artifact Structure

When validation-only completes successfully, the run directory contains:

```
artifacts/runs/lstm_baseline/20261114T150848726775Z_lstm_baseline_validation_only/
├── manifest.json          # Run metadata and parameters
├── model.json             # Persisted model weights, bias, scaler (strict JSON)
├── predictions.jsonl      # Validation probabilities (line-delimited JSON)
├── metrics.json           # Classification metrics
├── checks.json            # Sanity checks
└── run.log                # Execution log
```

## Loading and Replaying

To load a persisted model and exactly reproduce validation predictions:

```python
from pathlib import Path
from app.model_loader import load_and_predict

run_dir = Path("artifacts/runs/lstm_baseline/20261114T150848726775Z_lstm_baseline_validation_only")
probs, artifact, manifest = load_and_predict(run_dir)

# probs: 1D numpy array of validation probabilities
# artifact: ModelArtifact with weights, bias, scaler, metadata
# manifest: dict with run parameters and validation info
```

## Validation Guarantees

The loader performs strict validation before replay:

1. **Manifest validation**: Ensures run was validation-only mode with zero exit status
2. **Model hash**: SHA256 of model.json must match manifest entry (detects corruption)
3. **Data integrity**: OHLCV candles fingerprint must match (detects data changes)
4. **Schema**: Only schema_version "1.0" supported
5. **Feature columns**: Must match FEATURE_COLUMNS tuple exactly
6. **Dimensions**: Weights flattened shape must equal sequence_length × n_features
7. **Finitude**: All numeric values must be finite (no NaN, Inf, -Inf)
8. **Scale positivity**: Scaler scale must be strictly positive

## Artifact Format (model.json)

```json
{
  "metadata": {
    "schema_version": "1.0",
    "base_feature_columns": ["return_1", "return_5", ..., "atr_ratio"],
    "sequence_length": 50,
    "feature_count": 500,
    "scaler_mean_count": 10,
    "scaler_scale_count": 10,
    "weights_count": 500
  },
  "weights": [0.123, -0.456, ...],  // 500-element flattened array
  "bias": 0.789,
  "scaler_mean": [1.0, 2.0, ...],   // 10-element array
  "scaler_scale": [0.5, 0.6, ...]   // 10-element array (strictly positive)
}
```

All numeric values are JSON-compliant floats (no NaN, Inf, -Inf).

## Limitations & Caveats

1. **Validation-only scope**: Artifacts are created only for `--validation-only` mode
2. **FEATURE_COLUMNS immutable**: If features change, old artifacts become incompatible
3. **Training scaler only**: Scaler is fit on training data only (rows 0:train_bars)
4. **Data-bound**: Predictions exactly match only with identical input candles
5. **No train data**: Raw candles or training sequences are not persisted

## Testing

Unit and integration tests verify artifact persistence:

```bash
# Run all tests including artifact tests
pytest tests/test_lstm_runner.py tests/test_lstm_features.py \
        tests/test_lstm_baseline.py tests/test_model_artifact.py -q

# Expected output: 49 passed
```

Key test: `test_runner_and_loader_exact_probability_match` verifies that validation probabilities from predictions.jsonl exactly match loader-regenerated predictions (bit-for-bit).

## Manifest Entries

The manifest.json includes artifact metadata:

```json
{
  "model_artifact": {
    "path": "model.json",
    "sha256": "e3c0553a367cac40e84c029f5e80108d8cf571466ead15820a7b39bf85b93477",
    "schema_version": "1.0"
  },
  "evaluation_mode": "validation-only",
  "exit_status": 0,
  "data_sha256": "c5f4ddfc7ff20498a37139f0ac306af297c2ab9d682890193233b5a03f343a96",
  ...
}
```

## Implementation Files

- `app/model_artifact.py`: Save/load persisted models with validation
- `app/model_loader.py`: Replay runner results by reading manifest and model
- `tests/test_model_artifact.py`: Comprehensive unit and integration tests
- `scripts/run_lstm_baseline.py`: Modified to save artifacts in validation-only mode
