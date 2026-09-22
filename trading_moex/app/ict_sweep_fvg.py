"""ICT Liquidity Sweep + Fair Value Gap (FVG) — reversal strategy (pure pandas).

Методика ICT (Inner Circle Trader), разворотный сетап из 4 этапов:

1. **Liquidity Sweep** — цена пробивает пул ликвидности (внешние границы
   Daily/Session High/Low приоритетнее внутренних свингов), собирая стопы
   розницы. Валидный sweep — «ложный пробой» (fakeout): свеча закрывается
   обратно за уровень, оставив длинную тень.
2. **Displacement + FVG** — сразу после sweep рынок делает резкий импульс
   (displacement: тело свечи заметно больше теней/ATR), создавая ценовой
   дисбаланс — FVG (область между high свечи 1 и low свечи 3). Шумовые гэпы
   без displacement отсеиваются. Приоритет — FVG, перекрывающиеся с Order
   Block (OB).
3. **Retest** — возврат цены в FVG; вход по правилу 50 % глубины
   (Equilibrium). Опциональный фильтр Kill Zones (часы повышенной ликвидности).
4. **Управление** — стоп за FVG **и** за ближайший значимый экстремум sweep;
   тейк — ближайший противоположный пул ликвидности (или R:R-fallback).
   Обязательная проверка Market Structure Shift (MSS); для контртренда нужен
   «старший» пул (weekly/daily sweep).

Модуль не зависит от backtrader и используется backtrader-стратегией,
нотификатором и тестами. Все расчёты причинные: состояние на баре ``i``
использует только данные ``<= i`` (см. ``test_ict_sweep_fvg.py``).
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from .fib_pullback import _adx, _confirmed_pivots, _ema, prepare_ohlc  # noqa: F401
from .risk import atr as _atr
from .risk import true_range as _true_range  # noqa: F401

# ── Session-окна (UTC) для внешних границ и Kill Zones ───────────────────────
# MOEX торгуется ~07:00–20:50 UTC (утренняя 06:50–09:50, основная 10:00–18:40,
# вечерняя 19:00–20:50 UTC; у части бумаг вечерняя до 23:50 МСК). Западных
# сессий (Asia/London/NY) на нашей бирже НЕТ — «часы ликвидности» свои.
# Границы сессий считаются по **завершённым** свечам.
DEFAULT_SESSIONS = {
    "morning": (7, 10),   # 10:00–13:00 МСК
    "core": (10, 16),     # 13:00–19:00 МСК — пик ликвидности
    "evening": (16, 21),  # 19:00–00:00 МСК
}

# Kill Zones (интервалы UTC): реальные окна повышенной ликвидности MOEX —
# открытие утренней сессии (07:00–10:00) и вечерняя (16:00–21:00, совпадает с
# началом торгов в США, когда на MOEX приходит внешний поток).
DEFAULT_KILL_ZONES = ((7, 10), (16, 21))


# ── Session / внешние пулы ликвидности ───────────────────────────────────────

def _session_levels(df: pd.DataFrame, sessions: dict | None = None) -> dict:
    """Prior session high/low для каждого бара (без текущей свечи).

    Возвращает {name: (high_series, low_series)} — уровни **завершённой**
    прошлой одноимённой сессии, причинно доступные на баре ``i``.
    """
    sessions = sessions or DEFAULT_SESSIONS
    idx = df.index
    hours = idx.hour
    out: dict = {}
    for name, (h0, h1) in sessions.items():
        mask = (hours >= h0) & (hours < h1)
        sh = df["high"].where(mask).groupby(mask.cumsum()).cummax()
        sl = df["low"].where(mask).groupby(mask.cumsum()).cummin()
        # level = последний завершённый сессионный экстремум (сдвиг на 1 бар,
        # чтобы текущая свеча не влияла на решение о своём же пробое)
        out[name] = (sh.shift(1), sl.shift(1))
    return out


def _external_levels(
    df: pd.DataFrame, htf_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Внешние пулы: prior Daily / Previous-day / Weekly High/Low.

    Если ``htf_df`` не задан — Daily/Weekly строятся ресемплом из ``df``
    (только завершённые HTF-бары, ``shift(1)`` — без lookahead).
    Возвращает DataFrame с колонками ``d_high``, ``d_low``, ``w_high``, ``w_low``
    (ffill на LTF-индекс).
    """
    d = htf_df if htf_df is not None else df
    if not isinstance(d.index, pd.DatetimeIndex):
        d = prepare_ohlc(d)
    daily = pd.DataFrame(
        {
            "high": d["high"].resample("1D").max(),
            "low": d["low"].resample("1D").min(),
        }
    ).dropna()
    daily["pd_high"] = daily["high"].shift(1)  # previous-day high
    daily["pd_low"] = daily["low"].shift(1)
    weekly = pd.DataFrame(
        {
            "high": d["high"].resample("1W").max(),
            "low": d["low"].resample("1W").min(),
        }
    ).dropna()
    weekly["pw_high"] = weekly["high"].shift(1)
    weekly["pw_low"] = weekly["low"].shift(1)

    # Причинный маппинг HTF→LTF: значение HTF-бара доступно только после его
    # завершения. Сдвигаем индекс HTF-серий вправо на один период и reindex.
    res = pd.DataFrame(index=df.index)
    for src, cols in ((daily, ("pd_high", "pd_low")), (weekly, ("pw_high", "pw_low"))):
        for col in cols:
            shifted = src[col].copy()
            shifted.index = shifted.index + pd.Timedelta(days=1)
            res[col] = shifted.reindex(df.index, method="ffill")
    return res


