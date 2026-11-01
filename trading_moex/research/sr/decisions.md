# SR-001 Decisions

## 2026-11-01: Keep Research-Only

The strategy remains outside live/default production paths. Historical positive
results are unstable across periods and costs, and the current backtest does not
fully model execution. Re-run only after the blocking audit and with complete
run provenance.

## 2026-11-01: Baseline Re-Run Fails Gates

The blocking execution audit is closed (15/15 gates, `audit.md`) and the
strategy implementation is now committed (`a9d3747`), so `SR-001-baseline.yaml`
was executed reproducibly on `data/trader_4h.db`, `15min`, ten tickers,
`scenario_mode=2`, split boundary `2026-04-01`.

Full period, cost sweep (`commission` x `slippage` per side):

| commission | slippage | pooled return | PF    | trades |
|-----------:|---------:|--------------:|------:|-------:|
|     0.0000 |   0.0005 |       -0.3705% | 0.924 |    122 |
|     0.0000 |   0.0010 |       -1.0775% | 0.803 |    122 |
|     0.0005 |   0.0005 |       -1.5052% | 0.737 |    122 |
|     0.0005 |   0.0010 |       -2.2106% | 0.651 |    122 |
|     0.0010 |   0.0005 |       -2.6505% | 0.599 |    122 |
|     0.0010 |   0.0010 |       -3.3465% | 0.536 |    122 |

Split halves at `commission=0.0005`, `slippage=0.0005`:

| split | pooled return | PF    | trades | wins |
|-------|--------------:|------:|-------:|-----:|
| train |       -0.0372% | 0.983 |     53 |   13 |
| test  |       -1.1543% | 0.656 |     67 |   12 |

Every cell is negative, including zero commission, so the result is not a cost
artefact. The win rate is 24/122 (19.7%) at `min_rr` targets — the target is
effectively unreachable while stops fill. The legacy `+4.87%` train / `+0.99%`
test figures are not reproduced and should be treated as withdrawn.

Decision: `SR-001-baseline` is **rejected**. Do not promote to live/defaults and
do not run the ablations: the baseline has no edge to ablate. The study rules
cap the first comparison at "no more than twelve" predeclared ablations but
never enumerated them, so no named ablation is being skipped here; the blocking
observation is the zero-commission result. Reopening requires a materially
different mechanism (e.g. real D1/H4 levels plus M15 execution, or confirmed
candle reactions instead of swing counts), not new parameter values on this one.
