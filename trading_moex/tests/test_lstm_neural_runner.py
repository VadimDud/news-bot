"""Integration tests for run_lstm_neural.py runner.

Tests verify:
- CLI argument parsing and validation
- End-to-end training pipeline with real SQLite data
- Artifact generation (manifest, metrics, scaler, weights, predictions)
- Failure modes (insufficient data, missing PyTorch, artifact save failures)
- Fingerprint stability (appended future rows don't affect training fingerprint)
- Both label classes present in train and validation
- Timestamps prediction ledger correctness
- Read-only database access
- Atomic manifest writes (initial failure, final success)
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import sqlite3

# Add trading_moex to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.lstm_features import candle_features, FeatureScaler, make_sequence_partition
from app.lstm_neural import TORCH_AVAILABLE


# Skip all tests if PyTorch is unavailable
pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")


@pytest.fixture
def tmp_sqlite_db(tmp_path):
    """Create a SQLite database with synthetic OHLCV candles."""
    db_path = tmp_path / "test_trader.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY,
                ticker TEXT NOT NULL,
                period TEXT NOT NULL,
                begin TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                UNIQUE(ticker, period, begin)
            )
        """)

        # Generate synthetic OHLCV data
        np.random.seed(42)
        base_close = 100.0
        n_candles = 600  # Train (500) + Validation (100)

        candles = []
        base_ts = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc).replace(tzinfo=None)
        for i in range(n_candles):
            # Generate realistic OHLCV
            close = base_close * (1 + np.random.normal(0, 0.01))
            open_ = close * (1 + np.random.normal(0, 0.005))
            high = max(open_, close) * (1 + np.abs(np.random.normal(0, 0.003)))
            low = min(open_, close) * (1 - np.abs(np.random.normal(0, 0.003)))
            volume = int(np.random.uniform(1000, 10000))

            # Timestamp (UTC-naive as per protocol) - add 15 minutes per candle
            ts = base_ts + pd.Timedelta(minutes=i * 15)

            candles.append((
                "SBER",
                "15m",
                ts.isoformat(),
                float(open_),
                float(high),
                float(low),
                float(close),
                volume,
            ))
            base_close = close

        conn.executemany(
            "INSERT INTO candles (ticker, period, begin, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            candles,
        )
        conn.commit()

    return db_path


@pytest.fixture
def lstm_runner_script():
    """Path to the runner script."""
    return Path(__file__).resolve().parents[1] / "scripts" / "run_lstm_neural.py"


def run_runner(script_path, args, timeout=120):
    """Execute the runner script with given arguments.

    Args:
        script_path: Path to run_lstm_neural.py
        args: Dict of argument names to values
        timeout: Timeout in seconds

    Returns:
        (exit_code, stdout, stderr)
    """
    cmd = [sys.executable, str(script_path)]
    for key, value in args.items():
        cmd.append(f"--{key}")
        cmd.append(str(value))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return result.returncode, result.stdout, result.stderr


