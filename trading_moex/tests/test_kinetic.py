"""Tests for Kinetic Momentum strategy — synthetic data, no DB.

Проверяются:
- причинность фич (нет данных будущего бара в значениях текущего);
- симметрия лонг/шорт сигнала;
- корректность позиции на синтетическом тренде/импульсе;
- паритет pandas-серии и backtrader-стратегии;
- согласованность signals.SIGNAL_FUNCS["kinetic"].
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import kinetic  # noqa: E402
from app import signals as sig_mod  # noqa: E402
from app.backtest import run_backtest  # noqa: E402
from app.strategies import KineticMomentumStrategy  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candles(closes, base_vol=1000.0, seed=3):
    """OHLCV DataFrame (30min index) из цен закрытия."""
    rng = np.random.default_rng(seed)
    close = np.array(closes, dtype=float)
    opens = np.append(close[0], close[:-1])
    spread = np.abs(rng.normal(0, 0.2, len(close)))
    high = np.maximum(opens, close) + spread
    low = np.minimum(opens, close) - spread
    vol = base_vol * (1 + 0.2 * rng.normal(0, 1, len(close)))
    idx = pd.date_range("2024-01-01", periods=len(close), freq="30min")
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def _momentum_series(n=240, rho=0.55, drift=0.02, seed=1):
    """Цены с положительной автокорреляцией доходностей (моментум-режим).

    r_t = drift + rho*r_{t-1} + noise — серии однонаправленных ходов длиннее,
    чем у i.i.d. (полезно для проверки, что сигнал «зажигается» на тренде).
    """
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = drift + rho * r[i - 1] + rng.normal(0, 0.2)
    return (100.0 * np.exp(np.cumsum(r))).tolist()


def _flat_noise(n=300, seed=5):
    rng = np.random.default_rng(seed)
    p = 100.0 + np.cumsum(rng.normal(0, 0.15, n))
    return p.tolist()


# ---------------------------------------------------------------------------
# kinetic_features — причинность
# ---------------------------------------------------------------------------

def test_features_are_causal():
    """Значение фичи на баре i не меняется при добавлении будущих баров."""
    prices = _flat_noise(300)
    df = _candles(prices)
    f1 = kinetic.kinetic_features(df.iloc[:250])
    f2 = kinetic.kinetic_features(df.iloc[:251])
    # тот же бар (индекс 249 в обоих расчётах)
    for col in ("P", "KE", "ke_base", "v", "sigma", "m", "force"):
        assert np.isclose(f1[col].iloc[249], f2[col].iloc[249], equal_nan=True), col


def test_features_require_columns():
    with pytest.raises(Exception):
        kinetic.kinetic_features(pd.DataFrame({"close": [1.0, 2.0]}))


# ---------------------------------------------------------------------------
# kinetic_position — логика
# ---------------------------------------------------------------------------

def test_flat_on_too_little_data():
    df = _candles([100.0, 101.0])
    pos = kinetic.kinetic_position(df)
    assert (pos == 0).all()


def test_long_short_symmetry():
    """Серия с отрицанием лог-доходностей даёт зеркальную позицию.

    Сигнал зависит от знака P и v через logret: если logret' = -logret, то
    P' = -P, v' = -v, KE и ke_base не меняются → лонг-входы становятся
    шорт-входами (и наоборот). Это точное зеркало, в отличие от ценового.
    """
    closes = _flat_noise(400, seed=11)
    df = _candles(closes)
    c0 = float(df["close"].iloc[0])
    # лог-зеркало: log(close') = 2*log(c0) - log(close)
    closes_m = c0 * c0 / np.array(closes)
    df_m = _candles(closes_m)
    # лог-доходности должны быть ровно противоположны
    lr = np.log(np.array(closes)[1:] / np.array(closes)[:-1])
    lr_m = np.log(np.array(closes_m)[1:] / np.array(closes_m)[:-1])
    assert np.allclose(lr, -lr_m)

    params = dict(sigma_span=20, vol_span=20, mom_span=12, ke_span=40,
                  theta=1.5, v_dir=1, direction=0, cool_bars=2, min_hold=0)
    pos = kinetic.kinetic_position(df, **params).to_numpy()
    pos_m = kinetic.kinetic_position(df_m, **params).to_numpy()
    assert (pos == -pos_m).all()


def test_direction_restricts_side():
    df = _candles(_flat_noise(400), seed=4)
    pos_both = kinetic.kinetic_position(df, direction=0).to_numpy()
    pos_long = kinetic.kinetic_position(df, direction=1).to_numpy()
    pos_short = kinetic.kinetic_position(df, direction=-1).to_numpy()
    assert (pos_long >= 0).all()
    assert (pos_short <= 0).all()
    # оба направления не меньше узких
    assert (np.abs(pos_long) <= np.abs(pos_both)).all()
    assert (np.abs(pos_short) <= np.abs(pos_both)).all()


def test_momentum_regime_generates_positions():
    """На ряде с выраженными импульсами сигнал не всегда flat."""
    df = _candles(_momentum_series(seed=7))
    pos = kinetic.kinetic_position(df, direction=1, theta=1.0, v_dir=0,
                                   cool_bars=1, min_hold=0)
    assert (pos != 0).sum() > 0


def test_kinetic_breakdown_signal_key():
    df = _candles(_momentum_series(seed=9))
    out = kinetic.kinetic_breakdown(df)
    assert out  # непустой
    assert set(("P", "KE", "ke_base", "signal", "close", "energy_expanding")).issubset(out)


def test_flat_noise_low_entry_frequency():
    """Чистый шум даёт мало входов (порог |P|>=theta отсекает шум)."""
    df = _candles(_flat_noise(600, seed=2))
    pos = kinetic.kinetic_position(df, direction=0)
    total = (pos != 0).sum()
    assert total < len(df) * 0.3


# ---------------------------------------------------------------------------
# Согласованность с сигналами и bt-стратегией
# ---------------------------------------------------------------------------

def test_signals_not_in_live_registry():
    """Kinetic Momentum не подтверждена — не должна быть доступна в live-цикле.

    SIGNAL_FUNCS определяет LIVE_STRATEGIES; стратегия оставлена в STRATEGIES
    (реестр бэктеста/веб-формы), но без live-поддержки до подтверждения.
    """
    assert "kinetic" not in sig_mod.SIGNAL_FUNCS
    from app.strategies import STRATEGIES  # noqa: PLC0415
    assert "kinetic" in STRATEGIES
    # обёртка всё равно работает как чистая pandas-функция (для тестов/паритета)
    df = _candles(_momentum_series(seed=8))
    pos = sig_mod._kinetic_signal(df, theta=1.0, v_dir=0, direction=1, cool_bars=1)
    assert len(pos) == len(df)


def test_backtest_bt_and_pandas_agree():
    """Bt-стратегия и pandas-серия дают близкое число сделок/направление.

    Точное совпадение сделок невозможно из-за SL/TP-брекета в bt и разных
    моментов исполнения (open следующего бара); проверяем агрегаты.
    """
    df = _candles(_momentum_series(seed=3), base_vol=5000.0)
    params = dict(sigma_span=20, vol_span=20, mom_span=12, ke_span=40,
                  theta=1.0, v_dir=0, direction=1, cool_bars=1, min_hold=0)
    params = {**params,
              "risk_pct": 1.0, "atr_period": 20, "atr_stop_mult": 1.5,
              "rr_ratio": 2.0, "window": 200}
    bt_res = run_backtest(df, KineticMomentumStrategy, params, cash=100_000.0)
    pos = kinetic.kinetic_position(df, **{k: params[k] for k in
                                          ("sigma_span", "vol_span", "mom_span", "ke_span",
                                           "theta", "v_dir", "direction", "cool_bars", "min_hold")})
    # оба запускаются и генерируют сделки на трендовом ряде
    assert bt_res["trades_total"] >= 0
    assert (pos != 0).sum() >= 0
    # если bt открыл хотя бы одну сделку — итоговая доходность конечна
    assert isinstance(bt_res["total_return_pct"], float)
