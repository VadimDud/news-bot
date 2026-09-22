#!/usr/bin/env python3
"""CLI backtest / diagnostics for ICT Liquidity Sweep + FVG (reversal).

Usage (from repo root):
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_ict_sweep_fvg.py \
        --tickers MOEX,T,NLMK,LKOH,TATN,CHMF,NVTK,GAZP --periods 4h
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_ict_sweep_fvg.py \
        --grid --csv ict_results.csv

Диагностическая матрица (обязательна по конвенции репо): базовый сетап против
каждого входного фильтра по отдельности — чтобы поймать «фильтр режет net».
"""

import argparse
import itertools
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import data, storage
from app.backtest import run_backtest
from app import ict_sweep_fvg as ict
from app.fib_pullback import prepare_ohlc
from app.strategies import STRATEGIES, IctSweepFvgStrategy, strategy_defaults

DEFAULT_TICKERS = ["MOEX", "T", "NLMK", "LKOH", "TATN", "CHMF", "NVTK", "GAZP"]
DEFAULT_PERIODS = ["4h"]
DEFAULT_CASH = 100_000.0
DEFAULT_DAYS = 400

# Оси перебора: baseline → +OB → +kill zones → +MSS → +контртренд-фильтр.
GRID = {
    "fvg_ob_required": [0, 1],
    "kill_zones": [0, 1],
    "mss_required": [0, 1],
    "htf_confirmation_required": [0, 1],
}


def load_df(ticker: str, period: str, start: date, end: date) -> pd.DataFrame | None:
    try:
        return data.fetch_history(ticker, period, start, end)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ {ticker} {period}: MOEX недоступен ({e}), пробую кэш...")
        try:
            raw = storage.get_candles(ticker, period, start=start, end=end)
            if raw.empty:
                print(f"  ⚠ {ticker} {period}: кэш пуст")
                return None
            df = raw.copy()
            df["begin"] = pd.to_datetime(df["begin"])
            df = df.set_index("begin").sort_index()
            df.index.name = "datetime"
            return df[["open", "high", "low", "close", "volume"]].drop_duplicates()
        except Exception as e2:  # noqa: BLE001
            print(f"  ⚠ {ticker} {period}: кэш недоступен ({e2})")
            return None


def base_params(direction: int) -> dict:
    p = strategy_defaults("ict_sweep_fvg")
    p["direction"] = direction
    return p


def print_metrics(m: dict, tag: str):
    if m.get("trades_total", 0) == 0:
        print(f"{'':3}{tag}: нет сделок")
        return
    print(
        f"{'':3}{tag}: ret={m['total_return_pct']:+.2f}%  trades={m['trades_total']}  "
        f"win={m['win_rate_pct']:.1f}%  pf={m['profit_factor']}  dd={m['max_drawdown_pct']:.2f}%"
    )


def run_one(df, params: dict, cash: float) -> dict:
    p = dict(params)
    p["precomputed"] = ict._compute_arrays(
        prepare_ohlc(df), None, **ict._detector_params(p)
    )
    return run_backtest(df, IctSweepFvgStrategy, p, cash=cash)


def main():
    parser = argparse.ArgumentParser(description="ICT Liquidity Sweep + FVG backtest")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--start", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD")
    parser.add_argument("--grid", action="store_true", help="матрица фильтров")
    parser.add_argument("--direction", type=int, default=0,
                        help="0=оба (default), 1=только лонг, -1=только шорт")
    parser.add_argument("--csv", default=None, help="сохранить результаты в CSV")
    args = parser.parse_args()

    start = pd.Timestamp(args.start).date() if args.start else date.today() - timedelta(days=args.days)
    end = pd.Timestamp(args.end).date() if args.end else date.today()
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    periods = [p.strip() for p in args.periods.split(",") if p.strip()]

    rows = []
    for ticker in tickers:
        for period in periods:
            df = load_df(ticker, period, start, end)
            if df is None or len(df) < 60:
                print(f"  {ticker} {period}: данных мало ({0 if df is None else len(df)})")
                continue
            print(f"\n=== {ticker} {period} ({start}..{end}, {len(df)} bars) ===")
            bh = (float(df["close"].iloc[-1]) / float(df["close"].iloc[0]) - 1) * 100
            print(f"  buy&hold: {bh:+.2f}%")

            if not args.grid:
                m = run_one(df, base_params(args.direction), args.cash)
                print_metrics(m, f"dir={args.direction}")
                continue

            keys = list(GRID.keys())
            for combo in itertools.product(*[GRID[k] for k in keys]):
                p = base_params(args.direction)
                for k, v in zip(keys, combo):
                    p[k] = v
                m = run_one(df, p, args.cash)
                tag = ",".join(f"{k}={v}" for k, v in zip(keys, combo))
                print_metrics(m, tag)
                rows.append(
                    {"ticker": ticker, "period": period, "dir": args.direction, tag: ""}
                    | {k: v for k, v in zip(keys, combo)}
                    | {k: m[k] for k in ("trades_total", "win_rate_pct",
                                         "total_return_pct", "max_drawdown_pct", "profit_factor")}
                )

    if args.csv and rows:
        out = ROOT / args.csv
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"\nРезультаты: {out}")


if __name__ == "__main__":
    main()
