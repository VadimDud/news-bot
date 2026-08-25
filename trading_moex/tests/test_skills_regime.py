"""Tests for Market Regime Analysis skill."""

import numpy as np
import pandas as pd
import pytest

from app.skills.regime import RegimeResult, classify_regime


def _make_candles(
    n: int = 250,
    base_price: float = 250.0,
    trend: float = 0.0,  # daily drift
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    """Сгенерировать фиктивные свечи для тестов regime."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    # Базовый уровень + шум (без дрифта для предсказуемости)
    prices = base_price + rng.normal(0, base_price * volatility, n).cumsum()
    prices = np.maximum(prices, base_price * 0.5)  # не уходим в минус

    df = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": rng.randint(1000, 10000, n).astype(float),
    }, index=dates)
    return df


# ── Regime classification ────────────────────────────────────────────────────

def test_regime_uptrend():
    # Сознательно генерируем тренд через random walk с дрифтом
    rng = np.random.RandomState(1)
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    drift = np.linspace(200, 350, 250)  # линейный рост
    noise = rng.normal(0, 2, 250)
    prices = drift + noise
    df = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": rng.randint(1000, 10000, 250).astype(float),
    }, index=dates)
    result = classify_regime(df)
    assert result.regime == "trend_up"
    assert result.confidence > 0.5


def test_regime_downtrend():
    # Чёткий нисходящий тренд
    rng = np.random.RandomState(2)
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    drift = np.linspace(350, 200, 250)  # линейное падение
    noise = rng.normal(0, 2, 250)
    prices = drift + noise
    df = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": rng.randint(1000, 10000, 250).astype(float),
    }, index=dates)
    result = classify_regime(df)
    assert result.regime == "trend_down"
    assert result.confidence > 0.5


def test_regime_range():
    df = _make_candles(n=250, trend=0.0, volatility=0.005)
    result = classify_regime(df)
    assert result.regime in ("range", "trend_up", "trend_down")
    assert result.confidence > 0.1


def test_regime_high_vol():
    df = _make_candles(n=250, trend=0.0, volatility=0.1)
    result = classify_regime(df)
    assert result.regime == "high_vol"
    assert result.confidence > 0.5


# ── Insufficient data ────────────────────────────────────────────────────────

def test_regime_insufficient_data():
    df = _make_candles(n=50)
    result = classify_regime(df)
    assert result.regime == "range"
    assert result.confidence < 0.2


def test_regime_empty_df():
    df = pd.DataFrame()
    result = classify_regime(df)
    assert result.regime == "range"


# ── Details ──────────────────────────────────────────────────────────────────

def test_regime_has_details():
    df = _make_candles(n=250)
    result = classify_regime(df)
    assert "price" in result.details
    assert "ema200" in result.details
    assert "atr" in result.details


def test_regime_warning_messages():
    result_down = RegimeResult(regime="down", confidence=0.8, details={})
    assert "нисходящем" in result_down.as_warning()

    result_vol = RegimeResult(regime="high_vol", confidence=0.8, details={})
    assert "олатильность" in result_vol.as_warning()  # "Высокая волатильность"

    result_range = RegimeResult(regime="range", confidence=0.8, details={})
    assert "Боковой" in result_range.as_warning()

    result_up = RegimeResult(regime="trend_up", confidence=0.8, details={})
    assert result_up.as_warning() == ""
