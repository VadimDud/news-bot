# Sandbox Revision Incident

The 5min collector stopped at run `20261118T000040161628Z` after detecting a
revision of the completed `2026-11-17 12:25:00` UTC candle. Earlier batches and
the frozen enrollment history recorded OHLCV
`296.64, 296.87, 296.60, 296.87, 29179`; the failed batch recorded
`296.76, 296.87, 296.76, 296.87, 15511`.

This is a price and volume revision, not floating-point noise. The candle is
within the training history frozen by enrollment
`20261117T143613980241Z_LSTM-PROSPECTIVE-5MIN_enroll` at commit `926f9dc`.
The worker rejected the batch without overwriting the stored candle.

The STOP guard remains in place. Repeated scheduled invocations now exit
nonzero rather than reporting success while skipping collection. Neither the
enrollment manifest nor the frozen runner has been modified. No replacement
enrollment, forward-boundary change, or automatic retry of evaluation is allowed.

Limitations: the cause of the upstream revision is not established. Ignoring
historical revisions would change the declared collection policy; querying only
new timestamps would hide revisions rather than resolve them.

Next step: obtain an explicit reviewed data-revision policy before resuming the
5min study. The independent 15min study is not changed by this incident fix.
