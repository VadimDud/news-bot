import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import run_lstm_baseline as runner


def strict_load(text):
    def reject(value):
        raise AssertionError(f"non-JSON constant: {value}")
    return json.loads(text, parse_constant=reject)


@pytest.fixture
def candles():
    close = np.r_[100 + np.arange(70), 169 - np.arange(80) * .5]
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1,
                         "close": close, "volume": 100 + np.arange(150) % 11},
                        index=pd.date_range("2020-01-01", periods=150, name="timestamp"))


def test_git_helper_preserves_clean_and_reports_failure(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path / "repo")], check=True)
    monkeypatch.chdir(tmp_path / "repo")
    assert runner._git_value("git", "status", "--porcelain") == ""
    assert runner._git_value("git", "rev-parse", "HEAD") == "unknown"
    assert runner._git_value("missing-git-executable") == "unknown"


def test_partitioned_artifacts(candles, tmp_path, monkeypatch, capsys):
    args = argparse.Namespace(train_bars=70, validation_bars=20, test_bars=20,
                              forward_bars=20, sequence_length=3, horizon=2,
                              threshold=0, cost_rate=0, ticker="demo", period="1day",
                              artifacts_dir=str(tmp_path / "runs"))
    constructed = []
    original = runner.make_sequence_partition

    def record(*a, **kw):
        partition = original(*a, **kw)
        constructed.append(partition)
        return partition

    monkeypatch.setattr(runner, "make_sequence_partition", record)
    monkeypatch.setattr(runner, "_git_value", lambda *a: "" if "status" in a else "test-commit")
    assert runner.run_partitioned(candles, args) == 0
    result = strict_load(capsys.readouterr().out)
    output = Path(result["artifact_dir"])
    assert len(constructed) == 4
    assert constructed[0].y.mean() == 1
    assert constructed[1].y.mean() == 0
    assert {p.name for p in output.iterdir()} == {
        "manifest.json", "metrics.json", "checks.json", "predictions.jsonl", "run.log"}
    manifest = strict_load((output / "manifest.json").read_text())
    assert manifest["dirty_worktree"] is False
    assert manifest["untouched_forward"] is False
    assert manifest["rows"] == 130
    assert manifest["available_rows"] == 150
    assert manifest["ignored_trailing_rows"] == 20
    assert manifest["exit_status"] == 0
    assert manifest["failed_checks"] == []
    assert manifest["started_at_utc"] <= manifest["finished_at_utc"]
    assert manifest["numpy_version"] == np.__version__
    assert manifest["argv"] == sys.argv
    assert manifest["used_data_range"]["end"] == candles.index[129].isoformat()
    assert manifest["resolved_boundaries"]["train"]["row_end"] == 70
    assert manifest["data_sha256"] == runner._fingerprint_frame(candles.iloc[:130])
    metrics = strict_load((output / "metrics.json").read_text())
    assert metrics == result["metrics"]
    for value in metrics.values():
        assert value["majority"]["accuracy"] == 0
        assert value["majority"]["balanced_accuracy"] is None
        assert value["majority"]["recall"] is None
    assert all(strict_load((output / "checks.json").read_text()).values())
    predictions = [strict_load(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    assert len(predictions) == sum(m["samples"] for m in metrics.values())
    assert all(p["decision_timestamp"] < p["outcome_timestamp"] for p in predictions)
    assert runner.run_partitioned(candles, args) == 0
    assert strict_load(capsys.readouterr().out)["run_id"] != result["run_id"]


def test_sqlite_cli_strict_json_and_selected_fingerprint(candles, tmp_path):
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--test-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0"]
    folds = strict_load(subprocess.check_output(command, text=True))["folds"]
    assert folds[0]["majority"]["balanced_accuracy"] is None
    command += ["--validation-bars", "20", "--forward-bars", "20",
                "--artifacts-dir", str(tmp_path / "runs")]
    first = strict_load(subprocess.check_output(command, text=True))
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('not part of fingerprint')")
        connection.execute("INSERT INTO candles SELECT begin, open, high, low, close, volume, 'OTHER', period FROM candles")
    second = strict_load(subprocess.check_output(command, text=True))
    manifests = [strict_load((Path(r["artifact_dir"]) / "manifest.json").read_text())
                 for r in (first, second)]
    assert manifests[0]["data_sha256"] == manifests[1]["data_sha256"]
    changed = candles.copy()
    changed.loc[changed.index[30], "volume"] += 1
    assert runner._fingerprint_frame(changed) != runner._fingerprint_frame(candles)


def test_nonfinite_serialization():
    assert strict_load(json.dumps(runner._json_safe(
        {"metrics": [float("nan"), float("inf"), -float("inf"), 1.0]}),
        allow_nan=False)) == {"metrics": [None, None, None, 1.0]}


def test_checks_reject_wrong_scaler(candles, tmp_path, monkeypatch, capsys):
    args = argparse.Namespace(train_bars=70, validation_bars=20, test_bars=20,
                              forward_bars=20, sequence_length=3, horizon=2,
                              threshold=0, cost_rate=0, ticker="demo", period="1day",
                              artifacts_dir=str(tmp_path / "runs"))
    original = runner.FeatureScaler.fit

    def corrupt(cls, frame):
        scaler = original(frame)
        return cls(scaler.mean + 1, scaler.scale)

    monkeypatch.setattr(runner.FeatureScaler, "fit", classmethod(corrupt))
    assert runner.run_partitioned(candles, args) == 1
    result = strict_load(capsys.readouterr().out)
    manifest = strict_load((Path(result["artifact_dir"]) / "manifest.json").read_text())
    assert "train_only_scaler" in manifest["failed_checks"]


def test_checks_detect_invalid_later_sample(candles, tmp_path, monkeypatch, capsys):
    args = argparse.Namespace(train_bars=70, validation_bars=20, test_bars=20,
                              forward_bars=20, sequence_length=3, horizon=2,
                              threshold=0, cost_rate=0, ticker="demo", period="1day",
                              artifacts_dir=str(tmp_path / "runs"))
    original = runner.make_sequence_partition

    def corrupt(*a, **kw):
        partition = original(*a, **kw)
        if kw["decision_start"] == 90:
            outcomes = partition.outcome_timestamps.tolist()
            outcomes[1] = candles.index[75]
            return type(partition)(partition.X, partition.y,
                                   partition.decision_timestamps, pd.Index(outcomes))
        return partition

    monkeypatch.setattr(runner, "make_sequence_partition", corrupt)
    monkeypatch.setattr(runner, "_git_value", lambda *a: "unknown")
    assert runner.run_partitioned(candles, args) == 1
    output = Path(strict_load(capsys.readouterr().out)["artifact_dir"])
    checks = strict_load((output / "checks.json").read_text())
    assert checks["all_samples_decision_before_outcome"] is False
    assert checks["outcomes_contained_in_partition"] is False
    assert checks["disjoint_partition_samples"] is False
    assert checks["chronological_samples"] is False
    manifest = strict_load((output / "manifest.json").read_text())
    assert manifest["git_status"] == "unknown"
    assert manifest["dirty_worktree"] is None
    assert manifest["exit_status"] == 1
    assert "outcomes_contained_in_partition" in manifest["failed_checks"]


def test_validation_only_mode_rejects_missing_bars(candles, tmp_path):
    """Validation-only mode requires --validation-bars."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "0",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "validation-bars" in result.stderr.lower()


def test_validation_only_mode_rejects_test_or_forward(candles, tmp_path):
    """Validation-only mode disallows --test-bars and --forward-bars."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)

    # Try with --test-bars
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--test-bars", "20", "--sequence-length", "3", "--horizon", "2",
               "--threshold", "0", "--cost-rate", "0", "--validation-only"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "disallows" in result.stderr.lower()


def test_validation_only_prequery_validation_nonexistent_db(tmp_path):
    """Validation-only mode fails gracefully on nonexistent database."""
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(tmp_path / "nonexistent.db"),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "database" in result.stderr.lower() or "no candles" in result.stderr.lower()


def test_validation_only_prequery_validation_train_bars_required(candles, tmp_path):
    """Validation-only mode requires train_bars > 0."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "0", "--validation-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "train-bars" in result.stderr.lower()


def test_validation_only_prequery_validation_rejects_negative_forward_bars(candles, tmp_path):
    """Validation-only mode rejects explicit forward_bars including negative."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--forward-bars", "-5", "--sequence-length", "3", "--horizon", "2",
               "--threshold", "0", "--cost-rate", "0", "--validation-only"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert "disallows" in result.stderr.lower()


def test_validation_only_consumes_train_plus_validation_only(candles, tmp_path, monkeypatch, capsys):
    """Validation-only mode with full candles frame tracks loaded_rows correctly."""
    args = argparse.Namespace(
        train_bars=70, validation_bars=20, test_bars=None, forward_bars=0,
        sequence_length=3, horizon=2, threshold=0, cost_rate=0,
        ticker="demo", period="1day", artifacts_dir=str(tmp_path / "runs"),
        validation_only=True
    )
    monkeypatch.setattr(runner, "_git_value", lambda *a: "" if "status" in a else "test-commit")
    # Direct call records full frame as loaded_rows
    assert runner.run_validation_only(candles, args) == 0
    result = strict_load(capsys.readouterr().out)
    output = Path(result["artifact_dir"])
    manifest = strict_load((output / "manifest.json").read_text())

    # Direct call with full frame records loaded_rows as frame size
    assert manifest["rows"] == 90  # Consumed train + validation
    assert manifest["loaded_rows"] == 150  # Full frame passed in
    assert manifest["run_class"] == "diagnostic"
    assert manifest["evaluation_mode"] == "validation-only"
    assert "validation" in manifest["prediction_partitions"]
    assert "test" not in manifest["prediction_partitions"]
    assert "forward" not in manifest["prediction_partitions"]


def test_validation_only_produces_validation_metrics_only(candles, tmp_path, monkeypatch, capsys):
    """Validation-only mode evaluates validation partition only."""
    args = argparse.Namespace(
        train_bars=70, validation_bars=20, test_bars=0, forward_bars=0,
        sequence_length=3, horizon=2, threshold=0, cost_rate=0,
        ticker="demo", period="1day", artifacts_dir=str(tmp_path / "runs"),
        validation_only=True
    )
    monkeypatch.setattr(runner, "_git_value", lambda *a: "" if "status" in a else "test-commit")
    assert runner.run_validation_only(candles, args) == 0
    result = strict_load(capsys.readouterr().out)
    metrics = result["metrics"]
    
    # Only validation in metrics, no test or forward
    assert "validation" in metrics
    assert "test" not in metrics
    assert "forward" not in metrics
    assert metrics["validation"]["samples"] > 0


def test_validation_only_sql_limit_via_cli(candles, tmp_path):
    """Validation-only CLI uses SQL LIMIT to restrict loaded_rows to train+validation only."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)

    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only", "--artifacts-dir", str(tmp_path / "runs")]
    result = strict_load(subprocess.check_output(command, text=True))
    manifest = strict_load((Path(result["artifact_dir"]) / "manifest.json").read_text())

    # SQL LIMIT should restrict loaded_rows to exactly train + validation
    assert manifest["loaded_rows"] == 90
    assert manifest["rows"] == 90
    assert manifest["ignored_loaded_rows"] == 0


def test_validation_only_fingerprints_consumed_rows_only(candles, tmp_path, monkeypatch):
    """Validation-only mode fingerprints only consumed train + validation rows."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    
    # Run validation-only
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only", "--artifacts-dir", str(tmp_path / "runs")]
    first = strict_load(subprocess.check_output(command, text=True))
    
    # Fingerprint should only include first 90 rows
    manifest1 = strict_load((Path(first["artifact_dir"]) / "manifest.json").read_text())
    fingerprint1 = manifest1["data_sha256"]
    
    # Verify that fingerprint equals the consumed portion
    consumed = candles.iloc[:90]
    expected_fingerprint = runner._fingerprint_frame(consumed)
    assert fingerprint1 == expected_fingerprint


def test_validation_only_retains_default_partitioned_behavior(candles, tmp_path, monkeypatch, capsys):
    """Confirm default partitioned mode still works after validation-only changes."""
    args = argparse.Namespace(
        train_bars=70, validation_bars=20, test_bars=20, forward_bars=20,
        sequence_length=3, horizon=2, threshold=0, cost_rate=0,
        ticker="demo", period="1day", artifacts_dir=str(tmp_path / "runs"),
        validation_only=False
    )
    monkeypatch.setattr(runner, "_git_value", lambda *a: "" if "status" in a else "test-commit")
    assert runner.run_partitioned(candles, args) == 0
    result = strict_load(capsys.readouterr().out)
    metrics = result["metrics"]
    
    # Default partitioned should have all partitions
    assert "validation" in metrics
    assert "test" in metrics
    assert "forward" in metrics


def test_validation_only_checks_reject_invalid_flags(candles, tmp_path, monkeypatch, capsys):
    """Validation-only checks include validation_bars_positive."""
    args = argparse.Namespace(
        train_bars=70, validation_bars=20, test_bars=None, forward_bars=0,
        sequence_length=3, horizon=2, threshold=0, cost_rate=0,
        ticker="demo", period="1day", artifacts_dir=str(tmp_path / "runs"),
        validation_only=True
    )
    monkeypatch.setattr(runner, "_git_value", lambda *a: "unknown")
    assert runner.run_validation_only(candles, args) == 0
    output = Path(strict_load(capsys.readouterr().out)["artifact_dir"])
    checks = strict_load((output / "checks.json").read_text())

    assert checks["validation_bars_positive"] is True


def test_validation_only_later_rows_do_not_affect_validation(candles, tmp_path, monkeypatch, capsys):
    """Validation-only mode is unaffected by changes to rows after validation boundary."""
    db = tmp_path / "input.db"
    with sqlite3.connect(db) as connection:
        rows = candles.reset_index().rename(columns={"timestamp": "begin"})
        rows["ticker"], rows["period"] = "DEMO", "1day"
        rows.to_sql("candles", connection, index=False)
    
    # First run: validation-only on first 90 rows
    command = [sys.executable, str(Path(runner.__file__)), "--db", str(db),
               "--ticker", "demo", "--train-bars", "70", "--validation-bars", "20",
               "--sequence-length", "3", "--horizon", "2", "--threshold", "0",
               "--cost-rate", "0", "--validation-only", "--artifacts-dir", str(tmp_path / "runs")]
    first = strict_load(subprocess.check_output(command, text=True))

    # Insert more data after row 90
    with sqlite3.connect(db) as connection:
        new_rows = candles.iloc[90:].reset_index().rename(columns={"timestamp": "begin"})
        new_rows["ticker"], new_rows["period"] = "DEMO", "1day"
        new_rows.to_sql("candles", connection, index=False, if_exists="append")

    # Second run: same validation-only should produce identical results
    second = strict_load(subprocess.check_output(command, text=True))

    manifest1 = strict_load((Path(first["artifact_dir"]) / "manifest.json").read_text())
    manifest2 = strict_load((Path(second["artifact_dir"]) / "manifest.json").read_text())

    # Fingerprints should be identical (same consumed data)
    assert manifest1["data_sha256"] == manifest2["data_sha256"]
    assert manifest1["loaded_rows"] == manifest2["loaded_rows"] == 90


def test_validation_only_corrupt_scaler_fails_closed(candles, tmp_path, monkeypatch, capsys):
    """Validation-only mode fails if scaler is corrupted (train-only check)."""
    args = argparse.Namespace(
        train_bars=70, validation_bars=20, test_bars=None, forward_bars=0,
        sequence_length=3, horizon=2, threshold=0, cost_rate=0,
        ticker="demo", period="1day", artifacts_dir=str(tmp_path / "runs"),
        validation_only=True
    )
    original = runner.FeatureScaler.fit

    def corrupt(frame):
        scaler = original(frame)
        return runner.FeatureScaler(scaler.mean + 1, scaler.scale)

    monkeypatch.setattr(runner.FeatureScaler, "fit", classmethod(lambda cls, frame: corrupt(frame)))
    monkeypatch.setattr(runner, "_git_value", lambda *a: "unknown")
    assert runner.run_validation_only(candles, args) == 1
    output = Path(strict_load(capsys.readouterr().out)["artifact_dir"])
    manifest = strict_load((output / "manifest.json").read_text())
    assert "train_only_scaler" in manifest["failed_checks"]
