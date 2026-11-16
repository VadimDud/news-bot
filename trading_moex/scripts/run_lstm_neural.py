#!/usr/bin/env python3
"""Run PyTorch LSTM neural network baseline for directional classification research.

This script is validation-only and does NOT connect to live trading. It trains
a fixed-architecture LSTM on causal features using train-only scaling and
chronological partitions, comparing validation performance against the logistic
baseline and training prevalence.

PyTorch is optional; the script reports if unavailable without breaking existing tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import numbers
import shlex
import subprocess
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.lstm_baseline import ClassificationMetrics, classification_metrics, fit_logistic_baseline, majority_probabilities, predict_logistic
from app.lstm_features import FeatureScaler, candle_features, make_sequence_partition

# Optional PyTorch import
try:
    from app.lstm_neural import (
        TORCH_AVAILABLE,
        LSTMConfig,
        train_lstm_classifier,
        predict_lstm_probabilities,
        save_lstm_weights,
    )
except ImportError:
    TORCH_AVAILABLE = False


def _json_safe(value):
    """Convert non-finite numeric results to JSON null, recursively."""
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, numbers.Real):
        return value if math.isfinite(float(value)) else None
    return value


def _write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(_json_safe(value), indent=2, allow_nan=False))
    temporary.replace(path)


def _fingerprint_frame(frame: pd.DataFrame) -> str:
    selected = frame.loc[:, ["open", "high", "low", "close", "volume"]]
    payload = selected.to_csv(index=True, date_format="%Y-%m-%dT%H:%M:%S.%f").encode()
    return hashlib.sha256(payload).hexdigest()


def _write_failure_manifest(run_dir: Path, args, error: str, commit: str, data_sha256: str | None) -> None:
    """Write failure manifest before exiting on error."""
    try:
        git_status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        dirty = bool(git_status.strip())
    except subprocess.CalledProcessError:
        dirty = True

    manifest = {
        "run_id": run_dir.name.split("_")[0],
        "study_id": "LSTM-BASELINE-001",
        "evaluation_mode": "validation-only",
        "run_class": "diagnostic",
        "utc_start": datetime.now(timezone.utc).isoformat(),
        "command": shlex.join(sys.argv),
        "git_commit": commit,
        "dirty_worktree": dirty,
        "database": str(Path(args.db).resolve()),
        "ticker": args.ticker.upper(),
        "period": args.period,
        "data_sha256": data_sha256,
        "train_bars": args.train_bars,
        "validation_bars": args.validation_bars,
        "sequence_length": args.sequence_length,
        "horizon": args.horizon,
        "threshold": args.threshold,
        "cost_rate": args.cost_rate,
        "lstm_config": {
            "hidden_size": args.hidden_size,
            "num_layers": args.num_layers,
            "dropout": args.dropout,
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
            "epochs": args.epochs,
            "seed": args.seed,
        },
        "exit_status": 1,
        "failure_reason": error,
    }
    _write_json(run_dir / "manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/trader.db")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", default="15m")
    parser.add_argument("--train-bars", type=int, default=500)
    parser.add_argument("--validation-bars", type=int, required=True)
    parser.add_argument("--sequence-length", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--cost-rate", type=float, default=0.001)
    parser.add_argument("--threshold", type=float, default=0.003)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--artifacts-dir", default="artifacts/runs/lstm_neural")
    args = parser.parse_args()

    # Create run directory with microsecond timestamp
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        commit = "unknown"

    run_dir = Path(args.artifacts_dir) / f"{run_id}_LSTM-NEURAL_{commit}_{args.ticker.upper()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_failure_manifest(run_dir, args, "run_incomplete", commit, None)

    # Check PyTorch availability first
    if not TORCH_AVAILABLE:
        error = "PyTorch is not available. Install with: pip install torch"
        _write_failure_manifest(run_dir, args, error, commit, None)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Validation constraints
    if not (args.train_bars > 0 and args.validation_bars > 0):
        error = "--train-bars and --validation-bars must be positive"
        _write_failure_manifest(run_dir, args, error, commit, None)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Load candles (train + validation only) with read-only mode
    limit = args.train_bars + args.validation_bars
    try:
        with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as connection:
            frame = pd.read_sql_query(
                "SELECT begin AS timestamp, open, high, low, close, volume "
                "FROM candles WHERE ticker = ? AND period = ? ORDER BY begin LIMIT ?",
                connection, params=(args.ticker.upper(), args.period, limit), parse_dates=["timestamp"],
            ).set_index("timestamp")
    except Exception as e:
        error = f"Failed to load candles: {e}"
        _write_failure_manifest(run_dir, args, error, commit, None)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if frame.empty:
        error = "no candles found"
        _write_failure_manifest(run_dir, args, error, commit, None)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if len(frame) < limit:
        error = f"insufficient data: requested {limit} candles, got {len(frame)}"
        _write_failure_manifest(run_dir, args, error, commit, None)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Fingerprint data
    data_sha256 = _fingerprint_frame(frame)

    log_path = run_dir / "run.log"
    log_file = log_path.open("w")

    def log(msg: str) -> None:
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    log(f"Run ID: {run_id}")
    log(f"Ticker: {args.ticker}, Period: {args.period}")
    log(f"Train bars: {args.train_bars}, Validation bars: {args.validation_bars}")
    log(f"Sequence length: {args.sequence_length}, Horizon: {args.horizon}")
    log(f"Threshold: {args.threshold}, Cost rate: {args.cost_rate}")
    log(f"LSTM config: hidden={args.hidden_size}, layers={args.num_layers}, dropout={args.dropout}")
    log(f"Training: lr={args.learning_rate}, batch={args.batch_size}, epochs={args.epochs}, seed={args.seed}")
    log(f"Loaded {len(frame)} candles")
    log(f"Data SHA256: {data_sha256}")
    log(f"Storage timezone: UTC-naive (see research/protocol.md)")

    # Compute features and fit scaler on train prefix only
    try:
        raw_features = candle_features(frame)
        train_end = args.train_bars
        scaler = FeatureScaler.fit(raw_features.iloc[:train_end])
        log("Fitted scaler on training prefix only")
    except Exception as e:
        error = f"Feature computation failed: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Build train partition
    try:
        train_partition = make_sequence_partition(
            frame,
            feature_start=0,
            decision_start=0,
            decision_end=train_end,
            sequence_length=args.sequence_length,
            horizon=args.horizon,
            threshold=args.threshold,
            cost_rate=args.cost_rate,
            scaler=scaler,
        )
        log(f"Train partition: {len(train_partition.X)} samples")
    except Exception as e:
        error = f"Failed to create train partition: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Build validation partition
    try:
        val_partition = make_sequence_partition(
            frame,
            feature_start=0,
            decision_start=train_end,
            decision_end=len(frame),
            sequence_length=args.sequence_length,
            horizon=args.horizon,
            threshold=args.threshold,
            cost_rate=args.cost_rate,
            scaler=scaler,
        )
        log(f"Validation partition: {len(val_partition.X)} samples")
    except Exception as e:
        error = f"Failed to create validation partition: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Check class balance
    train_pos_rate = float(np.mean(train_partition.y))
    val_pos_rate = float(np.mean(val_partition.y))
    log(f"Train positive rate: {train_pos_rate:.4f}")
    log(f"Validation positive rate: {val_pos_rate:.4f}")

    if not (0 < train_pos_rate < 1 and 0 < val_pos_rate < 1):
        error = "Training or validation set has only one class"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Train logistic baseline
    log("\n=== Logistic Baseline ===")
    try:
        log_weights, log_bias = fit_logistic_baseline(
            train_partition.X, train_partition.y, learning_rate=0.05, epochs=300, l2=1.0
        )
        log_train_probs = predict_logistic(train_partition.X, log_weights, log_bias)
        log_val_probs = predict_logistic(val_partition.X, log_weights, log_bias)

        log_train_metrics = classification_metrics(train_partition.y, log_train_probs)
        log_val_metrics = classification_metrics(val_partition.y, log_val_probs)

        log(f"Logistic train accuracy: {log_train_metrics.accuracy:.4f}, log_loss: {log_train_metrics.log_loss:.4f}")
        log(f"Logistic val accuracy: {log_val_metrics.accuracy:.4f}, log_loss: {log_val_metrics.log_loss:.4f}")
    except Exception as e:
        error = f"Logistic baseline failed: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Training prevalence baseline
    log("\n=== Training Prevalence Baseline ===")
    try:
        prev_train_probs = majority_probabilities(train_partition.y, len(train_partition.y))
        prev_val_probs = majority_probabilities(train_partition.y, len(val_partition.y))

        prev_train_metrics = classification_metrics(train_partition.y, prev_train_probs)
        prev_val_metrics = classification_metrics(val_partition.y, prev_val_probs)

        log(f"Prevalence train accuracy: {prev_train_metrics.accuracy:.4f}, log_loss: {prev_train_metrics.log_loss:.4f}")
        log(f"Prevalence val accuracy: {prev_val_metrics.accuracy:.4f}, log_loss: {prev_val_metrics.log_loss:.4f}")
    except Exception as e:
        error = f"Prevalence baseline failed: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Train LSTM neural network
    log("\n=== LSTM Neural Network ===")
    lstm_config = LSTMConfig(
        input_size=10,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        epochs=args.epochs,
        seed=args.seed,
    )

    try:
        lstm_model, history = train_lstm_classifier(
            train_partition.X, train_partition.y,
            val_partition.X, val_partition.y,
            lstm_config,
        )
        log(f"LSTM training complete: {args.epochs} epochs")
        log(f"Final train loss: {history['train_loss'][-1]:.4f}, accuracy: {history['train_accuracy'][-1]:.4f}")
        log(f"Final val loss: {history['val_loss'][-1]:.4f}, accuracy: {history['val_accuracy'][-1]:.4f}")
    except Exception as e:
        error = f"LSTM training failed: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Generate LSTM predictions
    try:
        lstm_train_probs = predict_lstm_probabilities(lstm_model, train_partition.X)
        lstm_val_probs = predict_lstm_probabilities(lstm_model, val_partition.X)

        lstm_train_metrics = classification_metrics(train_partition.y, lstm_train_probs)
        lstm_val_metrics = classification_metrics(val_partition.y, lstm_val_probs)

        log(f"LSTM train accuracy: {lstm_train_metrics.accuracy:.4f}, log_loss: {lstm_train_metrics.log_loss:.4f}")
        log(f"LSTM val accuracy: {lstm_val_metrics.accuracy:.4f}, log_loss: {lstm_val_metrics.log_loss:.4f}")
    except Exception as e:
        error = f"LSTM prediction failed: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Write prediction ledger with timestamps
    try:
        train_ledger = pd.DataFrame({
            "decision_timestamp": train_partition.decision_timestamps,
            "outcome_timestamp": train_partition.outcome_timestamps,
            "label": train_partition.y,
            "logistic_prob": log_train_probs,
            "prevalence_prob": prev_train_probs,
            "lstm_prob": lstm_train_probs,
        })
        train_ledger.to_csv(run_dir / "train_predictions.csv", index=False)
        log("Wrote train_predictions.csv")

        val_ledger = pd.DataFrame({
            "decision_timestamp": val_partition.decision_timestamps,
            "outcome_timestamp": val_partition.outcome_timestamps,
            "label": val_partition.y,
            "logistic_prob": log_val_probs,
            "prevalence_prob": prev_val_probs,
            "lstm_prob": lstm_val_probs,
        })
        val_ledger.to_csv(run_dir / "validation_predictions.csv", index=False)
        log("Wrote validation_predictions.csv")
    except Exception as e:
        error = f"Failed to write prediction ledger: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Save LSTM weights
    weights_path = run_dir / "lstm_weights.pt"
    try:
        save_lstm_weights(lstm_model, str(weights_path))
        log(f"Saved LSTM weights to {weights_path.name}")
        log("WARNING: LSTM weights are NOT compatible with logistic baseline loader")
    except Exception as e:
        error = f"Failed to save LSTM weights: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Save scaler metadata
    try:
        scaler_metadata = {
            "mean": scaler.mean.tolist(),
            "scale": scaler.scale.tolist(),
            "fitted_on": "train_prefix_only",
            "feature_columns": list(raw_features.columns),
        }
        _write_json(run_dir / "scaler.json", scaler_metadata)
        log("Wrote scaler.json")
    except Exception as e:
        error = f"Failed to save scaler metadata: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Write metrics
    try:
        metrics = {
            "train_samples": len(train_partition.y),
            "validation_samples": len(val_partition.y),
            "train_positive_rate": train_pos_rate,
            "validation_positive_rate": val_pos_rate,
            "logistic": {
                "train": {
                    "accuracy": log_train_metrics.accuracy,
                    "balanced_accuracy": log_train_metrics.balanced_accuracy,
                    "log_loss": log_train_metrics.log_loss,
                    "precision": log_train_metrics.precision,
                    "recall": log_train_metrics.recall,
                    "f1": log_train_metrics.f1,
                    "brier_score": log_train_metrics.brier_score,
                },
                "validation": {
                    "accuracy": log_val_metrics.accuracy,
                    "balanced_accuracy": log_val_metrics.balanced_accuracy,
                    "log_loss": log_val_metrics.log_loss,
                    "precision": log_val_metrics.precision,
                    "recall": log_val_metrics.recall,
                    "f1": log_val_metrics.f1,
                    "brier_score": log_val_metrics.brier_score,
                },
            },
            "prevalence": {
                "train": {
                    "accuracy": prev_train_metrics.accuracy,
                    "balanced_accuracy": prev_train_metrics.balanced_accuracy,
                    "log_loss": prev_train_metrics.log_loss,
                    "precision": prev_train_metrics.precision,
                    "recall": prev_train_metrics.recall,
                    "f1": prev_train_metrics.f1,
                    "brier_score": prev_train_metrics.brier_score,
                },
                "validation": {
                    "accuracy": prev_val_metrics.accuracy,
                    "balanced_accuracy": prev_val_metrics.balanced_accuracy,
                    "log_loss": prev_val_metrics.log_loss,
                    "precision": prev_val_metrics.precision,
                    "recall": prev_val_metrics.recall,
                    "f1": prev_val_metrics.f1,
                    "brier_score": prev_val_metrics.brier_score,
                },
            },
            "lstm": {
                "train": {
                    "accuracy": lstm_train_metrics.accuracy,
                    "balanced_accuracy": lstm_train_metrics.balanced_accuracy,
                    "log_loss": lstm_train_metrics.log_loss,
                    "precision": lstm_train_metrics.precision,
                    "recall": lstm_train_metrics.recall,
                    "f1": lstm_train_metrics.f1,
                    "brier_score": lstm_train_metrics.brier_score,
                },
                "validation": {
                    "accuracy": lstm_val_metrics.accuracy,
                    "balanced_accuracy": lstm_val_metrics.balanced_accuracy,
                    "log_loss": lstm_val_metrics.log_loss,
                    "precision": lstm_val_metrics.precision,
                    "recall": lstm_val_metrics.recall,
                    "f1": lstm_val_metrics.f1,
                    "brier_score": lstm_val_metrics.brier_score,
                },
                "history": history,
            },
        }
        _write_json(run_dir / "metrics.json", metrics)
        log("Wrote metrics.json")
    except Exception as e:
        error = f"Failed to write metrics: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Write checks
    try:
        checks = {
            "scaler_fitted_on_train_only": True,
            "train_samples_positive": len(train_partition.y) > 0,
            "validation_samples_positive": len(val_partition.y) > 0,
            "both_classes_present_train": 0 < train_pos_rate < 1,
            "both_classes_present_val": 0 < val_pos_rate < 1,
            "all_metrics_finite": all([
                math.isfinite(log_val_metrics.log_loss),
                math.isfinite(prev_val_metrics.log_loss),
                math.isfinite(lstm_val_metrics.log_loss),
            ]),
            "pytorch_available": True,
            "read_only_db": True,
            "exact_row_count": len(frame) == limit,
        }
        _write_json(run_dir / "checks.json", checks)
        if not all(checks.values()):
            raise ValueError("Research sanity checks failed")
        log("Wrote checks.json")
    except Exception as e:
        error = f"Failed to write checks: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        _write_failure_manifest(run_dir, args, error, commit, data_sha256)
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Write success manifest (atomic final step after all artifacts)
    try:
        git_status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        dirty = bool(git_status.strip())
    except subprocess.CalledProcessError:
        dirty = True

    try:
        manifest = {
            "run_id": run_id,
            "study_id": "LSTM-BASELINE-001",
            "evaluation_mode": "validation-only",
            "run_class": "diagnostic",
            "utc_start": datetime.now(timezone.utc).isoformat(),
            "command": shlex.join(sys.argv),
            "git_commit": commit,
            "dirty_worktree": dirty,
            "database": str(Path(args.db).resolve()),
            "ticker": args.ticker.upper(),
            "period": args.period,
            "data_sha256": data_sha256,
            "storage_timezone": "UTC-naive",
            "market_timezone": "Europe/Moscow",
            "train_bars": args.train_bars,
            "validation_bars": args.validation_bars,
            "sequence_length": args.sequence_length,
            "horizon": args.horizon,
            "threshold": args.threshold,
            "cost_rate": args.cost_rate,
            "lstm_config": {
                "hidden_size": args.hidden_size,
                "num_layers": args.num_layers,
                "dropout": args.dropout,
                "learning_rate": args.learning_rate,
                "batch_size": args.batch_size,
                "epochs": args.epochs,
                "seed": args.seed,
            },
            "exit_status": 0,
        }
    except Exception as e:
        error = f"Failed to write manifest: {e}"
        log(f"ERROR: {error}")
        log_file.close()
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    log(f"\n=== Summary ===")
    log(f"Run directory: {run_dir}")
    log(f"Validation log loss comparison:")
    log(f"  Prevalence: {prev_val_metrics.log_loss:.4f}")
    log(f"  Logistic:   {log_val_metrics.log_loss:.4f}")
    log(f"  LSTM:       {lstm_val_metrics.log_loss:.4f}")

    if lstm_val_metrics.log_loss < log_val_metrics.log_loss:
        log("LSTM improves over logistic baseline")
    else:
        log("LSTM does not improve over logistic baseline")

    log("\nThis is a diagnostic research artifact, not a trading approval.")
    log("LSTM weights are not compatible with logistic model loader.")
    log("No promotion, orders, or deployment authorized.")

    log_file.close()
    _write_json(run_dir / "manifest.json", manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
