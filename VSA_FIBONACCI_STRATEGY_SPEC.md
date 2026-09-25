# Executable Technical Specification: VSA + Fibonacci Cycles

**Status:** normative implementation contract

**Instrument:** MOEX equity `T` (T-Technologies / T-Bank group, board and security
metadata MUST be resolved through the MOEX instrument reference; the strategy MUST halt
if the resolved security is not exactly `T`)

**Signal timeframe:** 15 minutes

**Context timeframe:** completed 4-hour bars with a causal 90-calendar-day lookback,
aligned to the MOEX exchange calendar

**Signal data:** all available validated feeds: OHLCV, trades/ticks with aggressor
classification, and L2 order-book snapshots. The strategy has explicit feature modes so
that missing optional feeds cannot be silently replaced with fabricated values.

**Direction:** long only

**Capital:** initial equity `1,000,000 RUB`; no leverage (`max_leverage = 1.0`)

**Default mode:** one position maximum, no averaging, no pyramiding, no overnight carry.
The production mode is selected from the validated parameter grid in Section 1.8; it is
not allowed to change parameters after OOS approval.

All times in this document are UTC. All timestamps are timezone-aware ISO-8601 values. A
15-minute bar ending at timestamp `t` covers `(t - 15 minutes, t]`. A signal is evaluated
only after the bar is closed. The implementation MUST NOT use a field of bar `t` before
the close event for that bar has been received.

The exchange calendar and the contract metadata (`tick_size`, `lot_size`, trading-session
boundaries, shortability, trading status) MUST be loaded from the broker/exchange adapter.
If any of those values is missing or stale, the system MUST refuse new orders. The
strategy does not infer tick or lot size from OHLCV.

## 1. Formal Signal Mathematics

### 1.1 Bar validity and indexing

For every bar `t`, define:

```text
O_t = open price
H_t = high price
L_t = low price
C_t = close price
V_t = volume

valid_t = (0 < L_t <= min(O_t, C_t) <= max(O_t, C_t) <= H_t)
           AND (V_t > 0)
```

The implementation MUST reject a bar if `valid_t` is false, if any value is NaN or
infinite, or if `C_t <= 0`. Rejected bars are not forward-filled.

The expected interval between adjacent bars inside one exchange session is exactly
900 seconds. A larger interval is a data gap unless the exchange calendar explicitly
marks the interval as a scheduled break. A gap inside a session invalidates all rolling
features spanning the gap and resets the cycle detector. The detector then requires
`max(20, 14) + 1 = 21` consecutive valid bars before producing a new signal.

For each valid non-first bar:

```text
price_change_t = C_t - C_(t-1)
dir_t   = +1 if price_change_t > 0
           -1 if price_change_t < 0
            0 otherwise

R_t     = H_t - L_t
B_t     = abs(C_t - O_t)
U_t     = H_t - max(O_t, C_t)
D_t     = min(O_t, C_t) - L_t
```

`R_t = 0` is valid for storage but cannot be a VSA signal bar. `dir_t = 0` is a doji and
breaks a directional run.

### 1.2 True range and causal rolling features

For `t > 0`:

```text
TR_t = max(H_t - L_t,
           abs(H_t - C_(t-1)),
           abs(L_t - C_(t-1)))
```

The default causal features at bar `t` exclude bar `t` from every rolling average:

```text
ATR_t     = mean(TR_(t-14), ..., TR_(t-1))
VMA_t     = mean(V_(t-20),  ..., V_(t-1))
volume_ratio_t = V_t / VMA_t
```

The values are defined only when all source bars are valid, contiguous within the same
session, and `ATR_t > 0`, `VMA_t > 0`. No population standard deviation, interpolation,
or zero replacement is permitted.

The strategy deliberately does not use a price z-score. A volume anomaly is defined only
by the ratio to causal `VMA_t`.

### 1.3 4-hour trend context

Let `h(t)` be the most recently completed 4-hour bar whose close timestamp is strictly
before the close timestamp of 15-minute bar `t`. The current, still-forming 4-hour bar is
never used. For 4-hour bars define:

```text
EMA^H_n(h) = C^H_h                                  if h = first valid bar
EMA^H_n(h) = alpha_n * C^H_h + (1-alpha_n) * EMA^H_n(h-1)
alpha_n = 2 / (n + 1)

O^H_h = first open, H^H_h = maximum high, L^H_h = minimum low,
C^H_h = last close of 15-minute bars in the 4-hour interval.
```

The 4-hour context is valid only after 200 completed 4-hour bars exist in the preceding
90 calendar days and all source bars are valid. Define the long-only regime:

```text
context_bull = (C^H_h > EMA^H_50(h))
               AND (EMA^H_20(h) > EMA^H_50(h))
               AND (EMA^H_50(h) > EMA^H_200(h))
               AND (EMA^H_20(h) > EMA^H_20(h-1))
```

`context_bull` is a mandatory entry condition in every candidate model. If the 4-hour
context is unavailable or false, no long entry is allowed. 4-hour bars are resampled from
15-minute data using first open, maximum high, minimum low, last close, and sum of volume;
an incomplete interval is invalid rather than forward-filled.

