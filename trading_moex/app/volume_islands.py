"""Causal event study for predominantly one-colour volume islands.

This module deliberately does not emit live signals.  Candle colour is only an
OHLCV proxy for order-flow direction: it is not a substitute for trade tape or
footprint data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IslandConfig:
    volume_window: int = 20
    separator_quantile: float = 0.20
    min_length: int = 2
    dominance_threshold: float = 0.60
    max_neutral_share: float = 0.30
    min_move_atr: float = 0.0
    atr_period: int = 14
    horizons: tuple[int, ...] = (1, 2, 4, 8, 12, 20)


def _causal_atr(frame: pd.DataFrame, period: int) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.shift(1).rolling(period, min_periods=period).mean()


def prepare_volume_islands(
    frame: pd.DataFrame,
    config: IslandConfig | None = None,
    directions: pd.Series | None = None,
) -> pd.DataFrame:
    """Add direction and strictly prior-volume features."""
    config = config or IslandConfig()
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {', '.join(sorted(missing))}")
    out = frame.copy().sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    calculated_direction = np.select(
        [out["close"] > out["open"], out["close"] < out["open"]], [1, -1], default=0
    )
    if directions is None:
        out["direction"] = calculated_direction
    else:
        if len(directions) != len(out):
            raise ValueError("directions must have the same length as frame")
        out["direction"] = np.asarray(directions, dtype=int)
    out["range"] = (out["high"] - out["low"]).clip(lower=0)
    out["body_ratio"] = (out["close"] - out["open"]).abs().div(out["range"].replace(0, np.nan)).fillna(0)
    prior = out["volume"].shift(1)
    out["volume_baseline"] = prior.rolling(config.volume_window, min_periods=config.volume_window).median()
    out["volume_ratio"] = out["volume"].div(out["volume_baseline"].replace(0, np.nan))
    out["separator_threshold"] = prior.rolling(
        config.volume_window, min_periods=config.volume_window
    ).quantile(config.separator_quantile)
    out["is_separator"] = out["volume"] <= out["separator_threshold"]
    out["atr"] = _causal_atr(out, config.atr_period)
    return out


def detect_islands(
    frame: pd.DataFrame,
    config: IslandConfig | None = None,
    directions: pd.Series | None = None,
) -> pd.DataFrame:
    """Return completed islands; confirmation is the separator bar itself."""
    config = config or IslandConfig()
    prepared = prepare_volume_islands(frame, config, directions)
    records: list[dict[str, object]] = []
    start: int | None = None

    for index, row in prepared.iterrows():
        if not np.isfinite(row["separator_threshold"]):
            start = None
            continue
        if not bool(row["is_separator"]):
            if start is None:
                start = index
            continue
        if start is None:
            continue
        island = prepared.iloc[start:index]
        start = None
        if len(island) < config.min_length:
            continue
        green = float(island.loc[island["direction"] == 1, "volume"].sum())
        red = float(island.loc[island["direction"] == -1, "volume"].sum())
        neutral = float(island.loc[island["direction"] == 0, "volume"].sum())
        directional = green + red
        total = directional + neutral
        if directional <= 0 or total <= 0:
            continue
        direction = 1 if green >= red else -1
        dominance = max(green, red) / directional
        if dominance < config.dominance_threshold or neutral / total > config.max_neutral_share:
            continue
        first, last = island.iloc[0], island.iloc[-1]
        move = direction * (float(last["close"]) / float(first["open"]) - 1)
        atr = float(row["atr"]) if np.isfinite(row["atr"]) else np.nan
        if config.min_move_atr and (not np.isfinite(atr) or abs(move * float(first["open"])) < config.min_move_atr * atr):
            continue
        records.append(
            {
                "start_index": index - len(island),
                "end_index": index - 1,
                "confirmation_index": index,
                "start_timestamp": first["timestamp"],
                "end_timestamp": last["timestamp"],
                "confirmation_timestamp": row["timestamp"],
                "direction": direction,
                "green_volume": green,
                "red_volume": red,
                "neutral_volume": neutral,
                "dominance": dominance,
                "bar_count": len(island),
                "open": float(first["open"]),
                "high": float(island["high"].max()),
                "low": float(island["low"].min()),
                "close": float(last["close"]),
                "island_move_pct": move * 100,
                "island_range": float(island["high"].max() - island["low"].min()),
                "atr": atr,
            }
        )
    return pd.DataFrame(records)


def evaluate_islands(
    frame: pd.DataFrame, islands: pd.DataFrame, config: IslandConfig | None = None
) -> pd.DataFrame:
    """Attach causal forward MFE/MAE and correction observations."""
    config = config or IslandConfig()
    prepared = prepare_volume_islands(frame, config)
    rows: list[dict[str, object]] = []
    for event in islands.to_dict("records"):
        entry_index = int(event["confirmation_index"]) + 1
        for horizon in config.horizons:
            future = prepared.iloc[entry_index : entry_index + horizon]
            if future.empty:
                continue
            direction = int(event["direction"])
            entry = float(future.iloc[0]["open"])
            favourable_high = future["high"] if direction == 1 else future["low"]
            adverse_low = future["low"] if direction == 1 else future["high"]
            mfe = direction * (float(favourable_high.max()) / entry - 1) * 100
            mae = direction * (float(adverse_low.min()) / entry - 1) * 100
            correction = max(0.0, -mae)
            island_move_pct = abs(float(event["island_move_pct"]))
            island_range_pct = float(event["island_range"]) / entry * 100
            rows.append(
                {
                    **event,
                    "entry_index": entry_index,
                    "entry": entry,
                    "horizon": horizon,
                    "mfe_pct": mfe,
                    "mae_pct": mae,
                    "correction_pct": correction,
                    "correction_of_island_move_pct": (
                        correction / island_move_pct * 100 if island_move_pct > 0 else np.nan
                    ),
                    "correction_of_island_range_pct": (
                        correction / island_range_pct * 100 if island_range_pct > 0 else np.nan
                    ),
                    "correction_atr": (
                        correction / 100 * entry / float(event["atr"])
                        if np.isfinite(event["atr"]) and float(event["atr"]) > 0
                        else np.nan
                    ),
                    "end_close": float(future.iloc[-1]["close"]),
                    "net_change_pct": direction * (float(future.iloc[-1]["close"]) / entry - 1) * 100,
                    "future_bars": len(future),
                }
            )
    return pd.DataFrame(rows)


def summarize_islands(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate event outcomes without selecting a parameter set."""
    if events.empty:
        return pd.DataFrame(columns=["horizon", "events", "mean_net_change_pct", "median_correction_pct", "continuation_rate"])
    return events.groupby("horizon", as_index=False).agg(
        events=("horizon", "size"),
        mean_net_change_pct=("net_change_pct", "mean"),
        median_correction_pct=("correction_pct", "median"),
        median_correction_atr=("correction_atr", "median"),
        continuation_rate=("net_change_pct", lambda values: float((values > 0).mean())),
        mean_mfe_pct=("mfe_pct", "mean"),
        mean_mae_pct=("mae_pct", "mean"),
    )


