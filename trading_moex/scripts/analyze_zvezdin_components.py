#!/usr/bin/env python3
"""Analyze saved Zvezdin component events without changing trading rules."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median


GROUPS = {
    "level_impulse": ("strong_level", "reverse_impulse"),
    "level_impulse_accel": ("strong_level", "reverse_impulse", "acceleration"),
    "level_impulse_atr": ("strong_level", "reverse_impulse", "atr_completion"),
    "level_impulse_volume": ("strong_level", "reverse_impulse", "volume_participant"),
    "all_five": (
        "acceleration", "atr_completion", "strong_level",
        "volume_participant", "reverse_impulse",
    ),
}


def load_rows(directory: Path) -> list[dict]:
    rows = []
    for path in sorted(directory.glob("*.csv")):
        ticker = path.stem.split("_")[0]
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                row["ticker"] = ticker
                row["bar"] = int(row["bar"])
                rows.append(row)
    return rows


def matches(row: dict, components: tuple[str, ...]) -> bool:
    return all(row[name] == "True" for name in components)


def signed_return(row: dict, horizon: int) -> float | None:
    value = row.get(f"fwd_{horizon}_return", "")
    if value == "":
        return None
    value = float(value)
    return value if row["side"] == "LONG" else -value


def classify(value: float) -> str:
    if value > 0:
        return "WIN"
    if value < 0:
        return "LOSS"
    return "FLAT"


def select_cooldown(rows: list[dict], cooldown: int) -> list[dict]:
    selected = []
    last_by_ticker: dict[str, int] = {}
    for row in sorted(rows, key=lambda item: (item["ticker"], item["bar"], item["side"])):
        last = last_by_ticker.get(row["ticker"])
        if last is not None and row["bar"] - last < cooldown:
            continue
        selected.append(row)
        last_by_ticker[row["ticker"]] = row["bar"]
    return selected


def stats(rows: list[dict], horizons: tuple[int, ...]) -> dict:
    result = {"count": len(rows), "horizons": {}}
    for horizon in horizons:
        values = [signed_return(row, horizon) for row in rows]
        values = [value for value in values if value is not None]
        outcomes = Counter(classify(value) for value in values)
        result["horizons"][str(horizon)] = {
            "count": len(values),
            "wins": outcomes["WIN"],
            "losses": outcomes["LOSS"],
            "flat": outcomes["FLAT"],
            "win_rate_ex_flat": (
                outcomes["WIN"] / (outcomes["WIN"] + outcomes["LOSS"])
                if outcomes["WIN"] + outcomes["LOSS"] else 0.0
            ),
            "mean_return_bps": 10000 * sum(values) / len(values) if values else 0.0,
            "median_return_bps": 10000 * median(values) if values else 0.0,
            "p25_return_bps": 10000 * sorted(values)[max(0, len(values) // 4)] if values else 0.0,
            "p75_return_bps": 10000 * sorted(values)[max(0, (3 * len(values)) // 4)] if values else 0.0,
        }
    return result


def build_report(rows: list[dict], horizons: tuple[int, ...], cooldown: int) -> dict:
    candidates = [row for row in rows if row["candidate"] == "True"]
    sparse = select_cooldown(candidates, cooldown)
    report = {
        "events": len(rows),
        "candidates": len(candidates),
        "cooldown_bars": cooldown,
        "non_overlapping_candidates": len(sparse),
        "groups": {},
        "per_ticker": {},
    }
    for name, components in GROUPS.items():
        report["groups"][name] = {
            "components": components,
            "all": stats([row for row in candidates if matches(row, components)], horizons),
            "non_overlapping": stats([row for row in sparse if matches(row, components)], horizons),
        }
    for ticker in sorted({row["ticker"] for row in rows}):
        ticker_candidates = [row for row in candidates if row["ticker"] == ticker]
        ticker_sparse = [row for row in sparse if row["ticker"] == ticker]
        report["per_ticker"][ticker] = {
            "candidates": len(ticker_candidates),
            "non_overlapping_candidates": len(ticker_sparse),
            "groups": {
                name: stats([row for row in ticker_sparse if matches(row, components)], horizons)
                for name, components in GROUPS.items()
            },
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Zvezdin component CSV reports")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizons", default="8,32,96")
    parser.add_argument("--cooldown", type=int, default=32)
    args = parser.parse_args()
    if args.cooldown < 1:
        raise SystemExit("--cooldown must be positive")
    horizons = tuple(int(value) for value in args.horizons.split(",") if value.strip())
    report = build_report(load_rows(Path(args.input_dir)), horizons, args.cooldown)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
