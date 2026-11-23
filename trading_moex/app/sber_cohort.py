"""Read-only, exclusion-aware sequence preparation for the new SBER cohort."""
from contextlib import closing
from pathlib import Path
import sqlite3

import pandas as pd

from app.lstm_features import make_sequence_partition


def cohort_partitions(database: Path, period: str, *, scaler, excluded_outcome_dates=()):
    """Yield independent labeled segments using a scaler fitted on separate history."""
    horizon = {'5min': 15, '15min': 5}[period]
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        frame = pd.read_sql_query(
            'SELECT begin AS timestamp,o AS open,h AS high,l AS low,c AS close,v AS volume '
            'FROM bars WHERE period=? ORDER BY begin', db, params=(period,),
            parse_dates=['timestamp'], index_col='timestamp')
        excluded = pd.DatetimeIndex([r[0] for r in db.execute(
            'SELECT begin FROM exclusions WHERE period=? ORDER BY begin', (period,))])
    if not frame.index.intersection(excluded).empty:
        raise ValueError('excluded candle present in accepted bars')
    # Split on recorded exclusions, not elapsed wall time (session breaks are normal).
    for _, segment in frame.groupby(excluded.searchsorted(frame.index)):
        try:
            part = make_sequence_partition(segment, feature_start=0, decision_start=0,
                decision_end=len(segment), sequence_length=50, horizon=horizon,
                threshold=.003, cost_rate=.001, scaler=scaler,
                excluded_outcome_dates=excluded_outcome_dates)
        except ValueError as exc:
            if str(exc) != 'no complete finite samples in sequence partition':
                raise
            continue
        yield part
