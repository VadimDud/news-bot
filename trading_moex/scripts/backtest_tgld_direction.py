#!/usr/bin/env python3
"""Проверка long/short/both для стратегий TGLD с параметром direction (TF >= 1h)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import storage
from app.backtest import run_backtest
from app.strategies import STRATEGIES, strategy_defaults


def load(period):
    raw = storage.get_candles("TGLD", period)
    raw["begin"] = pd.to_datetime(raw["begin"])
    raw = raw.set_index("begin").sort_index()
    raw.index.name = "datetime"
    return raw[["open", "high", "low", "close", "volume"]].drop_duplicates()


def main():
    periods = sys.argv[1].split(",") if len(sys.argv) > 1 else ["60min", "2h", "4h"]
    dir_strats = ["fib_pullback", "zone_break", "kinetic", "ict_sweep_fvg", "vol_breakdown"]
    for period in periods:
        df = load(period)
        print(f"\n=== TGLD {period}: {len(df)} бар ===", flush=True)
        for key in dir_strats:
            p0 = strategy_defaults(key, "TGLD")
            if "direction" not in p0:
                continue
            for d in (1, -1, 0):
                p = dict(p0)
                p["direction"] = d
                try:
                    m = run_backtest(df, STRATEGIES[key]["cls"], p, cash=100000.0, commission=0.0005)
                except Exception as e:  # noqa: BLE001
                    print(f"  {key:14s} dir={d:+d}: ERR {e}", flush=True)
                    continue
                pf = m.get("profit_factor")
                pf_s = "—" if pf is None else f"{pf:.2f}"
                print(f"  {key:14s} dir={d:+d}: ret={m['total_return_pct']:+7.2f}%  "
                      f"trades={m['trades_total']:>3d}  win={m['win_rate_pct']:5.1f}%  pf={pf_s}", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
