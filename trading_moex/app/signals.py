"""Чистые функции сигналов на pandas (без зависимости от backtrader).

Используются live-циклом и покрываются юнит-тестами. Backtrader-стратегии
в ``strategies.py`` повторяют ту же логику для бэктеста.
"""

import numpy as np
import pandas as pd

POSITION_KEY = "position"


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def sma_cross_position(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.Series:
    close = df["close"]
    f = sma(close, fast)
    s = sma(close, slow)
    return (f > s).astype(int)


def rsi_position(
    df: pd.DataFrame, period: int = 14, buy_threshold: float = 30, sell_threshold: float = 70
) -> pd.Series:
    values = rsi(df["close"], period).values
    pos = np.zeros(len(values), dtype=int)
    cur = 0
    for i, val in enumerate(values):
        if cur == 0 and val < buy_threshold:
            cur = 1
        elif cur == 1 and val > sell_threshold:
            cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


def donchian_position(df: pd.DataFrame, period: int = 20) -> pd.Series:
    high = df["high"].rolling(period, min_periods=1).max()
    low = df["low"].rolling(period, min_periods=1).min()
    close = df["close"].values
    prev_high = high.shift(1).values
    prev_low = low.shift(1).values
    pos = np.zeros(len(df), dtype=int)
    cur = 0
    for i in range(len(df)):
        if cur == 0 and i > 0 and close[i] > prev_high[i]:
            cur = 1
        elif cur == 1 and i > 0 and close[i] < prev_low[i]:
            cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


SIGNAL_FUNCS = {
    "sma_cross": sma_cross_position,
    "rsi": rsi_position,
    "donchian": donchian_position,
}


def signal_from_position(pos: pd.Series) -> str:
    """Вернуть действие по последней паре баров: buy / sell / hold."""
    if len(pos) < 2:
        return "hold"
    if pos.iloc[-1] == 1 and pos.iloc[-2] == 0:
        return "buy"
    if pos.iloc[-1] == 0 and pos.iloc[-2] == 1:
        return "sell"
    return "hold"
