"""Риск-менеджмент: ATR, дистанция стопа, размер позиции от % риска.

Правила Карен Фу, переведённые в математику:
- риск на сделку не более ``risk_pct`` (1–2 %) от капитала;
- стоп-лосс по ATR (``atr_stop_mult * ATR``);
- тейк-профит по соотношению R:R (``rr_ratio * дистанция стопа``);
- лот = риск-сумма / дистанция стопа.
"""

import numpy as np
import pandas as pd

DEFAULT_ATR_PERIOD = 14
DEFAULT_ATR_STOP_MULT = 1.5
DEFAULT_RR_RATIO = 2.0


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = DEFAULT_ATR_PERIOD) -> pd.Series:
    """Average True Range (Wilder-сглаживание, как в большинстве терминалов)."""
    tr = true_range(df)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def stop_distance(
    df: pd.DataFrame,
    period: int = DEFAULT_ATR_PERIOD,
    atr_mult: float = DEFAULT_ATR_STOP_MULT,
) -> pd.Series:
    """Дистанция стоп-лосса в единицах цены: ``atr_mult * ATR``."""
    return atr(df, period) * atr_mult


def stop_price(df: pd.DataFrame, period: int, atr_mult: float, side: str = "long") -> pd.Series:
    """Цена стоп-лосса: для лонга ниже текущего close."""
    dist = stop_distance(df, period, atr_mult)
    if side == "long":
        return df["close"] - dist
    return df["close"] + dist


def target_price(
    df: pd.DataFrame,
    period: int = DEFAULT_ATR_PERIOD,
    atr_mult: float = DEFAULT_ATR_STOP_MULT,
    rr_ratio: float = DEFAULT_RR_RATIO,
    side: str = "long",
) -> pd.Series:
    """Цена тейк-профита: дистанция стопа, умноженная на R:R."""
    dist = stop_distance(df, period, atr_mult) * rr_ratio
    if side == "long":
        return df["close"] + dist
    return df["close"] - dist


def position_size(equity: float, risk_pct: float, stop_distance_value: float, price: float) -> int:
    """Размер позиции (лот) так, чтобы риск по сделке = ``risk_pct`` от капитала.

    ``risk_pct`` — доля (0.01 = 1 %). Лот округляется вниз, минимум 1.
    """
    if equity <= 0 or price <= 0 or stop_distance_value <= 0:
        return 1
    risk_amount = equity * risk_pct
    size = int(risk_amount / stop_distance_value)
    return max(size, 1)


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"
