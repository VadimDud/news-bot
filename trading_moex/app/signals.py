"""Чистые функции сигналов на pandas (без зависимости от backtrader).

Используются live-циклом и покрываются юнит-тестами. Backtrader-стратегии
в ``strategies.py`` повторяют ту же логику для бэктеста.
"""

import numpy as np
import pandas as pd
from typing import Sequence


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
    """Торговать только по тренду: лонги выше EMA, шорты ниже.

    ``trend_period <= 0`` — фильтр выключен. Правило Карен Фу: покупки только
    выше скользящей средней (по умолчанию EMA 200), продажи/шорты — ниже.
    """
    if not trend_period or trend_period <= 0:
        return position
    ema = close.ewm(span=trend_period, adjust=False).mean()
    filtered = position.copy()
    filtered[(position > 0) & (close < ema)] = 0
    filtered[(position < 0) & (close > ema)] = 0
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


def _volume_hist(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
    vols: Sequence[float], bins: int,
) -> tuple[list[float], float, float] | None:
    """Объёмный профиль: типичная цена (h+l+c)/3 распределяется по ``bins``
    бинам диапазона цен свечей. Возвращает (hist, pricemin, binw) или None,
    если нет валидных баров. NaN-бары (тёплый период) пропускаются.
    """
    lo, hi, cl, v = [], [], [], []
    for h, l, c, vol in zip(highs, lows, closes, vols):
        if not (h == h and l == l and c == c and vol == vol and vol > 0):
            continue
        lo.append(l)
        hi.append(h)
        cl.append(c)
        v.append(vol)
    if not lo:
        return None
    pricemin = min(lo)
    pricemax = max(hi)
    if pricemax <= pricemin:
        return None
    binw = (pricemax - pricemin) / bins
    hist = [0.0] * bins
    for l, h, c, vol in zip(lo, hi, cl, v):
        b = int(((h + l + c) / 3.0 - pricemin) / binw)
        b = min(b, bins - 1)
        hist[b] += vol
    return hist, pricemin, binw


def volume_profile_levels(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
    vols: Sequence[float], price: float, bins: int = 40, mult: float = 1.5,
) -> tuple[float | None, float | None]:
    """Ближайшие высокообъёмные уровни (HVN) под и над ``price``.

    Строит объёмный профиль по последним свечам (типичная цена (h+l+c)/3,
    объём — в соответствующий бин диапазона цен). «Высокими» считаются бины
    с объёмом не ниже ``mult`` среднего по бин. Возвращает (поддержка,
    сопротивление) — центры ближайших HVN с нужной стороны от цены, либо
    None, если такого уровня нет. NaN-бары (тёплый период) пропускаются.
    """
    built = _volume_hist(highs, lows, closes, vols, bins)
    if built is None:
        return None, None
    hist, pricemin, binw = built
    avg = sum(hist) / bins
    threshold = avg * mult
    support = None
    resistance = None
    for b, vol in enumerate(hist):
        if vol < threshold:
            continue
        center = pricemin + (b + 0.5) * binw
        if center < price:
            support = center
        elif resistance is None:
            resistance = center
    return support, resistance


def volume_profile_zones(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
    vols: Sequence[float], bins: int = 40, mult: float = 1.5,
) -> list[tuple[float, float]]:
    """Зоны высокого объёма (HVN) как диапазоны цен, отсортированные по цене.

    Тот же объёмный профиль, что и ``volume_profile_levels``, но высокообъёмные
    бины группируются в соседние кластеры (зоны) с границами (bottom, top), а не
    отдаются единичными центрами. Зоны возвращаются по возрастанию цены —
    удобно для медвежьего пробоя: выбрать зону A (баланс/накопление) и ближайшую
    нижестоящую зону B (следующий объём), к которой движется цена. NaN-бары
    (тёплый период) пропускаются.
    """
    built = _volume_hist(highs, lows, closes, vols, bins)
    if built is None:
        return []
    hist, pricemin, binw = built
    avg = sum(hist) / bins
    threshold = avg * mult
    zones = []
    in_zone = False
    zb = 0.0
    zt = 0.0
    for b in range(bins):
        if hist[b] >= threshold and not in_zone:
            in_zone = True
            zb = pricemin + b * binw
            zt = pricemin + (b + 1) * binw
        elif in_zone:
            if hist[b] >= threshold:
                zt = pricemin + (b + 1) * binw
            else:
                zones.append((zb, zt))
                in_zone = False
    if in_zone:
        zones.append((zb, zt))
    return zones


