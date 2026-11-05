#!/usr/bin/env python3
"""Recognition-quality report and event catalog for the TA element library.

This is *not* a backtest. It answers one question per element: does the
detector find the thing it claims to find, at what rate, and with what timing
on real data? Trading rules are deliberately out of scope (see
``app/ta_lib.py``).

Usage (from trading_moex/):
    python3 scripts/ta_elements_report.py --db data/trader_4h.db --period 2h
    python3 scripts/ta_elements_report.py --period 2h --tickers SBER T GAZP \
        --cat-dir artifacts/runs/ta_elements/catalog
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd  # noqa: E402

from app import ta_lib  # noqa: E402
from app.sr_research import DEFAULT_TICKERS, load_candles  # noqa: E402


def analyze_ticker(df: pd.DataFrame, params: dict) -> dict:
    sw = ta_lib.swings(df, look=params["look"])
    lv = ta_lib.levels(df, look=params["look"], merge_atr=params["merge_atr"])
    # ``levels`` emits a row per confirmation/update; the catalog wants one row
    # per distinct level (its final price).
    lv_final = lv.drop_duplicates(subset="level_idx", keep="last") if len(lv) else lv
    br = ta_lib.breakouts(df, lv_final, max_age_bars=params["max_age"])
    rt = ta_lib.retests(df, br, max_wait_bars=params["retest_wait"])
    rr = ta_lib.returns_to_level(df, br, max_wait_bars=params["retest_wait"])
    fa = ta_lib.failures(df, rr, look=params["look"], max_wait_bars=params["fail_wait"])
    return {
        "bars": int(len(df)),
        "swings": len(sw),
        "swing_highs": int((sw["side"] == "high").sum()),
        "swing_lows": int((sw["side"] == "low").sum()),
        "levels": len(lv_final),
        "levels_merged": int((lv_final["touches"] > 1).sum()) if len(lv_final) else 0,
        "breakouts": len(br),
        "retests": len(rt),
        "returns": len(rr),
        "failures": len(fa),
        "retest_rate": len(rt) / len(br) if len(br) else 0.0,
        "return_rate": len(rr) / len(br) if len(br) else 0.0,
        "fail_rate": len(fa) / len(rr) if len(rr) else 0.0,
        "swing_amp_atr_median": float(sw["amp_atr"].median()) if len(sw) else None,
        "break_dist_atr_median": float(br["dist_atr"].median()) if len(br) else None,
        "retest_wait_median": float(rt["bars_since"].median()) if len(rt) else None,
        "return_wait_median": float(rr["bars_since"].median()) if len(rr) else None,
        "_events": {
            "swings": sw, "levels": lv_final, "breakouts": br,
            "retests": rt, "returns": rr, "failures": fa,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/trader_4h.db")
    ap.add_argument("--period", default="2h")
    ap.add_argument("--tickers", nargs="+", default=list(DEFAULT_TICKERS))
    ap.add_argument("--look", type=int, default=3)
    ap.add_argument("--merge-atr", type=float, default=0.5)
    ap.add_argument("--max-age", type=int, default=500)
    ap.add_argument("--retest-wait", type=int, default=10)
    ap.add_argument("--fail-wait", type=int, default=20)
    ap.add_argument("--cat-dir", help="Write per-ticker event CSVs here")
    args = ap.parse_args()

    params = {
        "look": args.look, "merge_atr": args.merge_atr, "max_age": args.max_age,
        "retest_wait": args.retest_wait, "fail_wait": args.fail_wait,
    }
    cat = Path(args.cat_dir) if args.cat_dir else None
    if cat:
        cat.mkdir(parents=True, exist_ok=True)

    summary = {}
    rows = []
    for ticker in args.tickers:
        df = load_candles(args.db, ticker, args.period)
        if df is None or len(df) < 2 * args.look + 2:
            print(f"{ticker}: insufficient data, skipped")
            continue
        res = analyze_ticker(df, params)
        events = res.pop("_events")
        summary[ticker] = res
        rows.append({"ticker": ticker, **res})
        if cat:
            for name, frame in events.items():
                if len(frame):
                    frame.to_csv(cat / f"{ticker}_{name}.csv", index=False)

    if not rows:
        print(json.dumps({"error": "no data"}, indent=2))
        return

    table = pd.DataFrame(rows)
    numeric = [c for c in table.columns if c != "ticker"]
    pooled = {
        "tickers": len(table),
        **{f"mean_{c}": float(table[c].mean()) for c in numeric if c.startswith(("bars", "swings", "levels", "breakouts", "retests", "returns", "failures"))},
        **{f"mean_{c}": float(table[c].mean()) for c in ("retest_rate", "return_rate", "fail_rate")},
        **{f"median_{c}": float(table[c].median()) for c in ("swing_amp_atr_median", "break_dist_atr_median", "retest_wait_median", "return_wait_median")},
    }
    print(json.dumps({"params": params, "pooled": pooled, "per_ticker": summary}, indent=2))
    if cat:
        print(f"\nEvent catalog written to {cat}")


if __name__ == "__main__":
    main()
