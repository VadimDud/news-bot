"""Volume-spike analysis for OHLCV candles.

The calculations in this module are deliberately independent from the live
trading code.  In particular, all rolling baselines are shifted by one bar so
that the signal candle cannot influence its own volume or ATR benchmark.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AnalysisConfig:
    """Thresholds for volume-spike detection and forward evaluation."""

    volume_multiplier: float = 2.5
    zscore_threshold: float = 2.5
    volume_sma_window: int = 20
    zscore_window: int = 50
    atr_period: int = 14
    horizon: int = 4


EVENT_COLUMNS = [
    "timestamp",
    "volume_ratio",
    "volume_zscore",
    "candle_type",
    "direction",
    "body_ratio",
    "upper_shadow_ratio",
    "lower_shadow_ratio",
    "atr_spread",
    "reaction",
    "outcome_status",
    "outcome_group",
    "net_change_15m_pct",
    "net_change_30m_pct",
    "net_change_60m_pct",
    "mfe_pct",
    "mae_pct",
    "future_bars",
]


def load_candles(db_path: str | Path, ticker: str = "T", period: str = "15min") -> pd.DataFrame:
    """Load candles from SQLite in read-only mode.

    Keeping the connection read-only prevents an analysis run from creating a
    database or changing the trading bot's live database.
    """
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")

    uri = f"file:{path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        frame = pd.read_sql_query(
            """
            SELECT begin AS timestamp, open, high, low, close, volume
            FROM candles
            WHERE ticker = ? AND period = ?
            ORDER BY begin
            """,
            connection,
            params=(ticker.upper(), period),
        )

    if frame.empty:
        raise ValueError(f"No candles found for {ticker.upper()} / {period}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        .drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    if frame.empty:
        raise ValueError(f"No valid OHLCV candles found for {ticker.upper()} / {period}")
    return frame


def _candle_type(direction: str, body_ratio: float, upper_ratio: float, lower_ratio: float) -> str:
    """Give a concise, deterministic label to a candle shape."""
    long_upper = upper_ratio >= 0.40
    long_lower = lower_ratio >= 0.40
    if direction == "Doji":
        if long_upper and not long_lower:
            return "Doji / upper rejection"
        if long_lower and not long_upper:
            return "Doji / lower rejection"
        return "Doji"
    if long_upper and upper_ratio >= lower_ratio:
        return "Bearish pin-bar / upper rejection"
    if long_lower and lower_ratio > upper_ratio:
        return "Bullish pin-bar / lower rejection"
    if body_ratio >= 0.60:
        return f"Full-bodied {direction.lower()}"
    return f"Small-body {direction.lower()}"


def prepare_candles(frame: pd.DataFrame, config: AnalysisConfig | None = None) -> pd.DataFrame:
    """Add non-forward-looking candle, volume and ATR features."""
    config = config or AnalysisConfig()
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {', '.join(sorted(missing))}")

    out = frame.copy().reset_index(drop=True)
    out["range"] = (out["high"] - out["low"]).clip(lower=0)
    out["body_abs"] = (out["close"] - out["open"]).abs()
    out["body_ratio"] = out["body_abs"].div(out["range"].replace(0, np.nan)).fillna(0.0)
    out["upper_wick"] = (out["high"] - out[["open", "close"]].max(axis=1)).clip(lower=0)
    out["lower_wick"] = (out[["open", "close"]].min(axis=1) - out["low"]).clip(lower=0)
    out["upper_shadow_ratio"] = out["upper_wick"].div(out["range"].replace(0, np.nan)).fillna(0.0)
    out["lower_shadow_ratio"] = out["lower_wick"].div(out["range"].replace(0, np.nan)).fillna(0.0)

    out["direction"] = np.select(
        [out["close"] > out["open"], out["close"] < out["open"]],
        ["Bullish", "Bearish"],
        default="Doji",
    )
    out["candle_type"] = [
        _candle_type(direction, body, upper, lower)
        for direction, body, upper, lower in zip(
            out["direction"],
            out["body_ratio"],
            out["upper_shadow_ratio"],
            out["lower_shadow_ratio"],
        )
    ]

    previous_close = out["close"].shift(1)
    true_range = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - previous_close).abs(),
            (out["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = true_range.rolling(config.atr_period, min_periods=config.atr_period).mean().shift(1)
    out["atr_spread"] = out["range"].div(out["atr"].replace(0, np.nan))

    prior_volume = out["volume"].shift(1)
    out["volume_sma"] = prior_volume.rolling(
        config.volume_sma_window, min_periods=config.volume_sma_window
    ).mean()
    out["volume_ratio"] = out["volume"].div(out["volume_sma"].replace(0, np.nan))
    prior_volume_mean = prior_volume.rolling(
        config.zscore_window, min_periods=config.zscore_window
    ).mean()
    prior_volume_std = prior_volume.rolling(
        config.zscore_window, min_periods=config.zscore_window
    ).std(ddof=0)
    out["volume_zscore"] = (out["volume"] - prior_volume_mean).div(prior_volume_std.replace(0, np.nan))
    out["is_volume_spike"] = (
        out["volume_ratio"].ge(config.volume_multiplier)
        | out["volume_zscore"].gt(config.zscore_threshold)
    )
    return out


def _pct_change(value: float | None, base: float) -> float | None:
    if value is None or not np.isfinite(value) or base == 0:
        return None
    return (value / base - 1.0) * 100.0


def _pct_move(distance: float, base: float) -> float:
    if base == 0:
        return np.nan
    return distance / base * 100.0


def _forward_reaction(frame: pd.DataFrame, index: int, config: AnalysisConfig) -> dict[str, Any]:
    signal = frame.iloc[index]
    future = frame.iloc[index + 1 : index + 1 + config.horizon]
    future_bars = len(future)
    if future_bars == 0:
        return {
            "reaction": "Insufficient data",
            "outcome_status": "Insufficient data",
            "outcome_group": "insufficient",
            "future_bars": 0,
        }

    direction = signal["direction"]
    signal_open = float(signal["open"])
    signal_close = float(signal["close"])
    signal_high = float(signal["high"])
    signal_low = float(signal["low"])
    atr = float(signal["atr"]) if pd.notna(signal["atr"]) else np.nan
    breakout_index: int | None = None
    reversal_index: int | None = None
    for offset, (_, bar) in enumerate(future.iterrows(), start=1):
        if direction == "Bullish":
            breakout = pd.notna(atr) and float(bar["high"]) > signal_high + atr
            reversal = float(bar["close"]) < signal_open
        elif direction == "Bearish":
            breakout = pd.notna(atr) and float(bar["low"]) < signal_low - atr
            reversal = float(bar["close"]) > signal_open
        else:
            # A doji has no closing direction, so only a range/ATR impulse is
            # meaningful; a close back through its open is not a reversal.
            breakout = (
                pd.notna(atr)
                and (float(bar["high"]) > signal_high + atr or float(bar["low"]) < signal_low - atr)
            )
            reversal = False
        if breakout and breakout_index is None:
            breakout_index = offset
        if reversal and reversal_index is None:
            reversal_index = offset

    has_complete_horizon = future_bars == config.horizon
    inside_range = has_complete_horizon and bool(
        (future["high"] <= signal_high).all() and (future["low"] >= signal_low).all()
    )

    if reversal_index is not None and (breakout_index is None or reversal_index <= breakout_index):
        reaction = "Reversal"
        status = "Liquidity sweep / reversal"
        group = "reversal"
    elif breakout_index is not None:
        if reversal_index is not None:
            reaction = "Impulse -> reversal"
            status = "False breakout"
            group = "reversal"
        else:
            reaction = "Impulse / continuation"
            status = "True breakout"
            group = "continuation"
    elif inside_range:
        reaction = "Flat / fading"
        status = "Position building in range"
        group = "flat"
    elif not has_complete_horizon:
        reaction = "Insufficient data"
        status = "Insufficient data"
        group = "insufficient"
    else:
        reaction = "Flat / fading"
        status = "Weak move without breakout"
        group = "flat"

    favorable_high = float(future["high"].max())
    adverse_low = float(future["low"].min())
    favorable_low = float(future["low"].min())
    adverse_high = float(future["high"].max())
    if direction == "Bearish":
        mfe = _pct_move(signal_close - favorable_low, signal_close)
        mae = _pct_move(adverse_high - signal_close, signal_close)
    else:
        # Doji is treated as a two-sided event: use the larger favorable side
        # and the larger adverse side, without inventing a direction.
        if direction == "Bullish":
            mfe = _pct_move(favorable_high - signal_close, signal_close)
            mae = _pct_move(signal_close - adverse_low, signal_close)
        else:
            up_move = _pct_change(favorable_high, signal_close)
            down_move = _pct_move(signal_close - favorable_low, signal_close)
            mfe = max(up_move or 0.0, down_move or 0.0)
            mae = max(up_move or 0.0, down_move or 0.0)

    net_changes: dict[str, float | None] = {}
    for minutes, offset in ((15, 1), (30, 2), (60, 4)):
        value = future["close"].iloc[offset - 1] if future_bars >= offset else None
        net_changes[f"net_change_{minutes}m_pct"] = _pct_change(value, signal_close)

    return {
        "reaction": reaction,
        "outcome_status": status,
        "outcome_group": group,
        "mfe_pct": mfe,
        "mae_pct": mae,
        "future_bars": future_bars,
        **net_changes,
    }


def analyze_events(frame: pd.DataFrame, config: AnalysisConfig | None = None) -> pd.DataFrame:
    """Return one row for every detected volume-spike candle."""
    config = config or AnalysisConfig()
    prepared = prepare_candles(frame, config)
    events: list[dict[str, Any]] = []
    for index, signal in prepared.loc[prepared["is_volume_spike"]].iterrows():
        reaction = _forward_reaction(prepared, int(index), config)
        events.append(
            {
                "timestamp": signal["timestamp"],
                "volume_ratio": float(signal["volume_ratio"]),
                "volume_zscore": float(signal["volume_zscore"]) if pd.notna(signal["volume_zscore"]) else None,
                "candle_type": signal["candle_type"],
                "direction": signal["direction"],
                "body_ratio": float(signal["body_ratio"]),
                "upper_shadow_ratio": float(signal["upper_shadow_ratio"]),
                "lower_shadow_ratio": float(signal["lower_shadow_ratio"]),
                "atr_spread": float(signal["atr_spread"]) if pd.notna(signal["atr_spread"]) else None,
                **reaction,
            }
        )
    return pd.DataFrame(events, columns=EVENT_COLUMNS)


def event_statistics(events: pd.DataFrame) -> dict[str, Any]:
    """Build aggregate statistics using only events with four future bars."""
    complete = events[events["outcome_group"] != "insufficient"].copy()
    total = len(events)
    complete_total = len(complete)

    def share(group: str) -> float:
        return (complete["outcome_group"].eq(group).mean() * 100.0) if complete_total else 0.0

    by_type: list[dict[str, Any]] = []
    if complete_total:
        for candle_type, group in complete.groupby("candle_type", sort=True):
            by_type.append(
                {
                    "candle_type": candle_type,
                    "events": len(group),
                    "mean_15m_pct": group["net_change_15m_pct"].mean(),
                    "mean_30m_pct": group["net_change_30m_pct"].mean(),
                    "mean_60m_pct": group["net_change_60m_pct"].mean(),
                    "continuation_pct": group["outcome_group"].eq("continuation").mean() * 100.0,
                    "flat_pct": group["outcome_group"].eq("flat").mean() * 100.0,
                    "reversal_pct": group["outcome_group"].eq("reversal").mean() * 100.0,
                }
            )
    return {
        "total_events": total,
        "complete_events": complete_total,
        "insufficient_events": total - complete_total,
        "continuation_pct": share("continuation"),
        "flat_pct": share("flat"),
        "reversal_pct": share("reversal"),
        "mean_15m_pct": complete["net_change_15m_pct"].mean() if complete_total else np.nan,
        "mean_30m_pct": complete["net_change_30m_pct"].mean() if complete_total else np.nan,
        "mean_60m_pct": complete["net_change_60m_pct"].mean() if complete_total else np.nan,
        "by_type": by_type,
    }