def _swing_levels(df: pd.DataFrame, swing_bars: int) -> tuple[pd.Series, pd.Series]:
    """Внутренние пулы: подтверждённые свинг high/low (без lookahead)."""
    return _confirmed_pivots(df, int(swing_bars))


# ── Sweep (ложный пробой) ────────────────────────────────────────────────────

def _is_bullish_sweep(o, h, l, c, level, wick_frac: float) -> bool:
    """Sweep вниз (сняли лоу, закрылись обратно выше) → сигнал вверх.

    Требуется: low пробил уровень, close вернулся выше уровня, нижняя тень
    (close-low) составляет не менее ``wick_frac`` диапазона свечи.
    """
    if level is None or not np.isfinite(level):
        return False
    rng = h - l
    if rng <= 0 or l >= level or c <= level:
        return False
    lower_wick = c - l
    return lower_wick >= wick_frac * rng


def _is_bearish_sweep(o, h, l, c, level, wick_frac: float) -> bool:
    """Sweep вверх (сняли хай, закрылись обратно ниже) → сигнал вниз."""
    if level is None or not np.isfinite(level):
        return False
    rng = h - l
    if rng <= 0 or h <= level or c >= level:
        return False
    upper_wick = h - c
    return upper_wick >= wick_frac * rng


# ── Displacement + FVG ───────────────────────────────────────────────────────

def _displacement(o, h, l, c, atr_val, body_atr_k: float, body_ratio_min: float) -> bool:
    """Импульсная свеча: тело ≥ k·ATR и ≥ доли диапазона (displacement)."""
    if not np.isfinite(atr_val) or atr_val <= 0:
        return False
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    if body < body_atr_k * atr_val:
        return False
    return body >= body_ratio_min * rng


def _fvg_at(df: pd.DataFrame, i: int, atr_val: float, body_atr_k: float,
            body_ratio_min: float) -> dict | None:
    """FVG на баре ``i`` по 3-свечному шаблону (свеча ``i-1`` = displacement).

    Bullish FVG: ``low[i] > high[i-2]`` → зона ``[high[i-2], low[i]]``.
    Bearish FVG: ``high[i] < low[i-2]`` → зона ``[high[i], low[i-2]]``.
    Возвращает dict с side/lo/hi/mid/create_idx или None.
    """
    if i < 2:
        return None
    o1, h1, l1, c1 = (df["open"].iat[i - 1], df["high"].iat[i - 1],
                      df["low"].iat[i - 1], df["close"].iat[i - 1])
    if not _displacement(o1, h1, l1, c1, atr_val, body_atr_k, body_ratio_min):
        return None
    h2, l2 = df["high"].iat[i - 2], df["low"].iat[i - 2]
    l0, h0 = df["low"].iat[i], df["high"].iat[i]
    if l0 > h2:  # bullish imbalance
        return {"side": 1, "lo": float(h2), "hi": float(l0), "create_idx": i}
    if h0 < l2:  # bearish imbalance
        return {"side": -1, "lo": float(h0), "hi": float(l2), "create_idx": i}
    return None


