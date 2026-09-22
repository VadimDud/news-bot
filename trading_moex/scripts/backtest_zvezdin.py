#!/usr/bin/env python3
"""Run the deterministic Zvezdin engine from a CSV file.

Examples from the repository root::

    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_zvezdin.py \
        --input candles.csv --mode single --output result.json

    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_zvezdin.py \
        --input candles.csv --mode wfo --train-bars 252 --test-bars 63

The CSV must contain ``open, high, low, close, volume`` and may contain a
``datetime`` column. Rows are never sorted or forward-filled by this script.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "trading_moex") not in sys.path:
    sys.path.insert(0, str(ROOT / "trading_moex"))

from app.zvezdin_backtest import (  # noqa: E402
    assess_robustness,
    m1_bars_by_parent,
    run_dataframe_backtest,
    sensitivity_grid,
    stress_costs,
    summarize_sensitivity,
    walk_forward_optimize,
    walk_forward_backtest,
)
from app.zvezdin_contract import load_default_config, strategy_config_for_ticker, strategy_config_from_contract  # noqa: E402
from app.zvezdin_calendar import load_calendar  # noqa: E402
from app.zvezdin_engine import StrategyConfig  # noqa: E402


def load_csv(path: str | Path, datetime_column: str = "datetime") -> pd.DataFrame:
    frame = pd.read_csv(path)
    if datetime_column in frame.columns:
        frame[datetime_column] = pd.to_datetime(frame[datetime_column], utc=True, errors="raise")
        frame = frame.set_index(datetime_column)
        frame.index.name = "datetime"
    return frame


def load_sqlite_candles(path: str | Path, ticker: str, period: str) -> pd.DataFrame:
    """Load the repository's ``candles(ticker, period, begin, OHLCV)`` table."""

    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query(
            "SELECT begin AS datetime, open, high, low, close, volume "
            "FROM candles WHERE ticker=? AND period=? ORDER BY begin",
            connection,
            params=(ticker, period),
        )
    if frame.empty:
        raise ValueError(f"no candles found for ticker={ticker!r}, period={period!r}")
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True, errors="raise")
    return frame.set_index("datetime")


def load_runtime_config(path: str | None) -> StrategyConfig:
    return strategy_config_from_contract(path) if path else load_default_config()


def load_grid(path: str | Path) -> dict[str, list]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value or any(not isinstance(item, list) for item in value.values()):
        raise ValueError("grid must be a non-empty JSON object with array values")
    return value


def parse_multipliers(value: str) -> tuple[float, ...]:
    try:
        multipliers = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("--multipliers must be comma-separated numbers") from exc
    if not multipliers or any(not math.isfinite(item) or item < 0 for item in multipliers):
        raise ValueError("--multipliers must contain finite non-negative numbers")
    return multipliers


