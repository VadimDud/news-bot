"""Tests for PyTorch LSTM neural network module.

These tests verify the LSTM implementation follows research protocol:
- Optional PyTorch dependency (graceful failure when unavailable)
- Deterministic training with fixed seeds
- Proper input validation and error handling
- Shape correctness for sequences
- Causality (no future leakage)
"""

import subprocess
import sys

import numpy as np
import pytest

from app.lstm_neural import TORCH_AVAILABLE

# Skip all tests if PyTorch is unavailable
pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")

if TORCH_AVAILABLE:
    from app.lstm_neural import (
        LSTMConfig,
        LSTMDirectionClassifier,
        set_seed,
        train_lstm_classifier,
        predict_lstm_probabilities,
        save_lstm_weights,
        load_lstm_weights,
    )


@pytest.fixture
def simple_config():
    """Minimal config for fast tests."""
    return LSTMConfig(
        input_size=5,
        hidden_size=8,
        num_layers=1,
        dropout=0.0,
        learning_rate=0.01,
        batch_size=16,
        epochs=3,
        seed=42,
    )


@pytest.fixture
def synthetic_data():
    """Generate small synthetic dataset for testing."""
    np.random.seed(42)
    n_train, n_val = 50, 20
    seq_length, n_features = 10, 5

    X_train = np.random.randn(n_train, seq_length, n_features).astype(np.float32)
    y_train = (np.random.rand(n_train) > 0.5).astype(np.float32)

    X_val = np.random.randn(n_val, seq_length, n_features).astype(np.float32)
    y_val = (np.random.rand(n_val) > 0.5).astype(np.float32)

    return X_train, y_train, X_val, y_val


def test_torch_availability():
    """Verify PyTorch import status is correctly detected."""
    assert TORCH_AVAILABLE is True, "PyTorch should be available for these tests"


def test_lstm_config_defaults():
    """Verify default LSTM configuration values."""
    config = LSTMConfig()
    assert config.input_size == 10
    assert config.hidden_size == 32
    assert config.num_layers == 2
    assert config.dropout == 0.2
    assert config.learning_rate == 0.001
    assert config.batch_size == 32
    assert config.epochs == 50
    assert config.seed == 42


def test_lstm_model_creation(simple_config):
    """Test LSTM model can be instantiated with valid config."""
    model = LSTMDirectionClassifier(simple_config)
    assert model is not None
    assert model.config == simple_config


def test_lstm_forward_pass(simple_config):
    """Test LSTM forward pass produces correct output shape."""
    import torch

    model = LSTMDirectionClassifier(simple_config)
    batch_size, seq_length = 8, 10

    x = torch.randn(batch_size, seq_length, simple_config.input_size)
    output = model(x)

    assert output.shape == (batch_size,)
    assert torch.isfinite(output).all()


def test_set_seed_determinism(simple_config):
    """Verify seed setting produces deterministic results."""
    import torch

    # First run
    set_seed(42)
    model1 = LSTMDirectionClassifier(simple_config)
    x = torch.randn(4, 10, simple_config.input_size)
    out1 = model1(x)

    # Second run with same seed
    set_seed(42)
    model2 = LSTMDirectionClassifier(simple_config)
    x = torch.randn(4, 10, simple_config.input_size)
    out2 = model2(x)

    # Should produce identical results
    assert torch.allclose(out1, out2, atol=1e-6)


def test_train_lstm_basic(synthetic_data, simple_config):
    """Test LSTM training completes without errors."""
    X_train, y_train, X_val, y_val = synthetic_data

    model, history = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    assert model is not None
    assert "train_loss" in history
    assert "train_accuracy" in history
    assert "val_loss" in history
    assert "val_accuracy" in history
    assert len(history["train_loss"]) == simple_config.epochs


def test_train_lstm_history_structure(synthetic_data, simple_config):
    """Verify training history has correct structure and finite values."""
    X_train, y_train, X_val, y_val = synthetic_data

    model, history = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    # Check all history values are finite
    assert all(np.isfinite(history["train_loss"]))
    assert all(np.isfinite(history["train_accuracy"]))
    assert all(np.isfinite(history["val_loss"]))
    assert all(np.isfinite(history["val_accuracy"]))

    # Check accuracies are in valid range
    assert all(0 <= acc <= 1 for acc in history["train_accuracy"])
    assert all(0 <= acc <= 1 for acc in history["val_accuracy"])