def ma_stacked(fast: float, mid: float, slow: float) -> bool:
    """Стекинг MA: быстрая выше средней, средняя выше медленной (тренд выстроен)."""
    return fast > mid > slow


def ma_golden_cross(
    fast_prev: float, mid_prev: float, fast: float, mid: float,
) -> bool:
    """Золотое сечение: быстрая MA пересекла среднюю снизу вверх."""
    return fast_prev <= mid_prev and fast > mid


def ma_slope_up(prev: float, cur: float) -> bool:
    """Наклон вверх: текущее значение MA выше значения bars назад (моментум)."""
    return cur > prev


def ma_pullback(low: float, close: float, mid: float) -> bool:
    """Откат к динамической поддержке (mid): низ коснулся/пробил mid и закрылся выше."""
    return low <= mid and close > mid


def ma_spread(
    fast: float, mid: float, slow: float, atr: float, min_spread: float,
) -> bool:
    """Расширение тренда: нормализованная разница между быстрой и медленной MA.

    Трендовый сигнал берётся только при «разжатых» линиях — когда дистанция
    ``(fast - slow)`` заметно больше разброса относительно средней. В стекинге
    эта «игла» равна ``(mid - slow)`` — минимальному зазору между соседними
    линиями. При сжатии (compression) зазор близок к нулю — входа нет.
    """
    if atr <= 0:
        return False
    span = max(fast - slow, 0.0)
    ref = max(max(fast, slow) - mid, 0.0)
    needle = max(span - ref, 0.0)
    return needle >= min_spread * atr


def scale_plan(
    ref: float, atr: float, parts: int, dist: float, stop_dist: float, rr: float,
) -> tuple[list[float], float, float, float]:
    """Усреднение входа из ``parts`` сделок: уровни, средний вход, стоп, тейк.

    Первая часть входит рынком по ``ref``, следующие — лимитками ниже через
    ``dist * ATR``. Средний вход усреднённой позиции — на (parts-1)/2 шага
    ниже ``ref``; стоп — на ``stop_dist`` ниже последней лимитки; тейк —
    ``stop_dist * rr`` от среднего входа. Риск на акцию (средний вход - стоп)
    равен ``stop_dist``, как и при обычном ATR-входе.
    """
    levels = [ref - dist * k * atr for k in range(1, parts)]
    avg_entry = ref - dist * (parts - 1) / 2.0 * atr
    stop = ref - dist * (parts - 1) * atr - stop_dist
    target = avg_entry + stop_dist * rr
    return levels, avg_entry, stop, target


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


# ── Фундаментальный сигнал ROE + P/B ────────────────────────────────────────

def _normalize_score(val, center, span):
    """Нормировка признака в [0, 1] вокруг center с размахом span (центр→0.5)."""
    if val is None:
        return 0.5
    return max(min((val - center + span) / (2 * span), 1.0), 0.0)


def _pb_percentile_score(pb_series, current_pb):
    """Дешевизна: перцентиль текущего P/B в собственной истории (0=дёшево→1).

    Низкий перцентиль = цена мала относительно стоимости капитала за историю
    бумаги → высокий балл. Если истории нет — нейтральный 0.5.
    """
    valid = pb_series.dropna()
    if len(valid) < 5 or current_pb is None:
        return 0.5
    pct = (valid <= current_pb).mean()
    return 1.0 - float(pct)


def _roe_score(avg_roe: float | None, max_roe: float = 30.0) -> float:
    """Качество: avg_roe, нормированное на max_roe (30%+ = 1.0)."""
    if avg_roe is None:
        return 0.0
    return max(min(avg_roe / max_roe, 1.0), 0.0)


def _momentum_score(ret: float | None, span: float = 0.30) -> float:
    """Моментум: возврат, нормированный на ±span вокруг 0 (центр → 0.5)."""
    return _normalize_score(ret, 0.0, span)


def _dividend_score(dividend_yield: float | None, max_yield: float = 8.0) -> float:
    """Дивидендная доходность, нормированная на max_yield."""
    if dividend_yield is None:
        return 0.0
    return max(min(dividend_yield / max_yield, 1.0), 0.0)


def _roe_stability_score(stability: float | None) -> float:
    """Стабильность ROE: min_roe / avg_roe (0-1), уже нормализовано."""
    if stability is None or np.isnan(stability):
        return 0.0
    return max(min(float(stability), 1.0), 0.0)


