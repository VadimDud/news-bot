#!/usr/bin/env python3
"""CLI backtest / grid-search for Fibonacci retracement (trend-continuation).

Usage (from repo root):
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_fib_pullback.py \
        --tickers SBER,LKOH --periods 1day --cash 100000
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_fib_pullback.py --grid
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_fib_pullback.py \
        --ticker YDEX --period 1h --grid --csv results.csv
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import data, storage
from app.backtest import run_backtest
from app.strategies import STRATEGIES, FibPullbackStrategy

DEFAULT_TICKERS = ["SBER", "LKOH"]
DEFAULT_PERIODS = ["30min", "1day"]
DEFAULT_CASH = 100_000.0
DEFAULT_DAYS = 365 * 2

# Параметры перебора (grid). Дефолты подбираются здесь, затем выносятся в
# TICKER_OVERRIDES/дефолты реестра, как у других стратегий.
GRID = {
    "trend_period": [50, 100, 200],
    "swing_bars": [5, 10, 20],
    "confluence_min": [1, 2],
    "fib_in_high": [0.618, 0.786],
    "rsi_oversold": [40.0, 50.0],
    "min_rr": [1.0, 1.5],
}
# Наборы параметров под шорт (direction=-1): те же ключи, другие кандидаты.
GRID_SHORT = {
    "trend_period": [50, 100, 200],
    "swing_bars": [5, 10, 20],
    "confluence_min": [1, 2],
    "fib_in_low": [0.382, 0.5],
    "fib_in_high": [0.618, 0.786],
    "rsi_overbought": [70.0, 80.0],
    "min_rr": [1.0, 1.5],
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


def base_params(direction: int = 1) -> dict:
    p = {pkey["key"]: pkey["default"] for pkey in STRATEGIES["fib_pullback"]["params"]}
    p["direction"] = direction
    if "min_swing_dist_atr" not in p:
        p["min_swing_dist_atr"] = 2.0
    return p


def print_metrics(m: dict, tag: str):
    if m.get("trades_total", 0) == 0:
        print(f"{'':3}{tag}: нет сделок")
        return
    print(
        f"{'':3}{tag}: ret={m['total_return_pct']:+.2f}%  trades={m['trades_total']}  "
        f"win={m['win_rate_pct']:.1f}%  pf={m['profit_factor']}  dd={m['max_drawdown_pct']:.2f}%"
    )


def run_one(df, params: dict) -> dict:
    return run_backtest(df, FibPullbackStrategy, params, cash=float(args.cash))


def main():
    global args
    parser = argparse.ArgumentParser(description="Fibonacci retracement backtest")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--start", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD")
    parser.add_argument("--grid", action="store_true", help="перебор параметров")
    parser.add_argument("--csv", default=None, help="сохранить результаты в CSV")
    parser.add_argument("--direction", type=int, default=1,
                        help="1=только лонг (default), -1=только шорт, 0=оба")
    args = parser.parse_args()

    start = pd.Timestamp(args.start).date() if args.start else date.today() - timedelta(days=args.days)
    end = pd.Timestamp(args.end).date() if args.end else date.today()
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    periods = [p.strip() for p in args.periods.split(",") if p.strip()]

    results = []
    for ticker in tickers:
        for period in periods:
            df = load_df(ticker, period, start, end)
            if df is None or len(df) < 60:
                print(f"  {ticker} {period}: данных мало ({0 if df is None else len(df)})")
                continue
            print(f"\n=== {ticker} {period} ({start}..{end}, {len(df)} bars) ===")
            if not args.grid:
                m = run_one(df, base_params(args.direction))
                print_metrics(m, "defaults")
                continue

            # ── Grid-search ────────────────────────────────────────────────
            best: list[tuple[dict, dict]] = []
            import itertools
            grid = GRID_SHORT if args.direction <= 0 else GRID
            keys = list(grid.keys())
            combos = list(itertools.product(*[grid[k] for k in keys]))
            for combo in combos:
                p = base_params(args.direction)
                for k, v in zip(keys, combo):
                    p[k] = v
                m = run_one(df, p)
                best.append((p, m))

            def key(item):
                m = item[1]
                # предпочитаем прибыльность при ограниченной просадке и не-нулевых сделках
                if m["trades_total"] == 0:
                    return (-1e9,)
                return (m["total_return_pct"], -m["max_drawdown_pct"])

            best.sort(key=key, reverse=True)
            # buy&hold для сравнения
            bh = (float(df["close"].iloc[-1]) / float(df["close"].iloc[0]) - 1) * 100
            print(f"  buy&hold: {bh:+.2f}%")

            print_metrics(best[0][1], "best")
            print(f"     params: {best[0][0]}")
            if args.csv:
                for p, m in best[:25]:
                    results.append(
                        {"ticker": ticker, "period": period, "params": repr(p)}
                        | {k: m[k] for k in
                           ("trades_total", "win_rate_pct", "total_return_pct", "max_drawdown_pct", "profit_factor")}
                    )

    if args.csv and results:
        out = ROOT / args.csv
        pd.DataFrame(results).to_csv(out, index=False)
        print(f"\nРезультаты: {out}")


if __name__ == "__main__":
    main()