def _classify_fvg(df: pd.DataFrame, fvg: dict, i: int) -> str:
    """Классификация FVG: normal / break_away / rejection.

    - ``rejection`` — FVG сформирован у sweep-экстремума (свеча создания
      пробила prior-локальный экстремум): типичная реакция на уровень;
    - ``break_away`` — FVG на баре создания обновил экстремум за
      ``lookback`` свечей и не перекрывал предыдущий FVG: разрыв-продолжение;
    - ``normal`` — все остальные.

    ``inversion`` определяется динамически (цена пробила зону и вернулась) и
    обрабатывается через ``_inverted_fvg``, а не на баре создания.
    """
    ci = int(fvg["create_idx"])
    side = int(fvg["side"])
    lookback = 20
    start = max(0, ci - lookback)
    window_high = df["high"].iloc[start:ci].max() if ci > start else np.nan
    window_low = df["low"].iloc[start:ci].min() if ci > start else np.nan
    if side == 1 and np.isfinite(window_high) and df["high"].iat[ci] > window_high:
        return "break_away"
    if side == -1 and np.isfinite(window_low) and df["low"].iat[ci] < window_low:
        return "break_away"
    # rejection: свеча создания коснулась экстремума прошлой свечи
    if side == 1 and ci > 0 and df["low"].iat[ci - 1] <= fvg["lo"] + 1e-12:
        return "rejection"
    if side == -1 and ci > 0 and df["high"].iat[ci - 1] >= fvg["hi"] - 1e-12:
        return "rejection"
    return "normal"


def _order_block(df: pd.DataFrame, fvg: dict) -> float | None:
    """Order Block перед импульсом: тело последней противоположной свечи.

    Для bullish FVG — последняя медвежья свеча до свечи создания; возвращаем
    её верхнюю границу (max(open, close)) как нижнюю границу OB-зоны. Для
    bearish — зеркально. Ищем в пределах ``ob_lookback`` свечей.
    """
    ci = int(fvg["create_idx"])
    side = int(fvg["side"])
    for j in range(ci - 2, max(ci - 12, -1), -1):
        if j < 0:
            break
        o, c = df["open"].iat[j], df["close"].iat[j]
        if side == 1 and c < o:  # медвежья свеча перед ростом
            return float(max(o, c))
        if side == -1 and c > o:  # бычья свеча перед падением
            return float(min(o, c))
    return None


def _fvg_ob_overlap(fvg: dict, ob_level: float | None, overlap_min: float) -> bool:
    """FVG перекрывается с Order Block.

    OB-уровень (тело последней противоположной свечи) обычно прилегает к
    границе FVG, а не лежит глубоко внутри. Поэтому confluence-условие —
    попадание OB-уровня в зону FVG **или** в пределах ``overlap_min`` доли
    высоты зоны от её края. ``overlap_min=0`` — достаточно касания.
    """
    if ob_level is None or not np.isfinite(ob_level):
        return False
    lo, hi = fvg["lo"], fvg["hi"]
    if hi <= lo:
        return False
    tol = max(float(overlap_min), 0.0) * (hi - lo)
    return (lo - tol) <= ob_level <= (hi + tol)


# ── Market Structure Shift ───────────────────────────────────────────────────

def _mss_confirms(df: pd.DataFrame, i: int, side: int, swing_low: np.ndarray,
                  swing_high: np.ndarray) -> bool:
    """MSS: после sweep цена пробила последний противоположный свинг.

    Для лонга (side=1) — close над последним подтверждённым swing high; для
    шорта — close под последним swing low. Причинно: свинги уже сдвинуты
    ``_confirmed_pivots``.
    """
    if i < 1:
        return False
    c = df["close"].iat[i]
    if side == 1:
        lvl = swing_high[i]
        return bool(np.isfinite(lvl) and c > lvl)
    lvl = swing_low[i]
    return bool(np.isfinite(lvl) and c < lvl)


