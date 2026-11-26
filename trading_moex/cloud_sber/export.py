"""Export only the research cohort and its processed candle batches (offline copy)."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile


def export(output=None):
    here = Path(__file__).resolve().parent
    runs = here.parent / 'artifacts/runs'
    cohort = runs / 'sber_forward_2000_v1'
    output = output or here / 'snapshot.zip'
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        dbfile = Path(tmp) / 'collection.db'
        db = sqlite3.connect(dbfile)
        src = sqlite3.connect((cohort / dbfile.name).as_uri() + '?mode=ro', uri=True)
        src.backup(db)
        src.close()
        tables = {name for name, in db.execute("select name from sqlite_master where type='table'")}
        if tables != {'bars', 'processed', 'processed_v2', 'exclusions', 'batch_errors', 'first_completion'}:
            raise ValueError('unexpected database schema')
        manifests = list(db.execute('select run from processed_v2 order by run'))
        status = (cohort / 'status.json').read_bytes()
        for p, stats in json.loads(status)['periods'].items():
            for table, key in [('bars', 'count'), ('exclusions', 'excluded'), ('batch_errors', 'batch_errors')]:
                if db.execute(f'select count(*) from {table} where period=?', (p,)).fetchone()[0] != stats[key]:
                    raise ValueError('status changed during export; retry')
        db.execute('VACUUM')
        db.close()
        bundle = Path(tmp) / 'snapshot.zip'
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as out:
            out.write(dbfile, cohort.name + '/collection.db')
            out.writestr(cohort.name + '/status.json', status)
            out.write(cohort / 'manifest.json', cohort.name + '/manifest.json')
            for run, in manifests:
                if not re.fullmatch(r'\d{8}T\d{12}Z', run):
                    raise ValueError('unexpected archive id')
                folder = runs / 'sber_observations' / run
                path = folder / 'manifest.json'
                meta = json.loads(path.read_bytes())
                if meta['ticker'] != 'SBER' or meta['run_id'] != run:
                    raise ValueError('unexpected archive identity')
                out.write(path, path.relative_to(runs))
                for p in ('5min', '15min'):
                    path = folder / (p + '.json')
                    obs = meta['observations'][p]
                    if 'payload_sha256' not in obs:
                        if obs['status'] == 'observed':
                            raise ValueError('missing archive digest')
                        continue
                    raw = path.read_bytes()
                    if (hashlib.sha256(raw).hexdigest() != obs['payload_sha256'] or
                            set(json.loads(raw)) != {'source', 'rows', 'source_sha256'}):
                        raise ValueError('unexpected archive payload')
                    out.writestr(str(path.relative_to(runs)), raw)
        bundle.replace(output)
    print(f'Exported {len(manifests)} SBER observation batches')


if __name__ == '__main__':
    export()
