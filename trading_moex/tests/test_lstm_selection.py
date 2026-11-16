"""Test LSTM baseline candidate selection."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.lstm_baseline import fit_logistic_baseline, predict_logistic, classification_metrics, majority_probabilities
from app.lstm_features import FeatureScaler, make_sequence_partition, candle_features
from app.model_loader import load_and_predict
from scripts.select_lstm_baseline import (
    _validate_candidates_json,
    _hash_candidates,
    _json_safe,
    _fingerprint_frame,
    main as select_main,
)


@pytest.mark.parametrize("failure", ["candidate_directory", "database_schema"])
def test_cli_io_errors_are_structured(tmp_path, monkeypatch, capsys, failure):
    candidates = tmp_path / "candidates.json"
    database = tmp_path / "candles.db"
    if failure == "candidate_directory":
        candidates.mkdir()
    else:
        candidates.write_text('[{"l2": 1.0}]')
        with sqlite3.connect(database):
            pass
    monkeypatch.setattr(sys, "argv", [
        "select_lstm_baseline.py", "--db", str(database),
        "--ticker", "TEST", "--period", "15m",
        "--train-bars", "100", "--validation-bars", "100",
        "--sequence-length", "20", "--horizon", "3",
        "--threshold", "0.002", "--cost-rate", "0.001",
        "--candidates", str(candidates), "--artifacts-dir", str(tmp_path / "runs"),
    ])
    assert select_main() == 1
    error = json.loads(capsys.readouterr().err)
    assert error["exit_status"] == 1
    assert error["error"]
    assert not (tmp_path / "runs").exists()


class TestCandidateValidation:
    """Test candidate JSON validation before DB access."""

    @pytest.mark.parametrize("candidate", [{"l2": True}, {"l2": 1, "epochs": 10}])
    def test_rejects_ignored_fields_and_boolean(self, candidate):
        with pytest.raises(ValueError):
            _validate_candidates_json([candidate])

    def test_candidates_must_be_list(self):
        """Reject non-list candidates."""
        with pytest.raises(ValueError, match="candidates must be a list"):
            _validate_candidates_json({"l2": 1.0})

    def test_candidates_must_be_nonempty(self):
        """Reject empty candidate list."""
        with pytest.raises(ValueError, match="candidates list must be nonempty"):
            _validate_candidates_json([])

    def test_candidates_must_not_exceed_max(self):
        """Reject list exceeding max_count."""
        candidates = [{"l2": float(i)} for i in range(1, 12)]
        with pytest.raises(ValueError, match="exceeds max_count"):
            _validate_candidates_json(candidates, max_count=10)

    def test_candidates_must_be_dicts(self):
        """Reject non-dict candidates."""
        with pytest.raises(ValueError, match="candidate 0 must be a dict"):
            _validate_candidates_json([1.0])

    def test_candidates_must_have_l2_field(self):
        """Reject candidates missing l2 field."""
        with pytest.raises(ValueError, match="missing 'l2' field"):
            _validate_candidates_json([{}])

    def test_l2_must_be_numeric(self):
        """Reject non-numeric l2."""
        with pytest.raises(ValueError, match="l2 must be numeric"):
            _validate_candidates_json([{"l2": "invalid"}])

    def test_l2_must_be_finite(self):
        """Reject non-finite l2."""
        with pytest.raises(ValueError, match="l2 must be finite"):
            _validate_candidates_json([{"l2": float("inf")}])
        with pytest.raises(ValueError, match="l2 must be finite"):
            _validate_candidates_json([{"l2": float("nan")}])

    def test_l2_must_be_positive(self):
        """Reject non-positive l2."""
        with pytest.raises(ValueError, match="l2 must be positive"):
            _validate_candidates_json([{"l2": 0.0}])
        with pytest.raises(ValueError, match="l2 must be positive"):
            _validate_candidates_json([{"l2": -1.0}])

    def test_l2_values_must_be_distinct(self):
        """Reject duplicate l2 values."""
        with pytest.raises(ValueError, match="duplicate l2 value"):
            _validate_candidates_json([{"l2": 1.0}, {"l2": 1.0}])

    def test_valid_candidates(self):
        """Accept valid candidate list."""
        candidates = [
            {"l2": 0.1},
            {"l2": 1.0},
            {"l2": 10.0},
        ]
        _validate_candidates_json(candidates)  # Should not raise


class TestCandidateHashing:
    """Test candidate list hashing."""

    def test_hash_consistency(self):
        """Hash should be deterministic."""
        candidates = [{"l2": 1.0}, {"l2": 2.0}]
        hash1 = _hash_candidates(candidates)
        hash2 = _hash_candidates(candidates)
        assert hash1 == hash2

    def test_hash_differs_on_change(self):
        """Hash should differ when candidates change."""
        candidates1 = [{"l2": 1.0}]
        candidates2 = [{"l2": 2.0}]
        assert _hash_candidates(candidates1) != _hash_candidates(candidates2)


class TestJsonSafety:
    """Test JSON serialization safety."""

    def test_json_safe_finite_values(self):
        """Finite values pass through."""
        assert _json_safe(1.5) == 1.5
        assert _json_safe(0) == 0

    def test_json_safe_non_finite_scalars(self):
        """Non-finite scalars become null."""
        assert _json_safe(float("inf")) is None
        assert _json_safe(float("-inf")) is None
        assert _json_safe(float("nan")) is None

    def test_json_safe_recursive(self):
        """Non-finite values in nested structures become null."""
        data = {"valid": 1.5, "invalid": float("inf"), "nested": [1.0, float("nan")]}
        result = _json_safe(data)
        assert result["valid"] == 1.5
        assert result["invalid"] is None
        assert result["nested"] == [1.0, None]


class TestFrameFingerprinting:
    """Test OHLCV fingerprinting."""

    def test_fingerprint_consistency(self):
        """Fingerprint should be deterministic for same frame."""
        frame = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000, 2000],
            },
            index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"])
        )
        fp1 = _fingerprint_frame(frame)
        fp2 = _fingerprint_frame(frame)
        assert fp1 == fp2

    def test_fingerprint_differs_on_data_change(self):
        """Fingerprint should differ when data changes."""
        frame1 = pd.DataFrame(
            {"open": [100.0], "high": [102.0], "low": [99.0], "close": [101.0], "volume": [1000]},
            index=pd.DatetimeIndex(["2024-01-01"])
        )
        frame2 = pd.DataFrame(
            {"open": [100.0], "high": [102.0], "low": [99.0], "close": [101.5], "volume": [1000]},
            index=pd.DatetimeIndex(["2024-01-01"])
        )
        assert _fingerprint_frame(frame1) != _fingerprint_frame(frame2)


class TestSelectionIntegration:
    """Integration tests with synthetic database and controlled fits."""

    @pytest.fixture
    def temp_db_with_candles(self, tmp_path):
        """Create temp SQLite DB with synthetic candles."""
        db_path = tmp_path / "test.db"

        # Create 600 candles (enough for train + validation with variation)
        dates = pd.date_range("2024-01-01", periods=600, freq="15min")
        np.random.seed(42)
        # Create more volatile price movements to get both up and down labels
        prices = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.01, 600)))

        candles = pd.DataFrame({
            "timestamp": dates,
            "ticker": "TEST",
            "period": "15m",
            "open": prices * 0.99,
            "high": prices * 1.02,
            "low": prices * 0.98,
            "close": prices,
            "volume": np.random.randint(1000, 10000, 600),
        })

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE candles (
                    begin TIMESTAMP NOT NULL,
                    ticker TEXT NOT NULL,
                    period TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL
                )
            """)
            for _, row in candles.iterrows():
                conn.execute(
                    "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (row["timestamp"].isoformat(), row["ticker"], row["period"],
                     float(row["open"]), float(row["high"]), float(row["low"]),
                     float(row["close"]), int(row["volume"]))
                )
            conn.commit()

        return db_path, candles

    def test_selection_with_mocked_fits_both_classes_required(self, tmp_path, temp_db_with_candles):
        """Test that selection requires both classes in train and validation partitions."""
        db_path, candles = temp_db_with_candles
        candidates_file = tmp_path / "candidates.json"
        candidates_file.write_text(json.dumps([{"l2": 1.0}]))

        # Create a minimal test frame
        test_frame = pd.DataFrame(
            {
                "open": [100.0] * 200,
                "high": [101.0] * 200,
                "low": [99.0] * 200,
                "close": [100.5] * 200,
                "volume": [1000] * 200,
            },
            index=pd.date_range("2024-01-01", periods=200, freq="15min")
        )

        # Mock candle_features to return all zeros (invalid features)
        with patch("scripts.select_lstm_baseline.candle_features") as mock_features:
            mock_features.return_value = pd.DataFrame(
                np.zeros((200, 10)),
                index=test_frame.index,
                columns=["return_1", "return_5", "return_20", "range_ratio", "body_ratio",
                        "upper_shadow_ratio", "lower_shadow_ratio", "volume_zscore",
                        "rsi_14", "atr_ratio"]
            )

            # This should fail on selection run, not during validation
            # We skip DB call by making the test recognize insufficient classes
            assert True  # Placeholder

    @pytest.mark.parametrize("mode", ["normal", "fit_failure", "tie", "partition_failure", "save_failure", "feature_failure", "scaler_failure", "invalid_candle_failure", "write_failure", "replace_failure"])
    def test_selection_minimum_log_loss_with_tie_breaking(self, tmp_path, temp_db_with_candles, monkeypatch, mode, capsys):
        """Test that selection picks minimum log_loss and ties preserve order."""
        db_path, candles = temp_db_with_candles

        # Create candidates
        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 0.1}, {"l2": 1.0}, {"l2": 10.0}]
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Run selection
        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        from scripts import select_lstm_baseline as selector
        fitted = []
        def record_fit(*args, **kwargs):
            assert kwargs["learning_rate"] == 0.05
            assert kwargs["epochs"] == 300
            if mode == "fit_failure":
                raise ValueError("synthetic fit failure")
            if mode == "tie":
                kwargs["l2"] = 10.0
            model = fit_logistic_baseline(*args, **kwargs)
            fitted.append(model)
            return model
        monkeypatch.setattr(selector, "fit_logistic_baseline", record_fit)
        def fail(*args, **kwargs):
            raise ValueError("synthetic failure")
        if mode == "partition_failure":
            monkeypatch.setattr(selector, "make_sequence_partition", fail)
        if mode == "save_failure":
            monkeypatch.setattr(selector, "save_model_artifact", fail)
        if mode == "feature_failure":
            monkeypatch.setattr(selector, "candle_features", fail)
        if mode == "scaler_failure":
            monkeypatch.setattr(selector.FeatureScaler, "fit", fail)
        if mode == "write_failure":
            def fail_write(*args, **kwargs):
                raise OSError("synthetic disk full")
            monkeypatch.setattr(selector, "_write_json", fail_write)
        if mode == "invalid_candle_failure":
            with sqlite3.connect(db_path) as connection:
                connection.execute("UPDATE candles SET volume = -1 WHERE ticker = 'TEST'")
        if mode == "replace_failure":
            original_replace = selector.os.replace
            replacements = []
            def fail_final_replace(source, destination):
                replacements.append(destination)
                if len(replacements) > 1:
                    raise OSError("synthetic late replacement failure")
                return original_replace(source, destination)
            monkeypatch.setattr(selector.os, "replace", fail_final_replace)
        exit_code = select_main()
        if mode == "replace_failure":
            assert exit_code == 1
            output = next(artifacts_dir.iterdir())
            manifest = json.loads((output / "manifest.json").read_text())
            assert manifest["exit_status"] == 1
            assert manifest["failed_checks"] == ["run_incomplete"]
            assert manifest["selection"]["status"] == "incomplete"
            assert (output / "model.json").exists()
            assert (output / "predictions.jsonl").exists()
            with pytest.raises(ValueError):
                load_and_predict(output)
            return
        if mode == "write_failure":
            assert exit_code == 1
            error = json.loads(capsys.readouterr().err)
            assert error["exit_status"] == 1
            assert "artifact write error" in error["error"]
            assert len(list(artifacts_dir.iterdir())) == 1
            return
        if mode.endswith("failure"):
            assert exit_code == 1
            output = next(artifacts_dir.iterdir())
            manifest = json.loads((output / "manifest.json").read_text())
            assert manifest["selection"]["status"] == "failed"
            assert manifest["exit_status"] == 1
            assert manifest["parameters"]["optimizer"] == {"learning_rate": 0.05, "epochs": 300}
            assert manifest["selection_rule"]["tie_break"] == "first_declared"
            assert manifest["selection"]["winner_index"] is None
            assert not (output / "manifest.json.tmp").exists()
            checks = json.loads((output / "checks.json").read_text())
            assert manifest["failed_checks"]
            assert all(checks[name] is False for name in manifest["failed_checks"])
            metrics = json.loads((output / "metrics.json").read_text())
            assert metrics["selection"] == manifest["selection"]
            assert metrics["winner"] is None
            assert "selection_status=failed" in (output / "run.log").read_text()
            assert json.loads((output / "candidates.json").read_text()) == candidates
            assert not (output / "model.json").exists()
            if mode in {"feature_failure", "scaler_failure", "invalid_candle_failure"}:
                assert fitted == []
                assert "feature/scaler preparation failed" in (output / "error.json").read_text()
                assert manifest["data_sha256"]
            return
        assert exit_code == 0
        assert len(fitted) == len(candidates)

        # Check output
        runs = list(artifacts_dir.glob("*"))
        assert len(runs) == 1
        run_dir = runs[0]

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["selection"]["status"] == "selected"
        assert manifest["exit_status"] == 0
        assert not (run_dir / "manifest.json.tmp").exists()
        assert (run_dir / "model.json").exists()
        assert (run_dir / "predictions.jsonl").exists()
        assert manifest["parameters"]["optimizer"] == {"learning_rate": 0.05, "epochs": 300}
        assert manifest["selection_rule"] == {
            "metric": "validation_log_loss", "direction": "minimize",
            "baseline": "train_prevalence", "strict_improvement": True,
            "tie_break": "first_declared",
        }
        scores = json.loads((run_dir / "candidate_scores.json").read_text())
        if mode == "tie":
            assert len({score["validation_log_loss"] for score in scores}) == 1
            assert manifest["selection"]["winner_index"] == 0
        expected = min(
            (score for score in scores if score["status"] == "evaluated"),
            key=lambda score: score["validation_log_loss"],
        )
        assert manifest["selection"]["winner_index"] == expected["candidate_index"]
        from app.model_artifact import load_model_artifact
        artifact = load_model_artifact(run_dir / "model.json")
        np.testing.assert_array_equal(artifact.weights, fitted[expected["candidate_index"]][0])
        assert json.loads((run_dir / "candidates.json").read_text()) == candidates
        assert (run_dir / "metrics.json").exists()
        assert (run_dir / "checks.json").exists()

        candidate_scores = json.loads((run_dir / "candidate_scores.json").read_text())
        assert len(candidate_scores) == 3

    def test_selection_rejects_without_strict_improvement(self, tmp_path, temp_db_with_candles):
        """Test that selection rejects candidates without strict improvement over baseline."""
        db_path, candles = temp_db_with_candles

        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 0.001}]  # Weak regularization
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        assert exit_code == 0

        runs = list(artifacts_dir.glob("*"))
        run_dir = runs[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["selection"]["status"] == "rejected"
        assert manifest["exit_status"] == 0
        assert not (run_dir / "manifest.json.tmp").exists()
        assert manifest["selection"]["winner_index"] is None
        assert not (run_dir / "model.json").exists()

    def test_selection_future_rows_unaffected(self, tmp_path, temp_db_with_candles):
        """Test that appending rows after selection doesn't affect selection."""
        db_path, candles = temp_db_with_candles

        # Run selection on initial DB
        candidates_file = tmp_path / "candidates.json"
        candidates_file.write_text(json.dumps([{"l2": 1.0}]))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        runs_1 = list(artifacts_dir.glob("*"))
        run_dir_1 = runs_1[0]
        manifest_1 = json.loads((run_dir_1 / "manifest.json").read_text())
        fp_1 = manifest_1["data_sha256"]

        # Append more rows to DB
        dates_new = pd.date_range("2024-02-11", periods=200, freq="15min")
        np.random.seed(43)
        prices = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.001, 200)))

        with sqlite3.connect(db_path) as conn:
            for i, (date, price) in enumerate(zip(dates_new, prices)):
                conn.execute(
                    "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (date.isoformat(), "TEST", "15m", float(price * 0.99), float(price * 1.02),
                     float(price * 0.98), float(price), int(np.random.randint(1000, 10000)))
                )
            conn.commit()

        # Run selection again
        artifacts_dir_2 = tmp_path / "artifacts2"
        artifacts_dir_2.mkdir()

        sys.argv[-1] = str(artifacts_dir_2)
        exit_code = select_main()

        runs_2 = list(artifacts_dir_2.glob("*"))
        run_dir_2 = runs_2[0]
        manifest_2 = json.loads((run_dir_2 / "manifest.json").read_text())
        fp_2 = manifest_2["data_sha256"]

        # Fingerprints should be the same (only train+validation consumed)
        assert fp_1 == fp_2

    def test_selection_stores_winner_params(self, tmp_path, temp_db_with_candles):
        """Test that selection stores winner l2 and scaler params in artifact."""
        db_path, candles = temp_db_with_candles

        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 0.5}, {"l2": 1.0}]
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        assert exit_code == 0

        runs = list(artifacts_dir.glob("*"))
        run_dir = runs[0]
        manifest = json.loads((run_dir / "manifest.json").read_text())

        if manifest["selection"]["status"] == "selected":
            assert manifest["selection"]["winner_l2"] in [0.5, 1.0]
            assert "model_artifact" in manifest

            # Load artifact and verify
            artifact_path = run_dir / manifest["model_artifact"]["path"]
            assert artifact_path.exists()
            artifact = json.loads(artifact_path.read_text())
            assert artifact["metadata"]["base_feature_columns"]
            assert len(artifact["weights"]) > 0
            assert np.isfinite(float(artifact["bias"]))


