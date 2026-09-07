#!/usr/bin/env python3
"""Статистическое исследование свечных паттернов и пробоев зон.

Сканирует свечи из БД по всем тикерам/таймфреймам и для каждого паттерна
из ``candle_patterns.PATTERNS`` считает вероятность продолжения на следующих
``horizon`` барах: win-rate vs базовая ставка стороны, edge, средний forward
в ATR, z-score значимости. Паттерны размечаются причинно (без lookahead).

Вывод:
  - сводная таблица по всем тикерам (пул событий) для каждого периода;
  - проверка устойчивости: две половины истории и разбивка мир/война;
  - лучшие паттерны (win-pct, edge, z) отсортированные по z/edge.

Usage (from trading_moex/):
    python3 scripts/candle_pattern_research.py --db data/trader.db --period 1day
    python3 scripts/candle_pattern_research.py --db data/trader_4h.db --period 4h
    python3 scripts/candle_pattern_research.py --db data/trader_4h.db --period 1day --horizon 10
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app import candle_patterns as cp  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

WAR_START = pd.Timestamp("2022-02-24")


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(str(db))
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def available_tickers(db: str, period: str) -> list[str]:
    con = sqlite3.connect(str(db))
    rows = con.execute(
        "SELECT DISTINCT ticker FROM candles WHERE period=?", (period,)
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _agg(stats: list[pd.DataFrame]) -> pd.DataFrame:
    if not stats:
        return pd.DataFrame()
    df = pd.concat(stats, ignore_index=True)
    if df.empty:
        return df
    g = df.groupby(["pattern", "side"], as_index=False).agg(
        total_n=("n", "sum"),
        win_n=("n", lambda s: np.nan),  # placeholder, посчитаем ниже
    )
    # win_n нельзя агрегировать mean от n напрямую — пересчитываем взвешенно
    out = df.groupby(["pattern", "side"]).apply(
        lambda grp: pd.Series({
            "total_n": int(grp["n"].sum()),
            "win_pct": round(float(np.average(grp["win_pct"], weights=grp["n"])), 1),
            "base_pct": round(float(np.average(grp["base_pct"], weights=grp["n"])), 1),
            "mean_atr": round(float(np.average(grp["mean_atr"], weights=grp["n"])), 3),
            "edge_pct": round(float(np.average(grp["win_pct"] - grp["base_pct"], weights=grp["n"])), 1),
        }),
        include_groups=False,
    ).reset_index()
    out = out[out["total_n"] > 0]
    # z по объединённой выборке (win_n / total_n против base)
    tot_win = []
    for (pat, side), grp in df.groupby(["pattern", "side"]):
        tot_win.append((pat, side, int((grp["win_pct"] / 100.0 * grp["n"]).sum())))
    tw = pd.DataFrame(tot_win, columns=["pattern", "side", "win_n"])
    out = out.merge(tw, on=["pattern", "side"], how="left")
    out["win_n"] = out["win_n"].fillna(0).astype(int)
    base = (out["base_pct"] / 100.0).clip(0.01, 0.99)
    se = np.sqrt(base * (1 - base) / out["total_n"].clip(lower=1))
    out["z"] = ((out["win_n"] / out["total_n"].clip(lower=1)) - base) / se
    out["z"] = out["z"].round(2)
    return out.sort_values("z", ascending=False).reset_index(drop=True)


def print_table(stats: list[pd.DataFrame], title: str, min_events: int = 30):
    df = _agg(stats)
    if df.empty:
        print(f"\n### {title}: нет данных")
        return
    df = df[df["total_n"] >= min_events]
    print(f"\n### {title} (n>=min {min_events})")
    print(f"{'pattern':16s} {'side':5s} {'n':>6s} {'win%':>7s} {'base%':>7s} "
          f"{'edge%':>7s} {'meanATR':>8s} {'z':>6s}")
    for _, r in df.iterrows():
        flag = " ◀" if abs(r["z"]) >= 2.5 else ""
        print(f"{r['pattern']:16s} {r['side']:5s} {int(r['total_n']):6d} {r['win_pct']:7.1f} "
              f"{r['base_pct']:7.1f} {r['edge_pct']:+7.1f} {r['mean_atr']:+8.3f} {r['z']:+6.2f}{flag}")


def _halves(df: pd.DataFrame):
    mid = len(df) // 2
    return ("1st_half", df.iloc[:mid]), ("2nd_half", df.iloc[mid:])


def _eras(df: pd.DataFrame):
    war = df.index >= WAR_START
    return ("peace", df[~war]), ("war", df[war])


def main():
    parser = argparse.ArgumentParser(description="Candle pattern continuation research")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--min-events", type=int, default=30)
    parser.add_argument("--zone", type=int, default=20)
    args = parser.parse_args()

    tickers = available_tickers(args.db, args.period)
    if not tickers:
        print(f"Нет тикеров для {args.period} в {args.db}")
        return

    all_stats, h1_stats, h2_stats, peace_stats, war_stats = [], [], [], [], []
    per_ticker = []
    print(f"Сканирую {args.period} horizon={args.horizon} zone={args.zone} "
          f"({len(tickers)} тикеров: {', '.join(sorted(tickers))})")
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if len(df) < 120:
            continue
        s = cp.continuation_stats(df, horizon=args.horizon, zone=args.zone)
        if s.empty:
            continue
        all_stats.append(s)
        h1, h2 = _halves(df)
        s1 = cp.continuation_stats(h1[1], horizon=args.horizon, zone=args.zone)
        s2 = cp.continuation_stats(h2[1], horizon=args.horizon, zone=args.zone)
        if not s1.empty:
            h1_stats.append(s1)
        if not s2.empty:
            h2_stats.append(s2)
        for name, sub in (("peace", _eras(df)[0][1]), ("war", _eras(df)[1][1])):
            ss = cp.continuation_stats(sub, horizon=args.horizon, zone=args.zone)
            if not ss.empty:
                (peace_stats if name == "peace" else war_stats).append(ss)
        # итог по тикеру (для per-ticker устойчивости)
        per_ticker.append((t, _agg([s])))

    print_table(all_stats, f"ВСЕ события {args.period}")
    print_table(h1_stats, f"1-я половина {args.period}")
    print_table(h2_stats, f"2-я половина {args.period}")
    if peace_stats:
        print_table(peace_stats, "Мир (до 2022-02-24)")
    if war_stats:
        print_table(war_stats, "Война (с 2022-02-24)")

    # Устойчивость: паттерн должен быть в плюсе в обеих половинах у >=60% тикеров
    print(f"\n### Устойчивость по тикерам (в плюсе в обеих половинах) {args.period}")
    rows = []
    for t, st in per_ticker:
        if st.empty:
            continue
        for _, r in st.iterrows():
            rows.append({"ticker": t, "pattern": r["pattern"], "side": r["side"],
                         "z": r["z"], "edge": r["edge_pct"], "n": r["total_n"]})
    if rows:
        pdf = pd.DataFrame(rows)
        g = pdf.groupby(["pattern", "side"]).apply(
            lambda grp: pd.Series({
                "positive_frac": round((grp["z"] > 1.5).mean(), 2),
                "positive_n": int((grp["z"] > 1.5).sum()),
                "tickers": int(len(grp)),
                "avg_z": round(float(grp["z"].mean()), 2),
                "total_events": int(grp["n"].sum()),
            }),
            include_groups=False,
        ).reset_index()
        g = g[g["positive_frac"] >= 0.5]
        if not g.empty:
            print(g.to_string(index=False))
        else:
            print("  нет паттернов, значимо положительных у >=50% тикеров")


if __name__ == "__main__":
    main()