### 1.4 VSA feature flags

The following normalized quantities are used when `R_t > 0`:

```text
body_range_t = B_t / R_t
upper_range_t = U_t / R_t
lower_range_t = D_t / R_t
range_atr_t = R_t / ATR_t
body_atr_t = B_t / ATR_t
```

The raw event gate is:

```text
volume_anomaly_t = (volume_ratio_t >= 2.5)
```

The exact requested feature flags are:

```text
absorption_flag_t = volume_anomaly_t
                    AND (R_t <= 0.7 * ATR_t)
                    AND (B_t <= 0.4 * ATR_t)

rejection_flag_t = volume_anomaly_t
                   AND (body_range_t <= 0.3)
                   AND ((U_t >= 0.6 * R_t) OR (D_t >= 0.6 * R_t))

momentum_flag_t = volume_anomaly_t
                  AND (R_t >= 1.5 * ATR_t)
                  AND (body_range_t >= 0.7)
```

The mutually exclusive `vsa_category_t` is assigned in this order:

```text
if momentum_flag_t:  MOMENTUM
elif rejection_flag_t: REJECTION
elif absorption_flag_t: ABSORPTION
else: NONE
```

The category priority is normative. The individual raw flags MUST remain available in
the event record. `rejection_side_t` is:

```text
UPPER if U_t >= 0.6 * R_t and U_t > D_t
LOWER if D_t >= 0.6 * R_t and D_t > U_t
BOTH  if U_t >= 0.6 * R_t and D_t >= 0.6 * R_t
NONE  otherwise
```

For a `BOTH` rejection, no pullback entry is allowed because the rejected side is
ambiguous. A doji (`dir_t = 0`) is recorded but cannot create an entry.

### 1.5 Optional trade-flow and order-book features

The complete research matrix MUST evaluate the following feed modes separately:

```text
M0 = OHLCV only
M1 = OHLCV + classified trades/ticks
M2 = OHLCV + L2 snapshots
M3 = OHLCV + classified trades/ticks + L2 snapshots
```

An absent feed is `unavailable`, never zero. A candidate requiring an unavailable feed is
not evaluated for that bar. Feed availability and staleness are reported per trade.

For every classified trade `j` inside bar `t`, `p_j` is price, `q_j > 0` is quantity, and
`s_j` is `+1` for buyer-initiated, `-1` for seller-initiated, or `0` for unknown. A trade
is included only if its timestamp is within the bar interval and its classification is
authoritative from the feed. Define:

```text
buy_volume_t  = sum(q_j where s_j = +1)
sell_volume_t = sum(q_j where s_j = -1)
known_volume_t = buy_volume_t + sell_volume_t
flow_delta_t  = buy_volume_t - sell_volume_t
delta_ratio_t = flow_delta_t / known_volume_t, when known_volume_t > 0
```

The tick-flow feature is valid only when `known_volume_t / V_t >= 0.80`. Otherwise the
feature is unavailable. Its causal rolling z-score is:

```text
mu_delta_t = mean(flow_delta_(t-20), ..., flow_delta_(t-1))
sd_delta_t = sqrt(sum((flow_delta_i - mu_delta_t)^2 for i=t-20..t-1) / 20)
delta_z_t  = (flow_delta_t - mu_delta_t) / sd_delta_t, when sd_delta_t > 0
```

For an L2 snapshot `k` at or before close `t`, use the first `L=5` price levels on each
side, with bid prices `b_i`, bid sizes `B_i`, ask prices `a_i`, and ask sizes `A_i`:

```text
mid_k = (b_1 + a_1) / 2
spread_rate_k = (a_1 - b_1) / mid_k
book_imbalance_k = (sum(B_i, i=1..5) - sum(A_i, i=1..5)) /
                   (sum(B_i, i=1..5) + sum(A_i, i=1..5))
```

The snapshot is valid only when all ten sizes are nonnegative, all prices are positive,
`b_1 < a_1`, and snapshot age is at most 30 seconds at bar close. For bar `t`, use the
last valid snapshot in `(t-30 seconds, t]`.

```text
book_long_t = (book_imbalance_t >= +0.20) AND (spread_rate_t <= 0.0020)
flow_long_t = (delta_ratio_t >= +0.10) AND (delta_z_t >= +0.50)
```

The L2 and trade-flow values are used only by candidate modes `M1`–`M3`; they are never
backfilled from future snapshots or inferred from candle range.

### 1.6 Candidate confirmation rules

The base VSA flags remain unchanged. The candidate gate is:

```text
M0: confirmation = TRUE
M1: confirmation = flow_long_u
M2: confirmation = book_long_u
M3: confirmation = flow_long_u AND book_long_u
```

Here `u` is the completed confirmation bar defined below. A no-flow ablation is labeled
`M0`; its result MUST NOT be merged with M1–M3 statistics.

### 1.7 Causal Fibonacci time-cycle detector

The allowed exact run lengths are:

```text
F = {1, 2, 3, 5, 8, 13}
```

A directional run is a maximal contiguous sequence of bars with the same nonzero
`dir`. A zero-direction bar terminates both the previous run and any possible cycle.

