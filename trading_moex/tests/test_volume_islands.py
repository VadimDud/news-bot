from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.volume_islands import (  # noqa: E402
    IslandConfig,
    detect_islands,
    evaluate_islands,
    prepare_volume_islands,
    evaluate_pullback_entries,
)


def make_frame(volumes: list[float], closes: list[float]) -> pd.DataFrame:
    opens = [value - 1 for value in closes]
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=len(closes), freq="4h"),
            "open": opens,
            "high": [value + 1 for value in closes],
            "low": [value - 2 for value in opens],
            "close": closes,
            "volume": volumes,
        }
    )


def test_volume_baseline_excludes_current_bar() -> None:
    frame = make_frame([10] * 20 + [100], [100 + i for i in range(21)])
    prepared = prepare_volume_islands(frame, IslandConfig(volume_window=20))

    assert prepared.iloc[-1]["volume_baseline"] == pytest.approx(10)
    assert prepared.iloc[-1]["volume_ratio"] == pytest.approx(10)


def test_island_is_confirmed_by_separator_and_not_separator_itself() -> None:
    # The first 20 bars establish the causal threshold. Bars 20 and 21 form the
    # island; bar 22 confirms it and must not be included in its OHLCV totals.
    volumes = [10] * 20 + [100, 100, 1, 100]
    closes = [100] * 20 + [101, 102, 102, 103]
    frame = make_frame(volumes, closes)
    config = IslandConfig(volume_window=20, separator_quantile=0.2, min_length=2)

    islands = detect_islands(frame, config)

    assert len(islands) == 1
    island = islands.iloc[0]
    assert island["start_index"] == 20
    assert island["end_index"] == 21
    assert island["confirmation_index"] == 22
    assert island["bar_count"] == 2
    assert island["green_volume"] == 200
    assert island["close"] == 102


def test_evaluation_starts_after_confirmation_and_reports_directional_metrics() -> None:
    volumes = [10] * 20 + [100, 100, 1, 100, 100]
    closes = [100] * 20 + [101, 102, 102, 104, 105]
    frame = make_frame(volumes, closes)
    config = IslandConfig(volume_window=20, horizons=(1, 2))
    islands = detect_islands(frame, config)
    events = evaluate_islands(frame, islands, config)

    assert set(events["entry_index"]) == {23}
    one_bar = events.loc[events["horizon"] == 1].iloc[0]
    assert one_bar["entry"] == 103
    assert one_bar["net_change_pct"] > 0
    assert one_bar["mfe_pct"] > 0
    assert one_bar["correction_of_island_range_pct"] >= 0


def test_future_bars_cannot_change_prior_island_detection() -> None:
    volumes = [10] * 20 + [100, 100, 1, 100, 100]
    closes = [100] * 20 + [101, 102, 102, 104, 105]
    frame = make_frame(volumes, closes)
    config = IslandConfig(volume_window=20)
    baseline = detect_islands(frame, config)

    mutated = frame.copy()
    mutated.loc[23:, "volume"] = 1_000_000
    mutated.loc[23:, "close"] = 1
    changed = detect_islands(mutated, config)

    assert baseline.iloc[0]["start_index"] == changed.iloc[0]["start_index"]
    assert baseline.iloc[0]["confirmation_index"] == changed.iloc[0]["confirmation_index"]


def test_placebo_directions_keep_volume_features_unchanged() -> None:
    frame = make_frame([10] * 20 + [100, 100, 1, 100], [100] * 20 + [101, 102, 102, 103])
    config = IslandConfig(volume_window=20)
    directions = pd.Series([-1] * len(frame))
    prepared = prepare_volume_islands(frame, config, directions)

    assert prepared["volume"].tolist() == frame["volume"].tolist()
    assert prepared["separator_threshold"].equals(
        prepare_volume_islands(frame, config)["separator_threshold"]
    )
    assert prepared["direction"].eq(-1).all()


def test_pullback_entry_uses_first_touch_and_directional_return() -> None:
    volumes = [10] * 20 + [100, 100, 1, 100, 100, 100]
    closes = [100] * 20 + [110, 120, 120, 115, 125, 130]
    frame = make_frame(volumes, closes)
    config = IslandConfig(volume_window=20, horizons=(1, 2))
    islands = detect_islands(frame, config)
    entries = evaluate_pullback_entries(frame, islands, config, levels=(0.5,))

    assert len(entries) == 1
    assert entries.iloc[0]["entry"] == pytest.approx(114.0)
    assert entries.iloc[0]["entry_index"] == 23
    assert entries.iloc[0]["mfe_pct"] > 0


def test_pullback_gap_through_level_is_not_a_fill() -> None:
    volumes = [10] * 20 + [100, 100, 1, 100]
    closes = [100] * 20 + [110, 120, 120, 100]
    frame = make_frame(volumes, closes)
    config = IslandConfig(volume_window=20, horizons=(4,))
    islands = detect_islands(frame, config)

    assert evaluate_pullback_entries(frame, islands, config, levels=(0.5,)).empty