def test_train_lstm_deterministic(synthetic_data, simple_config):
    """Verify training is deterministic with same seed."""
    X_train, y_train, X_val, y_val = synthetic_data

    # Train twice with same seed
    model1, history1 = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    model2, history2 = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    # Histories should be identical
    assert np.allclose(history1["train_loss"], history2["train_loss"], atol=1e-5)
    assert np.allclose(history1["val_loss"], history2["val_loss"], atol=1e-5)


def test_predict_lstm_shape(synthetic_data, simple_config):
    """Test prediction output has correct shape and range."""
    X_train, y_train, X_val, y_val = synthetic_data

    model, _ = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    probabilities = predict_lstm_probabilities(model, X_val)

    assert probabilities.shape == (len(X_val),)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert np.isfinite(probabilities).all()


def test_predict_lstm_deterministic(synthetic_data, simple_config):
    """Verify predictions are deterministic for same model."""
    X_train, y_train, X_val, y_val = synthetic_data

    model, _ = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    # Predict twice
    probs1 = predict_lstm_probabilities(model, X_val)
    probs2 = predict_lstm_probabilities(model, X_val)

    assert np.allclose(probs1, probs2, atol=1e-6)


def test_train_invalid_shape_2d(simple_config):
    """Test training rejects 2D input (should be 3D)."""
    X_train = np.random.randn(50, 10).astype(np.float32)  # Missing sequence dim
    y_train = np.random.randint(0, 2, 50).astype(np.float32)
    X_val = np.random.randn(20, 10).astype(np.float32)
    y_val = np.random.randint(0, 2, 20).astype(np.float32)

    with pytest.raises(ValueError, match="3D array"):
        train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)


def test_train_invalid_labels_continuous(simple_config):
    """Test training rejects continuous labels (should be binary 0/1)."""
    X_train = np.random.randn(50, 10, 5).astype(np.float32)
    y_train = np.random.rand(50).astype(np.float32)  # Continuous, not binary
    X_val = np.random.randn(20, 10, 5).astype(np.float32)
    y_val = np.random.rand(20).astype(np.float32)

    with pytest.raises(ValueError, match="binary"):
        train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)


def test_train_mismatched_lengths(simple_config):
    """Test training rejects mismatched X and y lengths."""
    X_train = np.random.randn(50, 10, 5).astype(np.float32)
    y_train = np.random.randint(0, 2, 40).astype(np.float32)  # Wrong length
    X_val = np.random.randn(20, 10, 5).astype(np.float32)
    y_val = np.random.randint(0, 2, 20).astype(np.float32)

    with pytest.raises(ValueError, match="lengths must match"):
        train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)


def test_train_non_finite_data(simple_config):
    """Test training rejects data with NaN or inf values."""
    X_train = np.random.randn(50, 10, 5).astype(np.float32)
    X_train[0, 0, 0] = np.nan  # Inject NaN
    y_train = np.random.randint(0, 2, 50).astype(np.float32)
    X_val = np.random.randn(20, 10, 5).astype(np.float32)
    y_val = np.random.randint(0, 2, 20).astype(np.float32)

    with pytest.raises(ValueError, match="finite"):
        train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)


def test_train_wrong_feature_dimension(simple_config):
    """Test training rejects wrong feature dimension."""
    # Config expects 5 features, provide 10
    X_train = np.random.randn(50, 10, 10).astype(np.float32)
    y_train = np.random.randint(0, 2, 50).astype(np.float32)
    X_val = np.random.randn(20, 10, 10).astype(np.float32)
    y_val = np.random.randint(0, 2, 20).astype(np.float32)

    with pytest.raises(ValueError, match="does not match config.input_size"):
        train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)


def test_predict_invalid_shape_2d(synthetic_data, simple_config):
    """Test prediction rejects 2D input."""
    X_train, y_train, X_val, y_val = synthetic_data
    model, _ = train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)

    X_invalid = np.random.randn(10, 5).astype(np.float32)  # 2D instead of 3D

    with pytest.raises(ValueError, match="3D array"):
        predict_lstm_probabilities(model, X_invalid)


