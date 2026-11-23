import hashlib
import json
import sqlite3

from scripts import collect_sber_2000 as collector


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
