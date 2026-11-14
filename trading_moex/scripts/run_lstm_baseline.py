#!/usr/bin/env python3
"""Run the offline chronological logistic baseline on SQLite candles."""

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

from app.lstm_baseline import classification_metrics, fit_logistic_baseline, majority_probabilities, predict_logistic
from app.lstm_features import (
    FeatureScaler,
    candle_features,
    chronological_boundaries,
    make_sequence_partition,
    walk_forward_splits,
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
    selected = frame.loc[:, ["open", "high", "low", "close", "volume"]]
    payload = selected.to_csv(index=True, date_format="%Y-%m-%dT%H:%M:%S.%f").encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/trader.db")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", default="1day")
    parser.add_argument("--train-bars", type=int, default=500)
    parser.add_argument("--test-bars", type=int, default=None)
    parser.add_argument("--sequence-length", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--cost-rate", type=float, default=0.001)
    parser.add_argument("--threshold", type=float, default=0.003)
    parser.add_argument("--validation-bars", type=int, default=0)
    parser.add_argument("--forward-bars", type=int, default=0)
    parser.add_argument("--validation-only", action="store_true",
                        help="Validation-only mode: requires --validation-bars > 0, consumes only train+validation data")
    parser.add_argument("--artifacts-dir", default="artifacts/runs/lstm_baseline")
    args = parser.parse_args()

    # Validate validation-only constraints before SQL
    if args.validation_only:
        if not (args.train_bars > 0):
            raise SystemExit("--validation-only requires --train-bars > 0")
        if not (args.validation_bars > 0):
            raise SystemExit("--validation-only requires --validation-bars > 0")
        if args.test_bars is not None:
            raise SystemExit("--validation-only disallows --test-bars")
        if args.forward_bars != 0 and args.forward_bars is not None:
            raise SystemExit("--validation-only disallows --forward-bars")
        # Direct entry validation
        return _validate_and_run_validation_only(args)

    # Restore default for test_bars for other modes
    if args.test_bars is None:
        args.test_bars = 100

    with sqlite3.connect(args.db) as connection:
        frame = pd.read_sql_query(
            "SELECT begin AS timestamp, open, high, low, close, volume "
            "FROM candles WHERE ticker = ? AND period = ? ORDER BY begin",
            connection, params=(args.ticker.upper(), args.period), parse_dates=["timestamp"],
        ).set_index("timestamp")

    if frame.empty:
        raise SystemExit("no candles found")

    if args.validation_bars or args.forward_bars:
        return run_partitioned(frame, args)

    splits = walk_forward_splits(
        frame, train_bars=args.train_bars, test_bars=args.test_bars,
        sequence_length=args.sequence_length, horizon=args.horizon,
        threshold=args.threshold, cost_rate=args.cost_rate,
    )
    if not splits:
        raise SystemExit("no usable walk-forward folds; check data and parameters")
    rows = []
    for number, split in enumerate(splits, 1):
        weights, bias = fit_logistic_baseline(split.train_x, split.train_y)
        model = classification_metrics(split.test_y, predict_logistic(split.test_x, weights, bias))
        majority = classification_metrics(split.test_y, majority_probabilities(split.train_y, len(split.test_y)))
        rows.append({"fold": number, "train_end": split.train_end, "test_end": split.test_end,
                     "decision_start": split.test_decision_timestamps[0].isoformat(),
                     "decision_end": split.test_decision_timestamps[-1].isoformat(),
                     "outcome_start": split.test_timestamps[0].isoformat(),
                     "outcome_end": split.test_timestamps[-1].isoformat(),
                     "model": model.__dict__, "majority": majority.__dict__})
    print(json.dumps(_json_safe({"ticker": args.ticker.upper(), "period": args.period, "folds": rows}),
                     indent=2, allow_nan=False))
    return 0


def _git_value(*command: str, default: str = "unknown") -> str:
    try:
        # An empty successful command is meaningful, notably for clean status.
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return default


def _validate_and_run_validation_only(args: argparse.Namespace) -> int:
    """Pre-query validation for validation-only mode, then load and run."""
    try:
        with sqlite3.connect(args.db) as connection:
            total_rows = args.train_bars + args.validation_bars
            frame = pd.read_sql_query(
                "SELECT begin AS timestamp, open, high, low, close, volume "
                "FROM candles WHERE ticker = ? AND period = ? ORDER BY begin LIMIT ?",
                connection, params=(args.ticker.upper(), args.period, total_rows),
                parse_dates=["timestamp"],
            ).set_index("timestamp")
    except sqlite3.Error as e:
        raise SystemExit(f"database error: {e}")

    if frame.empty:
        raise SystemExit("no candles found")
    if len(frame) < args.train_bars + args.validation_bars:
        raise SystemExit(
            f"insufficient candles: need {args.train_bars + args.validation_bars}, "
            f"got {len(frame)}"
        )

    return run_validation_only(frame, args)


def run_partitioned(frame: pd.DataFrame, args: argparse.Namespace) -> int:
    started_at = datetime.now(timezone.utc).isoformat()
    available_rows = len(frame)
    boundaries = chronological_boundaries(
        frame, train_bars=args.train_bars, validation_bars=args.validation_bars,
        test_bars=args.test_bars, forward_bars=args.forward_bars,
    )
    frame = frame.iloc[:boundaries.forward[1]]
    raw = candle_features(frame)
    scaler_rows = raw.iloc[boundaries.train[0]:boundaries.train[1]]
    scaler = FeatureScaler.fit(scaler_rows)
    train_partition = make_sequence_partition(
        frame, feature_start=boundaries.train[0],
        decision_start=boundaries.train[0], decision_end=boundaries.train[1],
        sequence_length=args.sequence_length, horizon=args.horizon,
        threshold=args.threshold, cost_rate=args.cost_rate, scaler=scaler,
    )
    partitions = {}
    for name, (start, end) in (
        ("validation", boundaries.validation),
        ("test", boundaries.test),
        ("forward", boundaries.forward),
    ):
        partitions[name] = make_sequence_partition(
            frame, feature_start=boundaries.train[0], decision_start=start,
            decision_end=end, sequence_length=args.sequence_length,
            horizon=args.horizon, threshold=args.threshold,
            cost_rate=args.cost_rate, scaler=scaler,
        )
    weights, bias = fit_logistic_baseline(
        train_partition.X, train_partition.y,
    )
    metrics = {}
    for name, partition in partitions.items():
        model = classification_metrics(partition.y, predict_logistic(partition.X, weights, bias))
        majority = classification_metrics(
            partition.y, majority_probabilities(train_partition.y, len(partition.y))
        )
        metrics[name] = {"model": model.__dict__, "majority": majority.__dict__,
                         "samples": len(partition.y),
                         "decision_start": partition.decision_timestamps[0].isoformat(),
                         "decision_end": partition.decision_timestamps[-1].isoformat(),
                         "outcome_start": partition.outcome_timestamps[0].isoformat(),
                         "outcome_end": partition.outcome_timestamps[-1].isoformat()}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_lstm_baseline_diagnostic")
    output = Path(args.artifacts_dir) / run_id
    output.mkdir(parents=True, exist_ok=False)
    git_status = _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "status", "--porcelain")
    manifest = {
        "run_id": run_id, "study_id": "LSTM-BASELINE-001",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
         "command": shlex.join(sys.argv), "argv": list(sys.argv),
         "git_commit": _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"),
         "git_status": git_status,
         "dirty_worktree": None if git_status == "unknown" else bool(git_status),
        "ticker": args.ticker.upper(), "period": args.period,
        "rows": len(frame), "date_start": frame.index[0].isoformat(),
         "date_end": frame.index[-1].isoformat(), "storage_timezone": "UTC-naive",
         "used_data_range": {"start": frame.index[0].isoformat(), "end": frame.index[-1].isoformat()},
         "resolved_boundaries": {
             name: {"row_start": start, "row_end": end,
                    "timestamp_start": frame.index[start].isoformat(),
                    "timestamp_end": frame.index[end - 1].isoformat()}
             for name, (start, end) in (
                 ("train", boundaries.train), ("validation", boundaries.validation),
                 ("test", boundaries.test), ("forward", boundaries.forward),
             )
         },
         "market_timezone": "Europe/Moscow",
         "boundary_convention": "row_end exclusive; timestamp_end inclusive",
         "forward_role": "evaluated historical holdout, not untouched prospective forward",
         "untouched_forward": False,
         "run_class": "diagnostic",
         "started_at_utc": started_at,
         "python_version": sys.version,
         "pandas_version": pd.__version__,
         "numpy_version": np.__version__,
         "data_source": {"database": getattr(args, "db", None), "table": "candles",
                         "columns": ["begin", "open", "high", "low", "close", "volume"]},
         "available_rows": available_rows,
         "ignored_trailing_rows": available_rows - len(frame),
         "prediction_partitions": list(partitions),
         "execution_model": "classification only; no fills, capital, sizing or executable returns",
         "warmup_policy": "drop non-finite feature windows; causal context may precede partition decisions",
         "fingerprint_scope": "used timestamp/open/high/low/close/volume rows in CSV order",
        "parameters": {k: getattr(args, k) for k in (
            "train_bars", "validation_bars", "test_bars", "forward_bars",
            "sequence_length", "horizon", "threshold", "cost_rate",
        )},
    }
    fingerprint = _fingerprint_frame(frame)
    _write_json(output / "metrics.json", metrics)
    ranges = {"train": boundaries.train, "validation": boundaries.validation,
              "test": boundaries.test, "forward": boundaries.forward}
    partition_names = tuple(ranges)
    non_overlapping = all(ranges[left][1] <= ranges[right][0]
                          for left, right in zip(partition_names, partition_names[1:]))
    sample_partitions = {"train": train_partition, **partitions}
    all_samples = [sample for partition in sample_partitions.values()
                   for sample in zip(partition.decision_timestamps, partition.outcome_timestamps)]
    containment = all(
        all(frame.index[start] <= decision <= frame.index[end - 1]
            and frame.index[start] <= outcome <= frame.index[end - 1]
            for decision, outcome in zip(partition.decision_timestamps, partition.outcome_timestamps))
        for name, partition in sample_partitions.items() for start, end in [ranges[name]]
    )
    sample_sets = [set(partition.decision_timestamps) | set(partition.outcome_timestamps)
                   for partition in sample_partitions.values()]
    disjoint_samples = all(not (sample_sets[left] & sample_sets[right])
                           for left in range(len(sample_sets))
                           for right in range(left + 1, len(sample_sets)))
    expected_mean = scaler_rows.mean().to_numpy()
    expected_scale = scaler_rows.std(ddof=0).to_numpy()
    expected_mean = np.where(np.isfinite(expected_mean), expected_mean, 0.0)
    expected_scale = np.where(np.isfinite(expected_scale) & (expected_scale > 0), expected_scale, 1.0)
    checks = {
        "non_overlapping_partitions": non_overlapping,
        "disjoint_partition_samples": disjoint_samples,
        "train_only_scaler": bool(np.allclose(scaler.mean, expected_mean)
                                  and np.allclose(scaler.scale, expected_scale)),
        "all_samples_decision_before_outcome": all(decision < outcome for decision, outcome in all_samples),
        "chronological_samples": all(
            timestamps.is_monotonic_increasing and timestamps.is_unique
            for partition in sample_partitions.values()
            for timestamps in (partition.decision_timestamps, partition.outcome_timestamps)
        ),
        "outcomes_contained_in_partition": containment,
    }
    _write_json(output / "checks.json", checks)
    exit_status = 0 if all(checks.values()) else 1
    failed_checks = [name for name, passed in checks.items() if not passed]
    (output / "run.log").write_text(
        f"diagnostic partitioned baseline\nrun_id={run_id}\n"
        f"command={shlex.join(sys.argv)}\n"
        f"exit_status={exit_status}\nfailed_checks={failed_checks}\n"
    )
    with (output / "predictions.jsonl").open("w") as predictions:
        for name, partition in partitions.items():
            probabilities = predict_logistic(partition.X, weights, bias)
            for decision, outcome, label, probability in zip(
                partition.decision_timestamps, partition.outcome_timestamps,
                partition.y, probabilities,
            ):
                predictions.write(json.dumps(_json_safe({
                    "partition": name, "decision_timestamp": decision.isoformat(),
                    "outcome_timestamp": outcome.isoformat(), "label": float(label),
                    "probability": float(probability),
                }), allow_nan=False) + "\n")
    _write_json(output / "manifest.json", {
        **manifest, "data_sha256": fingerprint,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_status": exit_status, "failed_checks": failed_checks,
    })
    print(json.dumps(_json_safe({"run_id": run_id, "artifact_dir": str(output),
                                "exit_status": exit_status, "metrics": metrics}),
                     indent=2, allow_nan=False))
    return exit_status