At close of bar `c`, a completed cycle candidate is recognized only if the following
conditions hold:

1. An impulse run occupies bars `a ... e`, where `e < c` and every `dir_i = d`.
2. Its length is `p = e - a + 1` and `p in F`.
3. A correction run occupies bars `e+1 ... c`, every `dir_i = -d`.
4. Its length is `q = c - e` and `q in F`.
5. Bar `c+1` closes with `dir_(c+1) = d`; this is the mandatory confirmation bar.
6. The bar sequence contains no invalid bar, gap, session boundary, or zero direction
   between `a` and `c+1`.

The cycle is first actionable at the close of `c+1`; it cannot be known at the close of
`c` because the correction might continue. The cycle endpoint price and correction
depth are computed without using the confirmation bar:

```text
S = C_(a-1)                  # impulse start reference
E = C_e                      # impulse endpoint

if d = +1:
    X = min(L_(e+1), ..., L_c)
    impulse_size = E - S
    depth = (E - X) / impulse_size
else:
    X = max(H_(e+1), ..., H_c)
    impulse_size = S - E
    depth = (X - E) / impulse_size
```

The candidate is valid only if `impulse_size > 0` and `0 <= depth <= 0.618`. A cycle
with depth above `0.618` is classified as invalidated and cannot create a signal. The
confirmation bar is not part of the correction depth.

The detector MUST emit each `(a, e, c, p, q, d)` cycle at most once. After emission,
the next candidate must start after `c+1`; overlapping duplicate interpretations of the
same run are forbidden.

### 1.8 Entry setup definitions

There are two setup families. Both use the same completed cycle, depth filter, and
`context_bull_u` condition. Since the strategy is long-only, bearish cycles are context
only and cannot create an entry.

#### Pullback setup

At close `c+1`, use the VSA event on correction endpoint `c`:

```text
pullback_long = (d = +1)
                 AND context_bull_u
                 AND (vsa_category_c in {ABSORPTION, REJECTION})
                 AND (dir_c = -1)
                 AND ((vsa_category_c = ABSORPTION)
                      OR (rejection_side_c = LOWER))

```

#### Momentum setup

At close `c+1`, use a momentum event on the confirmation bar:

```text
momentum_long = (d = +1)
                 AND context_bull_u
                AND (vsa_category_(c+1) = MOMENTUM)
                AND (dir_(c+1) = +1)
```

The selected candidate mode additionally requires its `confirmation` flag at `u`. If both
a pullback and momentum setup are true at the same decision point, the pullback setup
wins. One decision point creates at most one signal.

### 1.9 Parameters and optimization ranges

The production defaults are fixed as follows. An optimization run may use only the
listed grid values, must be performed on the training segment, and must not alter the
Fibonacci set or category priority.

| Parameter | Default | Allowed grid |
|---|---:|---:|
| signal interval | 15 min | fixed |
| context interval | 4h | fixed |
| context lookback | 90 calendar days | fixed |
| direction | LONG only | fixed |
| initial equity | 1,000,000 RUB | fixed |
| max leverage | 1.0 | fixed |
| feature mode | M0, M1, M2, M3 | all evaluated separately |
| entry order type | MARKET, LIMIT, STOP_LIMIT | all evaluated separately |
| `volume_window` | 20 | 10, 15, 20, 30, 40 |
| `atr_window` | 14 | 10, 14, 20, 30 |
| `volume_ratio_min` | 2.5 | 2.0, 2.5, 3.0, 3.5 |
| absorption range / ATR | 0.70 | 0.60, 0.70, 0.80 |
| absorption body / ATR | 0.40 | 0.30, 0.40, 0.50 |
| rejection body / range | 0.30 | 0.20, 0.30, 0.40 |
| rejection wick / range | 0.60 | 0.50, 0.60, 0.70 |
| momentum range / ATR | 1.50 | 1.25, 1.50, 1.75, 2.00 |
| momentum body / range | 0.70 | 0.60, 0.70, 0.80 |
| maximum correction depth | 0.618 | 0.382, 0.500, 0.618 |
| initial stop ATR floor | 1.50 | 1.25, 1.50, 2.00 |
| stop buffer ATR | 0.25 | 0.10, 0.25, 0.50 |
| take-profit gross R | 2.00 | 1.50, 2.00, 2.50, 3.00 |
| maximum holding bars | 8 | 4, 5, 8, 13 |
| risk per trade | 0.15% | 0.10%, 0.15%, 0.25% |
| daily max drawdown | 1.50% | fixed |

The parameter grid is a research grid, not permission to select the best result from all
historical data. Every candidate is evaluated with the same chronological walk-forward
procedure: train 60%, validate 20%, then untouched OOS 20%. On each walk-forward fold,
fit only on the train segment, select one candidate using validation rules below, and
freeze it before scoring the next OOS segment. The final production candidate is the
mode/order/threshold tuple selected most often across folds; ties are resolved by lower
risk, then fewer trades, then lexicographic parameter order. No candidate is selected by
OOS performance.

Validation selection is lexicographic and deterministic:

