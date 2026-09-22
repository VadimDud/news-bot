#!/usr/bin/env python3
"""Measure how the five Zvezdin components cluster in time."""

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


def load_candles(path: str, ticker: str, period: str, start: date, end: date) -> pd.DataFrame:
    with sqlite3.connect(path) as connection:
        frame = pd.read_sql_query(
            "SELECT begin AS datetime, open, high, low, close, volume "
            "FROM candles WHERE ticker=? AND period=? AND begin>=? AND begin<? ORDER BY begin",
            connection,
            params=(ticker, period, start.isoformat(), end.isoformat()),
        )
    if frame.empty:
        raise ValueError(f"no candles for {ticker} {period} in {start}..{end}")
    frame["datetime"] = pd.to_datetime(frame["datetime"], utc=True, errors="raise")
    return frame.set_index("datetime")


def component_timeline(frame: pd.DataFrame, config: StrategyConfig) -> list[dict]:
    bars = bars_from_dataframe(
        frame,
        session_start_minute=config.session_start_minute,
        session_end_minute=config.session_end_minute,
        slot_minutes=config.slot_minutes,
        calendar=config.calendar,
    )
    engine = StrategyEngine(config=config)
    atr_values: list[float | None] = []
    events: list[dict] = []
    for bar in bars:
        engine.on_bar(bar, emit_signals=True)
        atr_values.append(engine._atr[-1] if engine._atr else None)
        audit = engine.audit[-1] if engine.audit else None
        if audit is None:
            continue
        for side in (Side.LONG, Side.SHORT):
            flags = {
                "acceleration": bool(audit.acceleration),
                "atr_completion": bool(audit.exhaustion_long if side is Side.LONG else audit.exhaustion_short),
                "strong_level": bool(audit.long_zone_id if side is Side.LONG else audit.short_zone_id),
                "volume_participant": bool(audit.volume_spike),
                "reverse_impulse": bool(audit.candle_shape_long if side is Side.LONG else audit.candle_shape_short),
            }
            if any(flags.values()):
                events.append({
                    "bar": bar.index,
                    "datetime": frame.index[bar.index].isoformat(),
                    "side": side.value,
                    "atr_previous": atr_values[-2] if len(atr_values) > 1 else None,
                    **flags,
                })
        # Every bar is an independent diagnostic observation.
        engine.position = None
        engine.pending = None
        engine.emergency_zone_id = None
    return events


def forward_result(closes: list[float], index: int, side: str, horizon: int, atr: float, threshold: float) -> tuple[str | None, float | None]:
    future = index + horizon
    if future >= len(closes) or not atr or atr <= 0:
        return None, None
    signed = (closes[future] - closes[index]) / closes[index]
    if side == "SHORT":
        signed = -signed
    if abs(closes[future] - closes[index]) <= threshold * atr:
        return "FLAT", signed
    return ("WIN" if signed > 0 else "LOSS"), signed


def make_clusters(
    events: list[dict],
    bars: list,
    max_window: int,
    cooldown: int | None = None,
) -> list[dict]:
    by_side: dict[str, list[dict]] = {"LONG": [], "SHORT": []}
    for event in events:
        by_side[event["side"]].append(event)
    clusters: list[dict] = []
    for side, side_events in by_side.items():
        right = 0
        for start_position, first in enumerate(side_events):
            start_bar = first["bar"]
            end_bar = start_bar + max_window
            while right < len(side_events) and side_events[right]["bar"] <= end_bar:
                right += 1
            window = side_events[start_position:right]
            seen = {component: next((event["bar"] for event in window if event[component]), None) for component in COMPONENTS}
            if any(value is None for value in seen.values()):
                continue
            finish_bar = max(seen.values())
            clusters.append({
                "start_bar": start_bar,
                "finish_bar": finish_bar,
                "span_bars": finish_bar - start_bar,
                "side": side,
                "components": seen,
            })
    clusters.sort(key=lambda item: (item["side"], item["finish_bar"], item["start_bar"]))
    if cooldown is None:
        return clusters
    selected: list[dict] = []
    last_finish = {"LONG": -10**9, "SHORT": -10**9}
    for cluster in clusters:
        if cluster["start_bar"] < last_finish[cluster["side"]] + cooldown:
            continue
        selected.append(cluster)
        last_finish[cluster["side"]] = cluster["finish_bar"]
    return selected


