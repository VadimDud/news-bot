"""Price-action на уровнях R/S с анализом ликвидности (строго причинно).

Модуль реализует состязательную спецификацию из промта «Алгоритм Price Action
на уровнях R/S с анализом ликвидности» (уровни, объём, свечные паттерны,
ложные пробои/SWEEP, скопления ликвидности, объёмный профиль, логика сигнала с
защитным брекетом) как **библиотеку детекторов и один генератор сигналов**.

Принципы (совпадают с ``app/ta_lib.py``):

* Детектор на баре ``i`` читает только бары ``<= i``. Будущее не подсматривается.
* Уровни строятся на *подтверждённых* фракталах: пивот бара ``j`` известен
  только на баре ``j + look`` (см. ``ta_lib.swings``).
* Модуль не торгует сам: ``generate_signals`` выдаёт входы, а учёт PnL/издержек
  делает бэктест. Это отделяет «правильность обнаружения» от результата торговли.

Ключевое отличие от идеи промта — не «оптимизировать, пока не станет
прибыльно», а проверить, существует ли edge вообще и выдерживает ли он контроль
(см. ``research/levels_event_study`` — там тот же класс гипотез уже отвергнут).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .candle_patterns import prepare_ohlc
from .risk import atr as _atr


# ── Параметры ────────────────────────────────────────────────────────────────

@dataclass
class PALevelParams:
    """Параметры всех детекторов. Значения по умолчанию — стартовые, не оптимальные."""

    swing_look: int = 3
    atr_period: int = 14
    level_merge_atr: float = 0.5
    min_touches: int = 3
    vol_period: int = 20
    vol_mult: float = 1.5
    vp_bins: int = 40
    vp_mult: float = 1.5
    equal_level_atr: float = 0.25
    sweep_max_return_bars: int = 3
    pattern_atr_tol: float = 0.5
    rr_min: float = 1.5
    stop_buffer_atr: float = 0.2
    breakeven_r: float = 1.0
    trail_look: int = 5
    direction: int = 0  # 0=оба, 1=лонг, -1=шорт
    range_mult: float = 1.0  # расширение зоны уровня в ATR
    # ── Из видео (0/выкл — поведение прежнего PA-LEVELS не меняется) ────────
    use_htf: int = 0           # старший ТФ: лонг только в тренде вверх, шорт — вниз
    htf_ema_period: int = 50   # EMA тренда старшего ТФ
    require_compression: int = 0  # требовать сжатие диапазона (триггер из видео)
    compress_body_ratio: float = 0.35   # тело <= доли диапазона (сжатие)
    compress_range_atr: float = 0.6     # диапазон <= k*ATR (сжатие)


@dataclass
class Signal:
    """Один сигнал входа с готовыми уровнями брекета."""

    idx: int
    time: object
    side: int  # +1 лонг, -1 шорт
    price: float
    stop: float
    target: float
    reasons: list[str] = field(default_factory=list)


# ── 1. Уровни поддержки/сопротивления ────────────────────────────────────────

def find_support_resistance(
    df: pd.DataFrame,
    p: PALevelParams | None = None,
) -> pd.DataFrame:
    """Строит причинные уровни из подтверждённых свингов и считает их силу.

    Возвращает по строке на каждое обновление уровня: ``known_at`` (время,
    когда уровень стал известен), ``price``, ``side`` (``high``/``low``),
    ``touches`` (сколько свингов слилось), ``vol_reaction`` (средний
    относительный объём на барах-касаниях), ``age_bars`` (баров с первого
    касания), ``strength`` = touches × vol_reaction ÷ (age_bars+1).

    Слияние только с уровнями, подтверждёнными раньше текущего свинга, поэтому
    уровень не зависит от будущего (паттерн ``ta_lib.levels``).
    """
    p = p or PALevelParams()
    df = prepare_ohlc(df)
    n = len(df)
    look = int(p.swing_look)
    cols = ["level_idx", "known_at", "price", "side", "touches",
            "vol_reaction", "age_bars", "strength"]
    if n < 2 * look + 1:
        return pd.DataFrame(columns=cols)

    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    vol = df["volume"].to_numpy(float)
    atr = _atr(df, p.atr_period).to_numpy(float)
    avg_vol = pd.Series(vol).rolling(p.vol_period, min_periods=1).mean().to_numpy(float)
    idx = df.index

    def _rel_vol(j: int) -> float:
        a = avg_vol[j] if j < len(avg_vol) else np.nan
        return float(vol[j] / a) if a and a > 0 and np.isfinite(vol[j]) else 1.0

    swings = []
    for j in range(look, n - look):
        if high[j] > high[j - look:j].max() and high[j] >= high[j + 1:j + look + 1].max():
            swings.append((j, j + look, high[j], "high"))
        if low[j] < low[j - look:j].min() and low[j] <= low[j + 1:j + look + 1].min():
            swings.append((j, j + look, low[j], "low"))
    swings.sort(key=lambda s: s[1])

    live: list[dict] = []
    rows = []
    for swing_idx, known_at_idx, price, side in swings:
        a = atr[swing_idx]
        tol = p.level_merge_atr * a if a > 0 else 0.0
        target = None
        for lv in reversed(live):
            if lv["side"] != side:
                continue
            if abs(lv["price"] - price) <= tol:
                target = lv
                break
        rv = _rel_vol(swing_idx)
        if target is None:
            target = {
                "side": side, "prices": [price], "vols": [rv],
                "price": price, "first_idx": swing_idx, "level_idx": swing_idx,
                "known_at_idx": known_at_idx, "touches": 1,
            }
            live.append(target)
        else:
            target["prices"].append(price)
            target["vols"].append(rv)
            target["price"] = float(np.mean(target["prices"]))
            target["level_idx"] = swing_idx
            target["known_at_idx"] = known_at_idx
            target["touches"] += 1
        age = max(known_at_idx - target["first_idx"], 0)
        vol_reaction = float(np.mean(target["vols"]))
        strength = target["touches"] * vol_reaction / (age + 1)
        rows.append({
            "level_idx": target["level_idx"],
            "known_at": idx[known_at_idx],
            "price": target["price"],
            "side": side,
            "touches": target["touches"],
            "vol_reaction": vol_reaction,
            "age_bars": age,
            "strength": strength,
        })
    return pd.DataFrame(rows, columns=cols)


def levels_known_at(
    sr: pd.DataFrame, side: str, at_idx: int, min_touches: int,
) -> list[dict]:
    """Уровни ``side``, известные на баре ``at_idx`` и прошедшие min_touches.

    Каждому уровню соответствует последняя запись с ``known_pos <= at_idx``.
    Позиция ``known_pos`` = ``df.index.get_loc(known_at)`` внутри вызывающего
    кода — здесь нельзя, поэтому функция принимает уже переведённый список.
    """
    out = []
    for row in sr:
        if row["side"] != side:
            continue
        if row["known_pos"] > at_idx:
            continue
        if row["touches"] >= min_touches:
            out.append(row)
    return out


# ── 2. Объём и VSA ───────────────────────────────────────────────────────────

def relative_volume(df: pd.DataFrame, period: int = 20) -> np.ndarray:
    """Относительный объём бара к среднему за ``period`` (включая текущий).

    Используется как прокси для «подтверждения объёмом» и VSA-паттернов.
    """
    vol = pd.Series(prepare_ohlc(df)["volume"].to_numpy(float))
    avg = vol.rolling(period, min_periods=1).mean()
    return (vol / avg.replace(0, np.nan)).fillna(1.0).to_numpy(float)


def _bar_metrics(df: pd.DataFrame) -> dict[str, np.ndarray]:
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    rng = np.maximum(h - l, 1e-12)
    body = np.abs(c - o)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    return {"o": o, "h": h, "l": l, "c": c, "rng": rng,
            "body": body, "upper": upper, "lower": lower}


def compression_mask(df: pd.DataFrame, atr: np.ndarray, p: PALevelParams) -> np.ndarray:
    """Причинная маска «сжатия диапазона» (триггер из видео, п.2.4).

    Бар ``i`` — сжатие, если его тело ``<= compress_body_ratio`` диапазона
    (мелкая свеча/нерешительность) и диапазон ``<= compress_range_atr * ATR``.
    Только текущий бар, future не используется.
    """
    m = _bar_metrics(df)
    rng, body = m["rng"], m["body"]
    atr_a = np.asarray(atr, float)
    body_ok = body <= float(p.compress_body_ratio) * rng
    if p.compress_range_atr and p.compress_range_atr > 0:
        range_ok = np.isfinite(atr_a) & (atr_a > 0) & (rng <= float(p.compress_range_atr) * atr_a)
    else:
        range_ok = np.ones(len(rng), bool)
    return body_ok & range_ok


def htf_trend_at(htf_df: pd.DataFrame, ltf_index, ema_period: int) -> np.ndarray:
    """Причинный HTF-тренд: на каждый LTF-бар — направление (1/0/-1).

    Для LTF-бара ``i`` берётся последний *закрытый* HTF-бар с ``htf.begin <=
    begin_i`` (merge_asof, backward) — не подсматривает будущее. Тренд ``+1``,
    если close > EMA, ``-1`` если <, иначе ``0``. Возвращает массив длиной LTF.
    """
    htf = prepare_ohlc(htf_df)
    if htf.empty:
        return np.zeros(len(ltf_index), int)
    ema = htf["close"].ewm(span=int(ema_period), adjust=False).mean()
    dirs = pd.Series(np.where(htf["close"] > ema, 1,
                              np.where(htf["close"] < ema, -1, 0)), index=htf.index)
    ltf = pd.DataFrame({"t": pd.DatetimeIndex(ltf_index)}).sort_values("t")
    dirs_df = pd.DataFrame({"t": dirs.index, "dir": dirs.values}).sort_values("t")
    merged = pd.merge_asof(ltf, dirs_df, on="t", direction="backward")
    return merged["dir"].fillna(0).to_numpy(int)


# ── 3. Свечные паттерны на уровне ────────────────────────────────────────────

def detect_candlestick_patterns(
    df: pd.DataFrame, atr: np.ndarray, p: PALevelParams | None = None,
) -> pd.DataFrame:
    """Причинные свечные паттерны разворота: пинбар и поглощение.

    Для бара ``i`` возвращает ``bullish_reversal`` / ``bearish_reversal`` (bool),
    ``pattern`` — имя. Пинбар: тень ≥ 2× тела и ≥ 60% диапазона, хвост с
    нужной стороны. Поглощение: текущее тело накрывает предыдущее и его тело
    ≥ 50% диапазона. Всё — на закрытии бара ``i`` (future не используется).
    """
    df = prepare_ohlc(df)
    m = _bar_metrics(df)
    rng, body, upper, lower = m["rng"], m["body"], m["upper"], m["lower"]
    o, c = m["o"], m["c"]
    n = len(df)
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    name = np.array([""] * n, dtype=object)
    prev_o = np.roll(o, 1)
    prev_c = np.roll(c, 1)
    prev_rng = np.roll(rng, 1)
    for i in range(1, n):
        b = body[i]
        # пинбар-бык: длинный нижний хвост, маленькое тело сверху
        if lower[i] >= 2.0 * b and lower[i] >= 0.6 * rng[i] and b <= 0.35 * rng[i]:
            bull[i] = True
            name[i] = "pinbar"
        # пинбар-медведь: длинный верхний хвост
        elif upper[i] >= 2.0 * b and upper[i] >= 0.6 * rng[i] and b <= 0.35 * rng[i]:
            bear[i] = True
            name[i] = "pinbar"
        # бычье поглощение
        elif (c[i] > o[i] and prev_c[i] < prev_o[i]
              and c[i] >= prev_o[i] and o[i] <= prev_c[i]
              and (c[i] - o[i]) >= 0.5 * rng[i]):
            bull[i] = True
            name[i] = "engulfing"
        # медвежье поглощение
        elif (c[i] < o[i] and prev_c[i] > prev_o[i]
              and c[i] <= prev_o[i] and o[i] >= prev_c[i]
              and (o[i] - c[i]) >= 0.5 * rng[i]):
            bear[i] = True
            name[i] = "engulfing"
    return pd.DataFrame({"bullish_reversal": bull, "bearish_reversal": bear,
                         "pattern": name}, index=df.index)


# ── 4. Ложные пробои и SWEEP ликвидности ─────────────────────────────────────

def detect_false_breakouts(
    df: pd.DataFrame,
    sr: pd.DataFrame,
    p: PALevelParams | None = None,
) -> pd.DataFrame:
    """Причинные ложные пробои уровня с возвратом и признаком SWEEP.

    Пробой: закрытие бара ``i`` за уровнем (выше ``high``-уровня для шорта-ловушки
    вверх или ниже ``low``-уровня). Возврат: в пределах ``sweep_max_return_bars``
    баров закрытие возвращается на исходную сторону. Глубина пробоя в ATR.
    ``is_sweep`` = пробой на объёме ≥ ``vol_mult`` среднего и возврат на меньшем
    объёме. Событие фиксируется на баре возврата (``known_at``), не на пробое.
    """
    p = p or PALevelParams()
    df = prepare_ohlc(df)
    n = len(df)
    cols = ["level_pos", "broke_idx", "known_at_idx", "side", "depth_atr",
            "return_vol_ratio", "is_sweep"]
    if sr.empty or n == 0:
        return pd.DataFrame(columns=cols)

    atr = _atr(df, p.atr_period).to_numpy(float)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    relvol = relative_volume(df, p.vol_period)
    idx = df.index
    # позиция каждого уровня в индексе df (уровни известны только с known_at)
    sr = sr.copy()
    sr["known_pos"] = df.index.get_indexer(sr["known_at"])
    sr = sr[sr["known_pos"] >= 0]

    rows = []
    k = int(p.sweep_max_return_bars)
    # Плоские массивы уровней + порядок по known_pos для быстрого отсечения.
    lv_known = sr["known_pos"].to_numpy(int)
    lv_price = sr["price"].to_numpy(float)
    lv_side = sr["side"].to_numpy(object)
    high_mask = lv_side == "high"
    low_mask = lv_side == "low"
    for i in range(1, n):
        # только уровни, которые уже были известны (known_pos < i)
        avail = lv_known < i
        if not avail.any():
            continue
        a = atr[i] if atr[i] > 0 else np.nan
        # верхние уровни, пробитые этим баром и подтверждённые ранее
        hi_idx = np.where(avail & high_mask & (lv_price >= c[i - 1])
                          & (lv_price < h[i]))[0]
        lo_idx = np.where(avail & low_mask & (lv_price <= c[i - 1])
                          & (lv_price > l[i]))[0]
        for li in hi_idx:
            price = float(lv_price[li])
            level_pos = int(lv_known[li])
            if c[i] < price:  # вернулись на том же баре
                depth = (h[i] - price) / a if np.isfinite(a) else np.nan
                rows.append({
                    "level_pos": level_pos, "broke_idx": i - 1,
                    "known_at_idx": i, "side": -1, "depth_atr": depth,
                    "return_vol_ratio": float(relvol[i] / (relvol[i - 1] + 1e-9)),
                    "is_sweep": bool(relvol[i - 1] >= p.vol_mult and c[i] < price),
                })
            else:
                for r in range(1, k + 1):
                    j = i + r
                    if j >= n:
                        break
                    if c[j] < price:
                        depth = (h[i] - price) / a if np.isfinite(a) else np.nan
                        rows.append({
                            "level_pos": level_pos, "broke_idx": i,
                            "known_at_idx": j, "side": -1, "depth_atr": depth,
                            "return_vol_ratio": float(relvol[j] / (relvol[i] + 1e-9)),
                            "is_sweep": bool(relvol[i] >= p.vol_mult and relvol[j] < relvol[i]),
                        })
                        break
        for li in lo_idx:
            price = float(lv_price[li])
            level_pos = int(lv_known[li])
            if c[i] > price:
                depth = (price - l[i]) / a if np.isfinite(a) else np.nan
                rows.append({
                    "level_pos": level_pos, "broke_idx": i - 1,
                    "known_at_idx": i, "side": 1, "depth_atr": depth,
                    "return_vol_ratio": float(relvol[i] / (relvol[i - 1] + 1e-9)),
                    "is_sweep": bool(relvol[i - 1] >= p.vol_mult and c[i] > price),
                })
            else:
                for r in range(1, k + 1):
                    j = i + r
                    if j >= n:
                        break
                    if c[j] > price:
                        depth = (price - l[i]) / a if np.isfinite(a) else np.nan
                        rows.append({
                            "level_pos": level_pos, "broke_idx": i,
                            "known_at_idx": j, "side": 1, "depth_atr": depth,
                            "return_vol_ratio": float(relvol[j] / (relvol[i] + 1e-9)),
                            "is_sweep": bool(relvol[i] >= p.vol_mult and relvol[j] < relvol[i]),
                        })
                        break
    return pd.DataFrame(rows, columns=cols)


# ── 5. Скопления ликвидности и объёмный профиль ──────────────────────────────

def find_liquidity_clusters(
    df: pd.DataFrame, at_idx: int, p: PALevelParams | None = None,
) -> dict[str, float | None]:
    """BSL/SSL и объёмный профиль на баре ``at_idx`` (только прошлое).

    Возвращает ``bsl`` (buy-side liquidity — над максимумом окна),
    ``ssl`` (под минимумом), ``poc`` (цена с макс. объёмом), ``vah``/``val``
    (границы value area ≈70% объёма) по окну ``vp_bins*vol_period`` баров.
    """
    p = p or PALevelParams()
    df = prepare_ohlc(df)
    window = int(p.vp_bins * p.vol_period) if p.vp_bins * p.vol_period > 0 else 100
    lo = max(0, at_idx - window)
    seg = df.iloc[lo:at_idx + 1]
    if seg.empty:
        return {"bsl": None, "ssl": None, "poc": None, "vah": None, "val": None}
    h = seg["high"].to_numpy(float)
    l = seg["low"].to_numpy(float)
    c = seg["close"].to_numpy(float)
    v = seg["volume"].to_numpy(float)
    typical = (h + l + c) / 3.0
    hist, edges = np.histogram(typical, bins=p.vp_bins, weights=v)
    centers = (edges[:-1] + edges[1:]) / 2.0
    poc = float(centers[int(np.argmax(hist))]) if hist.sum() > 0 else None
    # value area ~70%
    order = np.argsort(hist)[::-1]
    target = hist.sum() * 0.70
    acc = 0.0
    chosen = []
    for b in order:
        chosen.append(b)
        acc += hist[b]
        if acc >= target:
            break
    vah = float(centers[max(chosen)]) if chosen else None
    val = float(centers[min(chosen)]) if chosen else None
    return {"bsl": float(h.max()), "ssl": float(l.min()), "poc": poc,
            "vah": vah, "val": val}


# ── 6. Генератор сигналов ────────────────────────────────────────────────────

def generate_signals(
    df: pd.DataFrame,
    p: PALevelParams | None = None,
    htf_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Собирает детекторы в причинные сигналы входа (пункт 6 промта).

    Лонг (зеркально шорт), если на баре ``i`` выполнено всё:
    1) цена вошла в зону сильного уровня поддержки (touches ≥ min_touches
       и объёмная реакция ≥ vol_mult), уровень известен;
    2) есть свечной паттерн-разворот вверх **или** бычий SWEEP под лоем;
    3) объём бара подтверждает: relvol[i] ≥ vol_mult (для sweep — возврат
       на меньшем объёме уже заложен в is_sweep);
    4) нет ближайшего сопротивления/HVN ближе, чем ``rr_min`` * риск.

    Возвращает DataFrame с колонками ``idx, time, side, price, stop, target,
    reasons``. Сигнал относится к закрытию бара ``idx``; вход — по open
    следующего бара в бэктесте.
    """
    p = p or PALevelParams()
    df = prepare_ohlc(df)
    n = len(df)
    if n < max(2 * p.swing_look + 1, p.vol_period + 1):
        return pd.DataFrame(columns=["idx", "time", "side", "price", "stop", "target", "reasons"])

    atr = _atr(df, p.atr_period).to_numpy(float)
    relvol = relative_volume(df, p.vol_period)
    sr = find_support_resistance(df, p)
    sr["known_pos"] = df.index.get_indexer(sr["known_at"])
    sr = sr[sr["known_pos"] >= 0]
    pats = detect_candlestick_patterns(df, atr, p)
    fbo = detect_false_breakouts(df, sr, p)
    patterns = pats.set_index(df.index)
    fbo_by_time = fbo.set_index(fbo["known_at_idx"]) if not fbo.empty else pd.DataFrame()

    # Триггер-сжатие (видео п.2.4) и фильтр HTF-тренда (видео п.1.3) — опционально.
    comp = compression_mask(df, atr, p) if p.require_compression else None
    htf_dir = (htf_trend_at(htf_df, df.index, p.htf_ema_period)
               if (p.use_htf and htf_df is not None and not htf_df.empty)
               else None)

    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    h, l = df["high"].to_numpy(float), df["low"].to_numpy(float)
    idx = df.index

    # быстрый доступ: для бара сколько сильных уровней рядом
    strong = sr[sr["touches"] >= p.min_touches].copy()
    strong["vol_ok"] = strong["vol_reaction"] >= p.vol_mult

    signals = []
    for i in range(1, n):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        price = c[i]
        # HTF-фильтр: лонг разрешён при тренде вверх, шорт — вниз (видео п.1.3)
        allow_long = htf_dir is None or htf_dir[i] > 0
        allow_short = htf_dir is None or htf_dir[i] < 0
        # Триггер-сжатие: если включён — вход только на сжимающемся баре
        comp_ok = (comp[i] if comp is not None else True)
        known = strong[strong["known_pos"] <= i]
        if known.empty:
            continue
        # зона допуска уровня
        tol = p.range_mult * a
        sup = known[(known["side"] == "low") & (known["vol_ok"])
                    & (np.abs(known["price"] - price) <= tol)]
        res = known[(known["side"] == "high") & (known["vol_ok"])
                    & (np.abs(known["price"] - price) <= tol)]

        # --- лонг ---
        if (p.direction >= 0 and allow_long and comp_ok and not sup.empty
                and patterns.iloc[i]["bullish_reversal"]):
            lvl = float(sup.iloc[-1]["price"])
            stop = l[i] - p.stop_buffer_atr * a
            risk = price - stop
            if risk > 0:
                # ближайшее сопротивление в известных уровнях и VP
                obstacles = known[(known["side"] == "high") & (known["price"] > price)]["price"]
                vp = find_liquidity_clusters(df, i, p)
                res_candidates = list(obstacles)
                for key in ("vah", "poc"):
                    v = vp.get(key)
                    if v is not None and v > price:
                        res_candidates.append(v)
                target = min(res_candidates) if res_candidates else price + p.rr_min * risk
                if target - price >= p.rr_min * risk:
                    signals.append({
                        "idx": i, "time": idx[i], "side": 1, "price": price,
                        "stop": float(stop), "target": float(target),
                        "reasons": [f"support@{lvl:.2f}", str(patterns.iloc[i]["pattern"]),
                                    f"vol={relvol[i]:.2f}"],
                    })
        # sweep-лонг (без обязательного паттерна, но с is_sweep)
        if (p.direction >= 0 and allow_long and comp_ok and not fbo.empty
                and not sup.empty):
            ev = fbo[(fbo["known_at_idx"] == i) & (fbo["side"] == 1) & fbo["is_sweep"]]
            if not ev.empty:
                lvl = float(sup.iloc[-1]["price"])
                stop = l[i] - p.stop_buffer_atr * a
                risk = price - stop
                if risk > 0:
                    obstacles = known[(known["side"] == "high") & (known["price"] > price)]["price"]
                    target = min(obstacles) if not obstacles.empty else price + p.rr_min * risk
                    if target - price >= p.rr_min * risk:
                        signals.append({
                            "idx": i, "time": idx[i], "side": 1, "price": price,
                            "stop": float(stop), "target": float(target),
                            "reasons": [f"sweep_ssl@{lvl:.2f}", f"vol={relvol[i]:.2f}"],
                        })

        # --- шорт ---
        if (p.direction <= 0 and allow_short and comp_ok and not res.empty
                and patterns.iloc[i]["bearish_reversal"]):
            lvl = float(res.iloc[-1]["price"])
            stop = h[i] + p.stop_buffer_atr * a
            risk = stop - price
            if risk > 0:
                obstacles = known[(known["side"] == "low") & (known["price"] < price)]["price"]
                vp = find_liquidity_clusters(df, i, p)
                sup_candidates = list(obstacles)
                for key in ("val", "poc"):
                    v = vp.get(key)
                    if v is not None and v < price:
                        sup_candidates.append(v)
                target = max(sup_candidates) if sup_candidates else price - p.rr_min * risk
                if price - target >= p.rr_min * risk:
                    signals.append({
                        "idx": i, "time": idx[i], "side": -1, "price": price,
                        "stop": float(stop), "target": float(target),
                        "reasons": [f"resistance@{lvl:.2f}", str(patterns.iloc[i]["pattern"]),
                                    f"vol={relvol[i]:.2f}"],
                    })
        if (p.direction <= 0 and allow_short and comp_ok and not fbo.empty and not res.empty):
            ev = fbo[(fbo["known_at_idx"] == i) & (fbo["side"] == -1) & fbo["is_sweep"]]
            if not ev.empty:
                lvl = float(res.iloc[-1]["price"])
                stop = h[i] + p.stop_buffer_atr * a
                risk = stop - price
                if risk > 0:
                    obstacles = known[(known["side"] == "low") & (known["price"] < price)]["price"]
                    target = max(obstacles) if not obstacles.empty else price - p.rr_min * risk
                    if price - target >= p.rr_min * risk:
                        signals.append({
                            "idx": i, "time": idx[i], "side": -1, "price": price,
                            "stop": float(stop), "target": float(target),
                            "reasons": [f"sweep_bsl@{lvl:.2f}", f"vol={relvol[i]:.2f}"],
                        })
    out = pd.DataFrame(signals)
    if out.empty:
        return pd.DataFrame(columns=["idx", "time", "side", "price", "stop", "target", "reasons"])
    # один сигнал на бар (приоритет паттерну над sweep) — берём первый
    out = out.drop_duplicates(subset=["idx", "side"], keep="first")
    return out.sort_values("idx").reset_index(drop=True)
