"""Causal adaptive scenarios and pattern statistics for the T 15m module.

The module is intentionally broker-free.  It stores completed pattern outcomes,
finds historical analogues using deterministic normalized Euclidean distance,
and returns recommendations that a separate execution layer may review.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, model_validator

from .vsa_strategy import StrategyConfig, prepare_strategy_frame


FEATURE_COLUMNS = (
    "atr_pct",
    "volume_ratio",
    "compression",
    "range_position",
    "body_ratio",
    "bars_in_range",
)


class PricePoint(BaseModel):
    time: int
    price: float


class LiveChartContext(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    timeframe: Literal["15min"] = "15min"
    current_price: float = Field(gt=0)
    nearest_level_price: float = Field(gt=0)
    level_type: Literal["HORIZONTAL", "VECTOR_TRENDLINE"]
    touches_count: int = Field(ge=0)
    current_atr: float = Field(gt=0)
    volume_surge_ratio: float = Field(ge=0)
    volatility_compression_score: float = Field(ge=0, le=1)


class DynamicScenario(BaseModel):
    id: Literal["BREAKOUT", "BOUNCE"]
    title: str
    probability: float = Field(ge=0, le=1)
    recommended_entry: float = Field(gt=0)
    recommended_sl: float = Field(gt=0)
    recommended_tp: float = Field(gt=0)
    historical_win_rate: float = Field(ge=0, le=1)
    historical_samples_count: int = Field(ge=0)
    projected_path: list[PricePoint]


class ContextAwareForecastResponse(BaseModel):
    timestamp: datetime
    context: LiveChartContext
    scenarios: list[DynamicScenario]
    suggested_maneuver: Literal["MOVE_TO_BREAKEVEN", "TRAIL_SL_BEHIND_FRACTAL"] | None = None


class ManeuverRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    direction: Literal["LONG"]
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    new_stop_loss: float = Field(gt=0)
    new_take_profit: float = Field(gt=0)
    quantity: int = Field(gt=0)
    active_stop_order_id: str | None = Field(default=None, max_length=128)
    dry_run: bool = True

    @model_validator(mode="after")
    def validate_long_bracket(self) -> "ManeuverRequest":
        if self.new_stop_loss >= self.current_price:
            raise ValueError("long stop must remain below current price")
        if self.new_stop_loss >= self.entry_price:
            raise ValueError("new stop cannot be at or above entry in this maneuver endpoint")
        if self.new_take_profit <= self.current_price:
            raise ValueError("take-profit must remain above current price")
        return self


@dataclass(frozen=True)
class PatternRecord:
    ticker: str
    timestamp: str
    scenario: Literal["BREAKOUT", "BOUNCE"]
    features: tuple[float, ...]
    forward_return_1: float | None
    forward_return_3: float | None
    forward_return_5: float | None
    forward_return_8: float | None
    success: bool | None


def _connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(path).expanduser())
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS adaptive_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            pattern_ts TEXT NOT NULL,
            scenario TEXT NOT NULL,
            feature_json TEXT NOT NULL,
            forward_return_1 REAL,
            forward_return_3 REAL,
            forward_return_5 REAL,
            forward_return_8 REAL,
            success INTEGER,
            UNIQUE(ticker, pattern_ts, scenario)
        )
        """
    )
    return connection


def _feature_vector(frame: pd.DataFrame, index: int) -> tuple[float, ...] | None:
    row = frame.iloc[index]
    atr = float(row["atr"]) if pd.notna(row["atr"]) else math.nan
    close = float(row["close"])
    if not np.isfinite(atr) or atr <= 0 or close <= 0:
        return None
    lookback = frame.iloc[max(0, index - 19): index + 1]
    range_high = float(lookback["high"].max())
    range_low = float(lookback["low"].min())
    range_width = range_high - range_low
    ranges = (lookback["high"] - lookback["low"]).to_numpy(float)
    compression = float(np.clip(np.mean(ranges[-5:]) / max(np.mean(ranges), 1e-12), 0, 1))
    values = (
        atr / close,
        float(row["volume_ratio"]),
        compression,
        (close - range_low) / range_width if range_width > 0 else 0.5,
        float(row["body_ratio"]),
        float((lookback["high"].cummax() - lookback["low"].cummin()).iloc[-1] / max(atr, 1e-12)),
    )
    if not np.isfinite(values).all():
        return None
    return tuple(float(value) for value in values)


