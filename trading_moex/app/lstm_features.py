"""Causal candle features and sequence assembly for offline LSTM research.

This module does not train models or emit trading signals. All normalization is
fit on the supplied training prefix to avoid leaking future distribution data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


FEATURE_COLUMNS = (
    "return_1", "return_5", "return_20", "range_ratio", "body_ratio",
    "upper_shadow_ratio", "lower_shadow_ratio", "volume_zscore",
    "rsi_14", "atr_ratio",
)


def candle_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return 10 scale-aware, causal features from OHLCV candles."""
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")
    validate_candles(frame)
    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    open_ = frame["open"].astype(float)
    volume = frame["volume"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    candle_range = high - low
    safe_range = candle_range.replace(0, np.nan)
    log_return = np.log(close).diff()
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    losses = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).where(losses.ne(0), 100.0)
    rsi = rsi.mask(gains.eq(0) & losses.eq(0), 50.0)
    volume_mean = volume.rolling(20, min_periods=20).mean()
    volume_std = volume.rolling(20, min_periods=20).std(ddof=0).replace(0, np.nan)
    result = pd.DataFrame(index=frame.index)
    result["return_1"] = log_return
    result["return_5"] = np.log(close / close.shift(5))
    result["return_20"] = np.log(close / close.shift(20))
    result["range_ratio"] = (high - low) / close.replace(0, np.nan)
    # A flat candle has no body or shadows; keep it usable in long sequences.
    result["body_ratio"] = ((close - open_).abs() / safe_range).fillna(0.0)
    result["upper_shadow_ratio"] = (
        (high - pd.concat([open_, close], axis=1).max(axis=1)) / safe_range
    ).fillna(0.0)
    result["lower_shadow_ratio"] = (
        (pd.concat([open_, close], axis=1).min(axis=1) - low) / safe_range
    ).fillna(0.0)
    result["volume_zscore"] = (volume - volume_mean) / volume_std
    result["rsi_14"] = rsi / 100.0
    result["atr_ratio"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / close.replace(0, np.nan)
    return result.loc[:, FEATURE_COLUMNS]


def validate_candles(frame: pd.DataFrame) -> None:
    """Reject malformed or ambiguously ordered OHLCV input."""
    required = {"open", "high", "low", "close", "volume"}
    if not frame.index.is_monotonic_increasing:
        raise ValueError("candle timestamps must be increasing")
    if frame.index.has_duplicates:
        raise ValueError("candle timestamps must be unique")
    values = frame.loc[:, sorted(required)].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("OHLCV values must be finite")
    if (frame["close"] <= 0).any() or (frame["open"] <= 0).any():
        raise ValueError("open and close prices must be positive")
    if (frame["high"] < frame[["open", "close"]].max(axis=1)).any():
        raise ValueError("high must be at least open and close")
    if (frame["low"] > frame[["open", "close"]].min(axis=1)).any():
        raise ValueError("low must be at most open and close")
    if (frame["volume"] < 0).any():
        raise ValueError("volume must be nonnegative")


@dataclass(frozen=True)
class FeatureScaler:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, frame: pd.DataFrame) -> "FeatureScaler":
        values = frame.to_numpy(float)
        mean = np.nanmean(values, axis=0)
        scale = np.nanstd(values, axis=0)
        mean = np.where(np.isfinite(mean), mean, 0.0)
        scale = np.where(np.isfinite(scale) & (scale > 0), scale, 1.0)
        return cls(mean, scale)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        values = (frame.to_numpy(float) - self.mean) / self.scale
        return pd.DataFrame(values, index=frame.index, columns=frame.columns)


@dataclass(frozen=True)
class WalkForwardSplit:
    train_x: np.ndarray
    train_y: np.ndarray
    test_x: np.ndarray
    test_y: np.ndarray
    test_decision_timestamps: pd.Index
    test_timestamps: pd.Index
    train_start: int
    train_end: int
    test_end: int
    scaler: FeatureScaler


