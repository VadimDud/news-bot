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
