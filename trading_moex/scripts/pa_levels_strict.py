"""Opt-in research sequence; see research/pa_levels/strict_spec.md."""
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.risk import atr
from app.timezones import as_utc_index, as_utc_naive_index, MARKET_TZ_NAME


@dataclass(frozen=True)
class StrictParams:
    atr_period: int = 14
    look: int = 3
    reversal_atr: float = 1.0
    zigzag_atr: float = 3.0
    zone_atr: float = .5
    cluster_atr: float = 1.0
    touches: int = 3
    separation: int = 7
    volume_period: int = 20
    volume_mult: float = 1.5
    penetration_atr: float = .5
    impulse_range_atr: float = 1.0
    impulse_body: float = .5
    return_bars: int = 3
    compression_bars: int = 3
    compression_body: float = .35
    compression_atr: float = .6
    stop_buffer_atr: float = .2
    min_target_atr: float = 1.0
    retest_bars: int = 12
    rr: float = 2.0
    htf_ema: int = 50
    compression_length: int = 2
    stop_mode: str = 'protected'  # 'protected' | 'breakout'
    require_impulse_break: bool = True
    htf_week_bars: int = 110  # trailing completed-week window on the HTF


def closed_candles(df, period):
    """Stored HTF begins have explicit close boundaries, never inferred gaps."""
    duration = {'60min': pd.Timedelta(hours=1), '5min': pd.Timedelta(minutes=5)}
    if period not in duration:
        raise ValueError('unsupported explicit HTF period')
    out = df.copy().reset_index(drop=True)
    out['available_at'] = as_utc_naive_index(df.index) + duration[period]
    return out


def htf_from_stored(df, period):
    """Wrap a stored HTF series with explicit close boundaries.

    ``60min`` and ``5min`` candles have fixed durations, so availability is the
    stored begin plus that duration. No aggregation and no future median.
    """
    if df is None or df.empty:
        raise ValueError('strict requires nonempty stored HTF')
    return closed_candles(df, period)


def completed_htf(df, period):
    """Explicit calendar close boundaries, independent of later timestamps."""
    if period not in ('1day', '4h') or df.empty:
        raise ValueError('strict HTF requires nonempty 1day or 4h source')
    local = as_utc_index(df.index).tz_convert(MARKET_TZ_NAME)
    day = local.tz_localize(None).normalize()
    bucket = day - pd.to_timedelta(day.dayofweek, unit='D') if period == '1day' else day
    end = bucket + pd.Timedelta(days=7 if period == '1day' else 1)
    ends = as_utc_naive_index(end.tz_localize(MARKET_TZ_NAME))
    source_end = (as_utc_naive_index((day + pd.Timedelta(days=1)).tz_localize(MARKET_TZ_NAME))
                  if period == '1day' else as_utc_naive_index(df.index) + pd.Timedelta(hours=4))
    work = df.copy()
    work['bucket'] = bucket
    work['available_at'] = np.maximum(ends.to_numpy(), source_end.to_numpy())
    out = work.groupby('bucket', sort=True).agg(
        open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
        close=('close', 'last'), volume=('volume', 'sum'),
        available_at=('available_at', 'max'))
    # The left edge can be a truncated historical bucket.
    return out.iloc[1:].reset_index(drop=True)


def strict_trend(htf, index, ema_period=50):
    if htf is None or htf.empty or 'available_at' not in htf:
        raise ValueError('strict requires explicit nonempty HTF close boundaries')
    times = pd.DatetimeIndex(htf.available_at).as_unit('ns')
    if times.tz is not None or not times.is_unique or not times.is_monotonic_increasing or times.hasnans:
        raise ValueError('HTF boundaries must be ordered unique UTC-naive')
    close = htf.close.to_numpy(float)
    if not np.isfinite(close).all():
        raise ValueError('invalid HTF close')
    ema = htf.close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    dirs = np.where(ema.notna(), np.sign(close - ema), 0).astype(int)
    pos = times.searchsorted(as_utc_naive_index(index), side='right') - 1
    return np.where(pos >= 0, dirs[np.maximum(pos, 0)], 0)


