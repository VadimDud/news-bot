import numpy as np
import pytest

from app.lstm_baseline import (
    classification_metrics,
    fit_logistic_baseline,
    majority_probabilities,
    predict_logistic,
)


def test_logistic_baseline_learns_simple_signal():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(80, 4, 2))
    y = (X[:, :, 0].mean(axis=1) > 0).astype(float)
    weights, bias = fit_logistic_baseline(X, y, epochs=500, l2=0.1)
    metrics = classification_metrics(y, predict_logistic(X, weights, bias))
    assert metrics.accuracy > 0.8


def test_majority_baseline_and_invalid_inputs():
    y = np.array([0, 0, 1, 0])
    probabilities = majority_probabilities(y, 3)
    assert probabilities.tolist() == [0.25, 0.25, 0.25]
    assert classification_metrics(np.array([0, 1]), probabilities[:2]).samples == 2
    with pytest.raises(ValueError):
        fit_logistic_baseline(np.ones((2, 3)), np.ones(2))


def test_metrics_report_positive_class_and_reject_invalid_values():
    metrics = classification_metrics(np.array([0, 1, 1, 0]), np.array([.1, .8, .6, .2]))
    assert metrics.predicted_positive_rate == .5
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    with pytest.raises(ValueError):
        classification_metrics(np.array([0, 2]), np.array([.1, .2]))
    with pytest.raises(ValueError):
        classification_metrics(np.array([0, 1]), np.array([float("nan"), .2]))
    assert np.isnan(classification_metrics(np.array([0, 0]), np.array([.1, .2])).balanced_accuracy)


def test_logistic_rejects_nonbinary_and_nonfinite_training_data():
    X = np.ones((3, 2, 1))
    with pytest.raises(ValueError, match="binary"):
        fit_logistic_baseline(X, np.array([0, 1, 2]))
    X[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        fit_logistic_baseline(X, np.array([0, 1, 1]))
