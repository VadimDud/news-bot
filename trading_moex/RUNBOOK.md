# MOEX Trader Runbook

## Safe rollout

1. Keep `TRADER_DRY_RUN=true` and verify the dashboard, watchlist, signals,
   reconciliation status and risk metrics.
2. Run dry-run through at least one complete market session. Confirm that the
   strategy uses only closed candles and that no order is sent.
3. Verify the broker portfolio manually and resolve any reconciliation issue.
4. Test the circuit breaker with a low-risk configuration in a non-production
   account or by unit/integration tests. Confirm that entries stop while exits
   remain available.
5. Use sandbox or a dedicated test account before enabling real orders.
6. Enable LIVE only with a separate API token, a strong
   `TRADER_WEB_PASSWORD`, and small position limits.

## Required safeguards

- `TRADER_DRY_RUN=true` by default.
- `TRADER_MAX_POSITION_PCT` must be greater than zero and no more than 100.
- Keep both circuit-breaker limits enabled:
  `TRADER_MAX_DAILY_LOSS_PCT` and `TRADER_MAX_DRAWDOWN_PCT`.
- Do not change strategy or mode while the live cycle is running.
- Stop the cycle before manually resetting the circuit breaker.

## Incident response

1. Press **Stop** in the dashboard.
2. Do not reset the circuit breaker until the broker portfolio, open orders and
   local `live_entries` state have been compared.
3. If state differs, keep LIVE disabled and resolve the position manually.
4. Review the journal and broker order history, including `order_id` and fill
   quantity.
5. Reset the circuit breaker only after the cause is understood.
6. Restart in dry-run and confirm reconciliation before any live restart.

## Operational checks

- Dashboard port is protected by `TRADER_WEB_PASSWORD` and should not be
  exposed directly to the public internet without HTTPS or a private network.
- Never put API tokens or passwords in logs, commits, screenshots or tickets.
- Back up the trader SQLite database before upgrades.
- After deployment run `pytest tests/ -q` inside `trading_moex` and check the
  Docker health endpoint on port `8081`.