```text
eligible = candidates with validation trades >= 50,
           validation profit_factor >= 1.05,
           validation max_drawdown <= 0.015,
           validation net_pnl > 0
score = (validation net_pnl / validation max_drawdown,
         validation profit_factor,
         -validation turnover)
select max(score)
```

If `eligible` is empty, the fold produces `NO_DEPLOYABLE_CANDIDATE`; no fallback to an
in-sample winner is allowed.

## 2. Finite State Machine

The system persists the state and broker order identifiers before and after every state
transition. On restart it MUST reconcile broker positions and open orders before creating
any new signal. Unknown broker state is a fail-closed condition.

| Current state | Event / trigger | New state | Required action |
|---|---|---|---|
| `IDLE / SCANNING` | Valid closed bar received and no position/cooldown | `IDLE / SCANNING` | Update causal features and evaluate setup |
| `IDLE / SCANNING` | Entry setup true | `SIGNAL_PENDING` | Persist `SignalEvent`; compute entry, SL, TP, expiry |
| `SIGNAL_PENDING` | Immediate next valid bar is available and entry window is open | `ORDER_PLACED` | Submit exactly one selected MARKET/LIMIT/STOP_LIMIT entry with idempotency key |
| `SIGNAL_PENDING` | Next bar missing, session boundary, TTL expired, or setup invalidated | `IDLE / SCANNING` | Cancel signal; submit no order |
| `ORDER_PLACED` | Full fill acknowledged | `IN_POSITION` | Persist fill; submit native stop and take-profit |
| `ORDER_PLACED` | Partial fill acknowledged | `ORDER_PLACED` | Resize protective orders to filled quantity; do not add quantity |
| `ORDER_PLACED` | Rejection, cancellation, or unresolved timeout | `IDLE / SCANNING` | Query order by idempotency key; cancel remainder; never duplicate |
| `IN_POSITION` | Stop trigger or emergency condition | `STOPPING_OUT` | Cancel TP; submit/maintain reduce-only market stop |
| `IN_POSITION` | TP fill | `COOLDOWN` | Reconcile residual quantity; record trade |
| `IN_POSITION` | Time exit at holding bar `N` or session end | `STOPPING_OUT` | Cancel protective orders; close at next available market price before overnight |
| `IN_POSITION` | Opposite signal | `IN_POSITION` | Ignore; opposite signals never reverse a position |
| `STOPPING_OUT` | Position quantity becomes zero | `COOLDOWN` | Record realized PnL and stop reason |
| `STOPPING_OUT` | Close order partially fills | `STOPPING_OUT` | Replace only the unfilled reduce-only quantity |
| `COOLDOWN` | Cooldown bars elapsed and no position/orders | `IDLE / SCANNING` | Clear cooldown |
| Any state | Daily drawdown circuit breaker trips | `COOLDOWN` or `STOPPING_OUT` | Cancel entries; flatten existing position; lock new entries |
| Any state | Data integrity or broker reconciliation failure | `COOLDOWN` | Cancel new orders; flatten if position status is known |

### 2.1 Pending-order TTL

The pending signal is valid for exactly the next eligible 15-minute bar open. It is not
valid for a later bar. The signal expires if:

```text
bar_open_timestamp - signal_decision_timestamp > 20 minutes
OR the next bar is not in the same exchange session
OR the next bar is invalid/missing
```

No signal is carried across a scheduled session break, overnight boundary, or data gap.
The exchange adapter MUST provide the session identifier for this test.

## 3. Exact Entry and Exit Execution

### 3.1 Entry conditions

At close of bar `u = c+1`, after all features are finalized, the complete entry predicate
is:

```text
can_enter = valid_u
            AND warmup_complete_u
            AND same_session(a, u)
            AND cycle_depth <= 0.618
            AND no_data_gap(a, u)
            AND no_open_position
            AND no_open_entry_order
            AND cooldown_expired
            AND circuit_breaker_off
            AND daily_trade_count < 3
            AND context_bull_u
            AND actual_or_assumed_spread_bps <= 20
            AND (pullback_long OR momentum_long)
```

The direction is:

```text
LONG  if pullback_long OR momentum_long
```

The selected entry order is submitted after bar `u` closes and has a one-bar lifetime.
The candidate order types are evaluated independently:

```text
MARKET:
    submit at next eligible bar open; P_ref is the adverse modeled fill from Section 5

LIMIT:
    if setup = PULLBACK:  limit_raw = C_u - 0.25 * ATR_u
    if setup = MOMENTUM:  limit_raw = C_u - 0.10 * ATR_u
    limit_price = floor_to_tick(limit_raw)
    fill if the next bar's low <= limit_price; fill at min(next_open, limit_price)
    if next_open < limit_price, fill at next_open (price improvement)

STOP_LIMIT:
    trigger_price = ceil_to_tick(max(C_u, E + 0.10 * ATR_u))
    limit_price = ceil_to_tick(trigger_price + 0.05 * ATR_u)
    fill only when authoritative ticks show trigger trade followed by a trade at or below
    limit_price; if only OHLC is available and ordering is ambiguous, do not fill
```

