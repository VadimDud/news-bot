import sqlite3

import numpy as np
import pandas as pd
import pytest

from app.lstm_features import FeatureScaler, candle_features, make_sequence_partition
from app.sber_cohort import cohort_partitions


@pytest.mark.parametrize('period,horizon', [('5min', 15), ('15min', 5)])
def test_exclusions_reset_features_windows_and_labels(tmp_path, period, horizon):
    # Deliberate ordinary day break inside the first segment, no exclusion there.
    stamps = pd.date_range('2026-01-01', periods=241, freq=period)
    stamps = stamps[:80].append(stamps[80:] + pd.Timedelta(days=1))
    x = np.arange(len(stamps))
    prices = 100 + np.sin(x / 6) + (x > 120)*50
    frame = pd.DataFrame(dict(open=prices, close=prices, high=prices+1, low=prices-1,
                              volume=30+x%17), index=stamps)
    path = tmp_path / 'collection.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE bars(period,begin,o,h,l,c,v)')
        db.execute('CREATE TABLE exclusions(period,begin)')
        db.executemany('INSERT INTO bars VALUES(?,?,?,?,?,?,?)', [
            (period, str(t), r.open, r.high, r.low, r.close, r.volume)
            for t, r in frame.iterrows() if t != stamps[120]])
        db.execute('INSERT INTO exclusions VALUES(?,?)', (period, str(stamps[120])))
    scaler = FeatureScaler.fit(candle_features(frame.iloc[:100]))
    parts = list(cohort_partitions(path, period, scaler=scaler))
    assert len(parts) == 2
    for actual, segment in zip(parts, [frame.iloc[:120], frame.iloc[121:]]):
        expected = make_sequence_partition(segment, feature_start=0, decision_start=0,
            decision_end=len(segment), scaler=scaler, horizon=horizon, threshold=.003, cost_rate=.001)
        np.testing.assert_array_equal(actual.X, expected.X)
        np.testing.assert_array_equal(actual.y, expected.y)
        assert actual.decision_timestamps.equals(expected.decision_timestamps)
        assert actual.outcome_timestamps.equals(expected.outcome_timestamps)
