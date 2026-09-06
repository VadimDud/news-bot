#!/usr/bin/env python3
"""Диагностика стратегии на 200-периодной скользящей средней (SMA200).

Варианты:
  - trend: всегда в рынке — лонг при close > SMA(N), шорт при close < SMA(N);
  - crossover: вход только на пересечении (close пересекает SMA), флэт между;
  - filter: SMA200 как фильтр тренда для Fib-стратегии (шорт только при
    close < SMA200, лонг только при close > SMA200).

Считает gross и net (с переносом 70/175 ₽/ночь для шортов), win-rate, число
сделок, max-DD. Разбивка по периодам (мирный до 2022-02-24 / военный после).

Вход/выход — по закрытию сигнального бара (заявка исполняется на следующем
баре по open) — причинно, без заглядывания вперёд. Нецинал фиксированный
(50к на сделку, тир 70₽/ночь), комиссия 0.05% на сторону.

Usage (from trading_moex/):
    python3 scripts/backtest_sma200.py --db data/trader_4h.db --period 1day
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

NOTIONAL = 50_000.0   # фиксированный нецинал на сделку (70₽/ночь тир)
COMMISSION = 0.0005   # на сторону
WAR_START = pd.Timestamp("2022-02-24")


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights_between(d0, d1, wk: bool) -> int:
    c = 0
    cur = d0
    while cur < d1:
        nxt = cur + timedelta(days=1)
        if wk:
            c += 1
        else:
            if nxt.weekday() == 5:
                c += 3
            elif nxt.weekday() < 5:
                c += 1
        cur = nxt
    return c


def simulate(df: pd.DataFrame, mode: str, n: int = 200, wk: bool = False) -> dict:
    """Чистая pandas-симуляция SMA-стратегии на OHLCV df.

    mode: "long" / "short" / "both" — направление стратегии;
    Возвращает сделки (list of dict) с pnl, gross, carry.
    """
    sma = df["close"].rolling(n).mean()
    close = df["close"]
    open_ = df["open"]

    # Сигнал: позиция-цель на баре (0 флэт, 1 лонг, -1 шорт).
    above = close > sma
    below = close < sma
    target = np.zeros(len(df), dtype=int)
    if mode == "long":
        target[above.values] = 1
    elif mode == "short":
        target[below.values] = -1
    else:  # both
        target[above.values] = 1
        target[below.values] = -1
    target = pd.Series(target, index=df.index).fillna(0).astype(int)

    trades: list[dict] = []
    cur = 0
    entry_i = -1
    entry_price = 0.0
    for i in range(1, len(df)):
        tgt = int(target.iloc[i])
        if cur == 0 and tgt != 0:
            # вход по open следующего бара (сигнал на баре i-1)
            if i + 1 >= len(df):
                break
            entry_price = float(open_.iloc[i + 1])
            cur = tgt
            entry_i = i + 1
        elif cur != 0 and tgt != cur:
            # выход по open следующего бара
            exit_i = i + 1 if i + 1 < len(df) else i
            exit_price = float(open_.iloc[exit_i])
            if cur == 1:
                pnl = (exit_price - entry_price) / entry_price * NOTIONAL
            else:
                pnl = (entry_price - exit_price) / entry_price * NOTIONAL
            # комиссия на вход и выход
            pnl -= 2 * COMMISSION * NOTIONAL
            d0 = df.index[entry_i].date()
            d1 = df.index[exit_i].date()
            carry = 0.0
            if cur == -1:
                carry = _carry_rate(NOTIONAL) * _nights_between(d0, d1, wk)
            trades.append({"entry": d0, "exit": d1, "dir": cur, "pnl": pnl, "carry": carry})
            cur = 0
            if tgt != 0:
                # реверс сразу (для both) — вход в противоположную сторону
                if exit_i + 1 < len(df):
                    entry_price = float(open_.iloc[exit_i + 1])
                    cur = tgt
                    entry_i = exit_i + 1
    # незакрытая позиция на конце — закрыть последним close
    if cur != 0:
        exit_price = float(close.iloc[-1])
        if cur == 1:
            pnl = (exit_price - entry_price) / entry_price * NOTIONAL
        else:
            pnl = (entry_price - exit_price) / entry_price * NOTIONAL
        pnl -= 2 * COMMISSION * NOTIONAL
        d0 = df.index[entry_i].date()
        d1 = df.index[-1].date()
        carry = _carry_rate(NOTIONAL) * _nights_between(d0, d1, wk) if cur == -1 else 0.0
        trades.append({"entry": d0, "exit": d1, "dir": cur, "pnl": pnl, "carry": carry})
    return trades


def equity_dd(trades: list[dict], initial: float = 100_000.0) -> float:
    """Max drawdown в деньгах по последовательности сделок (упрощённо)."""
    eq = initial
    peak = eq
    mdd = 0.0
    for t in sorted(trades, key=lambda x: x["exit"]):
        eq += t["pnl"] - t["carry"]
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return mdd


def simulate_crossover(df: pd.DataFrame, mode: str, n: int = 200, wk: bool = False) -> list[dict]:
    """Пересечение SMA: вход только при пересечении цены и SMA(N), флэт между.

    mode: "long" — вход на пересечении вверх, выход на пересечении вниз;
          "short" — зеркально; "both" — реверс.
    """
    sma = df["close"].rolling(n).mean()
    close = df["close"]
    open_ = df["open"]
    above = (close > sma).astype(int)

    target = np.zeros(len(df), dtype=int)
    state = 0  # 0 флэт, 1 лонг, -1 шорт — держится до реверса
    for i in range(1, len(df)):
        crossed_up = above.iloc[i] > above.iloc[i - 1]
        crossed_dn = above.iloc[i] < above.iloc[i - 1]
        if mode == "long":
            if crossed_up:
                state = 1
            elif crossed_dn:
                state = 0
        elif mode == "short":
            if crossed_dn:
                state = -1
            elif crossed_up:
                state = 0
        else:  # both — реверс
            if crossed_up:
                state = 1
            elif crossed_dn:
                state = -1
        target[i] = state

    trades: list[dict] = []
    cur = 0
    entry_i = -1
    entry_price = 0.0
    for i in range(1, len(df)):
        tgt = int(target[i])
        if cur == 0 and tgt != 0:
            if i + 1 >= len(df):
                break
            entry_price = float(open_.iloc[i + 1])
            cur = tgt
            entry_i = i + 1
        elif cur != 0 and tgt != cur and tgt != 0:
            exit_i = i + 1 if i + 1 < len(df) else i
            exit_price = float(open_.iloc[exit_i])
            if cur == 1:
                pnl = (exit_price - entry_price) / entry_price * NOTIONAL
            else:
                pnl = (entry_price - exit_price) / entry_price * NOTIONAL
            pnl -= 2 * COMMISSION * NOTIONAL
            d0 = df.index[entry_i].date()
            d1 = df.index[exit_i].date()
            carry = _carry_rate(NOTIONAL) * _nights_between(d0, d1, wk) if cur == -1 else 0.0
            trades.append({"entry": d0, "exit": d1, "dir": cur, "pnl": pnl, "carry": carry})
            cur = 0
            if exit_i + 1 < len(df):
                entry_price = float(open_.iloc[exit_i + 1])
                cur = tgt
                entry_i = exit_i + 1
        elif cur != 0 and tgt == 0:
            # выход в флэт (для long/short режимов)
            exit_i = i + 1 if i + 1 < len(df) else i
            exit_price = float(open_.iloc[exit_i])
            if cur == 1:
                pnl = (exit_price - entry_price) / entry_price * NOTIONAL
            else:
                pnl = (entry_price - exit_price) / entry_price * NOTIONAL
            pnl -= 2 * COMMISSION * NOTIONAL
            d0 = df.index[entry_i].date()
            d1 = df.index[exit_i].date()
            carry = _carry_rate(NOTIONAL) * _nights_between(d0, d1, wk) if cur == -1 else 0.0
            trades.append({"entry": d0, "exit": d1, "dir": cur, "pnl": pnl, "carry": carry})
            cur = 0
    if cur != 0:
        exit_price = float(close.iloc[-1])
        if cur == 1:
            pnl = (exit_price - entry_price) / entry_price * NOTIONAL
        else:
            pnl = (entry_price - exit_price) / entry_price * NOTIONAL
        pnl -= 2 * COMMISSION * NOTIONAL
        d0 = df.index[entry_i].date()
        d1 = df.index[-1].date()
        carry = _carry_rate(NOTIONAL) * _nights_between(d0, d1, wk) if cur == -1 else 0.0
        trades.append({"entry": d0, "exit": d1, "dir": cur, "pnl": pnl, "carry": carry})
    return trades


def _report(trades: list[dict], label: str) -> None:
    if not trades:
        print(f"{label:24} нет сделок")
        return
    g = sum(t["pnl"] for t in trades)
    c = sum(t["carry"] for t in trades)
    net = g - c
    w = sum(1 for t in trades if t["pnl"] > 0)
    mdd = equity_dd(trades)
    print(f"{label:24} n={len(trades):>4} win={w/len(trades)*100:>5.1f}% "
          f"gross={g:>+10,.0f} carry={c:>9,.0f} net={net:>+10,.0f} maxDD={mdd:>9,.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SMA200 стратегия")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--n", type=int, default=200)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    n = args.n

    print(f"SMA({n}) | период={args.period} | нецинал={NOTIONAL/1000:.0f}к | комиссия {COMMISSION*100:.2f}%/стор\n")

    # ── 1) standalone SMA: long / short / both ────────────────────────────
    for mode, lb in (("long", "SMA: только лонг"), ("short", "SMA: только шорт"),
                     ("both", "SMA: лонг+шорт (всегда в рынке)")):
        all_tr: list[dict] = []
        for t in tickers:
            df = load_df(t, args.db, args.period)
            if df.empty:
                continue
            wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
            all_tr.extend(simulate(df, mode, n, wk))
        _report(all_tr, lb)

    # ── 1b) crossover SMA ────────────────────────────────────────────────
    for mode, lb in (("long", "SMA-cross: только лонг"), ("short", "SMA-cross: только шорт"),
                     ("both", "SMA-cross: реверс")):
        all_tr = []
        for t in tickers:
            df = load_df(t, args.db, args.period)
            if df.empty:
                continue
            wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
            all_tr.extend(simulate_crossover(df, mode, n, wk))
        _report(all_tr, lb)

    # ── 2) разбивка по периодам (война/мир) ───────────────────────────────
    print("\nРазбивка по периодам (мирный < 2022-02-24 / военный >=):")
    for mode, lb in (("long", "лонг"), ("short", "шорт"), ("both", "лонг+шорт")):
        for label, mask in (("мирный", lambda idx: idx < WAR_START),
                            ("военный", lambda idx: idx >= WAR_START)):
            all_tr = []
            for t in tickers:
                df = load_df(t, args.db, args.period)
                if df.empty:
                    continue
                df = df[mask(df.index)]
                if len(df) < n + 5:
                    continue
                wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
                all_tr.extend(simulate(df, mode, n, wk))
            _report(all_tr, f"  {lb:9} [{label}]")

    # ── 3) buy & hold (контроль) ──────────────────────────────────────────
    print("\nBuy & Hold (контроль, на 100к с полным вложением):")
    for label, mask in (("весь период", None),
                        ("мирный", lambda idx: idx < WAR_START),
                        ("военный", lambda idx: idx >= WAR_START)):
        rets = []
        for t in tickers:
            df = load_df(t, args.db, args.period)
            if df.empty:
                continue
            if mask is not None:
                df = df[mask(df.index)]
            if len(df) < 2:
                continue
            rets.append((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100_000)
        if rets:
            avg = np.mean(rets)
            print(f"  BH [{label:9}]: avg pnl по тикеру={avg:>+10,.0f} (медиана {np.median(rets):+,.0f})")


if __name__ == "__main__":
    main()
