#!/usr/bin/env python3
"""Minimal offline finite validation-only logistic candidate selection.

Selects one candidate from a predeclared list by minimum validation log_loss,
enforcing strict improvement over training prevalence baseline. Persists candidate
list hash, snapshot fingerprint, diagnostic manifest, and selected model artifact.

No prospective claims, no refit after selection, no test/forward evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import numbers
import shlex
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.lstm_baseline import classification_metrics, fit_logistic_baseline, majority_probabilities, predict_logistic
from app.lstm_features import (
    FeatureScaler,
    candle_features,
    make_sequence_partition,
)
from app.model_artifact import save_model_artifact


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
    path.write_text(json.dumps(_json_safe(value), indent=2, allow_nan=False))


def _fingerprint_frame(frame: pd.DataFrame) -> str:
    """Compute SHA256 of consumed OHLCV rows in CSV order."""
    selected = frame.loc[:, ["open", "high", "low", "close", "volume"]]
    payload = selected.to_csv(index=True, date_format="%Y-%m-%dT%H:%M:%S.%f").encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_candidates_json(candidates: list, max_count: int = 10) -> None:
    """Validate candidate list structure before DB access.

    Raises:
        ValueError: if invalid structure, empty, duplicates, or non-finite l2 values
    """
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    if len(candidates) == 0:
        raise ValueError("candidates list must be nonempty")
    if len(candidates) > max_count:
        raise ValueError(f"candidates list exceeds max_count {max_count}")

    seen_l2 = set()
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {i} must be a dict")
        if "l2" not in candidate:
            raise ValueError(f"candidate {i} missing 'l2' field")
        if set(candidate) != {"l2"}:
            raise ValueError("only l2 may vary between candidates")

        l2 = candidate["l2"]
        if type(l2) not in (int, float):
            raise ValueError(f"candidate {i} l2 must be numeric, got {type(l2).__name__}")
        if not np.isfinite(l2):
            raise ValueError(f"candidate {i} l2 must be finite, got {l2}")
        if l2 <= 0:
            raise ValueError(f"candidate {i} l2 must be positive, got {l2}")

        if l2 in seen_l2:
            raise ValueError(f"candidate {i} has duplicate l2 value {l2}")
        seen_l2.add(l2)


def _hash_candidates(candidates: list) -> str:
    """Compute SHA256 of candidates JSON payload."""
    payload = json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _git_value(*command: str, default: str = "unknown") -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database path (ro mode)")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--period", required=True, help="Candle period (e.g., 15m)")
    parser.add_argument("--train-bars", type=int, required=True, help="Training set size")
    parser.add_argument("--validation-bars", type=int, required=True, help="Validation set size")
    parser.add_argument("--sequence-length", type=int, required=True, help="LSTM window length")
    parser.add_argument("--horizon", type=int, required=True, help="Forecast horizon in bars")
    parser.add_argument("--threshold", type=float, required=True, help="Return threshold for label")
    parser.add_argument("--cost-rate", type=float, required=True, help="Round-trip cost estimate")
    parser.add_argument("--candidates", required=True, help="Candidates JSON file path")
    parser.add_argument("--artifacts-dir", required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    # Strict pre-SQL validation
    try:
        if args.train_bars <= 0:
            raise ValueError("train-bars must be positive")
        if args.validation_bars <= 0:
            raise ValueError("validation-bars must be positive")
        if args.sequence_length <= 0:
            raise ValueError("sequence-length must be positive")
        if args.horizon <= 0:
            raise ValueError("horizon must be positive")
        if not math.isfinite(args.threshold):
            raise ValueError("threshold must be finite")
        if not math.isfinite(args.cost_rate):
            raise ValueError("cost-rate must be finite")
        if args.cost_rate < 0:
            raise ValueError("cost-rate must be nonnegative")

        # Load and validate candidates JSON
        candidates_path = Path(args.candidates)
        if not candidates_path.exists():
            raise ValueError(f"candidates file not found: {candidates_path}")

        try:
            candidates_payload = candidates_path.read_text()
            candidates = json.loads(candidates_payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"candidates JSON is malformed: {e}")

        _validate_candidates_json(candidates)

    except (ValueError, OSError) as e:
        print(json.dumps({"error": str(e), "exit_status": 1}, indent=2), file=sys.stderr)
        return 1

    # Load candles from SQLite (read-only, ORDER BY begin, LIMIT train+validation only)
    try:
        total_rows = args.train_bars + args.validation_bars
        with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as connection:
            frame = pd.read_sql_query(
                "SELECT begin AS timestamp, open, high, low, close, volume "
                "FROM candles WHERE ticker = ? AND period = ? ORDER BY begin LIMIT ?",
                connection, params=(args.ticker.upper(), args.period, total_rows),
                parse_dates=["timestamp"],
            ).set_index("timestamp")
    except (sqlite3.Error, pd.errors.DatabaseError, ValueError, OSError) as e:
        print(json.dumps({"error": f"database error: {e}", "exit_status": 1}, indent=2), file=sys.stderr)
        return 1

    if frame.empty:
        print(json.dumps({"error": "no candles found", "exit_status": 1}, indent=2), file=sys.stderr)
        return 1

    if len(frame) < total_rows:
        print(json.dumps({
            "error": f"insufficient candles: need {total_rows}, got {len(frame)}",
            "exit_status": 1
        }, indent=2), file=sys.stderr)
        return 1

    try:
        return _run_selection(frame, args, candidates, candidates_path)
    except OSError as e:
        print(json.dumps({"error": f"artifact write error: {e}", "exit_status": 1}), file=sys.stderr)
        return 1


def _run_selection(frame: pd.DataFrame, args: argparse.Namespace, candidates: list, candidates_path: Path) -> int:  # pylint: disable=too-many-locals
    """Run candidate selection and persist results."""
    started_at = datetime.now(timezone.utc).isoformat()
    loaded_rows = len(frame)
    optimizer = {"learning_rate": 0.05, "epochs": 300}

    # Split into train/validation
    train_end = args.train_bars
    validation_end = train_end + args.validation_bars
    frame_consumed = frame.iloc[:validation_end]

    # Create output directory with run_id
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_lstm_selection")
    output = Path(args.artifacts_dir) / run_id

    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as e:
        print(json.dumps({"error": f"artifact directory error: {e}", "exit_status": 1}), file=sys.stderr)
        return 1

    early_error = None

    # Preserve invalid-input diagnostics before attempting any model fit.
    try:
        raw = candle_features(frame_consumed)
        scaler_rows = raw.iloc[0:train_end]
        scaler = FeatureScaler.fit(scaler_rows)
    except (ValueError, TypeError) as e:
        early_error = f"feature/scaler preparation failed: {e}"

    # Build train partition
    if not early_error:
        try:
            train_partition = make_sequence_partition(
                frame_consumed, feature_start=0,
                decision_start=0, decision_end=train_end,
                sequence_length=args.sequence_length, horizon=args.horizon,
                threshold=args.threshold, cost_rate=args.cost_rate, scaler=scaler,
            )
        except ValueError as e:
            early_error = f"train partition build failed: {e}"

    # Build validation partition
    if not early_error:
        try:
            validation_partition = make_sequence_partition(
                frame_consumed, feature_start=0,
                decision_start=train_end, decision_end=validation_end,
                sequence_length=args.sequence_length, horizon=args.horizon,
                threshold=args.threshold, cost_rate=args.cost_rate, scaler=scaler,
            )
        except ValueError as e:
            early_error = f"validation partition build failed: {e}"

    # Verify both classes present in train and validation
    if not early_error:
        train_classes = set(train_partition.y)
        validation_classes = set(validation_partition.y)

        if len(train_classes) < 2:
            early_error = f"train partition missing class 0 or 1: classes={sorted(train_classes)}"
        elif len(validation_classes) < 2:
            early_error = f"validation partition missing class 0 or 1: classes={sorted(validation_classes)}"

    # Evaluate candidates and compute baseline (or capture error)
    candidate_scores = []
    fitted_models = {}
    baseline_log_loss = None

    if not early_error:
        for idx, candidate in enumerate(candidates):
            l2 = float(candidate["l2"])
            try:
                weights, bias = fit_logistic_baseline(
                    train_partition.X, train_partition.y, l2=l2, **optimizer
                )
                probabilities = predict_logistic(validation_partition.X, weights, bias)
                metrics = classification_metrics(validation_partition.y, probabilities)
                fitted_models[idx] = (weights.copy(), bias)

                if not np.isfinite(metrics.log_loss):
                    candidate_scores.append({
                        "candidate_index": idx,
                        "l2": l2,
                        "validation_log_loss": None,
                        "status": "invalid_metrics"
                    })
                    continue

                candidate_scores.append({
                    "candidate_index": idx,
                    "l2": l2,
                    "validation_log_loss": float(metrics.log_loss),
                    "status": "evaluated"
                })
            except Exception as e:
                candidate_scores.append({
                    "candidate_index": idx,
                    "l2": l2,
                    "validation_log_loss": None,
                    "status": f"fit_error: {e}"
                })

        # Compute baseline: majority class predictor on train, evaluate on validation
        try:
            baseline_probabilities = majority_probabilities(train_partition.y, len(validation_partition.y))
            baseline_metrics = classification_metrics(validation_partition.y, baseline_probabilities)
            baseline_log_loss = float(baseline_metrics.log_loss) if np.isfinite(baseline_metrics.log_loss) else None
        except Exception as e:
            early_error = f"baseline evaluation failed: {e}"

    # Select minimum validation log_loss with strict improvement over baseline
    winner_idx = None
    winner_score = None

    if not early_error:
        for score in candidate_scores:
            if score["status"] != "evaluated":
                continue
            if score["validation_log_loss"] is None:
                continue

            # Require strict improvement over baseline
            if baseline_log_loss is not None and not (score["validation_log_loss"] < baseline_log_loss):
                continue

            if winner_idx is None or score["validation_log_loss"] < winner_score["validation_log_loss"]:
                winner_idx = score["candidate_index"]
                winner_score = score

    # Prepare manifest
    git_status = _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "status", "--porcelain")
    manifest = {
        "run_id": run_id,
        "study_id": "LSTM-BASELINE-001",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": shlex.join(sys.argv),
        "argv": list(sys.argv),
        "git_commit": _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"),
        "git_status": git_status,
        "dirty_worktree": None if git_status == "unknown" else bool(git_status),
        "ticker": args.ticker.upper(),
        "period": args.period,
        "loaded_rows": loaded_rows,
        "consumed_rows": len(frame_consumed),
        "rows": len(frame_consumed),
        "date_start": frame_consumed.index[0].isoformat(),
        "date_end": frame_consumed.index[-1].isoformat(),
        "storage_timezone": "UTC-naive",
        "market_timezone": "Europe/Moscow",
        "used_data_range": {
            "start": frame_consumed.index[0].isoformat(),
            "end": frame_consumed.index[-1].isoformat()
        },
        "resolved_boundaries": {
            "train": {
                "row_start": 0,
                "row_end": train_end,
                "timestamp_start": frame_consumed.index[0].isoformat(),
                "timestamp_end": frame_consumed.index[train_end - 1].isoformat(),
            },
            "validation": {
                "row_start": train_end,
                "row_end": validation_end,
                "timestamp_start": frame_consumed.index[train_end].isoformat(),
                "timestamp_end": frame_consumed.index[validation_end - 1].isoformat(),
            }
        },
        "boundary_convention": "row_end exclusive; timestamp_end inclusive",
        "evaluation_mode": "validation-only",
        "run_class": "diagnostic",
        "started_at_utc": started_at,
        "python_version": sys.version,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "data_source": {
            "database": str(Path(args.db).resolve()),
            "table": "candles",
            "columns": ["begin", "open", "high", "low", "close", "volume"]
        },
        "parameters": {
            "optimizer": optimizer,
            "train_bars": args.train_bars,
            "validation_bars": args.validation_bars,
            "sequence_length": args.sequence_length,
            "horizon": args.horizon,
            "threshold": args.threshold,
            "cost_rate": args.cost_rate,
        },
        "candidates": {
            "file_path": str(candidates_path),
            "count": len(candidates),
            "sha256": _hash_candidates(candidates),
        },
        "baseline": {
            "prevalence": float(np.mean(train_partition.y)) if not early_error else None,
            "validation_log_loss": baseline_log_loss,
        },
        "selection_rule": {
            "metric": "validation_log_loss",
            "direction": "minimize",
            "baseline": "train_prevalence",
            "strict_improvement": True,
            "tie_break": "first_declared",
        },
        "selection": {
            "winner_index": winner_idx if not early_error else None,
            "winner_l2": float(candidates[winner_idx]["l2"]) if winner_idx is not None else None,
            "status": "failed" if early_error else ("selected" if winner_idx is not None else "rejected"),
        },
        "exit_status": 1 if early_error else 0,
        "failed_checks": [],
    }

    fingerprint = _fingerprint_frame(frame_consumed)

    # Write artifacts if early failure occurred
    if early_error:
        manifest["failed_checks"] = ["selection_preconditions"]
        manifest["candidates"]["artifact_path"] = "candidates.json"
        _write_json(output / "candidates.json", candidates)
        _write_json(output / "error.json", {"error": early_error})
        _write_json(output / "manifest.json", {
            **manifest,
            "data_sha256": fingerprint,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        _write_json(output / "checks.json", {"selection_preconditions": False})
        _write_json(output / "metrics.json", {
            "baseline": {"validation_log_loss": baseline_log_loss},
            "candidates": candidate_scores,
            "selection": manifest["selection"],
            "winner": None,
        })
        (output / "run.log").write_text(
            f"validation-only candidate selection\nrun_id={run_id}\n"
            f"command={shlex.join(sys.argv)}\nselection_status={manifest['selection']['status']}\n"
        )
        _write_json(output / "candidate_scores.json", candidate_scores)
        return 1

    # Success path: compute checks and finalize artifacts
    expected_mean = scaler_rows.mean().fillna(0).to_numpy()
    expected_scale = scaler_rows.std(ddof=0).to_numpy()
    expected_scale = np.where(np.isfinite(expected_scale) & (expected_scale > 0), expected_scale, 1.0)
    checks = {
        "train_only_scaler": bool(
            np.allclose(scaler.mean, expected_mean)
            and np.allclose(scaler.scale, expected_scale)
        ),
        "finite_baseline": baseline_log_loss is not None,
        "all_candidates_evaluated": all(score["status"] == "evaluated" for score in candidate_scores),
        "validation_only_data": loaded_rows == args.train_bars + args.validation_bars,
        "finite_candidate_scores": all(
            score["status"] != "evaluated" or np.isfinite(score["validation_log_loss"])
            for score in candidate_scores
        ),
        "selection_status_recorded": winner_idx is None or winner_idx in range(len(candidates)),
    }
    _write_json(output / "candidates.json", candidates)
    manifest["candidates"]["artifact_path"] = "candidates.json"
    manifest["failed_checks"] = [name for name, passed in checks.items() if not passed]
    manifest["exit_status"] = 1 if manifest["failed_checks"] else 0
    if manifest["failed_checks"]:
        winner_idx = None
        manifest["selection"] = {"status": "failed", "winner_index": None, "winner_l2": None}
    _write_json(output / "checks.json", checks)
    winner_metrics = next(
        (score for score in candidate_scores if score["candidate_index"] == winner_idx),
        None,
    )
    _write_json(output / "metrics.json", {
        "baseline": {"validation_log_loss": baseline_log_loss},
        "candidates": candidate_scores,
        "selection": manifest["selection"],
        "winner": winner_metrics,
    })
    (output / "run.log").write_text(
        f"validation-only candidate selection\nrun_id={run_id}\n"
        f"command={shlex.join(sys.argv)}\nselection_status={manifest['selection']['status']}\n"
    )

    # Write candidate scores
    _write_json(output / "candidate_scores.json", candidate_scores)
    _write_json(output / "manifest.json", {
        **manifest, "data_sha256": fingerprint,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    })

    # If winner selected, save model artifact and predictions ledger
    if winner_idx is not None:
        winner_l2 = float(candidates[winner_idx]["l2"])
        try:
            weights, bias = fitted_models[winner_idx]
            model_artifact_path, model_artifact_sha256 = save_model_artifact(
                output, weights, bias, scaler, sequence_length=args.sequence_length
            )
            manifest["model_artifact"] = {
                "path": str(model_artifact_path.relative_to(output)),
                "sha256": model_artifact_sha256,
                "schema_version": "1.0",
                "l2": winner_l2,
            }

            # Write predictions ledger for exact replay validation
            probabilities = predict_logistic(validation_partition.X, weights, bias)
            predictions_file = output / "predictions.jsonl"
            with predictions_file.open("x") as f:
                for prob, label, decision_ts, outcome_ts in zip(
                    probabilities, validation_partition.y,
                    validation_partition.decision_timestamps,
                    validation_partition.outcome_timestamps, strict=True,
                ):

                    record = {
                        "partition": "validation",
                        "decision_timestamp": decision_ts.isoformat(),
                        "outcome_timestamp": outcome_ts.isoformat(),
                        "label": float(label),
                        "probability": float(prob),
                    }
                    f.write(json.dumps(record, allow_nan=False) + "\n")

            _write_json(output / "manifest.json", {
                **manifest,
                "data_sha256": fingerprint,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            _write_json(output / "error.json", {"error": f"model artifact save failed: {e}"})
            manifest["exit_status"] = 1
            manifest["failed_checks"].append("model_artifact_saved")
            manifest["selection"]["status"] = "failed"
            winner_idx = None
            manifest["selection"]["winner_index"] = None
            manifest["selection"]["winner_l2"] = None
            checks["model_artifact_saved"] = False
            _write_json(output / "checks.json", checks)
            _write_json(output / "metrics.json", {
                "baseline": {"validation_log_loss": baseline_log_loss},
                "candidates": candidate_scores,
                "selection": manifest["selection"],
                "winner": None,
            })
            (output / "run.log").write_text(
                f"validation-only candidate selection\nrun_id={run_id}\n"
                f"command={shlex.join(sys.argv)}\nselection_status=failed\n"
            )
            _write_json(output / "manifest.json", {
                **manifest, "data_sha256": fingerprint,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            })

    # Output summary to stdout
    summary = {
        "run_id": run_id,
        "artifact_dir": str(output),
        "selection_status": manifest["selection"]["status"],
        "winner_index": winner_idx,
        "winner_l2": float(candidates[winner_idx]["l2"]) if winner_idx is not None else None,
        "baseline_log_loss": baseline_log_loss,
        "candidate_count": len(candidates),
        "exit_status": manifest["exit_status"],
    }
    print(json.dumps(_json_safe(summary), indent=2, allow_nan=False))
    return manifest["exit_status"]


if __name__ == "__main__":
    raise SystemExit(main())