def evaluate_pullback_entries(
    frame: pd.DataFrame,
    islands: pd.DataFrame,
    config: IslandConfig | None = None,
    levels: tuple[float, ...] = (0.382, 0.500, 0.618),
    horizon: int = 4,
) -> pd.DataFrame:
    """Evaluate first causal pullback entries into the island range.

    A level is considered filled when a future candle reaches it. The entry is
    the level itself, with no claim that a fill is possible if price gaps past
    it; such gaps are recorded and excluded from the fill sample.
    """
    config = config or IslandConfig()
    prepared = prepare_volume_islands(frame, config)
    rows: list[dict[str, object]] = []
    for event in islands.to_dict("records"):
        direction = int(event["direction"])
        low, high = float(event["low"]), float(event["high"])
        width = high - low
        if width <= 0:
            continue
        start = int(event["confirmation_index"]) + 1
        for level in levels:
            price = high - level * width if direction == 1 else low + level * width
            future = prepared.iloc[start:]
            if future.empty:
                continue
            from_side = future["open"] >= price if direction == 1 else future["open"] <= price
            touched = future.index[
                from_side & (future["low"] <= price) & (future["high"] >= price)
            ]
            if len(touched) == 0:
                continue
            entry_index = int(touched[0])
            after = prepared.iloc[entry_index : entry_index + horizon]
            if after.empty:
                continue
            favourable = after["high"] if direction == 1 else after["low"]
            adverse = after["low"] if direction == 1 else after["high"]
            rows.append(
                {
                    **event,
                    "pullback_level": level,
                    "entry_index": entry_index,
                    "entry": price,
                    "bars_to_fill": entry_index - start,
                    "mfe_pct": direction * (float(favourable.max()) / price - 1) * 100,
                    "mae_pct": direction * (float(adverse.min()) / price - 1) * 100,
                    "net_change_pct": direction * (float(after.iloc[-1]["close"]) / price - 1) * 100,
                    "future_bars": len(after),
                    "horizon": horizon,
                }
            )
    return pd.DataFrame(rows)
