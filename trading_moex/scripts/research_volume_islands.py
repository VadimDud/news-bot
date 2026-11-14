"""Run the VOL-ISLAND-001 causal event study on one ticker."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.volume_analysis import load_candles  # noqa: E402
from app.volume_islands import (  # noqa: E402
    IslandConfig,
    detect_islands,
    evaluate_islands,
    evaluate_pullback_entries,
    summarize_islands,
)


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _json_default(value):
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value)!r}")


def run(args: argparse.Namespace) -> Path:
    started = datetime.now(UTC)
    frame = load_candles(args.database, args.ticker, args.period)
    config = IslandConfig(
        volume_window=args.volume_window,
        separator_quantile=args.separator_quantile,
        min_length=args.min_length,
        dominance_threshold=args.dominance_threshold,
        max_neutral_share=args.max_neutral_share,
        horizons=tuple(args.horizons),
    )
    islands = detect_islands(frame, config)
    events = evaluate_islands(frame, islands, config)
    original_directions = frame["close"].gt(frame["open"]).astype(int)
    original_directions = np.where(
        frame["close"].lt(frame["open"]), -1, original_directions
    )
    placebo_runs = []
    for seed in args.placebo_seeds:
        rng = np.random.default_rng(seed)
        placebo_directions = pd.Series(rng.permutation(original_directions), index=frame.index)
        placebo_islands = detect_islands(frame, config, directions=placebo_directions)
        placebo_events = evaluate_islands(frame, placebo_islands, config)
        placebo_runs.append((seed, placebo_islands, placebo_events))
    placebo_islands = placebo_runs[0][1]
    placebo_events = placebo_runs[0][2]
    pullbacks = evaluate_pullback_entries(frame, islands, config, horizon=args.pullback_horizon)
    split_edges = [0.0, 0.50, 0.70, 0.90, 1.0]
    split_names = ("train", "validation", "test", "forward")
    split_summary: dict[str, list[dict]] = {}
    if not events.empty:
        event_positions = events["confirmation_index"].astype(int) / max(len(frame) - 1, 1)
        for name, lower, upper in zip(split_names, split_edges, split_edges[1:]):
            selected = events.loc[(event_positions >= lower) & (event_positions < upper)]
            split_summary[name] = summarize_islands(selected).to_dict("records")
    else:
        split_summary = {name: [] for name in split_names}
    run_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}_VOL-ISLAND-001_{_git_sha() or 'nogit'}_{args.ticker}"
    output = Path(args.output) / run_id
    output.mkdir(parents=True, exist_ok=False)

    source_bytes = frame.to_csv(index=False).encode()
    manifest = {
        "run_id": run_id,
        "study_id": "VOL-ISLAND-001",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(UTC),
        "command": " ".join(sys.argv),
        "git_commit": _git_sha(),
        "python": platform.python_version(),
        "database_identifier": str(Path(args.database).expanduser().resolve()),
        "ticker": args.ticker.upper(),
        "period": args.period,
        "storage_timezone": "UTC-naive SQLite timestamps",
        "market_timezone": "Europe/Moscow",
        "date_start": frame["timestamp"].min(),
        "date_end": frame["timestamp"].max(),
        "rows": len(frame),
        "input_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "parameters": config.__dict__,
        "execution_model": "event study; entry is next bar open; no costs applied",
        "provenance_status": "diagnostic unless run from a clean commit with immutable data snapshot",
    }
    metrics = {
        "input_rows": len(frame),
        "islands": len(islands),
        "events": len(events),
        "summary": summarize_islands(events).to_dict("records"),
        "placebo_summary": summarize_islands(placebo_events).to_dict("records"),
        "placebo_seeds": args.placebo_seeds,
        "placebo_islands": len(placebo_islands),
        "placebo_events": len(placebo_events),
        "placebo_runs": [
            {"seed": seed, "islands": len(p_islands), "summary": summarize_islands(p_events).to_dict("records")}
            for seed, p_islands, p_events in placebo_runs
        ],
        "pullback_summary": (
            pullbacks.groupby("pullback_level", as_index=False)
            .agg(
                events=("pullback_level", "size"),
                mean_net_change_pct=("net_change_pct", "mean"),
                median_bars_to_fill=("bars_to_fill", "median"),
                positive_rate=("net_change_pct", lambda values: float((values > 0).mean())),
            )
            .to_dict("records")
            if not pullbacks.empty
            else []
        ),
        "pullback_horizon": args.pullback_horizon,
        "chronological_split_summary": split_summary,
    }
    checks = {
        "timestamps_sorted_unique": bool(frame["timestamp"].is_monotonic_increasing and frame["timestamp"].is_unique),
        "no_event_before_confirmation": bool(
            events.empty or (events["entry_index"] > events["confirmation_index"]).all()
        ),
        "separator_excluded_from_island": bool(
            islands.empty or (islands["confirmation_index"] > islands["end_index"]).all()
        ),
        "open_positions": "not applicable to event study",
        "costs": "not applied; provide venue-specific costs before strategy evaluation",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, default=_json_default, indent=2), encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps(metrics, default=_json_default, indent=2), encoding="utf-8")
    (output / "checks.json").write_text(json.dumps(checks, default=_json_default, indent=2), encoding="utf-8")
    events.to_csv(output / "events.csv.gz", index=False, compression="gzip")
    islands.to_csv(output / "islands.csv.gz", index=False, compression="gzip")
    placebo_events.to_csv(output / "placebo_events.csv.gz", index=False, compression="gzip")
    placebo_islands.to_csv(output / "placebo_islands.csv.gz", index=False, compression="gzip")
    pullbacks.to_csv(output / "pullback_events.csv.gz", index=False, compression="gzip")
    (output / "run.log").write_text(
        f"Loaded {len(frame)} rows, detected {len(islands)} islands, evaluated {len(events)} events.\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", default="4h")
    parser.add_argument("--output", default="artifacts/runs/volume_islands", type=Path)
    parser.add_argument("--volume-window", type=int, default=20)
    parser.add_argument("--separator-quantile", type=float, default=0.20)
    parser.add_argument("--min-length", type=int, default=2)
    parser.add_argument("--dominance-threshold", type=float, default=0.60)
    parser.add_argument("--max-neutral-share", type=float, default=0.30)
    parser.add_argument("--horizons", type=int, nargs="+", default=[1, 2, 4, 8, 12, 20])
    parser.add_argument("--placebo-seeds", type=int, nargs="+", default=[20261112, 20261113, 20261114, 20261115, 20261116])
    parser.add_argument("--pullback-horizon", type=int, default=4)
    args = parser.parse_args()
    print(run(args))


if __name__ == "__main__":
    main()
