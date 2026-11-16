import numpy as np
import pandas as pd
import pytest

from app.lstm_features import (
    FEATURE_COLUMNS,
    candle_features,
    chronological_boundaries,
    FeatureScaler,
    make_sequence_partition,
    make_lstm_dataset,
    walk_forward_splits,
)


def candles(n=100):
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    close = 100 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {"open": close - 0.2, "high": close + 1, "low": close - 1,
         "close": close, "volume": np.linspace(100, 200, n)}, index=index
    )


def test_features_have_ten_columns_and_are_causal():
    frame = candles()
    first = candle_features(frame.iloc[:80])
    changed = frame.copy()
    changed.iloc[80:, changed.columns.get_loc("close")] = 1_000_000
    changed.iloc[80:, changed.columns.get_loc("high")] = 1_000_000
    second = candle_features(changed)
    pd.testing.assert_frame_equal(first, second.iloc[:80])
    assert list(first.columns) == list(FEATURE_COLUMNS)
    assert len(FEATURE_COLUMNS) == 10


def test_dataset_shape_and_train_only_scaler():
    frame = candles(140)
    X, y, decision_timestamps, outcome_timestamps, scaler = make_lstm_dataset(
        frame, sequence_length=20, horizon=5, train_end=90
    )
    assert X.ndim == 3 and X.shape[1:] == (20, 10)
    assert len(X) == len(y) == len(decision_timestamps) == len(outcome_timestamps)
    assert decision_timestamps[0] < outcome_timestamps[0]
    assert np.isfinite(X).all()
    expected_mean = np.nanmean(candle_features(frame).iloc[:90].to_numpy(), axis=0)
    np.testing.assert_allclose(scaler.mean, expected_mean)


def test_sequence_partition_excludes_only_outcomes_crossing_moscow_ex_date():
    frame = candles(100)
    frame.index = pd.date_range("2024-07-10 09:00", periods=100, freq="h")
    scaler = FeatureScaler.fit(candle_features(frame).iloc[:70])
    cutoff = "2024-07-13"
    partition = make_sequence_partition(
        frame, feature_start=0, decision_start=20, decision_end=70,
        sequence_length=20, horizon=5, scaler=scaler,
        excluded_outcome_dates=[cutoff],
    )

    baseline = make_sequence_partition(
        frame, feature_start=0, decision_start=20, decision_end=70,
        sequence_length=20, horizon=5, scaler=scaler,
    )
    kept = set(partition.decision_timestamps)
    expected_excluded = {
        decision for decision, outcome in zip(baseline.decision_timestamps, baseline.outcome_timestamps)
        if decision.tz_localize("UTC").tz_convert("Europe/Moscow").date()
        < pd.Timestamp(cutoff).date()
        <= outcome.tz_localize("UTC").tz_convert("Europe/Moscow").date()
    }
    assert set(baseline.decision_timestamps) - kept == expected_excluded
    assert expected_excluded


def test_invalid_dataset_parameters_fail():
    with pytest.raises(ValueError, match="train_end"):
        make_lstm_dataset(candles(), train_end=0)


def test_flat_candles_do_not_invalidate_feature_windows():
    frame = candles(140)
    frame.loc[frame.index[60], ["open", "high", "low", "close"]] = 100.0
    features = candle_features(frame)
    assert np.isfinite(features.iloc[61:].to_numpy()).all()


def test_flat_price_window_has_neutral_rsi():
    frame = candles(80)
    frame.loc[:, ["open", "high", "low", "close"]] = 100.0
    features = candle_features(frame)
    assert (features["rsi_14"].iloc[20:] == 0.5).all()


def test_rsi_rising_and_falling_prices():
    frame = candles(80)
    assert (candle_features(frame)["rsi_14"].iloc[20:] == 1.0).all()
    falling = frame.iloc[::-1].copy()
    falling.index = frame.index
    assert (candle_features(falling)["rsi_14"].iloc[20:] == 0.0).all()


@pytest.mark.parametrize("mutator", [
    lambda frame: frame.rename(index={frame.index[2]: frame.index[1]}),
    lambda frame: frame.iloc[::-1],
    lambda frame: frame.assign(volume=-1.0),
    lambda frame: frame.assign(high=frame["close"] - 1.0),
])
def test_invalid_candles_are_rejected(mutator):
    with pytest.raises(ValueError):
        candle_features(mutator(candles()))


def test_walk_forward_splits_by_decision_time_and_purges_train_labels():
    frame = candles(240)
    splits = walk_forward_splits(
        frame, train_bars=100, test_bars=30, sequence_length=20, horizon=5
    )
    split = splits[0]
    assert split.test_decision_timestamps[0] >= frame.index[100]
    assert split.test_timestamps[0] > split.test_decision_timestamps[0]
    # The train labels must finish before the decision boundary at row 100.
    assert len(split.train_y) == 56


def test_chronological_boundaries_are_contiguous_and_non_overlapping():
    frame = candles(240)
    boundaries = chronological_boundaries(
        frame, train_bars=100, validation_bars=30, test_bars=40, forward_bars=20
    )
    assert boundaries.train == (0, 100)
    assert boundaries.validation == (100, 130)
    assert boundaries.test == (130, 170)
    assert boundaries.forward == (170, 190)
    assert boundaries.train[1] == boundaries.validation[0]
    assert boundaries.validation[1] == boundaries.test[0]
    assert boundaries.test[1] == boundaries.forward[0]


def test_chronological_boundaries_reject_invalid_sizes():
    with pytest.raises(ValueError):
        chronological_boundaries(
            candles(100), train_bars=50, validation_bars=20,
            test_bars=20, forward_bars=20,
        )
    with pytest.raises(ValueError):
        chronological_boundaries(
            candles(120), train_bars=50, validation_bars=0,
            test_bars=20, forward_bars=20,
        )


def test_walk_forward_rejects_overlapping_test_folds():
    with pytest.raises(ValueError, match="overlapping"):
        walk_forward_splits(
            candles(240), train_bars=100, test_bars=30,
            sequence_length=20, horizon=5, step=10,
        )


def test_sequence_partition_keeps_outcomes_inside_decision_range():
    frame = candles(240)
    raw = candle_features(frame)
    scaler = FeatureScaler.fit(raw.iloc[:100])
    partition = make_sequence_partition(
        frame, feature_start=0, decision_start=100, decision_end=140,
        sequence_length=20, horizon=5, scaler=scaler,
    )
    assert partition.decision_timestamps[0] >= frame.index[100]
    assert partition.outcome_timestamps[-1] < frame.index[140]
    assert len(partition.X) == len(partition.y) == len(partition.decision_timestamps)


def test_walk_forward_is_chronological_and_scaler_uses_train_prefix():
    frame = candles(220)
    splits = walk_forward_splits(
        frame, train_bars=100, test_bars=30, sequence_length=20, horizon=5
    )
    assert len(splits) >= 2
    for split in splits:
        assert split.train_start < split.train_end <= split.test_end
        assert split.test_timestamps.is_monotonic_increasing
        train_features = candle_features(frame).iloc[split.train_start:split.train_end]
        np.testing.assert_allclose(
            split.scaler.mean, np.nanmean(train_features.to_numpy(), axis=0)
        )
    assert splits[0].test_timestamps[-1] < splits[1].test_timestamps[0]
