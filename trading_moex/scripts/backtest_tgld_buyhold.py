#!/usr/bin/env python3
"""Проверка теории «100% в золоте»: держим 100% капитала в TGLD, по сигналу
продаём в кэш, затем снова покупаем по сигналу (full-size long/flat, без ATR-лотов
и без фиксированного R:R-тейка).

Каждый сигнальный индикатор из STRATEGIES переиспользуется, но исполнение своё:
    * размер = весь свободный кэш (100% капитала), без стопов/тейков;
    * сигнал входа  -> рынком покупаем на 100%;
    * сигнал выхода -> полностью в кэш;
    * баровый close-to-close, комиссия как в бэктесте.

Usage:
    PYTHONPATH=trading_moex no_proxy="moex.com,iss.moex.com" \
        python3 trading_moex/scripts/backtest_tgld_buyhold.py [--periods 60min,2h,4h]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np
import pandas as pd

from app import storage, signals as sig

TICKER = "TGLD"
DEFAULT_PERIODS = ["60min", "2h", "4h"]
CASH = 100_000.0
COMMISSION = 0.0005


def load(period):
    raw = storage.get_candles(TICKER, period)
    raw["begin"] = pd.to_datetime(raw["begin"])
    raw = raw.set_index("begin").sort_index()
    raw.index.name = "datetime"
    return raw[["open", "high", "low", "close", "volume"]].drop_duplicates()


def sma(s, n):
    return s.rolling(n).mean()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def build_signals(df):
    """long_signal / exit_signal (bool Series) по каждой стратегии.

    Вход = стратегия «в лонге», выход = сигнал разворота/пробоя вниз. Без стопов
    и тейков — чистая проверка: «сидеть 100% в золоте и выходить по сигналу».
    """
    c = df["close"]
    out = {}

    f, s = sma(c, 10), sma(c, 30)
    out["sma_cross"] = ((f > s) & (f.shift(1) <= s.shift(1)), (f < s) & (f.shift(1) >= s.shift(1)))

    r = rsi(c, 14)
    out["rsi"] = ((r < 30) & (r.shift(1) >= 30), (r > 70) & (r.shift(1) <= 70))

    hi = df["high"].rolling(30).max().shift(1)
    lo = df["low"].rolling(30).min().shift(1)
    out["donchian"] = (c > hi, c < lo)

    # pinbar: молот (вход) / падающая звезда (выход)
    o, h, l = df["open"], df["high"], df["low"]
    rng = (h - l).replace(0, np.nan)
    body = (c - o).abs()
    lower_wick = pd.concat([o, c], axis=1).min(axis=1) - l
    upper_wick = h - pd.concat([o, c], axis=1).max(axis=1)
    hammer = (lower_wick >= 2.5 * body) & (lower_wick / rng >= 0.5)
    star = (upper_wick >= 2.5 * body) & (upper_wick / rng >= 0.5)
    out["pinbar"] = (hammer, star)

    # ma_trend: стек 20/100/200 + наклон; вход по кроссу 20/100, выход 20<100
    s20, s100, s200 = sma(c, 20), sma(c, 100), sma(c, 200)
    stacked = (s20 > s100) & (s100 > s200)
    out["ma_trend"] = (stacked & (s20.shift(1) <= s100.shift(1)), s20 < s100)

    # engulfing
    po, pc = o.shift(1), c.shift(1)
    bull = (c > o) & (po <= pc) & (c >= po) & (o <= pc)
    bear = (c < o) & (po >= pc) & (c <= po) & (o >= pc)
    out["engulfing"] = (bull, bear)

    # vol_breakdown — это шортовая методика, для «100% в золоте» неприменима
    # fib_pullback: вход как трендовое продолжение по откату к EMA-зоне (упрощённо),
    # выход по пробою ниже EMA200
    e200 = ema(c, 200)
    near = (l <= e200 * 1.01) & (c > e200)
    out["ma200_pullback"] = (near & (c.shift(1) <= e200.shift(1) * 1.01), c < e200)

    # buy&hold чистый (без выходов) добавляем отдельно
    return out


def run(df, entry, exit_):
    """Full-size long/flat: 100% кэша в лонг по entry, в кэш по exit."""
    cash = CASH
    pos = 0.0  # в долях ETF
    equity = []
    closes = df["close"].values
    ent = entry.fillna(False).values
    ex = exit_.fillna(False).values
    trades = 0
    won = 0
    entry_price = 0.0
    for i in range(len(df)):
        px = closes[i]
        if pos == 0 and ent[i]:
            pos = cash * (1 - COMMISSION) / px
            cash = 0.0
            entry_price = px
            trades += 1
        elif pos > 0 and ex[i]:
            cash = pos * px * (1 - COMMISSION)
            if px > entry_price:
                won += 1
            pos = 0.0
        equity.append(cash + pos * px)
    eq = pd.Series(equity, index=df.index)
    final = equity[-1]
    ret = (final / CASH - 1) * 100
    roll_max = eq.cummax()
    dd = ((eq - roll_max) / roll_max).min() * 100
    return {
        "ret": ret, "final": final, "trades": trades,
        "win": (won / trades * 100) if trades else 0.0,
        "dd": dd,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    args = ap.parse_args()
    periods = [p.strip() for p in args.periods.split(",") if p.strip()]

    for period in periods:
        df = load(period)
        if df is None or len(df) < 200:
            print(f"{period}: данных мало"); continue
        bh_ret = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        bh_eq = df["close"] / df["close"].iloc[0] * CASH
        bh_dd = ((bh_eq - bh_eq.cummax()) / bh_eq.cummax()).min() * 100
        # чистый buy&hold через тот же движок (без выходов)
        s = build_signals(df)
        print(f"\n=== TGLD {period}: {len(df)} бар, {df.index.min()}..{df.index.max()} ===")
        print(f"  {'buy&hold 100%':16s}: ret={bh_ret:+8.2f}%  dd={bh_dd:6.2f}%  (в золоте весь период)")
        for name, (entry, exit_) in s.items():
            m = run(df, entry, exit_)
            edge = m["ret"] - bh_ret
            print(f"  {name:16s}: ret={m['ret']:+8.2f}%  trades={m['trades']:>3d}  "
                  f"win={m['win']:5.1f}%  dd={m['dd']:6.2f}%  vs B&H {edge:+8.2f}%")


if __name__ == "__main__":
    main()
