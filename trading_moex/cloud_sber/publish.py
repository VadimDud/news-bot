"""Publish only the SBER ZIP in an isolated worktree; never force a push."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from export import export


def publish():
    root = Path(__file__).resolve().parents[2]
    branch = 'sber-data'
    bundle = Path('trading_moex/cloud_sber/snapshot.zip')
    key = 'sber_forward_2000_v1/status.json'

    def git(*args, cwd=root):
        return subprocess.run(['git', *args], cwd=cwd, text=True, check=True, stdout=subprocess.PIPE).stdout.strip()

    exists = git('ls-remote', '--heads', 'origin', f'refs/heads/{branch}')
    base = branch if exists else 'master'
    git('fetch', 'origin', f'refs/heads/{base}')
    commit = git('rev-parse', 'FETCH_HEAD')
    with TemporaryDirectory() as tmp:
        tree = Path(tmp) / 'tree'
        git('worktree', 'add', '--detach', str(tree), commit)
        try:
            with ZipFile(tree / bundle) as old:
                previous = json.loads(old.read(key))['updated_utc']
            export(tree / bundle)
            with ZipFile(tree / bundle) as new:
                current = json.loads(new.read(key))['updated_utc']
            if datetime.fromisoformat(current) < datetime.fromisoformat(previous):
                raise ValueError('refusing to publish an older cohort')
            if current != previous:
                git('add', '--', str(bundle), cwd=tree)
                git('commit', '-m', f'Update SBER snapshot {current}', '--', str(bundle), cwd=tree)
            elif exists:
                print(f'Already published {current}')
                return
            git('push', 'origin', f'HEAD:refs/heads/{branch}', cwd=tree)
            print(f'Published {current} on {branch}')
        finally:
            git('worktree', 'remove', '--force', str(tree))


if __name__ == '__main__':
    publish()
