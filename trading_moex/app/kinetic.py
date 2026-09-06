"""Kinetic Momentum — торговля по физической аналогии «импульс + инерция».

Цена рассматривается как частица, которой сообщают импульс участники рынка.
Чистая математика/физика на OHLCV-свечах (без паттернов и осцилляторов):

- скорость ``v = r / sigma`` — доходность, нормированная на текущую
  волатильность (EWMA-стандартное отклонение лог-доходностей);
- «масса» ``m = volume / SMA(volume)`` — относительный объём бара;
- импульс за бар ``p = m * v`` (количество движения, ``p = m·v``);
- суммарный импульс ``P`` за окно ``mom_span`` — накопленный направленный
  поток (II закон Ньютона: изменение количества движения = сила), нормированный
  в z-единицы ``Pz = P/(std(p)·√mom_span)`` (~N(0,1) при независимых импульсах,
  растёт на тренде — порог осмыслен и инвариантен к масштабу);
- кинетическая энергия ``KE = m * v^2`` за окно ``mom_span`` — «активность»
  рынка; пока KE расширяется (выше своего долгосрочного базиса ``ke_span``),
  внешняя сила ещё действует и тело сохраняет движение (I закон Ньютона);
- ускорение/сила ``F = P - P_prev`` — смена импульса.

Правила (эвристика «инерция»):
- вход по направлению накопленного импульса ``|Pz| >= theta`` ТОЛЬКО при
  расширяющейся кинетической энергии (KE > базиса) и согласии скорости ``v``;
- выход — когда импульс Pz развернулся (против знака позиции) либо энергия
  «диссипировала»: KE опустилась ниже базиса (охлаждение, ``cool_bars`` подряд).

Все индикаторы векторные и причинные (используют только прошлые бары), поэтому
модуль безопасен для live и покрывается юнит-тестами (нет lookahead).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


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


# ── Кинетические фичи (причинные, векторные) ────────────────────────────────

def kinetic_features(
    df: pd.DataFrame,
    sigma_span: int = 20,
    vol_span: int = 20,
    mom_span: int = 12,
    ke_span: int = 40,
) -> pd.DataFrame:
    """Причинные кинетические фичи на каждом баре (только данные <= бара).

    Возвращает DataFrame с тем же индексом и колонками:
    ``logret``, ``sigma``, ``v`` (скорость), ``m`` (масса/отн. объём),
    ``p`` (импульс бара), ``P`` (суммарный импульс), ``p_std`` (стд импульсов),
    ``Pz`` (нормированный импульс, z-единицы), ``KE`` (кинетическая энергия
    окна), ``ke_base`` (базис KE), ``force`` (P - P_prev),
    ``bull_bear`` (закрытие в диапазоне high-low).
    """
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    logret = np.log(close / close.shift(1))
    # Волатильность-«температура»: EWMA-стд лог-доходностей.
    sigma = logret.ewm(span=sigma_span, adjust=False, min_periods=2).std()
    sigma = sigma.replace(0, np.nan)
    v = logret / sigma  # скорость в единицах сигмы

    # Масса = относительный объём бара.
    vol_sma = volume.rolling(vol_span, min_periods=vol_span).mean().replace(0, np.nan)
    m = volume / vol_sma

    p = m * v  # импульс бара
    P = p.rolling(mom_span, min_periods=mom_span).sum()  # суммарный импульс
    KE = (m * v * v).rolling(mom_span, min_periods=mom_span).sum()  # кинетическая энергия
    ke_base = KE.rolling(ke_span, min_periods=ke_span).mean()  # базис энергии

    rng = (df["high"] - df["low"]).replace(0, np.nan)
    bull_bear = ((close - df["low"]) / rng).fillna(0.5)

    out = pd.DataFrame(index=df.index)
    out["logret"] = logret
    out["sigma"] = sigma
    out["v"] = v
    out["m"] = m
    out["p"] = p
    out["P"] = P
    out["p_std"] = p.rolling(mom_span, min_periods=mom_span).std()
    # Нормированный импульс (z-единицы): P / (std(p) * sqrt(mom_span)).
    # При i.i.d. импульсах — ~N(0,1), при тренде (автокорреляции знака) — растёт.
    # Порог theta в этих единицах осмыслен и инвариантен к масштабу/таймфрейму.
    p_std = out["p_std"]
    out["Pz"] = P / (p_std * float(mom_span) ** 0.5)
    out["KE"] = KE
    out["ke_base"] = ke_base
    out["force"] = P.diff()
    out["bull_bear"] = bull_bear
    return out


# ── Сигнал позиции ───────────────────────────────────────────────────────────

def kinetic_position(
    df: pd.DataFrame,
    sigma_span: int = 20,
    vol_span: int = 20,
    mom_span: int = 12,
    ke_span: int = 40,
    theta: float = 1.5,
    v_dir: int = 1,
    direction: int = 0,
    cool_bars: int = 2,
    min_hold: int = 0,
) -> pd.Series:
    """Серия позиций по Kinetic Momentum: -1 (шорт), 0 (flat), 1 (лонг).

    Вход — при ``|Pz| >= theta`` (нормированный импульс в z-единицах) и
    расширяющейся кинетической энергии (KE > ke_base); ``direction``: 1 = только
    лонг, -1 = только шорт, 0 = оба (default). ``v_dir``: 1 = требовать согласие
    направления скорости ``v`` с сигналом, 0 = не требовать. ``cool_bars`` —
    сколько подряд баров энергия/импульс должны быть против позиции, чтобы
    закрыться. ``min_hold`` — мин. число баров удержания (0 = нет).
    """
    df = prepare_ohlc(df)
    n = len(df)
    if n < 2:
        return pd.Series(np.zeros(n, dtype=int), index=df.index)

    feat = kinetic_features(df, sigma_span, vol_span, mom_span, ke_span)
    P = feat["Pz"].to_numpy(dtype=float)
    KE = feat["KE"].to_numpy(dtype=float)
    base = feat["ke_base"].to_numpy(dtype=float)
    v = feat["v"].to_numpy(dtype=float)

    pos = np.zeros(n, dtype=int)
    cur = 0
    age = 0
    cool = 0
    for i in range(n):
        Pi, KEi, basei, vi = P[i], KE[i], base[i], v[i]
        finite = np.isfinite(Pi) and np.isfinite(KEi) and np.isfinite(basei) and np.isfinite(vi)
        energy_alive = bool(finite and KEi > basei)

        if cur == 0:
            if finite:
                if direction >= 0 and Pi >= theta and energy_alive and (v_dir == 0 or vi > 0):
                    cur, age, cool = 1, 0, 0
                elif direction <= 0 and Pi <= -theta and energy_alive and (v_dir == 0 or vi < 0):
                    cur, age, cool = -1, 0, 0
        else:
            age += 1
            if cur > 0:
                momentum_dead = bool(not finite or Pi <= 0 or not energy_alive)
            else:
                momentum_dead = bool(not finite or Pi >= 0 or not energy_alive)
            if momentum_dead:
                cool += 1
            else:
                cool = 0
            if age >= min_hold and cool >= cool_bars:
                cur = 0
                age = 0
                cool = 0
        pos[i] = cur
    return pd.Series(pos, index=df.index)


# ── Аналитика последнего бара (для нотификатора/пояснений) ──────────────────

def kinetic_breakdown(df: pd.DataFrame, **params) -> dict:
    """Кинетические фичи и решение на последнем (завершённом) баре.

    Возвращает {} если данных мало. Для пояснения сигнала в Telegram/дашборде.
    """
    df = prepare_ohlc(df)
    n = len(df)
    if n < 2:
        return {}
    feat = kinetic_features(df, **{k: v for k, v in params.items()
                                    if k in ("sigma_span", "vol_span", "mom_span", "ke_span")})
    i = n - 1

    def num(name):
        val = feat[name].iloc[i]
        return None if (val is None or (isinstance(val, float) and val != val)) else round(float(val), 4)

    P = num("Pz")
    KE = num("KE")
    base = num("ke_base")
    direction = int(params.get("direction", 0))
    theta = float(params.get("theta", 1.5))
    signal = "hold"
    if P is not None and KE is not None and base is not None:
        energy_alive = KE > base
        v0 = feat["v"].iloc[i]
        if direction >= 0 and P >= theta and energy_alive and (float(params.get("v_dir", 1)) == 0 or (v0 == v0 and v0 > 0)):
            signal = "buy"
        elif direction <= 0 and P <= -theta and energy_alive and (float(params.get("v_dir", 1)) == 0 or (v0 == v0 and v0 < 0)):
            signal = "short"
    return {
        "n": n,
        "close": round(float(df["close"].iloc[i]), 4),
        "P": num("P"),
        "Pz": num("Pz"),
        "KE": KE,
        "ke_base": base,
        "force": num("force"),
        "v": num("v"),
        "sigma": num("sigma"),
        "m": num("m"),
        "energy_expanding": bool(KE is not None and base is not None and KE > base),
        "signal": signal,
    }


# ── Фильтр параметров ────────────────────────────────────────────────────────

_KINETIC_KEYS = ("sigma_span", "vol_span", "mom_span", "ke_span", "theta", "v_dir")


def _signal_params(params: dict) -> dict:
    """Оставить только параметры, которые принимает ``kinetic_position``."""
    return {k: v for k, v in params.items()
            if k in _KINETIC_KEYS + ("direction", "cool_bars", "min_hold")}