The `LIMIT` and `STOP_LIMIT` formulas apply only to the long direction. If the selected
candidate does not fill before the next bar closes, it expires; it is never carried to a
later bar. For live execution the broker's actual fill price is `P_e`. If `P_e` is worse
than the pre-trade reference price `P_ref`, the trade is recorded with execution-risk
slippage, the quantity is never increased, and the protective stop is recomputed from
`P_e` immediately after the fill. Market orders cannot guarantee the pre-trade risk
budget through an unmodeled gap.

The order quantity is computed before submission using `P_ref` and the provisional stop
`stop_ref` defined below. If the quantity rounds below one exchange lot, the signal is
rejected. After a fill, `P_e` replaces `P_ref` for all live protective-order calculations;
the filled quantity is not resized upward and any excess realized risk is recorded as
`EXECUTION_RISK_OVERRUN`.

### 3.2 Initial stop

Let `P` be either `P_ref` for pre-trade sizing or the actual average fill `P_e` for
post-fill protection, let `A = ATR_u`, and let `X` be the correction extreme from
Section 1.7. Define the unrounded stop distance for the long-only strategy:

```text
structural_distance = P - (X - 0.25 * A)
stop_distance = max(1.50 * A, structural_distance, 2 * tick_size)
stop_raw = P - stop_distance
```

The stop is rounded away from the entry:

```text
stop = floor_to_tick(stop_raw)
```

The native broker stop MUST be submitted immediately after the first fill and MUST be
reduce-only. The provisional pre-trade values are `stop_ref = stop(P_ref)` and
`D_ref = abs(P_ref - stop_ref)`. Position sizing uses `D_ref` before submission. The
post-fill values are `stop_e = stop(P_e)` and `D_e = abs(P_e - stop_e)`. If a partial
fill changes average entry, `stop_e` and all protective orders are recomputed from the
new average entry, but the total filled quantity is never increased.

### 3.3 Take-profit and trailing stop

Let `D = abs(P_e - stop_e)`, `c = commission_rate`, and
`a = spread_rate / 2 + slippage_rate`. The reference take-profit is chosen so that the
modeled net profit is at least `2 * D` per share before tax. It must use the same adverse
fill model as Section 5:

```text
TP_raw = (2 * D + P_e * (1 + c)) / ((1 - a) * (1 - c))
```

The formula solves `TP_raw * (1-a) * (1-c) - P_e * (1+c) = 2D`. The result is rounded
toward a larger profit with `ceil_to_tick`. The TP is reduce-only.

Trailing rules are evaluated only at the close of each completed bar and become active
for the next bar; this prevents intrabar look-ahead:

```text
if H_bar >= P_e + D:
    candidate = max(P_e + cost_buffer, highest_high_since_entry - 1.0 * ATR_u)
    stop_next = max(stop_current, floor_to_tick(candidate))
```

`cost_buffer = P_e * (c + a)` for both directions. The stop can only move in the
profitable direction and can never be widened. If a bar touches both stop and TP, the
stop is assumed to execute first
in backtests. This rule applies even if the bar's OHLC ordering cannot be known.

Let `v` be the first bar whose open receives the entry order. The position is closed at
the first available open of bar `v+8` (eight completed 15-minute bars after the entry
bar `v`), unless SL, trailing SL, TP, or emergency exit has already closed it. If bar
`v+8` is absent because the session ends, close at the first available open of the next
session; do not carry the time-exit order across more than one scheduled session break.

### 3.4 Hard stop and emergency exit

The native stop remains active independently of the strategy process. The execution
engine MUST issue a reduce-only market close when any condition below is true:

1. The broker reports a position while the native stop is absent, rejected, or unknown.
2. The broker reports a position/order state older than 60 seconds during an active
   session and reconciliation cannot restore it after two requests 5 seconds apart.
3. A newly closed bar has `abs(O_t - C_(t-1)) >= 3 * ATR_t` against the position.
4. A newly closed bar has `R_t >= 4 * ATR_t` and its close is adverse by at least
   `1 * ATR_t` from the previous close.
5. OHLCV validity fails while a position is open and the broker provides a current
   executable quote.
6. The daily drawdown circuit breaker trips.

For a gap through the stop, the fill price is the first executable market price, not the
nominal stop price. The backtest MUST fill at the adverse bar open when the open already
crosses the stop. A hard stop is not a guarantee against exchange halts, disconnection,
or an unfillable market; those outcomes are recorded as execution-risk events and must
be included in stress tests.

## 4. Risk Management and Position Sizing

### 4.1 Position sizing

Defaults:

```text
risk_fraction = 0.0015             # 0.15% of equity; 1,500 RUB at initial equity
max_leverage = 1.0
max_positions = 1
max_daily_entries = 3
```

Let:

```text
E = current mark-to-market equity
Q = risk_fraction * E
D_ref = abs(P_ref - stop_ref)
cost_per_share = P_ref * (commission_rate + slippage_rate + spread_rate / 2)
raw_quantity = Q / (D_ref + 2 * cost_per_share)
quantity = floor_to_lot(raw_quantity)
```

The order is rejected unless:

