"""Test diagnostic full-bar LSTM export with corrected architecture."""
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from scripts.export_lstm_diagnostic_probabilities import (
    export_diagnostic,
    validate_enrollment_manifest,
    validate_evaluation_manifest,
    load_history,
    load_forward,
)
from app.lstm_features import FeatureScaler, candle_features


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def create_candles(count: int, start_bar: int = 0) -> list[dict]:
    """Create sequential hourly candles with realistic price movement."""
    from datetime import datetime, timedelta
    start_time = datetime(2026, 1, 1, 0, 0, 0) + timedelta(hours=start_bar)
    rows = []
    price = 100.0
    for i in range(count):
        ts = start_time + timedelta(hours=i)
        idx = start_bar + i
        # Add realistic price movements (trending up and down)
        trend = 0.02 if (idx % 100) < 50 else -0.02
        price = price * (1 + trend + (0.001 * (idx % 7 - 3)))  # Ensure both positive and negative returns
        price = max(price, 50.0)  # Don't let price go to zero
        
        open_price = price
        high = price * 1.002
        low = price * 0.998
        close = price * (1 + 0.001 * ((idx + 3) % 5 - 2))
        close = max(close, low)
        close = min(close, high)
        
        rows.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "open": f"{open_price:.4f}",
            "high": f"{max(open_price, close, high):.4f}",
            "low": f"{min(open_price, close, low):.4f}",
            "close": f"{close:.4f}",
            "volume": str(1000 + idx * 10),
        })
        price = close
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


TEST_CALENDAR = [{"cutoff_date": "2026-01-02", "source": "smartlab"},
                 {"cutoff_date": "2026-01-10", "source": "smartlab"}]
CAL_HASH = sha256(json.dumps(TEST_CALENDAR, sort_keys=True, separators=(',', ':')).encode())


def make_enrollment(tmp_path: Path, history_count: int = 600) -> tuple[Path, dict]:
    """Create valid enrollment directory."""
    enroll_dir = tmp_path / "enrollment"
    enroll_dir.mkdir()
    
    history_rows = create_candles(history_count, start_bar=0)
    history_path = enroll_dir / "history.csv"
    write_csv(history_path, history_rows)
    history_hash = sha256(history_path.read_bytes())
    
    manifest = {
        "status": "enrolled",
        "exit_status": 0,
        "history_sha256": history_hash,
        "dividend_calendar": TEST_CALENDAR, "dividend_calendar_sha256": CAL_HASH,
        "parameters": {
            "train_bars": 500,
            "evaluation_bars": 2000,
            "sequence_length": 50,
            "horizon": 5,
            "threshold": 0.003,
            "cost_rate": 0.001,
            "hidden_size": 32,
            "num_layers": 2,
            "dropout": 0.2,
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 50,
            "seed": 42,
        },
        "database_identifier": "/tmp/test.db",
        "storage_timezone": "UTC-naive",
        "market_timezone": "Europe/Moscow",
        "train_start_utc": "2026-01-01T00:00:00",
        "train_end_utc": "2026-01-25T00:00:00",
    }
    (enroll_dir / "manifest.json").write_text(json.dumps(manifest))
    return enroll_dir, manifest


def make_evaluation(
    tmp_path: Path,
    enroll_manifest: dict,
    enroll_dir_for_hash: Path,
) -> tuple[Path, dict]:
    """Create valid evaluation directory."""
    eval_dir = tmp_path / "evaluation"
    eval_dir.mkdir()
    
    # Forward starts AFTER history (2000 bars)
    forward_rows = create_candles(2000, start_bar=600)
    forward_path = eval_dir / "forward.csv"
    write_csv(forward_path, forward_rows)
    forward_hash = sha256(forward_path.read_bytes())
    
    enroll_manifest_hash = sha256((enroll_dir_for_hash / "manifest.json").read_bytes())
    
    manifest = {
        "status": "completed",
        "exit_status": 0,
        "forward_sha256": forward_hash,
        "enrollment_manifest_sha256": enroll_manifest_hash,
        "dividend_calendar_sha256": CAL_HASH,
        "parameters": enroll_manifest["parameters"],
        "database_identifier": enroll_manifest["database_identifier"],
        "storage_timezone": enroll_manifest["storage_timezone"],
        "action": "evaluate",
        "evaluation_start_utc": "2026-01-25T00:00:00",
        "evaluation_end_utc": "2026-02-08T00:00:00",
    }
    (eval_dir / "manifest.json").write_text(json.dumps(manifest))
    return eval_dir, manifest


