from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.volume_analysis import AnalysisConfig, analyze_events, load_candles, prepare_candles


def make_frame(rows: list[tuple[float, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["open", "high", "low", "close", "volume"],
    ).assign(timestamp=pd.date_range("2026-01-01 10:00", periods=len(rows), freq="15min"))[
        ["timestamp", "open", "high", "low", "close", "volume"]
    ]


def test_prepare_candles_excludes_current_volume_from_sma() -> None:
    rows = [(100, 101, 99, 100, 10)] * 21
    rows.append((100, 106, 99, 105, 100))
    frame = prepare_candles(
        make_frame(rows),
        AnalysisConfig(volume_sma_window=20, zscore_window=5, atr_period=3),
    )

    signal = frame.iloc[-1]
    assert signal["volume_sma"] == 10
    assert signal["volume_ratio"] == 10
    assert signal["body_ratio"] == 5 / 7
    assert signal["direction"] == "Bullish"


def test_analyze_events_classifies_true_breakout_and_forward_returns() -> None:
    rows = [(100, 101, 99, 100, 10)] * 22
    rows.extend(
        [
            (100, 106, 99, 105, 100),
            (105, 110, 104, 107, 10),
            (107, 110, 106, 109, 10),
            (109, 111, 108, 110, 10),
            (110, 112, 109, 111, 10),
        ]
    )
    events = analyze_events(
        make_frame(rows),
        AnalysisConfig(volume_sma_window=20, zscore_window=5, atr_period=3),
    )

    event = events.iloc[0]
    assert event["reaction"] == "Impulse / continuation"
    assert event["outcome_status"] == "True breakout"
    assert event["outcome_group"] == "continuation"
    assert event["future_bars"] == 4
    assert event["net_change_15m_pct"] > 0
    assert event["mfe_pct"] > 0


def test_analyze_events_classifies_reversal_before_breakout() -> None:
    rows = [(100, 101, 99, 100, 10)] * 22
    rows.extend(
        [
            (100, 106, 99, 105, 100),
            (105, 106, 99, 98, 10),
            (98, 100, 97, 99, 10),
            (99, 101, 98, 100, 10),
            (100, 101, 99, 100, 10),
        ]
    )
    events = analyze_events(
        make_frame(rows),
        AnalysisConfig(volume_sma_window=20, zscore_window=5, atr_period=3),
    )

    assert events.iloc[0]["reaction"] == "Reversal"
    assert events.iloc[0]["outcome_group"] == "reversal"
    assert events.iloc[0]["outcome_status"] == "Liquidity sweep / reversal"


def test_doji_mfe_and_mae_are_positive_two_sided_extremes() -> None:
    rows = [(100, 101, 99, 100, 10)] * 22
    rows.extend(
        [
            (100, 102, 98, 100, 100),
            (100, 101, 99, 100, 10),
            (100, 101, 99, 100, 10),
            (100, 101, 99, 100, 10),
            (100, 101, 99, 100, 10),
        ]
    )
    events = analyze_events(
        make_frame(rows),
        AnalysisConfig(volume_sma_window=20, zscore_window=5, atr_period=3),
    )

    event = events.iloc[0]
    assert event["direction"] == "Doji"
    assert event["mfe_pct"] == pytest.approx(1.0)
    assert event["mae_pct"] == pytest.approx(1.0)


def test_load_candles_reads_selected_series_read_only(tmp_path) -> None:
    db_path = tmp_path / "trader.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS candles (ticker TEXT, period TEXT, begin TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
        )
        connection.executemany(
            "INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("T", "15min", "2026-01-01 10:15", 100, 101, 99, 100.5, 10),
                ("SBER", "15min", "2026-01-01 10:15", 200, 201, 199, 200.5, 20),
            ],
        )

    frame = load_candles(db_path, "T", "15min")
    assert len(frame) == 1
    assert frame.iloc[0]["close"] == 100.5
