#!/usr/bin/env python3
"""Incrementally cache MOEX candles in the trader SQLite database.

Exchange requests are forced to bypass proxy environment variables. Existing
rows are reused by ``fetch_history(..., use_cache=True)`` and the database
primary key makes repeated downloads idempotent.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

# MOEX/T-Bank traffic must not inherit a general-purpose proxy.
for _name in (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
):
    os.environ.pop(_name, None)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "trading_moex") not in sys.path:
    sys.path.insert(0, str(ROOT / "trading_moex"))

from app import config, data, storage  # noqa: E402


DEFAULT_TICKERS = ("CHMF", "GAZP", "LKOH", "MOEX", "MTSS", "NLMK", "NVTK", "SBER", "T", "TATN")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Incrementally cache MOEX candles")
    parser.add_argument("--db", default=str(ROOT / "trading_moex" / "data" / "trader_4h.db"))
    parser.add_argument("--period", default="15min", choices=tuple(data.PERIODS))
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.days < 1:
        raise SystemExit("--days must be positive")
    end = args.end or date.today()
    start = args.start or (end - timedelta(days=args.days))
    if start >= end:
        raise SystemExit("start date must precede end date")

    db_path = Path(args.db).resolve()
    config.DB_PATH = db_path
    config.DATA_DIR = db_path.parent
    storage.init_db()

    tickers = tuple(item.strip().upper() for item in args.tickers.split(",") if item.strip())
    for ticker in tickers:
        print(f"[{ticker} {args.period}] syncing {start}..{end}", flush=True)
        frame = data.fetch_history(ticker, args.period, start, end, use_cache=True)
        with sqlite3.connect(db_path) as connection:
            count, first, last = connection.execute(
                "SELECT COUNT(*), MIN(begin), MAX(begin) FROM candles WHERE ticker=? AND period=?",
                (ticker, args.period),
            ).fetchone()
        print(f"[{ticker} {args.period}] cached={count} first={first} last={last} returned={len(frame)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
