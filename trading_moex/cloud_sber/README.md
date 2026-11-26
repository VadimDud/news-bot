# SBER in GitHub Codespaces

`snapshot.zip` is a point-in-time offline copy, not a live database. It contains
the SBER cohort manifest, status, SQLite collection and the candle observations
processed by this collection. It does not contain broker credentials or orders.
The hourly collector continues on the original server, not in Codespaces.

The server publishes to `sber-data` hourly at :15 UTC. To get the latest copy in
a Codespace on `master` without switching branches or changing tracked files,
run from the repository root (Python 3, no installs):

```bash
RUNS=$(mktemp -d)
git fetch origin refs/heads/sber-data
git show FETCH_HEAD:trading_moex/cloud_sber/snapshot.zip > "$RUNS/snapshot.zip"
python3 -m zipfile -e "$RUNS/snapshot.zip" "$RUNS"
python3 -m json.tool "$RUNS/sber_forward_2000_v1/status.json"
python3 trading_moex/scripts/verify_sber_snapshot.py 5min --runs "$RUNS"
python3 trading_moex/scripts/verify_sber_snapshot.py 15min --runs "$RUNS"
```

`updated_utc` dates the published counts. `collecting` means no completed
snapshot exists; the verifier does not certify partial data as a finished set.
Repeat the commands to refresh. Inspect server publication with
`journalctl --user -u sber-cloud-publish.service`; stop scheduling with
`systemctl --user disable --now sber-cloud-publish.timer`. Network failures
do not interrupt collection; the next timer run retries from the remote tip.