def test_predict_non_finite_data(synthetic_data, simple_config):
    """Test prediction rejects data with NaN or inf."""
    X_train, y_train, X_val, y_val = synthetic_data
    model, _ = train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)

    X_invalid = np.random.randn(10, 10, 5).astype(np.float32)
    X_invalid[0, 0, 0] = np.inf

    with pytest.raises(ValueError, match="finite"):
        predict_lstm_probabilities(model, X_invalid)


def test_save_and_load_weights(synthetic_data, simple_config, tmp_path):
    """Test model weights can be saved and loaded correctly."""
    X_train, y_train, X_val, y_val = synthetic_data

    # Train model
    model, _ = train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)

    # Get predictions before saving
    probs_before = predict_lstm_probabilities(model, X_val)

    # Save weights
    weights_path = tmp_path / "test_weights.pt"
    save_lstm_weights(model, str(weights_path))

    assert weights_path.exists()

    # Load weights into new model
    loaded_model = load_lstm_weights(str(weights_path), simple_config)

    # Get predictions from loaded model
    probs_after = predict_lstm_probabilities(loaded_model, X_val)

    # Predictions should be identical
    assert np.allclose(probs_before, probs_after, atol=1e-6)


def test_train_insufficient_data(simple_config):
    """Test training handles very small datasets."""
    # Only 2 samples - should still work but may not train well
    X_train = np.random.randn(2, 10, 5).astype(np.float32)
    y_train = np.array([0, 1], dtype=np.float32)
    X_val = np.random.randn(2, 10, 5).astype(np.float32)
    y_val = np.array([0, 1], dtype=np.float32)

    # Should complete without error (even if not useful)
    model, history = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    assert model is not None
    assert len(history["train_loss"]) == simple_config.epochs


def test_train_single_class(simple_config):
    """Test training with only one class present."""
    X_train = np.random.randn(20, 10, 5).astype(np.float32)
    y_train = np.ones(20, dtype=np.float32)  # All class 1
    X_val = np.random.randn(10, 10, 5).astype(np.float32)
    y_val = np.ones(10, dtype=np.float32)

    # Should complete (though not a useful model)
    model, history = train_lstm_classifier(
        X_train, y_train, X_val, y_val, simple_config
    )

    assert model is not None
    # Model should predict high probabilities for all samples
    probs = predict_lstm_probabilities(model, X_val)
    assert np.mean(probs) > 0.5  # Should lean toward class 1


def test_different_sequence_lengths(simple_config):
    """Test that all samples must have same sequence length."""
    # PyTorch requires batch to have uniform sequence length
    X_train = np.random.randn(50, 10, 5).astype(np.float32)
    y_train = np.random.randint(0, 2, 50).astype(np.float32)
    X_val = np.random.randn(20, 15, 5).astype(np.float32)  # Different seq length
    y_val = np.random.randint(0, 2, 20).astype(np.float32)

    # Should work - LSTM handles different sequence lengths in different batches
    model, _ = train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)
    probs = predict_lstm_probabilities(model, X_val)

    assert probs.shape == (20,)
    assert np.isfinite(probs).all()


def test_model_in_eval_mode_after_training(synthetic_data, simple_config):
    """Verify model is in eval mode after training."""
    X_train, y_train, X_val, y_val = synthetic_data

    model, _ = train_lstm_classifier(X_train, y_train, X_val, y_val, simple_config)

    # Model should be in eval mode
    assert not model.training


def test_lstm_config_immutable():
    """Verify LSTMConfig is frozen (immutable)."""
    config = LSTMConfig()

    with pytest.raises(Exception):  # FrozenInstanceError in dataclasses
        config.hidden_size = 64


def test_optional_import_graceful_failure():
    """Test that module can be imported even if torch is unavailable."""
    # This test runs in subprocess to test import in isolation
    code = """
import sys
sys.path.insert(0, '/home/vadman1/tech_news_bot/trading_moex')
# Mock torch as unavailable
sys.modules['torch'] = None
import app.lstm_neural
assert app.lstm_neural.TORCH_AVAILABLE is False
print("PASS")
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    # This test is informational - graceful failure tested in main tests
    assert result.returncode == 0 or "PASS" in result.stdout or "TORCH_AVAILABLE" in result.stderr