def extract_pattern_records(
    frame: pd.DataFrame,
    *,
    ticker: str = "T",
    config: StrategyConfig | None = None,
) -> list[PatternRecord]:
    """Extract only closed bars and calculate outcomes from strictly later bars."""
    prepared = prepare_strategy_frame(frame, config)
    records: list[PatternRecord] = []
    for index, row in prepared.iterrows():
        category = str(row["vsa_category"])
        if category == "MOMENTUM":
            scenario: Literal["BREAKOUT", "BOUNCE"] = "BREAKOUT"
        elif category in {"ABSORPTION", "REJECTION"}:
            scenario = "BOUNCE"
        else:
            continue
        features = _feature_vector(prepared, index)
        if features is None:
            continue
        entry = float(row["close"])
        values: dict[int, float | None] = {}
        for horizon in (1, 3, 5, 8):
            future = prepared.iloc[index + 1:index + 1 + horizon]
            values[horizon] = (
                float(future.iloc[-1]["close"] / entry - 1.0) if len(future) == horizon else None
            )
        success = values[5] is not None and (
            values[5] > 0 if scenario == "BREAKOUT" else values[5] <= 0
        )
        records.append(PatternRecord(
            ticker=ticker.upper(), timestamp=str(pd.Timestamp(row["timestamp"])), scenario=scenario,
            features=features, forward_return_1=values[1], forward_return_3=values[3],
            forward_return_5=values[5], forward_return_8=values[8], success=success,
        ))
    return records


