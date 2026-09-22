#!/usr/bin/env python3
"""Build component statistics for the Zvezdin reversal hypothesis.

The diagnostic pass deliberately clears temporary orders/positions after each
bar. This makes every closed bar observable instead of hiding components behind
the one-position execution state. It does not change the trading engine.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "trading_moex") not in sys.path:
    sys.path.insert(0, str(ROOT / "trading_moex"))

from app.zvezdin_backtest import bars_from_dataframe  # noqa: E402
from app.zvezdin_contract import load_default_config  # noqa: E402
from app.zvezdin_engine import Side, StrategyConfig, StrategyEngine  # noqa: E402


COMPONENTS = (
    "acceleration",
    "atr_completion",
    "strong_level",
    "volume_participant",
    "reverse_impulse",
)


def load_sqlite_candles(
    path: str,
    ticker: str,
    period: str,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query(
            "SELECT begin AS datetime, open, high, low, close, volume "
            "FROM candles WHERE ticker=? AND period=? "
            "AND begin >= ? AND begin < ? ORDER BY begin",
            connection,
            params=(
                ticker,
                period,
                (start or date.min).isoformat(),
                (end or date.max).isoformat(),
            ),
        )
    if frame.empty:
        raise ValueError(f"no candles found for ticker={ticker!r}, period={period!r}")
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True, errors="raise")
    return frame.set_index("datetime")


def _direction_flags(audit, side: Side) -> dict[str, bool]:
    short = side is Side.SHORT
    return {
        "acceleration": bool(audit.acceleration),
        "atr_completion": bool(audit.exhaustion_short if short else audit.exhaustion_long),
        "strong_level": bool(audit.short_zone_id if short else audit.long_zone_id),
        "volume_participant": bool(audit.volume_spike),
        "reverse_impulse": bool(audit.candle_shape_short if short else audit.candle_shape_long),
    }


def _future_classification(
    closes: list[float],
    index: int,
    atr: float | None,
    horizon: int,
    threshold_atr: float,
) -> tuple[str | None, float | None, float | None, float | None]:
    future_index = index + horizon
    if future_index >= len(closes) or atr is None or atr <= 0:
        return None, None, None, None
    change = closes[future_index] - closes[index]
    threshold = threshold_atr * atr
    if change > threshold:
        direction = "LONG"
    elif change < -threshold:
        direction = "SHORT"
    else:
        direction = "FLAT"
    window = closes[index + 1:future_index + 1]
    return direction, change / closes[index], max(window) - closes[index], min(window) - closes[index]


def _signal_result(direction: str | None, side: Side) -> str | None:
    if direction is None:
        return None
    if direction == "FLAT":
        return "FLAT"
    expected = "LONG" if side is Side.LONG else "SHORT"
    return "WIN" if direction == expected else "LOSS"


def collect_component_events(
    frame: pd.DataFrame,
    config: StrategyConfig,
    horizon_bars: tuple[int, ...] = (8, 32, 96),
    threshold_atr: float = 0.25,
) -> tuple[list[dict], dict]:
    bars = bars_from_dataframe(
        frame,
        session_start_minute=config.session_start_minute,
        session_end_minute=config.session_end_minute,
        slot_minutes=config.slot_minutes,
        calendar=config.calendar,
    )
    closes = [bar.close for bar in bars]
    engine = StrategyEngine(config=config)
    records: list[dict] = []
    for bar in bars:
        engine.on_bar(bar, emit_signals=True)
        audit = engine.audit[-1] if engine.audit else None
        if audit is None:
            continue
        for side in (Side.LONG, Side.SHORT):
            flags = _direction_flags(audit, side)
            # Acceleration and volume are context-neutral. Do not create two
            # fake LONG/SHORT rows when neither directional anchor is present.
            if not (flags["strong_level"] or flags["reverse_impulse"]):
                continue
            record = {
                "bar": bar.index,
                "datetime": frame.index[bar.index].isoformat(),
                "side": side.value,
                "candidate": flags["strong_level"] and flags["reverse_impulse"],
                **flags,
                "components_count": sum(flags.values()),
                "component_set": "+".join(name for name in COMPONENTS if flags[name]),
                "atr_previous": audit.atr_previous,
                "close": bar.close,
                "volume": bar.volume,
            }
            for horizon in horizon_bars:
                direction, change, mfe, mae = _future_classification(
                    closes, bar.index, audit.atr_previous, horizon, threshold_atr,
                )
                prefix = f"fwd_{horizon}"
                record[f"{prefix}_direction"] = direction
                record[f"{prefix}_result"] = _signal_result(direction, side)
                record[f"{prefix}_return"] = change
                record[f"{prefix}_mfe"] = mfe
                record[f"{prefix}_mae"] = mae
            records.append(record)
        # Diagnostic mode must not suppress the next bar's component scan.
        engine.position = None
        engine.pending = None
        engine.emergency_zone_id = None

    summary = summarize_component_events(records, horizon_bars)
    return records, summary


def summarize_component_events(records: list[dict], horizon_bars: tuple[int, ...]) -> dict:
    summary = {
        "events": len(records),
        "candidate_events": sum(record["candidate"] for record in records),
        "component_counts": {},
        "component_rates": {},
        "component_outcomes": {},
        "candidate_outcomes": {},
        "side_counts": dict(Counter(record["side"] for record in records)),
        "combination_counts": dict(Counter(record["component_set"] for record in records)),
        "outcomes": {},
    }
    for component in COMPONENTS:
        selected = [record for record in records if record[component]]
        summary["component_counts"][component] = len(selected)
        summary["component_rates"][component] = len(selected) / len(records) if records else 0.0
        summary["component_outcomes"][component] = {}
        for horizon in horizon_bars:
            key = f"fwd_{horizon}_direction"
            result_key = f"fwd_{horizon}_result"
            summary["component_outcomes"][component][str(horizon)] = {
                "direction": dict(Counter(record[key] for record in selected if record[key] is not None)),
                "result": dict(Counter(record[result_key] for record in selected if record[result_key] is not None)),
            }
        summary["component_outcomes"][component]["by_side"] = {}
        for side in ("LONG", "SHORT"):
            side_selected = [record for record in selected if record["side"] == side]
            summary["component_outcomes"][component]["by_side"][side] = {
                "count": len(side_selected),
                **{
                    str(horizon): dict(Counter(
                        record[f"fwd_{horizon}_result"]
                        for record in side_selected
                        if record[f"fwd_{horizon}_result"] is not None
                    ))
                    for horizon in horizon_bars
                },
            }
    candidates = [record for record in records if record["candidate"]]
    for horizon in horizon_bars:
        key = f"fwd_{horizon}_result"
        summary["candidate_outcomes"][str(horizon)] = dict(
            Counter(record[key] for record in candidates if record[key] is not None)
        )
    for horizon in horizon_bars:
        key = f"fwd_{horizon}_direction"
        summary["outcomes"][str(horizon)] = dict(
            Counter(record[key] for record in records if record[key] is not None)
        )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zvezdin component/outcome statistics")
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--period", default="15min")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--output-prefix", required=True, help="prefix for .csv and .json files")
    parser.add_argument("--threshold-atr", type=float, default=0.25)
    parser.add_argument("--horizons", default="8,32,96", help="forward horizons in bars")
    parser.add_argument("--no-entry-volume", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    horizons = tuple(int(value) for value in args.horizons.split(",") if value.strip())
    end = args.end or date.today()
    start = args.start or (end - timedelta(days=args.days))
    if start >= end:
        raise SystemExit("--start must precede --end")
    config = load_default_config()
    if args.no_entry_volume:
        config = replace(config, volume_entry_filter=False, score_requires_flow=False)
    frame = load_sqlite_candles(args.sqlite, args.ticker, args.period, start, end)
    records, summary = collect_component_events(frame, config, horizons, args.threshold_atr)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(prefix.with_suffix(".csv"), index=False)
    document = {
        "ticker": args.ticker,
        "period": args.period,
        "bars": len(frame),
        "first_bar": frame.index[0].isoformat(),
        "last_bar": frame.index[-1].isoformat(),
        "horizons_bars": horizons,
        "threshold_atr": args.threshold_atr,
        "event_definition": "strong_level OR reverse_impulse provides the directional anchor; other components are confirmations",
        "candidate_definition": "strong_level AND reverse_impulse",
        "config": {
            "volume_entry_filter": config.volume_entry_filter,
            "post_entry_volume_management": config.post_entry_volume_management,
            "exhaustion_mode": config.exhaustion_mode,
        },
        "summary": summary,
    }
    prefix.with_suffix(".json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
