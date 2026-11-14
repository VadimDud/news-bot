"""Persistence layer for validation-only LSTM baseline models.

This module handles serialization and deserialization of fitted model artifacts:
weights, bias, scaler parameters (mean/scale), feature columns, and metadata.

Artifacts are stored as strict JSON with verification of finite values.
No secrets, training data, or raw candles are stored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

from app.lstm_features import FEATURE_COLUMNS, FeatureScaler


@dataclass(frozen=True)
class ModelArtifactMetadata:
    """Metadata for a persisted model artifact."""
    schema_version: str  # Must be "1.0"
    base_feature_columns: tuple[str, ...]  # The 10 LSTM features
    sequence_length: int  # Positive integer: LSTM window size (number of timesteps)
    feature_count: int  # sequence_length * len(base_feature_columns)
    scaler_mean_count: int  # Must equal len(base_feature_columns) == 10
    scaler_scale_count: int  # Must equal len(base_feature_columns) == 10
    weights_count: int  # Must equal feature_count


@dataclass(frozen=True)
class ModelArtifact:
    """In-memory representation of a persisted model artifact."""
    weights: np.ndarray  # 1D float array of fitted logistic weights (flattened: sequence_length * n_features)
    bias: float  # fitted bias term
    scaler: FeatureScaler  # mean and scale arrays (length = n_features, not flattened)
    base_feature_columns: tuple[str, ...]  # The base 10 LSTM features
    sequence_length: int  # LSTM window size for reconstruction
    metadata: ModelArtifactMetadata


def save_model_artifact(
    output_path: Path,
    weights: np.ndarray,
    bias: float,
    scaler: FeatureScaler,
    base_feature_columns: tuple[str, ...] = FEATURE_COLUMNS,
    sequence_length: int = 50,
) -> tuple[Path, str]:
    """Save a fitted logistic model to a JSON artifact file.
    
    Args:
        output_path: Directory where artifact is saved
        weights: 1D array of fitted weights (flattened: sequence_length * n_features)
        bias: fitted bias term
        scaler: FeatureScaler with mean and scale (not flattened, length = n_features)
        base_feature_columns: tuple of base feature names (10 features)
        sequence_length: LSTM window size (positive integer, e.g., 50)
    
    Returns:
        (artifact_file_path, sha256_hexdigest)
    
    Raises:
        ValueError: if any numeric value is non-finite, arrays have mismatched dimensions,
                   or sequence_length is not a positive integer
        FileExistsError: if model.json already exists (exclusive write)
    """
    # Validate sequence_length is positive integer
    if not isinstance(sequence_length, (int, np.integer)):
        raise ValueError(f"sequence_length must be integer, got {type(sequence_length).__name__}")
    if sequence_length <= 0:
        raise ValueError(f"sequence_length must be positive, got {sequence_length}")
    
    # Validate bias is finite scalar
    if not isinstance(bias, (int, float, np.number)):
        raise ValueError(f"bias must be numeric, got {type(bias).__name__}")
    if not np.isfinite(float(bias)):
        raise ValueError("bias must be finite")
    
    # Validate weights is 1D finite array
    if not isinstance(weights, np.ndarray) or weights.ndim != 1:
        raise ValueError("weights must be a 1D numpy array")
    if not np.isfinite(weights).all():
        raise ValueError("weights must contain only finite values")
    
    # Validate scaler dimensions match base_feature_columns
    n_features = len(base_feature_columns)
    if not isinstance(scaler.mean, np.ndarray) or scaler.mean.ndim != 1:
        raise ValueError("scaler.mean must be a 1D array")
    if not isinstance(scaler.scale, np.ndarray) or scaler.scale.ndim != 1:
        raise ValueError("scaler.scale must be a 1D array")
    if len(scaler.mean) != n_features:
        raise ValueError(f"scaler.mean length {len(scaler.mean)} must equal n_features {n_features}")
    if len(scaler.scale) != n_features:
        raise ValueError(f"scaler.scale length {len(scaler.scale)} must equal n_features {n_features}")
    
    # Validate scale is strictly positive
    if (scaler.scale <= 0).any():
        raise ValueError("scaler.scale must contain only positive values")
    
    # Validate mean and scale are finite
    if not np.isfinite(scaler.mean).all():
        raise ValueError("scaler.mean must contain only finite values")
    if not np.isfinite(scaler.scale).all():
        raise ValueError("scaler.scale must contain only finite values")
    
    # Validate weights count matches flattened dimensions
    expected_flattened = sequence_length * n_features
    if len(weights) != expected_flattened:
        raise ValueError(
            f"weights length {len(weights)} must equal sequence_length ({sequence_length}) * "
            f"n_features ({n_features}) = {expected_flattened}"
        )
    
    output_path.mkdir(parents=True, exist_ok=True)
    artifact_file = output_path / "model.json"
    
    # Exclusive write: fail if artifact already exists
    if artifact_file.exists():
        raise FileExistsError(f"artifact file already exists: {artifact_file}")
    
    # Convert to JSON-safe lists
    weights_list = weights.astype(float).tolist()
    mean_list = scaler.mean.astype(float).tolist()
    scale_list = scaler.scale.astype(float).tolist()
    
    metadata = ModelArtifactMetadata(
        schema_version="1.0",
        base_feature_columns=tuple(base_feature_columns),
        sequence_length=sequence_length,
        feature_count=len(weights_list),
        scaler_mean_count=len(mean_list),
        scaler_scale_count=len(scale_list),
        weights_count=len(weights_list),
    )
    
    artifact_dict = {
        "metadata": asdict(metadata),
        "weights": weights_list,
        "bias": float(bias),
        "scaler_mean": mean_list,
        "scaler_scale": scale_list,
    }
    
    # Verify strict JSON: no NaN, Inf, or -Inf (allow_nan=False rejects them)
    payload = json.dumps(artifact_dict, indent=2, allow_nan=False, sort_keys=True)
    artifact_file.write_text(payload)
    
    sha256 = hashlib.sha256(payload.encode()).hexdigest()
    return artifact_file, sha256


def load_model_artifact(artifact_file: Path) -> ModelArtifact:
    """Load a fitted logistic model from a JSON artifact file.
    
    Args:
        artifact_file: Path to model.json file
    
    Returns:
        ModelArtifact with weights, bias, scaler, base_feature_columns, sequence_length, and metadata
    
    Raises:
        FileNotFoundError: if artifact_file does not exist
        ValueError: if artifact is malformed, schema unsupported, or contains invalid values
    """
    if not artifact_file.exists():
        raise FileNotFoundError(f"artifact file not found: {artifact_file}")
    
    payload = artifact_file.read_text()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"artifact JSON is malformed: {e}")
    
    required_keys = {"metadata", "weights", "bias", "scaler_mean", "scaler_scale"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"artifact missing required keys: {missing}")
    
    meta_dict = data["metadata"]
    if meta_dict.get("schema_version") != "1.0":
        raise ValueError(f"unsupported schema_version: {meta_dict.get('schema_version')}")
    
    # Load and validate base_feature_columns
    base_feature_columns = tuple(meta_dict.get("base_feature_columns", []))
    if not base_feature_columns:
        raise ValueError("artifact must contain base_feature_columns")
    if base_feature_columns != FEATURE_COLUMNS:
        raise ValueError(
            f"artifact base_feature_columns {base_feature_columns} do not match expected {FEATURE_COLUMNS}"
        )
    
    # Load and validate sequence_length
    sequence_length = meta_dict.get("sequence_length")
    if not isinstance(sequence_length, (int, np.integer)):
        raise ValueError(f"sequence_length must be integer, got {type(sequence_length).__name__}")
    if sequence_length <= 0:
        raise ValueError(f"sequence_length must be positive, got {sequence_length}")
    
    # Load weights and validate shape
    weights_list = data.get("weights")
    if not isinstance(weights_list, list):
        raise ValueError(f"weights must be a list, got {type(weights_list).__name__}")
    
    try:
        weights = np.asarray(weights_list, dtype=float)
    except (ValueError, TypeError) as e:
        raise ValueError(f"weights not convertible to float array: {e}")
    
    if weights.ndim != 1:
        raise ValueError(f"weights must be 1D, got shape {weights.shape}")
    if not np.isfinite(weights).all():
        raise ValueError("weights must contain only finite values (no NaN, Inf, -Inf)")
    
    # Load bias and validate
    bias = data.get("bias")
    if not isinstance(bias, (int, float, np.number)):
        raise ValueError(f"bias must be numeric, got {type(bias).__name__}")
    try:
        bias = float(bias)
    except (ValueError, TypeError) as e:
        raise ValueError(f"bias not convertible to float: {e}")
    if not np.isfinite(bias):
        raise ValueError("bias must be finite (not NaN or Inf)")
    
    # Load scaler_mean and validate
    mean_list = data.get("scaler_mean")
    if not isinstance(mean_list, list):
        raise ValueError(f"scaler_mean must be a list, got {type(mean_list).__name__}")
    
    try:
        scaler_mean = np.asarray(mean_list, dtype=float)
    except (ValueError, TypeError) as e:
        raise ValueError(f"scaler_mean not convertible to float array: {e}")
    
    if scaler_mean.ndim != 1:
        raise ValueError(f"scaler_mean must be 1D, got shape {scaler_mean.shape}")
    if not np.isfinite(scaler_mean).all():
        raise ValueError("scaler_mean must contain only finite values")
    if len(scaler_mean) != len(base_feature_columns):
        raise ValueError(
            f"scaler_mean length {len(scaler_mean)} must equal n_features {len(base_feature_columns)}"
        )
    
    # Load scaler_scale and validate
    scale_list = data.get("scaler_scale")
    if not isinstance(scale_list, list):
        raise ValueError(f"scaler_scale must be a list, got {type(scale_list).__name__}")
    
    try:
        scaler_scale = np.asarray(scale_list, dtype=float)
    except (ValueError, TypeError) as e:
        raise ValueError(f"scaler_scale not convertible to float array: {e}")
    
    if scaler_scale.ndim != 1:
        raise ValueError(f"scaler_scale must be 1D, got shape {scaler_scale.shape}")
    if not np.isfinite(scaler_scale).all():
        raise ValueError("scaler_scale must contain only finite values")
    if len(scaler_scale) != len(base_feature_columns):
        raise ValueError(
            f"scaler_scale length {len(scaler_scale)} must equal n_features {len(base_feature_columns)}"
        )
    if (scaler_scale <= 0).any():
        raise ValueError("scaler_scale must contain only positive values")
    
    # Validate metadata counts match actual data
    expected_flattened = sequence_length * len(base_feature_columns)
    if len(weights) != expected_flattened:
        raise ValueError(
            f"weights length {len(weights)} must equal sequence_length ({sequence_length}) * "
            f"base_feature_columns ({len(base_feature_columns)}) = {expected_flattened}"
        )
    
    metadata_feature_count = meta_dict.get("feature_count")
    if metadata_feature_count != len(weights):
        raise ValueError(
            f"metadata feature_count {metadata_feature_count} does not match weights length {len(weights)}"
        )
    metadata_mean_count = meta_dict.get("scaler_mean_count")
    if metadata_mean_count != len(scaler_mean):
        raise ValueError(
            f"metadata scaler_mean_count {metadata_mean_count} does not match actual {len(scaler_mean)}"
        )
    metadata_scale_count = meta_dict.get("scaler_scale_count")
    if metadata_scale_count != len(scaler_scale):
        raise ValueError(
            f"metadata scaler_scale_count {metadata_scale_count} does not match actual {len(scaler_scale)}"
        )
    metadata_weights_count = meta_dict.get("weights_count")
    if metadata_weights_count != len(weights):
        raise ValueError(
            f"metadata weights_count {metadata_weights_count} does not match actual {len(weights)}"
        )
    
    scaler = FeatureScaler(mean=scaler_mean, scale=scaler_scale)
    
    metadata = ModelArtifactMetadata(
        schema_version="1.0",
        base_feature_columns=base_feature_columns,
        sequence_length=sequence_length,
        feature_count=len(weights),
        scaler_mean_count=len(scaler_mean),
        scaler_scale_count=len(scaler_scale),
        weights_count=len(weights),
    )
    
    return ModelArtifact(
        weights=weights,
        bias=bias,
        scaler=scaler,
        base_feature_columns=base_feature_columns,
        sequence_length=sequence_length,
        metadata=metadata,
    )


def artifact_sha256(artifact_file: Path) -> str:
    """Compute SHA256 of artifact file content."""
    if not artifact_file.exists():
        raise FileNotFoundError(f"artifact file not found: {artifact_file}")
    payload = artifact_file.read_text()
    return hashlib.sha256(payload.encode()).hexdigest()
