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

from .risk import atr as _atr, true_range as _true_range


# ── Сервисные функции ────────────────────────────────────────────────────────

def prepare_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Привести df к индексированному OHLCV (open, high, low, close, volume).

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


def _confirmed_pivots(df: pd.DataFrame, bars: int) -> tuple[pd.Series, pd.Series]:
    """Последние подтверждённые swing low/high из фракталов за ``bars`` свечей.

    Кандидат-пивот на баре ``j`` (минимум/максимум в окне ``[j-bars, j+bars]``)
    считается подтверждённым только с бара ``j + bars`` — поэтому на баре ``i``
    используется пивот с индексом ``<= i - bars`` (без заглядывания вперёд).
    Возвращает (swing_low, swing_high) с ffill-заполнением последнего пивота.
    """
    n = len(df)
    low = df["low"].values
    high = df["high"].values
    pl = np.full(n, np.nan)
    ph = np.full(n, np.nan)
    if bars <= 0:
        return pd.Series(low, index=df.index), pd.Series(high, index=df.index)
    for j in range(bars, n - bars):
        w_low = low[j - bars: j + bars + 1]
        w_high = high[j - bars: j + bars + 1]
        if low[j] <= w_low.min():
            pl[j] = low[j]
        if high[j] >= w_high.max():
            ph[j] = high[j]
    # Пивот с индексом j известен только на баре j+bars → сдвиг вправо на bars
    lag = bars
    pl_known = np.full(n, np.nan)
    ph_known = np.full(n, np.nan)
    pl_known[lag:] = pl[: n - lag]
    ph_known[lag:] = ph[: n - lag]
    return (
        pd.Series(pl_known, index=df.index).ffill(),
        pd.Series(ph_known, index=df.index).ffill(),
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
    retrace = np.full(n, np.nan)
    retrace_up = np.full(n, np.nan)
    target = np.full(n, np.nan)
    target_short = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(seg[i]) and seg[i] > 0:
            r = (swing_high[i] - close[i]) / seg[i]
            r_up = (close[i] - swing_low[i]) / seg[i]
            retrace[i] = r
            retrace_up[i] = r_up
            if fib_in_low <= r <= fib_in_high:
                in_discount[i] = True
            if fib_in_low <= r_up <= fib_in_high:
                in_premium[i] = True
            # Цель: притягательная зона 0 % (swing high) минус ``fib_tp`` долей.
            target[i] = swing_high[i] - fib_tp * seg[i]
            # Шорт-цель: swing low плюс ``fib_tp`` долей (зеркально).
            target_short[i] = swing_low[i] + fib_tp * seg[i]

    # Конфлюэнция (фактор F1 — зона, всегда требуется; F2 — свеча; F3 — RSI)
    factors = np.zeros(n, dtype=int)
    factors_short = np.zeros(n, dtype=int)
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    for i in range(1, n):
        f = 1  # зона Фибо (вход всегда от неё)
        if _bullish_confirmation(o[i], h[i], l[i], c[i], o[i - 1], c[i - 1], confirm_candle):
            f += 1
        if rsi_arr[i] <= rsi_oversold:
            f += 1
        factors[i] = f
        fs = 1  # зона Фибо (вход всегда от неё)
        if _bearish_confirmation(o[i], h[i], l[i], c[i], o[i - 1], c[i - 1], confirm_candle):
            fs += 1
        if rsi_arr[i] >= rsi_overbought:
            fs += 1
        factors_short[i] = fs

    return {
        "trend_up": trend_up,
        "vol_ok": vol_ok,
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
    breakdown["index"] = int(i)
    breakdown["open_next"] = None
    breakdown["direction"] = -1
    return breakdown