def roe_pb_signal(
    prices: pd.Series,
    fundamentals: pd.DataFrame,
    min_avg_roe: float = 15.0,
    min_single_roe: float = 12.0,
    pb_entry: float = 0.8,
    pb_exit: float = 1.5,
    roe_exit: float = 12.0,
    rebalance_days: int = 5,
    scoring: int = 0,
    w_roe: float = 1.0,
    w_pb: float = 1.0,
    w_momentum: float = 0.5,
    w_dividend: float = 0.5,
    w_stability: float = 0.5,
    min_score: float = 0.4,
    momentum_months: int = 6,
    stop_loss_pct: float = 0.0,
    dividends: pd.DataFrame | None = None,
) -> pd.Series:
    """Серия позиций (1=long, 0=flat) по «усреднённому ROE + P/B».

    ``fundamentals`` — DataFrame с колонками ``date`` (YYYY-MM-DD), ``roe`` (%),
    ``book_value_per_share`` (₽), отсортированный по дате. На каждый день
    prices значения forward-fill из последней строки отчётности; средний ROE —
    среднее за последние ``min_avg_roe`` лет по одному значению на год.

    Проверки выполняются каждые ``rebalance_days`` календарных дней:
    - вход: avg_roe >= min_avg_roe И годовой ROE >= min_single_roe
      И цена <= pb_entry * book_value_per_share;
    - выход: цена >= pb_exit * book_value_per_share ИЛИ годовой ROE < roe_exit.

    При ``scoring=1`` вход определяется взвешенным composite score (факторы
    ROE/PB/momentum/дивиденды/стабильность), а не жёсткими AND-условиями.
    """
    ff = _forward_fill_fundamentals(prices, fundamentals)

    avg_roe_col = fundamentals["avg_roe"] if "avg_roe" in fundamentals.columns else None
    if avg_roe_col is not None:
        avg_roe = (
            pd.to_numeric(avg_roe_col, errors="coerce")
            .set_axis(pd.to_datetime(fundamentals["date"]), axis=0)
            .reindex(prices.index)
            .values
        )
    else:
        avg_roe = _rolling_avg_roe_series(ff, fundamentals).values

    close = prices.values
    roe = ff["roe"].values
    bvps = ff["book_value_per_share"].values
    avg_roe_arr = avg_roe
    stability = np.full(len(close), np.nan)
    if "roe_stability" in ff.columns:
        stability = pd.to_numeric(ff["roe_stability"], errors="coerce").values

    # История P/B для перцентильного скоринга (скользящее окно) — в scoring=1
    pb_history = pd.Series(close, index=prices.index) / pd.Series(bvps, index=prices.index)
    pb_window = int(momentum_months) * 21

    # Дивидендная доходность за 12 мес (векторизовано) — в scoring=1
    dy_arr = np.zeros(len(close), dtype=float)
    if dividends is not None and not dividends.empty and scoring == 1:
        divs = dividends.copy()
        divs["date"] = pd.to_datetime(divs["date"])
        divs["dividend"] = pd.to_numeric(divs["dividend"], errors="coerce")
        divs = divs.dropna(subset=["date", "dividend"]).sort_values("date")
        if not divs.empty:
            div_ts = divs.set_index("date")["dividend"]
            for i in range(len(close)):
                dt_cur = prices.index[i]
                lower = dt_cur - pd.DateOffset(months=12)
                mask = (div_ts.index >= lower) & (div_ts.index <= dt_cur)
                total_div = float(div_ts[mask].sum()) if mask.any() else 0.0
                if total_div > 0 and close[i] > 0:
                    dy_arr[i] = total_div * 100.0 / close[i]

    pos = np.zeros(len(prices), dtype=int)
    cur = 0
    last_check = None
    entry_price = None  # цена закрытия бара входа (для стоп-лосса)
    div_accrued = 0.0   # накопленные дивиденды с момента входа (total-return)
    # Карта дивидендов по дате отсечки: {date: dividend_per_share}
    _div_map: dict = {}
    if dividends is not None and not dividends.empty:
        for _, r in dividends.iterrows():
            try:
                _div_map[pd.Timestamp(r["date"]).date()] = float(r["dividend"])
            except Exception:  # noqa: BLE001
                pass
    for i in range(len(prices)):
        cur_date = prices.index[i].date()
        # Начисление дивидендов: если позиция открыта и сегодня дата отсечки
        if cur == 1 and cur_date in _div_map:
            div_accrued += _div_map[cur_date]
        if last_check is None or (cur_date - last_check).total_seconds() // 86400 >= rebalance_days:
            last_check = cur_date
            if np.isnan(roe[i]) or np.isnan(bvps[i]) or np.isnan(avg_roe_arr[i]) or bvps[i] <= 0:
                pos[i] = cur
                continue
            if scoring == 0:
                if cur == 0:
                    if avg_roe_arr[i] >= min_avg_roe and roe[i] >= min_single_roe and close[i] <= pb_entry * bvps[i]:
                        cur = 1
                        entry_price = close[i]
                        div_accrued = 0.0
                else:
                    if close[i] >= pb_exit * bvps[i] or roe[i] < roe_exit:
                        cur = 0
                        entry_price = None
                        div_accrued = 0.0
            else:
                # Scoring-режим: composite score выше порога → вход.
                s_roe = _roe_score(avg_roe_arr[i])
                current_pb = close[i] / bvps[i]
                s_pb = _pb_percentile_score(
                    pd.Series(pb_history.values[max(0, i - pb_window): i + 1]),
                    current_pb,
                )
                lookback = max(1, int(momentum_months * 21))
                ret = None
                if i >= lookback:
                    if close[i - lookback] > 0:
                        ret = close[i] / close[i - lookback] - 1.0
                s_mom = _momentum_score(ret)
                s_div = _dividend_score(float(dy_arr[i]))
                s_stab = _roe_stability_score(stability[i])
                total_w = w_roe + w_pb + w_momentum + w_dividend + w_stability
                score = (
                    s_roe * w_roe + s_pb * w_pb + s_mom * w_momentum
                    + s_div * w_dividend + s_stab * w_stability
                ) / total_w if total_w > 0 else 0.0
                # Жёсткие условия выхода имеют приоритет над скорингом: без этого
                # дорогая бумага (P/B ≥ pb_exit) на следующем же баре покупается
                # обратно по score → осцилляция выход/вход каждый бар.
                hard_exit = close[i] >= pb_exit * bvps[i] or roe[i] < roe_exit
                if cur == 0 and score >= min_score and not hard_exit:
                    cur = 1
                    entry_price = close[i]
                    div_accrued = 0.0
                elif cur == 1 and (score < min_score * 0.6 or hard_exit):
                    cur = 0
                    entry_price = None
                    div_accrued = 0.0
        # Стоп-лосс: проверяется каждый бар (вне гейта ребаланса)
        # Total-return: эффективный вход = цена входа − накопленные дивиденды,
        # чтобы гэп на отсечке не триггерил ложный стоп.
        if stop_loss_pct > 0 and cur == 1 and entry_price is not None:
            effective_entry = max(entry_price - div_accrued, 0.0)
            if close[i] <= effective_entry * (1 - stop_loss_pct / 100.0):
                cur = 0
                entry_price = None
                div_accrued = 0.0
        pos[i] = cur
    return pd.Series(pos, index=prices.index)


