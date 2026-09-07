"""Multi-timeframe confirmation: LTF signal + HTF zone filter (pure pandas).

Архитектура:
- **Сигнал (LTF, например 1h):** свечной паттерн (marubozu / strong_body /
  engulfing / three_soldiers / zone_break) на закрытии бара ``t``.
- **Фильтр (HTF, например 1day):** зона-режим — ``close > max(high[K])``
  → +1 (рост), ``close < min(low[K])`` → −1 (падение), иначе 0.
- Вход только при ``S(t)·F(t) > 0`` (сигнал согласен с HTF-режимом).

Всё причинное: на баре ``t`` видны только данные ≤ ``t``. Дневной бар текущего
дня **не используется** (его close ещё неизвестен) — используется последний
завершённый бар строго до ``t``.

Подробнее: ``scripts/candle_pattern_mtf_research.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .candle_patterns import (
    detect_marubozu,
    detect_strong_body,
    detect_engulfing,
    detect_three_soldiers,
    detect_zone_break,
    prepare_ohlc,
)
from .risk import atr as _atr


# ── HTF зона-режим ───────────────────────────────────────────────────────────

def htf_zone_state(
    htf_df: pd.DataFrame,
    zone: int = 20,
) -> pd.Series:
    """Зона-режим на HTF: +1 (bull zone), −1 (bear zone), 0 (внутри зоны).

    Используются данные строго до текущего бара (cause-only):
    ``bull = close > max(high[−zone..−1])``, ``bear = close < min(low[−zone..−1])``.
    """
    htf = prepare_ohlc(htf_df)
    if len(htf) < zone + 2:
        return pd.Series(np.zeros(len(htf), dtype=int), index=htf.index)
    prev_high = htf["high"].rolling(zone).max().shift(1)
    prev_low = htf["low"].rolling(zone).min().shift(1)
    state = pd.Series(0, index=htf.index, dtype=int)
    state[htf["close"] > prev_high] = 1
    state[htf["close"] < prev_low] = -1
    return state


# ── HTF MA-режим ─────────────────────────────────────────────────────────────

def htf_ma_state(
    htf_df: pd.DataFrame,
    fast: int = 20,
    slow: int | None = None,
    atr_neutral: float = 0.0,
) -> pd.Series:
    """MA-режим на HTF: +1 (bull), −1 (bear), 0 (нейтраль/неопределённость).

    Одна MA: ``sign(close − EMA(fast))``. Две MA: ``sign(EMA(fast) − EMA(slow))``.
    ``atr_neutral > 0``: нейтральная зона ±k·ATR حول MA — внутри 0.

    Всё причинное: используем только завершённые бары (shifted).
    """
    htf = prepare_ohlc(htf_df)
    if len(htf) < max(fast, slow or 0, 5) + 2:
        return pd.Series(np.zeros(len(htf), dtype=int), index=htf.index)
    close = htf["close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    if slow and slow > 0:
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        diff = ema_fast - ema_slow
        state = pd.Series(0, index=htf.index, dtype=int)
        state[diff > 0] = 1
        state[diff < 0] = -1
    else:
        diff = close - ema_fast
        state = pd.Series(0, index=htf.index, dtype=int)
        state[diff > 0] = 1
        state[diff < 0] = -1
    if atr_neutral > 0:
        atr = _atr(htf, 14)
        neutral_zone = atr_neutral * atr
        inside = diff.abs() <= neutral_zone
        state[inside] = 0
    return state


# ── Causes-only alignment: HTF state → LTF timestamps ───────────────────────

def htf_state_at(
    ltf_df: pd.DataFrame,
    htf_state: pd.Series,
) -> pd.Series:
    """Привязать HTF-состояние к каждому бару LTF (cause-only).

    Для бара ``t`` (LTF) берётся состояние последнего HTF-бара, чей timestamp
    строго **< t** (не ≤). Это исключает lookahead: дневной бар, содержащий
    текущий часовой бар, ещё не закрыт.
    """
    ltf = prepare_ohlc(ltf_df)
    ltf_idx = ltf.index
    htf_idx = htf_state.index.sort_values()
    out = np.zeros(len(ltf), dtype=int)
    htf_arr = htf_state.reindex(htf_idx).to_numpy(dtype=int)
    htf_ts = htf_idx.values  # numpy datetime64

    for i, t in enumerate(ltf_idx.values):
        # Последний HTF-бар строго до t
        mask = htf_ts < t
        if mask.any():
            out[i] = int(htf_arr[mask][-1])
    return pd.Series(out, index=ltf_idx)


# ── Сигналы LTF ──────────────────────────────────────────────────────────────

_PATTERNS = {
    "marubozu": lambda df, **kw: detect_marubozu(df, **kw),
    "strong_body": lambda df, **kw: detect_strong_body(df, **kw),
    "engulfing": lambda df, **kw: detect_engulfing(df),
    "three_soldiers": lambda df, **kw: detect_three_soldiers(df, **kw),
    "zone_break": lambda df, **kw: detect_zone_break(df, **kw),
}


def ltf_signals(
    df: pd.DataFrame,
    pattern: str = "zone_break",
    zone: int = 20,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
) -> pd.Series:
    """Свечной паттерн на LTF → серия знаков: +1 (bull), −1 (bear), 0 (нет).

    Только «свежие» события: первый бар серии True (для zone_break иначе
    серия из N баров выше зоны даёт N событий с одной информацией).
    """
    df = prepare_ohlc(df)
    det = _PATTERNS.get(pattern)
    if det is None:
        raise ValueError(f"Неизвестный паттерн: {pattern}. Доступны: {list(_PATTERNS)}")
    kw = {}
    if pattern in ("zone_break",):
        kw["zone"] = zone
    if pattern == "strong_body":
        kw["atr_period"] = atr_period
        kw["atr_k"] = atr_k
        kw["body_ratio_min"] = body_ratio_min
    if pattern == "three_soldiers":
        kw["body_ratio_min"] = body_ratio_min
    bull, bear = det(df, **kw)
    bull_np = bull.to_numpy(dtype=bool)
    bear_np = bear.to_numpy(dtype=bool)
    # свежие события
    if len(bull_np) > 1:
        fresh_bull = bull_np.copy()
        fresh_bull[1:] = bull_np[1:] & ~bull_np[:-1]
        fresh_bear = bear_np.copy()
        fresh_bear[1:] = bear_np[1:] & ~bear_np[:-1]
    else:
        fresh_bull, fresh_bear = bull_np, bear_np
    out = np.zeros(len(df), dtype=int)
    out[fresh_bull] = 1
    out[fresh_bear] = -1
    return pd.Series(out, index=df.index)


# ── Комбинированный MTF-сигнал ───────────────────────────────────────────────

def _compute_htf_state(
    htf_df: pd.DataFrame,
    htf_filter: str = "zone",
    htf_zone: int = 20,
    htf_ma_fast: int = 20,
    htf_ma_slow: int = 50,
    htf_atr_neutral: float = 0.0,
) -> pd.Series:
    """Диспетчер HTF-фильтра: 'zone' | 'ma_single' | 'ma_cross'."""
    if htf_filter == "ma_single":
        return htf_ma_state(htf_df, fast=htf_ma_fast, slow=None, atr_neutral=htf_atr_neutral)
    elif htf_filter == "ma_cross":
        return htf_ma_state(htf_df, fast=htf_ma_fast, slow=htf_ma_slow, atr_neutral=htf_atr_neutral)
    else:  # "zone"
        return htf_zone_state(htf_df, zone=htf_zone)


def mtf_signal(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    htf_filter: str = "zone",
    htf_ma_fast: int = 20,
    htf_ma_slow: int = 50,
    htf_atr_neutral: float = 0.0,
) -> pd.Series:
    """Комбинированный сигнал: LTF-паттерн + HTF-фильтр.

    ``htf_filter``: 'zone' (пробой диапазона), 'ma_single' (close vs EMA),
    'ma_cross' (EMA fast vs EMA slow).

    Возвращает серию знаков: +1 (подтверждённый bull), −1 (подтверждённый
    bear), 0 (нет сигнала / фильтр не подтверждает).

    ``direction``: 1 = только лонг, -1 = только шорт, 0 = обе стороны.
    """
    sig = ltf_signals(ltf_df, pattern=pattern, zone=ltf_zone,
                      atr_period=atr_period, atr_k=atr_k, body_ratio_min=body_ratio_min)
    htf_state = _compute_htf_state(htf_df, htf_filter=htf_filter, htf_zone=htf_zone,
                                    htf_ma_fast=htf_ma_fast, htf_ma_slow=htf_ma_slow,
                                    htf_atr_neutral=htf_atr_neutral)
    filt = htf_state_at(ltf_df, htf_state)
    sig_np = sig.to_numpy(dtype=int)
    filt_np = filt.to_numpy(dtype=int)
    out = np.zeros(len(sig), dtype=int)
    for i in range(len(sig)):
        s, f = int(sig_np[i]), int(filt_np[i])
        if s != 0 and f != 0 and s == f:
            out[i] = s
    if direction == 1:
        out = np.where(out > 0, out, 0)
    elif direction == -1:
        out = np.where(out < 0, out, 0)
    return pd.Series(out, index=sig.index)


# ── Forward continuation stats (MTF) ─────────────────────────────────────────

def mtf_stats(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    horizon: int = 6,
    direction: int = 0,
    min_events: int = 20,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    htf_filter: str = "zone",
    htf_ma_fast: int = 20,
    htf_ma_slow: int = 50,
    htf_atr_neutral: float = 0.0,
) -> pd.DataFrame:
    """Статистика продолжения: с фильтром vs без фильтра vs базовая ставка.

    ``htf_filter``: 'zone' | 'ma_single' | 'ma_cross'.
    """
    ltf = prepare_ohlc(ltf_df)
    sig = ltf_signals(ltf, pattern=pattern, zone=ltf_zone,
                      atr_period=atr_period, atr_k=atr_k, body_ratio_min=body_ratio_min)
    htf_state = _compute_htf_state(htf_df, htf_filter=htf_filter, htf_zone=htf_zone,
                                    htf_ma_fast=htf_ma_fast, htf_ma_slow=htf_ma_slow,
                                    htf_atr_neutral=htf_atr_neutral)
    filt = htf_state_at(ltf, htf_state)
    close = ltf["close"].to_numpy(dtype=float)
    atr_arr = _atr(ltf, atr_period).to_numpy(dtype=float)
    atr_frac = np.where((atr_arr > 0) & (close > 0) & ~np.isnan(atr_arr), atr_arr / close, np.nan)
    # forward return (вход по close, выход по close+h)
    fwd = np.full(len(ltf), np.nan)
    if horizon > 0 and len(ltf) > horizon:
        fwd[: len(ltf) - horizon] = close[horizon:] / close[: len(ltf) - horizon] - 1.0
    valid = ~np.isnan(fwd)
    base_up = float((fwd[valid] > 0).mean()) if valid.any() else np.nan
    base_down = 1.0 - base_up if not np.isnan(base_up) else np.nan

    sig_np = sig.to_numpy(dtype=int)
    filt_np = filt.to_numpy(dtype=int)

    def _stats_for(mask: np.ndarray, side: str) -> dict | None:
        idx = np.where(mask & ~np.isnan(fwd))[0]
        if len(idx) < min_events:
            return None
        vals = fwd[idx]
        p0 = base_up if side == "bull" else base_down
        if np.isnan(p0):
            p0 = 0.5
        wins = (vals > 0) if side == "bull" else (vals < 0)
        n = int(len(vals))
        win_pct = float(wins.mean()) * 100.0
        se = np.sqrt(p0 * (1 - p0) / n) if 0 < p0 < 1 else 0.0
        z = float((wins.mean() - p0) / se) if se > 0 else 0.0
        ok = ~np.isnan(atr_frac[idx])
        mean_atr = 0.0
        if ok.any():
            sub_idx = idx[ok]
            mean_atr = float(np.nanmean(vals[ok] / atr_frac[sub_idx]))
        if side == "bear":
            mean_atr = -mean_atr
        return {
            "n": n,
            "win_pct": round(win_pct, 1),
            "base_pct": round(p0 * 100.0, 1),
            "edge_pct": round(win_pct - p0 * 100.0, 1),
            "mean_atr": round(mean_atr, 3),
            "z": round(z, 2),
        }

    rows = []
    for side, sign in (("bull", 1), ("bear", -1)):
        side_mask = sig_np == sign
        # 1) без фильтра (все события)
        r = _stats_for(side_mask, side)
        if r:
            rows.append({"label": "no_filter", "side": side, **r})
        # 2) confirmed (S·F > 0)
        confirmed_mask = side_mask & (filt_np == sign)
        r = _stats_for(confirmed_mask, side)
        if r:
            rows.append({"label": "confirmed", "side": side, **r})
        # 3) rejected (S есть, но F не совпадает или = 0)
        rejected_mask = side_mask & (filt_np != sign)
        r = _stats_for(rejected_mask, side)
        if r:
            rows.append({"label": "rejected", "side": side, **r})

    return pd.DataFrame(rows)


# ── Position series (для backtrader / анализа) ───────────────────────────────

def mtf_position(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    htf_filter: str = "zone",
    htf_ma_fast: int = 20,
    htf_ma_slow: int = 50,
    htf_atr_neutral: float = 0.0,
) -> pd.Series:
    """Позиция (1/−1/0) по MTF-сигналу: удержание до противоположного сигнала."""
    sig = mtf_signal(ltf_df, htf_df, pattern=pattern, ltf_zone=ltf_zone,
                     htf_zone=htf_zone, direction=direction, atr_period=atr_period,
                     atr_k=atr_k, body_ratio_min=body_ratio_min,
                     htf_filter=htf_filter, htf_ma_fast=htf_ma_fast,
                     htf_ma_slow=htf_ma_slow, htf_atr_neutral=htf_atr_neutral)
    sig_np = sig.to_numpy(dtype=int)
    pos = np.zeros(len(sig), dtype=int)
    cur = 0
    for i in range(len(sig)):
        if sig_np[i] != 0:
            cur = sig_np[i]
        pos[i] = cur
    return pd.Series(pos, index=sig.index)
