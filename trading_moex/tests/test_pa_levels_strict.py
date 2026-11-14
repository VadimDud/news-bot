from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from app.pa_levels import PALevelParams
from app.risk import atr
from scripts.backtest_pa_levels import simulate_trades
from scripts.pa_levels_strict import (StrictParams, completed_htf, generate_strict,
                                      strict_levels, strict_trend)


def setup(side=1):
    df = pd.DataFrame(dict(open=103., high=104., low=102., close=103., volume=100.),
                      index=pd.date_range('2024-01-01', periods=65))
    for i in (20, 30, 40):
        df.iloc[i] = [102, 103, 100, 102, 100]
    df.iloc[50] = [102, 103, 97, 98, 300]
    df.iloc[51] = [98, 102, 97.5, 101, 100]
    df.iloc[52] = [101, 101.4, 100.6, 101.1, 100]
    if side == -1:
        df[['open','high','low','close']] = 200-df[['open','low','high','close']].to_numpy()
    htf = pd.DataFrame(dict(close=100+side*np.arange(60),
        available_at=pd.date_range('2023-01-01', periods=60)))
    return df, htf


@pytest.mark.parametrize('side', [1, -1])
def test_sequence_and_frozen_breakout_stop(side):
    df, htf = setup(side)
    sig, counts, levels = generate_strict(df, htf)
    assert len(sig) == 1
    s = sig.iloc[0]
    assert (s.breakout_idx, s.return_idx, s.idx, s.touches) == (50, 51, 52, 3)
    assert s.stop == pytest.approx(100-side*3-side*.2*atr(df).iloc[49])
    assert s.target == pytest.approx(s.price+side*2*abs(s.price-s.stop))
    assert counts['impulses'] == counts['returned'] == counts['compressed'] == 1
    # A later return extreme does not move the stop if still inside its buffer.
    df.iloc[51, df.columns.get_loc('low' if side == 1 else 'high')] = 100-side*3.1
    changed, _, _ = generate_strict(df, htf)
    assert changed.iloc[0].stop == s.stop
    for cut in range(45, 66):
        small, _, snapshots = generate_strict(df.iloc[:cut], htf)
        pd.testing.assert_frame_equal(changed[changed.idx < cut].reset_index(drop=True), small, check_dtype=False)
        pd.testing.assert_frame_equal(strict_levels(df).query('known_idx < @cut').reset_index(drop=True), snapshots, check_dtype=False)


@pytest.mark.parametrize('mutation', ['impulse', 'volume', 'return_volume', 'late_return',
                                     'compression', 'recross', 'stop', 'htf', 'touches'])
def test_every_gate_fails_closed(mutation):
    df, htf = setup()
    p = StrictParams()
    if mutation == 'impulse':
        df.iloc[50, 0] = 98.2
    elif mutation == 'volume':
        df.iloc[50, 4] = 100
    elif mutation == 'return_volume':
        df.iloc[51, 4] = 300
    elif mutation == 'late_return':
        df.iloc[51:54, df.columns.get_loc('close')] = 99
    elif mutation == 'compression':
        df.iloc[52, df.columns.get_loc('high')] = 104
    elif mutation == 'recross':
        df.iloc[52, df.columns.get_loc('close')] = 99
    elif mutation == 'stop':
        df.iloc[51, df.columns.get_loc('low')] = 95
    elif mutation == 'htf':
        htf['close'] = 100-np.arange(60)
    else:
        p = replace(p, touches=4)
    assert generate_strict(df, htf, p)[0].empty


def test_no_pattern_or_return_bar_compression_bypass():
    df, htf = setup()
    # Return itself is compressed, but no later bar is compressed.
    df.iloc[51] = [100.5, 101.1, 100.2, 100.6, 100]
    df.iloc[52] = [101, 104, 100.6, 103, 100]
    assert generate_strict(df, htf)[0].empty
    df.iloc[50] = [102, 103, 97, 102, 300]  # same-bar pinbar sweep
    assert generate_strict(df, htf)[0].empty