def run_cli(args: argparse.Namespace) -> dict:
    if args.sqlite:
        if not args.ticker or not args.period:
            raise ValueError("--ticker and --period are required with --sqlite")
        frame = load_sqlite_candles(args.sqlite, args.ticker, args.period)
    else:
        if not args.input:
            raise ValueError("--input is required unless --sqlite is used")
        frame = load_csv(args.input, args.datetime_column)
    config = load_runtime_config(args.config)
    if args.ticker:
        profile_source = args.config or (ROOT / "trading_moex" / "config" / "zvezdin_default_config_v1_1.json")
        config = strategy_config_for_ticker(profile_source, args.ticker)
    if args.calendar:
        config = replace(config, calendar=load_calendar(args.calendar))
    if args.zone_signal_mode:
        config = replace(
            config,
            zone_signal_mode=args.zone_signal_mode,
            near_zone_atr_ratio=args.near_zone_atr_ratio,
        )
    if args.relaxation_pct is not None:
        config = replace(config, relaxation_pct=args.relaxation_pct)
    if args.signal_mode:
        config = replace(config, signal_mode=args.signal_mode, min_soft_score=args.min_soft_score)
    if args.hold_on_breakout:
        config = replace(config, emergency_exit=False)
    if args.exhaustion_mode:
        config = replace(config, exhaustion_mode=args.exhaustion_mode)
    if args.no_entry_volume:
        config = replace(config, volume_entry_filter=False, score_requires_flow=False)
    if args.manage_volume:
        config = replace(config, post_entry_volume_management=True)
    m1_by_bar = None
    if args.m1_input:
        m1_frame = load_csv(args.m1_input, args.m1_datetime_column)
        m1_by_bar = m1_bars_by_parent(
            m1_frame, frame, args.m1_bar_minutes, args.parent_bar_minutes,
        )

    if args.mode == "single":
        return run_dataframe_backtest(
            frame, config, quantity=args.quantity, m1_by_bar=m1_by_bar,
            liquidate_at_end=args.liquidate_at_end,
        ).as_dict()
    if args.mode == "wfo":
        return walk_forward_backtest(
            frame,
            config,
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
            warmup_bars=args.warmup_bars,
            quantity=args.quantity,
            initial_capital=args.initial_capital,
            liquidate_at_end=args.liquidate_at_end,
            m1_by_bar=m1_by_bar,
        ).as_dict()
    if args.mode == "sensitivity":
        if not args.grid:
            raise ValueError("--grid is required for sensitivity mode")
        return {
            "results": [
                item.as_dict() for item in sensitivity_grid(
                    frame, config, load_grid(args.grid), args.quantity, m1_by_bar,
                    args.liquidate_at_end,
                )
            ]
        }
    if args.mode == "stress":
        multipliers = parse_multipliers(args.multipliers)
        return {
            "results": [
                item.as_dict() for item in stress_costs(
                    frame, config, multipliers, args.quantity, m1_by_bar, args.liquidate_at_end,
                )
            ]
        }
    if args.mode == "report":
        if args.optimize:
            if not args.grid:
                raise ValueError("--grid is required with --optimize")
            wfo = walk_forward_optimize(
                frame,
                config,
                load_grid(args.grid),
                train_bars=args.train_bars,
                test_bars=args.test_bars,
                step_bars=args.step_bars,
                warmup_bars=args.warmup_bars,
                quantity=args.quantity,
                initial_capital=args.initial_capital,
                m1_by_bar=m1_by_bar,
                liquidate_at_end=args.liquidate_at_end,
            )
        else:
            wfo = walk_forward_backtest(
                frame,
                config,
                train_bars=args.train_bars,
                test_bars=args.test_bars,
                step_bars=args.step_bars,
                warmup_bars=args.warmup_bars,
                quantity=args.quantity,
                initial_capital=args.initial_capital,
                m1_by_bar=m1_by_bar,
                liquidate_at_end=args.liquidate_at_end,
            )
        stress = stress_costs(
            frame, config, parse_multipliers(args.multipliers),
            args.quantity, m1_by_bar, args.liquidate_at_end,
        )
        sensitivity = None
        if args.grid:
            sensitivity = summarize_sensitivity(
                sensitivity_grid(frame, config, load_grid(args.grid), args.quantity, m1_by_bar, args.liquidate_at_end),
                min_neighbor_ratio=args.min_neighbor_ratio,
                min_positive_fraction=args.min_sensitivity_positive_fraction,
            )
        return {
            "walk_forward": wfo.as_dict(),
            "stress": [item.as_dict() for item in stress],
            "sensitivity": sensitivity.as_dict() if sensitivity else None,
            "robustness": assess_robustness(
                wfo,
                stress,
                min_wfe=args.min_wfe,
                min_profitable_oos_fraction=args.min_profitable_oos_fraction,
                min_oos_trades=args.min_oos_trades,
                require_positive_stress=not args.allow_negative_stress,
                sensitivity=sensitivity,
                require_sensitivity=args.require_sensitivity,
            ).as_dict(),
        }
    raise ValueError(f"unknown mode: {args.mode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Zvezdin strategy backtest")
    parser.add_argument("--input", help="CSV with OHLCV data")
    parser.add_argument("--sqlite", help="SQLite database containing candles")
    parser.add_argument("--ticker", help="ticker for --sqlite")
    parser.add_argument("--period", help="candle period for --sqlite")
    parser.add_argument("--output", help="JSON output path; stdout when omitted")
    parser.add_argument("--config", help="runtime contract JSON; default config is used otherwise")
    parser.add_argument("--calendar", help="JSON calendar with holidays and early closes")
    parser.add_argument(
        "--zone-signal-mode",
        choices=["STRICT", "TOUCH", "RELAXED_REJECTION", "NEAR"],
        help="experimental zone filter; STRICT is the canonical default",
    )
    parser.add_argument("--near-zone-atr-ratio", type=float, default=0.10)
    parser.add_argument("--relaxation-pct", type=float, help="experimental uniform threshold relaxation, percent")
    parser.add_argument("--signal-mode", choices=["AND", "SCORE"], help="experimental soft-score signal mode")
    parser.add_argument("--min-soft-score", type=int, default=5)
    parser.add_argument("--hold-on-breakout", action="store_true", help="experimental: do not force-close on zone breakout")
    parser.add_argument("--exhaustion-mode", choices=["WAVE_ATR", "CURRENT_ATR"], help="experimental exhaustion basis")
    parser.add_argument("--no-entry-volume", action="store_true", help="experimental: do not use volume as an entry filter")
    parser.add_argument("--manage-volume", action="store_true", help="experimental: manage open positions from post-entry volume shocks")
    parser.add_argument("--datetime-column", default="datetime")
    parser.add_argument("--m1-input", help="optional M1 CSV for intrabar execution")
    parser.add_argument("--m1-datetime-column", default="datetime")
    parser.add_argument("--m1-bar-minutes", type=int, default=1)
    parser.add_argument(
        "--parent-bar-minutes", type=int,
        help="parent interval duration when the parent CSV contains only one bar",
    )
    parser.add_argument("--mode", choices=["single", "wfo", "sensitivity", "stress", "report"], default="single")
    parser.add_argument("--quantity", type=float, default=1.0)
    parser.add_argument("--initial-capital", type=float, default=100_000.0)
    parser.add_argument(
        "--liquidate-at-end",
        action="store_true",
        help="close an open position at the final close for a realized result",
    )
    parser.add_argument("--train-bars", type=int, default=252)
    parser.add_argument("--test-bars", type=int, default=63)
    parser.add_argument("--step-bars", type=int)
    parser.add_argument("--warmup-bars", type=int, default=0)
    parser.add_argument("--grid", help="JSON object of parameter arrays for sensitivity mode")
    parser.add_argument("--multipliers", default="1,2,3", help="comma-separated cost multipliers")
    parser.add_argument("--min-wfe", type=float, default=0.60)
    parser.add_argument("--min-profitable-oos-fraction", type=float, default=0.50)
    parser.add_argument("--min-oos-trades", type=int, default=1)
    parser.add_argument("--allow-negative-stress", action="store_true")
    parser.add_argument("--require-sensitivity", action="store_true")
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="select grid parameters independently on each WFO IS window",
    )
    parser.add_argument("--min-neighbor-ratio", type=float, default=0.80)
    parser.add_argument("--min-sensitivity-positive-fraction", type=float, default=0.50)
    parser.add_argument(
        "--fail-on-quality-gate",
        action="store_true",
        help="return exit code 1 when --mode report fails robustness checks",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_cli(args)
        rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        if args.mode == "report" and args.fail_on_quality_gate and not result["robustness"]["passed"]:
            return 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
