#!/usr/bin/env python3
"""Fixed STRICT-005 diagnostic; never a grid or an OOS test."""
import argparse
from collections import Counter
from dataclasses import asdict
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
from app.pa_levels import PALevelParams, generate_signals
from app.timezones import to_market
from scripts.backtest_pa_levels import ALL_TICKERS, simulate_trades
from scripts.pa_levels_strict import StrictParams, completed_htf, generate_strict, htf_from_stored, strict_trend
from scripts.research_pa_levels_diagnostic import summary


def build_htf(df, period):
    """Aggregated HTF (1day/4h from shorter LTF) or stored HTF (60min/5min)."""
    if period in ('1day', '4h'):
        return completed_htf(df, period)
    return htf_from_stored(df, period)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/trader_4h.db')
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%SZ')+'_PA-LEVELS-STRICT-005_'+git('rev-parse','--short','HEAD')
    out = ROOT / 'artifacts/runs/pa_levels' / run_id
    out.mkdir(parents=True, exist_ok=False)
    log = (out/'run.log').open('w')

    def emit(text):
        print(text, flush=True)
        print(text, file=log, flush=True)

    def save(name, obj):
        (out/name).write_text(json.dumps(obj, indent=2, default=str, allow_nan=False)+'\n')

    sources = ['scripts/pa_levels_strict.py','scripts/research_pa_levels_strict.py',
        'scripts/research_pa_levels_diagnostic.py','scripts/backtest_pa_levels.py',
        'app/pa_levels.py','app/risk.py','app/timezones.py','app/candle_patterns.py',
        'research/pa_levels/strict_spec.md','tests/test_pa_levels_strict.py',
        'tests/test_pa_levels.py','tests/test_pa_levels_execution.py']
    strict = PALevelParams(bailout_on_drawdown=1, breakeven_r=float('inf'), trail_look=0)
    manifest = dict(run_id=run_id, diagnostic=True, true_oos=False,
        command=shlex.join([sys.executable,*sys.argv]), cwd=str(ROOT), started_utc=started.isoformat(),
        commit=git('rev-parse','HEAD'), dirty_status=git('status','--porcelain'),
        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
        storage_timezone='UTC-naive', market_timezone='Europe/Moscow',
        db=str(Path(args.db).resolve()), table='candles',
        columns=['begin','open','high','low','close','volume'], tickers=ALL_TICKERS,
        periods=['1day','4h'], role='reused-history diagnostic; all history warmup',
        strict_params=asdict(StrictParams()), legacy_params=asdict(PALevelParams()),
        strict_execution=dict(breakeven='disabled',trail_look=0,bailout_entry_bar=True),
        commission=.0005, slippage=.0005, spread=0, capital=None,
        sizing='unit initial risk; no portfolio/equal cash/margin/carry',
        source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},
        data={}, exit_status=None)
    checks = dict(data={},prefix={},execution={}, margin='not modelled',
                  risk_budget='not modelled',open_positions='terminal liquidation')
    metrics, ledger, frames = {}, [], {}
    save('manifest.json',manifest)
    try:
        emit('Exact command: '+manifest['command'])
        emit('Frozen STRICT-005. Dirty diagnostic, NOT OOS. No parameter selection.')
        test_command = [sys.executable,'-m','pytest','tests/test_pa_levels.py',
                        'tests/test_pa_levels_execution.py','tests/test_pa_levels_strict.py','-q']
        test = subprocess.run(test_command,cwd=ROOT,text=True,capture_output=True)
        emit(test.stdout+test.stderr)
        checks['tests'] = dict(command=shlex.join(test_command), exit_status=test.returncode)
        assert test.returncode == 0, 'synthetic tests failed'
        with sqlite3.connect(f'file:{Path(args.db).resolve()}?mode=ro',uri=True) as con:
            con.execute('BEGIN')
            for period in manifest['periods']:
                for ticker in ALL_TICKERS:
                    key = period+':'+ticker
                    raw = pd.read_sql_query('SELECT begin,open,high,low,close,volume FROM candles WHERE ticker=? AND period=? ORDER BY begin',con,params=(ticker,period))
                    if raw.empty:
                        manifest['data'][key] = dict(rows=0, unavailable=True)
                        emit('Unavailable input: '+key)
                        continue
                    digest = hashlib.sha256(raw.to_csv(index=False,float_format='%.17g').encode()).hexdigest()
                    with gzip.open(out/f'input_{period}_{ticker}.csv.gz','wt') as f:
                        raw.to_csv(f,index=False,float_format='%.17g')
                    df = raw.set_index('begin')
                    df.index = pd.to_datetime(df.index)
                    ok = (df.index.is_unique and df.index.is_monotonic_increasing and not df.index.hasnans
                          and np.isfinite(df.to_numpy(float)).all()
                          and (df[['open','high','low','close']]>0).all().all()
                          and (df.high>=df[['open','close','low']].max(axis=1)).all()
                          and (df.low<=df[['open','close','high']].min(axis=1)).all() and (df.volume>=0).all())
                    checks['data'][key] = bool(ok)
                    assert ok, 'invalid OHLCV '+key
                    frames[period,ticker] = df
                    manifest['data'][key] = dict(rows=len(df),start=str(df.index[0]),end=str(df.index[-1]),sha256=digest)
        save('manifest.json',manifest)
        for period in manifest['periods']:
            tickers = [t for t in ALL_TICKERS if (period,t) in frames]
            if not tickers:
                metrics[period] = dict(status='unavailable; no stored candles')
                continue
            funnel = Counter()
            for ticker in tickers:
                df = frames[period,ticker]
                htf = completed_htf(df,period)
                sig, counts, levels = generate_strict(df,htf)
                funnel.update(counts)
                key = period+':'+ticker
                cuts = sorted(set([len(df)//2,3*len(df)//4]+[int(i)+1 for i in sig.idx]))
                for cut in cuts:
                    small_htf = completed_htf(df.iloc[:cut],period)
                    small, _, small_levels = generate_strict(df.iloc[:cut],small_htf)
                    pd.testing.assert_frame_equal(sig[sig.idx<cut].reset_index(drop=True),small,check_dtype=False)
                    pd.testing.assert_frame_equal(levels[levels.known_idx<cut].reset_index(drop=True),small_levels,check_dtype=False)
                    np.testing.assert_array_equal(strict_trend(htf,df.index[:cut]),strict_trend(small_htf,df.index[:cut]))
                checks['prefix'][key] = dict(passed=True,cuts=cuts,signals=len(sig),attrition=counts)
                for cell, signals, p in [('strict',sig,strict),('legacy',generate_signals(df),PALevelParams())]:
                    signals = signals.copy()
                    signals['ticker'] = ticker
                    rows = simulate_trades(df,signals,p,.0005,.0005,bailout_entry_bar=cell=='strict')
                    executed = {r['signal_idx'] for r in rows}
                    rejects = Counter()
                    busy = -1
                    for s in signals.to_dict('records'):
                        i = int(s['idx'])+1
                        if s['idx'] in executed:
                            busy = next(r['exit_idx'] for r in rows if r['signal_idx']==s['idx'])
                        elif i>=len(df):
                            rejects['no_next_open'] += 1
                        elif i<=busy:
                            rejects['overlap'] += 1
                        elif s['side']*(df.open.iloc[i]-s['stop'])<=0:
                            rejects['entry_stop_gap'] += 1
                        elif s['side']*(s['target']-df.open.iloc[i])<=0:
                            rejects['entry_target_gap'] += 1
                        else:
                            raise AssertionError('unexplained execution rejection')
                    previous = -1
                    for r in rows:
                        s = signals[signals.idx==r['signal_idx']]
                        side = 1 if r['side']=='L' else -1
                        s = s[s.side==side].iloc[0]
                        assert r['entry_idx']>previous and r['exit_idx']>=r['entry_idx']
                        assert r['initial_risk']>0 and side*(s.target-df.open.iloc[r['entry_idx']])>0
                        assert np.isclose(r['r_multiple']*r['initial_risk'],r['gross']-r['commission']-r['slippage'])
                        previous = r['exit_idx']
                        r.update(period=period,cell=cell,year=to_market(r['entry_time']).year,
                                 setup=str(s.reasons),level=s.get('level'),touches=s.get('touches'),
                                 zone=s.get('zone'),target_origin=s.get('target_origin','legacy unknown'),
                                 level_id=s.get('level_id'),breakout_idx=s.get('breakout_idx'),
                                 return_idx=s.get('return_idx'),breakout_extreme=s.get('breakout_extreme'))
                        seg = df.iloc[r['entry_idx']:r['exit_idx']+1]
                        entry = df.open.iloc[r['entry_idx']]
                        r['mfe_r_exit_bar_bound'] = float((seg.high.max()-entry if side==1 else entry-seg.low.min())/r['initial_risk'])
                        r['mae_r_exit_bar_bound'] = float((entry-seg.low.min() if side==1 else seg.high.max()-entry)/r['initial_risk'])
                    ledger.extend(rows)
                    checks['execution'][key+':'+cell] = dict(passed=True,candidates=len(signals),executed=len(rows),rejects=dict(rejects))
                emit(key+': '+json.dumps(counts))
            metrics[period] = dict(attrition=dict(funnel))
            for cell in ('strict','legacy'):
                rows = [r for r in ledger if r['period']==period and r['cell']==cell]
                r = np.array([t['r_multiple'] for t in rows])
                boot = np.random.default_rng(20261110).choice(r,size=(2000,len(r))).mean(axis=1) if len(r) else []
                metrics[period][cell] = dict(total=summary(rows),
                    tickers={t:summary([r for r in rows if r['ticker']==t]) for t in tickers},
                    calendar={str(y):summary([r for r in rows if r['year']==y]) for y in sorted({r['year'] for r in rows})},
                    remove_top_winner=summary(sorted(rows,key=lambda r:r['r_multiple'],reverse=True)[1:]) if any(r['r_multiple']>0 for r in rows) else None,
                    iid_bootstrap_95=np.quantile(boot,[.025,.975]).tolist() if len(boot) else None,
                    bootstrap_caveat='descriptive reused dependent sparse data; not confidence in edge',
                    exposure_bars={t:sum(r['exit_idx']-r['entry_idx']+1 for r in rows if r['ticker']==t)/len(frames[period,t]) for t in tickers})
                emit(period+' '+cell+': '+json.dumps(summary(rows)))
            metrics[period]['references'] = dict(no_trade_sum_r=0,
                buy_hold_price_return={t:float(frames[period,t].close.iloc[-1]/frames[period,t].open.iloc[0]-1) for t in tickers},
                portfolio='not modelled; bar occupancy not portfolio return-on-exposure')
        checks['all_passed'] = True
        manifest['exit_status'] = 0
    except Exception:
        checks['all_passed'] = False
        manifest['exit_status'] = 1
        emit(traceback.format_exc())
        raise
    finally:
        manifest['ended_utc'] = datetime.now(timezone.utc).isoformat()
        save('manifest.json',manifest)
        save('metrics.json',metrics)
        save('checks.json',checks)
        with gzip.open(out/'trades.jsonl.gz','wt') as f:
            for row in ledger:
                f.write(json.dumps(row,default=str,allow_nan=False)+'\n')
        emit('Artifacts: '+str(out))
        log.close()


if __name__ == '__main__':
    main()
