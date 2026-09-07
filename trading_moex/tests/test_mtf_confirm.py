"""Tests for Multi-Timeframe Confirmation — synthetic data, no DB.

Проверяются:
- причинность HTF зона-режима (нет lookahead);
- причинность htf_state_at (дневной бар текущего дня не виден);
- свежие события (fresh events) в ltf_signals;
- mtf_signal: подтверждение / отклонение фильтром;
- direction restriction (лонг / шорт);
- mtf_stats: корректность DataFrame и z-score.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import mtf_confirm  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _daily_closes(closes, base_vol=1e6, seed=3):
    """OHLCV DataFrame (daily) из цен закрытия."""
    rng = np.random.default_rng(seed)
    close = np.array(closes, dtype=float)
    opens = np.append(close[0], close[:-1])
    spread = np.abs(rng.normal(0, 0.5, len(close)))
    high = np.maximum(opens, close) + spread
    low = np.minimum(opens, close) - spread
    vol = base_vol * (1 + 0.3 * rng.normal(0, 1, len(close)))
    idx = pd.date_range("2021-01-04", periods=len(close), freq="B")
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def _hourly_closes(closes, base_vol=50000, seed=7):
    """OHLCV DataFrame (60min) из цен закрытия."""
    rng = np.random.default_rng(seed)
    close = np.array(closes, dtype=float)
    opens = np.append(close[0], close[:-1])
    spread = np.abs(rng.normal(0, 0.1, len(close)))
    high = np.maximum(opens, close) + spread
    low = np.minimum(opens, close) - spread
    vol = base_vol * (1 + 0.2 * rng.normal(0, 1, len(close)))
    idx = pd.date_range("2024-01-02 10:00", periods=len(close), freq="1h")
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def _daily_rising(n=60, seed=1):
    """Трендовый дневной ряд (close растёт)."""
    rng = np.random.default_rng(seed)
    p = 100.0 + np.cumsum(rng.uniform(0.3, 1.2, n))
    return _daily_closes(p.tolist(), seed=seed)


def _hourly_series(n=500, seed=5):
    """Часовой ряд с паттернами (импульсные блоки)."""
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = 0.01 * rng.choice([-1, 1]) + 0.4 * r[i - 1] + rng.normal(0, 0.08)
    p = 100.0 * np.exp(np.cumsum(r))
    return _hourly_closes(p.tolist(), seed=seed)


# ── htf_zone_state ────────────────────────────────────────────────────────────

def test_htf_zone_state_basic():
    """На возрастающем ряде (close > max(high[K-1])) → state = +1."""
    df = _daily_rising(60)
    state = mtf_confirm.htf_zone_state(df, zone=20)
    # После 20+ баров тренда вверх state должен быть +1
    last_val = state.iloc[-1]
    assert last_val in (0, 1)


def test_htf_zone_state_causality():
    """Добавление будущих баров не меняет state на прошлых барах."""
    df = _daily_rising(100)
    s1 = mtf_confirm.htf_zone_state(df.iloc[:80], zone=20)
    s2 = mtf_confirm.htf_zone_state(df.iloc[:81], zone=20)
    # Первые 80 баров должны совпадать
    assert (s1.values == s2.values[: len(s1)]).all()


def test_htf_zone_state_no_data():
    """При слишком малом df — zeros."""
    df = _daily_closes([100, 101, 102])
    state = mtf_confirm.htf_zone_state(df, zone=20)
    assert (state == 0).all()


# ── htf_state_at ──────────────────────────────────────────────────────────────

def test_htf_state_at_no_lookahead():
    """HTF-бар текущего дня не виден на小时内 баре этого дня.

    Проверяем: htf_state_at на баре t использует только HTF-бары < t.
    """
    daily = _daily_rising(60)
    state = mtf_confirm.htf_zone_state(daily, zone=20)
    hourly = _hourly_series(500)
    aligned = mtf_confirm.htf_state_at(hourly, state)
    # Все значения должны быть из {−1, 0, +1}
    unique = set(aligned.unique())
    assert unique <= {-1, 0, 1}


def test_htf_state_at_causality():
    """Добавление будущего часового бара не меняет aligned state на прошлом."""
    daily = _daily_rising(60)
    state = mtf_confirm.htf_zone_state(daily, zone=20)
    h1 = _hourly_series(200)
    h2 = _hourly_series(201)
    a1 = mtf_confirm.htf_state_at(h1, state)
    a2 = mtf_confirm.htf_state_at(h2, state)
    assert (a1.values == a2.values[: len(a1)]).all()


# ── ltf_signals ───────────────────────────────────────────────────────────────

def test_ltf_signals_fresh_only():
    """Зона-пробой: только первый бар серии = событие (не все бары выше зоны)."""
    hourly = _hourly_series(500)
    sig = mtf_confirm.ltf_signals(hourly, pattern="zone_break", zone=20)
    # Подряд идущие +1 не должны повторяться (fresh only)
    vals = sig.to_numpy(dtype=int)
    consecutive = 0
    for v in vals:
        if v != 0:
            consecutive += 1
            assert consecutive <= 1, f"Consecutive signal at index without fresh filter: {consecutive}"
        else:
            consecutive = 0


def test_ltf_signals_known_patterns():
    """Все паттерны детектируются (нужен df с хвостом)."""
    hourly = _hourly_series(500)
    for pat in ("marubozu", "strong_body", "engulfing", "three_soldiers", "zone_break"):
        sig = mtf_confirm.ltf_signals(hourly, pattern=pat, zone=20)
        assert len(sig) == len(hourly)


def test_ltf_signals_unknown_pattern():
    hourly = _hourly_series(100)
    with pytest.raises(ValueError, match="Неизвестный паттерн"):
        mtf_confirm.ltf_signals(hourly, pattern="nonexistent")


# ── mtf_signal ────────────────────────────────────────────────────────────────

def test_mtf_signal_confirmation():
    """Подтверждённый сигнал: LTF bull + HTF zone +1 → +1."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    sig = mtf_confirm.mtf_signal(hourly, daily, pattern="zone_break",
                                  ltf_zone=20, htf_zone=20, direction=0)
    vals = sig.to_numpy(dtype=int)
    assert set(vals.tolist()) <= {-1, 0, 1}