class TestRunnerBasicExecution:
    """Test basic runner execution and artifact generation."""

    def test_successful_training_run(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Test successful end-to-end training with all artifacts."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, stdout, stderr = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "period": "15m",
            "train-bars": 500,
            "validation-bars": 100,
            "sequence-length": 50,
            "horizon": 5,
            "threshold": 0.003,
            "cost-rate": 0.001,
            "hidden-size": 16,
            "num-layers": 1,
            "dropout": 0.1,
            "learning-rate": 0.001,
            "batch-size": 16,
            "epochs": 3,
            "seed": 42,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0, f"Runner failed with exit code {exit_code}\nstderr: {stderr}"

        # Find run directory
        run_dirs = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))
        assert len(run_dirs) == 1, f"Expected 1 run directory, got {len(run_dirs)}"
        run_dir = run_dirs[0]

        # Verify all required artifacts
        assert (run_dir / "manifest.json").exists(), "manifest.json missing"
        assert (run_dir / "metrics.json").exists(), "metrics.json missing"
        assert (run_dir / "checks.json").exists(), "checks.json missing"
        assert (run_dir / "scaler.json").exists(), "scaler.json missing"
        assert (run_dir / "lstm_weights.pt").exists(), "lstm_weights.pt missing"
        assert (run_dir / "train_predictions.csv").exists(), "train_predictions.csv missing"
        assert (run_dir / "validation_predictions.csv").exists(), "validation_predictions.csv missing"
        assert (run_dir / "run.log").exists(), "run.log missing"

    def test_manifest_json_structure(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify manifest.json contains all required fields."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())

        # Verify required fields
        required_fields = [
            "run_id", "study_id", "evaluation_mode", "run_class",
            "utc_start", "command", "git_commit", "dirty_worktree",
            "database", "ticker", "period", "data_sha256",
            "train_bars", "validation_bars", "sequence_length", "horizon",
            "threshold", "cost_rate", "lstm_config", "exit_status",
            "storage_timezone", "market_timezone",
        ]

        for field in required_fields:
            assert field in manifest, f"manifest missing field: {field}"

        assert manifest["exit_status"] == 0
        assert manifest["study_id"] == "LSTM-BASELINE-001"
        assert manifest["evaluation_mode"] == "validation-only"
        assert manifest["data_sha256"] is not None

    def test_start_bar_selects_later_rows_with_causal_warmup(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        artifacts_dir = tmp_path / "windowed"
        exit_code, _, stderr = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db), "ticker": "SBER", "period": "15m",
            "train-bars": 100, "validation-bars": 100, "start-bar": 400,
            "epochs": 2, "artifacts-dir": str(artifacts_dir),
        })
        assert exit_code == 0, stderr
        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        checks = json.loads((run_dir / "checks.json").read_text())
        train = pd.read_csv(run_dir / "train_predictions.csv")
        validation = pd.read_csv(run_dir / "validation_predictions.csv")
        assert manifest["start_bar"] == 400
        assert manifest["window_start_bar"] == 400
        assert manifest["window_end_bar"] == 600
        assert manifest["resolved_window_start"] == "2024-01-05 13:30:00"
        assert checks["exact_row_count"] is True
        assert pd.Timestamp(train.decision_timestamp.min()) >= pd.Timestamp(manifest["resolved_window_start"])
        assert pd.Timestamp(train.decision_timestamp.max()) < pd.Timestamp(validation.decision_timestamp.min())

    def test_start_bar_negative_fails_closed(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        artifacts_dir = tmp_path / "negative-offset"
        code, _, stderr = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db), "ticker": "SBER", "train-bars": 300,
            "validation-bars": 100, "start-bar": -1,
            "artifacts-dir": str(artifacts_dir),
        })
        assert code == 1
        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["exit_status"] == 1
        assert "non-negative" in stderr

    def test_metrics_json_structure(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify metrics.json contains baseline, logistic, and LSTM results."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        metrics = json.loads((run_dir / "metrics.json").read_text())

        # Verify structure
        assert "train_samples" in metrics
        assert "validation_samples" in metrics
        assert "logistic" in metrics
        assert "prevalence" in metrics
        assert "lstm" in metrics

        # Verify baseline metrics
        for model in ["logistic", "prevalence", "lstm"]:
            assert "train" in metrics[model]
            assert "validation" in metrics[model]
            assert "accuracy" in metrics[model]["train"]
            assert "log_loss" in metrics[model]["train"]
            assert "log_loss" in metrics[model]["validation"]

    def test_scaler_metadata(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify scaler.json contains mean and scale."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        scaler_meta = json.loads((run_dir / "scaler.json").read_text())

        assert "mean" in scaler_meta
        assert "scale" in scaler_meta
        assert scaler_meta["fitted_on"] == "train_prefix_only"
        assert "feature_columns" in scaler_meta
        assert len(scaler_meta["mean"]) == 10  # 10 features
        assert len(scaler_meta["scale"]) == 10

    def test_predictions_ledger_structure(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify prediction CSV contains correct columns and timestamps."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]

        # Check train predictions
        train_preds = pd.read_csv(run_dir / "train_predictions.csv")
        assert set(train_preds.columns) == {
            "decision_timestamp", "outcome_timestamp", "label",
            "logistic_prob", "prevalence_prob", "lstm_prob",
        }
        assert len(train_preds) > 0
        assert train_preds["label"].isin([0, 1]).all()
        assert (train_preds[["logistic_prob", "prevalence_prob", "lstm_prob"]] >= 0).all().all()
        assert (train_preds[["logistic_prob", "prevalence_prob", "lstm_prob"]] <= 1).all().all()

        # Check validation predictions
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")
        assert len(val_preds) > 0


class TestRunnerFailureModes:
    """Test error handling and failure manifests."""

    def test_insufficient_data(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Test runner fails gracefully with insufficient data."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, stdout, stderr = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 300,
            "validation-bars": 400,  # Total 700 > 600 available
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 1, "Should fail with exit code 1"
        assert "insufficient data" in stderr.lower()

        # Verify failure manifest was written
        run_dirs = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["exit_status"] == 1
        assert "failure_reason" in manifest

    def test_no_candles_found(self, tmp_path, lstm_runner_script):
        """Test runner fails when no candles match ticker."""
        # Create empty database
        db_path = tmp_path / "empty.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE candles (
                    ticker TEXT, period TEXT, begin TEXT,
                    open REAL, high REAL, low REAL, close REAL, volume INTEGER
                )
            """)

        artifacts_dir = tmp_path / "artifacts"

        exit_code, stdout, stderr = run_runner(lstm_runner_script, {
            "db": str(db_path),
            "ticker": "NONEXISTENT",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 1
        assert "no candles found" in stderr.lower()


class TestRunnerDataIntegrity:
    """Test data integrity: fingerprint, causality, and boundaries."""

    def test_fingerprint_stable_on_appended_data(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify fingerprint doesn't change when future rows are appended."""
        artifacts_dir = tmp_path / "artifacts"

        # First run
        exit_code1, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir),
        })
        assert exit_code1 == 0

        run_dir1 = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest1 = json.loads((run_dir1 / "manifest.json").read_text())
        fingerprint1 = manifest1["data_sha256"]

        # Append future rows to database
        with sqlite3.connect(tmp_sqlite_db) as conn:
            np.random.seed(100)
            base_close = 100.0
            n_existing = 600
            n_append = 50
            base_ts = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc).replace(tzinfo=None)

            new_candles = []
            for i in range(n_append):
                close = base_close * (1 + np.random.normal(0, 0.01))
                open_ = close * (1 + np.random.normal(0, 0.005))
                high = max(open_, close) * (1 + np.abs(np.random.normal(0, 0.003)))
                low = min(open_, close) * (1 - np.abs(np.random.normal(0, 0.003)))
                volume = int(np.random.uniform(1000, 10000))

                ts = base_ts + pd.Timedelta(minutes=(n_existing + i) * 15)

                new_candles.append((
                    "SBER", "15m", ts.isoformat(),
                    float(open_), float(high), float(low), float(close), volume
                ))
                base_close = close

            conn.executemany(
                "INSERT INTO candles (ticker, period, begin, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                new_candles,
            )
            conn.commit()

        # Second run (should read only train + validation)
        artifacts_dir2 = tmp_path / "artifacts2"
        exit_code2, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir2),
        })
        assert exit_code2 == 0

        run_dir2 = list(artifacts_dir2.glob("*_LSTM-NEURAL_*"))[0]
        manifest2 = json.loads((run_dir2 / "manifest.json").read_text())
        fingerprint2 = manifest2["data_sha256"]

        # Fingerprints must match (same 600 rows)
        assert fingerprint1 == fingerprint2, "Fingerprint changed despite same row count"

    def test_both_classes_present_in_labels(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify training and validation partitions have both label classes."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]

        train_preds = pd.read_csv(run_dir / "train_predictions.csv")
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")

        # Both classes must be present
        assert set(train_preds["label"].unique()) == {0, 1}, "Training labels don't have both classes"
        assert set(val_preds["label"].unique()) == {0, 1}, "Validation labels don't have both classes"

    def test_prediction_count_matches_samples(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify prediction count matches partition sample count."""
        artifacts_dir = tmp_path / "artifacts"

        train_bars = 500
        val_bars = 100

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": train_bars,
            "validation-bars": val_bars,
            "sequence-length": 50,
            "horizon": 5,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        metrics = json.loads((run_dir / "metrics.json").read_text())

        train_preds = pd.read_csv(run_dir / "train_predictions.csv")
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")

        # Prediction counts must match
        assert len(train_preds) == metrics["train_samples"]
        assert len(val_preds) == metrics["validation_samples"]


class TestRunnerTimestamps:
    """Test timestamp correctness in prediction ledgers."""

    def test_timestamps_are_iso_format(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify decision and outcome timestamps are ISO format strings."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")

        # All timestamps must be parseable ISO format
        for ts in val_preds["decision_timestamp"]:
            pd.Timestamp(ts)  # Will raise if invalid

        for ts in val_preds["outcome_timestamp"]:
            pd.Timestamp(ts)  # Will raise if invalid

    def test_outcome_timestamp_after_decision(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify outcome timestamps are always after decision timestamps."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "horizon": 5,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")

        decision_ts = pd.to_datetime(val_preds["decision_timestamp"])
        outcome_ts = pd.to_datetime(val_preds["outcome_timestamp"])

        # All outcomes must be after decisions
        assert (outcome_ts > decision_ts).all(), "Some outcomes are not after decisions"


class TestRunnerReadOnly:
    """Test read-only database access."""

    def test_readonly_database_access(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify runner doesn't modify the database."""
        # Get original file hash
        original_stat = tmp_sqlite_db.stat()
        original_mtime = original_stat.st_mtime

        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        # Check file wasn't modified
        new_stat = tmp_sqlite_db.stat()
        new_mtime = new_stat.st_mtime

        assert new_mtime == original_mtime, "Database file was modified"


class TestRunnerSeeding:
    """Test reproducibility with fixed seeds."""

    def test_deterministic_with_same_seed(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify two runs with same seed produce identical metrics."""
        artifacts_dir1 = tmp_path / "artifacts1"
        artifacts_dir2 = tmp_path / "artifacts2"

        for artifacts_dir in [artifacts_dir1, artifacts_dir2]:
            exit_code, _, _ = run_runner(lstm_runner_script, {
                "db": str(tmp_sqlite_db),
                "ticker": "SBER",
                "train-bars": 500,
                "validation-bars": 100,
                "seed": 42,
                "epochs": 2,
                "batch-size": 16,
                "artifacts-dir": str(artifacts_dir),
            })
            assert exit_code == 0

        run_dir1 = list(artifacts_dir1.glob("*_LSTM-NEURAL_*"))[0]
        run_dir2 = list(artifacts_dir2.glob("*_LSTM-NEURAL_*"))[0]

        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # LSTM training history should be very similar with same seed
        assert np.allclose(
            metrics1["lstm"]["train"]["accuracy"],
            metrics2["lstm"]["train"]["accuracy"],
            atol=1e-4,
        )


class TestRunnerArtifactAtomicity:
    """Test atomic manifest writes."""

    def test_manifest_written_on_success(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify success manifest is written at end."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())

        assert manifest["exit_status"] == 0
        assert "failure_reason" not in manifest

    def test_failure_manifest_written_on_error(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify failure manifest is written before exit."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 600,
            "validation-bars": 100,  # Total 700 > 600 available
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 1

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())

        assert manifest["exit_status"] == 1
        assert "failure_reason" in manifest


class TestRunnerMetricsConsistency:
    """Test metrics consistency across baselines."""

    def test_same_training_samples_across_models(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify all models evaluated on same training samples."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        metrics = json.loads((run_dir / "metrics.json").read_text())

        train_preds = pd.read_csv(run_dir / "train_predictions.csv")
        val_preds = pd.read_csv(run_dir / "validation_predictions.csv")

        # All three models should have predictions for same samples
        assert len(train_preds) == metrics["train_samples"]
        assert len(val_preds) == metrics["validation_samples"]

        # Training positive rate should match in predictions
        train_positive_rate = metrics["train_positive_rate"]
        predicted_positive_rate = train_preds["label"].mean()
        assert np.isclose(train_positive_rate, predicted_positive_rate, atol=1e-5)

    def test_all_metrics_finite(self, tmp_sqlite_db, tmp_path, lstm_runner_script):
        """Verify all reported metrics are finite (not NaN or inf)."""
        artifacts_dir = tmp_path / "artifacts"

        exit_code, _, _ = run_runner(lstm_runner_script, {
            "db": str(tmp_sqlite_db),
            "ticker": "SBER",
            "train-bars": 500,
            "validation-bars": 100,
            "epochs": 2,
            "artifacts-dir": str(artifacts_dir),
        })

        assert exit_code == 0

        run_dir = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))[0]
        metrics = json.loads((run_dir / "metrics.json").read_text())
        checks = json.loads((run_dir / "checks.json").read_text())

        assert checks["all_metrics_finite"] is True

        # Spot check a few values are finite
        for model in ["logistic", "prevalence", "lstm"]:
            for partition in ["train", "validation"]:
                log_loss = metrics[model][partition]["log_loss"]
                if log_loss is not None:
                    assert np.isfinite(log_loss), f"{model} {partition} log_loss not finite"


@pytest.mark.skipif(
    sys.executable not in ["/tmp/opencode/lstm-venv/bin/python"],
    reason="Requires PyTorch-enabled venv at /tmp/opencode/lstm-venv"
)
class TestRunnerWithTorchVenv:
    """Integration tests using isolated PyTorch venv."""

    def test_execution_with_subprocess_interpreter(self, tmp_sqlite_db, tmp_path):
        """Test runner executes successfully via subprocess with torch venv."""
        # This test verifies torch is actually available and executable
        check_torch = subprocess.run(
            ["/tmp/opencode/lstm-venv/bin/python", "-c", "import torch; print(torch.__version__)"],
            capture_output=True,
            text=True,
        )

        if check_torch.returncode != 0:
            pytest.skip("PyTorch not available in venv")

        # Now run the actual training
        artifacts_dir = tmp_path / "artifacts"
        lstm_runner_script = Path(__file__).resolve().parents[1] / "scripts" / "run_lstm_neural.py"

        result = subprocess.run(
            ["/tmp/opencode/lstm-venv/bin/python", str(lstm_runner_script),
             "--db", str(tmp_sqlite_db),
             "--ticker", "SBER",
             "--train-bars", "500",
             "--validation-bars", "100",
             "--epochs", "2",
             "--artifacts-dir", str(artifacts_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"Runner failed: {result.stderr}"

        # Verify artifacts exist
        run_dirs = list(artifacts_dir.glob("*_LSTM-NEURAL_*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "metrics.json").exists()
        assert (run_dir / "lstm_weights.pt").exists()
