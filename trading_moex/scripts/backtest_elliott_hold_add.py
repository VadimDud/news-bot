#!/usr/bin/env python3
"""Hold-add vs классический мартингейл Elliott (per-ticker, 10M депозит).

Режим hold_add: при минусе на закрытии свечи позиция НЕ закрывается, а на
открытии СЛЕДУЮЩЕЙ свечи добавляется лот (25→50→100% капитала цикла).
Выход всей позиции при суммарном плюсе на закрытии или после max_steps
шагов (перенос через ночь/гэпы учитываются честно).

Сравнивается с классикой: каждый шаг — отдельная сделка open→close, при
минусе ре-вход удвоенным лотом на open следующей свечи.

Usage (from trading_moex/):
    python3 scripts/backtest_elliott_hold_add.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

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


def run_ticker(df: pd.DataFrame, params: dict) -> dict:
    bt = ec.run_backtest(df, initial_equity=DEPOSIT, **params)
    m = bt["metrics"]
    peak = DEPOSIT
    mdd = 0.0
    for _d, v in bt["equity_curve"][1:]:
        peak = max(peak, v)
        mdd = max(mdd, peak - v)
    return {
        "cycles": m.get("total_cycles", 0),
        "trades": m.get("total_trades", 0),
        "win": m.get("win_rate", 0.0),
        "pnl": m.get("total_pnl", 0.0),
        "final": m.get("final_equity", DEPOSIT),
        "max_dd": mdd,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Elliott hold-add vs мартингейл")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    dfs = {}
    for t in tickers:
        df = load_df(t, args.db)
        if not df.empty:
            dfs[t] = df
    print(f"Elliott HOLD-ADD | депозит={DEPOSIT:,.0f} ₽ на тикер | 1day | "
          f"мартингейл 25→50→100, комиссия {args.commission*100:.2f}%/"
          f"слайпедж {args.slippage*100:.2f}%\n")

    base = {"wave_min": 3, "wave_max": 5, "base_pct": 0.25, "max_steps": 3,
            "commission": args.commission}

    def table(label: str, params: dict) -> None:
        print(f"\n{label}")
        print(f"  {'тикер':<6} {'циклов':>6} {'сделок':>6} {'win':>6} "
              f"{'net':>13} {'maxDD%':>7}")
        tot_net = 0.0
        tot_cycles = 0
        tot_wins = 0
        for t in tickers:
            r = run_ticker(dfs[t], params)
            tot_net += r["pnl"]
            tot_cycles += r["cycles"]
            tot_wins += int(round(r["win"] * r["cycles"]))
            if r["cycles"]:
                print(f"  {t:<6} {r['cycles']:>6} {r['trades']:>6} "
                      f"{r['win']*100:>5.1f}% {r['pnl']:>+13,.0f} {r['max_dd']/DEPOSIT*100:>6.1f}%")
        if tot_cycles:
            print(f"  {'ИТОГО':<6} {tot_cycles:>6} {'':>6} {tot_wins/tot_cycles*100:>5.1f}% "
                  f"{tot_net:>+13,.0f}")

    table("A. Классика (ре-вход удвоенным лотом, без переноса):", base)
    table("B. HOLD-ADD (держать в минусе + добавить на open след. свечи):",
          {**base, "hold_add": 1})

    print("\nC. HOLD-ADD с фильтром качества:")
    for qmin in (0.4, 0.8):
        table(f"  hold_add=1 q>={qmin}", {**base, "hold_add": 1, "quality_min": qmin})

    print("\nD. HOLD-ADD: 2 шага (25→50, без третьего):")
    table("  hold_add=1 max_steps=2", {**base, "hold_add": 1, "max_steps": 2})

    print("\nE. HOLD-ADD + расширенные волны (коррекции внутри):")
    table("  hold_add=1 use_corrections=1",
          {**base, "hold_add": 1, "use_corrections": 1, "macro_min_legs": 2,
           "macro_max_candles": 13, "corr_max_bars": 2, "corr_max_retr": 1.0,
           "w4_no_overlap": 1})


if __name__ == "__main__":
    main()