def store_pattern_records(db_path: str | Path, records: list[PatternRecord]) -> int:
    import json

    with _connect(db_path) as connection:
        if not records:
            return 0
        connection.executemany(
            """
            INSERT OR REPLACE INTO adaptive_patterns
            (ticker, pattern_ts, scenario, feature_json, forward_return_1,
             forward_return_3, forward_return_5, forward_return_8, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(
                record.ticker, record.timestamp, record.scenario, json.dumps(record.features),
                record.forward_return_1, record.forward_return_3, record.forward_return_5,
                record.forward_return_8, int(record.success) if record.success is not None else None,
            ) for record in records],
        )
        return len(records)


def _load_records(db_path: str | Path, ticker: str, scenario: str) -> list[tuple[np.ndarray, bool]]:
    import json

    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT feature_json, success FROM adaptive_patterns WHERE ticker = ? AND scenario = ? AND success IS NOT NULL",
            (ticker.upper(), scenario),
        ).fetchall()
    return [(np.asarray(json.loads(row["feature_json"]), dtype=float), bool(row["success"])) for row in rows]


def _nearest_stats(
    db_path: str | Path,
    ticker: str,
    scenario: Literal["BREAKOUT", "BOUNCE"],
    vector: tuple[float, ...],
    k: int = 50,
) -> tuple[float, int]:
    records = _load_records(db_path, ticker, scenario)
    if not records:
        return 0.5, 0
    target = np.asarray(vector, dtype=float)
    distances = sorted((float(np.linalg.norm(features - target)), success) for features, success in records)
    nearest = distances[: min(k, len(distances))]
    return float(np.mean([success for _, success in nearest])), len(nearest)


def build_live_context(frame: pd.DataFrame, ticker: str = "T") -> LiveChartContext | None:
    """Build a deterministic context from the last closed 15m bar."""
    prepared = prepare_strategy_frame(frame, StrategyConfig())
    if prepared.empty:
        return None
    row = prepared.iloc[-1]
    vector = _feature_vector(prepared, len(prepared) - 1)
    if vector is None:
        return None
    return LiveChartContext(
        ticker=ticker.upper(), current_price=float(row["close"]),
        nearest_level_price=float(prepared.iloc[-20:]["low"].min()), level_type="HORIZONTAL",
        touches_count=0, current_atr=float(row["atr"]), volume_surge_ratio=float(row["volume_ratio"]),
        volatility_compression_score=float(np.clip(vector[2], 0, 1)),
    )


def generate_forecast(
    frame: pd.DataFrame,
    db_path: str | Path,
    *,
    ticker: str = "T",
    current_position: dict[str, float] | None = None,
) -> ContextAwareForecastResponse:
    prepared = prepare_strategy_frame(frame, StrategyConfig())
    context = build_live_context(prepared, ticker)
    if context is None:
        raise ValueError("insufficient valid closed bars for adaptive context")
    vector = _feature_vector(prepared, len(prepared) - 1)
    assert vector is not None
    atr = context.current_atr
    entry = context.current_price
    base_time = int(pd.Timestamp(prepared.iloc[-1]["timestamp"]).timestamp())
    scenarios: list[DynamicScenario] = []
    probabilities: dict[str, float] = {}
    for scenario_id, title in (("BREAKOUT", "Импульсный пробой"), ("BOUNCE", "Отскок от уровня")):
        win_rate, samples = _nearest_stats(db_path, ticker, scenario_id, vector)
        prior = 0.5 if samples == 0 else win_rate
        if scenario_id == "BOUNCE":
            prior = 1.0 - prior if samples else 0.5
        probabilities[scenario_id] = prior
    total = sum(probabilities.values()) or 1.0
    for scenario_id, title in (("BREAKOUT", "Импульсный пробой"), ("BOUNCE", "Отскок от уровня")):
        probability = probabilities[scenario_id] / total
        if scenario_id == "BREAKOUT":
            stop = entry - 1.5 * atr
            target = entry + 2.5 * (entry - stop)
            path = [entry, entry + atr, target]
        else:
            stop = context.nearest_level_price - 0.25 * atr
            stop = min(stop, entry - 0.5 * atr)
            target = entry + 2.5 * (entry - stop)
            path = [entry, context.nearest_level_price, target]
        scenarios.append(DynamicScenario(
            id=scenario_id, title=title, probability=probability,
            recommended_entry=entry, recommended_sl=stop, recommended_tp=target,
            historical_win_rate=probabilities[scenario_id] if probabilities[scenario_id] else 0.5,
            historical_samples_count=_nearest_stats(db_path, ticker, scenario_id, vector)[1],
            projected_path=[PricePoint(time=base_time + i * 900, price=float(price)) for i, price in enumerate(path)],
        ))
    maneuver = None
    if current_position:
        position_entry = float(current_position["entry_price"])
        if context.current_price >= position_entry + 1.5 * atr:
            maneuver = "MOVE_TO_BREAKEVEN"
    return ContextAwareForecastResponse(
        timestamp=datetime.now(timezone.utc), context=context, scenarios=scenarios,
        suggested_maneuver=maneuver,
    )


def validate_maneuver(payload: ManeuverRequest) -> dict[str, object]:
    """Validate a UI maneuver and return a broker-neutral dry-run command."""
    risk = payload.entry_price - payload.new_stop_loss
    reward = payload.new_take_profit - payload.entry_price
    rr = reward / risk if risk > 0 else 0.0
    if rr < 2.0:
        raise ValueError("risk/reward must be at least 2.0")
    return {
        "status": "DRY_RUN_VALIDATED" if payload.dry_run else "REQUIRES_EXECUTION_ADAPTER",
        "ticker": payload.ticker.upper(), "direction": payload.direction,
        "quantity": payload.quantity, "stop_loss": payload.new_stop_loss,
        "take_profit": payload.new_take_profit, "risk_reward": round(rr, 4),
        "active_stop_order_id": payload.active_stop_order_id,
        "broker_action": None if payload.dry_run else "NOT_CONNECTED",
    }
