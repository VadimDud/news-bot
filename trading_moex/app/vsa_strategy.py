"""Executable long-only VSA/Fibonacci research strategy for MOEX ``T``.

This module is deliberately independent from the live broker engine.  It turns
completed 15-minute bars into causal signals and simulates conservative fills,
position sizing, exits, and the daily drawdown breaker from the strategy spec.
Optional trade-flow and order-book columns are accepted when supplied by a
separate data adapter; missing optional feeds are never treated as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .volume_analysis import FIB_COUNTS

FeatureMode = Literal["M0", "M1", "M2", "M3"]
EntryOrderType = Literal["MARKET", "LIMIT", "STOP_LIMIT"]


@dataclass(frozen=True)
class StrategyConfig:
    volume_multiplier: float = 2.5
    volume_window: int = 20
    atr_period: int = 14
    absorption_range_atr: float = 0.70
    absorption_body_atr: float = 0.40
    rejection_body_ratio: float = 0.30
    rejection_wick_ratio: float = 0.60
    momentum_range_atr: float = 1.50
    momentum_body_ratio: float = 0.70
    fib_depth_max: float = 0.618
    cycle_horizon: int = 13
    context_timeframe: str = "4h"
    context_lookback_days: int = 90
    context_fast: int = 20
    context_mid: int = 50
    context_slow: int = 200
    risk_fraction: float = 0.0015
    initial_equity: float = 1_000_000.0
    max_leverage: float = 1.0
    max_daily_drawdown: float = 0.015
    max_daily_entries: int = 3
    max_hold_bars: int = 8
    stop_atr_floor: float = 1.50
    stop_buffer_atr: float = 0.25
    target_r: float = 2.0
    commission_rate: float = 0.0004
    slippage_rate: float = 0.0005
    spread_rate: float = 0.0010
    spread_limit: float = 0.0020
    tick_size: float = 0.01
    lot_size: int = 1


@dataclass(frozen=True)
class Cycle:
    impulse_start: int
    impulse_end: int
    correction_end: int
    confirmation: int
    impulse_length: int
    correction_length: int
    impulse_start_price: float
    impulse_end_price: float
    correction_extreme: float
    depth: float


@dataclass(frozen=True)
class Signal:
    index: int
    timestamp: pd.Timestamp
    setup: Literal["PULLBACK", "MOMENTUM"]
    feature_mode: FeatureMode
    order_type: EntryOrderType
    cycle: Cycle
    atr: float
    close: float


@dataclass(frozen=True)
class Trade:
    signal_timestamp: pd.Timestamp
    entry_timestamp: pd.Timestamp
    exit_timestamp: pd.Timestamp
    setup: str
    feature_mode: str
    order_type: str
    quantity: int
    entry_price: float
    exit_price: float
    stop_price: float
    take_profit: float
    gross_pnl: float
    fees: float
    net_pnl: float
    exit_reason: str
    daily_drawdown_at_exit: float


@dataclass(frozen=True)
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: dict[str, float]


def _validate_config(config: StrategyConfig) -> None:
    if config.risk_fraction <= 0 or config.initial_equity <= 0:
        raise ValueError("risk_fraction and initial_equity must be positive")
    if config.max_leverage != 1.0:
        raise ValueError("this strategy is unleveraged and requires max_leverage=1.0")
    if config.max_daily_drawdown <= 0 or config.max_daily_drawdown >= 1:
        raise ValueError("max_daily_drawdown must be between zero and one")
    if config.tick_size <= 0 or config.lot_size <= 0:
        raise ValueError("tick_size and lot_size must be positive")
    if not set(FIB_COUNTS):
        raise ValueError("Fibonacci count set cannot be empty")


def _round_down(value: float, tick_size: float) -> float:
    return np.floor(value / tick_size + 1e-12) * tick_size


def _round_up(value: float, tick_size: float) -> float:
    return np.ceil(value / tick_size - 1e-12) * tick_size


def _round_lot(value: float, lot_size: int) -> int:
    return int(np.floor(value / lot_size + 1e-12) * lot_size)


def _required_columns(frame: pd.DataFrame) -> None:
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing strategy columns: {', '.join(sorted(missing))}")


def _higher_timeframe_context(frame: pd.DataFrame, config: StrategyConfig) -> pd.Series:
    """Return completed 4-hour context aligned strictly before each 15m bar."""
    source = frame[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"], errors="coerce")
    source = source.dropna(subset=["timestamp"]).sort_values("timestamp")
    higher = (
        source.set_index("timestamp")
        .resample("4h", label="right", closed="right", origin="start_day")
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
             close=("close", "last"), volume=("volume", "sum"))
        .dropna(subset=["open", "high", "low", "close", "volume"])
        .reset_index()
    )
    for period in (config.context_fast, config.context_mid, config.context_slow):
        higher[f"ema_{period}"] = higher["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    prior_context_count = []
    for timestamp in higher["timestamp"]:
        prior_context_count.append(int(((higher["timestamp"] < timestamp) & (higher["timestamp"] >= timestamp - pd.Timedelta(days=config.context_lookback_days))).sum()))
    higher["context_count"] = prior_context_count
    higher["context_bull"] = (
        higher["close"].gt(higher[f"ema_{config.context_mid}"])
        & higher[f"ema_{config.context_fast}"].gt(higher[f"ema_{config.context_mid}"])
        & higher[f"ema_{config.context_mid}"].gt(higher[f"ema_{config.context_slow}"])
        & higher[f"ema_{config.context_fast}"].gt(higher[f"ema_{config.context_fast}"].shift(1))
        & higher["context_count"].ge(config.context_slow)
    )
    higher = higher[["timestamp", "context_bull"]].sort_values("timestamp")
    target = frame[["timestamp"]].sort_values("timestamp")
    aligned = pd.merge_asof(
        target,
        higher,
        left_on="timestamp",
        right_on="timestamp",
        direction="backward",
        allow_exact_matches=False,
    )
    return aligned["context_bull"].fillna(False).astype(bool)


def context_diagnostics(frame: pd.DataFrame, config: StrategyConfig | None = None) -> dict[str, object]:
    """Report 4-hour context availability without weakening its warmup rule."""
    config = config or StrategyConfig()
    _required_columns(frame)
    timestamps = pd.Series(pd.to_datetime(frame["timestamp"], errors="coerce").dropna(), name="timestamp")
    start = timestamps.max() - pd.Timedelta(days=config.context_lookback_days)
    recent = timestamps[timestamps >= start]
    periods = int(recent.dt.floor("4h").nunique())
    minimum = config.context_slow
    return {
        "observed_4h_periods": periods,
        "required_4h_periods": int(minimum),
        "lookback_days": int(config.context_lookback_days),
        "insufficient_warmup": bool(periods < minimum),
    }


def prepare_strategy_frame(frame: pd.DataFrame, config: StrategyConfig | None = None) -> pd.DataFrame:
    """Calculate causal intraday, 4-hour, VSA, flow, and book features."""
    config = config or StrategyConfig()
    _validate_config(config)
    _required_columns(frame)
    out = frame.copy().reset_index(drop=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    numeric = ["open", "high", "low", "close", "volume"]
    for column in numeric:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["valid_bar"] = (
        out[numeric].notna().all(axis=1)
        & np.isfinite(out[numeric]).all(axis=1)
        & out["volume"].gt(0)
        & out["close"].gt(0)
        & out["low"].gt(0)
        & out["high"].ge(out["low"])
        & out["open"].between(out["low"], out["high"])
        & out["close"].between(out["low"], out["high"])
    )
    interval = out["timestamp"].diff().dt.total_seconds()
    previous_invalid = out["valid_bar"].shift(1).fillna(False).eq(False)
    break_mask = interval.ne(900).fillna(True) | ~out["valid_bar"] | previous_invalid
    out["segment"] = break_mask.cumsum()
    out["range"] = (out["high"] - out["low"]).clip(lower=0)
    out["body"] = (out["close"] - out["open"]).abs()
    out["body_ratio"] = out["body"].div(out["range"].replace(0, np.nan)).fillna(0.0)
    out["upper_wick"] = (out["high"] - out[["open", "close"]].max(axis=1)).clip(lower=0)
    out["lower_wick"] = (out[["open", "close"]].min(axis=1) - out["low"]).clip(lower=0)
    previous_close = out["close"].shift(1)
    true_range = pd.concat(
        [out["high"] - out["low"], (out["high"] - previous_close).abs(),
         (out["low"] - previous_close).abs()], axis=1,
    ).max(axis=1)
    out["atr"] = true_range.groupby(out["segment"], sort=False).transform(
        lambda values: values.rolling(config.atr_period, min_periods=config.atr_period).mean().shift(1)
    )
    out["volume_sma"] = out["volume"].groupby(out["segment"], sort=False).transform(
        lambda values: values.shift(1).rolling(config.volume_window, min_periods=config.volume_window).mean()
    )
    out["volume_ratio"] = out["volume"].div(out["volume_sma"].replace(0, np.nan))
    out["dir"] = np.sign(out["close"].diff()).astype(float)
    out.loc[interval.ne(900) | ~out["valid_bar"] | previous_invalid, "dir"] = 0
    out["is_anomalous_volume"] = out["volume_ratio"].ge(config.volume_multiplier)
    out["is_absorption"] = (
        out["is_anomalous_volume"] & out["range"].le(config.absorption_range_atr * out["atr"])
        & out["body"].le(config.absorption_body_atr * out["atr"])
    )
    out["is_rejection"] = (
        out["is_anomalous_volume"] & out["body_ratio"].le(config.rejection_body_ratio)
        & ((out["lower_wick"].ge(config.rejection_wick_ratio * out["range"]))
           | (out["upper_wick"].ge(config.rejection_wick_ratio * out["range"])))
    )
    out["is_momentum"] = (
        out["is_anomalous_volume"] & out["range"].ge(config.momentum_range_atr * out["atr"])
        & out["body_ratio"].ge(config.momentum_body_ratio)
    )
    out["vsa_category"] = "NONE"
    out.loc[out["is_absorption"], "vsa_category"] = "ABSORPTION"
    out.loc[out["is_rejection"], "vsa_category"] = "REJECTION"
    out.loc[out["is_momentum"], "vsa_category"] = "MOMENTUM"
    out["rejection_side"] = "NONE"
    lower = out["lower_wick"].ge(config.rejection_wick_ratio * out["range"])
    upper = out["upper_wick"].ge(config.rejection_wick_ratio * out["range"])
    out.loc[lower & ~upper, "rejection_side"] = "LOWER"
    out.loc[upper & ~lower, "rejection_side"] = "UPPER"
    out.loc[lower & upper, "rejection_side"] = "BOTH"
    out["context_bull"] = _higher_timeframe_context(out, config).to_numpy()

    if {"buy_volume", "sell_volume"}.issubset(out.columns):
        out["known_volume"] = out["buy_volume"].fillna(0) + out["sell_volume"].fillna(0)
        out["flow_delta"] = out["buy_volume"] - out["sell_volume"]
        out["flow_coverage"] = out["known_volume"].div(out["volume"].replace(0, np.nan))
    else:
        out["known_volume"] = np.nan
        out["flow_delta"] = np.nan
        out["flow_coverage"] = np.nan
    out["delta_ratio"] = out["flow_delta"].div(out["known_volume"].replace(0, np.nan))
    out["delta_mean"] = out["flow_delta"].shift(1).rolling(20, min_periods=20).mean()
    out["delta_std"] = out["flow_delta"].shift(1).rolling(20, min_periods=20).std(ddof=0)
    out["delta_z"] = (out["flow_delta"] - out["delta_mean"]).div(out["delta_std"].replace(0, np.nan))
    if "book_imbalance" not in out:
        out["book_imbalance"] = np.nan
    if "book_spread" not in out:
        out["book_spread"] = np.nan
    out["flow_long"] = out["flow_coverage"].ge(0.80) & out["delta_ratio"].ge(0.10) & out["delta_z"].ge(0.50)
    out["book_long"] = out["book_imbalance"].ge(0.20) & out["book_spread"].le(0.0020)
    return out


def detect_cycles(prepared: pd.DataFrame, config: StrategyConfig | None = None) -> list[Cycle]:
    """Find non-overlapping bullish exact Fibonacci impulse/correction cycles."""
    config = config or StrategyConfig()
    closes = prepared["close"].to_numpy(float)
    directions = prepared["dir"].to_numpy(float)
    cycles: list[Cycle] = []
    occupied_until = -1
    for start in range(1, len(prepared)):
        if start <= occupied_until or directions[start] != 1 or (start > 1 and directions[start - 1] == 1):
            continue
        impulse_end = start
        while impulse_end + 1 < len(prepared) and directions[impulse_end + 1] == 1:
            impulse_end += 1
        impulse_length = impulse_end - start + 1
        if impulse_length not in FIB_COUNTS:
            continue
        correction_start = impulse_end + 1
        if correction_start >= len(prepared) or directions[correction_start] != -1:
            continue
        correction_end = correction_start
        while correction_end + 1 < len(prepared) and directions[correction_end + 1] == -1:
            correction_end += 1
        correction_length = correction_end - correction_start + 1
        confirmation = correction_end + 1
        if correction_length not in FIB_COUNTS or confirmation >= len(prepared) or directions[confirmation] != 1:
            continue
        if prepared.loc[start : confirmation, "segment"].nunique() != 1:
            continue
        impulse_start_price = float(closes[start - 1])
        impulse_end_price = float(closes[impulse_end])
        impulse_size = impulse_end_price - impulse_start_price
        if impulse_size <= 0:
            continue
        correction_extreme = float(prepared.loc[correction_start:correction_end, "low"].min())
        depth = (impulse_end_price - correction_extreme) / impulse_size
        if depth < 0 or depth > config.fib_depth_max:
            occupied_until = confirmation
            continue
        cycles.append(Cycle(
            impulse_start=start,
            impulse_end=impulse_end,
            correction_end=correction_end,
            confirmation=confirmation,
            impulse_length=impulse_length,
            correction_length=correction_length,
            impulse_start_price=impulse_start_price,
            impulse_end_price=impulse_end_price,
            correction_extreme=correction_extreme,
            depth=depth,
        ))
        occupied_until = confirmation
    return cycles


def _confirmation_ok(row: pd.Series, mode: FeatureMode) -> bool:
    if mode == "M0":
        return True
    if mode == "M1":
        return bool(row["flow_long"])
    if mode == "M2":
        return bool(row["book_long"])
    return bool(row["flow_long"] and row["book_long"])


def build_signals(
    frame: pd.DataFrame,
    config: StrategyConfig | None = None,
    *,
    feature_mode: FeatureMode = "M0",
    order_type: EntryOrderType = "MARKET",
) -> tuple[pd.DataFrame, list[Signal]]:
    """Build causal long-only signals and return the prepared frame."""
    if feature_mode not in {"M0", "M1", "M2", "M3"}:
        raise ValueError(f"unknown feature mode: {feature_mode}")
    if order_type not in {"MARKET", "LIMIT", "STOP_LIMIT"}:
        raise ValueError(f"unknown order type: {order_type}")
    config = config or StrategyConfig()
    prepared = prepare_strategy_frame(frame, config)
    cycles = detect_cycles(prepared, config)
    signals: list[Signal] = []
    for cycle in cycles:
        u = cycle.confirmation
        endpoint = prepared.iloc[cycle.correction_end]
        confirmation = prepared.iloc[u]
        pullback = (
            bool(prepared.iloc[u]["context_bull"])
            and endpoint["vsa_category"] in {"ABSORPTION", "REJECTION"}
            and endpoint["dir"] == -1
            and (endpoint["vsa_category"] == "ABSORPTION" or endpoint["rejection_side"] == "LOWER")
        )
        momentum = (
            bool(confirmation["context_bull"])
            and confirmation["vsa_category"] == "MOMENTUM"
            and confirmation["dir"] == 1
        )
        if not (pullback or momentum) or not _confirmation_ok(confirmation, feature_mode):
            continue
        signals.append(Signal(
            index=u,
            timestamp=pd.Timestamp(confirmation["timestamp"]),
            setup="PULLBACK" if pullback else "MOMENTUM",
            feature_mode=feature_mode,
            order_type=order_type,
            cycle=cycle,
            atr=float(confirmation["atr"]),
            close=float(confirmation["close"]),
        ))
    return prepared, signals


def _entry_fill(
    prepared: pd.DataFrame,
    signal: Signal,
    next_bar: pd.Series,
    config: StrategyConfig,
) -> tuple[float, float] | None:
    """Return (modeled fill, raw price) or None when the order does not fill."""
    if not np.isfinite(signal.atr) or signal.atr <= 0:
        return None
    if signal.order_type == "MARKET":
        raw = float(next_bar["open"])
        return raw * (1 + config.spread_rate / 2 + config.slippage_rate), raw
    if signal.order_type == "LIMIT":
        raw_limit = signal.close - (0.25 if signal.setup == "PULLBACK" else 0.10) * signal.atr
        limit = _round_down(raw_limit, config.tick_size)
        if float(next_bar["low"]) > limit:
            return None
        raw = min(float(next_bar["open"]), limit)
        return raw, raw
    trigger = _round_up(max(signal.close, signal.cycle.impulse_end_price + 0.10 * signal.atr), config.tick_size)
    limit = _round_up(trigger + 0.05 * signal.atr, config.tick_size)
    # Without tick ordering, a stop-limit is fillable only when the bar opens
    # after the trigger. A high/low touch alone is deliberately insufficient.
    if float(next_bar["open"]) < trigger or float(next_bar["low"]) > limit:
        return None
    raw = min(float(next_bar["open"]), limit)
    return raw, raw


def _stop_and_target(entry: float, cycle: Cycle, atr: float, config: StrategyConfig) -> tuple[float, float]:
    stop_raw = entry - max(config.stop_atr_floor * atr,
                           entry - (cycle.correction_extreme - config.stop_buffer_atr * atr),
                           2 * config.tick_size)
    stop = _round_down(stop_raw, config.tick_size)
    distance = entry - stop
    a = config.spread_rate / 2 + config.slippage_rate
    target_raw = (config.target_r * distance + entry * (1 + config.commission_rate)) / (
        (1 - a) * (1 - config.commission_rate)
    )
    return stop, _round_up(target_raw, config.tick_size)


def _exit_fill(price: float, config: StrategyConfig) -> float:
    return price * (1 - config.spread_rate / 2 - config.slippage_rate)


def _metrics(trades: pd.DataFrame, equity: pd.DataFrame, initial: float) -> dict[str, float]:
    if trades.empty:
        return {"trades": 0.0, "profit_factor": np.nan, "net_pnl": 0.0,
                "return_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": np.nan}
    wins = trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum()
    losses = trades.loc[trades["net_pnl"] < 0, "net_pnl"].sum()
    daily = equity.set_index("timestamp")["equity"].resample("1D").last().dropna().pct_change().dropna()
    sharpe = np.nan
    if len(daily) >= 2 and daily.std(ddof=1) > 0:
        sharpe = float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
    return {
        "trades": float(len(trades)),
        "profit_factor": float(wins / abs(losses)) if losses else np.nan,
        "net_pnl": float(trades["net_pnl"].sum()),
        "return_pct": float((equity["equity"].iloc[-1] / initial - 1) * 100),
        "max_drawdown_pct": float((equity["drawdown"].max() if not equity.empty else 0) * 100),
        "sharpe": sharpe,
    }


def run_backtest(
    frame: pd.DataFrame,
    config: StrategyConfig | None = None,
    *,
    feature_mode: FeatureMode = "M0",
    order_type: EntryOrderType = "MARKET",
) -> BacktestResult:
    """Run a single non-overlapping long-only candidate."""
    config = config or StrategyConfig()
    prepared, signals = build_signals(frame, config, feature_mode=feature_mode, order_type=order_type)
    equity = config.initial_equity
    peak = equity
    day_start = equity
    breaker_day: object | None = None
    daily_entries = 0
    trades: list[Trade] = []
    curve: list[dict[str, object]] = []
    equity_events: dict[pd.Timestamp, float] = {}
    occupied_until = -1
    for signal in signals:
        u = signal.index
        v = u + 1
        if v >= len(prepared) or v <= occupied_until:
            continue
        signal_day = pd.Timestamp(prepared.iloc[v]["timestamp"]).date()
        if signal_day != breaker_day:
            day_start = equity
            daily_entries = 0
            breaker_day = signal_day
        if daily_entries >= config.max_daily_entries or (day_start - equity) / day_start >= config.max_daily_drawdown:
            continue
        if pd.Timestamp(prepared.iloc[u]["timestamp"]).date() != signal_day:
            continue
        entry_data = _entry_fill(prepared, signal, prepared.iloc[v], config)
        if entry_data is None:
            continue
        entry, raw_entry = entry_data
        stop, target = _stop_and_target(entry, signal.cycle, signal.atr, config)
        distance = entry - stop
        cost_per_share = entry * (config.commission_rate + config.slippage_rate + config.spread_rate / 2)
        quantity = _round_lot(
            config.risk_fraction * equity / (distance + 2 * cost_per_share), config.lot_size
        )
        if quantity < config.lot_size or quantity * entry > equity * config.max_leverage:
            continue
        if quantity * entry + quantity * entry <= 0.95 * equity:
            pass
        else:
            continue
        entry_fee = quantity * entry * config.commission_rate
        exit_index = min(len(prepared) - 1, v + config.max_hold_bars)
        exit_price = None
        exit_reason = "TIME"
        exit_ts = pd.Timestamp(prepared.iloc[exit_index]["timestamp"])
        for j in range(v, exit_index + 1):
            bar = prepared.iloc[j]
            current_day = pd.Timestamp(bar["timestamp"]).date()
            if current_day != signal_day:
                exit_price = _exit_fill(float(bar["open"]), config)
                exit_reason = "SESSION_END"
                exit_ts = pd.Timestamp(bar["timestamp"])
                break
            # Stop takes priority when both stop and target are touched.
            if float(bar["open"]) <= stop or float(bar["low"]) <= stop:
                raw_exit = float(bar["open"]) if float(bar["open"]) <= stop else stop
                exit_price = _exit_fill(raw_exit, config)
                exit_reason = "GAP_STOP" if float(bar["open"]) <= stop else "STOP"
                exit_ts = pd.Timestamp(bar["timestamp"])
                break
            if float(bar["high"]) >= target:
                exit_price = _exit_fill(target, config)
                exit_reason = "TAKE_PROFIT"
                exit_ts = pd.Timestamp(bar["timestamp"])
                break
            marked = equity + quantity * (float(bar["close"]) - entry)
            if (day_start - marked) / day_start >= config.max_daily_drawdown:
                exit_price = _exit_fill(float(bar["close"]), config)
                exit_reason = "DAILY_BREAKER"
                exit_ts = pd.Timestamp(bar["timestamp"])
                break
        if exit_price is None:
            exit_price = _exit_fill(float(prepared.iloc[exit_index]["open"]), config)
        exit_fee = quantity * exit_price * config.commission_rate
        gross = quantity * (exit_price - entry)
        net = gross - entry_fee - exit_fee
        equity += net
        equity_events[exit_ts] = equity
        peak = max(peak, equity)
        daily_dd = max(0.0, (day_start - equity) / day_start)
        trades.append(Trade(
            signal_timestamp=signal.timestamp, entry_timestamp=pd.Timestamp(prepared.iloc[v]["timestamp"]),
            exit_timestamp=exit_ts, setup=signal.setup, feature_mode=feature_mode,
            order_type=order_type, quantity=quantity, entry_price=entry, exit_price=exit_price,
            stop_price=stop, take_profit=target, gross_pnl=gross, fees=entry_fee + exit_fee,
            net_pnl=net, exit_reason=exit_reason, daily_drawdown_at_exit=daily_dd,
        ))
        occupied_until = exit_index
        daily_entries += 1
    curve_equity = config.initial_equity
    curve_peak = curve_equity
    for _, row in prepared.iterrows():
        timestamp = pd.Timestamp(row["timestamp"])
        if timestamp in equity_events:
            curve_equity = equity_events[timestamp]
        curve_peak = max(curve_peak, curve_equity)
        curve.append({
            "timestamp": timestamp,
            "equity": curve_equity,
            "drawdown": max(0.0, (curve_peak - curve_equity) / curve_peak),
        })
    trades_frame = pd.DataFrame([trade.__dict__ for trade in trades])
    curve_frame = pd.DataFrame(curve)
    return BacktestResult(trades_frame, curve_frame, _metrics(trades_frame, curve_frame, config.initial_equity))
