"""One-shot SBER sandbox observation. No study database, worker or timer."""
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


def snapshot():
    scripts = Path(__file__).resolve().parent
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).isoformat()
    run = scripts.parent / 'artifacts/runs/sber_observations' / now.strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    manifest = dict(run_id=run.name, requested_start_utc=start, ticker='SBER',
                    instrument_uid='e6123145-9665-43e0-8413-cd61b8aa9b13',
                    source='sandbox-invest-public-api.tbank.ru', storage_timezone='UTC-naive',
                    market_timezone='Europe/Moscow', study_admission=False, observations={})
    for period, script in [('5min', 'lstm_sandbox_collect_5min.py'), ('15min', 'lstm_sandbox_collect.py')]:
        observation = manifest['observations'][period] = dict(started_utc=datetime.now(timezone.utc).isoformat())
        try:
            code = (scripts / script).read_bytes()
            observation['collector_sha256'] = hashlib.sha256(code).hexdigest()
            response = subprocess.run(['docker', 'exec', '-i', 'trader-bot-engine', 'python', '-B', '-', start],
                                      input=code, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                      timeout=90, check=True)
            batch = json.loads(response.stdout)
            rows = batch['rows']
            digest = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
            if batch['source'] != manifest['source'] or digest != batch['source_sha256']:
                raise ValueError('invalid collector envelope')
            with (run / f'{period}.json').open('xb') as out:
                out.write(response.stdout)
            observation.update(status='observed' if rows else 'empty', rows=len(rows),
                               rows_sha256=digest, payload_sha256=hashlib.sha256(response.stdout).hexdigest())
        except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
            observation.update(status='failed', error_type=type(exc).__name__)
        observation['finished_utc'] = datetime.now(timezone.utc).isoformat()
    with (run / 'manifest.json').open('x') as out:
        json.dump(manifest, out, indent=2)
    print(json.dumps(manifest))
    return int(any(o['status'] != 'observed' for o in manifest['observations'].values()))


if __name__ == '__main__':
    raise SystemExit(snapshot())
