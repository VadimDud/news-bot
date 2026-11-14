"""Integration and unit tests for model artifact persistence and replay."""

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.lstm_baseline import fit_logistic_baseline, predict_logistic
from app.lstm_features import FEATURE_COLUMNS, FeatureScaler, candle_features, make_sequence_partition
from app.model_artifact import (
    ModelArtifact,
    ModelArtifactMetadata,
    artifact_sha256,
    load_model_artifact,
    save_model_artifact,
)
from app.model_loader import load_and_predict, _fingerprint_frame
from scripts import run_lstm_baseline as runner


def make_test_candles(n=300, seed=42):
    """Generate synthetic OHLCV candles."""
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    rng = np.random.default_rng(seed)
    close = 100 + rng.normal(0, 0.5, n).cumsum()
    return pd.DataFrame(
        {"open": close - 0.2, "high": close + 1, "low": close - 1,
         "close": close, "volume": rng.uniform(100, 200, n)}, index=index
    )


class TestModelArtifactSaveLoad:
    """Unit tests for save and load functions."""

    def test_save_and_load_roundtrip(self):
        """Test exact round-trip: save, load, values match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # Create test data
            weights = np.array([0.5 - 0.05*i for i in range(500)])
            bias = 0.123
            mean = np.ones(10) * 2.0
            scale = np.ones(10) * 0.5
            scaler = FeatureScaler(mean=mean, scale=scale)
            
            # Save
            artifact_path, sha256_hex = save_model_artifact(
                output_path, weights, bias, scaler, sequence_length=50
            )
            
            # Load
            loaded = load_model_artifact(artifact_path)
            
            # Verify exact equality
            assert loaded.bias == bias
            assert loaded.sequence_length == 50
            assert np.array_equal(loaded.weights, weights)
            assert np.array_equal(loaded.scaler.mean, mean)
            assert np.array_equal(loaded.scaler.scale, scale)

    def test_save_rejects_existing_file(self):
        """Test exclusive write: cannot overwrite existing artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            weights = np.zeros(500)
            bias = 0.0
            scaler = FeatureScaler(mean=np.ones(10), scale=np.ones(10))
            
            # Save once
            save_model_artifact(output_path, weights, bias, scaler, sequence_length=50)
            
            # Try to save again - must fail
            with pytest.raises(FileExistsError, match="already exists"):
                save_model_artifact(output_path, weights, bias, scaler, sequence_length=50)

    def test_save_rejects_invalid_sequence_length(self):
        """Test validation: sequence_length must be positive integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            weights = np.zeros(500)
            bias = 0.0
            scaler = FeatureScaler(mean=np.ones(10), scale=np.ones(10))
            
            # Float sequence_length
            with pytest.raises(ValueError, match="must be integer"):
                save_model_artifact(output_path, weights, bias, scaler, sequence_length=50.5)
            
            # Zero sequence_length
            with pytest.raises(ValueError, match="must be positive"):
                save_model_artifact(output_path, weights, bias, scaler, sequence_length=0)
            
            # Negative sequence_length
            with pytest.raises(ValueError, match="must be positive"):
                save_model_artifact(output_path, weights, bias, scaler, sequence_length=-1)

    def test_save_rejects_non_finite_values(self):
        """Test validation: all values must be finite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir)
            
            # NaN in weights
            weights_nan = np.array([0.5 if i != 100 else np.nan for i in range(500)])
            bias = 0.0
            scaler = FeatureScaler(mean=np.ones(10), scale=np.ones(10))
            with pytest.raises(ValueError, match="must contain only finite"):
                save_model_artifact(output_path, weights_nan, bias, scaler, sequence_length=50)
            
            # Inf in bias
            weights = np.zeros(500)
            with pytest.raises(ValueError, match="must be finite"):
                save_model_artifact(output_path, weights, np.inf, scaler, sequence_length=50)
            
            # Non-positive scale
            scaler_bad_scale = FeatureScaler(mean=np.ones(10), scale=np.array([1.0]*9 + [0.0]))
            with pytest.raises(ValueError, match="must contain only positive"):
                save_model_artifact(output_path, weights, bias, scaler_bad_scale, sequence_length=50)

    def test_load_rejects_schema_version_mismatch(self):
        """Test validation: only schema_version 1.0 supported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_file = Path(tmpdir) / "model.json"
            data = {
                "metadata": {
                    "schema_version": "2.0",  # Wrong!
                    "base_feature_columns": list(("f1",) * 10),
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            artifact_file.write_text(json.dumps(data))
            
            with pytest.raises(ValueError, match="unsupported schema_version"):
                load_model_artifact(artifact_file)

    def test_load_rejects_feature_columns_mismatch(self):
        """Test validation: base_feature_columns must match FEATURE_COLUMNS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_file = Path(tmpdir) / "model.json"
            data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10"],
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            artifact_file.write_text(json.dumps(data))
            
            with pytest.raises(ValueError, match="do not match expected"):
                load_model_artifact(artifact_file)

    def test_load_rejects_invalid_scale_positivity(self):
        """Test validation: scale must be strictly positive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_file = Path(tmpdir) / "model.json"
            from app.lstm_features import FEATURE_COLUMNS
            data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": list(FEATURE_COLUMNS),
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 9 + [0.0],  # One zero scale!
            }
            artifact_file.write_text(json.dumps(data))
            
            with pytest.raises(ValueError, match="must contain only positive"):
                load_model_artifact(artifact_file)


class TestLoaderReplayValidation:
    """Integration tests: runner -> artifact -> loader replay."""

    def test_runner_and_loader_exact_probability_match(self):
        """Test full replay: runner creates artifact, loader reproduces exact validation probs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            artifacts_dir = Path(tmpdir) / "artifacts"
            
            # Create test database with proper schema
            candles = make_test_candles(n=150)
            with sqlite3.connect(db_path) as conn:
                # Create table first
                conn.execute(
                    "CREATE TABLE candles (ticker TEXT, period TEXT, begin TIMESTAMP, "
                    "open REAL, high REAL, low REAL, close REAL, volume REAL)"
                )
                # Insert data using raw SQL
                for idx, row in candles.iterrows():
                    conn.execute(
                        "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("DEMO", "1h", idx.isoformat(), row["open"], row["high"], 
                         row["low"], row["close"], row["volume"])
                    )
                conn.commit()
            
            # Run validation-only mode
            import argparse
            args = argparse.Namespace(
                db=str(db_path),
                ticker="demo",
                period="1h",
                train_bars=50,
                validation_bars=20,
                sequence_length=20,
                horizon=3,
                threshold=0.0,
                cost_rate=0.0,
                artifacts_dir=str(artifacts_dir),
                validation_only=True,
                test_bars=None,
                forward_bars=0,
            )
            
            # Run
            exit_status = runner._validate_and_run_validation_only(args)
            assert exit_status == 0
            
            # Find the run directory
            run_dirs = list(artifacts_dir.glob("*_validation_only"))
            assert len(run_dirs) == 1
            run_dir = run_dirs[0]
            
            # Load predictions from predictions.jsonl
            predictions_file = run_dir / "predictions.jsonl"
            original_probs = []
            with predictions_file.open() as f:
                for line in f:
                    pred = json.loads(line)
                    original_probs.append(pred["probability"])
            original_probs = np.array(original_probs)
            
            # Load via loader and regenerate
            loaded_probs, artifact, manifest = load_and_predict(run_dir)
            
            # Must match exactly (within floating point precision)
            np.testing.assert_allclose(
                loaded_probs[:len(original_probs)],
                original_probs,
                rtol=1e-10,
                atol=1e-14,
            )

    def test_loader_rejects_non_validation_only_run(self):
        """Test validation: loader rejects non-validation-only manifests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            
            # Create manifest for walk-forward run (not validation-only)
            manifest = {
                "evaluation_mode": "walk-forward",
                "exit_status": 0,
                "model_artifact": {"sha256": "abc123", "path": "model.json"},
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create dummy model.json
            from app.lstm_features import FEATURE_COLUMNS
            model_data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": list(FEATURE_COLUMNS),
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            (run_dir / "model.json").write_text(json.dumps(model_data))
            
            with pytest.raises(ValueError, match="not validation-only mode"):
                load_and_predict(run_dir)

    def test_loader_rejects_failed_run(self):
        """Test validation: loader rejects manifests with non-zero exit_status before DB access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            
            # Create manifest for failed run (exit_status should be checked before DB)
            manifest = {
                "evaluation_mode": "validation-only",
                "exit_status": 1,  # Failed!
                "model_artifact": {"sha256": "abc123", "path": "model.json"},
                "data_source": {"database": "/nonexistent/path/test.db"},  # Irrelevant path
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create dummy model.json so FileNotFoundError doesn't occur first
            from app.lstm_features import FEATURE_COLUMNS
            model_data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": list(FEATURE_COLUMNS),
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            payload = json.dumps(model_data, sort_keys=True)
            (run_dir / "model.json").write_text(payload)
            
            # Loader should reject due to exit_status (before DB access)
            with pytest.raises(ValueError, match="did not complete successfully"):
                load_and_predict(run_dir)

    def test_loader_rejects_model_hash_mismatch(self):
        """Test validation: loader rejects if model.json SHA256 doesn't match manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            
            # Create manifest with wrong SHA256
            manifest = {
                "evaluation_mode": "validation-only",
                "exit_status": 0,
                "model_artifact": {"sha256": "wrong_hash_12345", "path": "model.json"},
                "resolved_boundaries": {
                    "train": {"row_end": 50},
                    "validation": {"row_end": 70},
                },
                "parameters": {
                    "train_bars": 50,
                    "validation_bars": 20,
                    "sequence_length": 50,
                    "horizon": 5,
                    "threshold": 0.0,
                    "cost_rate": 0.0,
                },
                "data_sha256": "some_hash",
                "loaded_rows": 70,
                "ticker": "DEMO",
                "period": "1h",
                "data_source": {"database": "/tmp/test.db"},
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create real model.json with different content
            from app.lstm_features import FEATURE_COLUMNS
            model_data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": list(FEATURE_COLUMNS),
                    "sequence_length": 50,
                    "feature_count": 500,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 500,
                },
                "weights": [0.1] * 500,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            (run_dir / "model.json").write_text(json.dumps(model_data, sort_keys=True))
            
            with pytest.raises(ValueError, match="SHA256 mismatch"):
                load_and_predict(run_dir)

    def test_loader_rejects_data_fingerprint_mismatch(self):
        """Test validation: loader rejects if candles data has changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            run_dir = Path(tmpdir) / "run"
            run_dir.mkdir()
            
            # Create database with original candles using SQL
            candles = make_test_candles(n=70)
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE candles (ticker TEXT, period TEXT, begin TIMESTAMP, "
                    "open REAL, high REAL, low REAL, close REAL, volume REAL)"
                )
                for idx, row in candles.iterrows():
                    conn.execute(
                        "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("DEMO", "1h", idx.isoformat(), row["open"], row["high"], 
                         row["low"], row["close"], row["volume"])
                    )
                conn.commit()
            
            # Compute original fingerprint
            original_fp = _fingerprint_frame(candles)
            
            # Modify database (change prices)
            candles_modified = candles.copy()
            candles_modified.iloc[0, candles_modified.columns.get_loc("close")] = 999.9
            with sqlite3.connect(db_path) as conn:
                conn.execute("DELETE FROM candles")
                for idx, row in candles_modified.iterrows():
                    conn.execute(
                        "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("DEMO", "1h", idx.isoformat(), row["open"], row["high"], 
                         row["low"], row["close"], row["volume"])
                    )
                conn.commit()
            
            # Create manifest with original fingerprint
            from app.lstm_features import FEATURE_COLUMNS
            manifest = {
                "evaluation_mode": "validation-only",
                "exit_status": 0,
                "model_artifact": {"sha256": "valid_hash", "path": "model.json"},
                "resolved_boundaries": {
                    "train": {"row_end": 50},
                    "validation": {"row_end": 70},
                },
                "parameters": {
                    "train_bars": 50,
                    "validation_bars": 20,
                    "sequence_length": 20,
                    "horizon": 3,
                    "threshold": 0.0,
                    "cost_rate": 0.0,
                },
                "data_sha256": original_fp,  # Original fingerprint (mismatched now)
                "loaded_rows": 70,
                "ticker": "DEMO",
                "period": "1h",
                "data_source": {"database": str(db_path)},
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create valid model.json
            model_data = {
                "metadata": {
                    "schema_version": "1.0",
                    "base_feature_columns": list(FEATURE_COLUMNS),
                    "sequence_length": 20,
                    "feature_count": 200,
                    "scaler_mean_count": 10,
                    "scaler_scale_count": 10,
                    "weights_count": 200,
                },
                "weights": [0.1] * 200,
                "bias": 0.0,
                "scaler_mean": [1.0] * 10,
                "scaler_scale": [1.0] * 10,
            }
            payload = json.dumps(model_data, sort_keys=True)
            (run_dir / "model.json").write_text(payload)
            
            # Compute and update manifest with correct model hash
            model_hash = hashlib.sha256(payload.encode()).hexdigest()
            manifest["model_artifact"]["sha256"] = model_hash
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Try to load - should fail due to fingerprint mismatch
            with pytest.raises(ValueError, match="data SHA256 mismatch"):
                load_and_predict(run_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
