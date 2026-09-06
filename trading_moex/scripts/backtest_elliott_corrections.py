#!/usr/bin/env python3
"""Бэктест Elliott-расширенных волн (с коррекциями внутри) на 10M депозите.

Идея: волна может состоять не только из свечей одного цвета — импульсные ноги
одного цвета могут разделяться короткими неглубокими коррекциями противоположного
цвета (волны 2/4 Эллиотта). На старшем ТФ такая конструкция выглядит одной свечой.
Сигнал (fade) известен только при пробое структуры: слишком длинная/глубокая
коррекция, перекрытие волной 4 территории волны 1 или превышение лимита свечей.

Live-faithful: вход на open свечи ПОСЛЕ пробойной, выход на close той же,
мартингейл 25→50→100 (шаги на последующих свечах). Движок — prod
elliott_candles.run_backtest (после исправления lookahead).

Usage (from trading_moex/):
    python3 scripts/backtest_elliott_corrections.py --db data/trader_4h.db
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

from app import elliott_candles as ec  # noqa: E402

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
DEPOSIT = 10_000_000.0


def load_df(ticker: str, db: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period='1day' ORDER BY begin",
        con, params=(ticker,),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def run_basket(dfs: dict[str, pd.DataFrame], params: dict) -> dict:
    """Мартингейл-прогон по всем тикерам последовательно на общем капитале."""
    equity = DEPOSIT
    peak = equity
    mdd = 0.0
    cycles = 0
    wins = 0
    per_ticker = {}
    for t, df in dfs.items():
        bt = ec.run_backtest(df, initial_equity=equity, **params)
        m = bt["metrics"]
        per_ticker[t] = {"cycles": m.get("total_cycles", 0),
                         "pnl": m.get("total_pnl", 0.0),
                         "win": m.get("win_rate", 0.0)}
        cycles += per_ticker[t]["cycles"]
        wins += int(round(per_ticker[t]["win"] * per_ticker[t]["cycles"]))
        for _d, v in bt["equity_curve"][1:]:
            peak = max(peak, v)
            mdd = max(mdd, peak - v)
        equity = m.get("final_equity", equity)
    return {"cycles": cycles, "wins": wins, "net": equity - DEPOSIT,
            "final": equity, "max_dd": mdd, "per_ticker": per_ticker}


def _report(label: str, r: dict) -> None:
    if not r["cycles"]:
        print(f"  {label:44} нет циклов")
        return
    print(f"  {label:44} циклов={r['cycles']:>5} win={r['wins']/r['cycles']*100:>5.1f}% "
          f"net={r['net']:>+13,.0f} maxDD={r['max_dd']/DEPOSIT*100:>5.1f}%")


def macro_raw_stats(dfs: dict[str, pd.DataFrame], params: dict) -> None:
    """Raw-край макро-сигналов: один шаг, вход open пробойной+1, выход close."""
    all_rows = []
    for t, df in dfs.items():
        cl = ec.classify_candles(df, params.get("body_ratio_min", 0.6),
                                 params.get("atr_period", 14), params.get("atr_k", 0.5))
        sigs = ec.detect_extended_waves(
            cl, params.get("wave_min", 3), params.get("wave_max", 5),
            params.get("macro_min_legs", 2), params.get("macro_max_candles", 13),
            params.get("corr_max_bars", 2), params.get("corr_max_retr", 1.0),
            params.get("w4_no_overlap", 1),
        )
        for s in sigs:
            idx = s["break_idx"] + 1
            if idx >= len(df):
                continue
            o = float(df["open"].iloc[idx])
            c = float(df["close"].iloc[idx])
            fade = "short" if s["direction"] == "bull" else "long"
            gross = (o - c) / o if fade == "short" else (c - o) / o
            all_rows.append({"ticker": t, "dir": fade, "gross": gross,
                             "candles": s["end_idx"] - s["start_idx"] + 1})
    if not all_rows:
        print("  (макро-сигналов нет)")
        return
    g = pd.DataFrame(all_rows)
    for lbl, grp in [("все", g), ("шорт", g[g["dir"] == "short"]), ("лонг", g[g["dir"] == "long"])]:
        if not len(grp):
            continue
        print(f"    {lbl:6}: n={len(grp):>4} win={(grp['gross']>0).mean()*100:>5.1f}% "
              f"gross_mean={(grp['gross'].mean())*100:+.3f}% "
              f"gross_med={grp['gross'].median()*100:+.3f}% "
              f"свечей_в_волне={grp['candles'].mean():.1f}")
    q_buckets = g.groupby(pd.cut(g["candles"], [0, 5, 8, 13, 100], labels=["≤5", "6-8", "9-13", ">13"]))
    for name, grp in q_buckets:
        if len(grp):
            print(f"    волна {name:4}: n={len(grp):>4} win={(grp['gross']>0).mean()*100:>5.1f}% "
                  f"gross_mean={grp['gross'].mean()*100:+.3f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description="Elliott расширенные волны (коррекции)")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    dfs = {}
    for t in tickers:
        df = load_df(t, args.db)
        if not df.empty:
            dfs[t] = df
    print(f"Elliott КОРРЕКЦИИ | депозит={DEPOSIT:,.0f} ₽ | тикеров={len(dfs)} | "
          f"мартингейл 25→50→100, комиссия 0.05%/сторона\n")

    base = {"wave_min": 3, "wave_max": 5, "base_pct": 0.25, "max_steps": 3,
            "commission": 0.0005}

    print("A. Baseline — без коррекций (только одноцветные серии L=3..5):")
    _report("use_corrections=0", run_basket(dfs, base))

    print("\nB. Расширенные волны (коррекции внутри, макс. 13 свечей):")
    corr = {**base, "use_corrections": 1, "macro_min_legs": 2, "macro_max_candles": 13,
            "corr_max_bars": 2, "corr_max_retr": 1.0, "w4_no_overlap": 1}
    r_b = run_basket(dfs, corr)
    _report("use_corrections=1", r_b)
    for t in tickers:
        p = r_b["per_ticker"].get(t)
        if p and p["cycles"]:
            print(f"      {t:<6} циклов={p['cycles']:>4} win={p['win']*100:>5.1f}% "
                  f"net={p['pnl']:>+12,.0f}")

    print("\nC. Расширенные волны + фильтр качества:")
    for qmin in (0.4, 0.8):
        _report(f"use_corrections=1 q>={qmin}", run_basket(dfs, {**corr, "quality_min": qmin}))

    print("\nD. Sweep параметров коррекций (мартингейл):")
    print("    {'retr':>6} {'bars':>4} {'w4':>3} {'maxсв':>5} {'minног':>6} {'cycles':>7} {'win%':>6} {'net':>14} {'maxDD%':>7}")
    for retr in (0.5, 0.618, 1.0):
        for bars in (1, 2, 3):
            for w4 in (0, 1):
                p = {**corr, "corr_max_retr": retr, "corr_max_bars": bars, "w4_no_overlap": w4}
                r = run_basket(dfs, p)
                if r["cycles"]:
                    print(f"    {retr:>6} {bars:>4} {w4:>3} {13:>5} {2:>6} "
                          f"{r['cycles']:>7} {r['wins']/r['cycles']*100:>6.1f} "
                          f"{r['net']:>14,.0f} {r['max_dd']/DEPOSIT*100:>7.1f}")
    for legs in (3,):
        for mc in (21,):
            p = {**corr, "macro_min_legs": legs, "macro_max_candles": mc}
            r = run_basket(dfs, p)
            if r["cycles"]:
                print(f"    {'1.0':>6} {2:>4} {1:>3} {mc:>5} {legs:>6} "
                      f"{r['cycles']:>7} {r['wins']/r['cycles']*100:>6.1f} "
                      f"{r['net']:>14,.0f} {r['max_dd']/DEPOSIT*100:>7.1f}")

    print("\nE. Raw-край макро-сигналов (1 шаг, без мартингейла):")
    macro_raw_stats(dfs, corr)


if __name__ == "__main__":
    main()
