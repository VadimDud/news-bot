#!/usr/bin/env python3
"""Walk-forward candidate matrix for the long-only T VSA strategy.

The script evaluates feature modes M0..M3 and MARKET/LIMIT/STOP_LIMIT
independently. It never selects a candidate using the OOS segment.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "trading_moex"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from app.vsa_strategy import (  # noqa: E402
    EntryOrderType,
    FeatureMode,
    StrategyConfig,
    run_backtest,
    context_diagnostics,
)
from app.volume_analysis import load_candles  # noqa: E402


MODES: tuple[FeatureMode, ...] = ("M0", "M1", "M2", "M3")
ORDER_TYPES: tuple[EntryOrderType, ...] = ("MARKET", "LIMIT", "STOP_LIMIT")


def _split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(frame)
    train_end = max(1, int(n * 0.60))
    validation_end = max(train_end + 1, int(n * 0.80))
    return frame.iloc[:train_end], frame.iloc[train_end:validation_end], frame.iloc[validation_end:]


def _row(mode: str, order_type: str, segment: str, result) -> dict[str, object]:
    row: dict[str, object] = {"mode": mode, "order_type": order_type, "segment": segment}
    row.update(result.metrics)
    return row


def _candidate_score(row: dict[str, object]) -> tuple[float, float, float] | None:
    trades = float(row["trades"])
    pf = float(row["profit_factor"])
    drawdown = float(row["max_drawdown_pct"]) / 100.0
    net = float(row["net_pnl"])
    if trades < 50 or not np.isfinite(pf) or pf < 1.05 or drawdown > 0.015 or net <= 0:
        return None
    return (net / max(drawdown, 1e-12), pf, -float(row.get("turnover", 0.0)))


def _fmt(value: object) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_report(
    frame: pd.DataFrame,
    rows: list[dict[str, object]],
    selected: tuple[str, str] | None,
    *,
    db: str,
    ticker: str,
    period: str,
) -> str:
    lines = [
        f"# VSA Strategy Walk-Forward: `{ticker}` / `{period}`",
        "",
        "## Contract",
        f"- Source: read-only SQLite `{Path(db).expanduser().resolve()}`.",
        f"- Candles: **{len(frame)}**, `{frame['timestamp'].iloc[0]}` to `{frame['timestamp'].iloc[-1]}`.",
        "- Direction: long only; initial equity 1,000,000 RUB; leverage 1.0; risk 0.15% per trade.",
        "- 4-hour context uses only completed 4-hour bars from the last 90 calendar days and EMA(20/50/200).",
        "- Candidate matrix: M0/M1/M2/M3 x MARKET/LIMIT/STOP_LIMIT.",
        "- Splits: chronological 60% train, 20% validation, 20% untouched OOS.",
        "",
        "## Results",
        "| Mode | Order | Segment | Trades | PF | Net PnL | Return % | Max DD % | Sharpe |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['mode']} | {row['order_type']} | {row['segment']} | "
            f"{_fmt(row['trades'])} | {_fmt(row['profit_factor'])} | {_fmt(row['net_pnl'])} | "
            f"{_fmt(row['return_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['sharpe'])} |"
        )
    lines.extend([
        "",
        "## Selection",
        f"- Selected candidate: **{selected[0]} / {selected[1]}**." if selected else "- Selected candidate: **NONE**.",
        "- A candidate is eligible only with validation trades >= 50, PF >= 1.05, validation max DD <= 1.5%, and positive validation PnL.",
        "- OOS performance is reported only after selection; it is never used for selection.",
        "- `DEPLOYMENT_NOT_APPROVED` if no candidate is selected or if OOS gates in the strategy specification fail.",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backtest the long-only T VSA strategy")
    parser.add_argument("--db", default=str(ROOT / "trading_moex" / "data" / "trader.db"))
    parser.add_argument("--ticker", default="T")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--output", default=str(ROOT / "vsa_strategy_walkforward.md"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = load_candles(args.db, args.ticker, args.period)
    diagnostics = context_diagnostics(frame, StrategyConfig())
    train, validation, out_of_sample = _split(frame)
    rows: list[dict[str, object]] = []
    validation_results: dict[tuple[str, str], object] = {}
    for mode, order_type in itertools.product(MODES, ORDER_TYPES):
        config = StrategyConfig()
        train_result = run_backtest(train, config, feature_mode=mode, order_type=order_type)
        validation_result = run_backtest(validation, config, feature_mode=mode, order_type=order_type)
        validation_results[(mode, order_type)] = validation_result
        rows.append(_row(mode, order_type, "train", train_result))
        rows.append(_row(mode, order_type, "validation", validation_result))
    eligible = []
    for key, result in validation_results.items():
        validation_row = _row(key[0], key[1], "validation", result)
        score = _candidate_score(validation_row)
        if score is not None:
            eligible.append((score, key))
    selected = max(eligible, reverse=True)[1] if eligible else None
    if selected:
        oos = run_backtest(out_of_sample, StrategyConfig(), feature_mode=selected[0], order_type=selected[1])
        rows.append(_row(selected[0], selected[1], "OOS", oos))
    report = render_report(frame, rows, selected, db=args.db, ticker=args.ticker, period=args.period)
    report += (
        f"## Data Sufficiency\n- Observed 4h periods in lookback: **{diagnostics['observed_4h_periods']}**.\n"
        f"- Required completed 4h periods: **{diagnostics['required_4h_periods']}**.\n"
        f"- Lookback: **{diagnostics['lookback_days']} calendar days**.\n"
        f"- Status: **{'INSUFFICIENT_4H_WARMUP' if diagnostics['insufficient_warmup'] else 'READY'}**.\n"
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.rstrip() + "\n", encoding="utf-8")
    print(f"Analyzed {len(frame)} candles; candidates={len(MODES) * len(ORDER_TYPES)}; selected={selected or 'NONE'}")
    print(f"Report written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