# ── Kill Zones ───────────────────────────────────────────────────────────────

def _in_kill_zone(ts: pd.Timestamp, zones: tuple = DEFAULT_KILL_ZONES,
                  duration_min: int = 0) -> bool:
    """Попадает ли бар (интервал ``[ts, ts+duration)``) в окно ликвидности.

    Учитывается не только час начала бара, но и его длительность: 4h-бар
    16:00–20:00 UTC перекрывает вечернюю Kill Zone, хотя начинается ровно
    на её границе. Если ``duration_min=0`` — проверяется только момент ``ts``.
    """
    start_min = ts.hour * 60 + ts.minute
    end_min = start_min + max(int(duration_min), 0)
    if end_min == start_min:
        end_min = start_min + 1  # точечный бар
    return any((h0 * 60) < end_min and (h1 * 60) > start_min for h0, h1 in zones)


def _bar_duration_min(df: pd.DataFrame) -> int:
    """Медианная длительность бара в минутах (0 — если индекс не временной)."""
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 3:
        return 0
    diffs = df.index.to_series().diff().dt.total_seconds().dropna()
    if diffs.empty:
        return 0
    return int(round(diffs.median() / 60.0))


def _kill_zone_mask(df: pd.DataFrame, zones: tuple = DEFAULT_KILL_ZONES) -> np.ndarray:
    dur = _bar_duration_min(df)
    mask = np.zeros(len(df), dtype=bool)
    for i, ts in enumerate(df.index):
        mask[i] = _in_kill_zone(ts, zones, dur)
    return mask


# ── Предрасчёт сигналов ──────────────────────────────────────────────────────

