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
from .market_data import aggregate_bar_market_data


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
    market_data_status: Literal["OHLCV_ONLY", "TRADE_FLOW", "L2", "TRADE_FLOW_L2"] = "OHLCV_ONLY"
    trade_flow_coverage: float = Field(ge=0, le=1)
    delta: float | None = None
    book_imbalance: float | None = None
    book_spread_rate: float | None = None


class DynamicScenario(BaseModel):
    id: Literal["BREAKOUT", "BOUNCE"]
    title: str
    probability: float = Field(ge=0, le=1)
    recommended_entry: float = Field(gt=0)
    recommended_sl: float = Field(gt=0)
    recommended_tp: float = Field(gt=0)
    historical_win_rate: float = Field(ge=0, le=1)
    historical_samples_count: int = Field(ge=0)
    confidence_low: float = Field(ge=0, le=1)
    confidence_high: float = Field(ge=0, le=1)
    sample_warning: Literal["OK", "LOW_SAMPLE", "NO_DATA"]
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


@dataclass(frozen=True)
class NearestStats:
    win_rate: float
    samples: int
    confidence_low: float
    confidence_high: float
    warning: Literal["OK", "LOW_SAMPLE", "NO_DATA"]


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


def _load_records(
    db_path: str | Path,
    ticker: str,
    scenario: str,
    before: pd.Timestamp | None = None,
) -> list[tuple[np.ndarray, bool, pd.Timestamp]]:
    import json

    query = "SELECT feature_json, success, pattern_ts FROM adaptive_patterns WHERE ticker = ? AND scenario = ? AND success IS NOT NULL"
    params: list[object] = [ticker.upper(), scenario]
    if before is not None:
        query += " AND pattern_ts < ?"
        params.append(str(before))
    with _connect(db_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [(
        np.asarray(json.loads(row["feature_json"]), dtype=float),
        bool(row["success"]),
        pd.Timestamp(row["pattern_ts"]),
    ) for row in rows]


def _wilson_interval(successes: float, effective_n: float, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson interval for weighted Bernoulli observations."""
    if effective_n <= 0:
        return 0.0, 1.0
    p = successes / effective_n
    denominator = 1.0 + z * z / effective_n
    center = (p + z * z / (2.0 * effective_n)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / effective_n + z * z / (4.0 * effective_n * effective_n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _nearest_stats(
    db_path: str | Path,
    ticker: str,
    scenario: Literal["BREAKOUT", "BOUNCE"],
    vector: tuple[float, ...],
    k: int = 50,
    before: pd.Timestamp | None = None,
) -> NearestStats:
    records = _load_records(db_path, ticker, scenario, before=before)
    if not records:
        return NearestStats(0.5, 0, 0.0, 1.0, "NO_DATA")
    target = np.asarray(vector, dtype=float)
    matrix = np.vstack([features for features, _, _ in records])
    median = np.median(matrix, axis=0)
    scale = np.subtract(*np.percentile(matrix, [75, 25], axis=0))
    scale = np.where(scale > 1e-12, scale, 1.0)
    normalized_target = (target - median) / scale
    normalized_matrix = (matrix - median) / scale
    distances = sorted(
        (float(np.linalg.norm(features - normalized_target)), success, timestamp)
        for features, (_, success, timestamp) in zip(normalized_matrix, records)
    )
    nearest = distances[: min(k, len(distances))]
    as_of = max(timestamp for _, _, timestamp in nearest)
    half_life_days = 180.0
    weights = np.asarray([
        math.exp(-math.log(2.0) * max(0.0, (as_of - timestamp).total_seconds()) / (half_life_days * 86400.0))
        for _, _, timestamp in nearest
    ])
    successes = float(sum(weight for weight, (_, success, _) in zip(weights, nearest) if success))
    effective_n = float(weights.sum() ** 2 / max(np.square(weights).sum(), 1e-12))
    rate = successes / max(weights.sum(), 1e-12)
    low, high = _wilson_interval(successes, effective_n)
    warning: Literal["OK", "LOW_SAMPLE", "NO_DATA"] = "OK" if effective_n >= 30 else "LOW_SAMPLE"
    return NearestStats(rate, len(nearest), low, high, warning)


def build_live_context(
    frame: pd.DataFrame,
    ticker: str = "T",
    db_path: str | Path | None = None,
) -> LiveChartContext | None:
    """Build a deterministic context from the last closed 15m bar."""
    prepared = prepare_strategy_frame(frame, StrategyConfig())
    if prepared.empty:
        return None
    row = prepared.iloc[-1]
    vector = _feature_vector(prepared, len(prepared) - 1)
    if vector is None:
        return None
    aggregate = None
    if db_path is not None:
        aggregate = aggregate_bar_market_data(
            db_path, ticker, pd.Timestamp(row["timestamp"]).to_pydatetime(),
            candle_volume=float(row["volume"]),
        )
    flow_ready = bool(aggregate and aggregate.coverage >= 0.80 and not aggregate.stale)
    book_ready = bool(aggregate and aggregate.book_imbalance is not None and not aggregate.stale)
    market_status = "TRADE_FLOW_L2" if flow_ready and book_ready else "TRADE_FLOW" if flow_ready else "L2" if book_ready else "OHLCV_ONLY"
    return LiveChartContext(
        ticker=ticker.upper(), current_price=float(row["close"]),
        nearest_level_price=float(prepared.iloc[-20:]["low"].min()), level_type="HORIZONTAL",
        touches_count=0, current_atr=float(row["atr"]), volume_surge_ratio=float(row["volume_ratio"]),
        volatility_compression_score=float(np.clip(vector[2], 0, 1)),
        market_data_status=market_status,
        trade_flow_coverage=float(aggregate.coverage if aggregate else 0.0),
        delta=float(aggregate.delta) if flow_ready else None,
        book_imbalance=float(aggregate.book_imbalance) if book_ready else None,
        book_spread_rate=float(aggregate.spread_rate) if book_ready and aggregate.spread_rate is not None else None,
    )


def generate_forecast(
    frame: pd.DataFrame,
    db_path: str | Path,
    *,
    ticker: str = "T",
    current_position: dict[str, float] | None = None,
) -> ContextAwareForecastResponse:
    prepared = prepare_strategy_frame(frame, StrategyConfig())
    context = build_live_context(prepared, ticker, db_path)
    if context is None:
        raise ValueError("insufficient valid closed bars for adaptive context")
    vector = _feature_vector(prepared, len(prepared) - 1)
    assert vector is not None
    atr = context.current_atr
    entry = context.current_price
    base_time = int(pd.Timestamp(prepared.iloc[-1]["timestamp"]).timestamp())
    before = pd.Timestamp(prepared.iloc[-1]["timestamp"])
    scenarios: list[DynamicScenario] = []
    probabilities: dict[str, float] = {}
    for scenario_id, title in (("BREAKOUT", "Импульсный пробой"), ("BOUNCE", "Отскок от уровня")):
        stats = _nearest_stats(db_path, ticker, scenario_id, vector, before=before)
        probabilities[scenario_id] = stats.win_rate
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
        stats = _nearest_stats(db_path, ticker, scenario_id, vector, before=before)
        scenarios.append(DynamicScenario(
            id=scenario_id, title=title, probability=probability,
            recommended_entry=entry, recommended_sl=stop, recommended_tp=target,
            historical_win_rate=stats.win_rate,
            historical_samples_count=stats.samples,
            confidence_low=stats.confidence_low,
            confidence_high=stats.confidence_high,
            sample_warning=stats.warning,
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