```text
quantity >= lot_size
quantity * P_ref <= E * max_leverage
quantity * P_ref + reserved_margin <= 0.95 * E
```

For this unleveraged default, `reserved_margin = quantity * P_ref`. The 5% equity reserve
cannot be used by a new position. All open-position risk is summed before a new order;
because `max_positions = 1`, this is normally one position.

### 4.2 Daily circuit breaker

At each exchange session start, set:

```text
day_start_equity = equity immediately before the first session bar
intraday_drawdown = (day_start_equity - current_equity) / day_start_equity
```

`current_equity` includes realized PnL, unrealized PnL, commissions, and modeled
slippage. If `intraday_drawdown >= 0.015`, the circuit breaker trips:

1. cancel all pending entry orders;
2. close any position with a reduce-only market order;
3. enter `COOLDOWN`;
4. reject all new entries for 12 hours and until the next session start, whichever is
   later.

The breaker resets only after both conditions are true: the lockout elapsed and a new
session has started. A manual reset is not permitted in production mode.

After a stop-loss exit, the symbol cooldown is 8 completed bars. After TP or time exit,
the symbol cooldown is 4 completed bars. The longer applicable cooldown wins.

## 5. Friction, Spread, and Slippage Model

### 5.1 Default costs

The reference model uses conservative one-way rates:

```text
commission_rate = 0.0004       # 4 bps per side; configurable exchange tariff
slippage_rate   = 0.0005       # 5 bps per side
spread_rate     = 0.0010       # 10 bps full spread, 5 bps per side
spread_limit    = 0.0020       # reject above 20 bps full spread
```

The actual current commission MUST come from the broker configuration. The backtest must
run both the defaults and a stress case of `commission_rate=0.0008`,
`slippage_rate=0.0010`, and `spread_rate=0.0020`.

For a market entry at raw price `P`:

```text
LONG fill  = P * (1 + spread_rate / 2 + slippage_rate)
```

For closing, apply the adverse direction again:

```text
LONG close fill  = P * (1 - spread_rate / 2 - slippage_rate)
```

Commission is charged on notional on both entry and exit:

```text
entry_fee = abs(quantity * entry_fill) * commission_rate
exit_fee  = abs(quantity * exit_fill) * commission_rate
```

The default round-trip break-even gross price movement is approximately:

```text
break_even_rate = 2 * commission_rate + spread_rate + 2 * slippage_rate
                 = 0.0028 = 28 bps
```

Exact break-even prices use actual fills and fees. For a long, the trade is net profitable
iff:

```text
quantity * exit_fill - exit_fee - quantity * entry_fill - entry_fee > 0
```

All production positions are long; short cash-flow formulas are out of scope.

### 5.2 Spread filter and feed requirements

OHLCV does not identify the instantaneous bid/ask spread. Therefore the signal layer
MUST NOT pretend that a spread is measured from candle range. The execution adapter has
two allowed modes:

1. If a current top-of-book quote is available for execution, calculate
   `spread_rate_actual = (ask - bid) / ((ask + bid) / 2)` and reject when it exceeds
   `0.0020` or either side is nonpositive.
2. If no quote is available, use the fixed conservative `spread_rate=0.0010` model and
   mark the fill as `ASSUMED_SPREAD`. A production deployment may disallow this mode;
   it MUST be configurable and the backtest must report it separately.

L2 imbalance and tick delta are used only by candidate modes M1--M3 as defined in
Section 1.6. They are never backfilled from future snapshots or inferred from candle
range.

## 6. Data Contracts and Typed Interfaces

The following Python dataclasses are normative. A C++ or Rust implementation MUST preserve
the same field meanings, units, nullability, and state transitions.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Literal

Direction = Literal["LONG"]
VsaCategory = Literal["NONE", "ABSORPTION", "REJECTION", "MOMENTUM"]
RejectionSide = Literal["NONE", "UPPER", "LOWER", "BOTH"]
FeatureMode = Literal["M0", "M1", "M2", "M3"]
EntryOrderType = Literal["MARKET", "LIMIT", "STOP_LIMIT"]


@dataclass(frozen=True)
class MarketDataTick:
    # Trade/quote event. Trade classification is optional but never fabricated.
    ts: datetime
    symbol: str
    last: Decimal
    quantity: Optional[Decimal]
    aggressor_side: Optional[Literal["BUY", "SELL"]]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    source_sequence: int


@dataclass(frozen=True)
class OrderBookSnapshot:
    ts: datetime
    symbol: str
    bids: tuple[tuple[Decimal, Decimal], ...]  # price, size; best first
    asks: tuple[tuple[Decimal, Decimal], ...]  # price, size; best first
    source_sequence: int


@dataclass(frozen=True)
class BarData:
    # Timestamp is the bar close timestamp.
    ts: datetime
    symbol: str
    timeframe_seconds: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    session_id: str
    context_bar_id: str


@dataclass(frozen=True)
class TradeFlowFeatures:
    bar_ts: datetime
    buy_volume: Decimal
    sell_volume: Decimal
    known_volume: Decimal
    delta: Decimal
    delta_ratio: Decimal
    delta_z: Decimal
    coverage: Decimal


