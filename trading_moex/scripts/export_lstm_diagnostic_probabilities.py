#!/usr/bin/env python3
"""Export full-bar LSTM probabilities from a completed prospective evaluation.

DIAGNOSTIC ONLY: offline causal inference without labels, for analysis only.

Architecture:
- Load frozen enrollment and evaluation manifests (must match hash contracts)
- Validate: parameters, database, timezone, enrollment_manifest_sha256 in evaluation
- Load history (with last 500 bars as training feature context only)
- Load forward (2000 bars, no outcome labels needed for inference)
- Fit scaler on last 500 historical features only
- Prepare inference sequences: 50-bar context, last bar included (no labels)
- Train LSTM on historical train partition (enrollment boundary)
- Infer probabilities on all 2000 forward bars as full window
- Export: per-bar decision timestamps + LSTM probabilities (no outcomes)
- Fail-closed if torch missing: raises ValueError, exit 1

Output artifacts (separate from prospective evaluation):
- manifest.json: diagnostic metadata, enrollment/evaluation hashes, parameter contract
- predictions_ledger.jsonl: full 2000 bars, LSTM probabilities only, decision_ts only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.lstm_features import FeatureScaler, candle_features, make_sequence_partition


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes())


def _git(command: str, *args: str) -> str:
    """Execute git command; return output or 'unknown' on failure."""
    try:
        return subprocess.check_output(
            ["git", command, *args],
            text=True,
            stderr=subprocess.DEVNULL,
            cwd=ROOT
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_json(path: Path, obj) -> None:
    """Write JSON-serializable object, converting non-finite to null."""
    def _safe(v):
        if isinstance(v, dict):
            return {k: _safe(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [_safe(x) for x in v]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            import math
            return v if math.isfinite(v) else None
        return v
    path.write_text(json.dumps(_safe(obj), indent=2, allow_nan=False) + "\n")


def validate_enrollment_manifest(enrollment_dir: Path) -> dict:
    """Load and validate enrollment manifest."""
    manifest_path = enrollment_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("enrollment manifest not found")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "enrolled":
        raise ValueError(f"enrollment status={manifest.get('status')}, expected 'enrolled'")
    if manifest.get("exit_status") != 0:
        raise ValueError(f"enrollment exit_status={manifest.get('exit_status')}, expected 0")
    return manifest


def validate_evaluation_manifest(evaluation_dir: Path) -> dict:
    """Load and validate evaluation manifest."""
    manifest_path = evaluation_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("evaluation manifest not found")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "completed":
        raise ValueError(f"evaluation status={manifest.get('status')}, expected 'completed'")
    if manifest.get("exit_status") != 0:
        raise ValueError(f"evaluation exit_status={manifest.get('exit_status')}, expected 0")
    return manifest


def load_history(enrollment_dir: Path, enrollment_manifest: dict) -> pd.DataFrame:
    """Load and verify history CSV."""
    history_path = enrollment_dir / "history.csv"
    if not history_path.exists():
        raise ValueError("history.csv not found")
    expected_hash = enrollment_manifest.get("history_sha256")
    if not expected_hash:
        raise ValueError("enrollment manifest missing history_sha256")
    actual_hash = sha256_file(history_path)
    if actual_hash != expected_hash:
        raise ValueError(f"history hash mismatch: expected {expected_hash}, got {actual_hash}")
    
    history = pd.read_csv(history_path, parse_dates=["timestamp"]).set_index("timestamp")
    if history.index.tz is not None:
        raise ValueError("history timestamps must be UTC-naive")
    if not history.index.is_monotonic_increasing:
        raise ValueError("history timestamps not monotonic increasing")
    if history.index.has_duplicates:
        raise ValueError("history timestamps duplicated")
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in history.columns:
            raise ValueError(f"history missing column: {col}")
    
    # Validate OHLCV bounds
    values = history[["open", "high", "low", "close", "volume"]].astype(float)
    if not np.isfinite(values).all().all():
        raise ValueError("history contains non-finite OHLCV")
    if (history["low"] > history["high"]).any():
        raise ValueError("invalid history: low > high")
    if ((history["open"] < history["low"]) | (history["open"] > history["high"])).any():
        raise ValueError("invalid history: open outside [low,high]")
    if ((history["close"] < history["low"]) | (history["close"] > history["high"])).any():
        raise ValueError("invalid history: close outside [low,high]")
    
    return history


def load_forward(evaluation_dir: Path, evaluation_manifest: dict) -> pd.DataFrame:
    """Load and verify forward CSV (exactly 2000 bars)."""
    forward_path = evaluation_dir / "forward.csv"
    if not forward_path.exists():
        raise ValueError("forward.csv not found")
    expected_hash = evaluation_manifest.get("forward_sha256")
    if not expected_hash:
        raise ValueError("evaluation manifest missing forward_sha256")
    actual_hash = sha256_file(forward_path)
    if actual_hash != expected_hash:
        raise ValueError(f"forward hash mismatch: expected {expected_hash}, got {actual_hash}")
    
    forward = pd.read_csv(forward_path, parse_dates=["timestamp"]).set_index("timestamp")
    if forward.index.tz is not None:
        raise ValueError("forward timestamps must be UTC-naive")
    if len(forward) != 2000:
        raise ValueError(f"forward has {len(forward)} bars, expected exactly 2000")
    if not forward.index.is_monotonic_increasing:
        raise ValueError("forward timestamps not monotonic increasing")
    if forward.index.has_duplicates:
        raise ValueError("forward timestamps duplicated")
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in forward.columns:
            raise ValueError(f"forward missing column: {col}")
    
    # Validate OHLCV bounds
    values = forward[["open", "high", "low", "close", "volume"]].astype(float)
    if not np.isfinite(values).all().all():
        raise ValueError("forward contains non-finite OHLCV")
    if (forward["low"] > forward["high"]).any():
        raise ValueError("invalid forward: low > high")
    if ((forward["open"] < forward["low"]) | (forward["open"] > forward["high"])).any():
        raise ValueError("invalid forward: open outside [low,high]")
    if ((forward["close"] < forward["low"]) | (forward["close"] > forward["high"])).any():
        raise ValueError("invalid forward: close outside [low,high]")
    
    return forward


def export_diagnostic(
    enrollment_dir: Path,
    evaluation_dir: Path,
    output_dir: Path,
) -> int:
    """Main export function."""
    output_dir.mkdir(parents=True, exist_ok=False)
    now = datetime.now(timezone.utc)
    manifest = {
        "study_id": "LSTM-BASELINE-DIAGNOSTIC-FULL-BAR",
        "diagnostic_only": True,
        "inference_mode": "full_2000_bars_no_outcome_labels",
        "started_at_utc": now.isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--porcelain"),
        "python_version": sys.version,
    }

    try:
        # 1. Load and validate manifests
        enrollment_manifest = validate_enrollment_manifest(enrollment_dir)
        evaluation_manifest = validate_evaluation_manifest(evaluation_dir)
        manifest["enrollment_manifest_sha256"] = sha256_file(enrollment_dir / "manifest.json")
        manifest["evaluation_manifest_sha256"] = sha256_file(evaluation_dir / "manifest.json")

        # 2. Validate contract compatibility
        if enrollment_manifest.get("parameters") != evaluation_manifest.get("parameters"):
            raise ValueError("parameters mismatch between enrollment and evaluation")
        if enrollment_manifest.get("database_identifier") != evaluation_manifest.get("database_identifier"):
            raise ValueError("database_identifier mismatch between enrollment and evaluation")
        if enrollment_manifest.get("storage_timezone") != evaluation_manifest.get("storage_timezone"):
            raise ValueError("storage_timezone mismatch between enrollment and evaluation")

        # 3. Validate enrollment hash in evaluation
        eval_enrollment_hash = evaluation_manifest.get("enrollment_manifest_sha256")
        if eval_enrollment_hash != manifest["enrollment_manifest_sha256"]:
            raise ValueError(f"evaluation.enrollment_manifest_sha256 mismatch: expected {eval_enrollment_hash}")

        manifest["parameters"] = enrollment_manifest["parameters"]

        # 4. Load history and forward
        history = load_history(enrollment_dir, enrollment_manifest)
        forward = load_forward(evaluation_dir, evaluation_manifest)

        if len(history) < 500:
            raise ValueError(f"history has {len(history)} bars, need at least 500")

        # 5. Verify chronological separation
        if history.index[-1] >= forward.index[0]:
            raise ValueError("history and forward not chronologically separated")

        # 6. Fit scaler on LAST 500 historical features only
        all_candles = pd.concat([history, forward])
        all_features = candle_features(all_candles)
        # Fit only on historical rows. Using all_features.iloc[-500:] would
        # accidentally select forward rows whenever history exceeds 500 bars.
        last_500_features = all_features.iloc[:len(history)].iloc[-500:]
        scaler = FeatureScaler.fit(last_500_features)
        manifest["scaler_mean"] = scaler.mean.tolist()
        manifest["scaler_scale"] = scaler.scale.tolist()

        # 7. Scale all features
        scaled = scaler.transform(all_features)

        # 8. Check for torch availability (fail-closed)
        try:
            import torch
            TORCH_AVAILABLE = True
        except ImportError:
            TORCH_AVAILABLE = False

        if not TORCH_AVAILABLE:
            raise ValueError("PyTorch not available; LSTM inference requires torch")

        # 9. Train LSTM on historical partition (last 500 bars as training data)
        from app.lstm_neural import LSTMConfig, train_lstm_classifier, predict_lstm_probabilities
        
        history_len = len(history)
        forward_len = len(forward)

        parameters = enrollment_manifest["parameters"]
        sequence_length = parameters["sequence_length"]
        calendar = enrollment_manifest.get('dividend_calendar')
        calendar_hash = sha256(json.dumps(calendar, sort_keys=True, separators=(',', ':')).encode())
        if (not calendar or calendar_hash != enrollment_manifest.get('dividend_calendar_sha256')
                or calendar_hash != evaluation_manifest.get('dividend_calendar_sha256')):
            raise ValueError('dividend calendar missing or hash mismatch')
        train = make_sequence_partition(history, feature_start=0, decision_start=history_len-500,
            decision_end=history_len, sequence_length=sequence_length, horizon=parameters['horizon'],
            threshold=parameters['threshold'], cost_rate=parameters['cost_rate'], scaler=scaler,
            excluded_outcome_dates=[event['cutoff_date'] for event in calendar])
        train_X, train_y = train.X, train.y
        manifest.update(dividend_calendar_sha256=calendar_hash, train_samples=len(train_y))

        if len(np.unique(train_y)) != 2:
            raise ValueError("training data single-class")

        config = LSTMConfig(
            input_size=train_X.shape[2],
            **{key: parameters[key] for key in ('hidden_size', 'num_layers', 'dropout',
                                                'learning_rate', 'batch_size', 'epochs', 'seed')},
        )
        model, _ = train_lstm_classifier(train_X, train_y, train_X, train_y, config)

        # 10. Prepare inference windows for ALL 2000 forward bars (no labels)
        # Each forward bar gets a 50-bar context window from history+forward
        # Last bar is included (bar 2000 of forward = bar (history_len+1999) of combined)
        infer_X = []
        infer_ts = []

        for i in range(forward_len):
            # Bar i of forward corresponds to index (history_len + i) in combined frame
            end_idx = history_len + i + 1
            if end_idx - sequence_length < 0:
                continue  # Not enough history for context
            window = scaled.iloc[end_idx - sequence_length:end_idx].values
            if not np.isfinite(window).all():
                raise ValueError(f"forward bar {i} has non-finite features")
            infer_X.append(window)
            infer_ts.append(forward.index[i])

        if len(infer_X) != 2000:
            raise ValueError(f"inferred only {len(infer_X)} bars, expected 2000")

        infer_X = np.asarray(infer_X, dtype=np.float32)
        probabilities = predict_lstm_probabilities(model, infer_X)

        if len(probabilities) != 2000:
            raise ValueError(f"got {len(probabilities)} predictions, expected 2000")
        if not np.isfinite(probabilities).all():
            raise ValueError("predictions contain non-finite values")
        if not ((probabilities >= 0) & (probabilities <= 1)).all():
            raise ValueError("predictions outside [0,1]")

        # 11. Write predictions ledger (decision_timestamp only, no outcome labels)
        predictions_path = output_dir / "predictions.jsonl"
        with predictions_path.open("w") as stream:
            for i, (ts, prob) in enumerate(zip(infer_ts, probabilities)):
                row = {
                    "index": i,
                    "partition": "forward",
                    "decision_timestamp": ts.isoformat(),
                    "probability": float(prob),
                }
                stream.write(json.dumps(row) + "\n")

        manifest["predictions_ledger_sha256"] = sha256_file(predictions_path)
        manifest["predictions_sha256"] = manifest["predictions_ledger_sha256"]
        manifest["predictions_count"] = len(probabilities)
        manifest["forward_bars_inferred"] = 2000
        manifest["forward_sha256"] = sha256_file(evaluation_dir / "forward.csv")
        manifest["evaluation_manifest_sha256"] = sha256_file(evaluation_dir / "manifest.json")
        manifest["prediction_schema"] = "partition,decision_timestamp,probability"

        manifest["status"] = "completed"
        manifest["exit_status"] = 0

    except Exception as exc:
        manifest.update(
            status="failed",
            failure_reason=str(exc),
            exit_status=1,
        )

    _write_json(output_dir / "manifest.json", manifest)
    return manifest["exit_status"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enrollment",
        required=True,
        type=Path,
        help="Path to enrollment directory (from enroll_prospective_lstm.py)",
    )
    parser.add_argument(
        "--evaluation",
        required=True,
        type=Path,
        help="Path to evaluation directory (from run_lstm_prospective.py evaluate)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory for diagnostic artifacts (must not exist)",
    )
    args = parser.parse_args()
    return export_diagnostic(args.enrollment, args.evaluation, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