def _compute_arrays(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    *,
    swing_bars: int = 10,
    ext_weight: int = 1,
    int_levels: int = 0,
    wick_frac: float = 0.5,
    body_atr_k: float = 1.0,
    body_ratio_min: float = 0.6,
    fvg_ob_required: int = 0,
    ob_overlap_min: float = 0.5,
    eq_frac: float = 0.50,
    retest_bars: int = 3,
    kill_zones: int = 0,
    mss_required: int = 0,
    htf_confirmation_required: int = 0,
    trend_period: int = 100,
    atr_period: int = 14,
    min_rr: float = 2.5,
    fib_tp: float = 0.0,
    use_htf: int = 0,
    htf_trend_period: int = 50,
) -> dict:
    """Векторизованный предрасчёт ICT-состояния на каждом баре.

    Возвращает dict с массивами: ``trend_up``, ``atr``, ``sweep_side``,
    ``fvg`` (list[dict|None]), ``in_zone``, ``entry_price``, ``stop_price``,
    ``target_price``, ``rr``, ``entry_ok_long``, ``entry_ok_short``, ``ts_hour``,
    ``kill_ok``, ``mss_ok``.
    """
    n = len(df)
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.date_range("2000-01-01", periods=n, freq="4h")
    atr_s = _atr(df, int(atr_period))
    atr_arr = atr_s.values
    close = df["close"].values
    ema = _ema(df["close"], int(trend_period))
    trend_up = (df["close"] > ema).values.astype(bool) if int(trend_period) > 0 else np.ones(n, bool)

    if int(use_htf) and htf_df is not None and not htf_df.empty:
        htf_ema = htf_df["close"].ewm(span=int(htf_trend_period), adjust=False).mean()
        up = bool(htf_df["close"].iloc[-1] > htf_ema.iloc[-1])
        trend_up = np.zeros(n, dtype=bool)
        trend_up[-1] = up

    sessions = _session_levels(df)
    ext = _external_levels(df, htf_df)
    swing_low_s, swing_high_s = _swing_levels(df, int(swing_bars))
    swing_low = swing_low_s.values
    swing_high = swing_high_s.values

    # Внешние уровни (приоритет) → fallback на внутренние свинги.
    # Приоритет внешних реализован порядком пулов в списке: сначала Daily/Weekly
    # и session-границы (первые ``ext_count``), внутренние свинги — в конце.
    # ``ext_weight`` оставлен для совместимости сигнатуры (флаг включения
    # приоритета); при 0 порядок сохраняется (внешние всё равно первыми, т.к.
    # это основной источник ликвидности по методике).
    low_pools: list[np.ndarray] = [
        ext["pd_low"].values, ext["pw_low"].values,
        sessions["morning"][1].values, sessions["core"][1].values,
        sessions["evening"][1].values,
    ]
    high_pools: list[np.ndarray] = [
        ext["pd_high"].values, ext["pw_high"].values,
        sessions["morning"][0].values, sessions["core"][0].values,
        sessions["evening"][0].values,
    ]
    if int(int_levels):
        low_pools.append(swing_low)
        high_pools.append(swing_high)
    ext_count = 5  # первые 5 пулов — внешние

    h = df["high"].values
    l = df["low"].values
    o = df["open"].values
    c = df["close"].values

    sweep_side = np.zeros(n, dtype=int)
    sweep_level = np.full(n, np.nan)
    sweep_extreme = np.full(n, np.nan)
    sweep_is_ext = np.zeros(n, dtype=bool)

    for i in range(n):
        a = atr_arr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        # Sweep вверх (bearish) — снимаем хай, закрываемся ниже.
        hit = False
        for k, arr in enumerate(high_pools):
            lvl = arr[i]
            if _is_bearish_sweep(o[i], h[i], l[i], c[i], lvl, float(wick_frac)):
                sweep_side[i] = -1
                sweep_level[i] = lvl
                sweep_extreme[i] = h[i]
                sweep_is_ext[i] = k < ext_count
                hit = True
                break
        if hit:
            continue
        # Sweep вниз (bullish) — снимаем лоу, закрываемся выше.
        for k, arr in enumerate(low_pools):
            lvl = arr[i]
            if _is_bullish_sweep(o[i], h[i], l[i], c[i], lvl, float(wick_frac)):
                sweep_side[i] = 1
                sweep_level[i] = lvl
                sweep_extreme[i] = l[i]
                sweep_is_ext[i] = k < ext_count
                break

    # FVG на каждом баре (причинно, только свеча i-1 = displacement).
    fvg_list: list[dict | None] = [None] * n
    for i in range(n):
        a = atr_arr[i - 1] if i >= 1 else np.nan
        f = _fvg_at(df, i, a, float(body_atr_k), float(body_ratio_min))
        if f is not None:
            f["kind"] = _classify_fvg(df, f, i)
            f["ob"] = _order_block(df, f)
        fvg_list[i] = f

    kill_ok = _kill_zone_mask(df) if int(kill_zones) else np.ones(n, dtype=bool)

    # ── Торговое состояние: sweep → retest FVG → вход ────────────────────────
    in_zone = np.zeros(n, dtype=bool)
    entry_price = np.full(n, np.nan)
    stop_price = np.full(n, np.nan)
    target_price = np.full(n, np.nan)
    rr = np.full(n, np.nan)
    entry_ok_long = np.zeros(n, dtype=bool)
    entry_ok_short = np.zeros(n, dtype=bool)
    mss_ok = np.zeros(n, dtype=bool)

    pending: dict | None = None
    age = 0
    for i in range(n):
        if pending is not None:
            age += 1
            side = int(pending["side"])
            f = pending.get("fvg")
            a = atr_arr[i]
            # Пока FVG не найден — ждём его появления, но не дольше retest_bars
            # от sweep (причинно: fvg_list[i] уже известен на баре i).
            if f is None:
                cand = fvg_list[i]
                if cand is not None and int(cand["side"]) == side:
                    if int(fvg_ob_required) and not _fvg_ob_overlap(
                        cand, cand.get("ob"), float(ob_overlap_min)
                    ):
                        pass  # FVG без OB-конфлюэнции не подходит
                    else:
                        pending["fvg"] = cand
                        pending["fvg_idx"] = i
                        age = 0
                if age > int(retest_bars):
                    pending = None
                continue

            # FVG есть → ждём возврата цены в зону (retest) и входим по 50 %.
            # Считаем возраст от бара появления FVG; дальний край против сделки
            # инвалидирует сетап.
            invalid = (side == 1 and c[i] < f["lo"]) or (side == -1 and c[i] > f["hi"])
            if invalid or age > int(retest_bars):
                pending = None
                continue

            touched = (l[i] <= f["hi"] and h[i] >= f["lo"])
            if not touched:
                continue

            eq = f["hi"] - float(eq_frac) * (f["hi"] - f["lo"]) if side == 1 \
                else f["lo"] + float(eq_frac) * (f["hi"] - f["lo"])
            in_zone[i] = True
            entry_price[i] = eq
            m = _mss_confirms(df, i, side, swing_low, swing_high) if int(mss_required) else True
            mss_ok[i] = bool(m)
            if m and bool(kill_ok[i]):
                # Стоп за FVG И за экстремум sweep (дистанционный буфер ATR).
                buf = float(a) if np.isfinite(a) else 0.0
                if side == 1:
                    stop_price[i] = min(f["lo"], pending["sweep_extreme"]) - buf
                    tgt = pending.get("target")
                    if tgt is None or not np.isfinite(tgt) or tgt <= eq:
                        risk = eq - stop_price[i]
                        tgt = eq + risk * float(min_rr)
                    target_price[i] = tgt
                else:
                    stop_price[i] = max(f["hi"], pending["sweep_extreme"]) + buf
                    tgt = pending.get("target")
                    if tgt is None or not np.isfinite(tgt) or tgt >= eq:
                        risk = stop_price[i] - eq
                        tgt = eq - risk * float(min_rr)
                    target_price[i] = tgt
                risk = abs(entry_price[i] - stop_price[i])
                reward = abs(target_price[i] - entry_price[i])
                rr[i] = reward / risk if risk > 0 else np.nan
                if np.isfinite(rr[i]) and rr[i] >= float(min_rr):
                    if side == 1:
                        entry_ok_long[i] = True
                    else:
                        entry_ok_short[i] = True
            pending = None

        # Новый sweep → начинаем ждать FVG + ретест (строго причинно).
        if pending is None and sweep_side[i] != 0 and not entry_ok_long[i] and not entry_ok_short[i]:
            side = int(sweep_side[i])
            # контртрендовый фильтр: против EMA требуется внешний пул
            against = (side == 1 and not trend_up[i]) or (side == -1 and trend_up[i])
            if int(htf_confirmation_required) and against and not bool(sweep_is_ext[i]):
                continue
            # фильтр Kill Zones: sweep должен быть в часы повышенной ликвидности
            if int(kill_zones) and not bool(kill_ok[i]):
                continue
            pending = {
                "side": side,
                "sweep_extreme": float(sweep_extreme[i]),
                "target": None,
                "fvg": None,
            }
            # цель: ближайший противоположный внешний пул на баре sweep
            if side == 1:
                cand = [arr[i] for arr in high_pools[:ext_count]
                        if np.isfinite(arr[i]) and arr[i] > l[i]]
                if cand:
                    pending["target"] = float(min(cand))
            else:
                cand = [arr[i] for arr in low_pools[:ext_count]
                        if np.isfinite(arr[i]) and arr[i] < h[i]]
                if cand:
                    pending["target"] = float(max(cand))
            age = 0
            # FVG может сформироваться уже на баре sweep (свеча i = третья FVG)
            f0 = fvg_list[i]
            if f0 is not None and int(f0["side"]) == side:
                if not int(fvg_ob_required) or _fvg_ob_overlap(
                    f0, f0.get("ob"), float(ob_overlap_min)
                ):
                    pending["fvg"] = f0
                    age = 0

    return {
        "trend_up": trend_up,
        "atr": atr_arr,
        "ema": ema.values,
        "sweep_side": sweep_side,
        "sweep_level": sweep_level,
        "sweep_extreme": sweep_extreme,
        "sweep_is_ext": sweep_is_ext,
        "fvg": fvg_list,
        "in_zone": in_zone,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "rr": rr,
        "entry_ok_long": entry_ok_long,
        "entry_ok_short": entry_ok_short,
        "mss_ok": mss_ok,
        "kill_ok": kill_ok,
        "swing_low": swing_low,
        "swing_high": swing_high,
        "min_rr": float(min_rr),
    }


