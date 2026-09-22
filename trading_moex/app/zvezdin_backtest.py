"""Pandas adapter and deterministic result aggregation for ZvezdinEngine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from itertools import product
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from math import isfinite
from typing import Any, Mapping, Sequence

import pandas as pd

from .zvezdin_engine import Bar, StrategyConfig, StrategyEngine, Trade, ZoneType, atr_wilder, is_pivot_high, is_pivot_low
from .zvezdin_calendar import SessionCalendar


REQUIRED_COLUMNS = frozenset({"open", "high", "low", "close", "volume"})


def _closed_htf_wave_ranges(
    df: pd.DataFrame,
    rule: str = "4h",
    pivot_q: int = 3,
    ltf_bar_minutes: int = 15,
) -> pd.Series:
    """Return the last completed HTF fractal-to-fractal wave at each LTF close.

    A higher-timeframe pivot is usable only after its right shoulder has closed.
    The returned value is aligned to the lower-timeframe bar and never uses the
    currently forming HTF bucket.
    """

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("HTF wave calculation requires a DatetimeIndex")
    if pivot_q < 1:
        raise ValueError("pivot_q must be positive")
    if ltf_bar_minutes < 1:
        raise ValueError("ltf_bar_minutes must be positive")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("DataFrame index must be increasing and unique")
    grouped = df[["open", "high", "low", "close", "volume"]].resample(
        rule, closed="left", label="left"
    ).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    if grouped.empty:
        return pd.Series(index=df.index, dtype="float64", name="htf_art")

    htf_bars = [
        Bar(i, float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume))
        for i, (_, row) in enumerate(grouped.iterrows())
    ]
    confirmed: dict[int, list[tuple[int, float, ZoneType]]] = {}
    for tau in range(len(grouped)):
        if tau + pivot_q >= len(grouped):
            break
        if is_pivot_high(htf_bars, tau, pivot_q):
            confirmed.setdefault(tau + pivot_q, []).append(
                (tau, float(grouped.iloc[tau].high), ZoneType.RESISTANCE)
            )
        if is_pivot_low(htf_bars, tau, pivot_q):
            confirmed.setdefault(tau + pivot_q, []).append(
                (tau, float(grouped.iloc[tau].low), ZoneType.SUPPORT)
            )

    # A pivot of the same type replaces the weaker one, matching the engine's
    # causal swing stack. Each completed adjacent pair is one HTF wave.
    values: list[float | None] = []
    htf_ends = grouped.index + pd.Timedelta(rule)
    confirmation_events = sorted(
        (confirmation, pivot)
        for confirmation, pivots in confirmed.items()
        for pivot in pivots
    )
    event_cursor = 0
    stack: list[tuple[int, float, ZoneType]] = []
    for timestamp in df.index:
        # Data timestamps mark bar open; the decision is made at bar close.
        decision_time = timestamp + pd.Timedelta(minutes=ltf_bar_minutes)
        available = int((htf_ends <= decision_time).sum())
        while event_cursor < len(confirmation_events) and confirmation_events[event_cursor][0] < available:
            pivot = confirmation_events[event_cursor][1]
            if not stack or stack[-1][2] is not pivot[2]:
                stack.append(pivot)
            elif (
                pivot[1] > stack[-1][1]
                if pivot[2] is ZoneType.RESISTANCE
                else pivot[1] < stack[-1][1]
            ):
                stack[-1] = pivot
            event_cursor += 1
        values.append(abs(stack[-1][1] - stack[-2][1]) if len(stack) >= 2 else None)
    return pd.Series(values, index=df.index, dtype="float64", name="htf_art")


def _closed_htf_directional_wave_ranges(
    df: pd.DataFrame,
    rule: str = "4h",
    pivot_q: int = 3,
    n_waves: int = 4,
    selection: str = "latest_mean",
) -> tuple[pd.Series, pd.Series]:
    """Return mean completed 4h up-wave and down-wave amplitudes.

    Up waves (low -> high) are used for long exhaustion and down waves
    (high -> low) for short exhaustion. Only the latest ``n_waves`` completed
    waves of each direction are averaged at every lower-timeframe close.
    ``selection`` can instead select the last wave or the largest historical
    waves, which keeps the choice causal while making the hypothesis explicit.
    """

    if n_waves < 1:
        raise ValueError("n_waves must be positive")
    if selection not in {"latest_mean", "last", "longest_mean", "longest"}:
        raise ValueError("unsupported directional wave selection")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("HTF wave calculation requires a DatetimeIndex")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("DataFrame index must be increasing and unique")
    grouped = df[["open", "high", "low", "close", "volume"]].resample(
        rule, closed="left", label="left"
    ).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    if grouped.empty:
        empty = pd.Series(index=df.index, dtype="float64")
        return empty.rename("htf_art_long"), empty.rename("htf_art_short")

    htf_bars = [
        Bar(i, float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume))
        for i, (_, row) in enumerate(grouped.iterrows())
    ]
    confirmed: dict[int, list[tuple[int, float, ZoneType]]] = {}
    for tau in range(len(htf_bars)):
        confirmation = tau + pivot_q
        if confirmation >= len(htf_bars):
            break
        if is_pivot_high(htf_bars, tau, pivot_q):
            confirmed.setdefault(confirmation, []).append(
                (tau, float(grouped.iloc[tau].high), ZoneType.RESISTANCE)
            )
        if is_pivot_low(htf_bars, tau, pivot_q):
            confirmed.setdefault(confirmation, []).append(
                (tau, float(grouped.iloc[tau].low), ZoneType.SUPPORT)
            )

    htf_ends = grouped.index + pd.Timedelta(rule)
    confirmation_events = sorted(
        (confirmation, pivot)
        for confirmation, pivots in confirmed.items()
        for pivot in pivots
    )
    event_cursor = 0
    stack: list[tuple[int, float, ZoneType]] = []
    long_values: list[float | None] = []
    short_values: list[float | None] = []
    for timestamp in df.index:
        decision_time = timestamp + pd.Timedelta(minutes=15)
        available = int((htf_ends <= decision_time).sum())
        while event_cursor < len(confirmation_events) and confirmation_events[event_cursor][0] < available:
            pivot = confirmation_events[event_cursor][1]
            if not stack or stack[-1][2] is not pivot[2]:
                stack.append(pivot)
            elif (
                pivot[1] > stack[-1][1]
                if pivot[2] is ZoneType.RESISTANCE
                else pivot[1] < stack[-1][1]
            ):
                stack[-1] = pivot
            event_cursor += 1

        up_waves = [
            abs(stack[index][1] - stack[index - 1][1])
            for index in range(1, len(stack))
            if stack[index - 1][2] is ZoneType.SUPPORT
            and stack[index][2] is ZoneType.RESISTANCE
        ]
        down_waves = [
            abs(stack[index][1] - stack[index - 1][1])
            for index in range(1, len(stack))
            if stack[index - 1][2] is ZoneType.RESISTANCE
            and stack[index][2] is ZoneType.SUPPORT
        ]
        def select_wave(waves: list[float]) -> float | None:
            if not waves:
                return None
            if selection == "last":
                return waves[-1]
            if selection == "longest":
                return max(waves)
            selected = waves[-n_waves:] if selection == "latest_mean" else sorted(waves, reverse=True)[:n_waves]
            return sum(selected) / len(selected)

        long_values.append(select_wave(up_waves))
        short_values.append(select_wave(down_waves))
    return (
        pd.Series(long_values, index=df.index, dtype="float64", name="htf_art_long"),
        pd.Series(short_values, index=df.index, dtype="float64", name="htf_art_short"),
    )


def _closed_htf_atr(
    df: pd.DataFrame,
    rule: str = "30min",
    period: int = 14,
    ltf_bar_minutes: int = 5,
) -> pd.Series:
    """Align Wilder ATR of completed HTF bars to closed LTF bars causally."""

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("HTF ATR calculation requires a DatetimeIndex")
    grouped = df[["open", "high", "low", "close", "volume"]].resample(
        rule, closed="left", label="left"
    ).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    htf_bars = [
        Bar(i, float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume))
        for i, (_, row) in enumerate(grouped.iterrows())
    ]
    atr_values = atr_wilder(htf_bars, period)
    htf_ends = grouped.index + pd.Timedelta(rule)
    values: list[float | None] = []
    for timestamp in df.index:
        decision_time = timestamp + pd.Timedelta(minutes=ltf_bar_minutes)
        available = int((htf_ends <= decision_time).sum())
        values.append(atr_values[available - 1] if available and atr_values[available - 1] is not None else None)
    return pd.Series(values, index=df.index, dtype="float64", name="htf_atr")


def _closed_htf_levels(
    df: pd.DataFrame,
    rule: str,
    pivot_q: int = 2,
    ltf_bar_minutes: int = 5,
) -> pd.DataFrame:
    """Return causal nearest confirmed support/resistance for each LTF bar."""

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("HTF levels require a DatetimeIndex")
    grouped = df[["open", "high", "low", "close", "volume"]].resample(
        rule, closed="left", label="left"
    ).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    htf_bars = [
        Bar(i, float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume))
        for i, (_, row) in enumerate(grouped.iterrows())
    ]
    events: dict[int, list[tuple[int, float, ZoneType]]] = {}
    for tau in range(len(htf_bars)):
        confirmation = tau + pivot_q
        if confirmation >= len(htf_bars):
            break
        if is_pivot_high(htf_bars, tau, pivot_q):
            events.setdefault(confirmation, []).append(
                (tau, float(grouped.iloc[tau].high), ZoneType.RESISTANCE)
            )
        if is_pivot_low(htf_bars, tau, pivot_q):
            events.setdefault(confirmation, []).append(
                (tau, float(grouped.iloc[tau].low), ZoneType.SUPPORT)
            )

    htf_ends = grouped.index + pd.Timedelta(rule)
    confirmed: list[tuple[int, float, ZoneType]] = []
    cursor = 0
    ordered_events = sorted(
        (confirmation, pivot) for confirmation, pivots in events.items() for pivot in pivots
    )
    rows = []
    for timestamp, row in df.iterrows():
        decision_time = timestamp + pd.Timedelta(minutes=ltf_bar_minutes)
        available = int((htf_ends <= decision_time).sum())
        while cursor < len(ordered_events) and ordered_events[cursor][0] < available:
            confirmed.append(ordered_events[cursor][1])
            cursor += 1
        close = float(row["close"])
        supports = [item for item in confirmed if item[2] is ZoneType.SUPPORT and item[1] <= close]
        resistances = [item for item in confirmed if item[2] is ZoneType.RESISTANCE and item[1] >= close]
        support = max(supports, key=lambda item: item[1]) if supports else None
        resistance = min(resistances, key=lambda item: item[1]) if resistances else None
        rows.append({
            "support": support[1] if support else None,
            "support_pivot_bar": support[0] if support else None,
            "support_pivot_time": str(grouped.index[support[0]]) if support else None,
            "resistance": resistance[1] if resistance else None,
            "resistance_pivot_bar": resistance[0] if resistance else None,
            "resistance_pivot_time": str(grouped.index[resistance[0]]) if resistance else None,
            "distance_to_support": close - support[1] if support else None,
            "distance_to_resistance": resistance[1] - close if resistance else None,
        })
    return pd.DataFrame(rows, index=df.index)


@dataclass(frozen=True)
class BacktestResult:
    trades: tuple[Trade, ...]
    events: tuple
    final_realized_pnl: float
    max_drawdown: float
    win_rate: float
    profit_factor: float | None
    open_position: dict | None = None
    pending_order: dict | None = None
    unrealized_pnl: float = 0.0
    equity_pnl: float = 0.0
    terminal_mark_price: float | None = None
    equity_curve: tuple[dict, ...] = ()
    audit: tuple = ()
    audit_summary: dict = None
    manifest: dict | None = None

    def as_dict(self) -> dict:
        return {
            "trades": [_json_safe(trade.__dict__) for trade in self.trades],
            "events": [_json_safe(event.__dict__) for event in self.events],
            "final_realized_pnl": self.final_realized_pnl,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "open_position": _json_safe(self.open_position),
            "pending_order": _json_safe(self.pending_order),
            "unrealized_pnl": self.unrealized_pnl,
            "equity_pnl": self.equity_pnl,
            "terminal_mark_price": self.terminal_mark_price,
            "equity_curve": [_json_safe(point) for point in self.equity_curve],
            "audit": [_json_safe(record.__dict__) for record in self.audit],
            "audit_summary": _json_safe(self.audit_summary or {}),
            "manifest": _json_safe(self.manifest or {}),
        }


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    in_sample: BacktestResult
    out_of_sample: BacktestResult
    wfe: float | None
    selected_parameters: dict[str, Any] | None = None

    def as_dict(self) -> dict:
        return {
            "fold": self.fold,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "in_sample": self.in_sample.as_dict(),
            "out_of_sample": self.out_of_sample.as_dict(),
            "wfe": self.wfe,
            "selected_parameters": self.selected_parameters,
        }


@dataclass(frozen=True)
class WalkForwardResult:
    folds: tuple[WalkForwardFold, ...]
    aggregate_oos: BacktestResult
    mean_wfe: float | None
    manifest: dict | None = None

    def as_dict(self) -> dict:
        return {
            "folds": [fold.as_dict() for fold in self.folds],
            "aggregate_oos": self.aggregate_oos.as_dict(),
            "mean_wfe": self.mean_wfe,
            "manifest": _json_safe(self.manifest or {}),
        }


@dataclass(frozen=True)
class SensitivityResult:
    parameters: dict[str, Any]
    result: BacktestResult

    def as_dict(self) -> dict:
        return {"parameters": self.parameters, "result": self.result.as_dict()}


@dataclass(frozen=True)
class RobustnessReport:
    passed: bool
    checks: dict[str, bool]
    metrics: dict[str, float | int | None]
    failures: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": dict(self.checks),
            "metrics": dict(self.metrics),
            "failures": list(self.failures),
        }


@dataclass(frozen=True)
class SensitivitySummary:
    passed: bool
    combinations: int
    best_parameters: dict[str, Any] | None
    best_equity_pnl: float | None
    median_equity_pnl: float | None
    positive_fraction: float
    neighbor_count: int
    neighbor_median_ratio: float | None
    failures: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "combinations": self.combinations,
            "best_parameters": self.best_parameters,
            "best_equity_pnl": self.best_equity_pnl,
            "median_equity_pnl": self.median_equity_pnl,
            "positive_fraction": self.positive_fraction,
            "neighbor_count": self.neighbor_count,
            "neighbor_median_ratio": self.neighbor_median_ratio,
            "failures": list(self.failures),
        }


def _json_safe(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Hash OHLCV data and its index without sorting or filling it."""

    columns = ["open", "high", "low", "close", "volume"]
    missing = set(columns).difference(df.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")
    rows = []
    for timestamp, row in df[columns].iterrows():
        if isinstance(timestamp, pd.Timestamp):
            timestamp = (timestamp.tz_convert("UTC") if timestamp.tzinfo else timestamp.tz_localize("UTC")).isoformat()
        rows.append([str(timestamp), *[format(float(row[column]), ".17g") for column in columns]])
    return _sha256_bytes("\n".join(",".join(row) for row in rows).encode("utf-8"))


def m1_mapping_fingerprint(m1_by_bar: Mapping[int, Sequence[Bar]] | None) -> str | None:
    if not m1_by_bar:
        return None
    rows = []
    for parent_index in sorted(m1_by_bar):
        for bar in m1_by_bar[parent_index]:
            rows.append([
                str(parent_index), str(bar.index),
                *[format(value, ".17g") for value in (bar.open, bar.high, bar.low, bar.close, bar.volume)],
            ])
    return _sha256_bytes("\n".join(",".join(row) for row in rows).encode("utf-8"))


def build_run_manifest(
    df: pd.DataFrame,
    config: StrategyConfig,
    mode: str,
    quantity: float,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
) -> dict:
    config_values = asdict(config)
    calendar = config_values.get("calendar")
    if calendar is not None:
        config_values["calendar"] = {
            "holidays": sorted(calendar["holidays"]),
            "early_closes": dict(sorted(calendar["early_closes"].items())),
        }
    manifest = {
        "manifest_version": "1.0.0",
        "engine": "zvezdin_deterministic_streaming",
        "mode": mode,
        "bars": len(df),
        "m1_bars": sum(len(values) for values in (m1_by_bar or {}).values()),
        "quantity": quantity,
        "liquidate_at_end": liquidate_at_end,
        "input_sha256": dataframe_fingerprint(df),
        "m1_sha256": m1_mapping_fingerprint(m1_by_bar),
        "config_sha256": _sha256_bytes(_canonical_json(config_values)),
        "config": config_values,
    }
    manifest["run_sha256"] = _sha256_bytes(_canonical_json(manifest))
    return manifest


def summarize_audit(audit: Sequence) -> dict:
    """Aggregate causal decisions without discarding the per-bar audit trail."""

    decisions = Counter(record.decision for record in audit)
    reasons = Counter(
        record.block_reason for record in audit if record.block_reason is not None
    )
    signal_count = sum(value for key, value in decisions.items() if key.startswith("SIGNAL_"))
    blocked_count = decisions.get("BLOCKED", 0)
    total = len(audit)

    def rate(field: str) -> float:
        if not audit:
            return 0.0
        return sum(bool(getattr(record, field, False)) for record in audit) / total

    return {
        "bars": total,
        "decisions": dict(sorted(decisions.items())),
        "block_reasons": dict(sorted(reasons.items())),
        "signal_count": signal_count,
        "blocked_count": blocked_count,
        "signal_rate": signal_count / total if total else 0.0,
        "component_pass_rates": {
            "macro_short": rate("macro_short"),
            "macro_long": rate("macro_long"),
            "micro_short": rate("micro_short"),
            "micro_long": rate("micro_long"),
            "exhaustion_short": rate("exhaustion_short"),
            "exhaustion_long": rate("exhaustion_long"),
            "volume_spike": rate("volume_spike"),
            "acceleration": rate("acceleration"),
            "candle_shape_short": rate("candle_shape_short"),
            "candle_shape_long": rate("candle_shape_long"),
            "pattern_short": rate("pattern_short"),
            "pattern_long": rate("pattern_long"),
            "soft_score_short_mean": sum(getattr(record, "soft_score_short", 0) for record in audit) / total if total else 0.0,
            "soft_score_long_mean": sum(getattr(record, "soft_score_long", 0) for record in audit) / total if total else 0.0,
        },
    }


def bars_from_dataframe(
    df: pd.DataFrame,
    session_start_minute: int = 0,
    session_end_minute: int = 1439,
    slot_minutes: int = 15,
    calendar: SessionCalendar | None = None,
    htf_art: pd.Series | None = None,
    htf_art_long: pd.Series | None = None,
    htf_art_short: pd.Series | None = None,
    htf_atr: pd.Series | None = None,
) -> list[Bar]:
    """Convert a closed OHLCV frame without sorting or filling missing data."""

    if not 0 <= session_start_minute < session_end_minute < 24 * 60:
        raise ValueError("session bounds must be ordered within one day")
    if slot_minutes < 1:
        raise ValueError("slot_minutes must be positive")
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")
    if not df.index.is_monotonic_increasing:
        raise ValueError("DataFrame index must be monotonic increasing")
    if df.index.has_duplicates:
        raise ValueError("DataFrame index must not contain duplicates")
    if htf_art is not None and not htf_art.index.equals(df.index):
        raise ValueError("htf_art must have the same index as the DataFrame")
    for name, series in (("htf_art_long", htf_art_long), ("htf_art_short", htf_art_short)):
        if series is not None and not series.index.equals(df.index):
            raise ValueError(f"{name} must have the same index as the DataFrame")
    if htf_atr is not None and not htf_atr.index.equals(df.index):
        raise ValueError("htf_atr must have the same index as the DataFrame")

    bars: list[Bar] = []
    calendar = calendar or SessionCalendar()
    for index, (timestamp, row) in enumerate(df.iterrows()):
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.tz_convert("UTC") if timestamp.tzinfo else timestamp.tz_localize("UTC")
            day = timestamp.date().isoformat()
            minute_of_day = timestamp.hour * 60 + timestamp.minute
            valid_session = calendar.is_valid_bar(
                day, minute_of_day, session_start_minute, session_end_minute,
            )
            slot = min(
                (minute_of_day - session_start_minute) // slot_minutes,
                (session_end_minute - session_start_minute) // slot_minutes,
            ) if valid_session else None
            rvol_day = calendar.is_valid_rvol_day(day)
        else:
            day = None
            slot = None
            valid_session = True
            rvol_day = True
        open_, high, low, close, volume = (
            float(row["open"]), float(row["high"]), float(row["low"]),
            float(row["close"]), float(row["volume"]),
        )
        spread = float(row["spread"]) if "spread" in df.columns and row["spread"] == row["spread"] else None
        slippage = float(row["slippage"]) if "slippage" in df.columns and row["slippage"] == row["slippage"] else None
        if not all(value == value for value in (open_, high, low, close, volume)):
            raise ValueError(f"NaN OHLCV value at row {index}")
        if high < max(open_, close) or low > min(open_, close) or high < low:
            raise ValueError(f"invalid OHLC range at row {index}")
        art = None if htf_art is None or pd.isna(htf_art.iloc[index]) else float(htf_art.iloc[index])
        art_long = None if htf_art_long is None or pd.isna(htf_art_long.iloc[index]) else float(htf_art_long.iloc[index])
        art_short = None if htf_art_short is None or pd.isna(htf_art_short.iloc[index]) else float(htf_art_short.iloc[index])
        atr_value = None if htf_atr is None or pd.isna(htf_atr.iloc[index]) else float(htf_atr.iloc[index])
        bars.append(Bar(index, open_, high, low, close, volume, day, slot, valid_session, rvol_day, spread, slippage, art, art_long, art_short, atr_value))
    return bars


def m1_bars_by_parent(
    m1_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    m1_bar_minutes: int = 1,
    parent_bar_minutes: int | None = None,
) -> dict[int, tuple[Bar, ...]]:
    """Attach closed M1 bars to parent bars by half-open time intervals.

    Parent timestamps are interpreted as bar-open timestamps. Every interval is
    ``[parent[i], parent[i+1])``; the final interval ends after
    ``m1_bar_minutes``. M1 data outside these intervals is rejected to prevent
    accidental use of data from a different session or timeframe.
    """

    if m1_bar_minutes < 1:
        raise ValueError("m1_bar_minutes must be positive")
    if parent_bar_minutes is not None and parent_bar_minutes < 1:
        raise ValueError("parent_bar_minutes must be positive")
    if not isinstance(m1_df.index, pd.DatetimeIndex) or not isinstance(parent_df.index, pd.DatetimeIndex):
        raise ValueError("parent and M1 data must use a DatetimeIndex")
    if not parent_df.index.is_monotonic_increasing or parent_df.index.has_duplicates:
        raise ValueError("parent index must be sorted and unique")
    if not m1_df.index.is_monotonic_increasing or m1_df.index.has_duplicates:
        raise ValueError("M1 index must be sorted and unique")
    if parent_df.empty:
        return {}

    parent_times = parent_df.index.tz_convert("UTC") if parent_df.index.tz else parent_df.index.tz_localize("UTC")
    m1_times = m1_df.index.tz_convert("UTC") if m1_df.index.tz else m1_df.index.tz_localize("UTC")
    if len(parent_times) > 1:
        deltas = parent_times[1:] - parent_times[:-1]
        if any(delta <= pd.Timedelta(0) for delta in deltas):
            raise ValueError("parent timestamps must be strictly increasing")
        final_parent_delta = deltas[-1]
    elif parent_bar_minutes is not None:
        final_parent_delta = pd.Timedelta(minutes=parent_bar_minutes)
    else:
        final_parent_delta = pd.Timedelta(minutes=m1_bar_minutes)
    if len(m1_times) and (m1_times[0] < parent_times[0] or m1_times[-1] >= parent_times[-1] + final_parent_delta):
        raise ValueError("M1 data contains timestamps outside parent intervals")
    m1_bars = bars_from_dataframe(m1_df)
    result: dict[int, tuple[Bar, ...]] = {}
    cursor = 0
    for parent_index, start in enumerate(parent_times):
        end = (
            parent_times[parent_index + 1]
            if parent_index + 1 < len(parent_times)
            else start + final_parent_delta
        )
        if end <= start:
            raise ValueError("parent timestamps must be strictly increasing")
        attached: list[Bar] = []
        while cursor < len(m1_times) and m1_times[cursor] < end:
            if m1_times[cursor] >= start:
                attached.append(m1_bars[cursor])
            elif m1_times[cursor] >= parent_times[0]:
                raise ValueError(f"M1 timestamp {m1_times[cursor]} is not inside parent interval")
            cursor += 1
        result[parent_index] = tuple(attached)
    if cursor < len(m1_times):
        raise ValueError(f"M1 timestamp {m1_times[cursor]} is outside parent intervals")
    return result


def run_dataframe_backtest(
    df: pd.DataFrame,
    config: StrategyConfig | None = None,
    quantity: float = 1.0,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
    htf_art: pd.Series | None = None,
    htf_art_long: pd.Series | None = None,
    htf_art_short: pd.Series | None = None,
    htf_atr: pd.Series | None = None,
) -> BacktestResult:
    config = config or StrategyConfig()
    if config.exhaustion_mode == "WAVE_ATR" and isinstance(df.index, pd.DatetimeIndex):
        htf_art_long, htf_art_short = _closed_htf_directional_wave_ranges(
            df, pivot_q=config.pivot_q, n_waves=config.n_waves, selection=config.wave_selection,
        ) if htf_art_long is None or htf_art_short is None else (htf_art_long, htf_art_short)
    bars = bars_from_dataframe(
        df,
        session_start_minute=config.session_start_minute,
        session_end_minute=config.session_end_minute,
        slot_minutes=config.slot_minutes,
        calendar=config.calendar,
        htf_art=htf_art,
        htf_art_long=htf_art_long,
        htf_art_short=htf_art_short,
        htf_atr=htf_atr,
    )
    engine = StrategyEngine(config=config, quantity=quantity)
    equity_curve: list[dict] = []
    for bar in bars:
        engine.on_bar(bar, (m1_by_bar or {}).get(bar.index, ()))
        realized = sum(trade.net_pnl for trade in engine.trades)
        floating = mark_to_market_pnl(engine.position, bar.close, config, bar)
        equity_curve.append({
            "bar": bar.index,
            "realized_pnl": realized,
            "unrealized_pnl": floating,
            "equity_pnl": realized + floating,
        })
    terminal_bar = bars[-1] if bars else None
    if liquidate_at_end and terminal_bar is not None and engine.position is not None:
        engine._close_position(
            terminal_bar.index,
            engine._exit_market(terminal_bar.close, engine.position.side, terminal_bar),
            "CLOSED_END",
        )
        realized = sum(trade.net_pnl for trade in engine.trades)
        if equity_curve:
            equity_curve[-1] = {
                "bar": terminal_bar.index,
                "realized_pnl": realized,
                "unrealized_pnl": 0.0,
                "equity_pnl": realized,
            }
    return summarize_trades(
        engine.trades,
        engine.events,
        engine.position,
        engine.pending,
        terminal_bar.close if terminal_bar is not None else None,
        config,
        equity_curve,
        engine.audit,
        build_run_manifest(df, config, "single", quantity, m1_by_bar, liquidate_at_end),
    )


def _slice_m1(
    m1_by_bar: Mapping[int, Sequence[Bar]] | None,
    start: int,
    stop: int,
) -> dict[int, Sequence[Bar]]:
    if not m1_by_bar:
        return {}
    return {index - start: values for index, values in m1_by_bar.items() if start <= index < stop}


def _aggregate_equity_curves(results: Sequence[BacktestResult]) -> list[dict]:
    """Join independent OOS fold curves into one continuous equity series."""

    curve: list[dict] = []
    offset = 0.0
    bar_index = 0
    for result in results:
        for point in result.equity_curve:
            curve.append({
                "bar": bar_index,
                "realized_pnl": offset + point["realized_pnl"],
                "unrealized_pnl": point["unrealized_pnl"],
                "equity_pnl": offset + point["equity_pnl"],
            })
            bar_index += 1
        offset += result.equity_pnl
    return curve


def _annualized_return(result: BacktestResult, frame: pd.DataFrame, initial_capital: float) -> float | None:
    if initial_capital <= 0 or len(frame) < 2:
        return None
    final_capital = initial_capital + result.final_realized_pnl
    if final_capital <= 0:
        return None
    if isinstance(frame.index, pd.DatetimeIndex):
        elapsed = (frame.index[-1] - frame.index[0]).total_seconds() / (365.25 * 24 * 3600)
        years = max(elapsed, 1.0 / 365.25)
    else:
        years = 1.0
    return (final_capital / initial_capital) ** (1.0 / years) - 1.0


def walk_forward_efficiency(
    in_sample: BacktestResult,
    out_of_sample: BacktestResult,
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    initial_capital: float = 100_000.0,
) -> float | None:
    """Return CAGR(OOS) / CAGR(IS), or None when IS is not profitable."""

    is_return = _annualized_return(in_sample, train_frame, initial_capital)
    oos_return = _annualized_return(out_of_sample, test_frame, initial_capital)
    if is_return is None or oos_return is None or is_return <= 0:
        return None
    return oos_return / is_return


def walk_forward_backtest(
    df: pd.DataFrame,
    config: StrategyConfig | None = None,
    train_bars: int = 12 * 21,
    test_bars: int = 3 * 21,
    step_bars: int | None = None,
    quantity: float = 1.0,
    initial_capital: float = 100_000.0,
    warmup_bars: int = 0,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
) -> WalkForwardResult:
    """Run independent rolling IS/OOS folds without carrying state across folds."""

    if train_bars < 1 or test_bars < 1:
        raise ValueError("train_bars and test_bars must be positive")
    if warmup_bars < 0:
        raise ValueError("warmup_bars must be non-negative")
    step = test_bars if step_bars is None else step_bars
    if step < 1:
        raise ValueError("step_bars must be positive")
    runtime_config = config or StrategyConfig()
    full_htf_art = (
        _closed_htf_wave_ranges(df, pivot_q=runtime_config.pivot_q)
        if runtime_config.exhaustion_mode == "WAVE_ATR" and isinstance(df.index, pd.DatetimeIndex)
        else None
    )
    full_htf_directional = (
        _closed_htf_directional_wave_ranges(
            df, pivot_q=runtime_config.pivot_q, n_waves=runtime_config.n_waves,
            selection=runtime_config.wave_selection,
        )
        if runtime_config.exhaustion_mode == "WAVE_ATR" and isinstance(df.index, pd.DatetimeIndex)
        else (None, None)
    )
    bars = bars_from_dataframe(
        df,
        session_start_minute=runtime_config.session_start_minute,
        session_end_minute=runtime_config.session_end_minute,
        slot_minutes=runtime_config.slot_minutes,
        calendar=runtime_config.calendar,
    )
    folds: list[WalkForwardFold] = []
    oos_trades: list[Trade] = []
    oos_events: list = []
    oos_audit: list = []
    fold_number = 0
    start = 0
    while start + train_bars + test_bars <= len(bars):
        train_end = start + train_bars
        test_end = train_end + test_bars
        train_frame = df.iloc[start:train_end]
        test_frame = df.iloc[train_end:test_end]
        train_result = run_dataframe_backtest(
            train_frame, runtime_config, quantity, _slice_m1(m1_by_bar, start, train_end), liquidate_at_end,
            None if full_htf_art is None else full_htf_art.iloc[start:train_end],
            None if full_htf_directional[0] is None else full_htf_directional[0].iloc[start:train_end],
            None if full_htf_directional[1] is None else full_htf_directional[1].iloc[start:train_end],
        )
        if warmup_bars:
            context_start = max(0, train_end - warmup_bars)
            warmup_length = train_end - context_start
            context_frame = df.iloc[context_start:test_end].copy()
            context_m1 = _slice_m1(m1_by_bar, context_start, test_end)
            context_engine = StrategyEngine(config=runtime_config, quantity=quantity)
            context_bars = bars_from_dataframe(
                context_frame,
                session_start_minute=runtime_config.session_start_minute,
                session_end_minute=runtime_config.session_end_minute,
                slot_minutes=runtime_config.slot_minutes,
                calendar=runtime_config.calendar,
                htf_art=None if full_htf_art is None else full_htf_art.iloc[context_start:test_end],
                htf_art_long=full_htf_directional[0].iloc[context_start:test_end],
                htf_art_short=full_htf_directional[1].iloc[context_start:test_end],
            )
            context_equity: list[dict] = []
            for context_bar in context_bars:
                context_engine.on_bar(
                    context_bar,
                    context_m1.get(context_bar.index, ()),
                    emit_signals=context_bar.index >= warmup_length,
                )
                if context_bar.index >= warmup_length:
                    oos_trades_so_far = [
                        trade for trade in context_engine.trades if trade.entry_bar >= warmup_length
                    ]
                    realized = sum(trade.net_pnl for trade in oos_trades_so_far)
                    floating = mark_to_market_pnl(
                        context_engine.position, context_bar.close, runtime_config, context_bar,
                    )
                    context_equity.append({
                        "bar": context_bar.index - warmup_length,
                        "realized_pnl": realized,
                        "unrealized_pnl": floating,
                        "equity_pnl": realized + floating,
                    })
            if liquidate_at_end and context_bars and context_engine.position is not None:
                terminal = context_bars[-1]
                terminal_mark_price = terminal.close
                context_engine._close_position(
                    terminal.index,
                    context_engine._exit_market(terminal.close, context_engine.position.side, terminal),
                    "CLOSED_END",
                )
                if context_equity:
                    realized = sum(
                        trade.net_pnl for trade in context_engine.trades
                        if trade.entry_bar >= warmup_length
                    )
                    context_equity[-1] = {
                        "bar": context_equity[-1]["bar"],
                        "realized_pnl": realized,
                        "unrealized_pnl": 0.0,
                        "equity_pnl": realized,
                    }
            else:
                terminal_mark_price = context_bars[-1].close if context_bars else None
            context_trades = [trade for trade in context_engine.trades if trade.entry_bar >= warmup_length]
            context_events = [event for event in context_engine.events if event.bar >= warmup_length]
            test_position = context_engine.position
            terminal_price = terminal_mark_price
            test_result = summarize_trades(
                context_trades,
                context_events,
                test_position,
                context_engine.pending,
                terminal_price,
                runtime_config,
                equity_curve=context_equity,
                audit=[record for record in context_engine.audit if record.bar >= warmup_length],
            )
        else:
            test_result = run_dataframe_backtest(
                test_frame, runtime_config, quantity, _slice_m1(m1_by_bar, train_end, test_end), liquidate_at_end,
                None if full_htf_art is None else full_htf_art.iloc[train_end:test_end],
                None if full_htf_directional[0] is None else full_htf_directional[0].iloc[train_end:test_end],
                None if full_htf_directional[1] is None else full_htf_directional[1].iloc[train_end:test_end],
            )
        fold = WalkForwardFold(
            fold_number, start, train_end, train_end, test_end,
            train_result, test_result,
            walk_forward_efficiency(train_result, test_result, train_frame, test_frame, initial_capital),
        )
        folds.append(fold)
        oos_trades.extend(test_result.trades)
        oos_events.extend(test_result.events)
        oos_audit.extend(test_result.audit)
        fold_number += 1
        start += step
    aggregate = summarize_trades(
        oos_trades,
        oos_events,
        audit=oos_audit,
        equity_curve=_aggregate_equity_curves([fold.out_of_sample for fold in folds]),
    )
    valid_wfe = [fold.wfe for fold in folds if fold.wfe is not None]
    return WalkForwardResult(
        tuple(folds),
        aggregate,
        sum(valid_wfe) / len(valid_wfe) if valid_wfe else None,
        build_run_manifest(df, runtime_config, "wfo", quantity, m1_by_bar, liquidate_at_end),
    )


def _select_is_result(results: Sequence[SensitivityResult]) -> SensitivityResult:
    """Select an IS winner with deterministic tie-breaking."""

    if not results:
        raise ValueError("optimization grid produced no combinations")
    return min(
        results,
        key=lambda item: (
            -item.result.equity_pnl,
            item.result.max_drawdown,
            json.dumps(item.parameters, sort_keys=True, separators=(",", ":")),
        ),
    )


def walk_forward_optimize(
    df: pd.DataFrame,
    config: StrategyConfig,
    grid: Mapping[str, Sequence[Any]],
    train_bars: int = 12 * 21,
    test_bars: int = 3 * 21,
    step_bars: int | None = None,
    quantity: float = 1.0,
    initial_capital: float = 100_000.0,
    warmup_bars: int = 0,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
) -> WalkForwardResult:
    """Optimize parameters on each IS window, then freeze them for OOS."""

    if not grid:
        raise ValueError("optimization grid must not be empty")
    if train_bars < 1 or test_bars < 1:
        raise ValueError("train_bars and test_bars must be positive")
    step = test_bars if step_bars is None else step_bars
    if step < 1:
        raise ValueError("step_bars must be positive")
    runtime_config = config
    full_htf_art = (
        _closed_htf_wave_ranges(df, pivot_q=runtime_config.pivot_q)
        if runtime_config.exhaustion_mode == "WAVE_ATR" and isinstance(df.index, pd.DatetimeIndex)
        else None
    )
    full_htf_directional = (
        _closed_htf_directional_wave_ranges(
            df, pivot_q=runtime_config.pivot_q, n_waves=runtime_config.n_waves,
            selection=runtime_config.wave_selection,
        )
        if runtime_config.exhaustion_mode == "WAVE_ATR" and isinstance(df.index, pd.DatetimeIndex)
        else (None, None)
    )
    bars = bars_from_dataframe(
        df,
        session_start_minute=runtime_config.session_start_minute,
        session_end_minute=runtime_config.session_end_minute,
        slot_minutes=runtime_config.slot_minutes,
        calendar=runtime_config.calendar,
    )
    folds: list[WalkForwardFold] = []
    oos_trades: list[Trade] = []
    oos_events: list = []
    oos_audit: list = []
    start = 0
    fold_number = 0
    while start + train_bars + test_bars <= len(bars):
        train_end = start + train_bars
        test_end = train_end + test_bars
        train_frame = df.iloc[start:train_end]
        test_frame = df.iloc[train_end:test_end]
        is_results = sensitivity_grid(
            train_frame,
            runtime_config,
            grid,
            quantity,
            _slice_m1(m1_by_bar, start, train_end),
            liquidate_at_end,
            None if full_htf_art is None else full_htf_art.iloc[start:train_end],
            None if full_htf_directional[0] is None else full_htf_directional[0].iloc[start:train_end],
            None if full_htf_directional[1] is None else full_htf_directional[1].iloc[start:train_end],
        )
        winner = _select_is_result(is_results)
        selected_config = replace(runtime_config, **winner.parameters)
        if warmup_bars:
            context_start = max(0, train_end - warmup_bars)
            warmup_length = train_end - context_start
            context_frame = df.iloc[context_start:test_end]
            context_m1 = _slice_m1(m1_by_bar, context_start, test_end)
            context_bars = bars_from_dataframe(
                context_frame,
                session_start_minute=selected_config.session_start_minute,
                session_end_minute=selected_config.session_end_minute,
                slot_minutes=selected_config.slot_minutes,
                calendar=selected_config.calendar,
                htf_art=(
                    None
                    if full_htf_art is None
                    else full_htf_art.iloc[context_start:test_end]
                ),
                htf_art_long=None if full_htf_directional[0] is None else full_htf_directional[0].iloc[context_start:test_end],
                htf_art_short=None if full_htf_directional[1] is None else full_htf_directional[1].iloc[context_start:test_end],
            )
            engine = StrategyEngine(selected_config, quantity)
            context_equity: list[dict] = []
            for context_bar in context_bars:
                engine.on_bar(
                    context_bar,
                    context_m1.get(context_bar.index, ()),
                    emit_signals=context_bar.index >= warmup_length,
                )
                if context_bar.index >= warmup_length:
                    oos_trades_so_far = [
                        trade for trade in engine.trades if trade.entry_bar >= warmup_length
                    ]
                    realized = sum(trade.net_pnl for trade in oos_trades_so_far)
                    floating = mark_to_market_pnl(engine.position, context_bar.close, selected_config, context_bar)
                    context_equity.append({
                        "bar": context_bar.index - warmup_length,
                        "realized_pnl": realized,
                        "unrealized_pnl": floating,
                        "equity_pnl": realized + floating,
                    })
            terminal_price = context_bars[-1].close if context_bars else None
            if liquidate_at_end and context_bars and engine.position is not None:
                terminal = context_bars[-1]
                engine._close_position(
                    terminal.index,
                    engine._exit_market(terminal.close, engine.position.side, terminal),
                    "CLOSED_END",
                )
                if context_equity:
                    realized = sum(
                        trade.net_pnl for trade in engine.trades
                        if trade.entry_bar >= warmup_length
                    )
                    context_equity[-1] = {
                        "bar": context_equity[-1]["bar"],
                        "realized_pnl": realized,
                        "unrealized_pnl": 0.0,
                        "equity_pnl": realized,
                    }
            test_trades = [trade for trade in engine.trades if trade.entry_bar >= warmup_length]
            test_events = [event for event in engine.events if event.bar >= warmup_length]
            test_audit = [record for record in engine.audit if record.bar >= warmup_length]
            test_result = summarize_trades(
                test_trades,
                test_events,
                engine.position,
                engine.pending,
                terminal_price,
                selected_config,
                equity_curve=context_equity,
                audit=test_audit,
            )
        else:
            test_result = run_dataframe_backtest(
                test_frame,
                selected_config,
                quantity,
                _slice_m1(m1_by_bar, train_end, test_end),
                liquidate_at_end,
                None if full_htf_art is None else full_htf_art.iloc[train_end:test_end],
            )
        fold = WalkForwardFold(
            fold_number,
            start,
            train_end,
            train_end,
            test_end,
            winner.result,
            test_result,
            walk_forward_efficiency(winner.result, test_result, train_frame, test_frame, initial_capital),
            dict(winner.parameters),
        )
        folds.append(fold)
        oos_trades.extend(test_result.trades)
        oos_events.extend(test_result.events)
        oos_audit.extend(test_result.audit)
        start += step
        fold_number += 1
    aggregate = summarize_trades(
        oos_trades,
        oos_events,
        audit=oos_audit,
        equity_curve=_aggregate_equity_curves([fold.out_of_sample for fold in folds]),
    )
    valid_wfe = [fold.wfe for fold in folds if fold.wfe is not None]
    return WalkForwardResult(
        tuple(folds),
        aggregate,
        sum(valid_wfe) / len(valid_wfe) if valid_wfe else None,
        build_run_manifest(df, runtime_config, "wfo_optimized", quantity, m1_by_bar, liquidate_at_end),
    )


def sensitivity_grid(
    df: pd.DataFrame,
    config: StrategyConfig,
    grid: Mapping[str, Sequence[Any]],
    quantity: float = 1.0,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
    htf_art: pd.Series | None = None,
    htf_art_long: pd.Series | None = None,
    htf_art_short: pd.Series | None = None,
) -> tuple[SensitivityResult, ...]:
    """Run every parameter combination in an isolated engine."""

    unknown = set(grid).difference(config.__dataclass_fields__)
    if unknown:
        raise ValueError(f"unknown sensitivity parameters: {sorted(unknown)}")
    names = tuple(grid)
    results = []
    for values in product(*(grid[name] for name in names)):
        parameters = dict(zip(names, values))
        candidate = replace(config, **parameters)
        results.append(SensitivityResult(
                parameters,
                run_dataframe_backtest(
                    df, candidate, quantity, m1_by_bar, liquidate_at_end,
                    htf_art, htf_art_long, htf_art_short,
                ),
        ))
    return tuple(results)


def stress_costs(
    df: pd.DataFrame,
    config: StrategyConfig,
    multipliers: Sequence[float] = (1.0, 2.0, 3.0),
    quantity: float = 1.0,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
    liquidate_at_end: bool = False,
) -> tuple[SensitivityResult, ...]:
    """Stress fixed spread, slippage and commission independently per run."""

    if any(multiplier < 0 for multiplier in multipliers):
        raise ValueError("cost multipliers must be non-negative")
    results = []
    for multiplier in multipliers:
        candidate = replace(
            config,
            fixed_spread=config.fixed_spread * multiplier,
            fixed_slippage=config.fixed_slippage * multiplier,
            commission_rate=config.commission_rate * multiplier,
        )
        results.append(SensitivityResult(
            {"cost_multiplier": multiplier},
            run_dataframe_backtest(df, candidate, quantity, m1_by_bar, liquidate_at_end),
        ))
    return tuple(results)


def summarize_sensitivity(
    results: Sequence[SensitivityResult],
    min_neighbor_ratio: float = 0.80,
    min_positive_fraction: float = 0.50,
) -> SensitivitySummary:
    """Evaluate whether sensitivity results form a stable region, not a spike."""

    if not isfinite(min_neighbor_ratio) or not 0 <= min_neighbor_ratio <= 1:
        raise ValueError("min_neighbor_ratio must be within [0, 1]")
    if not isfinite(min_positive_fraction) or not 0 <= min_positive_fraction <= 1:
        raise ValueError("min_positive_fraction must be within [0, 1]")
    if not results:
        return SensitivitySummary(False, 0, None, None, None, 0.0, 0, None, ("no_combinations",))

    ordered = sorted(results, key=lambda item: item.result.equity_pnl, reverse=True)
    best = ordered[0]
    values = [item.result.equity_pnl for item in results]
    positive_fraction = sum(value > 0 for value in values) / len(values)
    median_value = float(pd.Series(values).median())
    parameter_names = tuple(best.parameters)
    neighbors = []
    for candidate in results:
        differences = [name for name in parameter_names if candidate.parameters[name] != best.parameters[name]]
        if len(differences) != 1:
            continue
        name = differences[0]
        values_for_name = sorted({item.parameters[name] for item in results})
        best_position = values_for_name.index(best.parameters[name])
        candidate_position = values_for_name.index(candidate.parameters[name])
        if abs(candidate_position - best_position) == 1 and all(
            candidate.parameters[other] == best.parameters[other]
            for other in parameter_names if other != name
        ):
            neighbors.append(candidate.result.equity_pnl)
    if best.result.equity_pnl > 0 and neighbors:
        neighbor_ratio = float(pd.Series(neighbors).median()) / best.result.equity_pnl
    else:
        neighbor_ratio = None
    failures = []
    if positive_fraction < min_positive_fraction:
        failures.append("positive_fraction")
    if not neighbors:
        failures.append("no_neighbors")
    elif neighbor_ratio is None or neighbor_ratio < min_neighbor_ratio:
        failures.append("sharp_peak")
    return SensitivitySummary(
        not failures,
        len(results),
        dict(best.parameters),
        best.result.equity_pnl,
        median_value,
        positive_fraction,
        len(neighbors),
        neighbor_ratio,
        tuple(failures),
    )


def assess_robustness(
    walk_forward: WalkForwardResult,
    stress_results: Sequence[SensitivityResult] = (),
    min_wfe: float = 0.60,
    min_profitable_oos_fraction: float = 0.50,
    min_oos_trades: int = 1,
    require_positive_stress: bool = True,
    sensitivity: SensitivitySummary | None = None,
    require_sensitivity: bool = False,
) -> RobustnessReport:
    """Apply explicit quality gates to already completed validation runs."""

    if (
        not isfinite(min_wfe)
        or not isfinite(min_profitable_oos_fraction)
        or min_wfe < 0
        or not 0 <= min_profitable_oos_fraction <= 1
        or min_oos_trades < 0
    ):
        raise ValueError("invalid robustness thresholds")
    folds = walk_forward.folds
    wfe_values = [fold.wfe for fold in folds if fold.wfe is not None]
    profitable_folds = sum(
        fold.out_of_sample.equity_pnl > 0 for fold in folds
    )
    profitable_fraction = profitable_folds / len(folds) if folds else 0.0
    worst_wfe = min(wfe_values) if wfe_values else None
    oos_trades = len(walk_forward.aggregate_oos.trades)
    stress_values = [item.result.equity_pnl for item in stress_results]
    worst_stress = min(stress_values) if stress_values else None

    checks = {
        "has_folds": bool(folds),
        "wfe": len(wfe_values) == len(folds) and bool(wfe_values) and worst_wfe >= min_wfe,
        "profitable_oos_fraction": profitable_fraction >= min_profitable_oos_fraction,
        "minimum_oos_trades": oos_trades >= min_oos_trades,
        "positive_stress": (
            not require_positive_stress
            or not stress_values
            or worst_stress > 0
        ),
        "sensitivity": (
            not require_sensitivity
            or (sensitivity is not None and sensitivity.passed)
        ),
    }
    failures = tuple(name for name, passed in checks.items() if not passed)
    return RobustnessReport(
        not failures,
        checks,
        {
            "folds": len(folds),
            "worst_wfe": worst_wfe,
            "mean_wfe": walk_forward.mean_wfe,
            "profitable_oos_fraction": profitable_fraction,
            "oos_trades": oos_trades,
            "worst_stress_equity_pnl": worst_stress,
            "min_wfe": min_wfe,
            "min_profitable_oos_fraction": min_profitable_oos_fraction,
            "sensitivity_positive_fraction": sensitivity.positive_fraction if sensitivity else None,
            "sensitivity_neighbor_median_ratio": sensitivity.neighbor_median_ratio if sensitivity else None,
        },
        failures,
    )


def summarize_trades(
    trades: Sequence[Trade], events: Sequence = (), open_position=None, pending_order=None,
    terminal_mark_price: float | None = None, config: StrategyConfig | None = None,
    equity_curve: Sequence[Mapping[str, Any]] = (),
    audit: Sequence = (),
    manifest: Mapping[str, Any] | None = None,
) -> BacktestResult:
    pnl = 0.0
    peak = 0.0
    max_drawdown = 0.0
    wins = 0
    gross_wins = 0.0
    gross_losses = 0.0
    for trade in trades:
        pnl += trade.net_pnl
        peak = max(peak, pnl)
        max_drawdown = max(max_drawdown, peak - pnl)
        if trade.net_pnl > 0:
            wins += 1
            gross_wins += trade.net_pnl
        elif trade.net_pnl < 0:
            gross_losses += abs(trade.net_pnl)
    count = len(trades)
    unrealized = mark_to_market_pnl(open_position, terminal_mark_price, config)
    curve = tuple(dict(point) for point in equity_curve)
    curve_drawdown = max(
        (peak - point["equity_pnl"] for peak, point in _running_peaks(curve)),
        default=0.0,
    )
    return BacktestResult(
        tuple(trades), tuple(events), pnl, max(curve_drawdown, max_drawdown),
        wins / count if count else 0.0,
        gross_wins / gross_losses if gross_losses else None,
        open_position.__dict__.copy() if open_position is not None else None,
        pending_order.__dict__.copy() if pending_order is not None else None,
        unrealized,
        pnl + unrealized,
        terminal_mark_price,
        curve,
        tuple(audit),
        summarize_audit(audit),
        dict(manifest) if manifest is not None else None,
    )


def _running_peaks(curve: Sequence[Mapping[str, Any]]):
    peak = 0.0
    for point in curve:
        peak = max(peak, float(point["equity_pnl"]))
        yield peak, point


def mark_to_market_pnl(
    position: Mapping[str, Any] | Any | None,
    close_price: float | None,
    config: StrategyConfig | None = None,
    bar: Bar | None = None,
) -> float:
    """Mark an open position to a hypothetical market exit at ``close_price``."""

    if position is None or close_price is None:
        return 0.0
    config = config or StrategyConfig()
    if isinstance(position, Mapping):
        side = position["side"]
        entry = position["entry_price"]
        quantity = position["quantity"]
    else:
        side = position.side
        entry = position.entry_price
        quantity = position.quantity
    side = side.value if hasattr(side, "value") else side
    spread = config.fixed_spread
    slippage = config.fixed_slippage
    if config.spread_model == "DYNAMIC_FROM_DATA":
        if bar is None or bar.spread is None:
            raise ValueError("dynamic spread requires spread on terminal bar")
        spread = bar.spread
    if config.slippage_model == "DYNAMIC_FROM_DATA":
        if bar is None or bar.slippage is None:
            raise ValueError("dynamic slippage requires slippage on terminal bar")
        slippage = bar.slippage
    adjustment = spread / 2.0 + slippage
    exit_price = close_price - adjustment if side == "LONG" else close_price + adjustment
    gross = (exit_price - entry) * quantity if side == "LONG" else (entry - exit_price) * quantity
    fees = (entry + exit_price) * quantity * config.commission_rate
    return gross - fees


def assert_causal_prefix(
    bars: Sequence[Bar],
    cutoff: int,
    config: StrategyConfig | None = None,
    m1_by_bar: Mapping[int, Sequence[Bar]] | None = None,
) -> None:
    """Raise if appending future bars changes events through ``cutoff``."""

    if cutoff < 0 or cutoff >= len(bars):
        raise ValueError("cutoff must identify a bar in the supplied series")
    prefix_engine = StrategyEngine(config=config)
    full_engine = StrategyEngine(config=config)
    minute_data = m1_by_bar or {}
    for bar in bars[:cutoff + 1]:
        prefix_engine.on_bar(bar, minute_data.get(bar.index, ()))
    for bar in bars:
        full_engine.on_bar(bar, minute_data.get(bar.index, ()))
    prefix_events = [event for event in prefix_engine.events if event.bar <= cutoff]
    full_events = [event for event in full_engine.events if event.bar <= cutoff]
    if prefix_events != full_events:
        raise AssertionError(f"future bars changed events at or before bar {cutoff}")
