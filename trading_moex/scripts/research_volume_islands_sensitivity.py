"""Pre-registered robustness grid for VOL-ISLAND-001.

This reports all cells; it must not be used to select a best cell on the same
sample. It is intentionally an event-study diagnostic, not a trading runner.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from app.volume_analysis import load_candles
from app.volume_islands import IslandConfig, detect_islands, evaluate_islands


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--period", default="4h")
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/runs/volume_islands"))
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for ticker in args.tickers:
        frame = load_candles(args.database, ticker, args.period)
        for quantile in (0.10, 0.20, 0.30):
            for dominance in (0.50, 0.60, 0.70):
                for min_length in (2, 3, 4):
                    config = IslandConfig(
                        separator_quantile=quantile,
                        dominance_threshold=dominance,
                        min_length=min_length,
                        horizons=(4,),
                    )
                    islands = detect_islands(frame, config)
                    events = evaluate_islands(frame, islands, config)
                    if events.empty:
                        rows.append({
                            "ticker": ticker,
                            "separator_quantile": quantile,
                            "dominance_threshold": dominance,
                            "min_length": min_length,
                            "islands": len(islands),
                            "events": 0,
                            "mean_net_change_pct": None,
                            "positive_rate": None,
                        })
                        continue
                    rows.append({
                        "ticker": ticker,
                        "separator_quantile": quantile,
                        "dominance_threshold": dominance,
                        "min_length": min_length,
                        "islands": len(islands),
                        "events": len(events),
                        "mean_net_change_pct": float(events["net_change_pct"].mean()),
                        "positive_rate": float((events["net_change_pct"] > 0).mean()),
                    })

    started = datetime.now(UTC)
    run_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}_VOL-ISLAND-001-sensitivity"
    output = args.output / run_id
    output.mkdir(parents=True, exist_ok=False)
    result = pd.DataFrame(rows)
    result.to_csv(output / "sensitivity.csv.gz", index=False, compression="gzip")
    manifest = {
        "run_id": run_id,
        "study_id": "VOL-ISLAND-001",
        "period": args.period,
        "tickers": args.tickers,
        "cells": 27,
        "horizon": 4,
        "grid": {
            "separator_quantile": [0.10, 0.20, 0.30],
            "dominance_threshold": [0.50, 0.60, 0.70],
            "min_length": [2, 3, 4],
        },
        "selection_policy": "report all cells; no best-cell selection",
        "provenance_status": "diagnostic; existing dirty worktree",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = result.groupby(["separator_quantile", "dominance_threshold", "min_length"], as_index=False).agg(
        tickers=("ticker", "nunique"),
        total_events=("events", "sum"),
        mean_net_change_pct=("mean_net_change_pct", "mean"),
        median_ticker_net_change_pct=("mean_net_change_pct", "median"),
        mean_positive_rate=("positive_rate", "mean"),
    )
    summary.to_json(output / "summary.json", orient="records", indent=2)
    (output / "run.log").write_text(
        "All 27 pre-registered parameter cells were reported; no cell was selected.\n",
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