@dataclass(frozen=True)
class ChronologicalBoundaries:
    """Row boundaries for a non-overlapping research protocol."""

    train: tuple[int, int]
    validation: tuple[int, int]
    test: tuple[int, int]
    forward: tuple[int, int]


@dataclass(frozen=True)
class SequencePartition:
    X: np.ndarray
    y: np.ndarray
    decision_timestamps: pd.Index
    outcome_timestamps: pd.Index


def chronological_boundaries(
    candles: pd.DataFrame,
    *,
    train_bars: int,
    validation_bars: int,
    test_bars: int,
    forward_bars: int,
) -> ChronologicalBoundaries:
    """Return fixed train/validation/test/forward row ranges.

    The ranges are contiguous, non-overlapping, and expressed as half-open
    integer positions. No model or scaler is fit by this helper.
    """
    sizes = (train_bars, validation_bars, test_bars, forward_bars)
    if any(size <= 0 for size in sizes):
        raise ValueError("all chronological split sizes must be positive")
    total = sum(sizes)
    if len(candles) < total:
        raise ValueError("not enough candles for train/validation/test/forward split")
    train_end = train_bars
    validation_end = train_end + validation_bars
    test_end = validation_end + test_bars
    return ChronologicalBoundaries(
        train=(0, train_end),
        validation=(train_end, validation_end),
        test=(validation_end, test_end),
        forward=(test_end, test_end + forward_bars),
    )


def make_sequence_partition(
    candles: pd.DataFrame,
    *,
    feature_start: int,
    decision_start: int,
    decision_end: int,
    sequence_length: int = 50,
    horizon: int = 5,
    threshold: float = 0.0,
    cost_rate: float = 0.0,
    scaler: FeatureScaler,
) -> SequencePartition:
    """Build samples for a decision range using a caller-supplied train scaler."""
    if sequence_length <= 0 or horizon <= 0:
        raise ValueError("sequence_length and horizon must be positive")
    if not 0 <= feature_start <= decision_start <= decision_end <= len(candles):
        raise ValueError("invalid sequence partition boundaries")
    raw = candle_features(candles)
    scaled = scaler.transform(raw)
    close = candles["close"].astype(float).to_numpy()
    X, y, decision_timestamps, outcome_timestamps = [], [], [], []
    first_end = max(sequence_length, decision_start + 1)
    for end in range(first_end, min(decision_end + 1, len(candles) - horizon + 1)):
        decision_at = end - 1
        label_at = end + horizon - 1
        if decision_at < decision_start or label_at >= decision_end:
            continue
        window = scaled.iloc[end - sequence_length:end].to_numpy(float)
        if not np.isfinite(window).all():
            continue
        X.append(window)
        y.append(float(close[label_at] / close[decision_at] - 1 > threshold + cost_rate))
        decision_timestamps.append(candles.index[decision_at])
        outcome_timestamps.append(candles.index[label_at])
    if not X:
        raise ValueError("no complete finite samples in sequence partition")
    return SequencePartition(
        np.asarray(X), np.asarray(y, dtype=np.float32),
        pd.Index(decision_timestamps), pd.Index(outcome_timestamps),
    )


def _validate_split_parameters(
    candles: pd.DataFrame, train_bars: int, test_bars: int,
    sequence_length: int, horizon: int, step: int,
) -> None:
    if train_bars <= 0 or test_bars <= 0 or sequence_length <= 0 or horizon <= 0:
        raise ValueError("train_bars, test_bars, sequence_length and horizon must be positive")
    if step <= 0:
        raise ValueError("step must be positive")
    if step < test_bars:
        raise ValueError("step must be at least test_bars to prevent overlapping test folds")
    if len(candles) <= sequence_length + horizon:
        raise ValueError("not enough candles for sequence and horizon")


