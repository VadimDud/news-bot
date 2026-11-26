# SBER archive cohort: diagnostic scoring contract v1

Scope: `sber_forward_2000_v1`, separately for 5min and 15min. This is not
enrollment or a continuation of the stopped studies. No model training or
scoring at intermediate counts; no automatic paper or live orders.

Use the first committed collector update at 2000 accepted bars per period.
Preserve accepted rows, exclusions, first-run provenance and counts from that
version in an immutable fingerprinted snapshot. If that exact version is
unavailable and cannot be reconstructed from verified archive batches, report
inconclusive; do not substitute the latest database. Later broker revisions
stay in the archive. The collector inserts the canonical JSON payload and
its SHA-256 into `collection.db:first_completion` inside the same SQLite
transaction as the accepted bars. Use the period-specific blob, not the live
`bars` table; `status.json` only advertises the digest. On read, verify it
against the actual bytes before scoring. This guards against routine updates,
not deliberate replacement of the database by an administrator.

Bind the matching frozen historical enrollment, calendar, parameters and
environment by ID and hash. Train and scale only on the original historical
partition (500 bars plus causal warmup, sequence length 50). Apply the
dividend outcome mask. For each accepted decision the binary target is a
close-to-close return strictly above 0.004 over 15 bars (5min) or 5 bars
(15min). Use the exclusion-aware cohort loader: restart warmup at each
recorded exclusion, never bridge gaps in features or labels. Do not extend
the snapshot to replace lost windows. Score all retained decision times;
10:00-19:00 Moscow is an execution filter, not a classification filter.

Hypothesis per period: LSTM has strictly lower binary log loss than BOTH
L2 logistic regression on the same flattened inputs (lr 0.05, 300 epochs,
L2 1.0) and the constant positive-label fraction from training. Use the
project's classification_metrics clipping. Require identical ordered decision
and outcome timestamps and labels for all three; never silently intersect
different ledgers. Compare unrounded mean losses. Report both differences
(LSTM minus baseline); a tie or loss against either is not an improvement.
Report class balance, scored sample count, exclusions, balanced accuracy
and confusion matrix at 0.5 as diagnostics, not alternative pass criteria.

Missing provenance, class coverage, invalid/nonfinite labels, probabilities
or scores, boundary violations or mismatched keys make the result inconclusive.
Do not retune, rerun on a new boundary, pool periods or select the better one.
Overlapping labels are not independent trials: a lower point estimate is not
statistical confirmation or evidence of executable profitability.

Next step: implement a read-only snapshot verifier before terminal scoring.