def zigzag_pivots(df, p=StrictParams()):
    """Causal zigzag: only macro reversals that move >= zigzag_atr * ATR.

    Returns a list of (j, side, price) where side=+1 is a swing low (support)
    and side=-1 is a swing high (resistance). Each new pivot must reverse the
    current leg by at least ``zigzag_atr`` ATR, which ignores small noise.
    A pivot is only *confirmed* once the opposite reversal leg completes, so
    the returned ``known_idx`` is causal (never the pivot bar itself).
    """
    h, l = df['high'].to_numpy(float), df['low'].to_numpy(float)
    a = atr(df, p.atr_period).shift().to_numpy(float)
    n = len(df)
    pivots = []
    if n == 0:
        return pivots
    # Track the running leg: last extreme and its direction.
    dir_ = 0            # +1 up leg (looking for high), -1 down leg (looking for low)
    ext_idx, ext_price = 0, float(df['close'].iloc[0])
    lo_idx, lo_price = 0, float(l[0])
    hi_idx, hi_price = 0, float(h[0])
    for j in range(1, n):
        if not np.isfinite(a[j]) or a[j] <= 0:
            continue
        thresh = p.zigzag_atr * a[j]
        if l[j] < lo_price:
            lo_idx, lo_price = j, l[j]
        if h[j] > hi_price:
            hi_idx, hi_price = j, h[j]
        if dir_ >= 0:
            # looking for a swing high; track highest
            if h[j] >= hi_price:
                hi_idx, hi_price = j, h[j]
            if hi_price - l[j] >= thresh or (hi_price - ext_price) >= thresh:
                # down reversal confirmed -> previous high is resistance
                if hi_price - ext_price >= thresh:
                    pivots.append((ext_idx, -1, ext_price, j))
                dir_ = -1
                ext_idx, ext_price = lo_idx if lo_price == l[j] else j, l[j]
                lo_idx, lo_price = j, l[j]
                hi_idx, hi_price = j, h[j]
        else:
            if l[j] <= lo_price:
                lo_idx, lo_price = j, l[j]
            if h[j] - lo_price >= thresh or (ext_price - lo_price) >= thresh:
                if ext_price - lo_price >= thresh:
                    pivots.append((ext_idx, 1, ext_price, j))
                dir_ = +1
                ext_idx, ext_price = hi_idx if hi_price == h[j] else j, h[j]
                hi_idx, hi_price = j, h[j]
                lo_idx, lo_price = j, l[j]
    return pivots


def strict_levels(df, p=StrictParams()):
    """Immutable anchor IDs and append-only snapshots of distinct rebounds.

    Only macro zigzag pivots are considered; small noise swings are ignored.
    """
    c = df['close'].to_numpy(float)
    a = atr(df, p.atr_period).shift().to_numpy(float)
    live, rows = [], []
    for j, side, price, known in zigzag_pivots(df, p):
        if j < p.look or j >= len(df) - p.look or not np.isfinite(a[j]) or a[j] <= 0:
            continue
        # Merge a pivot into an existing level of the same side when it is
        # within that level's cluster zone (one level per price region, no
        # near-identical siblings). Distance is measured against the anchor
        # price and a wide ATR-based cluster tolerance.
        tol = max(p.cluster_atr * a[j], p.zone_atr * a[j])
        matches = [lv for lv in live if lv['side'] == side and abs(lv['price']-price) <= tol]
        lv = min(matches, key=lambda v: (abs(v['price']-price), v['level_id'])) if matches else None
        if lv is None:
            lv = dict(level_id=len(live), side=side, price=float(price), zone=p.zone_atr*a[j],
                      anchor_atr=a[j], touches=0, last_pivot=j)
            live.append(lv)
        else:
            if j-lv['last_pivot'] < p.separation:
                continue
            if np.max(side*(c[lv['last_pivot']+1:j]-lv['price'])) < p.reversal_atr*lv['anchor_atr']:
                continue
        lv.update(touches=lv['touches']+1, last_pivot=j, known_idx=known)
        rows.append(lv.copy())
    return pd.DataFrame(rows, columns=['level_id','side','price','zone','anchor_atr','touches','last_pivot','known_idx'])


SIGNAL_COLUMNS = ['idx','time','side','price','stop','target','reasons','level_id','level',
                  'touches','zone','breakout_idx','return_idx','breakout_extreme','target_origin']


def weekly_levels(htf, p, asof_pos):
    """Levels built only from the trailing completed week of HTF bars.

    ``asof_pos`` is the index into ``htf`` of the last HTF bar available now.
    Only bars ``asof_pos-htf_week_bars+1 .. asof_pos`` are used, so levels
    reflect roughly the last week of hourly history, not the full series.
    Returns (levels_df, avg_range) where avg_range is the mean HTF high-low
    over the same trailing week (the "average price movement" baseline).
    """
    lo = max(0, asof_pos - p.htf_week_bars + 1)
    win = htf.iloc[lo:asof_pos + 1].reset_index(drop=True)
    if len(win) < 3:
        return strict_levels(win, p).assign(), float('nan')
    avg_range = float((win['high'] - win['low']).mean())
    return strict_levels(win, p), avg_range


