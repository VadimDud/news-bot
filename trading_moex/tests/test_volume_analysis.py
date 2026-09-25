from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.volume_analysis import (
    AnalysisConfig,
    add_fibonacci_features,
    analyze_events,
    load_candles,
    prepare_candles,
)
from app.vsa_fibonacci import VSAConfig, analyze_fibonacci_cycles, analyze_vsa_events, prepare_vsa


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


def test_fibonacci_features_use_only_confirmed_pivots() -> None:
    rows = []
    for index in range(40):
        close = 100 + (index % 12) if index < 24 else 112 - (index - 24)
        rows.append((close, close + 1, close - 1, close, 10))
    frame = prepare_candles(make_frame(rows), AnalysisConfig(atr_period=3))
    fib = add_fibonacci_features(frame, swing_bars=2)

    assert fib["fib_valid"].any()
    assert set(fib["fib_context"].dropna().unique()) <= {
        "Golden zone 50-61.8%",
        "Near Fib level",
        "Valid swing, away from level",
        "No confirmed swing",
    }
    # A pivot at bar j cannot affect a Fib context before j + swing_bars.
    assert fib.loc[0, "fib_context"] == "No confirmed swing"


def test_vsa_categories_and_forward_metrics() -> None:
    rows = [(100, 101, 99, 100, 10)] * 20
    rows.extend(
        [
            (100, 100.3, 99.7, 100.1, 100),  # absorption
            (100.1, 100.2, 98.0, 100.2, 100),  # lower rejection
            (100.2, 105.0, 99.8, 104.8, 100),  # momentum after anomaly
            (104.8, 106, 104, 105.5, 10),
            (105.5, 107, 105, 106.5, 10),
            (106.5, 108, 106, 107.5, 10),
            (107.5, 109, 107, 108.5, 10),
            (108.5, 110, 108, 109.5, 10),
            (109.5, 111, 109, 110.5, 10),
            (110.5, 112, 110, 111.5, 10),
            (111.5, 113, 111, 112.5, 10),
        ]
    )
    frame = make_frame(rows)
    config = VSAConfig(volume_window=20, atr_period=3)
    prepared = prepare_vsa(frame, config)
    events = analyze_vsa_events(frame, config)

    assert prepared.iloc[20]["anomaly_type"] == "Absorption / stopping volume"
    assert prepared.iloc[21]["anomaly_type"] == "Rejection / liquidity sweep"
    assert prepared.iloc[22]["anomaly_type"] == "Trend climax / pure momentum"
    assert len(events) == 3
    assert events.iloc[0]["flat_4"] == 0
    assert events.iloc[0]["mfe_pct_1"] >= 0


def test_fibonacci_cycles_capture_exact_counts() -> None:
    closes = [100, 101, 102, 103, 104, 105, 104, 103, 104, 105, 106, 107]
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=len(closes), freq="15min"),
            "open": closes,
            "high": [value + 0.2 for value in closes],
            "low": [value - 0.2 for value in closes],
            "close": closes,
            "volume": [10] * len(closes),
        }
    )
    cycles = analyze_fibonacci_cycles(frame, VSAConfig())
    assert not cycles.empty
    assert ((cycles["impulse_length"] == 5) & (cycles["correction_length"] == 2)).any()
