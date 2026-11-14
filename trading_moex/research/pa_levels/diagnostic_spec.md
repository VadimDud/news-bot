# PA-LEVELS-DIAG-004: Frozen Specification

Fixed before execution, 2026-11-10. Diagnostic on already inspected history,
not train/test, not OOS, no parameter selection and no p-values.

Hypothesis: the frozen daily video implementation has positive net mean R
that is not entirely explained by one ticker/winner or random entry timing.
This is an implementation diagnostic, not a test proving presence/absence of edge.

Universe: SBER,LKOH,GAZP,TATN,NVTK,CHMF,NLMK,MOEX,T,MTSS; all stored 1day rows
in data/trader_4h.db, no new downloads. Use full history for causal warmup.
Storage UTC-naive, market calendar Europe/Moscow. HTF explicitly OFF: no daily
higher timeframe available; do not invent a weekly strategy.

Fixed cells: baseline defaults; video compression=1, after_return=1,
impulse=.5, bailout=1, rr=2; video_no_bailout; video_no_impulse.
Other parameters remain PALevelParams defaults. No best-cell selection.
Commission .0005 and slippage .0005 per side; additive price cost, no spread,
borrow, dividends, funding, lot constraints or portfolio allocation model.
Primary metrics: net R mean, median, sum, PF_R, worst R, exit-ordered realised
drawdown R including zero origin; separate calendar-year entry cohorts.
No summation of per-share currency NET across tickers. Capital not modelled.
No-trade reference zero R; buy/hold price return and time exposure descriptive
only, not comparable portfolio returns. No equal-cash or pooled portfolio claim.

Video robustness: leave each ticker out, remove each winning trade individually,
remove top 1 and top 3 winners (R-ranked). Bootstrap 2000 replicates seed 20261110:
IID trade and calendar-year cluster percentile intervals. Few clusters, dependence,
selection/history reuse and sparse trades make these descriptive, not confidence
in a discovered edge or p-values.

Random-entry control: seeds 0..19, one random candidate per executed video trade,
same ticker and Moscow calendar year, exact side, signal-time risk/ATR and
target/risk matched to its template. Random timing after 20 warmup bars.
Risk/target use only sampled bar close and trailing ATR; no next-open knowledge.
Identical execution and costs. Gaps and overlaps may reduce realised counts;
report counts and risk/side distributions, do not retry to force favourable fills.
This is NOT random-level control; conditional matching uses historical template
information and cannot isolate levels or establish a null distribution/p-value.

Execution repairs only: stop gap at open, close-triggered bailout at next open,
reject wrong-side target after entry gap, missing HTF fails loudly, no inferred
last HTF close, remove future-global fbo.empty dependency from compression gate.
Preserve entry-bar bailout exemption, pattern bypass in after-return mode,
historical level snapshots, sweep association and other business semantics.

Checks: synthetic both-side gap/OCO/bailout tests; prefix equivalence of full
signal rows (including brackets); data order, duplicates, finite positive OHLC,
OHLC consistency; positive risk, bracket direction, no overlap/duplicate exits,
R/cost identities. Terminal liquidation labelled eod; MFE/MAE whole exit bar
bounds only, not a known intrabar path. Margin/risk budgets not modelled.
Stop on failed integrity/execution checks; preserve failed run. Do not expand grid
if sparse or negative. A positive mean surviving removals/control is at most a
reason for prospective work, not validation; a negative mean is not proof of no edge.

Limitations: daily OHLC ambiguity, reused data, detector semantics not a faithful
guarantee of the video, missing carry and corporate-action audit, sparse sample.
Next step: obtain a genuinely uninspected, timestamp-bounded forward sample under
the same frozen specification before any confirmatory inference.
