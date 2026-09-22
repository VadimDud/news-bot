#!/usr/bin/env python3
"""Aggregate ICT diagnostic across tickers: sum net by filter combo + direction.

Usage:
    PYTHONPATH=trading_moex TRADER_DATA_DIR=... python3 ict_diag.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import itertools

from app import storage
from app import ict_sweep_fvg as ict
from app.backtest import run_backtest
from app.fib_pullback import prepare_ohlc
from app.strategies import IctSweepFvgStrategy, strategy_defaults

TICKERS = ["MOEX", "T", "NLMK", "LKOH", "TATN", "CHMF", "NVTK", "GAZP"]
GRID = {
    "fvg_ob_required": [0, 1],
    "kill_zones": [0, 1],
    "mss_required": [0, 1],
    "htf_confirmation_required": [0, 1],
}


def load(ticker):
    raw = storage.get_candles(ticker, "4h")
    if raw.empty:
        return None
    return prepare_ohlc(raw)


def run(df, params):
    p = dict(params)
    p["precomputed"] = ict._compute_arrays(prepare_ohlc(df), None, **ict._detector_params(p))
    return run_backtest(df, IctSweepFvgStrategy, p, cash=100_000.0)


def main():
    data = {t: load(t) for t in TICKERS}
    data = {t: d for t, d in data.items() if d is not None and len(d) > 60}
    print("tickers:", ",".join(f"{t}({len(d)})" for t, d in data.items()))

    keys = list(GRID.keys())
    for direction in (0, 1, -1):
        print(f"\n########## direction={direction} ##########")
        agg = {}
        for combo in itertools.product(*[GRID[k] for k in keys]):
            tag = ",".join(f"{k}={v}" for k, v in zip(keys, combo))
            net = 0.0
            n = 0
            wins = 0
            cash0 = 100_000.0
            for t, df in data.items():
                p = strategy_defaults("ict_sweep_fvg")
                p["direction"] = direction
                for k, v in zip(keys, combo):
                    p[k] = v
                m = run(df, p)
                net += m["final_value"] - cash0
                n += m["trades_total"]
                wins += m["trades_won"]
            agg[tag] = (n, wins / n * 100 if n else 0.0, net)
        for tag, (n, win, net) in sorted(agg.items(), key=lambda x: -x[1][2]):
            print(f"  {tag}: n={n:3d} win={win:5.1f}% net={net:+9.0f} ₽")


if __name__ == "__main__":
    main()