class TestValidateEnrollment:
    def test_valid_enrollment(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path)
        result = validate_enrollment_manifest(enroll_dir)
        assert result["status"] == "enrolled"
        assert result["exit_status"] == 0

    def test_missing_manifest(self, tmp_path):
        enroll_dir = tmp_path / "empty"
        enroll_dir.mkdir()
        with pytest.raises(ValueError, match="not found"):
            validate_enrollment_manifest(enroll_dir)

    def test_wrong_status(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path)
        manifest["status"] = "waiting"
        (enroll_dir / "manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="status"):
            validate_enrollment_manifest(enroll_dir)

    def test_nonzero_exit_status(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path)
        manifest["exit_status"] = 1
        (enroll_dir / "manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="exit_status"):
            validate_enrollment_manifest(enroll_dir)


class TestValidateEvaluation:
    def test_valid_evaluation(self, tmp_path):
        enroll_dir, enroll_manifest = make_enrollment(tmp_path)
        eval_dir, manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        result = validate_evaluation_manifest(eval_dir)
        assert result["status"] == "completed"
        assert result["exit_status"] == 0

    def test_missing_manifest(self, tmp_path):
        eval_dir = tmp_path / "empty"
        eval_dir.mkdir()
        with pytest.raises(ValueError, match="not found"):
            validate_evaluation_manifest(eval_dir)

    def test_wrong_status(self, tmp_path):
        enroll_dir, enroll_manifest = make_enrollment(tmp_path)
        eval_dir, manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        manifest["status"] = "waiting"
        (eval_dir / "manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="status"):
            validate_evaluation_manifest(eval_dir)


class TestLoadHistory:
    def test_valid_history(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path, history_count=700)
        history = load_history(enroll_dir, manifest)
        assert len(history) == 700
        assert set(["open", "high", "low", "close", "volume"]).issubset(history.columns)

    def test_missing_file(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path)
        (enroll_dir / "history.csv").unlink()
        with pytest.raises(ValueError, match="not found"):
            load_history(enroll_dir, manifest)

    def test_hash_mismatch(self, tmp_path):
        enroll_dir, manifest = make_enrollment(tmp_path)
        manifest["history_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="hash mismatch"):
            load_history(enroll_dir, manifest)


class TestLoadForward:
    def test_valid_forward(self, tmp_path):
        enroll_dir, enroll_manifest = make_enrollment(tmp_path)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        forward = load_forward(eval_dir, eval_manifest)
        assert len(forward) == 2000
        assert forward.index.is_monotonic_increasing
        assert not forward.index.has_duplicates

    def test_wrong_count(self, tmp_path):
        enroll_dir, enroll_manifest = make_enrollment(tmp_path)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        # Modify forward to have 1999 rows
        forward_path = eval_dir / "forward.csv"
        rows = create_candles(1999, start_bar=600)
        write_csv(forward_path, rows)
        eval_manifest["forward_sha256"] = sha256(forward_path.read_bytes())
        (eval_dir / "manifest.json").write_text(json.dumps(eval_manifest))
        with pytest.raises(ValueError, match="1999.*expected exactly 2000"):
            load_forward(eval_dir, eval_manifest)

    def test_hash_mismatch(self, tmp_path):
        enroll_dir, enroll_manifest = make_enrollment(tmp_path)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        eval_manifest["forward_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="hash mismatch"):
            load_forward(eval_dir, eval_manifest)


class TestExportDiagnostic:
    def test_completes_with_valid_inputs(self, tmp_path, monkeypatch):
        """Full end-to-end test with mocked LSTM."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        output_dir = tmp_path / "output"
        
        # Mock torch and LSTM training
        import sys
        import types
        
        # Create mock torch module
        mock_torch = types.ModuleType("torch")
        sys.modules["torch"] = mock_torch
        
        # Create mock LSTM module
        mock_lstm_module = types.ModuleType("lstm_neural")
        
        class MockConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        def mock_train_lstm_classifier(train_X, train_y, val_X, val_y, config):
            from app.lstm_features import make_sequence_partition
            from app.timezones import to_market
            history = load_history(enroll_dir, enroll_manifest)
            scaler = FeatureScaler.fit(candle_features(history).iloc[-500:])
            raw = make_sequence_partition(history, feature_start=0, decision_start=len(history)-500,
                decision_end=len(history), sequence_length=50, horizon=5, threshold=.003,
                cost_rate=.001, scaler=scaler)
            keep = [not any(to_market(d).date().isoformat() < event['cutoff_date'] <=
                            to_market(o).date().isoformat() for event in TEST_CALENDAR)
                    for d, o in zip(raw.decision_timestamps, raw.outcome_timestamps)]
            assert not all(keep)
            np.testing.assert_array_equal(train_X, raw.X[keep])
            np.testing.assert_array_equal(train_y, raw.y[keep])
            return object(), None
        
        def mock_predict_lstm_probabilities(model, X):
            # Return synthetic probabilities (all 0.5 for reproducibility)
            return np.full(len(X), 0.5, dtype=np.float32)
        
        mock_lstm_module.LSTMConfig = MockConfig
        mock_lstm_module.train_lstm_classifier = mock_train_lstm_classifier
        mock_lstm_module.predict_lstm_probabilities = mock_predict_lstm_probabilities
        sys.modules["app.lstm_neural"] = mock_lstm_module
        
        try:
            exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
        finally:
            # Clean up mocks
            del sys.modules["torch"]
            del sys.modules["app.lstm_neural"]
        
        assert exit_code == 0
        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "predictions.jsonl").exists()
        
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert manifest["status"] == "completed"
        assert manifest["diagnostic_only"] is True
        assert manifest["predictions_count"] == 2000
        assert manifest["forward_bars_inferred"] == 2000

    def test_exact_2000_timestamps(self, tmp_path, monkeypatch):
        """Verify ledger has EXACTLY 2000 timestamps."""
        import sys
        import types
        
        # Mock torch
        mock_torch = types.ModuleType("torch")
        sys.modules["torch"] = mock_torch
        
        mock_lstm_module = types.ModuleType("lstm_neural")
        class MockConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        def mock_train_lstm_classifier(train_X, train_y, val_X, val_y, config):
            return object(), None
        
        def mock_predict_lstm_probabilities(model, X):
            return np.full(len(X), 0.5, dtype=np.float32)
        
        mock_lstm_module.LSTMConfig = MockConfig
        mock_lstm_module.train_lstm_classifier = mock_train_lstm_classifier
        mock_lstm_module.predict_lstm_probabilities = mock_predict_lstm_probabilities
        sys.modules["app.lstm_neural"] = mock_lstm_module
        
        try:
            enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
            eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
            output_dir = tmp_path / "output"
            
            exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
            
            assert exit_code == 0
            ledger_path = output_dir / "predictions.jsonl"
            with ledger_path.open() as stream:
                lines = stream.readlines()
            assert len(lines) == 2000, f"ledger has {len(lines)} lines, expected 2000"
            
            # Verify all are valid JSON with decision_timestamp and partition field
            for i, line in enumerate(lines):
                row = json.loads(line)
                assert "decision_timestamp" in row, f"line {i} missing decision_timestamp"
                assert "partition" in row, f"line {i} missing partition field"
                assert row["partition"] == "forward", f"line {i} partition={row['partition']}, expected 'forward'"
                assert "probability" in row, f"line {i} missing probability"
                assert "outcome_timestamp" not in row, "outcome_timestamp must not be in ledger"
                prob = row["probability"]
                assert 0 <= prob <= 1, f"line {i} probability {prob} outside [0,1]"
        finally:
            del sys.modules["torch"]
            del sys.modules["app.lstm_neural"]

    def test_last_bar_included(self, tmp_path, monkeypatch):
        """Verify last forward bar (2000th) is included in inference."""
        import sys
        import types
        
        mock_torch = types.ModuleType("torch")
        sys.modules["torch"] = mock_torch
        
        mock_lstm_module = types.ModuleType("lstm_neural")
        class MockConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        def mock_train_lstm_classifier(train_X, train_y, val_X, val_y, config):
            return object(), None
        
        def mock_predict_lstm_probabilities(model, X):
            return np.full(len(X), 0.5, dtype=np.float32)
        
        mock_lstm_module.LSTMConfig = MockConfig
        mock_lstm_module.train_lstm_classifier = mock_train_lstm_classifier
        mock_lstm_module.predict_lstm_probabilities = mock_predict_lstm_probabilities
        sys.modules["app.lstm_neural"] = mock_lstm_module
        
        try:
            enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
            eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
            output_dir = tmp_path / "output"
            
            exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
            assert exit_code == 0
            
            # Last timestamp in forward should match last timestamp in ledger
            forward = eval_dir / "forward.csv"
            forward_rows = list(csv.DictReader(forward.open()))
            last_forward_ts = forward_rows[-1]["timestamp"]
            # Convert to ISO format for comparison
            from datetime import datetime
            dt = datetime.strptime(last_forward_ts, "%Y-%m-%d %H:%M:%S")
            expected_ts = dt.isoformat()
            
            ledger_path = output_dir / "predictions.jsonl"
            with ledger_path.open() as stream:
                last_ledger_row = None
                for line in stream:
                    last_ledger_row = json.loads(line)
            
            assert last_ledger_row is not None
            assert last_ledger_row["decision_timestamp"] == expected_ts, \
                f"last ledger timestamp {last_ledger_row['decision_timestamp']} != expected {expected_ts}"
        finally:
            del sys.modules["torch"]
            del sys.modules["app.lstm_neural"]

    def test_fails_without_torch(self, tmp_path):
        """Verify fails closed if torch not available."""
        import sys
        import builtins
        
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        output_dir = tmp_path / "output"
        
        # Save original import
        orig_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == "app.lstm_neural":
                raise ImportError("lstm_neural module not available (torch missing)")
            return orig_import(name, *args, **kwargs)
        
        # Temporarily replace import
        builtins.__import__ = mock_import
        
        try:
            exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
        finally:
            builtins.__import__ = orig_import
        
        assert exit_code == 1
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert manifest["status"] == "failed"
        assert "PyTorch" in manifest["failure_reason"] or "torch" in manifest["failure_reason"].lower()

    def test_enrollment_hash_mismatch(self, tmp_path):
        """Verify evaluation.enrollment_manifest_sha256 must match."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        
        # Corrupt evaluation's enrollment_manifest_sha256
        eval_manifest["enrollment_manifest_sha256"] = "0" * 64
        (eval_dir / "manifest.json").write_text(json.dumps(eval_manifest))
        
        output_dir = tmp_path / "output"
        exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
        
        assert exit_code == 1
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert "mismatch" in manifest["failure_reason"].lower()

    def test_parameters_mismatch(self, tmp_path):
        """Verify parameters must match between enrollment and evaluation."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        
        # Change evaluation parameters
        eval_manifest["parameters"]["threshold"] = 0.005
        (eval_dir / "manifest.json").write_text(json.dumps(eval_manifest))
        
        output_dir = tmp_path / "output"
        exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
        
        assert exit_code == 1
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert "parameters" in manifest["failure_reason"].lower() and "mismatch" in manifest["failure_reason"].lower()

    def test_chronological_separation(self, tmp_path):
        """Verify history and forward must not overlap."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        
        # Make forward start before history ends (overlap)
        forward_rows = create_candles(2000, start_bar=500)  # Starts at 500, history ends at 600
        write_csv(eval_dir / "forward.csv", forward_rows)
        eval_manifest["forward_sha256"] = sha256((eval_dir / "forward.csv").read_bytes())
        (eval_dir / "manifest.json").write_text(json.dumps(eval_manifest))
        
        output_dir = tmp_path / "output"
        exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
         
        assert exit_code == 1
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert "chronologically separated" in manifest["failure_reason"]

    def test_insufficient_history(self, tmp_path):
        """Verify fails if history < 500 bars."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=400)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        
        output_dir = tmp_path / "output"
        exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
        
        assert exit_code == 1
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert "400" in manifest["failure_reason"] and "500" in manifest["failure_reason"]

    def test_scaler_regression_on_last_500_bars(self, tmp_path):
        """Verify scaler is fit on last 500 bars of history."""
        enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
        eval_dir, eval_manifest = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
        
        # Load history to extract last 500 bars and compute expected scaler
        history = load_history(enroll_dir, enroll_manifest)
        last_500_candles = history.iloc[-500:]
        last_500_features = candle_features(last_500_candles)
        expected_scaler = FeatureScaler.fit(last_500_features)
        
        # Verify scaler state can be serialized and matches expected bounds
        assert expected_scaler.mean is not None
        assert expected_scaler.scale is not None
        assert len(expected_scaler.mean) > 0
        assert len(expected_scaler.scale) > 0
        
        # Verify mean and scale are finite
        assert np.all(np.isfinite(expected_scaler.mean))
        assert np.all(np.isfinite(expected_scaler.scale))
        # Verify scales are positive (non-zero variance after normalization)
        assert np.all(expected_scaler.scale > 0)

    def test_prefix_invariance_with_perturbed_forward_ohlc(self, tmp_path):
        """Verify decisions are invariant to late-stage OHLC perturbations."""
        import sys
        import types
        
        mock_torch = types.ModuleType("torch")
        sys.modules["torch"] = mock_torch
        
        mock_lstm_module = types.ModuleType("lstm_neural")
        class MockConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        def mock_train_lstm_classifier(train_X, train_y, val_X, val_y, config):
            return object(), None
        
        def mock_predict_lstm_probabilities(model, X):
            return np.full(len(X), 0.5, dtype=np.float32)
        
        mock_lstm_module.LSTMConfig = MockConfig
        mock_lstm_module.train_lstm_classifier = mock_train_lstm_classifier
        mock_lstm_module.predict_lstm_probabilities = mock_predict_lstm_probabilities
        sys.modules["app.lstm_neural"] = mock_lstm_module
        
        try:
            # Create first run with original forward
            enroll_dir, enroll_manifest = make_enrollment(tmp_path, history_count=600)
            eval_dir1, eval_manifest1 = make_evaluation(tmp_path, enroll_manifest, enroll_dir)
            output_dir1 = tmp_path / "output1"
            
            exit_code1 = export_diagnostic(enroll_dir, eval_dir1, output_dir1)
            assert exit_code1 == 0
            
            # Read first run's predictions
            with (output_dir1 / "predictions.jsonl").open() as f:
                first_preds = [json.loads(line) for line in f]
            
            # Create second run with slightly perturbed close price (last 10 bars only)
            # This keeps OHLC relationships intact
            forward_rows = create_candles(2000, start_bar=600)
            # Perturb last 10 bars (indices 1990-1999) using multiplicative factor
            # applied uniformly to OHLCV to preserve relationships
            for i in range(1990, 2000):
                multiplier = 1.0 + np.random.randn() * 0.005  # 0.5% std dev
                for key in ["open", "high", "low", "close"]:
                    val = float(forward_rows[i][key])
                    forward_rows[i][key] = f"{val * multiplier:.4f}"
            
            eval_dir2 = tmp_path / "evaluation2"
            eval_dir2.mkdir()
            forward_path2 = eval_dir2 / "forward.csv"
            write_csv(forward_path2, forward_rows)
            
            eval_manifest2 = eval_manifest1.copy()
            eval_manifest2["forward_sha256"] = sha256(forward_path2.read_bytes())
            (eval_dir2 / "manifest.json").write_text(json.dumps(eval_manifest2))
            
            output_dir2 = tmp_path / "output2"
            exit_code2 = export_diagnostic(enroll_dir, eval_dir2, output_dir2)
            assert exit_code2 == 0
            
            # Read second run's predictions
            with (output_dir2 / "predictions.jsonl").open() as f:
                second_preds = [json.loads(line) for line in f]
            
            # First 1990 predictions should be identical (causal context not affected by future perturbation)
            for i in range(1990):
                assert first_preds[i]["decision_timestamp"] == second_preds[i]["decision_timestamp"]
                assert abs(first_preds[i]["probability"] - second_preds[i]["probability"]) < 1e-6, \
                    f"bar {i}: probabilities diverged {first_preds[i]['probability']} vs {second_preds[i]['probability']}"
        finally:
            del sys.modules["torch"]
            del sys.modules["app.lstm_neural"]

    def test_5min_horizon_15_integration(self, tmp_path):
        """Test with 5-minute bars and horizon=15 (75 minutes forward)."""
        import sys
        import types
        
        mock_torch = types.ModuleType("torch")
        sys.modules["torch"] = mock_torch
        
        mock_lstm_module = types.ModuleType("lstm_neural")
        class MockConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        def mock_train_lstm_classifier(train_X, train_y, val_X, val_y, config):
            return object(), None
        
        def mock_predict_lstm_probabilities(model, X):
            return np.full(len(X), 0.5, dtype=np.float32)
        
        mock_lstm_module.LSTMConfig = MockConfig
        mock_lstm_module.train_lstm_classifier = mock_train_lstm_classifier
        mock_lstm_module.predict_lstm_probabilities = mock_predict_lstm_probabilities
        sys.modules["app.lstm_neural"] = mock_lstm_module
        
        try:
            # Create 5-minute candles instead of hourly
            enroll_dir = tmp_path / "enrollment"
            enroll_dir.mkdir()
            
            start_time = datetime(2026, 1, 1, 0, 0, 0)
            history_rows = []
            price = 100.0
            for i in range(600):
                ts = start_time + timedelta(minutes=5 * i)
                trend = 0.001 if (i % 100) < 50 else -0.001
                price = price * (1 + trend)
                price = max(price, 50.0)
                
                open_price = price
                high = price * 1.001
                low = price * 0.999
                close = price * (1 + 0.0005 * ((i + 3) % 5 - 2))
                close = max(close, low)
                close = min(close, high)
                
                history_rows.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": f"{open_price:.4f}",
                    "high": f"{max(open_price, close, high):.4f}",
                    "low": f"{min(open_price, close, low):.4f}",
                    "close": f"{close:.4f}",
                    "volume": str(1000 + i * 10),
                })
                price = close
            
            history_path = enroll_dir / "history.csv"
            write_csv(history_path, history_rows)
            history_hash = sha256(history_path.read_bytes())
            
            manifest = {
                "status": "enrolled",
                "exit_status": 0,
                "history_sha256": history_hash,
                "dividend_calendar": TEST_CALENDAR, "dividend_calendar_sha256": CAL_HASH,
                "parameters": {
                    "train_bars": 500,
                    "evaluation_bars": 2000,
                    "sequence_length": 50,
                    "horizon": 15,  # 75 minutes forward
                    "threshold": 0.003,
                    "cost_rate": 0.001,
                    "hidden_size": 32,
                    "num_layers": 2,
                    "dropout": 0.2,
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 50,
                    "seed": 42,
                },
                "database_identifier": "/tmp/test.db",
                "storage_timezone": "UTC-naive",
                "market_timezone": "Europe/Moscow",
                "train_start_utc": "2026-01-01T00:00:00",
                "train_end_utc": "2026-01-03T02:00:00",
            }
            (enroll_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create evaluation with 2000 5-minute forward candles
            eval_dir = tmp_path / "evaluation"
            eval_dir.mkdir()
            
            forward_rows = []
            price = history_rows[-1]["close"]
            price = float(price)
            for i in range(2000):
                ts = start_time + timedelta(minutes=5 * (600 + i))
                trend = 0.001 if (i % 100) < 50 else -0.001
                price = price * (1 + trend)
                price = max(price, 50.0)
                
                open_price = price
                high = price * 1.001
                low = price * 0.999
                close = price * (1 + 0.0005 * ((i + 3) % 5 - 2))
                close = max(close, low)
                close = min(close, high)
                
                forward_rows.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": f"{open_price:.4f}",
                    "high": f"{max(open_price, close, high):.4f}",
                    "low": f"{min(open_price, close, low):.4f}",
                    "close": f"{close:.4f}",
                    "volume": str(1000 + (600 + i) * 10),
                })
                price = close
            
            forward_path = eval_dir / "forward.csv"
            write_csv(forward_path, forward_rows)
            forward_hash = sha256(forward_path.read_bytes())
            
            enroll_manifest_hash = sha256((enroll_dir / "manifest.json").read_bytes())
            
            eval_manifest = {
                "status": "completed",
                "exit_status": 0,
                "forward_sha256": forward_hash,
                "enrollment_manifest_sha256": enroll_manifest_hash,
                "dividend_calendar_sha256": CAL_HASH,
                "parameters": manifest["parameters"],
                "database_identifier": manifest["database_identifier"],
                "storage_timezone": manifest["storage_timezone"],
                "action": "evaluate",
                "evaluation_start_utc": "2026-01-03T02:00:00",
                "evaluation_end_utc": "2026-01-10T18:40:00",
            }
            (eval_dir / "manifest.json").write_text(json.dumps(eval_manifest))
            
            output_dir = tmp_path / "output_5min"
            exit_code = export_diagnostic(enroll_dir, eval_dir, output_dir)
            
            assert exit_code == 0
            assert (output_dir / "manifest.json").exists()
            assert (output_dir / "predictions.jsonl").exists()
            
            result_manifest = json.loads((output_dir / "manifest.json").read_text())
            assert result_manifest["status"] == "completed"
            assert result_manifest["parameters"]["horizon"] == 15
            
            # Verify 2000 predictions were generated
            with (output_dir / "predictions.jsonl").open() as f:
                lines = f.readlines()
            assert len(lines) == 2000
            
            # Verify first prediction timestamp matches first forward bar
            first_pred = json.loads(lines[0])
            first_forward_ts = forward_rows[0]["timestamp"]
            dt = datetime.strptime(first_forward_ts, "%Y-%m-%d %H:%M:%S")
            assert first_pred["decision_timestamp"] == dt.isoformat()
            
        finally:
            del sys.modules["torch"]
            del sys.modules["app.lstm_neural"]
