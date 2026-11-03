"""Run a reproducible research experiment for any registered strategy.

Example:
    python -m scripts.research_strategy --strategy zone_break --study-zone ZB-001 --split test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.sr_research import (
    DEFAULT_TICKERS, ExperimentSpec, new_run_id, run_experiment,
    write_report, write_run_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--study-id", default=None)
    parser.add_argument("--db", default="data/trader_4h.db")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--split", choices=("full", "train", "test"), default="full")
    parser.add_argument("--split-at", default="2026-04-01")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="Override a strategy parameter; repeatable.")
    parser.add_argument("--output", help="Legacy single JSON output path")
    parser.add_argument("--run-dir", help="Artifact directory; defaults to artifacts/runs/<strategy>/<run-id>")
    parser.add_argument("--tickers", nargs="+", default=list(DEFAULT_TICKERS))
    args = parser.parse_args()

    overrides = {}
    for assignment in args.set:
        key, _, raw = assignment.partition("=")
        if not _:
            parser.error(f"--set expects KEY=VALUE, got {assignment!r}")
        for cast in (int, float):
            try:
                overrides[key] = cast(raw)
                break
            except ValueError:
                continue
        else:
            overrides[key] = raw

    study_id = args.study_id or args.strategy.upper()
    spec = ExperimentSpec(
        db_path=args.db,
        period=args.period,
        commission=args.commission,
        slippage=args.slippage,
        split=args.split,
        split_at=args.split_at,
        start=args.start,
        end=args.end,
        tickers=tuple(args.tickers),
        strategy=args.strategy,
        study_id=study_id,
    )
    report = run_experiment(spec, overrides)
    run_dir = (
        Path(args.run_dir) if args.run_dir
        else Path("artifacts/runs") / args.strategy / new_run_id(study_id)
    )
    write_run_artifacts(report, run_dir, command=" ".join(sys.argv))
    if args.output:
        write_report(report, args.output)
    print(json.dumps(report["pooled"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
