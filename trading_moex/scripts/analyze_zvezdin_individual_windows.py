#!/usr/bin/env python3
"""Grid-test separate memory windows for the five Zvezdin components."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from itertools import product
from pathlib import Path
from statistics import mean, median

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


def component_timeline(frame: pd.DataFrame, config: StrategyConfig) -> tuple[list, dict[tuple[int, str], dict[str, bool]]]:
    bars = bars_from_dataframe(
        frame,
        session_start_minute=config.session_start_minute,
        session_end_minute=config.session_end_minute,
        slot_minutes=config.slot_minutes,
        calendar=config.calendar,
    )
    engine = StrategyEngine(config=config)
    flags_by_bar_side: dict[tuple[int, str], dict[str, bool]] = {}
    for bar in bars:
        engine.on_bar(bar, emit_signals=True)
        audit = engine.audit[-1] if engine.audit else None
        if audit is None:
            continue
        for side in (Side.LONG, Side.SHORT):
            flags_by_bar_side[(bar.index, side.value)] = {
                "acceleration": bool(audit.acceleration),
                "atr_completion": bool(audit.exhaustion_long if side is Side.LONG else audit.exhaustion_short),
                "strong_level": bool(audit.long_zone_id if side is Side.LONG else audit.short_zone_id),
                "volume_participant": bool(audit.volume_spike),
                "reverse_impulse": bool(audit.candle_shape_long if side is Side.LONG else audit.candle_shape_short),
            }
        # Diagnostic mode observes every bar independently.
        engine.position = None
        engine.pending = None
        engine.emergency_zone_id = None
    return bars, flags_by_bar_side


def _signal_rows(
    bars: list,
    flags: dict[tuple[int, str], dict[str, bool]],
    windows: dict[str, int],
    cooldown: int,
) -> list[dict]:
    rows: list[dict] = []
    last_signal = {"LONG": -10**9, "SHORT": -10**9}
    last_seen = {side: {component: None for component in COMPONENTS} for side in ("LONG", "SHORT")}
    for bar in bars:
        for side in ("LONG", "SHORT"):
            current = flags.get((bar.index, side), {})
            seen = last_seen[side]
            for component in COMPONENTS:
                if current.get(component, False):
                    seen[component] = bar.index
            if any(value is None for value in seen.values()):
                continue
            if bar.index - last_signal[side] < cooldown:
                continue
            if any(bar.index - seen[component] >= windows[component] for component in COMPONENTS):
                continue
            rows.append({
                "bar": bar.index,
                "side": side,
                "component_bars": dict(seen),
                "span_bars": bar.index - min(seen.values()),
            })
            last_signal[side] = bar.index
    return rows


def _signed_return(closes: list[float], signal: dict, horizon: int) -> float | None:
    index = signal["bar"]
    if index + horizon >= len(closes):
        return None
    value = (closes[index + horizon] - closes[index]) / closes[index]
    return value if signal["side"] == "LONG" else -value


def stats(signals: list[dict], closes: list[float], horizons: tuple[int, ...]) -> dict:
    result = {"count": len(signals), "mean_span_bars": mean([x["span_bars"] for x in signals]) if signals else 0.0, "horizons": {}}
    for horizon in horizons:
        values = [value for signal in signals if (value := _signed_return(closes, signal, horizon)) is not None]
        outcomes = Counter("WIN" if value > 0 else "LOSS" if value < 0 else "FLAT" for value in values)
        result["horizons"][str(horizon)] = {
            "count": len(values),
            "wins": outcomes["WIN"],
            "losses": outcomes["LOSS"],
            "flat": outcomes["FLAT"],
            "win_rate_ex_flat": outcomes["WIN"] / (outcomes["WIN"] + outcomes["LOSS"])
            if outcomes["WIN"] + outcomes["LOSS"] else 0.0,
            "mean_return_bps": 10000 * mean(values) if values else 0.0,
            "median_return_bps": 10000 * median(values) if values else 0.0,
        }
    return result


def parse_values(raw: str) -> tuple[int, ...]:
    values = tuple(sorted({int(value.strip()) for value in raw.split(",") if value.strip()}))
    if not values or any(value < 1 for value in values):
        raise ValueError("window values must be positive integers")
    return values


def analyze_ticker(
    frame: pd.DataFrame,
    config: StrategyConfig,
    grids: dict[str, tuple[int, ...]],
    horizons: tuple[int, ...],
    cooldown: int,
) -> list[dict]:
    bars, flags = component_timeline(frame, config)
    closes = [bar.close for bar in bars]
    rows = []
    for values in product(*(grids[component] for component in COMPONENTS)):
        windows = dict(zip(COMPONENTS, values))
        signals = _signal_rows(bars, flags, windows, cooldown)
        record = {"windows": windows, "stats": stats(signals, closes, horizons)}
        rows.append(record)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid-test individual component windows")
    parser.add_argument("--sqlite", required=True)
    parser.add_argument("--tickers", required=True)
    parser.add_argument("--period", default="15min")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--acceleration", default="1,2,4")
    parser.add_argument("--atr-completion", default="1,2,4,8")
    parser.add_argument("--strong-level", default="1,2,4,8,16")
    parser.add_argument("--volume-participant", default="1,2,4,8")
    parser.add_argument("--reverse-impulse", default="1,2,4")
    parser.add_argument("--cooldown", type=int, default=8)
    parser.add_argument("--horizons", default="8,32,96")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    grids = {
        "acceleration": parse_values(args.acceleration),
        "atr_completion": parse_values(args.atr_completion),
        "strong_level": parse_values(args.strong_level),
        "volume_participant": parse_values(args.volume_participant),
        "reverse_impulse": parse_values(args.reverse_impulse),
    }
    horizons = parse_values(args.horizons)
    config = replace(load_default_config(), volume_entry_filter=False, score_requires_flow=False)
    report = {
        "period": args.period,
        "start": args.start.isoformat(),
        "end": args.end.isoformat(),
        "cooldown": args.cooldown,
        "grids": grids,
        "tickers": {},
    }
    for ticker in (value.strip().upper() for value in args.tickers.split(",") if value.strip()):
        frame = load_candles(args.sqlite, ticker, args.period, args.start, args.end)
        report["tickers"][ticker] = analyze_ticker(frame, config, grids, horizons, args.cooldown)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tickers": len(report["tickers"]), "variants_per_ticker": len(next(iter(report["tickers"].values())))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
