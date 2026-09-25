"""Causal VSA anomaly and Fibonacci-cycle statistics for OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .volume_analysis import FIB_COUNTS, load_candles


@dataclass(frozen=True)
class VSAConfig:
    volume_multiplier: float = 2.5
    volume_window: int = 20
    atr_period: int = 14
    forward_horizons: tuple[int, ...] = (1, 3, 5, 8)
    flat_horizon: int = 4
    body_small_pin_ratio: float = 0.30
    shadow_pin_ratio: float = 0.60
    absorption_range_atr: float = 0.70
    absorption_body_atr: float = 0.40
    momentum_range_atr: float = 1.50
    momentum_body_ratio: float = 0.70
    cycle_horizon: int = 13


ANOMALY_TYPES = (
    "Absorption / stopping volume",
    "Rejection / liquidity sweep",
    "Trend climax / pure momentum",
)


def prepare_vsa(frame: pd.DataFrame, config: VSAConfig | None = None) -> pd.DataFrame:
    """Calculate causal ATR/volume features and assign VSA categories.

    The requested categories are not mutually exclusive mathematically. Events
    are assigned exclusively with momentum taking priority over rejection, and
    rejection over absorption; this prevents double-counting in the comparison
    table while preserving the requested three anomaly families.
    """
    config = config or VSAConfig()
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {', '.join(sorted(missing))}")
    out = frame.copy().reset_index(drop=True)
    out["range"] = (out["high"] - out["low"]).clip(lower=0)
    out["body"] = (out["close"] - out["open"]).abs()
    out["body_ratio"] = out["body"].div(out["range"].replace(0, np.nan)).fillna(0.0)
    out["upper_wick"] = (out["high"] - out[["open", "close"]].max(axis=1)).clip(lower=0)
    out["lower_wick"] = (out[["open", "close"]].min(axis=1) - out["low"]).clip(lower=0)
    out["upper_wick_ratio"] = out["upper_wick"].div(out["range"].replace(0, np.nan)).fillna(0.0)
    out["lower_wick_ratio"] = out["lower_wick"].div(out["range"].replace(0, np.nan)).fillna(0.0)

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
    previous_volume = out["volume"].shift(1)
    out["volume_sma"] = previous_volume.rolling(
        config.volume_window, min_periods=config.volume_window
    ).mean()
    out["volume_ratio"] = out["volume"].div(out["volume_sma"].replace(0, np.nan))
    out["is_anomalous_volume"] = out["volume_ratio"] >= config.volume_multiplier

    out["is_absorption"] = (
        out["is_anomalous_volume"]
        & out["range"].le(config.absorption_range_atr * out["atr"])
        & out["body"].le(config.absorption_body_atr * out["atr"])
    )
    out["is_bullish_rejection"] = (
        out["is_anomalous_volume"]
        & out["body_ratio"].le(config.body_small_pin_ratio)
        & out["lower_wick_ratio"].ge(config.shadow_pin_ratio)
    )
    out["is_bearish_rejection"] = (
        out["is_anomalous_volume"]
        & out["body_ratio"].le(config.body_small_pin_ratio)
        & out["upper_wick_ratio"].ge(config.shadow_pin_ratio)
    )
    out["is_momentum"] = (
        out["is_anomalous_volume"]
        & out["range"].ge(config.momentum_range_atr * out["atr"])
        & out["body_ratio"].ge(config.momentum_body_ratio)
    )

    out["anomaly_type"] = ""
    out["rejection_side"] = ""
    # Specific rejection shapes take precedence over the broad absorption rule.
    out.loc[out["is_absorption"], "anomaly_type"] = "Absorption / stopping volume"
    rejection = out["is_bullish_rejection"] | out["is_bearish_rejection"]
    out.loc[rejection, "anomaly_type"] = "Rejection / liquidity sweep"
    out.loc[out["is_bullish_rejection"], "rejection_side"] = "bullish / lower tail"
    out.loc[out["is_bearish_rejection"], "rejection_side"] = "bearish / upper tail"
    out.loc[out["is_momentum"], "anomaly_type"] = "Trend climax / pure momentum"
    out["is_vsa_event"] = out["anomaly_type"].ne("")
    out["direction"] = np.select(
        [out["close"] > out["open"], out["close"] < out["open"]],
        ["bullish", "bearish"],
        default="doji",
    )
    return out


def _directional_metrics(
    frame: pd.DataFrame,
    index: int,
    config: VSAConfig,
) -> dict[str, Any]:
    signal = frame.iloc[index]
    future = frame.iloc[index + 1 : index + 1 + max(config.forward_horizons)]
    entry = float(signal["close"])
    direction = 1 if signal["direction"] == "bullish" else -1 if signal["direction"] == "bearish" else 0
    signal_high = float(signal["high"])
    signal_low = float(signal["low"])
    result: dict[str, Any] = {}
    for horizon in config.forward_horizons:
        bars = future.iloc[:horizon]
        if len(bars) < horizon:
            result[f"win_{horizon}"] = np.nan
            result[f"reversal_{horizon}"] = np.nan
            result[f"mfe_pct_{horizon}"] = np.nan
            result[f"mfe_atr_{horizon}"] = np.nan
            result[f"mae_pct_{horizon}"] = np.nan
            continue
        if direction == 0:
            favorable = max(float(bars["high"].max()) - entry, entry - float(bars["low"].min()))
            adverse = favorable
            result[f"win_{horizon}"] = np.nan
            result[f"reversal_{horizon}"] = np.nan
        else:
            favorable = direction * (
                float(bars["high"].max()) - entry if direction == 1 else float(bars["low"].min()) - entry
            )
            adverse = direction * (
                float(bars["low"].min()) - entry if direction == 1 else float(bars["high"].max()) - entry
            )
            final_return = direction * (float(bars["close"].iloc[-1]) / entry - 1.0)
            result[f"win_{horizon}"] = float(final_return > 0)
            result[f"reversal_{horizon}"] = float(final_return < 0)
        atr = float(signal["atr"]) if pd.notna(signal["atr"]) and float(signal["atr"]) > 0 else np.nan
        result[f"mfe_pct_{horizon}"] = favorable / entry * 100.0
        result[f"mfe_atr_{horizon}"] = favorable / atr if np.isfinite(atr) else np.nan
        result[f"mae_pct_{horizon}"] = max(0.0, -adverse) / entry * 100.0

    flat_bars = frame.iloc[index + 1 : index + 1 + config.flat_horizon]
    result["flat_4"] = float(
        len(flat_bars) == config.flat_horizon
        and (flat_bars["high"] <= signal_high).all()
        and (flat_bars["low"] >= signal_low).all()
    )
    result["forward_bars"] = len(future)
    return result


def analyze_vsa_events(frame: pd.DataFrame, config: VSAConfig | None = None) -> pd.DataFrame:
    """Return forward-looking metrics for each classified anomaly."""
    config = config or VSAConfig()
    prepared = prepare_vsa(frame, config)
    rows: list[dict[str, Any]] = []
    for index, signal in prepared.loc[prepared["is_vsa_event"]].iterrows():
        metrics = _directional_metrics(prepared, int(index), config)
        rows.append(
            {
                "timestamp": signal["timestamp"],
                "anomaly_type": signal["anomaly_type"],
                "rejection_side": signal["rejection_side"],
                "direction": signal["direction"],
                "volume_ratio": float(signal["volume_ratio"]),
                "range_atr": float(signal["range"] / signal["atr"]) if pd.notna(signal["atr"]) and signal["atr"] else np.nan,
                "body_ratio": float(signal["body_ratio"]),
                "atr": float(signal["atr"]) if pd.notna(signal["atr"]) else np.nan,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def _run_length(values: np.ndarray, start: int, direction: int) -> int:
    length = 0
    for value in values[start:]:
        if direction == 1 and value <= 0:
            break
        if direction == -1 and value >= 0:
            break
        length += 1
    return length


def _cycle_observation(
    frame: pd.DataFrame,
    start: int,
    direction: int,
    config: VSAConfig,
) -> dict[str, Any] | None:
    """Measure impulse/correction lengths from a causal directional start.

    The impulse is the consecutive close-to-close move after the anchor. The
    correction is the next opposite close-to-close run. Continuation means a
    later close breaks the impulse extreme in the original direction.
    """
    closes = frame["close"].to_numpy(float)
    changes = np.diff(closes)
    if start >= len(changes) or direction == 0:
        return None
    impulse_length = _run_length(changes, start, direction)
    if impulse_length == 0:
        return None
    correction_start = start + impulse_length
    correction_length = _run_length(changes, correction_start, -direction)
    if correction_length == 0:
        return None
    impulse_start_price = closes[start]
    impulse_end_index = correction_start
    impulse_end_price = closes[impulse_end_index]
    correction_end_index = correction_start + correction_length
    if correction_end_index >= len(closes):
        return None
    correction_end_price = closes[correction_end_index]
    impulse_size = abs(impulse_end_price - impulse_start_price)
    if impulse_size <= 0:
        return None
    correction_depth = abs(impulse_end_price - correction_end_price) / impulse_size
    post = closes[correction_end_index + 1 : correction_end_index + 1 + config.cycle_horizon]
    resumed = False
    for value in post:
        if direction == 1:
            if value > impulse_end_price:
                resumed = True
                break
            if value <= impulse_start_price:
                break
        else:
            if value < impulse_end_price:
                resumed = True
                break
            if value >= impulse_start_price:
                break
    return {
        "impulse_length": impulse_length,
        "correction_length": correction_length,
        "correction_depth": correction_depth,
        "resumed": float(resumed),
        "anchor_index": start,
    }


def analyze_fibonacci_cycles(
    frame: pd.DataFrame,
    config: VSAConfig | None = None,
    *,
    event_indices: set[int] | None = None,
) -> pd.DataFrame:
    """Collect cycle observations from anomalies and independent extrema.

    Event anchors are always included. For coverage, each local close extreme
    followed by a directional move is also an anchor, but no future prices are
    used to define the initial direction.
    """
    config = config or VSAConfig()
    prepared = prepare_vsa(frame, config)
    closes = prepared["close"].to_numpy(float)
    changes = np.diff(closes)
    anchors: set[int] = set(event_indices or set())
    if len(changes) and changes[0] != 0:
        anchors.add(0)
    for index in range(1, len(changes)):
        if changes[index] != 0 and (index == 1 or np.sign(changes[index]) != np.sign(changes[index - 1])):
            anchors.add(index)
    rows: list[dict[str, Any]] = []
    for anchor in sorted(anchors):
        if event_indices and anchor in event_indices:
            direction = int(np.sign(closes[anchor] - float(prepared["open"].iloc[anchor])))
        else:
            direction = int(np.sign(changes[anchor])) if anchor < len(changes) else 0
        observation = _cycle_observation(prepared, anchor, direction, config)
        if observation is None:
            continue
        observation["anchor_timestamp"] = prepared["timestamp"].iloc[anchor]
        observation["anchor_is_vsa"] = int(anchor in (event_indices or set()))
        if observation["impulse_length"] in FIB_COUNTS and observation["correction_length"] in FIB_COUNTS:
            rows.append(observation)
    return pd.DataFrame(rows)


def classify_depth(depth: float) -> str:
    if depth <= 0.382:
        return "<=38.2%"
    if depth <= 0.500:
        return "38.2-50%"
    if depth <= 0.618:
        return "50-61.8%"
    return ">61.8%"


def cycle_matrix(cycles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for impulse in FIB_COUNTS:
        row: dict[str, Any] = {"impulse": impulse}
        for correction in FIB_COUNTS:
            subset = cycles[
                cycles["impulse_length"].eq(impulse)
                & cycles["correction_length"].eq(correction)
            ]
            row[correction] = subset["resumed"].mean() * 100.0 if len(subset) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def depth_summary(cycles: pd.DataFrame) -> pd.DataFrame:
    if cycles.empty:
        return pd.DataFrame(columns=["depth", "events", "continuation_pct", "mean_depth"])
    return (
        cycles.assign(depth=cycles["correction_depth"].map(classify_depth))
        .groupby("depth", sort=False)
        .agg(
            events=("resumed", "size"),
            continuation_pct=("resumed", lambda values: values.mean() * 100.0),
            mean_depth=("correction_depth", "mean"),
        )
        .reset_index()
    )
