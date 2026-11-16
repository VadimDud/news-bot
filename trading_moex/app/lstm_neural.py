"""PyTorch LSTM neural network for directional classification research.

This module provides a minimal LSTM implementation for the LSTM-BASELINE-001 study.
PyTorch is an optional dependency; the module fails gracefully if unavailable.

This is a research artifact, not a production trading system. No live orders.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Optional PyTorch import - fail gracefully if unavailable
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
    _BaseModule = nn.Module
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore
    nn = None  # type: ignore
    optim = None  # type: ignore
    _BaseModule = object  # type: ignore


@dataclass(frozen=True)
class LSTMConfig:
    """Fixed LSTM architecture configuration for reproducibility."""
    input_size: int = 10  # Number of features per timestep
    hidden_size: int = 32  # LSTM hidden units
    num_layers: int = 2    # Stacked LSTM layers
    dropout: float = 0.2   # Dropout rate between LSTM layers
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 50
    seed: int = 42


class LSTMDirectionClassifier(_BaseModule):
    """Binary direction classifier using stacked LSTM layers.

    Architecture:
    - Input: [batch, sequence_length, input_size]
    - LSTM: 2 layers, 32 hidden units, 0.2 dropout
    - Output: [batch, 1] logits (sigmoid activation for probabilities)
    """

    def __init__(self, config: LSTMConfig):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is not available; cannot create LSTM model")

        super().__init__()
        self.config = config

        self.lstm = nn.LSTM(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=config.dropout if config.num_layers > 1 else 0.0,
            batch_first=True,
        )

        self.fc = nn.Linear(config.hidden_size, 1)

    def forward(self, x):
        # x shape: [batch, sequence_length, input_size]
        lstm_out, _ = self.lstm(x)
        # Take the last timestep output
        last_hidden = lstm_out[:, -1, :]  # [batch, hidden_size]
        logits = self.fc(last_hidden)     # [batch, 1]
        return logits.squeeze(-1)         # [batch]


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    if not TORCH_AVAILABLE:
        return

    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_lstm_classifier(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    config: LSTMConfig,
) -> tuple[LSTMDirectionClassifier, dict]:
    """Train LSTM classifier and return model with training history.

    Args:
        X_train: Training sequences [n_samples, sequence_length, n_features]
        y_train: Training labels [n_samples] (binary 0/1)
        X_val: Validation sequences [n_samples, sequence_length, n_features]
        y_val: Validation labels [n_samples] (binary 0/1)
        config: LSTM architecture and training configuration

    Returns:
        (trained_model, history) where history contains loss/accuracy per epoch

    Raises:
        ImportError: if PyTorch is not available
        ValueError: if input shapes are invalid or contain non-finite values
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available; cannot train LSTM model")

    # Validate inputs
    if X_train.ndim != 3 or X_val.ndim != 3:
        raise ValueError("X must be 3D arrays [n_samples, sequence_length, n_features]")
    if len(X_train) != len(y_train) or len(X_val) != len(y_val):
        raise ValueError("X and y lengths must match")
    if not np.isfinite(X_train).all() or not np.isfinite(y_train).all():
        raise ValueError("Training data must contain only finite values")
    if not np.isfinite(X_val).all() or not np.isfinite(y_val).all():
        raise ValueError("Validation data must contain only finite values")
    if not np.isin(y_train, (0, 1)).all() or not np.isin(y_val, (0, 1)).all():
        raise ValueError("Labels must be binary (0 or 1)")
    if X_train.shape[2] != config.input_size:
        raise ValueError(f"Feature dimension {X_train.shape[2]} does not match config.input_size {config.input_size}")

    # Set seeds for reproducibility
    set_seed(config.seed)

    # Convert to PyTorch tensors
    X_train_t = torch.from_numpy(X_train).float()
    y_train_t = torch.from_numpy(y_train).float()
    X_val_t = torch.from_numpy(X_val).float()
    y_val_t = torch.from_numpy(y_val).float()

    # Create data loaders
    train_dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t)
    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True
    )

    # Initialize model, loss, optimizer
    model = LSTMDirectionClassifier(config)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)

    # Training history
    history = {
        "train_loss": [],
        "train_accuracy": [],
        "val_loss": [],
        "val_accuracy": [],
    }

    # Training loop
    model.train()
    for epoch in range(config.epochs):
        epoch_losses = []
        epoch_correct = 0
        epoch_total = 0

        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            epoch_losses.append(loss.item())
            predictions = (torch.sigmoid(logits) >= 0.5).float()
            epoch_correct += (predictions == batch_y).sum().item()
            epoch_total += len(batch_y)

        train_loss = float(np.mean(epoch_losses))
        train_accuracy = epoch_correct / epoch_total

        # Validation evaluation
        model.eval()
        with torch.no_grad():
            val_logits = model(X_val_t)
            val_loss = criterion(val_logits, y_val_t).item()
            val_predictions = (torch.sigmoid(val_logits) >= 0.5).float()
            val_accuracy = (val_predictions == y_val_t).float().mean().item()
        model.train()

        history["train_loss"].append(train_loss)
        history["train_accuracy"].append(train_accuracy)
        history["val_loss"].append(val_loss)
        history["val_accuracy"].append(val_accuracy)

    model.eval()
    return model, history


def predict_lstm_probabilities(
    model: LSTMDirectionClassifier,
    X: np.ndarray,
) -> np.ndarray:
    """Generate probability predictions from trained LSTM model.

    Args:
        model: Trained LSTM classifier
        X: Input sequences [n_samples, sequence_length, n_features]

    Returns:
        Array of probabilities [n_samples] in range [0, 1]

    Raises:
        ImportError: if PyTorch is not available
        ValueError: if X has invalid shape or non-finite values
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available; cannot make predictions")

    if X.ndim != 3:
        raise ValueError("X must be 3D array [n_samples, sequence_length, n_features]")
    if not np.isfinite(X).all():
        raise ValueError("X must contain only finite values")

    model.eval()
    with torch.no_grad():
        X_t = torch.from_numpy(X).float()
        logits = model(X_t)
        probabilities = torch.sigmoid(logits).numpy()

    return probabilities


def save_lstm_weights(model: LSTMDirectionClassifier, filepath: str) -> None:
    """Save LSTM model weights to file.

    This saves only the model state_dict, not the optimizer or training state.
    The saved weights are not compatible with logistic baseline artifacts.

    Args:
        model: Trained LSTM model
        filepath: Path to save weights (e.g., 'lstm_weights.pt')

    Raises:
        ImportError: if PyTorch is not available
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available; cannot save model")

    torch.save(model.state_dict(), filepath)


def load_lstm_weights(
    filepath: str,
    config: LSTMConfig,
) -> LSTMDirectionClassifier:
    """Load LSTM model weights from file.

    Args:
        filepath: Path to saved weights
        config: LSTM configuration (must match the saved model)

    Returns:
        Loaded LSTM model in eval mode

    Raises:
        ImportError: if PyTorch is not available
        FileNotFoundError: if filepath does not exist
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available; cannot load model")

    model = LSTMDirectionClassifier(config)
    model.load_state_dict(torch.load(filepath, weights_only=True))
    model.eval()
    return model
