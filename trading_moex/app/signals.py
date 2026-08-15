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


# ── Трендовый фильтр ────────────────────────────────────────────────────────

def apply_trend_filter(
    position: pd.Series, close: pd.Series, trend_period: int = 200
) -> pd.Series:
    """Торговать только по тренду: длинные позиции разрешены выше EMA.

    ``trend_period <= 0`` — фильтр выключен. Правило Карен Фу: покупки только
    выше скользящей средней (по умолчанию EMA 200).
    """
    if not trend_period or trend_period <= 0:
        return position
    ema = close.ewm(span=trend_period, adjust=False).mean()
    filtered = position.copy()
    filtered[close < ema] = 0
    return filtered


# ── Свечные паттерны ────────────────────────────────────────────────────────

def _body(o: float, c: float) -> float:
    return abs(c - o)


def _lower_wick(o: float, h: float, l: float, c: float) -> float:
    return min(o, c) - l


def _upper_wick(o: float, h: float, l: float, c: float) -> float:
    return h - max(o, c)


def is_bullish_pinbar(o: float, h: float, l: float, c: float, wick_ratio: float = 2.0) -> bool:
    """Молот: тело в верхней части, длинная нижняя тень >= wick_ratio * тело."""
    body = _body(o, c)
    if body <= 0:
        return False
    return _lower_wick(o, h, l, c) >= wick_ratio * body and _upper_wick(o, h, l, c) <= body


def is_bearish_pinbar(o: float, h: float, l: float, c: float, wick_ratio: float = 2.0) -> bool:
    """Падающая звезда: тело в нижней части, длинная верхняя тень."""
    body = _body(o, c)
    if body <= 0:
        return False
    return _upper_wick(o, h, l, c) >= wick_ratio * body and _lower_wick(o, h, l, c) <= body


def is_bullish_engulfing(o: float, h: float, l: float, c: float, po: float, pc: float) -> bool:
    """Бычье поглощение: тело текущей бычьей свечи полностью поглощает тело предыдущей."""
    prev_bear = pc < po
    cur_bull = c > o
    return prev_bear and cur_bull and min(o, c) < min(po, pc) and max(o, c) > max(po, pc)


def is_bearish_engulfing(o: float, h: float, l: float, c: float, po: float, pc: float) -> bool:
    prev_bull = pc > po
    cur_bear = c < o
    return prev_bull and cur_bear and min(o, c) < min(po, pc) and max(o, c) > max(po, pc)


def volume_confirms(vol: float, avg_vol: float, vol_mult: float, vol_period: int) -> bool:
    """Подтверждение сигнала объёмом: объём свечи не ниже среднего с множителем.

    ``vol_period <= 0`` — фильтр выключен; при NaN/нулевом среднем (тёплый
    период индикатора) требуем просто ненулевой объём.
    """
    if vol_period <= 0:
        return True
    if avg_vol != avg_vol or avg_vol <= 0:
        return vol > 0
    return vol >= vol_mult * avg_vol


def bulls_dominate(high: float, low: float, close: float, bull_frac: float) -> bool:
    """Доля «быков» на свече: close ближе к high, чем к low (покупки двигают цену).

    ``bull_frac <= 0`` — выключено; при нулевом диапазоне свечи — False.
    """
    if bull_frac <= 0:
        return True
    rng = high - low
    if rng <= 0:
        return False
    return (close - low) / rng >= bull_frac


def pinbar_position(df: pd.DataFrame, wick_ratio: float = 2.0) -> pd.Series:
    """Вход на бычьем пин-баре (молот), выход на медвежьем (падающая звезда)."""
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    pos = np.zeros(len(df), dtype=int)
    cur = 0
    for i in range(1, len(df)):
        if cur == 0:
            if is_bullish_pinbar(o[i], h[i], l[i], c[i], wick_ratio):
                cur = 1
        elif is_bearish_pinbar(o[i], h[i], l[i], c[i], wick_ratio):
            cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


def engulfing_position(df: pd.DataFrame) -> pd.Series:
    """Вход на бычьем поглощении, выход на медвежьем поглощении."""
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    pos = np.zeros(len(df), dtype=int)
    cur = 0
    for i in range(1, len(df)):
        if cur == 0:
            if is_bullish_engulfing(o[i], h[i], l[i], c[i], o[i - 1], c[i - 1]):
                cur = 1
        elif is_bearish_engulfing(o[i], h[i], l[i], c[i], o[i - 1], c[i - 1]):
            cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


SIGNAL_FUNCS = {
    "sma_cross": sma_cross_position,
    "rsi": rsi_position,
    "donchian": donchian_position,
    "pinbar": pinbar_position,
    "engulfing": engulfing_position,
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
