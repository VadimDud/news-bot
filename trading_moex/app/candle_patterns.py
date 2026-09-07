"""Candle-pattern detectors (pure pandas, causal) + forward continuation stats.

Статистический инструмент: паттерны размечаются ТОЛЬКО по данным до текущего
бара (без lookahead), затем измеряется вероятность продолжения (forward
continuation) на следующих ``horizon`` барах. Два семейства:

1. **Свечные паттерны** — марубодзу, длинное тело (импульс), поглощение,
   «три солдата/три ворона» — каждый с направлением (bull → +1, bear → −1);
2. **Пробой зоны** — закрытие за пределы недавнего диапазона (консолидация):
   ``close > max(high[−zone..−1])`` → тренд вверх и наоборот.

Направление событий в ``PATTERN_SIGN``; ``detect_patterns`` возвращает
DataFrame булевых колонок (событие закрыто на баре i). ``continuation_stats``
считает win-rate/expectancy/edge против базовой ставки и z-score значимости.

Подробности/вывод: ``scripts/candle_pattern_research.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .risk import atr as _atr


# ── Сервисные функции ────────────────────────────────────────────────────────

def prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Привести df к OHLCV с datetime-индексом (как в fib_pullback.prepare_ohlc).

    Принимает либо DataFrame с datetime-индексом, либо с колонкой ``begin``
    (формат из SQLite/``storage.get_candles``). Возвращает копию.
    """
    out = df.copy()
    if "begin" in out.columns:
        out["begin"] = pd.to_datetime(out["begin"], errors="coerce")
        out = out.set_index("begin").sort_index()
    else:
        out.index = pd.to_datetime(out.index, errors="coerce")
        out = out.sort_index()
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in out.columns]
    return out[cols]


# ── Детекторы ────────────────────────────────────────────────────────────────

def _body(df: pd.DataFrame) -> pd.Series:
    return df["close"] - df["open"]