def roe_pb_position(
    df: pd.DataFrame,
    fundamentals: pd.DataFrame | None = None,
    min_avg_roe: float = 15.0,
    min_single_roe: float = 12.0,
    pb_entry: float = 0.8,
    pb_exit: float = 1.5,
    roe_exit: float = 12.0,
    rebalance_days: int = 5,
    scoring: int = 0,
    w_roe: float = 1.0,
    w_pb: float = 1.0,
    w_momentum: float = 0.5,
    w_dividend: float = 0.5,
    w_stability: float = 0.5,
    min_score: float = 0.4,
    momentum_months: int = 6,
    stop_loss_pct: float = 0.0,
    dividends: pd.DataFrame | None = None,
) -> pd.Series:
    """Позиция (1=long, 0=flat) по «высокий ROE + цена дешевле капитала».

    Live-обёртка над ``roe_pb_signal``: принимает OHLCV-DataFrame ``df``
    (как остальные live-сигналы), а отчётность — параметром ``fundamentals``
    (колонки ``date``, ``roe``, ``book_value_per_share``). Если отчётности
    нет — позиция всегда 0 (не торгуем без данных), не падаем.
    """
    if fundamentals is None or fundamentals.empty:
        return pd.Series(np.zeros(len(df), dtype=int), index=df.index)
    return roe_pb_signal(
        df["close"],
        fundamentals,
        min_avg_roe=min_avg_roe,
        min_single_roe=min_single_roe,
        pb_entry=pb_entry,
        pb_exit=pb_exit,
        roe_exit=roe_exit,
        rebalance_days=rebalance_days,
        scoring=scoring,
        w_roe=w_roe,
        w_pb=w_pb,
        w_momentum=w_momentum,
        w_dividend=w_dividend,
        w_stability=w_stability,
        min_score=min_score,
        momentum_months=momentum_months,
        stop_loss_pct=stop_loss_pct,
        dividends=dividends,
    )