@dataclass(frozen=True)
class OrderBookFeatures:
    snapshot_ts: datetime
    mid: Decimal
    spread_rate: Decimal
    imbalance_5: Decimal
    age_seconds: int


@dataclass(frozen=True)
class CycleContext:
    impulse_start_index: int
    impulse_end_index: int
    correction_end_index: int
    impulse_length: int
    correction_length: int
    impulse_direction: int       # +1 or -1
    impulse_start_price: Decimal
    impulse_end_price: Decimal
    correction_extreme: Decimal
    correction_depth: Decimal    # [0, 0.618]
    confirmed_at: datetime


@dataclass(frozen=True)
class SignalEvent:
    signal_id: str
    symbol: str
    created_at: datetime
    decision_bar_ts: datetime
    entry_bar_ts: datetime
    direction: Literal["LONG"]
    feature_mode: FeatureMode
    entry_order_type: EntryOrderType
    setup: Literal["PULLBACK", "MOMENTUM"]
    vsa_category: Literal["ABSORPTION", "REJECTION", "MOMENTUM"]
    volume_ratio: Decimal
    atr: Decimal
    cycle: CycleContext
    expected_entry: Decimal
    limit_price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    stop_price: Decimal
    take_profit: Decimal
    quantity: int
    expires_at: datetime


@dataclass(frozen=True)
class OrderExecutionPayload:
    client_order_id: str
    broker_order_id: Optional[str]
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"]
    quantity: int
    limit_price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    reduce_only: bool
    submitted_at: datetime
    signal_id: Optional[str]


def evaluate_entry_rules(
    bars: list[BarData],
    ticks: list[MarketDataTick],
    order_books: list[OrderBookSnapshot],
    account: "AccountSnapshot",
    state: "StrategyState",
    metadata: "ContractMetadata",
    feature_mode: FeatureMode,
    entry_order_type: EntryOrderType,
) -> Optional[SignalEvent]:
    """Evaluate only after the last bar in `bars` has closed."""
```

Normative pseudocode for `evaluate_entry_rules`:

```text
1. assert bars are ordered by increasing close timestamp and all ticks/books are ordered.
2. reject and return None if symbol != "T" or timeframe != 900 seconds.
3. reject and return None if any bar fails valid_t or the required session/gap checks.
4. reject and return None if fewer than 21 causal intraday bars or 200 completed 4h bars
   in the preceding 90 calendar days exist.
5. calculate TR, ATR, VMA, volume ratio, candle geometry, completed 4h EMAs, and VSA flags.
6. assign exactly one VSA category using MOMENTUM > REJECTION > ABSORPTION priority.
7. if feature_mode is M1 or M3, aggregate authoritative ticks and require 80% classified
   volume coverage; calculate delta_ratio and causal delta_z or return None.
8. if feature_mode is M2 or M3, select the last valid L2 snapshot no older than 30 seconds;
   calculate five-level imbalance and spread or return None.
9. update the non-overlapping directional-run detector.
10. return None unless a new exact (p, q) Fibonacci cycle was confirmed on the last bar.
11. reject and return None if cycle depth is outside [0, 0.618] or if d != +1.
12. test pullback and momentum long predicates using the specified VSA event.
13. require the selected M0/M1/M2/M3 confirmation predicate on the decision bar.
14. reject and return None if state has a position, open entry order, cooldown, daily
    breaker, or three entries already recorded for the session.
15. obtain actual bid/ask when available; otherwise apply the configured assumed spread.
16. reject and return None if spread exceeds 20 bps or the execution price is invalid.
17. set entry_bar_ts to the immediate next eligible bar open; reject across a gap,
    session boundary, or more than 20 minutes after the decision close.
18. compute the provisional stop from ATR, correction extreme, and tick size; round down.
19. compute quantity from 1,000,000-RUB starting equity/current equity, 0.15% risk,
    stop distance, fees, spread, max leverage 1.0, and lot size; round down.
20. reject if quantity is below one lot or violates leverage/margin/reserve constraints.
21. compute the fee-adjusted 2R take-profit and round it upward.
22. create a deterministic signal_id from symbol, decision_bar_ts, mode, order type,
    setup, and cycle indexes; do not use a random id for deduplication.
23. set expires_at to the next bar open plus 20 minutes and return SignalEvent.
```

Required supporting contracts:

```python
@dataclass(frozen=True)
class ContractMetadata:
    symbol: str
    tick_size: Decimal
    lot_size: int
    metadata_as_of: datetime


@dataclass(frozen=True)
class AccountSnapshot:
    initial_equity: Decimal             # exactly 1_000_000 RUB at backtest/live start
    equity: Decimal
    day_start_equity: Decimal
    available_cash: Decimal
    position_quantity: int
    position_avg_price: Optional[Decimal]
    commission_rate: Decimal


@dataclass
class StrategyState:
    fsm_state: str
    cooldown_until: Optional[datetime]
    breaker_until: Optional[datetime]
    daily_entries: int
    active_signal_id: Optional[str]
    active_client_order_id: Optional[str]
