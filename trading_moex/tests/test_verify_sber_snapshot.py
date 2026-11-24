import json
import sqlite3
from hashlib import sha256

import pytest

from scripts import verify_sber_snapshot as verifier


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, 'TARGET', 1)
    run = '20261124T071000160827Z'
    root = tmp_path / 'sber_forward_2000_v1'
    root.mkdir()
    archive = tmp_path / 'sber_observations' / run
    archive.mkdir(parents=True)
    start = '2026-11-24T06:00:00+00:00'
    stamp = '2026-11-24 07:00:00'
    manifest = json.dumps(dict(ticker='SBER', orders_enabled=False, periods=['5min', '15min'],
                               target=1, start_utc=start)).encode()
    (root / 'manifest.json').write_bytes(manifest)
    raw = json.dumps({'rows': [[stamp, 2, 3, 1, 2, 100]]}).encode()
    (archive / '5min.json').write_bytes(raw)
    obs = dict(status='observed', finished_utc='2026-11-24T07:10:01+00:00', payload_sha256=sha256(raw).hexdigest())
    (archive / 'manifest.json').write_text(json.dumps(dict(run_id=run, ticker='SBER', observations={'5min': obs},
        instrument_uid='e6123145-9665-43e0-8413-cd61b8aa9b13', source='sandbox-invest-public-api.tbank.ru')))
    snap = dict(schema=1, period='5min', policy='exclude-conflicts-v2', manifest_sha256=sha256(manifest).hexdigest(),
                start_utc=start, exclusions=[], batch_errors=[], counts=dict(count=1, target=1, state='complete',
                excluded=0, batch_errors=0), bars=[dict(period='5min', begin=stamp, o=2, h=3, l=1, c=2, v=100, first_run=run)])
    dbpath = root / 'collection.db'
    with sqlite3.connect(dbpath) as db:
        db.execute('CREATE TABLE first_completion(period,sha256,payload)')
        db.execute('CREATE TABLE bars(period)')
    return tmp_path, dbpath, snap


@pytest.mark.parametrize('fault', [None, 'hash', 'period', 'manifest_sha256', 'bar'])
def test_frozen(cohort, fault):
    runs, path, snap = cohort
    if fault in ('period', 'manifest_sha256'):
        snap[fault] = 'wrong'
    if fault == 'bar':
        snap['bars'][0]['v'] += 1
    raw = json.dumps(snap).encode()
    digest = 'wrong' if fault == 'hash' else sha256(raw).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO first_completion VALUES(?,?,?)', ('5min', digest, raw))
    before = path.read_bytes()
    if fault:
        with pytest.raises(ValueError):
            verifier.verify(runs, '5min')
    else:
        assert verifier.verify(runs, '5min')['sha256'] == digest
    assert path.read_bytes() == before


def test_missing_snapshot(cohort):
    runs, path, _ = cohort
    assert verifier.verify(runs, '15min')['state'] == 'collecting'
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO bars VALUES('15min')")
    with pytest.raises(ValueError, match='target reached'):
        verifier.verify(runs, '15min')