def test_level_snapshots_and_distinct_rebounds():
    df, _ = setup()
    levels = strict_levels(df)
    support = levels[levels.side == 1]
    assert support.iloc[:3].touches.tolist() == [1, 2, 3]
    assert support.iloc[:3].level_id.nunique() == 1
    assert support.iloc[:3].price.tolist() == [100, 100, 100]
    # Multiple nearby pivots cannot validate a level without separation.
    p = replace(StrictParams(), separation=25)
    assert strict_levels(df, p).touches.max() < 3
    df.iloc[30, df.columns.get_loc('low')] = 99.8
    assert strict_levels(df).iloc[1].price == 100
    df.iloc[40, df.columns.get_loc('low')] = 96  # other ID cannot validate original
    assert generate_strict(df, setup()[1])[0].empty


@pytest.mark.parametrize('period', ['1day', '4h'])
def test_calendar_htf_prefix_and_boundary(period):
    df = pd.DataFrame(dict(open=100., high=110., low=90., close=np.arange(200)+100., volume=1.),
                      index=pd.date_range('2024-01-01', periods=200, freq='D' if period == '1day' else '4h'))
    htf = completed_htf(df, period)
    boundary = htf.available_at.iloc[1]
    dirs = strict_trend(htf, [boundary-pd.Timedelta(nanoseconds=1), boundary], 2)
    assert dirs.tolist() == [0, 1]
    if period == '1day':
        assert htf.available_at.iloc[0] == pd.Timestamp('2024-01-14 21:00')
    for cut in (50, 99, 150):
        np.testing.assert_array_equal(strict_trend(htf, df.index[:cut], 2),
            strict_trend(completed_htf(df.iloc[:cut], period), df.index[:cut], 2))
    future = df.copy()
    future.iloc[150:, future.columns.get_loc('close')] = 1
    np.testing.assert_array_equal(strict_trend(htf, df.index[:150], 2),
        strict_trend(completed_htf(future, period), df.index[:150], 2))
    aware = df.copy()
    aware.index = aware.index.tz_localize('UTC').tz_convert('Europe/Moscow')
    pd.testing.assert_frame_equal(htf, completed_htf(aware, period))


def test_htf_missing_warmup_and_cross_midnight_source():
    df, _ = setup()
    with pytest.raises(ValueError):
        generate_strict(df, None)
    assert not strict_trend(completed_htf(df, '1day'), df.index).any()
    df = df.iloc[:4].copy()
    df.index = pd.to_datetime(['2024-01-01 19:00', '2024-01-02 19:00',
                               '2024-01-03 19:00', '2024-01-04 19:00'])
    assert completed_htf(df, '4h').available_at.iloc[0] == pd.Timestamp('2024-01-02 23:00')


@pytest.mark.parametrize('side', [1, -1])
def test_strict_execution_entry_bailout_and_gap_rejects(side):
    df, htf = setup(side)
    sig = generate_strict(df, htf)[0]
    p = PALevelParams(bailout_on_drawdown=1, breakeven_r=float('inf'), trail_look=0)
    df.iloc[53, df.columns.get_loc('close')] = df.open.iloc[53]-side*.1
    tr = simulate_trades(df, sig, p, .0005, .0005, bailout_entry_bar=True)[0]
    assert tr['reason'] == 'bailout' and tr['entry_idx'] == 53 and tr['exit_idx'] == 54
    for value in (sig.iloc[0].stop-side, sig.iloc[0].target+side):
        df.iloc[53, df.columns.get_loc('open')] = value
        assert simulate_trades(df, sig, p, 0, 0, bailout_entry_bar=True) == []


def test_nearest_level_target_not_minimum_2r(monkeypatch):
    import scripts.pa_levels_strict as module
    df, htf = setup()
    levels = strict_levels(df)
    obstacle = levels.iloc[2].to_dict()
    obstacle.update(level_id=99, side=-1, price=102., known_idx=44, touches=3)
    monkeypatch.setattr(module, 'strict_levels', lambda *_: pd.concat([levels, pd.DataFrame([obstacle])]))
    sig = generate_strict(df, htf)[0].iloc[0]
    assert sig.target == 102 and sig.target_origin == 'level'