def _forward_fill_fundamentals(prices: pd.Series, fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Квартальные значения ROE/BV развёрнуты на каждый день prices (ffill)."""
    cols = ["roe", "book_value_per_share"]
    if "roe_stability" in fundamentals.columns:
        cols.append("roe_stability")
    fund = fundamentals.copy()
    fund["date"] = pd.to_datetime(fund["date"])
    # Векторный ffill вместо iterrows: pandas 3.x при iterrows() по смешанным
    # колонкам (дата + float) превращает nan в NaT, что ломает присваивание
    # во float64-колонку (LossySetitemError).
    series = (
        fund.sort_values("date")
        .set_index("date")[cols]
        .apply(pd.to_numeric, errors="coerce")
        .astype("float64")
    )
    idx = prices.index
    filled = (
        series.reindex(series.index.union(idx))
        .sort_index()
        .ffill()
        .reindex(idx)
    )
    ff = pd.DataFrame(index=idx)
    for c in cols:
        ff[c] = filled[c].to_numpy(dtype=float)
    return ff


def _rolling_avg_roe_series(
    ff: pd.DataFrame, fundamentals: pd.DataFrame | None = None, years: int = 10
) -> pd.Series:
    """Средний ROE за ``years`` отчётных лет, уже опубликованных к бару.

    Берём последнее значение ROE по каждому отчётному году из ``fundamentals``
    (дата отчёта определяет год) и усредняем за последние ``years`` лет,
    чей отчёт уже вышел (дата отчёта <= дата бара). Без ``fundamentals`` —
    по последним значениям года из дневного ряда ``ff``. Это исключает
    look-ahead: отчёт за 2024 не виден в начале 2024.
    """
    if fundamentals is not None and not fundamentals.empty:
        fund = fundamentals.copy()
        fund["date"] = pd.to_datetime(fund["date"])
        fund = fund.sort_values("date")
        annual = fund.groupby(fund["date"].dt.year)["roe"].last()
    else:
        annual = ff.groupby(ff.index.year)["roe"].last()

    series = [np.nan] * len(ff)
    for i, ts in enumerate(ff.index):
        # года, чей отчётный год закончился к бару: date(y-12-31) <= ts
        eligible_ts = ts - pd.Timedelta(days=1)
        eligible_years = [y for y in annual.index if pd.Timestamp(f"{y}-12-31") <= eligible_ts][-years:]
        if not eligible_years:
            continue
        valid = [float(annual.loc[y]) for y in eligible_years if not np.isnan(annual.loc[y])]
        if valid:
            series[i] = float(np.mean(valid))
    return pd.Series(series, index=ff.index)


def roe_score_breakdown(
    prices: pd.Series,
    fundamentals: pd.DataFrame,
    *,
    w_roe: float = 1.0,
    w_pb: float = 1.0,
    w_momentum: float = 0.5,
    w_dividend: float = 0.5,
    w_stability: float = 0.5,
    momentum_months: int = 6,
    dividends: pd.DataFrame | None = None,
) -> dict:
    """Composite score и факторные оценки ROE+P/B на последнем баре.

    Повторяет скоринг-ветку ``roe_pb_signal`` для одной точки — нужно для
    человекочитаемых пояснений сигналов (сколько дал каждый фактор).
    Возвращает {} если данных недостаточно.
    """
    if prices is None or len(prices) == 0 or fundamentals is None or fundamentals.empty:
        return {}

    ff = _forward_fill_fundamentals(prices, fundamentals)
    if ff.empty:
        return {}

    if "avg_roe" in fundamentals.columns:
        avg_roe = (
            pd.to_numeric(fundamentals["avg_roe"], errors="coerce")
            .set_axis(pd.to_datetime(fundamentals["date"]), axis=0)
            .reindex(prices.index)
            .values.astype(float)
        )
    else:
        avg_roe = _rolling_avg_roe_series(ff, fundamentals).values.astype(float)

    close = prices.values.astype(float)
    bvps = pd.to_numeric(ff["book_value_per_share"], errors="coerce").values.astype(float)
    if "roe_stability" in ff.columns:
        stability = pd.to_numeric(ff["roe_stability"], errors="coerce").values.astype(float)
    else:
        stability = np.full(len(close), np.nan)

    i = len(close) - 1
    window = max(1, int(momentum_months) * 21)

    current_pb = None
    if not np.isnan(bvps[i]) and bvps[i] > 0:
        current_pb = close[i] / bvps[i]

    avg_roe_i = None if np.isnan(avg_roe[i]) else float(avg_roe[i])
    s_roe = _roe_score(avg_roe_i)

    pb_history = pd.Series(close, index=prices.index) / pd.Series(bvps, index=prices.index)
    s_pb = (
        _pb_percentile_score(pb_history.iloc[max(0, i - window): i + 1], current_pb)
        if current_pb is not None
        else 0.5
    )

    ret = None
    if i >= window and close[i - window] > 0:
        ret = close[i] / close[i - window] - 1.0
    s_mom = _momentum_score(ret)

    # Дивидендная доходность за 12 мес
    dy_val = 0.0
    if dividends is not None and not dividends.empty and close[i] > 0:
        divs = dividends.copy()
        divs["date"] = pd.to_datetime(divs["date"])
        divs["dividend"] = pd.to_numeric(divs["dividend"], errors="coerce")
        divs = divs.dropna(subset=["date", "dividend"]).sort_values("date")
        if not divs.empty:
            div_ts = divs.set_index("date")["dividend"]
            dt_cur = prices.index[i]
            lower = dt_cur - pd.DateOffset(months=12)
            mask = (div_ts.index >= lower) & (div_ts.index <= dt_cur)
            total_div = float(div_ts[mask].sum()) if mask.any() else 0.0
            if total_div > 0:
                dy_val = total_div * 100.0 / close[i]
    s_div = _dividend_score(dy_val)

    st = None if np.isnan(stability[i]) else float(stability[i])
    s_stab = _roe_stability_score(st)

    total_w = w_roe + w_pb + w_momentum + w_dividend + w_stability
    score = (
        (s_roe * w_roe + s_pb * w_pb + s_mom * w_momentum + s_div * w_dividend + s_stab * w_stability)
        / total_w
        if total_w > 0
        else 0.0
    )
    return {
        "score": round(float(score), 3),
        "s_roe": round(float(s_roe), 3),
        "s_pb": round(float(s_pb), 3),
        "s_mom": round(float(s_mom), 3),
        "s_div": round(float(s_div), 3),
        "s_stab": round(float(s_stab), 3),
        "momentum_ret_pct": None if ret is None else round(ret * 100.0, 1),
        "current_pb": None if current_pb is None else round(current_pb, 2),
    }


def _fib_pullback_signal(df: pd.DataFrame, **kwargs):
    """Обёртка fib-сигнала: подключение чистой логики из ``fib_pullback``.

    Сигнатура соответствует остальным SIGNAL_FUNCS (df + параметры), а
    опциональный старший таймфрейм (``htf_df``) live-цикл подставляет отдельно —
    здесь он из kwargs убирается, чтобы не ломать общий контракт.
    """
    from . import fib_pullback

    htf_df = kwargs.pop("htf_df", None)
    return fib_pullback.fib_pullback_signal(df, htf_df=htf_df, **kwargs)


def signal_from_position(pos: pd.Series) -> str:
    """Вернуть действие по последней паре баров: buy / sell / short / cover / hold."""
    if len(pos) < 2:
        return "hold"
    last, prev = pos.iloc[-1], pos.iloc[-2]
    if last == 1 and prev == 0:
        return "buy"
    if last == 0 and prev == 1:
        return "sell"
    if last == -1 and prev == 0:
        return "short"
    if last == 0 and prev == -1:
        return "cover"
    return "hold"


SIGNAL_FUNCS = {
    "sma_cross": sma_cross_position,
    "rsi": rsi_position,
    "donchian": donchian_position,
    "pinbar": pinbar_position,
    "engulfing": engulfing_position,
    "roe_portfolio": roe_pb_position,
    "fib_pullback": _fib_pullback_signal,
}
