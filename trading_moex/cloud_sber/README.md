# SBER in GitHub Codespaces

`snapshot.zip` is a point-in-time offline copy, not a live database. It contains
the SBER cohort manifest, status, SQLite collection and the candle observations
processed by this collection. It does not contain broker credentials or orders.
The hourly collector continues on the original server, not in Codespaces.

In a Codespace on `master`, run from the repository root (Python 3, no installs):

```bash
RUNS=$(mktemp -d)
python3 -m zipfile -e trading_moex/cloud_sber/snapshot.zip "$RUNS"
python3 -m json.tool "$RUNS/sber_forward_2000_v1/status.json"
python3 trading_moex/scripts/verify_sber_snapshot.py 5min --runs "$RUNS"
python3 trading_moex/scripts/verify_sber_snapshot.py 15min --runs "$RUNS"
```

`updated_utc` dates the published counts. `collecting` means no completed
snapshot exists; the verifier does not certify partial data as a finished set.
After a newer copy is published, pull and extract to a fresh temporary directory.
