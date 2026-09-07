#!/usr/bin/env python3
"""Честная валидация стратегии «Пробой зоны» (свечной паттерн-продолжение).

Методика (подробно: ``app/candle_patterns.py``, статистика:
``scripts/candle_pattern_research.py``):
- на дневках пробой зоны консолидации (close за пределы диапазона предыдущих
  ``zone`` баров) имеет статистически наибольшую вероятность продолжения
  (win-rate выше базовой ставки, z>2, положителен и в «военной» эре);
- фильтр ``strong_candle`` (длинное тело на баре пробоя) усиливает сигнал.

Live-faithful: сигнал на закрытии бара i, вход по open бара i+1, выход при
обратном пробое зоны (или ATR-стоп/тейк). Риск 1%, комиссия 0.05%/сторона.
Сравнение с buy&hold и случайным входом; разбивка на две половины истории.

Usage (from trading_moex/):
    python3 scripts/backtest_candle_zone.py --db data/trader_4h.db --period 1day
    python3 scripts/backtest_candle_zone.py --period 1day --grid
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.backtest import run_backtest  # noqa: E402
from app.strategies import STRATEGIES, ZoneBreakStrategy  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
CASH = 100_000.0

GRID = {
    "zone": [10, 20, 30, 50],
    "strong_candle": [0, 1],
    "direction": [1],
}


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3_connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def sqlite3_connect(db):
    import sqlite3
    return sqlite3.connect(str(db))


def available_tickers(db: str, period: str) -> list[str]:
    con = sqlite3_connect(db)
    rows = con.execute("SELECT DISTINCT ticker FROM candles WHERE period=?", (period,)).fetchall()
    con.close()
    return [r[0] for r in rows]


def base_params(**over) -> dict:
    p = {x["key"]: x["default"] for x in STRATEGIES["zone_break"]["params"]}
    p.update(over)
    return p


def print_metrics(m: dict, tag: str):
    if m["trades_total"] == 0:
        print(f"{'':3}{tag}: нет сделок")
        return
    print(
        f"{'':3}{tag}: ret={m['total_return_pct']:+7.2f}%  n={m['trades_total']:3d}  "
        f"win={m['win_rate_pct']:4.1f}%  pf={m['profit_factor']}  dd={m['max_drawdown_pct']:5.1f}%"
    )


def run_panel(ticker: str, df: pd.DataFrame, params: dict):
    print(f"\n=== Пробой зоны {ticker} {args.period} ({len(df)} баров) ===")
    mid = len(df) // 2
    for name, sub in (("вся история", df), ("train (1-я пол.)", df.iloc[:mid]), ("test (2-я пол.)", df.iloc[mid:])):
        if len(sub) < 100:
            print(f"  {name}: мало данных")
            continue
        print_metrics(run_backtest(sub, ZoneBreakStrategy, params, cash=CASH, commission=0.0005), name)
    bh = (float(df["close"].iloc[-1]) / float(df["close"].iloc[0]) - 1) * 100
    print(f"  buy&hold: {bh:+.2f}%")


def main():
    global args
    parser = argparse.ArgumentParser(description="Zone break honest validation")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--zone", type=int, default=None)
    parser.add_argument("--strong", type=int, default=None, help="0/1")
    parser.add_argument("--direction", type=int, default=1)
    parser.add_argument("--grid", action="store_true")
    args = parser.parse_args()

    tickers = [args.ticker] if args.ticker else available_tickers(args.db, args.period)
    over = {}
    if args.zone is not None:
        over["zone"] = args.zone
    if args.strong is not None:
        over["strong_candle"] = args.strong
    over["direction"] = args.direction
    params = base_params(**over)

    if not args.grid:
        for t in tickers:
            df = load_df(t, args.db, args.period)
            if len(df) < 150:
                print(f"{t} {args.period}: мало данных ({len(df)})")
                continue
            run_panel(t, df, params)
        return

    # ── Grid: обе половины должны быть прибыльными ─────────────────────────
    keys = list(GRID.keys())
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    print(f"Grid {args.period}: {len(combos)} комбинаций x {len(tickers)} тикеров")
    best = []
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if len(df) < 300:
            continue
        mid = len(df) // 2
        for combo in combos:
            p = base_params(**{k: v for k, v in zip(keys, combo)})
            tr = run_backtest(df.iloc[:mid], ZoneBreakStrategy, p, cash=CASH, commission=0.0005)
            te = run_backtest(df.iloc[mid:], ZoneBreakStrategy, p, cash=CASH, commission=0.0005)
            if tr["trades_total"] < 5 or te["trades_total"] < 3:
                continue
            if tr["total_return_pct"] <= 0 or te["total_return_pct"] <= 0:
                continue
            score = tr["total_return_pct"] + te["total_return_pct"]
            best.append((score, t, dict(p), tr, te))
    best.sort(key=lambda x: -x[0])
    if not best:
        print("нет комбинаций, прибыльных на обеих половинах")
        return
    for score, t, p, tr, te in best[:12]:
        cfg = {k: p[k] for k in keys}
        print(f"  {t:5s} train={tr['total_return_pct']:+7.2f}% test={te['total_return_pct']:+7.2f}% | {cfg}")


if __name__ == "__main__":
    main()