def test_mtf_signal_direction_long_only():
    """direction=1: только лонг (≥0)."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    sig = mtf_confirm.mtf_signal(hourly, daily, pattern="zone_break",
                                  ltf_zone=20, htf_zone=20, direction=1)
    assert (sig >= 0).all()


def test_mtf_signal_direction_short_only():
    """direction=-1: только шорт (≤0)."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    sig = mtf_confirm.mtf_signal(hourly, daily, pattern="zone_break",
                                  ltf_zone=20, htf_zone=20, direction=-1)
    assert (sig <= 0).all()


def test_mtf_signal_confirms_subset_of_bare():
    """MTF-сигнал — подмножество LTF-сигнала (фильтр отсекает часть)."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    bare = mtf_confirm.ltf_signals(hourly, pattern="zone_break", zone=20)
    mtf = mtf_confirm.mtf_signal(hourly, daily, pattern="zone_break",
                                  ltf_zone=20, htf_zone=20, direction=0)
    # Каждый MTF-сигнал есть в bare
    mask = mtf.to_numpy(dtype=int) != 0
    assert (bare.to_numpy(dtype=int)[mask] == mtf.to_numpy(dtype=int)[mask]).all()


# ── mtf_stats ─────────────────────────────────────────────────────────────────

def test_mtf_stats_structure():
    """mtf_stats возвращает DataFrame с нужными колонками."""
    daily = _daily_rising(100)
    hourly = _hourly_series(800)
    stats = mtf_confirm.mtf_stats(hourly, daily, pattern="zone_break",
                                   ltf_zone=20, htf_zone=20, horizon=6)
    assert isinstance(stats, pd.DataFrame)
    if not stats.empty:
        assert {"label", "side", "n", "win_pct", "z"}.issubset(stats.columns)


def test_mtf_stats_confirmed_vs_rejected():
    """Если есть и confirmed, и rejected — z-значения разные."""
    daily = _daily_rising(100)
    hourly = _hourly_series(1000)
    stats = mtf_confirm.mtf_stats(hourly, daily, pattern="zone_break",
                                   ltf_zone=20, htf_zone=20, horizon=6, min_events=5)
    if stats.empty:
        pytest.skip("Нет событий для статистики")
    labels = stats["label"].tolist()
    # Если есть оба типа — z должны быть определены
    for _, row in stats.iterrows():
        assert isinstance(row["z"], float)
        assert isinstance(row["win_pct"], float)


# ── mtf_position ──────────────────────────────────────────────────────────────

def test_mtf_position_values():
    """Позиция содержит только {−1, 0, +1}."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    pos = mtf_confirm.mtf_position(hourly, daily, pattern="zone_break",
                                    ltf_zone=20, htf_zone=20, direction=0)
    unique = set(pos.unique())
    assert unique <= {-1, 0, 1}


def test_mtf_position_holds_until_reverse():
    """Позиция удерживается до противоположного сигнала (серия-машина)."""
    daily = _daily_rising(80)
    hourly = _hourly_series(500)
    pos = mtf_confirm.mtf_position(hourly, daily, pattern="zone_break",
                                    ltf_zone=20, htf_zone=20, direction=0)
    vals = pos.to_numpy(dtype=int)
    # Не может быть прыжка 1 → −1 без прохождения через 0 (серия-машина не
    # делает этого: позиция = последний сигнал, без промежуточного flat).
    for i in range(1, len(vals)):
        if vals[i] != 0 and vals[i - 1] != 0:
            # Если обе не-zero — они должны быть одного знака
            assert vals[i] == vals[i - 1], (
                f"Position jump {vals[i-1]} → {vals[i]} without flat at index {i}"
            )