# ── Фильтр параметров (реестр стратегии шлёт и риск-параметры) ───────────────

def _detector_params(params: dict) -> dict:
    """Оставить только параметры, которые принимает ``_compute_arrays``."""
    accepted = set(inspect.signature(_compute_arrays).parameters)
    return {k: v for k, v in params.items() if k in accepted and k not in ("df", "htf_df")}


# ── Публичный сигнал позиции ─────────────────────────────────────────────────

def ict_sweep_fvg_signal(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> pd.Series:
    """Серия позиций по ICT Liquidity Sweep + FVG.

    ``direction`` через kwargs: 1=long only, -1=short only, 0=both.
    """
    direction = int(params.pop("direction", 0))
    df = prepare_ohlc(df)
    if htf_df is not None and not htf_df.empty:
        htf_df = prepare_ohlc(htf_df)
    n = len(df)
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    pos = np.zeros(n, dtype=int)
    entry_i = -1
    side = 0
    for i in range(n):
        if pos[i - 1] if i > 0 else 0:
            pos[i] = pos[i - 1]
        if side != 0 and entry_i >= 0:
            stop = st["stop_price"][entry_i]
            tgt = st["target_price"][entry_i]
            hi, lo = float(df["high"].iat[i]), float(df["low"].iat[i])
            hit = False
            if side == 1:
                hit = (np.isfinite(stop) and lo <= stop) or (np.isfinite(tgt) and hi >= tgt)
            else:
                hit = (np.isfinite(stop) and hi >= stop) or (np.isfinite(tgt) and lo <= tgt)
            if hit:
                pos[i] = 0
                side = 0
                entry_i = -1
                continue
        if side == 0:
            if direction >= 0 and st["entry_ok_long"][i]:
                pos[i] = 1
                side = 1
                entry_i = i
            elif direction <= 0 and st["entry_ok_short"][i]:
                pos[i] = -1
                side = -1
                entry_i = i
    return pd.Series(pos, index=df.index)


def ict_score_breakdown(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> dict:
    """Детализация ICT-состояния на последнем баре (для нотификатора/дашборда)."""
    df = prepare_ohlc(df)
    n = len(df)
    if n < 3:
        return {}
    if htf_df is not None and not htf_df.empty:
        htf_df = prepare_ohlc(htf_df)
    st = _compute_arrays(df, htf_df, **_detector_params(params))
    i = n - 1
    f = st["fvg"][i]
    out = {
        "n": n,
        "close": float(df["close"].iloc[i]),
        "trend_up": bool(st["trend_up"][i]),
        "sweep_side": int(st["sweep_side"][i]),
        "sweep_level": None if not np.isfinite(st["sweep_level"][i]) else float(st["sweep_level"][i]),
        "sweep_is_external": bool(st["sweep_is_ext"][i]),
        "in_zone": bool(st["in_zone"][i]),
        "entry_ok_long": bool(st["entry_ok_long"][i]),
        "entry_ok_short": bool(st["entry_ok_short"][i]),
        "entry_price": None if not np.isfinite(st["entry_price"][i]) else float(st["entry_price"][i]),
        "stop_price": None if not np.isfinite(st["stop_price"][i]) else float(st["stop_price"][i]),
        "target_price": None if not np.isfinite(st["target_price"][i]) else float(st["target_price"][i]),
        "rr": None if not np.isfinite(st["rr"][i]) else round(float(st["rr"][i]), 2),
        "kill_ok": bool(st["kill_ok"][i]),
        "mss_ok": bool(st["mss_ok"][i]),
    }
    if f is not None:
        out["fvg"] = {
            "side": int(f["side"]),
            "lo": round(float(f["lo"]), 4),
            "hi": round(float(f["hi"]), 4),
            "mid": round((f["lo"] + f["hi"]) / 2.0, 4),
            "kind": f.get("kind"),
            "ob": None if f.get("ob") is None else round(float(f["ob"]), 4),
        }
    return out


def detect_latest_setup(
    df: pd.DataFrame,
    htf_df: pd.DataFrame | None = None,
    **params,
) -> dict | None:
    """ICT-setup на последнем баре (None, если входа нет)."""
    df = prepare_ohlc(df)
    out = ict_score_breakdown(df, htf_df, **params)
    if not out:
        return None
    if not (out["entry_ok_long"] or out["entry_ok_short"]):
        return None
    out["index"] = len(df) - 1
    out["direction"] = 1 if out["entry_ok_long"] else -1
    return out