def generate_strict(df, htf, p=StrictParams()):
    """Forward state machine. Returns signals, attrition counters, level history.

    Levels and the average HTF range are rebuilt from the trailing completed
    week of HTF bars only (``htf_week_bars``), as required by the written spec.
    """
    trend = strict_trend(htf, df.index, p.htf_ema)
    htf_times = as_utc_naive_index(pd.DatetimeIndex(htf.available_at))
    ltf_times = as_utc_naive_index(df.index)
    o,h,l,c,v = (df[k].to_numpy(float) for k in ('open','high','low','close','volume'))
    a = atr(df, p.atr_period).shift().to_numpy(float)
    avg_v = df.volume.rolling(p.volume_period).mean().shift().to_numpy(float)
    live, pending, signals, counts = {}, [], [], Counter()
    retests = {}   # level_id -> retest state after a breakout
    deleted = set()  # broken levels deleted because no retest-and-bounce
    cur_week_pos = None  # asof_pos of the last HTF bar available (week rebuild key)
    week_avg_range = float('nan')
    all_level_snapshots = []  # for provenance/prefix tests
    for i in range(1, len(df)):
        # --- trailing-week level rebuild at each completed-week boundary ---
        asof_pos = int(htf_times.searchsorted(ltf_times[i], side='right')) - 1
        week_key = None
        if asof_pos >= 0:
            week_key = htf_times[asof_pos].isocalendar()[:2] if hasattr(htf_times[asof_pos], 'isocalendar') else (htf_times[asof_pos].year, htf_times[asof_pos].isocalendar()[1])
        if week_key != cur_week_pos:
            cur_week_pos = week_key
            if asof_pos >= 0:
                wlevels, week_avg_range = weekly_levels(htf, p, asof_pos)
                all_level_snapshots.append((i, wlevels.copy()))
                new_live = {}
                for row in wlevels.to_dict('records'):
                    lid = row['level_id']
                    if lid in deleted:
                        continue
                    prev = live.get(lid)
                    if prev is not None and prev.get('flipped_side') is not None:
                        row['side'] = prev['flipped_side']
                    row['available_at'] = htf.available_at.iloc[asof_pos]
                    new_live[lid] = row
                live = new_live
        if not np.isfinite(a[i]) or a[i] <= 0:
            counts['warmup_bars'] += 1
            continue
        ready = []
        for ev in pending:
            side, lv = ev['side'], ev['level']
            if ev['return_idx'] is None:
                if i-ev['breakout_idx'] > p.return_bars:
                    counts['return_timeout'] += 1
                    continue
                if side*(c[i]-lv['price']) > 0:
                    rng = h[i]-l[i]
                    if not (rng >= p.impulse_range_atr*a[i]
                            and side*(c[i]-o[i]) >= p.impulse_body*rng):
                        counts['return_impulse_reject'] += 1
                        continue
                    ev['return_idx'] = i
                    counts['returned'] += 1
                ready.append(ev)
                continue  # no compression on the return candle
            if i-ev['return_idx'] > p.compression_bars:
                counts['compression_timeout'] += 1
                continue
            if side*(c[i]-lv['price']) <= 0:
                counts['recross_reject'] += 1
                continue
            rng = h[i]-l[i]
            start = i-p.compression_length+1
            ranges = h[start:i+1]-l[start:i+1]
            if not (start > ev['return_idx'] and len(ranges) == p.compression_length
                    and (np.diff(ranges) < 0).all()
                    and 0 < rng <= p.compression_atr*a[i]
                    and abs(c[i]-o[i]) <= p.compression_body*rng
                    and side*(c[i]-o[i]) > 0):
                ready.append(ev)
                continue
            counts['compressed'] += 1
            if trend[i] != side:
                counts['htf_reject'] += 1
                continue
            if signals and signals[-1]['idx'] == i:
                counts['same_bar_priority_reject'] += 1
                continue
            # Stop: breakout-candle extreme (video option) or nearest protected level.
            if p.stop_mode == 'breakout':
                stop = ev['extreme'] - side * p.stop_buffer_atr * a[i]
                risk = side * (c[i] - stop)
            else:
                values = l if side == 1 else h
                extrema = [j for j in range(1, i)
                           if side*(values[j-1]-values[j]) > 0
                           and side*(values[j+1]-values[j]) > 0
                           and side*(c[i]-values[j]) > 0]
                if not extrema:
                    counts['no_known_stop_extremum'] += 1
                    continue
                stop_idx = extrema[-1]
                stop = values[stop_idx]-side*p.stop_buffer_atr*a[i]
                risk = side*(c[i]-stop)
            # Target: a *significant* opposite level that is clearly beyond the
            # current price region, not a near-duplicate/noise level. A level
            # qualifies only if it is farther than min_target_atr * ATR from the
            # signal price (avoid picking a level that is effectively at price).
            min_dist = p.min_target_atr * a[i]
            obstacles = [x['price'] for x in live.values() if x['side'] == -side
                         and x['touches'] >= p.touches and not x.get('invalid')
                         and side*(x['price']-c[i]) > min_dist]
            rr_target = c[i] + side * p.rr * risk
            # Target: nearest significant opposite level, but never closer than
            # rr * risk (video: nearest level OR 1:2 minimum). Take the farther.
            if obstacles:
                near = min(obstacles, key=lambda x: abs(x - c[i]))
                target = near if side * (near - rr_target) >= 0 else rr_target
                target_origin = 'level' if target == near else 'level<rr->2R'
            else:
                target = rr_target
                target_origin = '2R'
            if risk <= 0 or target <= 0:
                counts['bracket_reject'] += 1
                continue
            signals.append(dict(idx=i, time=df.index[i], side=side, price=c[i], stop=stop,
                target=target, reasons=['strict_break_return_compress'], level_id=lv['level_id'],
                level=lv['price'], touches=lv['touches'], zone=lv['zone'],
                breakout_idx=ev['breakout_idx'], return_idx=ev['return_idx'],
                breakout_extreme=ev['extreme'], target_origin=target_origin))
            counts['signals'] += 1
        pending = ready
        validated = [lv for lv in live.values() if lv['touches'] >= p.touches]
        counts['bars_with_validated_level' if validated else 'bars_without_validated_level'] += 1
        for lv in validated:
            side, price = lv['side'], lv['price']
            extreme = l[i] if side == 1 else h[i]
            if not (side*(c[i-1]-price) >= 0 and side*(extreme-price) < 0):
                continue
            counts['crossings'] += 1
            rng = h[i]-l[i]
            if not side*(c[i]-price) < 0:
                # Wick/shadow pierced the level but the body did not close
                # through it: a false break. The level is NOT broken; its
                # significance grows (extra confirmed touch, hardened zone).
                counts['shadow_false_break'] += 1
                lv['touches'] = lv['touches'] + 1
                lv['last_pivot'] = i
                continue
            counts['breakouts'] += 1
            if p.require_impulse_break:
                rng = h[i]-l[i]
                if not (rng >= p.impulse_range_atr*a[i]
                        and side*(o[i]-c[i]) >= p.impulse_body*rng):
                    counts['breakout_impulse_reject'] += 1
                    continue
            # A broken level does NOT flip automatically. It becomes the opposite
            # S/R only if price retests it from the new side and bounces; else it
            # is deleted. See the retest state machine below.
            pending.append(dict(side=side, level=lv.copy(), breakout_idx=i, return_idx=None,
                                extreme=extreme, stop=extreme-side*p.stop_buffer_atr*a[i], volume=v[i]))
            retests[lv['level_id']] = dict(side=side, price=lv['price'], zone=lv['zone'],
                                           start=i, flip=None)
        # --- retest state machine for broken levels ---
        for lid in list(retests):
            rt = retests[lid]
            lv = live.get(lid)
            if lv is None:
                del retests[lid]
                continue
            if i - rt['start'] > p.retest_bars:
                # No retest-and-bounce: the broken level is deleted for good.
                live.pop(lid, None)
                deleted.add(lid)
                del retests[lid]
                counts['broken_deleted'] += 1
                continue
            new_side = -rt['side']
            # Price has come back to test the level from the new side.
            touched = (new_side == -1 and h[i] >= rt['price'] - rt['zone']) or \
                      (new_side == 1 and l[i] <= rt['price'] + rt['zone'])
            if not touched:
                continue
            # Bounce = close stays on the new side (did not re-close through).
            bounced = new_side * (c[i] - rt['price']) > 0 and new_side * (c[i-1] - rt['price']) >= 0
            if bounced:
                rt['flip'] = i
                counts['retest_flipped'] += 1
            if rt['flip'] is not None and i > rt['flip']:
                lv['side'] = new_side
                lv['touches'] = p.touches
                del retests[lid]
    counts['pending_at_end'] = len(pending)
    counts['level_snapshots'] = len(all_level_snapshots)
    counts['week_avg_range'] = week_avg_range if np.isfinite(week_avg_range) else None
    snapshot = pd.concat([s for _, s in all_level_snapshots], ignore_index=True) \
        if all_level_snapshots else pd.DataFrame(columns=['level_id','side','price','zone',
        'anchor_atr','touches','last_pivot','known_idx'])
    return pd.DataFrame(signals, columns=SIGNAL_COLUMNS), dict(counts), snapshot
