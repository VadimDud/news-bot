"""Run a reproducible support/resistance research experiment.

Example:
    python -m scripts.research_sr --split test --output reports/sr-test.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.sr_research import (
    DEFAULT_TICKERS, ExperimentSpec, new_run_id, run_experiment,
    write_report, write_run_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/trader_4h.db")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--scenario", type=int, default=2, choices=(0, 1, 2))
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--split", choices=("full", "train", "test"), default="full")
    parser.add_argument("--split-at", default="2026-04-01")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output", help="Legacy single JSON output path")
    parser.add_argument("--run-dir", help="Artifact directory; defaults to artifacts/runs/sr/<run-id>")
    parser.add_argument("--tickers", nargs="+", default=list(DEFAULT_TICKERS))
    args = parser.parse_args()
    spec = ExperimentSpec(
        db_path=args.db,
        period=args.period,
        scenario_mode=args.scenario,
        commission=args.commission,
        slippage=args.slippage,
        split=args.split,
        split_at=args.split_at,
        start=args.start,
        end=args.end,
        tickers=tuple(args.tickers),
    )
    report = run_experiment(spec)
    run_dir = Path(args.run_dir) if args.run_dir else Path("artifacts/runs/sr") / new_run_id()
    write_run_artifacts(report, run_dir, command=" ".join(__import__("sys").argv))
    if args.output:
        write_report(report, args.output)
    print(json.dumps(report["pooled"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