def run_validation_only(frame: pd.DataFrame, args: argparse.Namespace) -> int:
    """Validation-only mode: fit on train, evaluate on validation, no test/forward."""
    if args.train_bars <= 0 or args.validation_bars <= 0:
        raise ValueError("train_bars and validation_bars must be positive")
    started_at = datetime.now(timezone.utc).isoformat()
    loaded_rows = len(frame)

    # Compute just train/validation boundaries (no test/forward)
    train_end = args.train_bars
    validation_end = train_end + args.validation_bars
    if len(frame) < validation_end:
        raise SystemExit(f"not enough candles: need {validation_end}, got {len(frame)}")

    # Consume only up to validation end; never load test/forward
    consumed_end = validation_end
    frame = frame.iloc[:consumed_end]
    raw = candle_features(frame)
    scaler_rows = raw.iloc[0:train_end]
    scaler = FeatureScaler.fit(scaler_rows)

    train_partition = make_sequence_partition(
        frame, feature_start=0,
        decision_start=0, decision_end=train_end,
        sequence_length=args.sequence_length, horizon=args.horizon,
        threshold=args.threshold, cost_rate=args.cost_rate, scaler=scaler,
    )

    validation_partition = make_sequence_partition(
        frame, feature_start=0,
        decision_start=train_end, decision_end=validation_end,
        sequence_length=args.sequence_length, horizon=args.horizon,
        threshold=args.threshold, cost_rate=args.cost_rate, scaler=scaler,
    )

    weights, bias = fit_logistic_baseline(train_partition.X, train_partition.y)

    model = classification_metrics(
        validation_partition.y, predict_logistic(validation_partition.X, weights, bias)
    )
    majority = classification_metrics(
        validation_partition.y,
        majority_probabilities(train_partition.y, len(validation_partition.y))
    )

    metrics = {
        "validation": {
            "model": model.__dict__, "majority": majority.__dict__,
            "samples": len(validation_partition.y),
            "decision_start": validation_partition.decision_timestamps[0].isoformat(),
            "decision_end": validation_partition.decision_timestamps[-1].isoformat(),
            "outcome_start": validation_partition.outcome_timestamps[0].isoformat(),
            "outcome_end": validation_partition.outcome_timestamps[-1].isoformat(),
        }
    }

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_lstm_baseline_validation_only")
    output = Path(args.artifacts_dir) / run_id
    output.mkdir(parents=True, exist_ok=False)

    git_status = _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "status", "--porcelain")
    manifest = {
        "run_id": run_id, "study_id": "LSTM-BASELINE-001",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": shlex.join(sys.argv), "argv": list(sys.argv),
        "git_commit": _git_value("git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"),
        "git_status": git_status,
        "dirty_worktree": None if git_status == "unknown" else bool(git_status),
        "ticker": args.ticker.upper(), "period": args.period,
        "rows": len(frame), "date_start": frame.index[0].isoformat(),
        "date_end": frame.index[-1].isoformat(), "storage_timezone": "UTC-naive",
        "used_data_range": {"start": frame.index[0].isoformat(), "end": frame.index[-1].isoformat()},
        "resolved_boundaries": {
            "train": {"row_start": 0, "row_end": train_end,
                      "timestamp_start": frame.index[0].isoformat(),
                      "timestamp_end": frame.index[train_end - 1].isoformat()},
            "validation": {"row_start": train_end, "row_end": validation_end,
                           "timestamp_start": frame.index[train_end].isoformat(),
                           "timestamp_end": frame.index[validation_end - 1].isoformat()},
        },
        "market_timezone": "Europe/Moscow",
        "boundary_convention": "row_end exclusive; timestamp_end inclusive",
        "evaluation_mode": "validation-only",
        "run_class": "diagnostic",
        "started_at_utc": started_at,
        "python_version": sys.version,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "data_source": {"database": getattr(args, "db", None), "table": "candles",
                        "columns": ["begin", "open", "high", "low", "close", "volume"]},
        "loaded_rows": loaded_rows,
        "ignored_loaded_rows": loaded_rows - len(frame),
        "prediction_partitions": ["validation"],
        "execution_model": "classification only; no fills, capital, sizing or executable returns",
        "warmup_policy": "drop non-finite feature windows; causal context may precede partition decisions",
        "fingerprint_scope": "consumed timestamp/open/high/low/close/volume rows only in CSV order",
        "parameters": {k: getattr(args, k) for k in (
            "train_bars", "validation_bars", "sequence_length", "horizon", "threshold", "cost_rate",
        )},
    }

    fingerprint = _fingerprint_frame(frame)
    _write_json(output / "metrics.json", metrics)

    # Sanity checks for validation-only mode
    ranges = {"train": (0, train_end), "validation": (train_end, validation_end)}
    partition_names = tuple(ranges)
    non_overlapping = all(ranges[left][1] <= ranges[right][0]
                          for left, right in zip(partition_names, partition_names[1:]))

    sample_partitions = {"train": train_partition, "validation": validation_partition}
    all_samples = [sample for partition in sample_partitions.values()
                   for sample in zip(partition.decision_timestamps, partition.outcome_timestamps)]
    containment = all(
        all(frame.index[start] <= decision <= frame.index[end - 1]
            and frame.index[start] <= outcome <= frame.index[end - 1]
            for decision, outcome in zip(partition.decision_timestamps, partition.outcome_timestamps))
        for name, partition in sample_partitions.items() for start, end in [ranges[name]]
    )

    sample_sets = [set(partition.decision_timestamps) | set(partition.outcome_timestamps)
                   for partition in sample_partitions.values()]
    disjoint_samples = all(not (sample_sets[left] & sample_sets[right])
                           for left in range(len(sample_sets))
                           for right in range(left + 1, len(sample_sets)))

    expected_mean = scaler_rows.mean().to_numpy()
    expected_scale = scaler_rows.std(ddof=0).to_numpy()
    expected_mean = np.where(np.isfinite(expected_mean), expected_mean, 0.0)
    expected_scale = np.where(np.isfinite(expected_scale) & (expected_scale > 0), expected_scale, 1.0)

    checks = {
        "non_overlapping_partitions": non_overlapping,
        "disjoint_partition_samples": disjoint_samples,
        "train_only_scaler": bool(np.allclose(scaler.mean, expected_mean)
                                  and np.allclose(scaler.scale, expected_scale)),
        "all_samples_decision_before_outcome": all(decision < outcome for decision, outcome in all_samples),
        "chronological_samples": all(
            timestamps.is_monotonic_increasing and timestamps.is_unique
            for partition in sample_partitions.values()
            for timestamps in (partition.decision_timestamps, partition.outcome_timestamps)
        ),
        "outcomes_contained_in_partition": containment,
        "validation_bars_positive": args.validation_bars > 0,
    }

    _write_json(output / "checks.json", checks)
    exit_status = 0 if all(checks.values()) else 1
    failed_checks = [name for name, passed in checks.items() if not passed]

    (output / "run.log").write_text(
        f"validation-only selection gate\nrun_id={run_id}\n"
        f"command={shlex.join(sys.argv)}\n"
        f"exit_status={exit_status}\nfailed_checks={failed_checks}\n"
    )

    with (output / "predictions.jsonl").open("w") as predictions:
        probabilities = predict_logistic(validation_partition.X, weights, bias)
        for decision, outcome, label, probability in zip(
            validation_partition.decision_timestamps, validation_partition.outcome_timestamps,
            validation_partition.y, probabilities,
        ):
            predictions.write(json.dumps(_json_safe({
                "partition": "validation", "decision_timestamp": decision.isoformat(),
                "outcome_timestamp": outcome.isoformat(), "label": float(label),
                "probability": float(probability),
            }), allow_nan=False) + "\n")

    # Save model artifact for validation-only mode: weights, bias, scaler, feature columns
    model_artifact_path, model_artifact_sha256 = save_model_artifact(
        output, weights, bias, scaler, sequence_length=args.sequence_length
    )

    _write_json(output / "manifest.json", {
        **manifest, "data_sha256": fingerprint,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_status": exit_status, "failed_checks": failed_checks,
        "model_artifact": {
            "path": str(model_artifact_path.relative_to(output)),
            "sha256": model_artifact_sha256,
            "schema_version": "1.0",
        },
    })

    print(json.dumps(_json_safe({"run_id": run_id, "artifact_dir": str(output),
                                "exit_status": exit_status, "metrics": metrics}),
                     indent=2, allow_nan=False))
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
