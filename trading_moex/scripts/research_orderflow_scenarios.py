#!/usr/bin/env python3
"""Summarize fixed order-flow scenarios from the bot's SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from app.orderflow_research import evaluate_orderflow_scenarios, load_orderflow_bars, summarize_scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/trader.db")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--horizon", type=int, default=4)
    args = parser.parse_args()
    with sqlite3.connect(Path(args.db).expanduser()) as connection:
        candles = pd.read_sql_query(
            "SELECT begin AS timestamp, close, volume FROM candles WHERE ticker = ? AND period = '15min' ORDER BY begin",
            connection, params=(args.ticker.upper(),),
        ) if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'candles'"
        ).fetchone() else pd.DataFrame(columns=["timestamp", "close", "volume"])
    bars = load_orderflow_bars(args.db, args.ticker)
    events = evaluate_orderflow_scenarios(bars, candles, horizon=args.horizon)
    print(summarize_scenarios(events).to_json(orient="records", indent=2))
    print(f"events={len(events)} flow_bars={len(bars)} candles={len(candles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
