#!/usr/bin/env python3
"""VSA anomaly and Fibonacci time-cycle statistics for a local SQLite DB.

Example:
    python trading_moex/scripts/vsa_fibonacci_stats.py \
        --db /tmp/trader.db --ticker T --period 15min
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TRADING_PACKAGE = ROOT / "trading_moex"
if str(TRADING_PACKAGE) not in sys.path:
    sys.path.insert(0, str(TRADING_PACKAGE))

from app.vsa_fibonacci import (  # noqa: E402
    ANOMALY_TYPES,
    FIB_COUNTS,
    VSAConfig,
    analyze_fibonacci_cycles,
    analyze_vsa_events,
    cycle_matrix,
    depth_summary,
    load_candles,
    prepare_vsa,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VSA and Fibonacci cycle statistics")
    parser.add_argument("--db", default=str(ROOT / "trading_moex" / "data" / "trader.db"))
    parser.add_argument("--ticker", default="T")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--volume-multiplier", type=float, default=2.5)
    parser.add_argument("--volume-window", type=int, default=20)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--output", default=str(ROOT / "vsa_fibo_report.md"))
    return parser


def fmt_pct(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}%"


def fmt_num(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _event_summary(events: pd.DataFrame, anomaly_type: str, horizon: int = 8) -> dict[str, object]:
    group = events[events["anomaly_type"].eq(anomaly_type)]
    complete = group[group[f"win_{horizon}"].notna()]
    return {
        "type": anomaly_type,
        "count": len(group),
        "reversal": complete[f"reversal_{horizon}"].mean() * 100.0 if len(complete) else np.nan,
        "continuation": complete[f"win_{horizon}"].mean() * 100.0 if len(complete) else np.nan,
        "flat": group["flat_4"].mean() * 100.0 if len(group) else np.nan,
        "mfe_pct": complete[f"mfe_pct_{horizon}"].mean() if len(complete) else np.nan,
        "mfe_atr": complete[f"mfe_atr_{horizon}"].mean() if len(complete) else np.nan,
        "mae_pct": complete[f"mae_pct_{horizon}"].mean() if len(complete) else np.nan,
        "mean_return": complete.apply(
            lambda row: row[f"mfe_pct_{horizon}"] - row[f"mae_pct_{horizon}"], axis=1
        ).mean() if len(complete) else np.nan,
        "complete": len(complete),
    }


def _reaction_horizon_table(events: pd.DataFrame) -> str:
    lines = [
        "| Anomaly | Horizon | Events | Directional win | Reversal | Mean MFE % | Mean MFE ATR | Mean MAE % | Flat (4 bars) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for anomaly in ANOMALY_TYPES:
        group = events[events["anomaly_type"].eq(anomaly)]
        for horizon in (1, 3, 5, 8):
            complete = group[group[f"win_{horizon}"].notna()]
            lines.append(
                f"| {anomaly} | {horizon} | {len(complete)} | "
                f"{fmt_pct(complete[f'win_{horizon}'].mean() * 100 if len(complete) else np.nan)} | "
                f"{fmt_pct(complete[f'reversal_{horizon}'].mean() * 100 if len(complete) else np.nan)} | "
                f"{fmt_pct(complete[f'mfe_pct_{horizon}'].mean() if len(complete) else np.nan)} | "
                f"{fmt_num(complete[f'mfe_atr_{horizon}'].mean() if len(complete) else np.nan)} ATR | "
                f"{fmt_pct(complete[f'mae_pct_{horizon}'].mean() if len(complete) else np.nan)} | "
                f"{fmt_pct(group['flat_4'].mean() * 100 if len(group) else np.nan)} |"
            )
    return "\n".join(lines)


def _cycle_matrix_table(matrix: pd.DataFrame) -> str:
    lines = [
        "| Impulse \\ Correction | " + " | ".join(str(value) for value in FIB_COUNTS) + " |",
        "|---|" + "---:|" * len(FIB_COUNTS),
    ]
    for _, row in matrix.iterrows():
        lines.append(
            "| " + str(int(row["impulse"])) + " | " + " | ".join(
                fmt_pct(row[value]) for value in FIB_COUNTS
            ) + " |"
        )
    return "\n".join(lines)


def _depth_table(summary: pd.DataFrame) -> str:
    lines = [
        "| Correction depth | Events | Continuation | Mean depth | Interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    interpretation = {
        "<=38.2%": "Shallow correction",
        "38.2-50%": "Moderate correction",
        "50-61.8%": "Golden-zone correction",
        ">61.8%": "Deep correction / invalidation risk",
    }
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['depth']} | {int(row['events'])} | {fmt_pct(row['continuation_pct'])} | "
            f"{fmt_pct(row['mean_depth'] * 100)} | {interpretation.get(row['depth'], '')} |"
        )
    return "\n".join(lines)


def _top_events(events: pd.DataFrame, limit: int = 10) -> None:
    print(f"Top {min(limit, len(events))} VSA events by volume ratio")
    for rank, (_, event) in enumerate(events.sort_values("volume_ratio", ascending=False).head(limit).iterrows(), start=1):
        timestamp = pd.Timestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(
            f"{rank:2}. {timestamp} | {event['anomaly_type']} | "
            f"ratio={event['volume_ratio']:.2f}x | "
            f"win8={fmt_pct(event['win_8'] * 100 if pd.notna(event['win_8']) else np.nan)} | "
            f"MFE8={fmt_pct(event['mfe_pct_8'])} | MAE8={fmt_pct(event['mae_pct_8'])}"
        )


def render_report(
    frame: pd.DataFrame,
    events: pd.DataFrame,
    cycles: pd.DataFrame,
    *,
    args: argparse.Namespace,
    config: VSAConfig,
) -> str:
    summaries = [_event_summary(events, anomaly) for anomaly in ANOMALY_TYPES]
    matrix = cycle_matrix(cycles)
    depths = depth_summary(cycles)
    lines = [
        f"# VSA and Fibonacci Cycle Statistics: `{args.ticker.upper()}` / `{args.period}`",
        "",
        "## Data and Methodology",
        f"- Source: read-only SQLite database `{Path(args.db).expanduser().resolve()}`.",
        f"- History: **{len(frame)}** candles, `{pd.Timestamp(frame['timestamp'].iloc[0])}` to `{pd.Timestamp(frame['timestamp'].iloc[-1])}`.",
        f"- Anomalous volume: `Volume >= {config.volume_multiplier:g} * SMA_Volume({config.volume_window})`; SMA excludes the signal candle.",
        f"- ATR({config.atr_period}) uses prior true ranges and excludes the signal candle from its mean.",
        "- VSA categories use the exact thresholds from the research brief. Overlapping categories are assigned exclusively with momentum taking priority over rejection, and rejection over absorption; the final table has one row per event.",
        "- Forward direction is measured from signal close in the direction of its close relative to open. Doji anomalies have no directional win/reversal classification.",
        "- MFE uses the best high/low excursion in the favorable direction; MAE is the maximum adverse excursion, reported positive. Flat means all next four highs/lows remain inside the signal range.",
        "- Cycle observations use consecutive close-to-close directional runs. The initial impulse and next opposite run must have exact lengths in `{1, 2, 3, 5, 8, 13}`; continuation means a close breaks the impulse endpoint in the original direction within 13 bars after correction and before the impulse start is invalidated.",
        "",
        "## 1. VSA Comparison (8-bar horizon)",
        "| Type of anomaly | Events | Reversal (%) | Continuation (%) | Flat (%) | Mean MFE (% / ATR) | Mean MAE (%) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary['type']} | {summary['count']} | {fmt_pct(summary['reversal'])} | "
            f"{fmt_pct(summary['continuation'])} | {fmt_pct(summary['flat'])} | "
            f"{fmt_pct(summary['mfe_pct'])} / {fmt_num(summary['mfe_atr'])} ATR | {fmt_pct(summary['mae_pct'])} |"
        )
    lines.extend(
        [
            "",
            "### Reaction by Horizon",
            _reaction_horizon_table(events),
            "",
            "## 2. Fibonacci Time-Cycle Matrix",
            f"Cycle observations with exact Fib counts: **{len(cycles)}**; VSA-anchored observations: **{int(cycles['anchor_is_vsa'].sum()) if not cycles.empty else 0}**.",
            "Probability in each cell is the percentage of observations where the original direction later breaks the impulse endpoint.",
            _cycle_matrix_table(matrix),
            "",
            "### Correction Depth",
            _depth_table(depths),
            "",
            "## 3. Practical Conclusions",
        ]
    )
    if summaries:
        best = max(summaries, key=lambda item: (item["mean_return"] if pd.notna(item["mean_return"]) else -np.inf))
        lines.append(
            f"- Highest simple MFE-minus-MAE expectancy proxy at 8 bars: **{best['type']}** "
            f"({fmt_pct(best['mean_return'])}); this is descriptive and excludes fees, slippage and position sizing."
        )
    if not depths.empty:
        best_depth = depths.loc[depths["continuation_pct"].idxmax()]
        lines.append(
            f"- Best observed correction-depth bucket: **{best_depth['depth']}** with "
            f"{fmt_pct(best_depth['continuation_pct'])} continuation ({int(best_depth['events'])} observations)."
        )
    if not cycles.empty:
        eligible = cycles[cycles["impulse_length"].isin(FIB_COUNTS) & cycles["correction_length"].isin(FIB_COUNTS)].copy()
        if len(eligible):
            eligible["ratio"] = eligible["impulse_length"] / eligible["correction_length"]
            ratio = eligible.groupby("ratio")["resumed"].agg(["mean", "size"]).sort_values("mean", ascending=False).iloc[0]
            lines.append(
                f"- Highest observed impulse/correction ratio bucket: **{ratio.name:.2f}** with "
                f"{ratio['mean'] * 100:.1f}% continuation (n={int(ratio['size'])}); do not treat a small cell as a stable edge."
            )
    lines.extend(
        [
            "- The bot should treat VSA category and cycle count as filters or context, not standalone entries. The cycle matrix is vulnerable to overlapping events and multiple testing.",
            "- A production rule should be validated with walk-forward splits, costs, non-overlapping trades, and a minimum sample size per cell before deployment.",
            "",
            "## Top VSA Events",
            "| Timestamp | Anomaly | Volume ratio | Direction | Range/ATR | Body/range | Win 8 | MFE 8 | MAE 8 |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for _, event in events.sort_values("volume_ratio", ascending=False).head(25).iterrows():
        lines.append(
            f"| {pd.Timestamp(event['timestamp']):%Y-%m-%d %H:%M} | {fmt_cell(event['anomaly_type'])} | "
            f"{event['volume_ratio']:.2f}x | {event['direction']} | {fmt_num(event['range_atr'])}x | "
            f"{fmt_pct(event['body_ratio'] * 100)} | {fmt_pct(event['win_8'] * 100 if pd.notna(event['win_8']) else np.nan)} | "
            f"{fmt_pct(event['mfe_pct_8'])} | {fmt_pct(event['mae_pct_8'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = build_parser().parse_args()
    if args.volume_multiplier <= 0 or args.volume_window <= 0 or args.atr_period <= 0:
        raise SystemExit("volume multiplier, volume window and ATR period must be positive")
    config = VSAConfig(
        volume_multiplier=args.volume_multiplier,
        volume_window=args.volume_window,
        atr_period=args.atr_period,
    )
    frame = load_candles(args.db, args.ticker, args.period)
    prepared = prepare_vsa(frame, config)
    events = analyze_vsa_events(frame, config)
    event_indices = set(prepared.index[prepared["is_vsa_event"]].tolist())
    cycles = analyze_fibonacci_cycles(frame, config, event_indices=event_indices)
    report = render_report(frame, events, cycles, args=args, config=config)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Analyzed {len(frame)} candles; VSA events={len(events)}; cycle observations={len(cycles)}")
    print(f"Report written to {output}")
    _top_events(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
