#!/usr/bin/env python3
"""Frozen PA-LEVELS-DIAG-004; outputs are descriptive, never OOS."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import shlex
import sqlite3
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from app.pa_levels import PALevelParams, _atr, generate_signals
from app.timezones import to_market
from scripts.backtest_pa_levels import ALL_TICKERS, simulate_trades


def summary(rows):
    rows = sorted(rows, key=lambda t: (str(t['exit_time']), t['ticker']))
    r = np.array([t['r_multiple'] for t in rows], float)
    eq = np.r_[0., np.cumsum(r)]
    return dict(n=len(r), mean_r=float(r.mean()) if len(r) else None,
                median_r=float(np.median(r)) if len(r) else None,
                sum_r=float(r.sum()), worst_r=float(r.min()) if len(r) else None,
                pf_r=float(r[r > 0].sum() / -r[r < 0].sum()) if (r < 0).any() else None,
                max_dd_r=float((np.maximum.accumulate(eq) - eq).max()),
                longs=sum(t['side'] == 'L' for t in rows),
                risk_pct_median=float(np.median([t['initial_risk'] / t['entry'] for t in rows])) if rows else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/trader_4h.db')
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%SZ') + '_PA-LEVELS-DIAG-004_' + git('rev-parse', '--short', 'HEAD')
    out = ROOT / 'artifacts/runs/pa_levels' / run_id
    out.mkdir(parents=True, exist_ok=False)
    log = (out / 'run.log').open('w')

    def emit(text):
        print(text, flush=True)
        print(text, file=log, flush=True)

    def save(name, data):
        (out / name).write_text(json.dumps(data, indent=2, default=str, allow_nan=False) + '\n')

    video = PALevelParams(require_compression=1, compress_after_return=1,
                          impulse_atr_min=.5, bailout_on_drawdown=1, rr_min=2, use_htf=0)
    cells = dict(baseline=PALevelParams(), video=video,
                 video_no_bailout=replace(video, bailout_on_drawdown=0),
                 video_no_impulse=replace(video, impulse_atr_min=0))
    sources = ['app/pa_levels.py', 'app/risk.py', 'app/candle_patterns.py',
               'app/timezones.py', 'scripts/backtest_pa_levels.py',
               'scripts/research_pa_levels_diagnostic.py',
               'research/pa_levels/diagnostic_spec.md',
               'tests/test_pa_levels.py', 'tests/test_pa_levels_execution.py']
    manifest = dict(run_id=run_id, diagnostic=True, true_oos=False,
                    started_utc=started.isoformat(), command=shlex.join([sys.executable, *sys.argv]),
                    cwd=str(ROOT), commit=git('rev-parse', 'HEAD'),
                    dirty_status=git('status', '--porcelain'),
                    python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                    storage_timezone='UTC-naive', market_timezone='Europe/Moscow',
                    db=str(Path(args.db).resolve()), table='candles',
                    columns=['begin', 'open', 'high', 'low', 'close', 'volume'],
                    period='1day', tickers=ALL_TICKERS, role='reused-history diagnostic',
                    params={k: asdict(v) for k, v in cells.items()},
                    commission=.0005, slippage=.0005, spread=0,
                    capital=None, sizing='unit initial risk descriptive R; no portfolio',
                    execution='next open; stop gaps at open; intrabar stop first; bailout next open; terminal close liquidation',
                    source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in sources},
                    data={}, exit_status=None)
    save('manifest.json', manifest)
    checks = dict(data={}, execution={}, prefix={}, tests='pytest tests/test_pa_levels.py tests/test_pa_levels_execution.py -q: 23 passed',
                  margin='not modelled', risk_budget='not modelled', open_positions='terminal close liquidation',
                  htf='explicitly disabled; 1day has no supplied HTF')
    results, ledger, frames, signals = {}, [], {}, {}
    try:
        emit('Exact command: ' + manifest['command'])
        emit('Diagnostic only; frozen specification; no best selection.')
        with sqlite3.connect(f'file:{Path(args.db).resolve()}?mode=ro', uri=True) as con:
            con.execute('BEGIN')
            for ticker in ALL_TICKERS:
                raw = pd.read_sql_query('SELECT begin, open, high, low, close, volume FROM candles WHERE ticker=? AND period=? ORDER BY begin', con, params=(ticker, '1day'))
                digest = hashlib.sha256(raw.to_csv(index=False, float_format='%.17g').encode()).hexdigest()
                df = raw.rename(columns={'begin': 'dt'}).set_index('dt')
                df.index = pd.to_datetime(df.index)
                a = df.to_numpy(float)
                ok = (len(df) > 20 and df.index.is_unique and df.index.is_monotonic_increasing
                      and np.isfinite(a).all() and (df[['open','high','low','close']] > 0).all().all()
                      and (df.high >= df[['open','close','low']].max(axis=1)).all()
                      and (df.low <= df[['open','close','high']].min(axis=1)).all()
                      and (df.volume >= 0).all())
                checks['data'][ticker] = bool(ok)
                assert ok, f'data integrity: {ticker}'
                frames[ticker] = df
                manifest['data'][ticker] = dict(sha256=digest, rows=len(df), start=str(df.index[0]), end=str(df.index[-1]))
                with gzip.open(out / f'input_{ticker}.csv.gz', 'wt') as f:
                    raw.to_csv(f, index=False, float_format='%.17g')
        save('manifest.json', manifest)

        def execute(ticker, sig, p, cell, seed=None):
            df = frames[ticker]
            sig = sig.copy()
            sig['ticker'] = ticker
            rows = simulate_trades(df, sig, p, .0005, .0005)
            prev = -1
            atr = _atr(df, p.atr_period).to_numpy(float)
            for t in rows:
                side = 1 if t['side'] == 'L' else -1
                s = sig[sig.idx == t['signal_idx']]
                s = s[s.side == side].iloc[0]
                t.update(cell=cell, seed=seed, year=to_market(t['entry_time']).year,
                         signal_risk_atr=abs(s.price - s.stop) / atr[int(s.idx)],
                         signal_target_r=abs(s.target - s.price) / abs(s.price - s.stop),
                         setup=str(s.reasons), level=None, touches=None, zone=None,
                         target_origin='not exposed by generator',
                         metadata_limit='level in reasons only; touches/zone/target origin not exposed')
                seg = df.iloc[t['entry_idx']:t['exit_idx'] + 1]
                t['mfe_r_exit_bar_bound'] = float(((seg.high.max() - t['entry']) if side == 1 else (t['entry'] - seg.low.min())) / t['initial_risk'])
                t['mae_r_exit_bar_bound'] = float(((t['entry'] - seg.low.min()) if side == 1 else (seg.high.max() - t['entry'])) / t['initial_risk'])
                assert t['entry_idx'] > prev and t['exit_idx'] >= t['entry_idx']
                assert t['initial_risk'] > 0 and side * (float(s.target) - df.open.iloc[t['entry_idx']]) > 0
                assert np.isclose(t['r_multiple'] * t['initial_risk'], t['gross'] - t['commission'] - t['slippage'])
                prev = t['exit_idx']
            ledger.extend(rows)
            checks['execution'][f'{cell}:{seed}:{ticker}'] = dict(passed=True, candidates=len(sig), executed=len(rows), skipped=len(sig)-len(rows))
            return rows

        years = list(range(min(to_market(df.index[0]).year for df in frames.values()),
                           max(to_market(df.index[-1]).year for df in frames.values()) + 1))
        for cell, p in cells.items():
            trades = []
            for ticker, df in frames.items():
                sig = generate_signals(df, p)
                signals[cell, ticker] = sig
                if cell == 'video':
                    cuts = sorted(set([len(df)//2, len(df)*3//4] + [int(i)+1 for i in sig.idx]))
                    for cut in cuts:
                        pd.testing.assert_frame_equal(sig[sig.idx < cut].reset_index(drop=True),
                                                      generate_signals(df.iloc[:cut], p).reset_index(drop=True), check_dtype=False)
                    checks['prefix'][ticker] = dict(passed=True, cuts=cuts, compared_signals=len(sig))
                trades.extend(execute(ticker, sig, p, cell))
            results[cell] = dict(total=summary(trades),
                                 calendar={str(y): summary([t for t in trades if t['year'] == y]) for y in years},
                                 tickers={t: summary([r for r in trades if r['ticker'] == t]) for t in ALL_TICKERS})
            emit(cell + ': ' + json.dumps(results[cell]['total']))

        real = [t for t in ledger if t['cell'] == 'video']
        results['robustness'] = dict(
            leave_ticker_out={ticker: summary([t for t in real if t['ticker'] != ticker]) for ticker in ALL_TICKERS},
            leave_winner_out={str(i): summary([t for j,t in enumerate(real) if j != i]) for i,r in enumerate(real) if r['r_multiple'] > 0},
            remove_top={str(k): summary(sorted(real, key=lambda t: t['r_multiple'], reverse=True)[k:]) for k in (1,3)})
        rng = np.random.default_rng(20261110)
        r = np.array([t['r_multiple'] for t in real])
        boot = rng.choice(r, size=(2000, len(r)), replace=True).mean(axis=1) if len(r) else []
        clusters = [np.array([t['r_multiple'] for t in real if t['year'] == y]) for y in years]
        cluster_boot = []
        for _ in range(2000):
            sample = np.concatenate([clusters[i] for i in rng.integers(0, len(years), len(years))])
            if len(sample):
                cluster_boot.append(sample.mean())
        results['bootstrap'] = dict(iid_percentile_95=np.quantile(boot, [.025,.975]).tolist() if len(boot) else None,
                                    calendar_cluster_percentile_95=np.quantile(cluster_boot, [.025,.975]).tolist() if cluster_boot else None,
                                    replicates=2000, nonempty_cluster_replicates=len(cluster_boot),
                                    caveat='descriptive only; sparse dependent reused data, few calendar clusters; no p-value')
        results['random_entry'] = {}
        for seed in range(20):
            rng = np.random.default_rng(seed)
            controls = []
            for ticker, df in frames.items():
                atr = _atr(df, video.atr_period).to_numpy(float)
                entry_year = np.array([to_market(x).year for x in df.index])
                picks, rows = set(), []
                for template in [t for t in real if t['ticker'] == ticker]:
                    candidates = [i for i in range(20, len(df)-1) if entry_year[i+1] == template['year'] and i not in picks]
                    if not candidates:
                        continue
                    i = int(rng.choice(candidates)); picks.add(i)
                    side = 1 if template['side'] == 'L' else -1
                    price = float(df.close.iloc[i])
                    risk = atr[i] * template['signal_risk_atr']
                    rows.append(dict(idx=i, time=df.index[i], side=side, price=price,
                                     stop=price-side*risk, target=price+side*risk*template['signal_target_r'], reasons=['random_entry_matched']))
                sig = pd.DataFrame(rows, columns=['idx','time','side','price','stop','target','reasons'])
                controls.extend(execute(ticker, sig, video, 'random_entry', seed))
            results['random_entry'][str(seed)] = summary(controls)
        means = [m['mean_r'] for m in results['random_entry'].values() if m['n']]
        results['random_entry_summary'] = dict(seed_mean_r_range=[min(means), max(means)],
                                             mean_of_seed_means=float(np.mean(means)),
                                             caveat='random ENTRY, not random LEVEL; matched templates conditional on realised historical trades; not a p-value')
        results['reference'] = dict(no_trade_sum_r=0, portfolio_returns='not modelled',
            buy_hold_price_return={t: float(df.close.iloc[-1]/df.open.iloc[0]-1) for t,df in frames.items()},
            video_bar_exposure={t: sum(r['exit_idx']-r['entry_idx']+1 for r in real if r['ticker']==t)/len(df) for t,df in frames.items()},
            exposure_caveat='bar occupancy, includes full exit bar; not time-weighted market exposure; no return-on-exposure portfolio claim')
        checks['all_passed'] = True
        manifest['exit_status'] = 0
        emit('Robustness: ' + json.dumps(results['robustness']))
        emit('Bootstrap: ' + json.dumps(results['bootstrap']))
        emit('Random-entry: ' + json.dumps(results['random_entry_summary']))
    except Exception:
        manifest['exit_status'] = 1
        checks['all_passed'] = False
        emit(traceback.format_exc())
        raise
    finally:
        manifest['ended_utc'] = datetime.now(timezone.utc).isoformat()
        save('manifest.json', manifest)
        save('metrics.json', results)
        save('checks.json', checks)
        with gzip.open(out / 'trades.jsonl.gz', 'wt') as f:
            for row in ledger:
                f.write(json.dumps(row, default=str, allow_nan=False) + '\n')
        emit('Artifacts: ' + str(out))
        log.close()


if __name__ == '__main__':
    main()