def enrich_clusters(clusters: list[dict], bars: list, closes: list[float], horizons: tuple[int, ...], threshold_atr: float) -> list[dict]:
    enriched = []
    for cluster in clusters:
        finish = cluster["finish_bar"]
        record = dict(cluster)
        record["datetime"] = bars[finish].index if hasattr(bars[finish], "index") else finish
        record["close"] = closes[finish]
        for horizon in horizons:
            result, signed_return = forward_result(
                closes, finish, cluster["side"], horizon,
                bars[finish].atr_previous if hasattr(bars[finish], "atr_previous") else 0.0,
                threshold_atr,
            )
            record[f"fwd_{horizon}_result"] = result
            record[f"fwd_{horizon}_return"] = signed_return
        enriched.append(record)
    return enriched


def cluster_stats(clusters: list[dict], horizons: tuple[int, ...]) -> dict:
    result = {"count": len(clusters), "components": {}, "outcomes": {}}
    for component in COMPONENTS:
        result["components"][component] = sum(component in cluster["components"] for cluster in clusters)
    for horizon in horizons:
        values = [cluster[f"fwd_{horizon}_result"] for cluster in clusters if cluster.get(f"fwd_{horizon}_result")]
        counts = Counter(values)
        result["outcomes"][str(horizon)] = {
            "WIN": counts["WIN"], "LOSS": counts["LOSS"], "FLAT": counts["FLAT"],
        }
    return result


def analyze_ticker(frame: pd.DataFrame, config: StrategyConfig, windows: tuple[int, ...], horizons: tuple[int, ...], threshold_atr: float) -> dict:
    bars = bars_from_dataframe(
        frame,
        session_start_minute=config.session_start_minute,
        session_end_minute=config.session_end_minute,
        slot_minutes=config.slot_minutes,
        calendar=config.calendar,
    )
    timeline = component_timeline(frame, config)
    closes = [bar.close for bar in bars]
    atr_by_side_bar = {
        (event["side"], event["bar"]): event.get("atr_previous")
        for event in timeline
    }
    output = {"timeline_events": len(timeline), "windows": {}}
    for window in windows:
        raw = make_clusters(timeline, bars, window)
        sparse = make_clusters(timeline, bars, window, cooldown=window)
        # The diagnostic engine stores ATR internally, so use the causal ATR
        # value attached to the source bar when available for direction tests.
        for cluster_set in (raw, sparse):
            for cluster in cluster_set:
                finish = cluster["finish_bar"]
                cluster["datetime"] = frame.index[finish].isoformat()
                cluster["close"] = closes[finish]
                cluster["atr_previous"] = atr_by_side_bar.get((cluster["side"], finish))
                for horizon in horizons:
                    if finish + horizon >= len(closes):
                        cluster[f"fwd_{horizon}_result"] = None
                        cluster[f"fwd_{horizon}_return"] = None
                        continue
                    change = closes[finish + horizon] - closes[finish]
                    signed = change / closes[finish] if cluster["side"] == "LONG" else -change / closes[finish]
                    threshold = 0.25 * cluster["atr_previous"] if cluster["atr_previous"] else 0.0
                    if abs(change) <= threshold:
                        cluster[f"fwd_{horizon}_result"] = "FLAT"
                    else:
                        cluster[f"fwd_{horizon}_result"] = "WIN" if signed > 0 else "LOSS"
                    cluster[f"fwd_{horizon}_return"] = signed
        output["windows"][str(window)] = {
            "raw": cluster_stats(raw, horizons),
            "non_overlapping": cluster_stats(sparse, horizons),
            "clusters": sparse,
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Time clustering of Zvezdin components")
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--tickers", required=True)
    parser.add_argument("--period", default="15min")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--windows", default="1,2,4,8,16,32")
    parser.add_argument("--horizons", default="8,32,96")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = replace(load_default_config(), volume_entry_filter=False, score_requires_flow=False)
    windows = tuple(int(value) for value in args.windows.split(",") if value.strip())
    horizons = tuple(int(value) for value in args.horizons.split(",") if value.strip())
    report = {"period": args.period, "start": args.start.isoformat(), "end": args.end.isoformat(), "tickers": {}}
    for ticker in (value.strip().upper() for value in args.tickers.split(",") if value.strip()):
        frame = load_candles(args.sqlite, ticker, args.period, args.start, args.end)
        report["tickers"][ticker] = analyze_ticker(frame, config, windows, horizons, 0.25)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
