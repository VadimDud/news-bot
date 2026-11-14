"""Small, deterministic baselines for the offline LSTM study.

The implementation deliberately avoids adding a machine-learning dependency.
It is a benchmark for the same walk-forward tensors, not a trading strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClassificationMetrics:
    samples: int
    positive_rate: float
    accuracy: float
    balanced_accuracy: float
    log_loss: float
    predicted_positive_rate: float
    precision: float
    recall: float
    f1: float
    brier_score: float


def _logistic(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40, 40)))


def fit_logistic_baseline(
    X: np.ndarray,
    y: np.ndarray,
    *,
    learning_rate: float = 0.05,
    epochs: int = 300,
    l2: float = 1.0,
) -> tuple[np.ndarray, float]:
    """Fit a regularized logistic model on flattened sequence tensors."""
    if X.ndim != 3 or len(X) != len(y) or len(X) == 0:
        raise ValueError("X must be a nonempty 3D tensor matching y")
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("X and y must contain only finite values")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("y must contain only binary labels")
    if epochs <= 0 or learning_rate <= 0 or l2 < 0:
        raise ValueError("invalid logistic baseline parameters")
    features = X.reshape(len(X), -1).astype(float)
    targets = np.asarray(y, dtype=float)
    weights = np.zeros(features.shape[1], dtype=float)
    bias = 0.0
    for _ in range(epochs):
        probabilities = _logistic(features @ weights + bias)
        error = probabilities - targets
        weights -= learning_rate * (features.T @ error / len(features) + l2 * weights)
        bias -= learning_rate * float(error.mean())
    return weights, bias


def predict_logistic(X: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    if X.ndim != 3:
        raise ValueError("X must be a 3D tensor")
    features = X.reshape(len(X), -1).astype(float)
    if features.shape[1] != len(weights):
        raise ValueError("feature shape does not match fitted weights")
    return _logistic(features @ weights + bias)


def classification_metrics(y: np.ndarray, probabilities: np.ndarray) -> ClassificationMetrics:
    raw_targets = np.asarray(y, dtype=float)
    raw_probabilities = np.asarray(probabilities, dtype=float)
    if (not np.isfinite(raw_targets).all() or not np.isfinite(raw_probabilities).all()
            or not np.isin(raw_targets, (0, 1)).all()
            or (raw_probabilities < 0).any() or (raw_probabilities > 1).any()):
        raise ValueError("binary finite targets and probabilities in [0, 1] are required")
    targets = raw_targets.astype(int)
    probabilities = np.clip(raw_probabilities, 1e-7, 1 - 1e-7)
    if len(targets) == 0 or len(targets) != len(probabilities):
        raise ValueError("y and probabilities must be nonempty and equal length")
    predicted = probabilities >= 0.5
    accuracy = float(np.mean(predicted == targets))
    recalls = []
    for label in (0, 1):
        mask = targets == label
        if mask.any():
            recalls.append(float(np.mean(predicted[mask] == label)))
    loss = -float(np.mean(targets * np.log(probabilities) + (1 - targets) * np.log(1 - probabilities)))
    true_positive = int(((predicted == 1) & (targets == 1)).sum())
    false_positive = int(((predicted == 1) & (targets == 0)).sum())
    positive_count = int((targets == 1).sum())
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / positive_count if positive_count else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if np.isfinite(recall) and precision + recall else 0.0)
    balanced_accuracy = float(np.mean(recalls)) if len(recalls) == 2 else float("nan")
    return ClassificationMetrics(
        samples=len(targets),
        positive_rate=float(np.mean(targets)),
        accuracy=accuracy,
        balanced_accuracy=balanced_accuracy,
        log_loss=loss,
        predicted_positive_rate=float(np.mean(predicted)),
        precision=float(precision), recall=float(recall), f1=float(f1),
        brier_score=float(np.mean((probabilities - targets) ** 2)),
    )


def majority_probabilities(y_train: np.ndarray, n: int) -> np.ndarray:
    if len(y_train) == 0 or n <= 0:
        raise ValueError("training labels and output size must be positive")
    return np.full(n, float(np.mean(y_train)), dtype=float)
