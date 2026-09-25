from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from app.adaptive_scenarios import (
    ManeuverRequest,
    build_live_context,
    extract_pattern_records,
    generate_forecast,
    store_pattern_records,
    validate_maneuver,
)
from app.adaptive_scenarios import NearestStats, _nearest_stats
from app.vsa_strategy import StrategyConfig


def _frame(rows: int = 80) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01 10:00", periods=rows, freq="15min")
    close = [100 + i * 0.05 for i in range(rows)]
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": close,
        "high": [value + 0.2 for value in close],
        "low": [value - 0.2 for value in close],
        "close": close,
        "volume": [10.0] * rows,
    })


def test_pattern_store_creates_local_database_and_is_idempotent(tmp_path) -> None:
    records = extract_pattern_records(_frame(80), ticker="T", config=StrategyConfig())
    db_path = tmp_path / "adaptive.db"

    assert store_pattern_records(db_path, records) == len(records)
    assert store_pattern_records(db_path, records) == len(records)
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM adaptive_patterns").fetchone()[0] == len(records)


def test_forecast_is_rejected_when_closed_bar_context_is_insufficient(tmp_path) -> None:
    with pytest.raises(ValueError, match="insufficient"):
        generate_forecast(_frame(10), tmp_path / "adaptive.db")


def test_maneuver_is_dry_run_and_requires_two_to_one_rr() -> None:
    payload = ManeuverRequest(
        ticker="T", direction="LONG", entry_price=100, current_price=102,
        new_stop_loss=98, new_take_profit=105, quantity=10, dry_run=True,
    )
    result = validate_maneuver(payload)

    assert result["status"] == "DRY_RUN_VALIDATED"
    assert result["broker_action"] is None

    with pytest.raises(ValueError, match="risk/reward"):
        validate_maneuver(payload.model_copy(update={"new_take_profit": 103}))


def test_long_maneuver_rejects_stop_above_current_price() -> None:
    with pytest.raises(ValueError, match="below current price"):
        ManeuverRequest(
            ticker="T", direction="LONG", entry_price=100, current_price=102,
            new_stop_loss=103, new_take_profit=110, quantity=1,
        )


def test_nearest_stats_normalizes_features_and_reports_low_sample(tmp_path) -> None:
    records = []
    for index, volume_ratio in enumerate((2.0, 2.1, 2.2, 2.3)):
        records.append({
            "ticker": "T", "pattern_ts": f"2026-01-01 10:{index:02d}:00",
            "scenario": "BREAKOUT", "feature_json": f"[{volume_ratio}, 0, 0, 0, 0, 0]",
            "success": 1 if index < 3 else 0,
        })
    db_path = tmp_path / "stats.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE adaptive_patterns (
                id INTEGER PRIMARY KEY, ticker TEXT, pattern_ts TEXT, scenario TEXT,
                feature_json TEXT, forward_return_1 REAL, forward_return_3 REAL,
                forward_return_5 REAL, forward_return_8 REAL, success INTEGER
            )
        """)
        connection.executemany(
            "INSERT INTO adaptive_patterns (ticker, pattern_ts, scenario, feature_json, success) VALUES (:ticker, :pattern_ts, :scenario, :feature_json, :success)",
            records,
        )
    stats = _nearest_stats(db_path, "T", "BREAKOUT", (2.25, 0, 0, 0, 0, 0), k=4)

    assert isinstance(stats, NearestStats)
    assert stats.samples == 4
    assert stats.warning == "LOW_SAMPLE"
    assert 0 <= stats.confidence_low <= stats.win_rate <= stats.confidence_high <= 1


def test_nearest_stats_excludes_future_patterns(tmp_path) -> None:
    db_path = tmp_path / "future.db"
    records = extract_pattern_records(_frame(80), ticker="T", config=StrategyConfig())
    store_pattern_records(db_path, records)

    stats = _nearest_stats(
        db_path, "T", "BREAKOUT", (0.01, 2.5, 0.5, 0.5, 0.5, 1.0),
        before=pd.Timestamp("2020-01-01"),
    )

    assert stats.warning == "NO_DATA"
    assert stats.samples == 0
