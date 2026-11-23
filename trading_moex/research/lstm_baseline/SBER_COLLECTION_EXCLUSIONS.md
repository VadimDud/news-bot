# Collection-only exclusion policy (v2)

The active `sber_forward_2000_v1` archive cohort retains its original start
boundary. On a conflicting OHLCV observation, record the period, timestamp,
first and conflicting values and archive run IDs in `collection.db:exclusions`.
Remove that key only from the derived `bars` sample, never from source batches.
Even a later reversion does not readmit it. A known timestamp with invalid
OHLCV is likewise excluded. Distinct timeframes are independent. An empty,
failed or checksum-invalid period batch is not evidence that a bar changed.

Count at most 2000 accepted timestamps per period. Keep comparing accepted
keys on future archive overlap even at the cap; replace exclusions with later
eligible observations. Status is as-of the last processed snapshot, not a
frozen evaluation dataset. Re-process archived observations from the original
boundary once on policy upgrade. Never fill exclusion gaps, and do not treat
either side of a gap as adjacent in downstream features or outcome windows.

`app.sber_cohort.cohort_partitions` reads bars and explicit exclusions in one
read-only transaction, splitting each timeframe before feature computation.
Each segment warms up independently. The caller supplies a scaler fitted on
separate training history and any dividend dates. Normal session breaks alone
do not split this bar-based diagnostic. Missing bars without a recorded
exclusion are not detected by this rule. This loader is not a study enrollment.

Limits: observations outside the collector overlap may not expose a revision.
STOPs, incident reports, enrollment and evaluation rules of the separate
frozen prospective studies are unchanged.