def walk_forward_splits(
    candles: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    sequence_length: int = 50,
    horizon: int = 5,
    threshold: float = 0.0,
    cost_rate: float = 0.0,
    step: int | None = None,
    expanding: bool = False,
) -> tuple[WalkForwardSplit, ...]:
    """Create chronological train/test tensors without shuffling or leakage."""
    if step is None:
        step = test_bars
    _validate_split_parameters(candles, train_bars, test_bars, sequence_length, horizon, step)
    raw = candle_features(candles)
    close = candles["close"].astype(float).to_numpy()
    splits: list[WalkForwardSplit] = []
    test_start = train_bars
    while test_start < len(candles):
        train_start = 0 if expanding else max(0, test_start - train_bars)
        train_end = test_start
        test_end = min(len(candles), test_start + test_bars)
        scaler = FeatureScaler.fit(raw.iloc[train_start:train_end])
        scaled = scaler.transform(raw)
        train_x, train_y = [], []
        test_x, test_y, test_decision_timestamps, test_timestamps = [], [], [], []
        for end in range(sequence_length, len(candles) - horizon + 1):
            decision_at = end - 1
            label_at = end + horizon - 1
            if label_at >= test_end:
                break
            window = scaled.iloc[end - sequence_length:end].to_numpy(float)
            if not np.isfinite(window).all():
                continue
            label = float(close[label_at] / close[end - 1] - 1 > threshold + cost_rate)
            # A training label must be fully known before the fold boundary.
            if train_start <= decision_at < train_end and label_at < train_end:
                train_x.append(window)
                train_y.append(label)
            elif test_start <= decision_at < test_end:
                test_x.append(window)
                test_y.append(label)
                test_decision_timestamps.append(candles.index[decision_at])
                test_timestamps.append(candles.index[label_at])
        if train_x and test_x:
            splits.append(WalkForwardSplit(
                np.asarray(train_x), np.asarray(train_y, dtype=np.float32),
                np.asarray(test_x), np.asarray(test_y, dtype=np.float32),
                pd.Index(test_decision_timestamps),
                pd.Index(test_timestamps), train_start, train_end, test_end, scaler,
            ))
        test_start += step
    return tuple(splits)


def make_lstm_dataset(
    candles: pd.DataFrame,
    *,
    sequence_length: int = 50,
    horizon: int = 5,
    threshold: float = 0.0,
    cost_rate: float = 0.0,
    train_end: int,
) -> tuple[np.ndarray, np.ndarray, pd.Index, pd.Index, FeatureScaler]:
    """Build chronological ``[samples, window, features]`` arrays.

    ``train_end`` is a row boundary. The scaler is fit only on feature rows
    strictly before it. Returned samples are limited to decisions whose labels
    are fully known before that boundary.
    """
    if sequence_length <= 0 or horizon <= 0:
        raise ValueError("sequence_length and horizon must be positive")
    if len(candles) <= sequence_length + horizon:
        raise ValueError("not enough candles for sequence and horizon")
    raw = candle_features(candles)
    boundary = train_end
    if not 0 < boundary <= len(raw):
        raise ValueError("train_end must be within the candle frame")
    scaler = FeatureScaler.fit(raw.iloc[:boundary])
    scaled = scaler.transform(raw)
    close = candles["close"].astype(float).to_numpy()
    X, y, decision_timestamps, outcome_timestamps = [], [], [], []
    for end in range(sequence_length, len(candles) - horizon + 1):
        label_at = end + horizon - 1
        if label_at >= boundary:
            break
        window = scaled.iloc[end - sequence_length:end]
        if not np.isfinite(window.to_numpy()).all():
            continue
        forward_return = close[label_at] / close[end - 1] - 1
        X.append(window.to_numpy(float))
        y.append(float(forward_return > threshold + cost_rate))
        decision_timestamps.append(candles.index[end - 1])
        outcome_timestamps.append(candles.index[label_at])
    if not X:
        raise ValueError("no complete finite feature windows")
    return (
        np.asarray(X), np.asarray(y, dtype=np.float32),
        pd.Index(decision_timestamps), pd.Index(outcome_timestamps), scaler,
    )
