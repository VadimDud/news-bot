"""Fibonacci Retracement trend-continuation strategy (pure pandas functions).

Логика перенесена с ручного фибо-анализа на математику (см. видеокурс
"7 Fibonacci Trading Hacks"):

1. Market Regime Filter — вход только в тренде (close > EMA) при умеренной
   волатильности (ATR/close ниже потолка) и (опц.) ADX выше порога;
2. Swing Points — фракталы Билла Вильямса: локальные минимумы/максимумы за
   ``swing_bars`` свечей с подтверждением; фильтр минимального хода импульса;
3. Discount Zone — покупка только при откате цены в зону [fib_in_low .. fib_in_high]
   от последнего импульса (swing low → swing high) для положительного RRR;
4. Multi-Factor Confluence — вход при совпадении зоны Фибо + свечного паттерна +
   RSI перепроданности (минимум ``confluence_min`` факторов);
5. Higher Timeframe — опциональный фильтр глобального тренда: LTF-вход только
   в направлении тренда старшего таймфрейма (``htf_df``);
6. Risk — структурный стоп за экстремум + RRR-гейт (см. backtrader-стратегию).

Не зависит от backtrader — используется live-циклом и покрывается тестами.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
from .timezones import as_utc_naive_index

from .risk import atr as _atr, true_range as _true_range


# ── Сервисные функции ────────────────────────────────────────────────────────

def prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Привести df к индексированному OHLCV (open, high, low, close, volume).

    Принимает либо DataFrame с datetime-индексом, либо с колонкой ``begin``
    (формат из SQLite/``storage.get_candles``). Возвращает копию.
    """
    out = df.copy()
    if "begin" in out.columns:
        out["begin"] = as_utc_naive_index(out["begin"], errors="coerce")
        out = out.set_index("begin").sort_index()
    else:
        out.index = as_utc_naive_index(out.index, errors="coerce")
        out = out.sort_index()
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in out.columns]
    return out[cols]


