#!/usr/bin/env python3
"""Test whether anomalous volume behaves differently near Fibonacci levels."""

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

from app.volume_analysis import (  # noqa: E402
    AnalysisConfig,
    add_fibonacci_features,
    analyze_events,
    event_statistics,
    load_candles,
    prepare_candles,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Measure the relationship between volume spikes and Fib levels")
    result.add_argument("--db", default=str(ROOT / "trading_moex" / "data" / "trader.db"))
    result.add_argument("--ticker", default="T")
    result.add_argument("--period", default="15min")
    result.add_argument("--swing-bars", type=int, default=10)
    result.add_argument("--proximity", type=float, default=0.05, help="Fib fraction tolerance, default 0.05")
    result.add_argument("--volume-multiplier", type=float, default=2.5)
    result.add_argument("--zscore-threshold", type=float, default=2.5)
    result.add_argument("--output", default=str(ROOT / "fib_volume_relationship_report.md"))
    return result


def _pct(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}%"


def _level(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100.0 if denominator else np.nan


def _group_table(all_bars: pd.DataFrame, events: pd.DataFrame) -> list[dict[str, object]]:
    contexts = ["Golden zone 50-61.8%", "Near Fib level", "Valid swing, away from level", "No confirmed swing"]
    rows: list[dict[str, object]] = []
    for context in contexts:
        bars = all_bars[all_bars["fib_context"].eq(context)]
        group = events[events["fib_context"].eq(context)]
        complete = group[group["outcome_group"] != "insufficient"]
        rows.append(
            {
                "context": context,
                "bars": len(bars),
                "events": len(group),
                "event_rate": _rate(len(group), len(bars)),
                "mean_ratio": group["volume_ratio"].mean() if len(group) else np.nan,
                "continuation": _rate(int(complete["outcome_group"].eq("continuation").sum()), len(complete)),
                "flat": _rate(int(complete["outcome_group"].eq("flat").sum()), len(complete)),
                "reversal": _rate(int(complete["outcome_group"].eq("reversal").sum()), len(complete)),
                "mean_60m": complete["net_change_60m_pct"].mean() if len(complete) else np.nan,
            }
        )
    return rows


def _level_table(all_bars: pd.DataFrame, events: pd.DataFrame, proximity: float) -> list[dict[str, object]]:
    """Return disjoint nearest-level statistics for the four tested ratios."""
    rows: list[dict[str, object]] = []
    for level in (0.382, 0.500, 0.618, 0.786):
        bars = all_bars[
            all_bars["fib_nearest_level"].eq(level)
            & all_bars["fib_distance"].le(proximity)
        ]
        group = events[
            events["fib_nearest_level"].eq(level)
            & events["fib_distance"].le(proximity)
        ]
        complete = group[group["outcome_group"] != "insufficient"]
        rows.append(
            {
                "level": level,
                "bars": len(bars),
                "events": len(group),
                "event_rate": _rate(len(group), len(bars)),
                "continuation": _rate(int(complete["outcome_group"].eq("continuation").sum()), len(complete)),
                "flat": _rate(int(complete["outcome_group"].eq("flat").sum()), len(complete)),
                "reversal": _rate(int(complete["outcome_group"].eq("reversal").sum()), len(complete)),
                "mean_60m": complete["net_change_60m_pct"].mean() if len(complete) else np.nan,
            }
        )
    return rows


def _bootstrap_diff(first: np.ndarray, second: np.ndarray, seed: int = 20260925) -> tuple[float, float, float]:
    """Difference in means with a lightweight reproducible percentile bootstrap."""
    if len(first) == 0 or len(second) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = 4000
    left = rng.choice(first, (samples, len(first)), replace=True).mean(axis=1)
    right = rng.choice(second, (samples, len(second)), replace=True).mean(axis=1)
    difference = float(first.mean() - second.mean())
    low, high = np.percentile(left - right, [2.5, 97.5])
    return difference, float(low), float(high)


def render_report(
    *,
    frame: pd.DataFrame,
    events: pd.DataFrame,
    groups: list[dict[str, object]],
    levels: list[dict[str, object]],
    volume_stats: dict[str, object],
    args: argparse.Namespace,
) -> str:
    valid = frame[frame["fib_valid"]]
    golden = frame[frame["fib_context"].eq("Golden zone 50-61.8%")]
    away = frame[frame["fib_context"].eq("Valid swing, away from level")]
    golden_spikes = golden[golden["is_volume_spike"]]
    away_spikes = away[away["is_volume_spike"]]
    rate_diff, rate_low, rate_high = _bootstrap_diff(
        golden["is_volume_spike"].astype(float).to_numpy(),
        away["is_volume_spike"].astype(float).to_numpy(),
    )
    event_golden = events[events["fib_context"].eq("Golden zone 50-61.8%")]
    event_away = events[events["fib_context"].eq("Valid swing, away from level")]
    complete_golden = event_golden[event_golden["outcome_group"] != "insufficient"]
    complete_away = event_away[event_away["outcome_group"] != "insufficient"]
    continuation_diff, continuation_low, continuation_high = _bootstrap_diff(
        complete_golden["outcome_group"].eq("continuation").astype(float).to_numpy(),
        complete_away["outcome_group"].eq("continuation").astype(float).to_numpy(),
    )

    lines = [
        f"# Fibonacci / Volume Relationship: `{args.ticker.upper()}` / `{args.period}`",
        "",
        "## Method",
        f"- Data: {len(frame)} candles, `{pd.Timestamp(frame['timestamp'].iloc[0])}` to `{pd.Timestamp(frame['timestamp'].iloc[-1])}`.",
        f"- Fib anchors: causally confirmed fractal pivots with `swing_bars={args.swing_bars}`; this matches the bot's `fib_pullback` methodology.",
        "- Tested levels: 38.2%, 50.0%, 61.8%, 78.6% of the latest confirmed swing range.",
        f"- A level is considered near when the retracement fraction is within +/- {args.proximity:.3f} ({args.proximity * 100:.1f} percentage points).",
        f"- Volume event: SMA(20) ratio >= {args.volume_multiplier:g} OR Z-score(50) > {args.zscore_threshold:g}.",
        "- The golden zone is 50.0-61.8%, the same entry zone used by the bot. Adjacent events are not de-clustered.",
        "",
        "## Result",
        f"- Volume events: **{volume_stats['total_events']}**; complete forward outcomes: **{volume_stats['complete_events']}**.",
        f"- Valid confirmed Fib swing context: **{len(valid)}** bars ({len(valid) / len(frame) * 100:.1f}%).",
        f"- Golden-zone volume-event rate: **{_pct(_rate(len(golden_spikes), len(golden)))}** ({len(golden_spikes)}/{len(golden)}).",
        f"- Valid-swing-away event rate: **{_pct(_rate(len(away_spikes), len(away)))}** ({len(away_spikes)}/{len(away)}).",
        f"- Golden-zone minus away event-rate difference: **{_pct(rate_diff * 100)}**, bootstrap 95% CI [{_pct(rate_low * 100)}, {_pct(rate_high * 100)}].",
        f"- Golden-zone continuation rate: **{_pct(_rate(int(complete_golden['outcome_group'].eq('continuation').sum()), len(complete_golden)))}**; away: **{_pct(_rate(int(complete_away['outcome_group'].eq('continuation').sum()), len(complete_away)))}**.",
        f"- Continuation-rate difference: **{_pct(continuation_diff * 100)}**, bootstrap 95% CI [{_pct(continuation_low * 100)}, {_pct(continuation_high * 100)}].",
        "",
        "## Breakdown",
        "| Fib context | All bars | Volume events | Event rate | Mean ratio | Continuation | Flat | Reversal | Mean 60m close change |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in groups:
        lines.append(
            f"| {row['context']} | {row['bars']} | {row['events']} | {_pct(row['event_rate'])} | {row['mean_ratio']:.2f}x | "
            f"{_pct(row['continuation'])} | {_pct(row['flat'])} | {_pct(row['reversal'])} | {_pct(row['mean_60m'])} |"
        )

    lines.extend(
        [
            "",
            "### Individual Levels",
            "| Nearest Fib level | All bars near level | Volume events | Event rate | Continuation | Flat | Reversal | Mean 60m close change |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in levels:
        lines.append(
            f"| {row['level'] * 100:.1f}% | {row['bars']} | {row['events']} | {_pct(row['event_rate'])} | "
            f"{_pct(row['continuation'])} | {_pct(row['flat'])} | {_pct(row['reversal'])} | {_pct(row['mean_60m'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- A relationship is plausible only if both event frequency and forward reaction differ from the away-from-level control; a high raw count near Fib is not evidence by itself.",
            "- Individual-level rows are disjoint: each bar is assigned to its nearest Fib ratio, only when it is within the selected tolerance.",
            "- The bootstrap interval is descriptive, not a multiple-testing-adjusted significance test. It does not remove intraday seasonality, news effects, or overlapping events.",
            "- Small samples, especially for a single level, should not be used as a standalone trading rule.",
            "",
            "## Volume Events With Fib Context",
            "| Timestamp | Fib context | Nearest level | Retracement | Volume ratio | Reaction | 60m change | Outcome |",
            "|---|---|---:|---:|---:|---|---:|---|",
        ]
    )
    event_context = events.sort_values("volume_ratio", ascending=False)
    for _, event in event_context.iterrows():
        timestamp = pd.Timestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"| {timestamp} | {event['fib_context']} | {_level(event['fib_nearest_level'])} | {_level(event['fib_retracement'])} | "
            f"{event['volume_ratio']:.2f}x | {event['reaction']} | {_pct(event['net_change_60m_pct'], 3)} | {event['outcome_status']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parser().parse_args()
    config = AnalysisConfig(
        volume_multiplier=args.volume_multiplier,
        zscore_threshold=args.zscore_threshold,
    )
    raw = load_candles(args.db, args.ticker, args.period)
    prepared = prepare_candles(raw, config)
    prepared = add_fibonacci_features(prepared, swing_bars=args.swing_bars, proximity=args.proximity)
    events = analyze_events(raw, config)
    event_features = prepared[prepared["is_volume_spike"]][
        ["timestamp", "fib_context", "fib_nearest_level", "fib_distance", "fib_retracement"]
    ]
    events = events.merge(event_features, on="timestamp", how="left")
    groups = _group_table(prepared, events)
    levels = _level_table(prepared, events, args.proximity)
    report = render_report(
        frame=prepared,
        events=events,
        groups=groups,
        levels=levels,
        volume_stats=event_statistics(events),
        args=args,
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report.split("## Result", 1)[1].split("## Breakdown", 1)[0].strip())
    print(f"Report written to {output}")
    print("Top 10 events by volume ratio and Fib context:")
    for rank, (_, event) in enumerate(events.sort_values("volume_ratio", ascending=False).head(10).iterrows(), start=1):
        print(
            f"{rank:2}. {pd.Timestamp(event['timestamp']):%Y-%m-%d %H:%M} | "
            f"{event['volume_ratio']:.2f}x | {event['fib_context']} | "
            f"level={_level(event['fib_nearest_level'])} | {event['reaction']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
