#!/usr/bin/env python3
"""Probe MOEX order-flow endpoints without exposing credentials or responses."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any


for _name in (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy",
):
    os.environ.pop(_name, None)


def _probe(ticker: str, method: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        from moexalgo import Ticker

        result = getattr(Ticker(ticker), method)(**kwargs)
        rows = list(result)
        return {
            "status": "ok",
            "rows": len(rows),
            "fields": sorted(rows[0]) if rows else [],
        }
    except Exception as exc:  # Network/auth/library errors are the probe's output.
        return {"status": "error", "error_type": type(exc).__name__, "error": str(exc)[:240]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", default="SBER")
    parser.add_argument("--date", help="YYYY-MM-DD; used for historical tradestats")
    args = parser.parse_args()

    date = args.date
    probes = {
        "tradestats": _probe(
            args.ticker,
            "tradestats",
            {"start": date, "end": date, "native": True} if date else {"native": True},
        ),
        "trades": _probe(args.ticker, "trades", {"native": True}),
        "orderbook": _probe(args.ticker, "orderbook", {"native": True}),
    }
    print(json.dumps({"ticker": args.ticker, "date": date, "probes": probes}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
