import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
import pytest

from scripts import collect_sber_2000 as collector
from scripts import verify_sber_snapshot as verifier


def test_first_seen_boundary_and_independent_caps(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, 'TARGET', 2)
    collector.update(tmp_path, init=True)
    cohort = tmp_path / 'sber_forward_2000_v1'
    (cohort / 'manifest.json').write_text(json.dumps({'start_utc': '2026-11-23T12:01:00+00:00'}))
    for hour, minutes, volume in [(13, [0, 15], 42), (14, [15, 30, 45], 99), (15, [15], 42)]:
        run = tmp_path / 'sber_observations' / f'20261123T{hour}0000000000Z'
        run.mkdir(parents=True)
        meta = dict(run_id=run.name, source='sandbox-invest-public-api.tbank.ru',
                    instrument_uid='e6123145-9665-43e0-8413-cd61b8aa9b13', observations={})
        for p in collector.PERIODS:
            rows = [[f'2026-11-23 12:{m:02}:00', 1, 1, 1, 1, volume] for m in minutes]
            if p == '15min' and hour == 14:
                rows[0][-1] = 42
            raw = json.dumps({'rows': rows}).encode()
            (run / (p + '.json')).write_bytes(raw)
            meta['observations'][p] = dict(status='observed', finished_utc=f'2026-11-23T{hour}:00:01+00:00',
                                           payload_sha256=hashlib.sha256(raw).hexdigest())
        (run / 'manifest.json').write_text(json.dumps(meta))
        if hour == 14:
            with sqlite3.connect(cohort / 'collection.db') as db:
                db.execute("CREATE TRIGGER fail_capture BEFORE INSERT ON first_completion WHEN NEW.period='15min' BEGIN SELECT RAISE(ABORT,'simulated failure'); END")
            with pytest.raises(sqlite3.IntegrityError, match='simulated failure'):
                collector.update(tmp_path)
            with sqlite3.connect(cohort / 'collection.db') as db:
                assert db.execute('SELECT count(*) FROM first_completion').fetchone() == (0,)
                assert db.execute('SELECT count(*) FROM bars').fetchone() == (2,)
                db.execute('DROP TRIGGER fail_capture')
        result = collector.update(tmp_path)
        assert [v['count'] for v in result.values()] == ([1, 1] if hour == 13 else [2, 2])
    assert collector.update(tmp_path) == result
    with sqlite3.connect(cohort / 'collection.db') as db:
        assert list(db.execute('SELECT period,begin,v FROM bars ORDER BY period,begin')) == [
            ('15min','2026-11-23 12:15:00',42), ('15min','2026-11-23 12:30:00',99),
            ('5min','2026-11-23 12:30:00',99), ('5min','2026-11-23 12:45:00',99)]
        old, new = db.execute('SELECT old_values,observed_values FROM exclusions').fetchone()
        assert json.loads(old)[-1] == 42 and json.loads(new)[-1] == 99
        assert result['5min']['excluded'] == 1 and result['15min']['excluded'] == 0
        snapshots = dict(db.execute('SELECT period,payload FROM first_completion'))
        for p, payload in snapshots.items():
            assert hashlib.sha256(payload).hexdigest() == result[p]['first_completion_sha256']
            frozen = json.loads(payload)
            assert len(frozen['bars']) == 2 and len(frozen['exclusions']) == result[p]['excluded']
            assert all(row['first_run'] for row in frozen['bars'])
    # Later broker revisions invalidate accepted live bars, not the scoring snapshot.
    run2 = run.with_name('20261123T160000000000Z')
    run2.mkdir()
    meta['run_id'] = run2.name
    for p in collector.PERIODS:
        raw = json.dumps({'rows': [['2026-11-23 12:30:00', 1, 1, 1, 1, 101]]}).encode()
        (run2 / (p + '.json')).write_bytes(raw)
        meta['observations'][p]['payload_sha256'] = hashlib.sha256(raw).hexdigest()
    (run2 / 'manifest.json').write_text(json.dumps(meta))
    latest = collector.update(tmp_path)
    assert all(s['count'] == 1 for s in latest.values())
    with sqlite3.connect(cohort / 'collection.db') as db:
        assert snapshots == dict(db.execute('SELECT period,payload FROM first_completion'))


def test_full_size_snapshots_verify_at_independent_completions(tmp_path):
    collector.update(tmp_path, init=True)
    manifest = tmp_path / 'sber_forward_2000_v1' / 'manifest.json'
    boundary = datetime.fromisoformat(json.loads(manifest.read_bytes())['start_utc'])
    start = boundary.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    frozen5 = None
    for step, ranges in enumerate([{'5min': range(2001), '15min': range(667)},
                                   {'5min': range(2001, 2002), '15min': range(667, 2001)}]):
        finish = start + timedelta(days=(step + 1) * 12)
        run = tmp_path / 'sber_observations' / finish.strftime('%Y%m%dT%H%M%S%fZ')
        run.mkdir(parents=True)
        observations = {}
        for p, indices in ranges.items():
            rows = [[(start + timedelta(minutes=i * collector.PERIODS[p])).strftime('%Y-%m-%d %H:%M:%S'),
                     2, 3, 1, 2, i] for i in indices]
            raw = json.dumps({'rows': rows}).encode()
            (run / f'{p}.json').write_bytes(raw)
            observations[p] = dict(status='observed', finished_utc=finish.isoformat(),
                                   payload_sha256=hashlib.sha256(raw).hexdigest())
        (run / 'manifest.json').write_text(json.dumps(dict(run_id=run.name, ticker='SBER',
            source='sandbox-invest-public-api.tbank.ru', instrument_uid='e6123145-9665-43e0-8413-cd61b8aa9b13',
            observations=observations)))
        status = collector.update(tmp_path)
        for p in collector.PERIODS:
            result = verifier.verify(tmp_path, p)
            if step == 0 and p == '15min':
                assert result == dict(period=p, state='collecting', count=667, target=2000)
            else:
                assert result == dict(period=p, state='verified', count=2000, sha256=status[p]['first_completion_sha256'])
        if step == 0:
            frozen5 = status['5min']['first_completion_sha256']
        else:
            assert status['5min']['first_completion_sha256'] == frozen5
