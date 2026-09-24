#!/usr/bin/env python3
"""Analyze the price reaction to anomalous volume in a local trader DB.

Example:
    python trading_moex/scripts/analyze_volume_impact.py \
        --db trading_moex/data/trader.db --ticker T --period 15min
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TRADING_PACKAGE = ROOT / "trading_moex"
if str(TRADING_PACKAGE) not in sys.path:
    sys.path.insert(0, str(TRADING_PACKAGE))

from app.volume_analysis import (  # noqa: E402
    AnalysisConfig,
    analyze_events,
    event_statistics,
    load_candles,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze volume spikes and forward price reaction")
    parser.add_argument("--db", default=str(ROOT / "trading_moex" / "data" / "trader.db"))
    parser.add_argument("--ticker", default="T")
    parser.add_argument("--period", default="15min")
    parser.add_argument("--volume-multiplier", type=float, default=2.5)
    parser.add_argument("--zscore-threshold", type=float, default=2.5)
    parser.add_argument("--output", default=str(ROOT / "volume_analysis_report.md"))
    return parser


def _fmt(value: object, digits: int = 2, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{digits}f}{suffix}"


def _fmt_pct(value: object) -> str:
    return _fmt(value, 3, "%")


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _events_table(events: pd.DataFrame) -> str:
    lines = [
        "| Timestamp | Volume Ratio | Candle Type | Reaction (Next 1-4 bars) | Net Change % (15m / 30m / 60m) | Outcome Status | Body/Range | Upper wick | Lower wick | Range/ATR | MFE / MAE |",
        "|---|---:|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, event in events.iterrows():
        timestamp = pd.Timestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M")
        net = " / ".join(_fmt_pct(event[column]) for column in (
            "net_change_15m_pct", "net_change_30m_pct", "net_change_60m_pct"
        ))
        lines.append(
            "| " + " | ".join(
                _markdown_cell(value)
                for value in (
                    timestamp,
                    _fmt(event["volume_ratio"], 2, "x"),
                    event["candle_type"],
                    event["reaction"],
                    net,
                    event["outcome_status"],
                    _fmt(event["body_ratio"] * 100.0, 1, "%"),
                    _fmt(event["upper_shadow_ratio"] * 100.0, 1, "%"),
                    _fmt(event["lower_shadow_ratio"] * 100.0, 1, "%"),
                    _fmt(event["atr_spread"], 2, "x"),
                    f"{_fmt_pct(event['mfe_pct'])} / {_fmt_pct(event['mae_pct'])}",
                )
            ) + " |"
        )
    return "\n".join(lines)


def _statistics_markdown(stats: dict[str, object]) -> str:
    by_type = stats["by_type"]
    best_continuation = max(by_type, key=lambda item: (item["continuation_pct"], item["events"])) if by_type else None
    highest_reversal = max(by_type, key=lambda item: (item["reversal_pct"], item["events"])) if by_type else None
    strongest_60m = max(by_type, key=lambda item: (item["mean_60m_pct"], item["events"])) if by_type else None
    lines = [
        f"- Всего событий: **{stats['total_events']}**.",
        f"- С полным горизонтом 60 минут: **{stats['complete_events']}**; событий у конца выборки: **{stats['insufficient_events']}**.",
        f"- Продолжение с истинным пробоем: **{stats['continuation_pct']:.1f}%**.",
        f"- Флет/затухание без подтвержденного импульса: **{stats['flat_pct']:.1f}%**.",
        f"- Разворот, включая ложный пробой: **{stats['reversal_pct']:.1f}%**.",
        f"- Среднее изменение цены: 15m **{_fmt_pct(stats['mean_15m_pct'])}**, 30m **{_fmt_pct(stats['mean_30m_pct'])}**, 60m **{_fmt_pct(stats['mean_60m_pct'])}**.",
        f"- Наибольшая доля продолжения среди типов: **{best_continuation['candle_type']}** ({best_continuation['continuation_pct']:.1f}%, n={best_continuation['events']})." if best_continuation else "- Для сравнения типов недостаточно событий.",
        f"- Наибольшая доля разворотов среди типов: **{highest_reversal['candle_type']}** ({highest_reversal['reversal_pct']:.1f}%, n={highest_reversal['events']})." if highest_reversal else "",
        f"- Максимальное среднее необусловленное изменение за 60m: **{strongest_60m['candle_type']}** ({_fmt_pct(strongest_60m['mean_60m_pct'])}, n={strongest_60m['events']})." if strongest_60m else "",
        "",
        "| Candle Type | Events | Mean 15m | Mean 30m | Mean 60m | Continuation | Flat | Reversal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in stats["by_type"]:
        lines.append(
            f"| {_markdown_cell(item['candle_type'])} | {item['events']} | {_fmt_pct(item['mean_15m_pct'])} | "
            f"{_fmt_pct(item['mean_30m_pct'])} | {_fmt_pct(item['mean_60m_pct'])} | "
            f"{item['continuation_pct']:.1f}% | {item['flat_pct']:.1f}% | {item['reversal_pct']:.1f}% |"
        )
    return "\n".join(lines)


def render_report(
    events: pd.DataFrame,
    stats: dict[str, object],
    *,
    ticker: str,
    period: str,
    db_path: str,
    config: AnalysisConfig,
    row_count: int,
    first_timestamp: object,
    last_timestamp: object,
) -> str:
    """Render the complete Markdown report."""
    report = [
        f"# Volume Impact Analysis: `{ticker}` / `{period}`",
        "",
        "## Data and Methodology",
        f"- Source: read-only SQLite database `{db_path}`.",
        f"- Candles analyzed: **{row_count}**, from **{pd.Timestamp(first_timestamp)}** to **{pd.Timestamp(last_timestamp)}**.",
        f"- Volume spike: `volume >= SMA({config.volume_sma_window}) * {config.volume_multiplier:g}` **OR** `volume Z-score({config.zscore_window}) > {config.zscore_threshold:g}`.",
        f"- ATR: prior `{config.atr_period}` true ranges; forward horizon: next `{config.horizon}` candles (15-60 minutes).",
        "- Rolling baselines exclude the signal candle to avoid look-ahead contamination.",
        "- Impulse requires a break of the signal high/low and movement greater than 1 ATR from the signal close.",
        "- Reversal requires a close across the signal open, covering the signal body. If an impulse is later reversed, it is a false breakout and belongs to the reversal group.",
        "- MFE/MAE are measured from the signal close over the available forward bars; MAE is reported as a positive adverse percentage.",
        "- Mean 15m/30m/60m changes are raw close-to-close percentages, not direction-normalized returns; small candle-type samples should not be overinterpreted.",
        "- Adjacent signal candles are retained as separate events; no de-clustering or trade-level de-duplication is applied.",
        "",
        "## Statistical Summary",
        _statistics_markdown(stats),
        "",
        "## Interpretation",
        "- Directional volume is most useful when the candle has a large body, a high range/ATR ratio, and the first subsequent bars break the signal extreme without closing back through its body.",
        "- Long upper shadows indicate supply/rejection risk; long lower shadows indicate demand/rejection risk. A high volume ratio alone is not treated as directional evidence.",
        "- A false breakout is separated from a clean continuation because the initial excursion beyond the range is subsequently rejected within the four-bar observation window.",
        "",
        "## Detected Events",
        _events_table(events),
        "",
    ]
    return "\n".join(report)


def print_top_events(events: pd.DataFrame, limit: int = 10) -> None:
    print(f"Top {min(limit, len(events))} volume events by Volume Ratio")
    if events.empty:
        print("No events found.")
        return
    top = events.sort_values(["volume_ratio", "volume_zscore"], ascending=False).head(limit)
    for rank, (_, event) in enumerate(top.iterrows(), start=1):
        timestamp = pd.Timestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(
            f"{rank:2}. {timestamp} | ratio={_fmt(event['volume_ratio'], 2, 'x')} "
            f"z={_fmt(event['volume_zscore'], 2)} | {event['candle_type']} | "
            f"{event['reaction']} | 60m={_fmt_pct(event['net_change_60m_pct'])} | {event['outcome_status']}"
        )


def main() -> int:
    args = build_parser().parse_args()
    if args.volume_multiplier <= 0 or args.zscore_threshold <= 0:
        raise SystemExit("volume thresholds must be positive")
    config = AnalysisConfig(
        volume_multiplier=args.volume_multiplier,
        zscore_threshold=args.zscore_threshold,
    )
    frame = load_candles(args.db, args.ticker, args.period)
    events = analyze_events(frame, config)
    stats = event_statistics(events)
    report = render_report(
        events,
        stats,
        ticker=args.ticker.upper(),
        period=args.period,
        db_path=str(Path(args.db).expanduser().resolve()),
        config=config,
        row_count=len(frame),
        first_timestamp=frame["timestamp"].iloc[0],
        last_timestamp=frame["timestamp"].iloc[-1],
    )
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Analyzed {len(frame)} candles and found {len(events)} volume events.")
    print(f"Report written to {output}")
    print_top_events(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
