# LSTM SBER Paper Execution

Status: **pre-registered diagnostic protocol**. This document does not
authorize orders or model promotion.

The simulator consumes a frozen prospective prediction file. It does not train
models or select thresholds from forward results.

## Rules

- `p >= 0.55`: buy SBER shares.
- `p <= 0.45`: sell a SBER futures contract (short futures).
- Contract selection for future paper studies: rank only T-Bank contracts on
  ordinary SBER shares, not SBERP. Compare lagged two-sided quote availability,
  relative spread and executable depth for the intended notional in the Moscow
  window; confirm traded turnover in comparable RUB units. Prefer a verified
  perpetual only when liquidity is comparable. Include its funding/carry in
  costs; do not interpret a far-future API expiry by itself as proof of terms.
  Archive candidates before choosing; one book snapshot is not a ranking.
- Otherwise: no position.
- Enter at the next completed candle open; no same-candle execution.
- Execution window (Europe/Moscow, no weekday filter): enter no earlier than
  10:00 and only if the full horizon fits by 19:00. Entry must immediately
  follow the signal bar. Exit at the close of decision bar + horizon, i.e.
  75 minutes after entry for either timeframe. Last eligible entry: 17:45.
  Ledger timestamps remain UTC-naive; exit denotes close time, not bar start.
  Missing holding bars invalidate the run rather than carrying overnight.
  The clock filter is not proof of broker availability or sufficient liquidity.
- Exit at the completed candle close after the frozen model horizon: 5 bars for
  15-minute study, 15 bars for 5-minute study.
- One position at a time per independent leg; this is not a pooled portfolio.
  Fixed quantity: one share or one futures contract. Stock lots are not modeled.
  No pyramiding, overnight special handling, or order retries.
- Shares use 0.05% commission and 0.05% slippage per side.
- Futures use 0.02% commission and 0.02% slippage per side. Explicit CLI inputs
  are required: `--futures-contract`, `--futures-multiplier` (RUB per quoted
  price point), `--futures-initial-margin` (RUB per contract), and
  `--futures-expiry` (UTC-naive). All input bars must precede expiry.
  Entries require available realized cash to cover fixed margin plus entry fee.
  Margin is not a loss cap; intratrade margin calls are not modeled.
- Open positions are force-closed at the final available close and reported
  separately as forced exits. No open position is silently counted as realized.

## Required Input

CSV columns: `timestamp,open,high,low,close,probability,futures_open,futures_close`. Timestamps are
UTC-naive SQLite-compatible values, sorted and unique. The prediction file must
be produced by the frozen prospective runner and must retain its manifest,
model commit, database hash, and study horizon. Futures prices must be aligned
to the same timestamps and belong to the named contract; spot substitution is
forbidden. The validated producer/join and price provenance remain pending.

## Required Outputs

The run writes a manifest, checks, metrics and compressed trade ledger. It
reports each leg separately, including realized PnL, unrealized PnL, costs,
exposure, return on exposure, drawdown, trade count, win rate and profit factor.

This study cannot establish profitability until predictions come from the
completed prospective evaluation and does not model bid/ask depth, contract
expiry/roll, variation margin, or broker-specific fills. Returns use separate
initial cash per leg; drawdown is realized-close only. Forced exits are included
in aggregate PnL and also reported as `forced_exit_pnl`. Exposure return divides
PnL by time-averaged notional across input bars (not annualized). Horizons count
rows, including session gaps; no claim of elapsed-time equivalence is made.

Limitations: diagnostic only; full provenance and execution gates remain open.
The exporter writes `predictions.jsonl` separately. Use
`join_lstm_paper_inputs.py --prediction-manifest <export>/manifest.json` to
bind that ledger to the completed evaluation before joining futures prices.
See `LIVE_READINESS.md`.

## Diagnostic Input Bridge

`scripts/join_lstm_paper_inputs.py` accepts `--evaluation-dir`, `--predictions`,
`--futures` and a new `--output` directory. It writes `paper_input.csv` and
`join_manifest.json`. The evaluation must be completed with exit status zero
and UTC-naive storage. For diagnostic exports, the separate prediction
manifest binds `predictions_ledger_sha256` and `evaluation_manifest_sha256`;
the old prospective evaluation manifest intentionally has no prediction hash.
Prediction JSONL requires `partition=forward`, `decision_timestamp` and finite
`probability`. Futures CSV requires `timestamp,open,close`; its adjacent
`<stem>.manifest.json` requires `instrument_type=futures`, `contract`, `source`,
`storage_timezone=UTC-naive` and matching `data_sha256`.

All three timestamp sequences must match exactly. No filling, interpolation,
dropping bars, or stock-price fallback is permitted. Prices are validated.
Hashes bind supplied bytes, not authenticity of the source or model execution.
Enrollment replay, instrument metadata verification and full run provenance
remain unimplemented; bridge outputs are diagnostic only.

Existing frozen prospective runners do not emit a prediction ledger or its
hash. Their classification samples also exclude boundary/dividend outcomes,
so an offline classification ledger is not a full-bar execution ledger.
The bridge intentionally rejects those artifacts; do not fabricate missing
probabilities, manually add hashes to old manifests, or modify frozen runners.

The diagnostic export is a separate retraining path, not the original
prospective model evaluation, and does not authorize execution.
