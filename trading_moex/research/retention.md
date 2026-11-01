# Research Retention And Cleanup

## Storage Classes

| Class | Location | Git policy | Retention |
|---|---|---|---|
| Study knowledge | `research/` | commit | permanent while relevant |
| Run provenance and approved summaries | `artifacts/runs/` | local, back up deliberately | permanent for cited runs |
| Full ledgers and input snapshots | `artifacts/runs/` | local, compressed | keep for key and failed runs; do not delete cited evidence |
| Rebuildable cache | `artifacts/cache/` | ignored | delete after 14 days if unused |
| Scratch output | `artifacts/scratch/` | ignored | delete after 14 days |
| Figures and verbose logs | run directory | ignored | delete after 90 days if not cited |
| Cleanup candidates | `artifacts/quarantine/` | ignored | review for 30 days before deletion |

The existing `data/` databases remain source data and are not cleaned by this
policy. Do not move or delete them without a separate migration plan.

## Safe Cleanup

Cleanup is dry-run by default. A cleanup report must list exact paths, size,
reason, age, and the durable run or decision that replaces each item.

1. Never delete active runs, cited evidence, study specifications, source data,
   secrets, or files with unclear ownership.
2. Do not follow symlinks outside the artifact root.
3. Move approved candidates to `quarantine/` first.
4. Delete only after the quarantine period and a second explicit approval.
5. Remove duplicates only after comparing hashes and preserving one provenance
   record.

No agent may run a destructive cleanup command or use `git clean` as part of
research housekeeping without explicit user approval.
