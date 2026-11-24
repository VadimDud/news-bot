# SBER first-completion integrity check

From the repository root, run `python3 trading_moex/scripts/verify_sber_snapshot.py 5min`
or replace `5min` with `15min`. This is a manual read-only check, not a scoring job.

- `collecting`: no frozen row and the live count is below target.
- `verified`: the stored blob matches its digest, cohort manifest, period and counts;
  accepted bars match their referenced archive batches. Later live revisions do not
  replace the frozen rows. Keep the returned digest with downstream diagnostics.
- Nonzero exit: missing inputs or inconsistent evidence; do not score.

This is an internal consistency check, not independent attestation. It does not replay
the exclusion policy, establish the training data lineage, or approve paper/live use.
