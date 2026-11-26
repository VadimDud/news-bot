"""Read-only integrity check of one first-completion snapshot; never scores it."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3


RUNS = Path(__file__).resolve().parents[1] / 'artifacts/runs'
PERIODS = {'5min': 5, '15min': 15}
TARGET = 2000


def verify(runs, period):
    if period not in PERIODS:
        raise ValueError('unknown period')
    cohort = runs / 'sber_forward_2000_v1'
    manifest = (cohort / 'manifest.json').read_bytes()
    meta = json.loads(manifest)
    if (meta['ticker'] != 'SBER' or meta['target'] != TARGET or meta['orders_enabled'] is not False
            or period not in meta['periods']):
        raise ValueError('unexpected cohort manifest')
    boundary = datetime.fromisoformat(meta['start_utc'])
    if boundary.utcoffset() != timedelta(0):
        raise ValueError('expected UTC start')
    uri = (cohort / 'collection.db').resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.execute('BEGIN')
        frozen = db.execute('SELECT sha256,payload FROM first_completion WHERE period=?', (period,)).fetchone()
        if frozen is None:
            count, = db.execute('SELECT count(*) FROM bars WHERE period=?', (period,)).fetchone()
            if count >= TARGET:
                raise ValueError('target reached without snapshot')
            return dict(period=period, state='collecting', count=count, target=TARGET)

    digest, payload = frozen
    if sha256(payload).hexdigest() != digest:
        raise ValueError('snapshot hash mismatch')
    snap = json.loads(payload)
    if (snap['schema'] != 1 or snap['period'] != period or snap['policy'] != 'exclude-conflicts-v2'
            or snap['manifest_sha256'] != sha256(manifest).hexdigest() or snap['start_utc'] != meta['start_utc']):
        raise ValueError('snapshot identity mismatch')
    bars = snap['bars']
    exclusions, errors = snap['exclusions'], snap['batch_errors']
    if (len(bars) != TARGET or snap['counts'] != dict(count=TARGET, target=TARGET, state='complete',
            excluded=len(exclusions), batch_errors=len(errors))):
        raise ValueError('snapshot counts mismatch')
    stamps = [bar['begin'] for bar in bars]
    if (stamps != sorted(set(stamps)) or set(stamps).intersection(row['begin'] for row in exclusions)
            or any(row['period'] != period for rows in (bars, exclusions, errors) for row in rows)):
        raise ValueError('snapshot row identity mismatch')

    archives = {}
    for bar in bars:
        run = bar['first_run']
        if not re.fullmatch(r'\d{8}T\d{12}Z', run) or run < boundary.strftime('%Y%m%dT%H%M%S%fZ'):
            raise ValueError('invalid first_run')
        if run not in archives:
            folder = runs / 'sber_observations' / run
            archive = json.loads((folder / 'manifest.json').read_bytes())
            obs = archive['observations'][period]
            raw = (folder / f'{period}.json').read_bytes()
            if (archive['run_id'] != run or archive['ticker'] != 'SBER'
                    or archive['source'] != 'sandbox-invest-public-api.tbank.ru'
                    or archive['instrument_uid'] != 'e6123145-9665-43e0-8413-cd61b8aa9b13'
                    or obs['status'] != 'observed' or sha256(raw).hexdigest() != obs['payload_sha256']):
                raise ValueError('archive identity or checksum mismatch')
            archives[run] = ({row[0]: row[1:] for row in json.loads(raw)['rows']},
                             datetime.fromisoformat(obs['finished_utc']))
        rows, finish = archives[run]
        stamp = datetime.fromisoformat(bar['begin'])
        start = stamp.replace(tzinfo=timezone.utc)
        if (stamp.tzinfo is not None or start < boundary or start + timedelta(minutes=PERIODS[period]) > finish
                or rows.get(bar['begin']) != [bar[key] for key in ('o', 'h', 'l', 'c', 'v')]):
            raise ValueError('bar does not match first observation')
    return dict(period=period, state='verified', count=len(bars), sha256=digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('period', choices=PERIODS)
    parser.add_argument('--runs', type=Path, default=RUNS, help='directory containing the exported cohort and archives')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.runs, args.period)))
    except (ValueError, KeyError, IndexError, TypeError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'inconclusive: {exc}\n')
