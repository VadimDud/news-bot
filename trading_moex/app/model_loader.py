"""Helper to load and apply persisted LSTM baseline model artifacts.

This module provides utilities to replay validation-only runs by loading
persisted model artifacts and generating exact validation probabilities.

The loader validates manifest, model hash, and dataset fingerprint to ensure
reproducibility.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.lstm_baseline import predict_logistic
from app.lstm_features import FEATURE_COLUMNS, candle_features, FeatureScaler, make_sequence_partition
from app.model_artifact import ModelArtifact, load_model_artifact, artifact_sha256


def _fingerprint_frame(frame: pd.DataFrame) -> str:
    """Compute SHA256 fingerprint of OHLCV candles (canonical format)."""
    selected = frame.loc[:, ["open", "high", "low", "close", "volume"]]
    payload = selected.to_csv(index=True, date_format="%Y-%m-%dT%H:%M:%S.%f").encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_prediction_ledger(
    artifact_dir: Path, partition, probabilities: np.ndarray
) -> None:
    """Validate the persisted validation ledger against reconstructed samples."""
    ledger_file = artifact_dir / "predictions.jsonl"
    if not ledger_file.exists():
        raise ValueError("predictions.jsonl not found")
    try:
        records = [json.loads(line) for line in ledger_file.read_text().splitlines()]
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"predictions.jsonl is invalid: {e}")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("prediction ledger record must be an object")
    records = [record for record in records if record.get("partition") == "validation"]
    if len(records) != len(probabilities):
        raise ValueError("validation prediction ledger length does not match reconstructed partition")
    for record, decision, outcome, label, probability in zip(
        records, partition.decision_timestamps, partition.outcome_timestamps,
        partition.y, probabilities, strict=True,
    ):
        if not isinstance(record, dict):
            raise ValueError("prediction ledger record must be an object")
        if record.get("decision_timestamp") != decision.isoformat():
            raise ValueError("prediction ledger decision timestamp mismatch")
        if record.get("outcome_timestamp") != outcome.isoformat():
            raise ValueError("prediction ledger outcome timestamp mismatch")
        if record.get("label") != float(label):
            raise ValueError("prediction ledger label mismatch")
        try:
            finite_probability = np.isfinite(record.get("probability", np.nan))
        except TypeError:
            finite_probability = False
        if not finite_probability or record["probability"] != float(probability):
            raise ValueError("prediction ledger probability mismatch")


def load_and_predict(
    artifact_dir: Path,
) -> tuple[np.ndarray, ModelArtifact, dict]:
    """Load a persisted validation-only or selector run and replay exact validation predictions.
    
    This function reads the manifest.json to determine run parameters, validates
    the model artifact SHA256, loads the model, and regenerates the exact
    validation probabilities from the original run.
    
    Supports both runner (run_lstm_baseline.py) and selector (select_lstm_baseline.py)
    artifacts. Both must be validation-only evaluation_mode with a model_artifact entry.

    Args:
        artifact_dir: Path to the run artifact directory (must contain manifest.json and model.json)
    
    Returns:
        (probabilities, loaded_artifact, manifest) where:
        - probabilities: 1D array of exact validation probabilities from original run
        - loaded_artifact: ModelArtifact with weights, bias, scaler
        - manifest: dict containing run metadata and parameters
    
    Raises:
        FileNotFoundError: if manifest.json or model.json not found
        ValueError: if manifest is invalid, run was not validation-only, had non-zero exit,
                   model hash mismatch, data fingerprint mismatch, or other validation failures
    """
    artifact_dir = Path(artifact_dir)
    manifest_file = artifact_dir / "manifest.json"
    model_file = artifact_dir / "model.json"
    
    if not manifest_file.exists():
        raise FileNotFoundError(f"manifest.json not found: {manifest_file}")
    if not model_file.exists():
        raise FileNotFoundError(f"model.json not found: {model_file}")
    
    # Load and validate manifest
    try:
        manifest = json.loads(manifest_file.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"manifest.json is malformed: {e}")
    
    # Verify validation-only mode (early validation, before DB access)
    evaluation_mode = manifest.get("evaluation_mode")
    if evaluation_mode != "validation-only":
        raise ValueError(
            f"manifest evaluation_mode is '{evaluation_mode}', expected 'validation-only'. "
            f"This run was not validation-only mode."
        )
    
    # Verify successful exit (early validation, before DB access)
    exit_status = manifest.get("exit_status")
    if exit_status != 0:
        raise ValueError(
            f"manifest exit_status is {exit_status}, not 0. "
            f"Original run did not complete successfully."
        )
    
    # Get model artifact metadata from manifest
    model_artifact_metadata = manifest.get("model_artifact", {})
    if not model_artifact_metadata:
        raise ValueError("manifest missing model_artifact entry")
    
    expected_sha256 = model_artifact_metadata.get("sha256")
    if not expected_sha256:
        raise ValueError("manifest model_artifact missing sha256")
    
    # Verify model.json SHA256 matches manifest
    actual_sha256 = artifact_sha256(model_file)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"model.json SHA256 mismatch: computed {actual_sha256}, manifest has {expected_sha256}. "
            f"Artifact may be corrupted or modified."
        )
    
    # Load model artifact
    artifact = load_model_artifact(model_file)
    
    # Extract parameters from manifest (frozen, not caller-supplied)
    resolved_boundaries = manifest.get("resolved_boundaries", {})
    train_boundary = resolved_boundaries.get("train", {}).get("row_end")
    validation_boundary = resolved_boundaries.get("validation", {}).get("row_end")
    
    if train_boundary is None or validation_boundary is None:
        raise ValueError("manifest missing resolved_boundaries.train.row_end or validation.row_end")
    
    parameters = manifest.get("parameters", {})
    train_bars = parameters.get("train_bars")
    validation_bars = parameters.get("validation_bars")
    sequence_length = parameters.get("sequence_length")
    horizon = parameters.get("horizon")
    threshold = parameters.get("threshold", 0.0)
    cost_rate = parameters.get("cost_rate", 0.0)
    
    if sequence_length != artifact.sequence_length:
        raise ValueError(
            f"manifest sequence_length {sequence_length} does not match artifact {artifact.sequence_length}"
        )
    
    # Verify data fingerprint from manifest
    expected_fingerprint = manifest.get("data_sha256")
    if not expected_fingerprint:
        raise ValueError("manifest missing data_sha256")
    
    # Load the original candles from manifest metadata
    loaded_rows = manifest.get("loaded_rows")
    if loaded_rows is None:
        raise ValueError("manifest missing loaded_rows")
    
    # Get data source info
    data_source = manifest.get("data_source", {})
    database = data_source.get("database")
    
    if not database:
        raise ValueError("manifest missing data_source.database")
    
    # Import here to avoid circular dependency and keep validation-only from app logic
    import sqlite3
    try:
        # Open database in read-only mode to avoid creating it if missing
        db_uri = f"file:{database}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            ticker = manifest.get("ticker")
            period = manifest.get("period")
            frame = pd.read_sql_query(
                "SELECT begin AS timestamp, open, high, low, close, volume "
                "FROM candles WHERE ticker = ? AND period = ? ORDER BY begin LIMIT ?",
                conn, params=(ticker, period, loaded_rows),
                parse_dates=["timestamp"],
            ).set_index("timestamp")
        finally:
            conn.close()
    except (sqlite3.Error, FileNotFoundError) as e:
        raise ValueError(f"failed to load candles from database {database}: {e}")
    
    if frame.empty:
        raise ValueError(f"no candles found in database {database} for {ticker}/{period}")
    
    if len(frame) < validation_boundary:
        raise ValueError(
            f"loaded {len(frame)} candles, but need {validation_boundary} rows "
            f"(train_bars {train_bars} + validation_bars {validation_bars})"
        )
    
    # Slice to just train+validation consumed data
    consumed_frame = frame.iloc[:validation_boundary]
    
    # Verify data fingerprint
    actual_fingerprint = _fingerprint_frame(consumed_frame)
    if actual_fingerprint != expected_fingerprint:
        raise ValueError(
            f"data SHA256 mismatch: computed {actual_fingerprint}, manifest has {expected_fingerprint}. "
            f"Candles data has changed since original run."
        )
    
    # Build validation partition with exact same parameters as original run
    raw = candle_features(consumed_frame)
    scaler_rows = raw.iloc[0:train_bars]
    scaler = FeatureScaler.fit(scaler_rows)
    
    # Verify loaded scaler matches artifact scaler (sanity check)
    if not np.allclose(scaler.mean, artifact.scaler.mean):
        raise ValueError("fitted scaler mean does not match artifact scaler mean")
    if not np.allclose(scaler.scale, artifact.scaler.scale):
        raise ValueError("fitted scaler scale does not match artifact scaler scale")
    
    # Build validation partition exactly as in original run
    validation_partition = make_sequence_partition(
        consumed_frame,
        feature_start=0,
        decision_start=train_bars,
        decision_end=validation_boundary,
        sequence_length=sequence_length,
        horizon=horizon,
        threshold=threshold,
        cost_rate=cost_rate,
        scaler=artifact.scaler,  # Use loaded scaler
    )
    
    # Generate predictions using loaded weights and bias
    probabilities = predict_logistic(
        validation_partition.X,
        artifact.weights,
        artifact.bias,
    )
    _validate_prediction_ledger(artifact_dir, validation_partition, probabilities)

    return probabilities, artifact, manifest