def _body_ratio(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return _body(df).abs() / rng


def detect_marubozu(df: pd.DataFrame, min_ratio: float = 0.9) -> tuple[pd.Series, pd.Series]:
    """Марубодзу: тело >= min_ratio диапазона, почти без теней (сильный импульс).

    Возвращает (bull, bear) — булевы серии: свеча с телом, покрывающим почти
    весь диапазон high-low вверх/вниз.
    """
    body = _body(df)
    rng = df["high"] - df["low"]
    strong = rng > 0
    bull = strong & (body > 0) & (_body_ratio(df) >= min_ratio)
    bear = strong & (body < 0) & (_body_ratio(df) >= min_ratio)
    return bull.fillna(False), bear.fillna(False)


def detect_strong_body(
    df: pd.DataFrame, atr_period: int = 14, atr_k: float = 1.0, body_ratio_min: float = 0.6
) -> tuple[pd.Series, pd.Series]:
    """Длинное тело (импульс): тело >= atr_k*ATR и тело/диапазон >= body_ratio_min."""
    body_abs = _body(df).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    ratio = body_abs / rng
    atr = _atr(df, atr_period)
    strong = (body_abs >= atr_k * atr) & (ratio >= body_ratio_min)
    bull = strong & (_body(df) > 0)
    bear = strong & (_body(df) < 0)
    return bull.fillna(False), bear.fillna(False)


def detect_engulfing(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Бычье/медвежье поглощение (тело поглощает тело предыдущей свечи)."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    po, pc = o.shift(1), c.shift(1)
    prev_bear, cur_bull = pc < po, c > o
    bull = prev_bear & cur_bull & (pd.concat([o, c], axis=1).min(axis=1) < pd.concat([po, pc], axis=1).min(axis=1)) \
        & (pd.concat([o, c], axis=1).max(axis=1) > pd.concat([po, pc], axis=1).max(axis=1))
    prev_bull, cur_bear = pc > po, c < o
    bear = prev_bull & cur_bear & (pd.concat([o, c], axis=1).min(axis=1) < pd.concat([po, pc], axis=1).min(axis=1)) \
        & (pd.concat([o, c], axis=1).max(axis=1) > pd.concat([po, pc], axis=1).max(axis=1))
    return bull.fillna(False), bear.fillna(False)


def detect_three_soldiers(df: pd.DataFrame, body_ratio_min: float = 0.5) -> tuple[pd.Series, pd.Series]:
    """Три солдата/три ворона: 3 однонаправленные свечи, каждый close выше/ниже
    предыдущего, open внутри тела предыдущей (без длинных теней-смены)."""
    o, c = df["open"], df["close"]
    body = _body(df)
    ratio = _body_ratio(df)
    c1, c2, c3 = c.shift(2), c.shift(1), c
    o1, o2, o3 = o.shift(2), o.shift(1), o

    soldier = (
        (body.shift(2) > 0) & (body.shift(1) > 0) & (body > 0)
        & (c1 < c2) & (c2 < c3)
        & (o2 > o1) & (o2 < c1) & (o3 > o2) & (o3 < c2)
        & (ratio.shift(2) >= body_ratio_min) & (ratio.shift(1) >= body_ratio_min)
        & (ratio >= body_ratio_min)
    )
    crow = (
        (body.shift(2) < 0) & (body.shift(1) < 0) & (body < 0)
        & (c1 > c2) & (c2 > c3)
        & (o2 < o1) & (o2 > c1) & (o3 < o2) & (o3 > c2)
        & (ratio.shift(2) >= body_ratio_min) & (ratio.shift(1) >= body_ratio_min)
        & (ratio >= body_ratio_min)
    )
    return soldier.fillna(False), crow.fillna(False)


def detect_zone_break(df: pd.DataFrame, zone: int = 20) -> tuple[pd.Series, pd.Series]:
    """Пробой зоны: close уходит за пределы диапазона предыдущих ``zone`` баров.

    Зона = консолидация; закрытие за max(high) / ниже min(low) предыдущих
    баров означает выход из равновесия → тренд. Возвращает (bull_break,
    bear_break). Используется диапазон ПРЕДЫДУЩИХ баров (без текущего).
    """
    if zone <= 1:
        raise ValueError("zone должно быть >= 2")
    prev_high = df["high"].rolling(zone).max().shift(1)
    prev_low = df["low"].rolling(zone).min().shift(1)
    bull = df["close"] > prev_high
    bear = df["close"] < prev_low
    return bull.fillna(False), bear.fillna(False)


# ── Свечные паттерны (per-bar детекторы, scalar) ────────────────────────────

def _candle_body(o: float, c: float) -> float:
    return abs(c - o)


def _lower_wick(o: float, h: float, l: float, c: float) -> float:
    return min(o, c) - l


def _upper_wick(o: float, h: float, l: float, c: float) -> float:
    return h - max(o, c)


def is_bullish_pinbar(o: float, h: float, l: float, c: float, wick_ratio: float = 2.0) -> bool:
    """Молот: тело в верхней части, длинная нижняя тень >= wick_ratio * тело."""
    body = _candle_body(o, c)
    if body <= 0:
        return False
    return _lower_wick(o, h, l, c) >= wick_ratio * body and _upper_wick(o, h, l, c) <= body


def is_bearish_pinbar(o: float, h: float, l: float, c: float, wick_ratio: float = 2.0) -> bool:
    """Падающая звезда: тело в нижней части, длинная верхняя тень."""
    body = _candle_body(o, c)
    if body <= 0:
        return False
    return _upper_wick(o, h, l, c) >= wick_ratio * body and _lower_wick(o, h, l, c) <= body


def is_bullish_engulfing(o: float, h: float, l: float, c: float, po: float, pc: float) -> bool:
    """Бычье поглощение: тело текущей бычьей свечи полностью поглощает тело предыдущей."""
    prev_bear = pc < po
    cur_bull = c > o
    return prev_bear and cur_bull and min(o, c) < min(po, pc) and max(o, c) > max(po, pc)


def is_bearish_engulfing(o: float, h: float, l: float, c: float, po: float, pc: float) -> bool:
    """Медвежье поглощение."""
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


# Словарь паттернов: имя → (детектор возвращает пару (bull, bear) | флаги).
# Направление события: bull → +1 (ожидаем рост), bear → −1 (ожидаем падение).
PATTERNS: dict[str, tuple[str, tuple[str, str]]] = {
    "marubozu": ("Марубодзу (сильный импульс)", ("bull", "bear")),
    "strong_body": ("Длинное тело ≥ ATR", ("bull", "bear")),
    "engulfing": ("Поглощение", ("bull", "bear")),
    "three_soldiers": ("Три солдата / три ворона", ("bull", "bear")),
    "zone_break": ("Пробой зоны (тренд)", ("bull", "bear")),
}


def detect_patterns(
    df: pd.DataFrame,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    zone: int = 20,
) -> pd.DataFrame:
    """Булевы колонки событий для всех паттернов (bull/bear пары).

    Возвращает DataFrame с колонками ``<pat>_bull`` / ``<pat>_bear``.
    Все индикаторы причинные: значение на баре i использует только бары <= i.
    """
    out = pd.DataFrame(index=df.index)
    mb, mb2 = detect_marubozu(df)
    out["marubozu_bull"], out["marubozu_bear"] = mb, mb2
    sb, sb2 = detect_strong_body(df, atr_period, atr_k, body_ratio_min)
    out["strong_body_bull"], out["strong_body_bear"] = sb, sb2
    eb, eb2 = detect_engulfing(df)
    out["engulfing_bull"], out["engulfing_bear"] = eb, eb2
    ts, tc = detect_three_soldiers(df, body_ratio_min)
    out["three_soldiers_bull"], out["three_soldiers_bear"] = ts, tc
    zb, zb2 = detect_zone_break(df, zone)
    out["zone_break_bull"], out["zone_break_bear"] = zb, zb2
    return out


# ── Позиция по пробою зоны (для live/бэктест-стратегии) ─────────────────────

def zone_break_position(
    df: pd.DataFrame,
    zone: int = 20,
    direction: int = 1,
    strong_candle: int = 0,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    exit_zone: int = 0,
) -> pd.Series:
    """Серия позиций (1/0) по пробою зоны консолидации.

    Зона = диапазон предыдущих ``zone`` баров (high/low). Лонг открывается при
    «свежем» пробое вверх: ``close > max(high[prev])`` на баре, который до этого
    был внутри зоны (предыдущий close <= зоны). ``strong_candle=1`` требует на
    баре пробоя длинное тело (>= atr_k*ATR и body_ratio >= body_ratio_min) —
    статистически усиливает сигнал. Выход — при обратном пробое зоны вниз
    (``exit_zone``>0) либо, по умолчанию, по серии-машине сигнала (только на
    закрытии: удержание, пока не случился новый противоположный пробой).

    Направление: ``direction`` 1 = только лонг, -1 = только шорт, 0 = оба.
    Все индикаторы причинные (без lookahead): решение на баре i — по его close.
    """
    df = prepare_ohlc(df)
    n = len(df)
    if n < max(zone, 5) + 2:
        return pd.Series(np.zeros(n, dtype=int), index=df.index)
    ph = df["high"].rolling(zone).max().shift(1)
    pl = df["low"].rolling(zone).min().shift(1)
    if exit_zone is None or exit_zone <= 0:
        exit_zone = zone
    xh = df["high"].rolling(int(exit_zone)).max().shift(1)
    xl = df["low"].rolling(int(exit_zone)).min().shift(1)

    bull_break = (df["close"] > ph) & (df["close"].shift(1) <= ph.shift(1).fillna(np.inf))
    bear_break = (df["close"] < pl) & (df["close"].shift(1) >= pl.shift(1).fillna(-np.inf))
    if int(strong_candle):
        sb, sb2 = detect_strong_body(df, atr_period, atr_k, body_ratio_min)
        bull_break = bull_break & sb
        bear_break = bear_break & sb2

    close = df["close"].to_numpy(dtype=float)
    xl_a = xl.to_numpy(dtype=float)
    xh_a = xh.to_numpy(dtype=float)
    bull_a = bull_break.to_numpy(dtype=bool)
    bear_a = bear_break.to_numpy(dtype=bool)

    pos = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        if cur == 0:
            if direction >= 0 and bull_a[i]:
                cur = 1
            elif direction <= 0 and bear_a[i]:
                cur = -1
        elif cur == 1:
            if close[i] < xl_a[i]:
                cur = 0
        else:  # cur == -1
            if close[i] > xh_a[i]:
                cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


def zone_break_state(
    df: pd.DataFrame,
    zone: int = 20,
    strong_candle: int = 0,
    atr_period: int = 14,
    atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
) -> dict:
    """Состояние пробоя зоны НА ПОСЛЕДНЕМ баре df (для bt-стратегии, причинное).

    Возвращает {bull_break, bear_break (bool — свежий пробой на текущем баре),
    xl, xh (границы зоны ПРЕДЫДУЩИХ баров для выхода)}. Используются только
    бары <= последнего — безопасно для live-цикла. Требует тёплого окна.
    """
    df = prepare_ohlc(df)
    if len(df) < zone + 3:
        return {"bull_break": False, "bear_break": False, "xl": np.nan, "xh": np.nan}
    ph = df["high"].rolling(zone).max().shift(1)
    pl = df["low"].rolling(zone).min().shift(1)
    prev_ph = ph.shift(1)
    prev_pl = pl.shift(1)
    bull_break = bool(((df["close"] > ph) & (df["close"].shift(1) <= prev_ph.fillna(np.inf))).iloc[-1])
    bear_break = bool(((df["close"] < pl) & (df["close"].shift(1) >= prev_pl.fillna(-np.inf))).iloc[-1])
    if int(strong_candle):
        sb, sb2 = detect_strong_body(df, atr_period, atr_k, body_ratio_min)
        bull_break = bool(bull_break and bool(sb.iloc[-1]))
        bear_break = bool(bear_break and bool(sb2.iloc[-1]))
    return {
        "bull_break": bull_break,
        "bear_break": bear_break,
        "xl": float(pl.iloc[-1]) if not pd.isna(pl.iloc[-1]) else np.nan,
        "xh": float(ph.iloc[-1]) if not pd.isna(ph.iloc[-1]) else np.nan,
    }


# ── Forward continuation stats ───────────────────────────────────────────────

def continuation_stats(
    df: pd.DataFrame,
    horizon: int = 5,
    min_events: int = 20,
    atr_period: int = 14,
    **detect_kw,
) -> pd.DataFrame:
    """Статистика продолжения по всем паттернам на одном тикере/ТФ.

    Событие на баре i (закрытие) → forward-доходность close[i+h]/close[i]−1
    для h = horizon. Для bull-паттерна «успех» = fwd > 0; для bear — fwd < 0.

    Возвращает DataFrame строк на паттерн-направление:
    pat (имя), side, n, win_pct, base_pct (базовая ставка для стороны),
    edge_pct (win − base), mean_atr (средний fwd в ATR-единицах, по знаку),
    z (z-score биномиального теста против base).
    """
    flags = detect_patterns(df, atr_period=atr_period, **detect_kw)
    close = df["close"].to_numpy(dtype=float)
    fwd = np.full(len(df), np.nan)
    if horizon > 0:
        fwd[: len(df) - horizon] = (
            close[horizon:] / close[: len(df) - horizon] - 1.0
        )
    atr = _atr(df, atr_period).to_numpy(dtype=float)

    # Базовая ставка: доля баров, где следующий close выше текущего.
    valid = ~np.isnan(fwd)
    base_up = float((fwd[valid] > 0).mean()) if valid.any() else np.nan
    base_down = 1.0 - base_up if not np.isnan(base_up) else np.nan

    rows = []
    atr_frac = np.where((atr > 0) & (close > 0) & ~np.isnan(atr), atr / close, np.nan)
    for col in flags.columns:
        side = "bull" if col.endswith("_bull") else "bear"
        ev = flags[col].to_numpy(dtype=bool)
        # Только «свежие» события: первый бар серии True. Для зонных пробоев
        # (zone_break) иначе серия из N дней подряд выше зоны даёт N одинаковых
        # событий с одной информацией (автокорреляция завышает n и z).
        fresh = ev.copy()
        if len(ev) > 1:
            fresh[1:] = ev[1:] & ~ev[:-1]
        idx = np.where(fresh & ~np.isnan(fwd))[0]
        if len(idx) < min_events:
            continue
        vals = fwd[idx]
        base = base_up if side == "bull" else base_down
        wins = (vals > 0) if side == "bull" else (vals < 0)
        n = int(len(vals))
        win_pct = float(wins.mean()) * 100.0
        # edge в %: (win − base). z-score биномиального теста.
        p0 = base if not np.isnan(base) else 0.5
        z = 0.0
        if 0 < p0 < 1:
            se = np.sqrt(p0 * (1 - p0) / n)
            z = float((wins.mean() - p0) / se) if se > 0 else 0.0
        # Средний forward в единицах ATR/цену (доли цены), по знаку стороны.
        scale = atr_frac[idx]
        ok = scale == scale
        mean_atr = 0.0
        if ok.any():
            mean_atr = float(np.mean(vals[ok] / scale[ok]))
        if side == "bear":
            mean_atr = -mean_atr
        rows.append({
            "pattern": col.replace("_" + side, ""),
            "side": side,
            "n": n,
            "win_pct": round(win_pct, 1),
            "base_pct": round(base * 100.0, 1),
            "edge_pct": round(win_pct - base * 100.0, 1),
            "mean_atr": round(mean_atr, 3),
            "z": round(z, 2),
        })
    return pd.DataFrame(rows)
