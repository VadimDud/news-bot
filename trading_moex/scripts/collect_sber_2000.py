"""First-observed SBER candles after explicit start; no model or order calls."""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3

RUNS = Path(__file__).resolve().parents[1] / 'artifacts/runs'
PERIODS = {'5min': 5, '15min': 15}
TARGET = 2000


def update(runs=RUNS, *, init=False):
    cohort = runs / 'sber_forward_2000_v1'
    if init:
        cohort.mkdir(exist_ok=False)
        with (cohort / 'manifest.json').open('x') as out:
            json.dump(dict(start_utc=datetime.now(timezone.utc).isoformat(), target=TARGET,
                           ticker='SBER', policy='first observed completed bar; archive-only',
                           periods=list(PERIODS), orders_enabled=False), out, indent=2)
    boundary = datetime.fromisoformat(json.loads((cohort / 'manifest.json').read_text())['start_utc'])
    with sqlite3.connect(cohort / 'collection.db', timeout=60) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS bars(period TEXT, begin TEXT, o REAL,h REAL,l REAL,c REAL,v INTEGER,first_run TEXT, PRIMARY KEY(period,begin))')
        # New cursor: replay retained archives once under the exclusion policy.
        db.execute('CREATE TABLE IF NOT EXISTS processed_v2(run TEXT PRIMARY KEY)')
        db.execute('CREATE TABLE IF NOT EXISTS exclusions(period TEXT, begin TEXT, reason TEXT, first_run TEXT, old_values TEXT, incident_run TEXT, observed_values TEXT, PRIMARY KEY(period,begin))')
        db.execute('CREATE TABLE IF NOT EXISTS batch_errors(run TEXT,period TEXT,reason TEXT, PRIMARY KEY(run,period))')
        counts = dict(db.execute('SELECT period,count(*) FROM bars GROUP BY period'))
        for path in sorted((runs / 'sber_observations').glob('*/manifest.json')):
            run = path.parent.name
            if run < boundary.strftime('%Y%m%dT%H%M%S%fZ') or db.execute('SELECT 1 FROM processed_v2 WHERE run=?',(run,)).fetchone():
                continue
            meta = json.loads(path.read_bytes())
            if (meta['run_id'] != run or meta['source'] != 'sandbox-invest-public-api.tbank.ru'
                    or meta['instrument_uid'] != 'e6123145-9665-43e0-8413-cd61b8aa9b13'):
                raise ValueError('unexpected archive identity')
            for period, minutes in PERIODS.items():
                obs = meta['observations'][period]
                if obs['status'] != 'observed':
                    db.execute('INSERT INTO batch_errors VALUES(?,?,?)', (run, period, obs['status']))
                    continue
                raw = (path.parent / (period + '.json')).read_bytes()
                if sha256(raw).hexdigest() != obs['payload_sha256']:
                    db.execute('INSERT INTO batch_errors VALUES(?,?,?)', (run, period, 'payload hash mismatch'))
                    continue
                finish = datetime.fromisoformat(obs['finished_utc'])
                for row in json.loads(raw)['rows']:
                    try:
                        stamp, *values = row
                        start = datetime.fromisoformat(stamp)
                        if start.tzinfo is not None:
                            raise ValueError('expected UTC-naive bar start')
                    except (ValueError, TypeError):
                        db.execute('INSERT OR IGNORE INTO batch_errors VALUES(?,?,?)',
                                   (run, period, 'unidentifiable row; see archived payload'))
                        continue
                    start = start.replace(tzinfo=timezone.utc)
                    if start < boundary or start + timedelta(minutes=minutes) > finish:
                        continue
                    key = (period, stamp)
                    if db.execute('SELECT 1 FROM exclusions WHERE period=? AND begin=?', key).fetchone():
                        continue
                    old = db.execute('SELECT o,h,l,c,v,first_run FROM bars WHERE period=? AND begin=?', key).fetchone()
                    valid = (len(values) == 5 and all(type(v) in (int, float) and math.isfinite(v) for v in values)
                             and 0 < values[2] <= values[0] <= values[1]
                             and values[2] <= values[3] <= values[1] and values[4] >= 0)
                    if not valid or (old and old[:5] != tuple(values)):
                        db.execute('INSERT INTO exclusions VALUES(?,?,?,?,?,?,?)', (*key,
                                   'revision' if valid else 'invalid OHLCV', old[5] if old else None,
                                   json.dumps(old[:5]) if old else None, run, json.dumps(values)))
                        if old:
                            db.execute('DELETE FROM bars WHERE period=? AND begin=?', key)
                            counts[period] -= 1
                        continue
                    if old or counts.get(period, 0) >= TARGET:
                        continue
                    inserted = db.execute('INSERT OR IGNORE INTO bars VALUES(?,?,?,?,?,?,?,?)',
                                          (period, stamp, *values, run)).rowcount
                    counts[period] = counts.get(period, 0) + inserted
            db.execute('INSERT INTO processed_v2 VALUES(?)', (run,))
        exclusions = dict(db.execute('SELECT period,count(*) FROM exclusions GROUP BY period'))
        errors = dict(db.execute('SELECT period,count(*) FROM batch_errors GROUP BY period'))
        status = {p: {'count': counts.get(p, 0), 'target': TARGET,
                      'excluded': exclusions.get(p, 0), 'batch_errors': errors.get(p, 0),
                      'state': 'complete' if counts.get(p) == TARGET else 'collecting'} for p in PERIODS}
    tmp = cohort / 'status.tmp'
    tmp.write_text(json.dumps(dict(policy='exclude-conflicts-v2', start_utc=boundary.isoformat(), updated_utc=datetime.now(timezone.utc).isoformat(),
                                   periods=status), indent=2))
    tmp.replace(cohort / 'status.json')
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', action='store_true')
    print(json.dumps(update(init=parser.parse_args().init)))