```

## 7. Edge Cases and Acceptance Tests

The implementation is accepted only if all tests below pass deterministically. Tests must
include long-only variants, all four feature modes, all three entry-order types, and must
use integer ticks and exchange lots.

### 7.1 Required edge-case behavior

1. **Missing bar inside a session:** do not forward-fill; invalidate rolling windows and
   cycle state; produce no signal until 21 new contiguous valid bars are available.
2. **Scheduled session break:** do not classify the break as a missing-bar error, but do
   not carry a pending order or cycle signal across the break.
3. **Invalid OHLC:** reject any bar with `high < low`, a close outside `[low, high]`,
   nonpositive volume, NaN, or infinity; keep the last known broker position protected.
4. **Partial fill:** resize native SL/TP to the filled quantity, recompute average-entry
   stop levels, cancel the unfilled remainder at TTL, and never submit an extra quantity.
5. **Duplicate order response:** retrying a network request with the same
   `client_order_id` must return/reconcile the original order, never create a duplicate.
6. **Network loss during order submission:** enter `ORDER_PLACED`, query by idempotency
   key after reconnect, and block all new entries until the broker result is known.
7. **Gap through stop at session open:** fill at the first executable open/market price,
   record `GAP_STOP`, and calculate realized loss from the actual fill rather than the
   nominal stop.
8. **Stop and TP both touched in one OHLC bar:** choose stop first in backtests and emit
   an `AMBIGUOUS_INTRABAR_STOP_FIRST` audit event.
9. **Zero ATR or zero rolling volume:** do not divide, do not create a signal, and wait
   for a valid warmup window.
10. **Depth above 61.8%:** classify the cycle as invalidated and reject both setups,
    even if the VSA event passes all thresholds.
11. **Doji VSA anomaly:** record it for statistics but do not trade it and do not assign
     a direction.
12. **Restart with an open broker position:** reconcile first, attach/replace native
    protective orders, enter `IN_POSITION` or `STOPPING_OUT`, and do not replay a prior
    signal.
13. **Stale quote or stale metadata:** reject new orders; if a position exists, invoke
    emergency handling and keep the native stop active.
14. **Daily drawdown threshold:** at exactly 1.50% drawdown, cancel pending entries,
     flatten, and lock trading; at 1.499%, do not trip the breaker solely for rounding.
15. **Lot rounding:** if risk sizing yields less than one lot, reject the trade rather
    than exceeding the risk budget.

### 7.2 Unit-test fixtures

The test suite MUST include:

- a synthetic bullish impulse of lengths `1, 2, 3, 5, 8, 13` and a correction of each
  allowed length, proving exactly one cycle event per pair;
- a correction with depth `0.618000` that is accepted and `0.618001` that is rejected;
- a momentum bar satisfying every threshold by equality and one epsilon below each
  threshold, proving inclusive comparisons;
- a rejection bar with both qualifying wicks, proving `BOTH` produces no pullback entry;
- a VSA bar whose volume ratio is `2.499999` rejected and `2.500000` accepted;
- entry-bar OHLC where both SL and TP are touched, proving stop-first ordering;
- a full partial-fill sequence (`40%`, `40%`, `20%`) and an unfilled remainder expiry;
 - a long stop gap with actual fill worse than the nominal stop;
 - market, limit, and stop-limit fill/no-fill cases, including ambiguous OHLC ordering;
 - each feed mode M0, M1, M2, M3 with missing and stale optional data;
- 4h EMA context using only completed 4h bars from the preceding 90 calendar days;
 - adaptive scenario layer stores only completed-bar outcomes in local SQLite, uses deterministic k-NN analogues, and exposes forecast/maneuver API in dry-run mode;
- an idempotent submit/reconnect/reconcile sequence;
- session-boundary and intra-session-gap fixtures.

### 7.3 Backtest and out-of-sample acceptance thresholds

These are minimum deployment gates, not claims about current performance. The dataset
must be split chronologically into 60% training, 20% validation, and 20% untouched
out-of-sample data. The final parameters are frozen before the out-of-sample run.

The report MUST include gross and net results, the default friction case, the stressed
friction case, trade count, exposure, turnover, and bootstrap confidence intervals.

The strategy passes the minimum viability gate only if **all** conditions hold on the
untouched out-of-sample segment:

```text
closed trades >= 200
net profit factor >= 1.15
annualized Sharpe ratio >= 0.75
maximum peak-to-trough equity drawdown <= 10.0%
net expectancy after all modeled costs > 0
default-friction and stress-friction net PnL both > 0
no single calendar month contributes > 35% of total net profit
```

Sharpe is calculated from non-overlapping daily equity returns, annualized with the
actual number of exchange sessions per year. Profit factor is `sum(winning net PnL) /
abs(sum(losing net PnL))`; if the denominator is zero the result is undefined and the
test fails. A failed gate means `DEPLOYMENT_NOT_APPROVED`; the implementation MUST NOT
loosen the thresholds or silently fall back to in-sample results.

The acceptance report MUST also show results after removing the ten largest winning
trades and after doubling slippage. These robustness results are diagnostic and cannot
replace the mandatory gates above.