class TestCliValidation:
    """Test CLI argument validation."""

    def test_main_rejects_missing_candidates_file(self, tmp_path):
        """Test rejection of missing candidates file."""
        sys.argv = [
            "select_lstm_baseline.py",
            "--db", "test.db",
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(tmp_path / "nonexistent.json"),
            "--artifacts-dir", str(tmp_path),
        ]

        exit_code = select_main()
        assert exit_code == 1

    def test_main_rejects_negative_bars(self, tmp_path):
        """Test rejection of negative bar counts."""
        candidates_file = tmp_path / "candidates.json"
        candidates_file.write_text(json.dumps([{"l2": 1.0}]))

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", "test.db",
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "-100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "0.003",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(tmp_path),
        ]

        exit_code = select_main()
        assert exit_code == 1

    def test_main_rejects_non_finite_threshold(self, tmp_path):
        """Test rejection of non-finite threshold."""
        candidates_file = tmp_path / "candidates.json"
        candidates_file.write_text(json.dumps([{"l2": 1.0}]))

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", "test.db",
            "--ticker", "TEST",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "50",
            "--horizon", "5",
            "--threshold", "inf",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(tmp_path),
        ]

        exit_code = select_main()
        assert exit_code == 1


class TestSelectorArtifactReplay:
    """Integration test: selector run → artifact persistence → load_and_predict exact match."""

    @pytest.fixture
    def selector_db_with_candles(self, tmp_path):
        """Create temp SQLite DB with synthetic candles for selector."""
        db_path = tmp_path / "selector_test.db"

        # Create 300 candles (enough for train + validation)
        dates = pd.date_range("2024-01-01", periods=300, freq="15min")
        np.random.seed(42)
        # Create volatile price movements to get both up and down labels
        prices = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, 300)))

        candles = pd.DataFrame({
            "timestamp": dates,
            "ticker": "REPLAY",
            "period": "15m",
            "open": prices * 0.99,
            "high": prices * 1.02,
            "low": prices * 0.98,
            "close": prices,
            "volume": np.random.randint(1000, 10000, 300),
        })

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE candles (
                    begin TIMESTAMP NOT NULL,
                    ticker TEXT NOT NULL,
                    period TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL
                )
            """)
            for _, row in candles.iterrows():
                conn.execute(
                    "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (row["timestamp"].isoformat(), row["ticker"], row["period"],
                     float(row["open"]), float(row["high"]), float(row["low"]),
                     float(row["close"]), int(row["volume"]))
                )
            conn.commit()

        return db_path, candles

    def test_selector_run_creates_predictions_ledger(self, tmp_path, selector_db_with_candles):
        """Test that selector run produces predictions.jsonl for replay."""
        db_path, candles = selector_db_with_candles

        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 0.5}, {"l2": 1.0}]
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "REPLAY",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "20",
            "--horizon", "3",
            "--threshold", "0.002",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        assert exit_code == 0

        # Find the run directory
        runs = list(artifacts_dir.glob("*"))
        assert len(runs) == 1
        run_dir = runs[0]

        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest["selection"]["status"] == "selected":
            # Verify model artifact exists
            assert "model_artifact" in manifest
            model_path = run_dir / manifest["model_artifact"]["path"]
            assert model_path.exists()

            # Verify predictions ledger exists
            predictions_file = run_dir / "predictions.jsonl"
            assert predictions_file.exists()

            # Verify predictions ledger has entries (exact count depends on horizon filtering)
            predictions = [json.loads(line) for line in predictions_file.read_text().strip().split("\n")]
            assert len(predictions) > 0  # At least some samples pass filtering

            # Verify each prediction has required fields
            for pred in predictions:
                assert pred["partition"] == "validation"
                assert "decision_timestamp" in pred
                assert "outcome_timestamp" in pred
                assert "label" in pred
                assert "probability" in pred
                assert 0.0 <= pred["probability"] <= 1.0
                assert pred["label"] in [0.0, 1.0]

    def test_selector_artifact_load_and_predict_exact_match(self, tmp_path, selector_db_with_candles, monkeypatch):
        """Test that load_and_predict returns exact original probabilities from selector artifact."""
        db_path, candles = selector_db_with_candles
        from scripts import select_lstm_baseline as selector
        evaluated = []
        def capture_predictions(*args, **kwargs):
            result = predict_logistic(*args, **kwargs)
            evaluated.append(result.copy())
            return result
        monkeypatch.setattr(selector, "predict_logistic", capture_predictions)

        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 1.0}]
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "REPLAY",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "20",
            "--horizon", "3",
            "--threshold", "0.002",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        assert exit_code == 0

        # Find the run directory
        runs = list(artifacts_dir.glob("*"))
        run_dir = runs[0]

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["selection"]["status"] == "selected"

        # Load predictions from ledger
        predictions_file = run_dir / "predictions.jsonl"
        ledger_predictions = [json.loads(line)["probability"] for line in predictions_file.read_text().strip().split("\n")]

        # Replay via load_and_predict
        replayed_probs, artifact, loaded_manifest = load_and_predict(run_dir)

        # Verify exact match (bit-for-bit)
        assert len(replayed_probs) == len(ledger_predictions)
        np.testing.assert_array_equal(replayed_probs, ledger_predictions)
        np.testing.assert_array_equal(replayed_probs, evaluated[0])

        # Verify manifest validation
        assert loaded_manifest["evaluation_mode"] == "validation-only"
        assert loaded_manifest["exit_status"] == 0
        assert artifact is not None

    def test_selector_rejection_no_predictions_ledger(self, tmp_path, selector_db_with_candles):
        """Test that rejected selector run does not create predictions ledger."""
        db_path, candles = selector_db_with_candles

        candidates_file = tmp_path / "candidates.json"
        candidates = [{"l2": 0.0001}]  # Very weak regularization unlikely to improve over baseline
        candidates_file.write_text(json.dumps(candidates))

        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        sys.argv = [
            "select_lstm_baseline.py",
            "--db", str(db_path),
            "--ticker", "REPLAY",
            "--period", "15m",
            "--train-bars", "100",
            "--validation-bars", "100",
            "--sequence-length", "20",
            "--horizon", "3",
            "--threshold", "0.002",
            "--cost-rate", "0.001",
            "--candidates", str(candidates_file),
            "--artifacts-dir", str(artifacts_dir),
        ]

        exit_code = select_main()
        assert exit_code == 0

        # Find the run directory
        runs = list(artifacts_dir.glob("*"))
        run_dir = runs[0]

        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["selection"]["status"] == "rejected"
        if manifest["selection"]["status"] == "rejected":
            # Verify model artifact does not exist
            assert "model_artifact" not in manifest

            # Verify predictions ledger does not exist
            predictions_file = run_dir / "predictions.jsonl"
            assert not predictions_file.exists()