def _ema(series: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        return pd.Series(np.nan, index=series.index)
    return series.ewm(span=period, adjust=False).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ADX (14); потокобезопасно на чистом pandas. Возвращает серию."""
    if period <= 0 or len(df) == 0:
        return pd.Series(np.nan, index=df.index)
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = _true_range(df)
    atr_ = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    pdm = pd.Series(plus_dm, index=df.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean()
    mdm = pd.Series(minus_dm, index=df.index).ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean()
    plus_di = 100.0 * (pdm / atr_.replace(0, np.nan))
    minus_di = 100.0 * (mdm / atr_.replace(0, np.nan))
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


_PIVOT_CACHE: dict[tuple[int, int, int, int], tuple[np.ndarray, np.ndarray]] = {}
_PIVOT_CACHE_ORDER: list[tuple[int, int, int, int]] = []
_PIVOT_CACHE_MAX = 64


def _pivot_cache_key(df: pd.DataFrame, bars: int) -> tuple[int, int, int, int]:
    """Идентичность данных по длине, первому/последнему close и bars.

    Для одного и того же DataFrame (бэктест, подбор по сетке) ключ стабилен,
    поэтому дорогие фракталы считаются один раз. Хэш закрытия крайних баров
    ловит подмену данных без копирования всей серии.
    """
    first = float(df["close"].iloc[0]) if len(df) else 0.0
    last = float(df["close"].iloc[-1]) if len(df) else 0.0
    return (len(df), hash((first, last)), int(bars), id(df))


def _confirmed_pivots(df: pd.DataFrame, bars: int) -> tuple[pd.Series, pd.Series]:
    """Последние подтверждённые swing low/high из фракталов за ``bars`` свечей.

    Кандидат-пивот на баре ``j`` (минимум/максимум в окне ``[j-bars, j+bars]``)
    считается подтверждённым только с бара ``j + bars`` — поэтому на баре ``i``
    используется пивот с индексом ``<= i - bars`` (без заглядывания вперёд).
    Возвращает (swing_low, swing_high) с ffill-заполнением последнего пивота.
    """
    key = _pivot_cache_key(df, bars)
    cached = _PIVOT_CACHE.get(key)
    if cached is not None:
        return pd.Series(cached[0], index=df.index), pd.Series(cached[1], index=df.index)
    n = len(df)
    low = df["low"].values
    high = df["high"].values
    pl = np.full(n, np.nan)
    ph = np.full(n, np.nan)
    if bars <= 0:
        return pd.Series(low, index=df.index), pd.Series(high, index=df.index)
    if n <= 2 * bars:
        return (
            pd.Series(pl, index=df.index).ffill(),
            pd.Series(ph, index=df.index).ffill(),
        )
    # Векторизация: rolling min/max по окну 2*bars+1 совпадает с ручным
    # перебором, но без Python-цикла на каждый бар.
    window = 2 * bars + 1
    low_s = pd.Series(low)
    high_s = pd.Series(high)
    win_low = low_s.rolling(window, center=True, min_periods=window).min().values
    win_high = high_s.rolling(window, center=True, min_periods=window).max().values
    pl = np.where(low <= win_low, low, np.nan)
    ph = np.where(high >= win_high, high, np.nan)
    # Пивот с индексом j известен только на баре j+bars → сдвиг вправо на bars
    lag = bars
    pl_known = np.full(n, np.nan)
    ph_known = np.full(n, np.nan)
    pl_known[lag:] = pl[: n - lag]
    ph_known[lag:] = ph[: n - lag]
    pl_filled = pd.Series(pl_known, index=df.index).ffill().values
    ph_filled = pd.Series(ph_known, index=df.index).ffill().values
    _PIVOT_CACHE[key] = (pl_filled, ph_filled)
    _PIVOT_CACHE_ORDER.append(key)
    if len(_PIVOT_CACHE_ORDER) > _PIVOT_CACHE_MAX:
        _PIVOT_CACHE.pop(_PIVOT_CACHE_ORDER.pop(0), None)
    return (
        pd.Series(pl_filled, index=df.index),
        pd.Series(ph_filled, index=df.index),
    )


def _bullish_confirmation(o, h, l, c, po, pc, confirm_candle: int) -> bool:
    """Паттерн подтверждения на свече входа: пинбар или бычье поглощение."""
    if not confirm_candle:
        return False
    body = abs(c - o)
    rng = h - l
    if rng > 0 and body > 0:
        lower = min(o, c) - l
        upper = h - max(o, c)
        # молот: длинная нижняя тень, тело в верхней части
        if lower >= 2.0 * body and upper <= body:
            return True
    # бычье поглощение
    return pc < po and c > o and min(o, c) < min(po, pc) and max(o, c) > max(po, pc)


def _bearish_confirmation(o, h, l, c, po, pc, confirm_candle: int) -> bool:
    """Паттерн подтверждения для шорт-входа: пинбар-шорт или медвежье поглощение."""
    if not confirm_candle:
        return False
    body = abs(c - o)
    rng = h - l
    if rng > 0 and body > 0:
        upper = h - max(o, c)
        lower = min(o, c) - l
        # пинбар-шорт: длинная верхняя тень, тело в нижней части
        if upper >= 2.0 * body and lower <= body:
            return True
    # медвежье поглощение
    return po < pc and c < o and max(o, c) > max(po, pc) and min(o, c) < min(po, pc)


# ── Предрасчёт всех массивов сигнала ─────────────────────────────────────────

def _confirmation_masks(o, h, l, c, confirm_candle: int) -> tuple[np.ndarray, np.ndarray]:
    """Векторизованные маски пинбара/поглощения (паритет с *_confirmation)."""
    n = len(o)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    if not confirm_candle or n < 2:
        return bull, bear
    prev_o = np.roll(o, 1)
    prev_c = np.roll(c, 1)
    body = np.abs(c - o)
    rng = h - l
    has_body = (rng > 0) & (body > 0)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    bull_hammer = has_body & (lower >= 2.0 * body) & (upper <= body)
    bull_engulf = (prev_c < prev_o) & (c > o) & (np.minimum(o, c) < np.minimum(prev_o, prev_c)) \
        & (np.maximum(o, c) > np.maximum(prev_o, prev_c))
    bull = bull_hammer | bull_engulf
    bear_hammer = has_body & (upper >= 2.0 * body) & (lower <= body)
    bear_engulf = (prev_o < prev_c) & (c < o) & (np.maximum(o, c) > np.maximum(prev_o, prev_c)) \
        & (np.minimum(o, c) < np.minimum(prev_o, prev_c))
    bear = bear_hammer | bear_engulf
    bull[0] = False
    bear[0] = False
    return bull, bear


def weakness_masks(
    o, h, l, c,
    *,
    consolidation_atr: float = 0.0,
    narrow_range_ratio: float = 0.5,
    doji_body_ratio: float = 0.0,
    upper_shadow_ratio: float = 0.0,
    lower_shadow_ratio: float = 0.0,
    atr_arr=None,
    prev_range=None,
    bar_range=None,
) -> dict:
    """Причинные маски «ослабления тренда» на баре (без lookahead).

    Каждая маска — про *данные текущего бара* и (для сжатия диапазона)
    предыдущего: показывает, что покупатели/продавцы «кончились».

    - ``doji``: тело мало относительно диапазона (нерешительность).
      ``doji_body_ratio`` — макс. доля тела в диапазоне (0 = выкл).
    - ``consolidation``: диапазон бара сжат (range <= ratio * средний range).
      ``consolidation_atr`` — порог в ATR (0 = выкл), ``narrow_range_ratio`` —
      множитель к среднему диапазону за ``consolidation_period`` (если ATR не задан).
    - ``upper_shadow``: длинная верхняя тень — отказ от роста (можно измерить в
      долях диапазона; ``upper_shadow_ratio`` = мин. доля верхней тени, 0 = выкл).
    - ``lower_shadow``: длинная нижняя тень — отказ от падения.

    Возвращает dict булевых numpy-массивов длиной ``len(o)``.
    """
    n = len(o)
    o = np.asarray(o, dtype=float)
    h = np.asarray(h, dtype=float)
    l = np.asarray(l, dtype=float)
    c = np.asarray(c, dtype=float)
    rng = h - l
    body = np.abs(c - o)
    safe_rng = np.where(rng > 0, rng, np.nan)

    doji = np.zeros(n, dtype=bool)
    if doji_body_ratio and doji_body_ratio > 0:
        doji = (rng > 0) & (body <= float(doji_body_ratio) * rng)

    upper_shadow = np.zeros(n, dtype=bool)
    if upper_shadow_ratio and upper_shadow_ratio > 0:
        upper = h - np.maximum(o, c)
        upper_shadow = (rng > 0) & (upper >= float(upper_shadow_ratio) * rng)

    lower_shadow = np.zeros(n, dtype=bool)
    if lower_shadow_ratio and lower_shadow_ratio > 0:
        lower = np.minimum(o, c) - l
        lower_shadow = (rng > 0) & (lower >= float(lower_shadow_ratio) * rng)

    consolidation = np.zeros(n, dtype=bool)
    if consolidation_atr and consolidation_atr > 0 and atr_arr is not None:
        atr_a = np.asarray(atr_arr, dtype=float)
        consolidation = (rng > 0) & np.isfinite(atr_a) & (rng <= float(consolidation_atr) * atr_a)
    elif narrow_range_ratio and narrow_range_ratio > 0 and prev_range is not None:
        prev_a = np.asarray(prev_range, dtype=float)
        consolidation = (rng > 0) & np.isfinite(prev_a) & (rng <= float(narrow_range_ratio) * prev_a)

    return {
        "doji": doji,
        "consolidation": consolidation,
        "upper_shadow": upper_shadow,
        "lower_shadow": lower_shadow,
        "range": rng,
        "body": body,
        "body_ratio": np.where(rng > 0, body / safe_rng, 0.0),
    }


def _compute_arrays(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    *,
    swing_bars: int = 10,
    min_swing_dist_atr: float = 2.0,
    trend_period: int = 50,
    htf_trend_period: int = 50,
    use_htf: int = 0,
    regime_adx_min: float = 0.0,
    regime_atr_vol_max: float = 0.0,
    fib_in_low: float = 0.50,
    fib_in_high: float = 0.618,
    fib_tp: float = 0.0,
    confluence_min: int = 2,
    confirm_candle: int = 1,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    # ── Объёмные гейты (0/выкл — поведение прод не меняется) ─────────────────
    vol_period: int = 20,
    vol_min_rel: float = 0.0,   # мин. относительный объём (vol/SMA) для входа
    vol_max_rel: float = 0.0,   # макс. относительный объём (0 = без потолка)
    long_need_bull_vol: float = 0.0,   # мин. доля быков на баре лонга (0 = выкл)
    short_need_bear_vol: float = 0.0,  # макс. доля быков на баре шорта (0 = выкл)
    # ── Свечи ослабления тренда (0/выкл — поведение прод не меняется) ────────
    # Требовать на баре входа признак «продавцы/покупатели кончились»:
    # доджи (тело <= доля диапазона), консолидация (range <= ATR*k), длинная
    # верхняя тень (отказ от роста — для шорта), нижняя (для лонга).
    weak_need_doji: float = 0.0,        # макс. body_ratio для «доджи» (0 = выкл)
    weak_need_consolidation_atr: float = 0.0,  # range <= k*ATR (0 = выкл)
    weak_narrow_range_ratio: float = 0.5,      # range <= ratio*prev_range (для консолидации без ATR)
    weak_need_upper_shadow: float = 0.0,  # мин. доля верхней тени для шорта (0 = выкл)
    weak_need_lower_shadow: float = 0.0,  # мин. доля нижней тени для лонга (0 = выкл)
    weak_min_signals: int = 1,          # сколько признаков слабости нужно (ИЛИ-логика, если >0)
) -> dict:
    """Векторизованный предрасчёт состояния сигнала на каждом баре.

    Возвращает dict массив/серий: trend_up, swing_low, swing_high, seg, rsi,
    in_zone, in_discount, factors, adx, atr, vol_ratio, target.
    """
    n = len(df)
    idx = df.index
    atr_s = _atr(df, 14)
    atr_arr = atr_s.values
    atr_safe = np.where(np.isnan(atr_s.values) | (atr_s.values <= 0), np.nan, atr_s.values)

    ema_own = _ema(df["close"], int(trend_period))

    # Глобальный тренд: HTF (если включён и есть данные) иначе — свои бары.
    trend_up = np.ones(n, dtype=bool)
    if int(use_htf) and htf_df is not None and not htf_df.empty:
        htf_ema = htf_df["close"].ewm(span=int(htf_trend_period), adjust=False).mean()
        htf_last_up = bool(htf_df["close"].iloc[-1] > htf_ema.iloc[-1])
        trend_up = np.zeros(n, dtype=bool)
        trend_up[-1] = htf_last_up
    elif int(trend_period) > 0:
        trend_up = (df["close"] > ema_own).values.astype(bool)

    # Волатильность (regime): ATR/close выше потолка — хаос, входа нет.
    vol_ratio = atr_safe / df["close"].values
    vol_ok = np.ones(n, dtype=bool)
    if regime_atr_vol_max and regime_atr_vol_max > 0:
        vol_ok = (vol_ratio <= regime_atr_vol_max) & np.isfinite(df["close"].values)

    adx_s = _adx(df, 14) if regime_adx_min and regime_adx_min > 0 else pd.Series(
        np.nan, index=idx
    )
    adx_ok = np.ones(n, dtype=bool)
    if regime_adx_min and regime_adx_min > 0:
        adx_ok = (adx_s.fillna(regime_adx_min) >= regime_adx_min).values.astype(bool)

    swing_low_s, swing_high_s = _confirmed_pivots(df, int(swing_bars))
    swing_low = swing_low_s.values
    swing_high = swing_high_s.values

    close = df["close"].values
    seg = np.where(
        (~np.isnan(swing_low)) & (~np.isnan(swing_high)) & (swing_high > swing_low),
        swing_high - swing_low,
        np.nan,
    )

    in_discount = np.zeros(n, dtype=bool)
    in_premium = np.zeros(n, dtype=bool)
    rsi_s = None
    if rsi_period and rsi_period > 0:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
        avg_loss = loss.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi_s = (100 - 100 / (1 + rs)).fillna(50.0)
    rsi_arr = rsi_s.values if rsi_s is not None else np.full(n, np.nan)

    # Ретрейсмент (глубина отката от экстремума): 0% — цена на swing high,
    # 100% — на swing low. Discount-зона (по видеокурсу) — глубина 50–61.8 %.
    # Премиальная зона для шорта — зеркально: откат вверх от swing low на 50–61.8 %.
    # Векторизованный расчёт: раньше это был Python-цикл на каждый бар с
    # numpy-скалярами, что доминировало во времени бэктеста и подбора.
    valid_seg = np.isfinite(seg) & (seg > 0)
    safe_seg = np.where(valid_seg, seg, 1.0)
    retrace = np.where(valid_seg, (swing_high - close) / safe_seg, np.nan)
    retrace_up = np.where(valid_seg, (close - swing_low) / safe_seg, np.nan)
    in_discount = valid_seg & (retrace >= fib_in_low) & (retrace <= fib_in_high)
    in_premium = valid_seg & (retrace_up >= fib_in_low) & (retrace_up <= fib_in_high)
    # Цель: притягательная зона 0 % (swing high) минус ``fib_tp`` долей.
    target = np.where(valid_seg, swing_high - fib_tp * safe_seg, np.nan)
    # Шорт-цель: swing low плюс ``fib_tp`` долей (зеркально).
    target_short = np.where(valid_seg, swing_low + fib_tp * safe_seg, np.nan)

    # Конфлюэнция (фактор F1 — зона, всегда требуется; F2 — свеча; F3 — RSI)
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    bull_conf, bear_conf = _confirmation_masks(o, h, l, c, confirm_candle)
    factors = np.ones(n, dtype=int)  # зона Фибо (вход всегда от неё)
    factors_short = np.ones(n, dtype=int)
    factors += bull_conf.astype(int)
    factors += (rsi_arr <= rsi_oversold).astype(int)
    factors_short += bear_conf.astype(int)
    factors_short += (rsi_arr >= rsi_overbought).astype(int)
    if n:
        factors[0] = 0
        factors_short[0] = 0

    # ── Объёмные фичи (причинные) + маски для гейтов ────────────────────────
    vol = df["volume"].values.astype(float)
    vol_sma = pd.Series(vol, index=idx).rolling(int(vol_period), min_periods=5).mean()
    vol_rel = np.where((vol_sma > 0).values.astype(bool), vol / vol_sma.values, np.nan)
    vol_ok = np.ones(n, dtype=bool)
    if vol_min_rel and vol_min_rel > 0:
        vol_ok &= (~np.isnan(vol_rel)) & (vol_rel >= vol_min_rel)
    if vol_max_rel and vol_max_rel > 0:
        vol_ok &= (~np.isnan(vol_rel)) & (vol_rel <= vol_max_rel)

    # Доля быков на баре: (close - low) / (high - low). 0..1.
    bar_rng = h - l
    bull_bear = np.where(bar_rng > 0, (c - l) / np.where(bar_rng > 0, bar_rng, np.nan), 0.5)
    bull_vol_ok = np.ones(n, dtype=bool)
    if long_need_bull_vol and long_need_bull_vol > 0:
        bull_vol_ok &= bull_bear >= long_need_bull_vol
    bear_vol_ok = np.ones(n, dtype=bool)
    if short_need_bear_vol and short_need_bear_vol > 0:
        bear_vol_ok &= bull_bear <= short_need_bear_vol

    # ── Свечи ослабления тренда (доджи / консолидация / тени) ───────────────
    # средний диапазон за 20 баров — для консолидации без ATR
    prev_range = pd.Series(bar_rng, index=idx).rolling(20, min_periods=5).mean().shift(1).values
    weakness = weakness_masks(
        o, h, l, c,
        consolidation_atr=weak_need_consolidation_atr,
        narrow_range_ratio=weak_narrow_range_ratio,
        doji_body_ratio=weak_need_doji,
        upper_shadow_ratio=weak_need_upper_shadow,
        lower_shadow_ratio=weak_need_lower_shadow,
        atr_arr=atr_arr,
        prev_range=prev_range,
        bar_range=bar_rng,
    )
    # Слабость в пользу шорта (покупатели кончились): доджи, консолидация,
    # длинная верхняя тень. В пользу лонга — зеркально (нижняя тень).
    short_weak_parts = [weakness["doji"], weakness["consolidation"], weakness["upper_shadow"]]
    long_weak_parts = [weakness["doji"], weakness["consolidation"], weakness["lower_shadow"]]
    short_weak = np.sum([p.astype(int) for p in short_weak_parts], axis=0)
    long_weak = np.sum([p.astype(int) for p in long_weak_parts], axis=0)
    need_weak_short = (
        (weak_need_doji > 0) or (weak_need_consolidation_atr > 0)
        or (weak_need_upper_shadow > 0)
    )
    need_weak_long = (
        (weak_need_doji > 0) or (weak_need_consolidation_atr > 0)
        or (weak_need_lower_shadow > 0)
    )
    min_sig = max(1, int(weak_min_signals))
    short_weak_ok = np.ones(n, dtype=bool)
    if need_weak_short:
        short_weak_ok = short_weak >= min_sig
    long_weak_ok = np.ones(n, dtype=bool)
    if need_weak_long:
        long_weak_ok = long_weak >= min_sig

    return {
        "trend_up": trend_up,
        "weak_short_ok": short_weak_ok,
        "weak_long_ok": long_weak_ok,
        "weak_short_count": short_weak,
        "weak_long_count": long_weak,
        "weak_doji": weakness["doji"],
        "weak_consolidation": weakness["consolidation"],
        "weak_upper_shadow": weakness["upper_shadow"],
        "weak_lower_shadow": weakness["lower_shadow"],
        "vol_ok": vol_ok,
        "bull_vol_ok": bull_vol_ok,
        "bear_vol_ok": bear_vol_ok,
        "vol_rel": vol_rel,
        "bull_bear_in": bull_bear,
        "adx_ok": adx_ok,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "seg": seg,
        "in_discount": in_discount,
        "in_premium": in_premium,
        "retrace": retrace,
        "retrace_up": retrace_up,
        "rsi": rsi_arr,
        "factors": factors,
        "factors_short": factors_short,
        "atr": atr_arr,
        "vol_ratio": vol_ratio,
        "target": target,
        "target_short": target_short,
        "adx": adx_s,
        "ema": ema_own.values,
        "min_swing_dist_atr": min_swing_dist_atr,
        "confluence_min": confluence_min,
        "confirm_candle": confirm_candle,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "fib_in_low": fib_in_low,
        "fib_in_high": fib_in_high,
        "fib_tp": fib_tp,
    }


def _entry_ok(st: dict, i: int) -> bool:
    """Положительное решение о входе на баре ``i`` (без учёта позиции)."""
    if not bool(st["trend_up"][i]) or not bool(st["vol_ok"][i]) or not bool(st["adx_ok"][i]):
        return False
    if not bool(st.get("bull_vol_ok", np.ones(1, dtype=bool))[i]):
        return False
    if not bool(st.get("weak_long_ok", np.ones(1, dtype=bool))[i]):
        return False
    if not st["in_discount"][i]:
        return False
    seg = st["seg"][i]
    if np.isnan(seg) or seg <= 0:
        return False
    atr = st["atr"][i]
    if np.isnan(atr) or atr <= 0:
        return False
    if seg < st["min_swing_dist_atr"] * atr:
        return False
    return int(st["factors"][i]) >= int(st["confluence_min"])


def _exit_ok(st: dict, i: int) -> bool:
    """Положительное решение о выходе (по тренду / тейку у цели / RSI перекупленности)."""
    if not bool(st["trend_up"][i]):
        return True
    tgt = st["target"][i]
    if not np.isnan(tgt) and st.get("close") is not None and st["close"][i] >= tgt:
        return True
    rsi = st["rsi"][i]
    if not np.isnan(rsi) and rsi >= st["rsi_overbought"]:
        return True
    return False


def _entry_ok_short(st: dict, i: int) -> bool:
    """Положительное решение о шорт-входе на баре ``i`` (без учёта позиции)."""
    if bool(st["trend_up"][i]) or not bool(st["vol_ok"][i]) or not bool(st["adx_ok"][i]):
        return False
    if not bool(st.get("bear_vol_ok", np.ones(1, dtype=bool))[i]):
        return False
    if not bool(st.get("weak_short_ok", np.ones(1, dtype=bool))[i]):
        return False
    if not st["in_premium"][i]:
        return False
    seg = st["seg"][i]
    if np.isnan(seg) or seg <= 0:
        return False
    atr = st["atr"][i]
    if np.isnan(atr) or atr <= 0:
        return False
    if seg < st["min_swing_dist_atr"] * atr:
        return False
    return int(st["factors_short"][i]) >= int(st["confluence_min"])


def _exit_ok_short(st: dict, i: int) -> bool:
    """Положительное решение о выходе из шорта (тренд вверх / тейк / RSI перепроданности)."""
    if bool(st["trend_up"][i]):
        return True
    tgt = st["target_short"][i]
    if not np.isnan(tgt) and st.get("close") is not None and st["close"][i] <= tgt:
        return True
    rsi = st["rsi"][i]
    if not np.isnan(rsi) and rsi <= st["rsi_oversold"]:
        return True
    return False


# ── Фильтр параметров (реестр стратегии шлёт и риск-параметры) ───────────────

def _detector_params(params: dict) -> dict:
    """Оставить только параметры, которые принимает ``_compute_arrays``.

    Стратегия в реестре передаёт все свои параметры, включая чисто
    риск-менеджментские (risk_pct, atr_period, rr_ratio, ...), которые детектор
    не принимает — их нужно отсечь, иначе TypeError.
    """
    accepted = set(inspect.signature(_compute_arrays).parameters)
    return {k: v for k, v in params.items() if k in accepted and k not in ("df", "htf_df")}


# ── Публичный сигнал позиции ─────────────────────────────────────────────────

def fib_pullback_signal(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> pd.Series:
    """Серия позиций по Фибо-ретрейсменту (трендовое продолжение).

    ``direction`` задаётся через kwargs: 1=long only (default), -1=short only,
    0=both. OHLCV-DataFrame ``df`` — рабочий таймфрейм (LTF); ``htf_df`` —
    старший таймфрейм для фильтра глобального тренда (опц., при ``use_htf``).

    Ключевые параметры: ``swing_bars`` (пивоты), ``fib_in_low``/``fib_in_high``
    (зона отката), ``confluence_min`` (мин. факторов), ``trend_period`` (EMA),
    ``regime_atr_vol_max`` (потолок волатильности), ``rsi_oversold``/``rsi_overbought``.
    """
    direction = int(params.pop("direction", 1))
    df = prepare_ohlc(df)
    if htf_df is not None and not htf_df.empty:
        htf_df = prepare_ohlc(htf_df)
    n = len(df)
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    st["close"] = df["close"].values
    pos = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        if cur == 0:
            if direction >= 0 and _entry_ok(st, i):
                cur = 1
            elif direction <= 0 and _entry_ok_short(st, i):
                cur = -1
        elif cur == 1:
            if _exit_ok(st, i) or (direction <= 0 and _entry_ok_short(st, i)):
                cur = 0
        else:  # short position
            if _exit_ok_short(st, i) or (direction >= 0 and _entry_ok(st, i)):
                cur = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


# ── Аналитика последнего бара (для нотификатора и пояснений) ────────────────

def fib_score_breakdown(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> dict:
    """Факторная оценка и уровни Фибо на последнем (завершённом) баре.

    Возвращает {} если данных мало. Для пояснения сигнала в Telegram/дашборде:
    зона отката, RSI, ADX, волатильность, тренд, факторы, цены уровней.
    """
    df = prepare_ohlc(df)
    n = len(df)
    if n < 3:
        return {}
    if htf_df is not None and not htf_df.empty:
        htf_df = prepare_ohlc(htf_df)
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    i = n - 1

    swing_low = st["swing_low"][i]
    swing_high = st["swing_high"][i]
    seg = st["seg"][i]
    atr = st["atr"][i]

    out = {
        "n": n,
        "close": float(df["close"].iloc[i]),
        "swing_low": None if np.isnan(swing_low) else float(swing_low),
        "swing_high": None if np.isnan(swing_high) else float(swing_high),
        "segment": None if np.isnan(seg) else float(seg),
        "atr": None if np.isnan(atr) else float(atr),
        "in_discount": bool(st["in_discount"][i]),
        "in_premium": bool(st["in_premium"][i]),
        "rsi": None if np.isnan(st["rsi"][i]) else round(float(st["rsi"][i]), 1),
        "adx": None if np.isnan(st["adx"].iloc[i]) else round(float(st["adx"].iloc[i]), 1),
        "vol_ratio": None if np.isnan(st["vol_ratio"][i]) else round(float(st["vol_ratio"][i]) * 100.0, 2),
        "vol_rel": None if np.isnan(st["vol_rel"][i]) else round(float(st["vol_rel"][i]), 2),
        "bull_bear_in": None if np.isnan(st["bull_bear_in"][i]) else round(float(st["bull_bear_in"][i]), 2),
        "factors": int(st["factors"][i]),
        "factors_short": int(st["factors_short"][i]),
        "trend_up": bool(st["trend_up"][i]),
        "in_zone": bool(st["in_discount"][i]),
    }

    # Цены Фибо-уровней (глубина ретрейсмента от swing high); 0 % = swing high.
    if not np.isnan(seg) and seg > 0 and not np.isnan(swing_high):
        out["levels"] = {
            "38.2%": round(float(swing_high - 0.382 * seg), 4),
            "50.0%": round(float(swing_high - 0.500 * seg), 4),
            "61.8%": round(float(swing_high - 0.618 * seg), 4),
            "78.6%": round(float(swing_high - 0.786 * seg), 4),
            "0% (цель)": round(float(swing_high), 4),
        }
        # Шорт-уровни: глубина отката вверх от swing low.
        out["levels_short"] = {
            "38.2%": round(float(swing_low + 0.382 * seg), 4),
            "50.0%": round(float(swing_low + 0.500 * seg), 4),
            "61.8%": round(float(swing_low + 0.618 * seg), 4),
            "78.6%": round(float(swing_low + 0.786 * seg), 4),
            "0% (цель)": round(float(swing_low), 4),
        }
    return out


def _rr_gate_ok(breakdown: dict, *, short: bool, **params) -> bool:
    """R:R-гейт для setup-а: reward (до цели 0 %) / risk (до экстремума) ≥ min_rr.

    Лонг: цель = swing high, стоп = swing low (за экстремум импульса).
    Шорт: цель = swing low, стоп = swing high (зеркально).
    Если stop_dist <= 0 или min_rr <= 0 — гейт выключен (пропускаем).
    """
    min_rr = float(params.get("min_rr", 0.0) or 0.0)
    if min_rr <= 0:
        return True
    close = breakdown.get("close")
    sw_high = breakdown.get("swing_high")
    sw_low = breakdown.get("swing_low")
    if close is None or sw_high is None or sw_low is None or sw_high <= sw_low:
        return True
    if short:
        stop_dist = sw_high - close
        reward = close - sw_low
    else:
        stop_dist = close - sw_low
        reward = sw_high - close
    if stop_dist <= 0 or reward <= 0:
        return False
    return (reward / stop_dist) >= min_rr


def detect_latest_setup(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> dict | None:
    """Вернуть setup входа, если последний бар его закрывает (иначе None).

    Условия те же, что в ``fib_pullback_signal``: тренд + зона Фибо + конфлюэнция.
    Возвращает broken-down dict либо None. Цель — дедупликация в нотификаторе.
    """
    df = prepare_ohlc(df)
    breakdown = fib_score_breakdown(df, htf_df, **params)
    if not breakdown or not breakdown["in_discount"] or not breakdown["trend_up"]:
        return None
    i = len(df) - 1
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    st["close"] = df["close"].values
    if not _entry_ok(st, i):
        return None
    if not _rr_gate_ok(breakdown, short=False, **params):
        return None
    breakdown["index"] = int(i)
    breakdown["open_next"] = None
    return breakdown


def detect_latest_short_setup(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> dict | None:
    """Вернуть шорт-setup входа, если последний бар его закрывает (иначе None).

    Зеркало ``detect_latest_setup``: тренд вниз + премиальная зона Фибо +
    конфлюэнция. Для нотификатора шорт-сигналов.
    """
    df = prepare_ohlc(df)
    breakdown = fib_score_breakdown(df, htf_df, **params)
    if not breakdown or not breakdown["in_premium"] or breakdown["trend_up"]:
        return None
    i = len(df) - 1
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    st["close"] = df["close"].values
    if not _entry_ok_short(st, i):
        return None
    if not _rr_gate_ok(breakdown, short=True, **params):
        return None
    breakdown["index"] = int(i)
    breakdown["open_next"] = None
    breakdown["direction"] = -1
    return breakdown
