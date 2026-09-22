"""Causal, event-driven implementation of the Zvezdin strategy contract.

The engine deliberately does not use pandas or a retrospective indicator pass.
``StrategyEngine.on_bar`` processes one closed bar at a time and only queues a
signal for the next bar.  This makes the state transitions easy to audit and
keeps the implementation usable with live feeds as well as historical data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import ceil, isfinite
from statistics import median
from typing import Sequence

from .zvezdin_calendar import SessionCalendar


class ZoneType(str, Enum):
    RESISTANCE = "RESISTANCE"
    SUPPORT = "SUPPORT"


class ZoneStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED_TOUCHES = "EXPIRED_TOUCHES"
    EXPIRED_AGE = "EXPIRED_AGE"
    INVALIDATED_BROKEN = "INVALIDATED_BROKEN"


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ReversalPhase(str, Enum):
    IDLE = "IDLE"
    IMPULSE_REACHED = "IMPULSE_REACHED"
    COMPRESSION = "COMPRESSION"
    RE_EXPANSION = "RE_EXPANSION"


class PositionStatus(str, Enum):
    IDLE = "IDLE"
    SIGNAL_PENDING = "SIGNAL_PENDING"
    IN_POSITION = "IN_POSITION"


@dataclass(frozen=True)
class Bar:
    """A closed OHLCV bar. ``day`` and ``slot`` are used by causal RVOL."""

    index: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    day: str | int | None = None
    slot: int | None = None
    valid_session: bool = True
    rvol_valid_day: bool = True
    spread: float | None = None
    slippage: float | None = None
    htf_art: float | None = None
    htf_art_long: float | None = None
    htf_art_short: float | None = None
    htf_atr: float | None = None

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if self.index < 0 or not all(isfinite(value) for value in values):
            raise ValueError("bar index and OHLCV values must be finite")
        if (
            self.volume < 0
            or self.high < self.low
            or self.high < max(self.open, self.close)
            or self.low > min(self.open, self.close)
        ):
            raise ValueError("invalid OHLCV bar")
        if self.spread is not None and (not isfinite(self.spread) or self.spread < 0):
            raise ValueError("spread must be finite and non-negative")
        if self.slippage is not None and (not isfinite(self.slippage) or self.slippage < 0):
            raise ValueError("slippage must be finite and non-negative")
        if self.htf_art is not None and (not isfinite(self.htf_art) or self.htf_art < 0):
            raise ValueError("htf_art must be finite and non-negative")
        for name in ("htf_art_long", "htf_art_short"):
            value = getattr(self, name)
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError(f"{name} must be finite and non-negative")
        if self.htf_atr is not None and (not isfinite(self.htf_atr) or self.htf_atr < 0):
            raise ValueError("htf_atr must be finite and non-negative")


@dataclass(frozen=True)
class Pivot:
    index: int
    confirmed_at: int
    price: float
    kind: ZoneType


@dataclass
class Zone:
    zone_id: int
    zone_type: ZoneType
    center: float
    width: float
    created_at: int
    eligible_from: int
    touches: int = 0
    age: int = 0
    hits: int = 1
    status: ZoneStatus = ZoneStatus.ACTIVE
    previous_overlap: bool = False
    last_touch_at: int | None = None

    @property
    def min_price(self) -> float:
        return self.center - self.width

    @property
    def max_price(self) -> float:
        return self.center + self.width


@dataclass
class PendingOrder:
    side: Side
    signal_bar: int
    zone_id: int
    stop_loss: float
    atr: float


@dataclass
class Position:
    side: Side
    entry_bar: int
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    zone_id: int
    initial_risk: float = 0.0


@dataclass
class ReversalSetup:
    phase: ReversalPhase = ReversalPhase.IDLE
    started_at: int | None = None
    compression_bars: int = 0
    impulse_extreme: float | None = None
    impulse_start_price: float | None = None
    impulse_body: float = 0.0
    compression_range_sum: float = 0.0
    zone_id: int | None = None
    compression_high: float | None = None
    compression_low: float | None = None
    level_state: str = "ACTIVE_ZONE"


@dataclass(frozen=True)
class Trade:
    side: Side
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    quantity: float
    reason: str
    net_pnl: float


@dataclass(frozen=True)
class EngineEvent:
    bar: int
    event: str
    side: Side | None = None
    zone_id: int | None = None
    price: float | None = None


@dataclass(frozen=True)
class SignalAudit:
    """Causal decision record produced after a bar closes."""

    bar: int
    atr_previous: float | None
    ema_current: float | None
    zone_id: int | None
    short_zone_id: int | None
    long_zone_id: int | None
    macro_short: bool
    macro_long: bool
    micro_short: bool
    micro_long: bool
    exhaustion_short: bool
    exhaustion_long: bool
    volume_spike: bool
    acceleration: bool
    candle_shape_short: bool
    candle_shape_long: bool
    soft_score_short: int
    soft_score_long: int
    pattern_short: bool
    pattern_long: bool
    decision: str
    block_reason: str | None
    reversal_phase_long: str = ReversalPhase.IDLE.value
    reversal_phase_short: str = ReversalPhase.IDLE.value
    level_state_long: str = "ACTIVE_ZONE"
    level_state_short: str = "ACTIVE_ZONE"
    rsi_value: float | None = None


@dataclass
class StrategyConfig:
    pivot_q: int = 3
    atr_period: int = 14
    ema_period: int = 200
    n_waves: int = 4
    wave_selection: str = "latest_mean"
    reversal_setup_enabled: bool = True
    compression_min_bars: int = 2
    compression_max_bars: int = 4
    compression_range_ratio: float = 0.60
    compression_body_ratio: float = 0.60
    reexpansion_ratio: float = 1.20
    impulse_art_eta: float = 0.85
    exhaustion_eta: float = 0.85
    zone_cluster_atr_ratio: float = 0.15
    zone_width_atr_ratio: float = 0.10
    true_breakout_beta: float = 0.25
    price_discovery_enabled: bool = True
    max_touches: int = 3
    max_age_bars: int = 150
    zone_idle_max_bars: int = 150
    stale_level_enabled: bool = True
    stale_level_atr_min: float = 0.85
    stale_level_atr_max: float = 1.25
    stale_level_require_art: bool = True
    uncertain_rsi_enabled: bool = True
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 65.0
    rvol_days: int = 20
    rvol_k_v: float = 2.5
    rvol_k_std: float = 2.0
    max_gap_atr_ratio: float = 0.20
    risk_reward_ratio: float = 2.5
    tick_size: float = 0.01
    fixed_spread: float = 0.0
    fixed_slippage: float = 0.0
    spread_model: str = "FIXED"
    slippage_model: str = "FIXED"
    slippage_atr_ratio: float = 0.0
    commission_rate: float = 0.0003
    max_concurrent_positions: int = 1
    body_lookback: int = 10
    body_anomaly_ratio: float = 2.0
    volume_floor: float = 1.0
    session_start_minute: int = 0
    session_end_minute: int = 1439
    slot_minutes: int = 15
    zone_signal_mode: str = "STRICT"
    near_zone_atr_ratio: float = 0.10
    relaxation_pct: float = 0.0
    signal_mode: str = "AND"
    min_soft_score: int = 5
    emergency_exit: bool = True
    exhaustion_mode: str = "WAVE_ATR"
    flat_at_day_boundary: bool = True
    score_requires_flow: bool = True
    component_window_acceleration: int = 1
    component_window_atr_completion: int = 1
    component_window_strong_level: int = 1
    component_window_volume_participant: int = 1
    component_window_reverse_impulse: int = 1
    volume_entry_filter: bool = True
    post_entry_volume_management: bool = False
    volume_stop_buffer_atr_ratio: float = 0.10
    volume_target_extension_r: float = 0.50
    calendar: SessionCalendar = field(default_factory=SessionCalendar, compare=False)

    def __post_init__(self) -> None:
        positive_ints = (
            "pivot_q", "atr_period", "ema_period", "n_waves", "max_touches",
            "max_age_bars", "zone_idle_max_bars", "rvol_days", "body_lookback", "max_concurrent_positions",
            "slot_minutes",
            "compression_min_bars", "compression_max_bars", "rsi_period",
        )
        for name in positive_ints:
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        non_negative = (
            "fixed_spread", "fixed_slippage", "commission_rate", "volume_floor",
            "slippage_atr_ratio", "volume_stop_buffer_atr_ratio", "volume_target_extension_r",
            "compression_range_ratio", "compression_body_ratio", "reexpansion_ratio", "impulse_art_eta",
            "stale_level_atr_min", "stale_level_atr_max",
            "rsi_oversold", "rsi_overbought",
        )
        for name in non_negative:
            if not isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        ratio_fields = (
            "exhaustion_eta", "zone_cluster_atr_ratio", "zone_width_atr_ratio",
            "true_breakout_beta", "rvol_k_v", "rvol_k_std", "max_gap_atr_ratio",
            "risk_reward_ratio", "body_anomaly_ratio",
        )
        if any(not isfinite(getattr(self, name)) for name in ratio_fields):
            raise ValueError("strategy ratios must be finite")
        if self.tick_size <= 0 or self.risk_reward_ratio <= 0:
            raise ValueError("tick_size and risk_reward_ratio must be positive")
        if self.spread_model not in {"FIXED", "DYNAMIC_FROM_DATA"}:
            raise ValueError("unsupported spread_model")
        if self.slippage_model not in {"FIXED", "VOLATILITY_SCALED", "DYNAMIC_FROM_DATA"}:
            raise ValueError("unsupported slippage_model")
        if self.spread_model == "DYNAMIC_FROM_DATA" and self.fixed_spread < 0:
            raise ValueError("dynamic spread requires non-negative fallback")
        if self.zone_width_atr_ratio > self.zone_cluster_atr_ratio:
            raise ValueError("zone width ratio cannot exceed cluster radius ratio")
        if self.zone_signal_mode not in {"STRICT", "TOUCH", "RELAXED_REJECTION", "NEAR"}:
            raise ValueError("unsupported zone_signal_mode")
        if not 0 <= self.relaxation_pct <= 100:
            raise ValueError("relaxation_pct must be within [0, 100]")
        if self.signal_mode not in {"AND", "SCORE"}:
            raise ValueError("unsupported signal_mode")
        if not 0 <= self.min_soft_score <= 5:
            raise ValueError("min_soft_score must be within [0, 5]")
        if self.exhaustion_mode not in {"WAVE_ATR", "CURRENT_ATR"}:
            raise ValueError("unsupported exhaustion_mode")
        if self.wave_selection not in {"latest_mean", "last", "longest_mean", "longest"}:
            raise ValueError("unsupported wave_selection")
        if self.compression_min_bars > self.compression_max_bars:
            raise ValueError("compression_min_bars cannot exceed compression_max_bars")
        if self.stale_level_atr_min > self.stale_level_atr_max:
            raise ValueError("stale_level_atr_min cannot exceed stale_level_atr_max")
        if not 0 <= self.rsi_oversold < self.rsi_overbought <= 100:
            raise ValueError("RSI thresholds must satisfy 0 <= oversold < overbought <= 100")
        for name in (
            "component_window_acceleration", "component_window_atr_completion",
            "component_window_strong_level", "component_window_volume_participant",
            "component_window_reverse_impulse",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        if not 0 <= self.session_start_minute < 24 * 60:
            raise ValueError("session_start_minute must be within one day")
        if not self.session_start_minute < self.session_end_minute < 24 * 60:
            raise ValueError("session_end_minute must follow session_start_minute")


def true_range(current: Bar, previous_close: float | None) -> float:
    if previous_close is None:
        return current.high - current.low
    return max(
        current.high - current.low,
        abs(current.high - previous_close),
        abs(current.low - previous_close),
    )


def atr_wilder(bars: Sequence[Bar], period: int) -> list[float | None]:
    """Return causal Wilder ATR values; the seed is the first ``period`` TRs."""

    result: list[float | None] = [None] * len(bars)
    if period < 1 or len(bars) < period:
        return result
    trs = [true_range(bar, bars[i - 1].close if i else None) for i, bar in enumerate(bars)]
    value = sum(trs[:period]) / period
    result[period - 1] = value
    for i in range(period, len(bars)):
        value = ((period - 1) * value + trs[i]) / period
        result[i] = value
    return result


def ema(bars: Sequence[Bar], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(bars)
    if period < 1 or len(bars) < period:
        return result
    value = sum(bar.close for bar in bars[:period]) / period
    result[period - 1] = value
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(bars)):
        value = alpha * bars[i].close + (1.0 - alpha) * value
        result[i] = value
    return result


def body(bar: Bar) -> float:
    return abs(bar.close - bar.open)


def upper_shadow(bar: Bar) -> float:
    return bar.high - max(bar.open, bar.close)


def lower_shadow(bar: Bar) -> float:
    return min(bar.open, bar.close) - bar.low


def is_pivot_high(bars: Sequence[Bar], tau: int, q: int) -> bool:
    if tau < q or tau + q >= len(bars):
        return False
    value = bars[tau].high
    return all(value > bars[tau - i].high for i in range(1, q + 1)) and all(
        value >= bars[tau + i].high for i in range(1, q + 1)
    )


def is_pivot_low(bars: Sequence[Bar], tau: int, q: int) -> bool:
    if tau < q or tau + q >= len(bars):
        return False
    value = bars[tau].low
    return all(value < bars[tau - i].low for i in range(1, q + 1)) and all(
        value <= bars[tau + i].low for i in range(1, q + 1)
    )


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = max(1, ceil(probability * len(ordered))) - 1
    return ordered[min(position, len(ordered) - 1)]


def robust_slot_baseline(
    bars: Sequence[Bar], current: Bar, days: int, volume_floor: float = 1.0,
) -> tuple[float, float] | None:
    """Return (median, robust sigma) from prior valid sessions only."""

    if current.day is None or current.slot is None:
        return None
    by_day: dict[str | int, float] = {}
    for bar in reversed(bars):
        if not bar.valid_session or not bar.rvol_valid_day or bar.day == current.day or bar.slot != current.slot:
            continue
        if bar.day not in by_day and bar.volume >= 0:
            by_day[bar.day] = bar.volume
        if len(by_day) == days:
            break
    if len(by_day) < days:
        return None
    values = list(by_day.values())
    low = _nearest_rank(values, 0.05)
    high = _nearest_rank(values, 0.95)
    winsorized = [min(high, max(low, value)) for value in values]
    center = median(winsorized)
    mad = median([abs(value - center) for value in winsorized])
    sigma = max(volume_floor, 0.05 * center, 1.4826 * mad)
    return center, sigma


def volume_spike(
    bars: Sequence[Bar], current: Bar, config: StrategyConfig,
) -> bool:
    baseline = robust_slot_baseline(bars, current, config.rvol_days, config.volume_floor)
    if baseline is None:
        return False
    center, sigma = baseline
    return (
        current.volume >= config.rvol_k_v * center
        and current.volume >= center + config.rvol_k_std * sigma
    )


def pinbar_short(
    bar: Bar, atr_previous: float, tick_size: float, zone: Zone,
    require_zone_rejection: bool = True,
    relaxation_pct: float = 0.0,
) -> bool:
    range_value = bar.high - bar.low
    if range_value <= 0 or range_value < max(2 * tick_size, 0.5 * atr_previous):
        return False
    loosen = relaxation_pct / 100.0
    return (
        body(bar) <= (0.30 + 0.30 * loosen) * range_value
        and upper_shadow(bar) >= (0.60 - 0.20 * loosen) * range_value
        and lower_shadow(bar) <= (0.15 + 0.15 * loosen) * range_value
        and bar.close <= bar.low + (0.35 + 0.20 * loosen) * range_value
        and (not require_zone_rejection or bar.close < zone.min_price)
    )


def pinbar_long(
    bar: Bar, atr_previous: float, tick_size: float, zone: Zone,
    require_zone_rejection: bool = True,
    relaxation_pct: float = 0.0,
) -> bool:
    range_value = bar.high - bar.low
    if range_value <= 0 or range_value < max(2 * tick_size, 0.5 * atr_previous):
        return False
    loosen = relaxation_pct / 100.0
    return (
        body(bar) <= (0.30 + 0.30 * loosen) * range_value
        and lower_shadow(bar) >= (0.60 - 0.20 * loosen) * range_value
        and upper_shadow(bar) <= (0.15 + 0.15 * loosen) * range_value
        and bar.close >= bar.low + (0.65 - 0.20 * loosen) * range_value
        and (not require_zone_rejection or bar.close > zone.max_price)
    )


def engulfing_short(
    previous: Bar, current: Bar, zone: Zone,
    require_zone_rejection: bool = True,
    relaxation_pct: float = 0.0,
) -> bool:
    previous_body = body(previous)
    return (
        previous.close > previous.open
        and previous_body > 0
        and previous_body >= 0.60 * (previous.high - previous.low)
        and current.close < current.open
        and current.open >= previous.close
        and current.close <= previous.open
        and body(current) >= (0.80 - 0.20 * relaxation_pct / 100.0) * previous_body
        and current.high <= previous.high
        and (not require_zone_rejection or current.close < zone.min_price)
    )


def engulfing_long(
    previous: Bar, current: Bar, zone: Zone,
    require_zone_rejection: bool = True,
    relaxation_pct: float = 0.0,
) -> bool:
    previous_body = body(previous)
    return (
        previous.close < previous.open
        and previous_body > 0
        and previous_body >= 0.60 * (previous.high - previous.low)
        and current.close > current.open
        and current.open <= previous.close
        and current.close >= previous.open
        and body(current) >= (0.80 - 0.20 * relaxation_pct / 100.0) * previous_body
        and current.low >= previous.low
        and (not require_zone_rejection or current.close > zone.max_price)
    )


def _round_to_tick(price: float, tick_size: float) -> float:
    return round(round(price / tick_size) * tick_size, 10)


class StrategyEngine:
    """Single-instrument deterministic streaming engine."""

    def __init__(self, config: StrategyConfig | None = None, quantity: float = 1.0) -> None:
        self.config = config or StrategyConfig()
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self.quantity = quantity
        self.bars: list[Bar] = []
        self.pivots: list[Pivot] = []
        self._materialized_pivots: set[tuple[int, ZoneType]] = set()
        self._pending_pivots: list[Pivot] = []
        self._swing_stack: list[Pivot] = []
        self._swing_snapshots: list[tuple[Pivot, ...]] = []
        self.zones: dict[int, Zone] = {}
        self.pending: PendingOrder | None = None
        self.position: Position | None = None
        self.trades: list[Trade] = []
        self.events: list[EngineEvent] = []
        self.audit: list[SignalAudit] = []
        self.next_zone_id = 1
        self.emergency_zone_id: int | None = None
        self._atr: list[float | None] = []
        self._ema: list[float | None] = []
        self._rsi: list[float | None] = []
        self._rsi_avg_gain = 0.0
        self._rsi_avg_loss = 0.0
        self._component_seen = {
            side: {name: None for name in (
                "acceleration", "atr_completion", "strong_level",
                "volume_participant", "reverse_impulse",
            )}
            for side in (Side.LONG, Side.SHORT)
        }
        self._component_zones: dict[Side, Zone | None] = {Side.LONG: None, Side.SHORT: None}
        self.reversal_setups = {Side.LONG: ReversalSetup(), Side.SHORT: ReversalSetup()}

    @property
    def status(self) -> PositionStatus:
        if self.position is not None:
            return PositionStatus.IN_POSITION
        if self.pending is not None:
            return PositionStatus.SIGNAL_PENDING
        return PositionStatus.IDLE

    def on_bar(
        self,
        bar: Bar,
        m1_bars: Sequence[Bar] = (),
        emit_signals: bool = True,
    ) -> None:
        """Process one complete bar, including its next-open and M1 phases."""

        expected = len(self.bars)
        if bar.index != expected:
            raise ValueError(f"expected bar index {expected}, got {bar.index}")
        self._session_boundary_phase(bar)
        self._open_phase(bar)
        self.bars.append(bar)
        self._update_indicators(bar)
        self._intrabar_phase(bar, m1_bars)
        self._close_phase(bar, emit_signals=emit_signals)

    def _session_boundary_phase(self, bar: Bar) -> None:
        """Do not carry an intraday position or pending order into a new day."""

        if not self.config.flat_at_day_boundary or not self.bars:
            return
        previous = self.bars[-1]
        if previous.day is None or bar.day is None or previous.day == bar.day:
            return
        if self.position is not None:
            self._close_position(
                previous.index,
                self._exit_market(previous.close, self.position.side, previous),
                "CLOSED_SESSION",
            )
            self.events.append(EngineEvent(previous.index, "SESSION_EXIT", price=previous.close))
        self.pending = None
        self.emergency_zone_id = None
        for setup in self.reversal_setups.values():
            setup.phase = ReversalPhase.IDLE
            setup.started_at = None
            setup.compression_bars = 0
            setup.impulse_extreme = None
            setup.impulse_start_price = None
            setup.impulse_body = 0.0
            setup.compression_range_sum = 0.0
            setup.zone_id = None
            setup.level_state = "ACTIVE_ZONE"
            setup.compression_high = None
            setup.compression_low = None

    def _update_indicators(self, bar: Bar) -> None:
        index = bar.index
        previous_close = self.bars[index - 1].close if index else None
        tr = true_range(bar, previous_close)

        if index + 1 < self.config.atr_period:
            self._atr.append(None)
        elif index + 1 == self.config.atr_period:
            seed_trs = [
                true_range(self.bars[i], self.bars[i - 1].close if i else None)
                for i in range(index + 1)
            ]
            self._atr.append(sum(seed_trs) / self.config.atr_period)
        else:
            previous_atr = self._atr[-1]
            self._atr.append(((self.config.atr_period - 1) * previous_atr + tr) / self.config.atr_period)

        if index + 1 < self.config.ema_period:
            self._ema.append(None)
        elif index + 1 == self.config.ema_period:
            seed = sum(item.close for item in self.bars) / self.config.ema_period
            self._ema.append(seed)
        else:
            previous_ema = self._ema[-1]
            alpha = 2.0 / (self.config.ema_period + 1.0)
            self._ema.append(alpha * bar.close + (1.0 - alpha) * previous_ema)

        period = self.config.rsi_period
        if index < period:
            self._rsi.append(None)
        elif index == period:
            changes = [self.bars[i].close - self.bars[i - 1].close for i in range(1, index + 1)]
            gains = sum(max(change, 0.0) for change in changes) / period
            losses = sum(max(-change, 0.0) for change in changes) / period
            self._rsi_avg_gain = gains
            self._rsi_avg_loss = losses
            self._rsi.append(100.0 if losses == 0 and gains > 0 else 50.0 if losses == 0 else 100.0 - 100.0 / (1.0 + gains / losses))
        else:
            previous = self._rsi[-1]
            change = bar.close - self.bars[-2].close
            previous_gain = self._rsi_avg_gain
            previous_loss = self._rsi_avg_loss
            gain = max(change, 0.0)
            loss = max(-change, 0.0)
            self._rsi_avg_gain = ((period - 1) * previous_gain + gain) / period
            self._rsi_avg_loss = ((period - 1) * previous_loss + loss) / period
            self._rsi.append(100.0 if self._rsi_avg_loss == 0 else 100.0 - 100.0 / (1.0 + self._rsi_avg_gain / self._rsi_avg_loss))

    def _open_phase(self, bar: Bar) -> None:
        if self.emergency_zone_id is not None and self.position is not None:
            self._close_position(bar.index, self._exit_market(bar.open, self.position.side, bar), "CLOSED_EMERGENCY")
            self.events.append(EngineEvent(bar.index, "EMERGENCY_EXIT", price=bar.open))
            self.emergency_zone_id = None
            self.pending = None
            return
        if self.emergency_zone_id is not None:
            self.pending = None
            self.emergency_zone_id = None
        if self.pending is None:
            return
        order = self.pending
        self.pending = None
        atr_previous = self._atr[-1] if self._atr else None
        if order.atr <= 0 or abs(bar.open - self.bars[-1].close) > self.config.max_gap_atr_ratio * order.atr:
            self.events.append(EngineEvent(bar.index, "CANCELLED_GAP", order.side, order.zone_id))
            return
        if self.position is not None:
            return
        entry = self._entry_market(bar.open, order.side, bar, order.atr)
        risk = order.stop_loss - entry if order.side is Side.SHORT else entry - order.stop_loss
        if risk <= 0:
            self.events.append(EngineEvent(bar.index, "CANCELLED_INVALID_STOP", order.side, order.zone_id))
            return
        target = entry - self.config.risk_reward_ratio * risk if order.side is Side.SHORT else entry + self.config.risk_reward_ratio * risk
        self.position = Position(
            order.side, bar.index, entry, order.stop_loss, target, self.quantity,
            order.zone_id, risk,
        )
        self.events.append(EngineEvent(bar.index, "ENTRY", order.side, order.zone_id, entry))

    def _intrabar_phase(self, bar: Bar, m1_bars: Sequence[Bar]) -> None:
        if self.position is None:
            return
        for minute in m1_bars:
            if self.position is None:
                break
            self.process_intrabar(minute, bar.index)

    def process_intrabar(self, minute: Bar, exit_bar: int | None = None) -> None:
        """Apply the canonical synthetic path and worst-case same-segment rule."""

        if self.position is None:
            return
        position = self.position
        exit_bar = minute.index if exit_bar is None else exit_bar
        path = self._synthetic_path(minute)
        stop = position.stop_loss
        target = position.take_profit

        if position.side is Side.SHORT and minute.open >= stop:
            self._close_position(exit_bar, self._exit_stop(position, minute.open, minute), "CLOSED_SL")
            return
        if position.side is Side.LONG and minute.open <= stop:
            self._close_position(exit_bar, self._exit_stop(position, minute.open, minute), "CLOSED_SL")
            return
        if position.side is Side.SHORT and minute.open <= target:
            self._close_position(exit_bar, self._exit_target(position), "CLOSED_TP")
            return
        if position.side is Side.LONG and minute.open >= target:
            self._close_position(exit_bar, self._exit_target(position), "CLOSED_TP")
            return

        if minute.open == minute.close and self._crosses(minute.low, minute.high, stop) and self._crosses(minute.low, minute.high, target):
            self._close_position(exit_bar, self._exit_stop(position, bar=minute), "CLOSED_SL")
            return

        for start, end in zip(path, path[1:]):
            stop_hit = self._crosses(start, end, stop)
            target_hit = self._crosses(start, end, target)
            if not stop_hit and not target_hit:
                continue
            # If both levels are crossed by the same segment, OHLC data cannot
            # reveal their order. The canonical contract takes the stop.
            if stop_hit and target_hit:
                self._close_position(exit_bar, self._exit_stop(position, bar=minute), "CLOSED_SL")
            elif stop_hit:
                self._close_position(exit_bar, self._exit_stop(position, bar=minute), "CLOSED_SL")
            elif target_hit:
                self._close_position(exit_bar, self._exit_target(position), "CLOSED_TP")
            return

    @staticmethod
    def _crosses(start: float, end: float, level: float) -> bool:
        return min(start, end) <= level <= max(start, end)

    @staticmethod
    def _synthetic_path(bar: Bar) -> tuple[float, float, float, float]:
        if bar.open == bar.close:
            # A doji has no directional evidence. The path itself is not used
            # to resolve a two-level collision because the first segment can
            # contain both levels and is handled by Worst-Case below.
            return (bar.open, bar.high, bar.low, bar.close)
        if bar.close > bar.open:
            return (bar.open, bar.low, bar.high, bar.close)
        return (bar.open, bar.high, bar.low, bar.close)

    def _close_phase(self, bar: Bar, emit_signals: bool = True) -> None:
        index = bar.index
        atr_previous = bar.htf_atr if bar.htf_atr is not None else (self._atr[index - 1] if index > 0 else None)
        self._register_pivot(index)
        if atr_previous is None:
            self.audit.append(self._build_audit(bar, None, "BLOCKED", "ATR_WARMUP"))
            return

        self._update_zones(bar, atr_previous)
        self._create_zones_from_new_pivots(index, atr_previous)
        self._manage_position_by_volume(bar, atr_previous)
        self._update_reversal_setups(bar, atr_previous)
        if self.position is not None and self.emergency_zone_id is not None:
            self.audit.append(self._build_audit(bar, atr_previous, "BLOCKED", "EMERGENCY_EXIT"))
            return
        if emit_signals:
            self._queue_signal(bar, atr_previous)
            for side in (Side.LONG, Side.SHORT):
                if self.reversal_setups[side].phase is ReversalPhase.RE_EXPANSION:
                    self._reset_reversal_setup(side)
        else:
            self.audit.append(self._build_audit(bar, atr_previous, "WARMUP", "SIGNALS_DISABLED"))

    def _build_audit(
        self,
        bar: Bar,
        atr_previous: float | None,
        decision: str,
        block_reason: str | None,
        short_zone: Zone | None = None,
        long_zone: Zone | None = None,
        short_exhaustion: bool = False,
        long_exhaustion: bool = False,
        volume_signal: bool = False,
        acceleration_signal: bool = False,
        short_shape: bool = False,
        long_shape: bool = False,
        short_pattern: bool = False,
        long_pattern: bool = False,
        soft_score_short: int = 0,
        soft_score_long: int = 0,
    ) -> SignalAudit:
        ema_current = self._ema[bar.index] if bar.index < len(self._ema) else None
        return SignalAudit(
            bar.index,
            atr_previous,
            ema_current,
            short_zone.zone_id if short_zone else long_zone.zone_id if long_zone else None,
            short_zone.zone_id if short_zone else None,
            long_zone.zone_id if long_zone else None,
            ema_current is not None and bar.close < ema_current,
            ema_current is not None and bar.close > ema_current,
            self._micro_context(bar.index, Side.SHORT),
            self._micro_context(bar.index, Side.LONG),
            short_exhaustion,
            long_exhaustion,
            volume_signal,
            acceleration_signal,
            short_shape,
            long_shape,
            short_pattern,
            long_pattern,
            soft_score_short,
            soft_score_long,
            decision,
            block_reason,
            self.reversal_setups[Side.LONG].phase.value,
            self.reversal_setups[Side.SHORT].phase.value,
            self.reversal_setups[Side.LONG].level_state,
            self.reversal_setups[Side.SHORT].level_state,
            self._rsi[bar.index] if bar.index < len(self._rsi) else None,
        )

    def _register_pivot(self, current_index: int) -> None:
        tau = current_index - self.config.pivot_q
        if tau >= 0:
            if is_pivot_high(self.bars, tau, self.config.pivot_q):
                self._add_confirmed_pivot(Pivot(tau, current_index, self.bars[tau].high, ZoneType.RESISTANCE))
            if is_pivot_low(self.bars, tau, self.config.pivot_q):
                self._add_confirmed_pivot(Pivot(tau, current_index, self.bars[tau].low, ZoneType.SUPPORT))
        self._swing_snapshots.append(tuple(self._swing_stack))

    def _add_confirmed_pivot(self, pivot: Pivot) -> None:
        self.pivots.append(pivot)
        self._pending_pivots.append(pivot)
        if not self._swing_stack or self._swing_stack[-1].kind is not pivot.kind:
            self._swing_stack.append(pivot)
            return
        more_extreme = (
            pivot.price > self._swing_stack[-1].price
            if pivot.kind is ZoneType.RESISTANCE
            else pivot.price < self._swing_stack[-1].price
        )
        if more_extreme:
            self._swing_stack[-1] = pivot

    def _update_zones(self, bar: Bar, atr_previous: float) -> None:
        loosen = self.config.relaxation_pct / 100.0
        for zone in list(self.zones.values()):
            if zone.status is not ZoneStatus.ACTIVE:
                continue
            breakout = self.config.price_discovery_enabled and (
                zone.zone_type is ZoneType.RESISTANCE
                and bar.close > zone.max_price + self.config.true_breakout_beta * (1.0 - loosen) * atr_previous
            ) or (
                zone.zone_type is ZoneType.SUPPORT
                and bar.close < zone.min_price - self.config.true_breakout_beta * (1.0 - loosen) * atr_previous
            )
            if breakout:
                zone.status = ZoneStatus.INVALIDATED_BROKEN
                if self.config.emergency_exit and self.position is not None and self.position.zone_id == zone.zone_id:
                    self.emergency_zone_id = zone.zone_id
                if self.pending is not None and self.pending.zone_id == zone.zone_id:
                    self.pending = None
                continue
            zone.age += 1
            overlap = bar.high >= zone.min_price and bar.low <= zone.max_price
            touch = overlap and not zone.previous_overlap
            zone.previous_overlap = overlap
            if touch:
                zone.touches += 1
                zone.last_touch_at = bar.index
            if zone.touches > self.config.max_touches:
                zone.status = ZoneStatus.EXPIRED_TOUCHES
            elif zone.age > self.config.max_age_bars or (
                zone.last_touch_at is not None
                and bar.index - zone.last_touch_at > self.config.zone_idle_max_bars
            ):
                zone.status = ZoneStatus.EXPIRED_AGE

    def _create_zones_from_new_pivots(self, current_index: int, atr_previous: float) -> None:
        loosen = self.config.relaxation_pct / 100.0
        pending = self._pending_pivots
        self._pending_pivots = []
        for pivot in pending:
            if pivot.confirmed_at > current_index:
                self._pending_pivots.append(pivot)
                continue
            if (pivot.index, pivot.kind) in self._materialized_pivots:
                continue
            candidates = [
                zone for zone in self.zones.values()
                if zone.status is ZoneStatus.ACTIVE
                and zone.zone_type is pivot.kind
                and abs(pivot.price - zone.center) <= self.config.zone_cluster_atr_ratio * (1.0 + loosen) * atr_previous
            ]
            if candidates:
                selected = min(candidates, key=lambda zone: (abs(pivot.price - zone.center), zone.zone_id))
                selected.hits += 1
                self._materialized_pivots.add((pivot.index, pivot.kind))
                continue
            width = max(self.config.tick_size, self.config.zone_width_atr_ratio * (1.0 + loosen) * atr_previous)
            zone = Zone(
                zone_id=self.next_zone_id,
                zone_type=pivot.kind,
                center=pivot.price,
                width=width,
                created_at=current_index,
                eligible_from=current_index + 1,
                last_touch_at=current_index,
            )
            self.zones[zone.zone_id] = zone
            self.next_zone_id += 1
            self._materialized_pivots.add((pivot.index, pivot.kind))

    def _reset_reversal_setup(self, side: Side) -> None:
        self.reversal_setups[side] = ReversalSetup()

    def _setup_zone(self, bar: Bar, side: Side) -> Zone | None:
        wanted = ZoneType.SUPPORT if side is Side.LONG else ZoneType.RESISTANCE
        candidates = []
        for zone in self.zones.values():
            if zone.status is not ZoneStatus.ACTIVE or zone.zone_type is not wanted:
                continue
            if bar.high >= zone.min_price and bar.low <= zone.max_price:
                distance = abs(bar.low - zone.center) if side is Side.LONG else abs(bar.high - zone.center)
                candidates.append((distance, -zone.hits, zone.zone_id, zone))
        return min(candidates, default=(0, 0, 0, None))[3]

    def _setup_zone_by_id(self, side: Side) -> Zone | None:
        setup = self.reversal_setups[side]
        zone = self.zones.get(setup.zone_id) if setup.zone_id is not None else None
        wanted = ZoneType.SUPPORT if side is Side.LONG else ZoneType.RESISTANCE
        return zone if zone is not None and zone.status is ZoneStatus.ACTIVE and zone.zone_type is wanted else None

    def _directional_art(self, bar: Bar, side: Side) -> float | None:
        return bar.htf_art_long if side is Side.LONG else bar.htf_art_short

    def _uncertain_level_rsi_ok(self, bar: Bar, side: Side) -> bool:
        setup = self.reversal_setups[side]
        if setup.level_state != "STALE_ATR" or not self.config.uncertain_rsi_enabled:
            return True
        if bar.index < 1 or self._rsi[bar.index] is None or self._rsi[bar.index - 1] is None:
            return False
        previous = self._rsi[bar.index - 1]
        current = self._rsi[bar.index]
        if side is Side.LONG:
            return previous <= self.config.rsi_oversold and current > previous
        return previous >= self.config.rsi_overbought and current < previous

    def _stale_level_fallback(self, bar: Bar, side: Side, art: float, atr_previous: float) -> bool:
        if not self.config.stale_level_enabled or atr_previous <= 0:
            return False
        swings = self._alternating_pivots(bar.index)
        start_kind = ZoneType.RESISTANCE if side is Side.LONG else ZoneType.SUPPORT
        starts = [pivot for pivot in swings if pivot.kind is start_kind]
        if not starts:
            return False
        start = starts[-1].price
        extreme = bar.low if side is Side.LONG else bar.high
        excursion = start - extreme if side is Side.LONG else extreme - start
        ratio = excursion / atr_previous
        return (
            self.config.stale_level_atr_min <= ratio <= self.config.stale_level_atr_max
            and (not self.config.stale_level_require_art or excursion >= self.config.impulse_art_eta * art)
        )

    def _fallback_zone(self, bar: Bar, side: Side, atr_previous: float) -> Zone | None:
        setup = self.reversal_setups[side]
        if setup.level_state != "STALE_ATR" or setup.impulse_extreme is None:
            return None
        zone_type = ZoneType.SUPPORT if side is Side.LONG else ZoneType.RESISTANCE
        return Zone(
            -1 if side is Side.LONG else -2,
            zone_type,
            setup.impulse_extreme,
            max(self.config.tick_size, self.config.zone_width_atr_ratio * atr_previous),
            setup.started_at or bar.index,
            bar.index,
        )

    def _update_reversal_setups(self, bar: Bar, atr_previous: float) -> None:
        """Advance the causal impulse/compression/re-expansion setup FSM."""

        if not self.config.reversal_setup_enabled or len(self.bars) < 2:
            return
        previous = self.bars[-2]
        range_value = bar.high - bar.low
        if range_value <= 0 or atr_previous <= 0:
            return

        for side in (Side.LONG, Side.SHORT):
            setup = self.reversal_setups[side]
            zone = self._setup_zone(bar, side)
            art = self._directional_art(bar, side)
            if art is None or art <= 0:
                continue

            adverse = bar.close < previous.close if side is Side.LONG else bar.close > previous.close
            favorable = bar.close > previous.close if side is Side.LONG else bar.close < previous.close
            if setup.phase is ReversalPhase.IDLE:
                if not adverse or (zone is None and not self._stale_level_fallback(bar, side, art, atr_previous)):
                    continue
                swings = self._alternating_pivots(bar.index)
                start_kind = ZoneType.RESISTANCE if side is Side.LONG else ZoneType.SUPPORT
                starting_swings = [pivot for pivot in swings if pivot.kind is start_kind]
                impulse_start = starting_swings[-1].price if starting_swings else previous.close
                setup.started_at = bar.index
                setup.impulse_start_price = impulse_start
                setup.impulse_extreme = bar.low if side is Side.LONG else bar.high
                setup.impulse_body = body(bar)
                setup.zone_id = zone.zone_id if zone is not None else None
                distance = (
                    setup.impulse_start_price - setup.impulse_extreme
                    if side is Side.LONG
                    else setup.impulse_extreme - setup.impulse_start_price
                )
                if distance >= self.config.impulse_art_eta * art:
                    setup.phase = ReversalPhase.IMPULSE_REACHED
                    setup.level_state = "ACTIVE_ZONE" if zone is not None else "STALE_ATR"
                else:
                    self._reset_reversal_setup(side)
                continue

            if setup.phase is ReversalPhase.IMPULSE_REACHED:
                small_range = range_value <= self.config.compression_range_ratio * atr_previous
                small_body = body(bar) <= self.config.compression_body_ratio * max(setup.impulse_body, atr_previous)
                if small_range and small_body and not adverse:
                    setup.phase = ReversalPhase.COMPRESSION
                    setup.compression_bars = 1
                    setup.compression_high = bar.high
                    setup.compression_low = bar.low
                    setup.compression_range_sum = range_value
                elif adverse:
                    if side is Side.LONG:
                        setup.impulse_extreme = min(setup.impulse_extreme or bar.low, bar.low)
                    else:
                        setup.impulse_extreme = max(setup.impulse_extreme or bar.high, bar.high)
                else:
                    self._reset_reversal_setup(side)
                continue

            if setup.phase is ReversalPhase.COMPRESSION:
                prior_high = setup.compression_high or bar.high
                prior_low = setup.compression_low or bar.low
                compression_range = setup.compression_range_sum / max(setup.compression_bars, 1)
                expansion = range_value >= self.config.reexpansion_ratio * compression_range
                broke_compression = bar.close > prior_high if side is Side.LONG else bar.close < prior_low
                if setup.compression_bars >= self.config.compression_min_bars and favorable and expansion and broke_compression:
                    setup.phase = ReversalPhase.RE_EXPANSION
                    continue
                if setup.compression_bars >= self.config.compression_max_bars:
                    self._reset_reversal_setup(side)
                    continue
                if small_range := range_value <= self.config.compression_range_ratio * atr_previous:
                    setup.compression_bars += 1
                    setup.compression_range_sum += range_value
                    setup.compression_high = max(setup.compression_high or bar.high, bar.high)
                    setup.compression_low = min(setup.compression_low or bar.low, bar.low)
                else:
                    self._reset_reversal_setup(side)
                continue

            if setup.phase is ReversalPhase.RE_EXPANSION:
                # Keep the phase through the next close so _queue_signal can
                # evaluate the re-expansion as an entry gate.
                continue

    def _select_zone(self, bar: Bar, side: Side) -> Zone | None:
        wanted = ZoneType.RESISTANCE if side is Side.SHORT else ZoneType.SUPPORT
        loosen = self.config.relaxation_pct / 100.0
        candidates = []
        for zone in self.zones.values():
            if zone.status is not ZoneStatus.ACTIVE or zone.zone_type is not wanted or zone.eligible_from > bar.index:
                continue
            overlap = bar.high >= zone.min_price and bar.low <= zone.max_price
            if self.config.zone_signal_mode == "TOUCH":
                eligible = overlap
            elif self.config.zone_signal_mode == "RELAXED_REJECTION":
                eligible = overlap
            elif self.config.zone_signal_mode == "NEAR":
                near_distance = self.config.near_zone_atr_ratio * (1.0 + loosen) * (self._atr[bar.index - 1] or 0.0)
                eligible = (
                    bar.high >= zone.min_price - near_distance
                    and bar.low <= zone.max_price + near_distance
                )
            else:
                rejected = bar.close < zone.min_price if side is Side.SHORT else bar.close > zone.max_price
                eligible = overlap and rejected
            if eligible:
                distance = abs(bar.high - zone.center) if side is Side.SHORT else abs(bar.low - zone.center)
                candidates.append((distance, -zone.hits, zone.zone_id, zone))
        return min(candidates, default=(0, 0, 0, None))[3]

    def _queue_signal(self, bar: Bar, atr_previous: float) -> None:
        if self.position is not None or self.pending is not None:
            self.audit.append(self._build_audit(bar, atr_previous, "BLOCKED", "POSITION_OR_ORDER_EXISTS"))
            return
        ema_current = self._ema[bar.index]
        if ema_current is None:
            self.audit.append(self._build_audit(bar, atr_previous, "BLOCKED", "INDICATOR_WARMUP"))
            return
        short_zone = (
            self._select_zone(bar, Side.SHORT)
            or self._setup_zone_by_id(Side.SHORT)
            or self._fallback_zone(bar, Side.SHORT, atr_previous)
        )
        long_zone = (
            self._select_zone(bar, Side.LONG)
            or self._setup_zone_by_id(Side.LONG)
            or self._fallback_zone(bar, Side.LONG, atr_previous)
        )
        if short_zone is not None:
            self._component_zones[Side.SHORT] = short_zone
        if long_zone is not None:
            self._component_zones[Side.LONG] = long_zone
        short_reversal = (
            not self.config.reversal_setup_enabled
            or self.reversal_setups[Side.SHORT].phase is ReversalPhase.RE_EXPANSION
        )
        long_reversal = (
            not self.config.reversal_setup_enabled
            or self.reversal_setups[Side.LONG].phase is ReversalPhase.RE_EXPANSION
        )
        short_reversal = short_reversal and self._uncertain_level_rsi_ok(bar, Side.SHORT)
        long_reversal = long_reversal and self._uncertain_level_rsi_ok(bar, Side.LONG)
        short_exhaustion = self._exhausted(bar.index, Side.SHORT) or (
            self.config.reversal_setup_enabled and short_reversal
        )
        long_exhaustion = self._exhausted(bar.index, Side.LONG) or (
            self.config.reversal_setup_enabled and long_reversal
        )
        micro_short = self._micro_context(bar.index, Side.SHORT)
        micro_long = self._micro_context(bar.index, Side.LONG)
        macro_short = bar.close < ema_current
        macro_long = bar.close > ema_current
        short = short_zone is not None and macro_short and micro_short and short_exhaustion and short_reversal
        long = long_zone is not None and macro_long and micro_long and long_exhaustion and long_reversal
        volume_current, _ = self._volume_components(bar)
        acceleration_current, _ = self._acceleration_components(bar)
        short_shape_current = bool(short_zone and self._short_candle_shape(bar, short_zone, atr_previous))
        long_shape_current = bool(long_zone and self._long_candle_shape(bar, long_zone, atr_previous))
        self._remember_component("acceleration", acceleration_current, bar.index)
        self._remember_component("volume_participant", volume_current, bar.index)
        self._remember_component("atr_completion", short_exhaustion, bar.index, Side.SHORT)
        self._remember_component("atr_completion", long_exhaustion, bar.index, Side.LONG)
        self._remember_component("reverse_impulse", short_shape_current, bar.index, Side.SHORT)
        self._remember_component("reverse_impulse", long_shape_current, bar.index, Side.LONG)
        if short_zone is not None:
            self._remember_component("strong_level", True, bar.index, Side.SHORT)
        if long_zone is not None:
            self._remember_component("strong_level", True, bar.index, Side.LONG)
        short_zone = self._recent_zone(Side.SHORT, bar.index) or short_zone
        long_zone = self._recent_zone(Side.LONG, bar.index) or long_zone
        volume_signal = self._recent_component("volume_participant", bar.index)
        acceleration_signal = self._recent_component("acceleration", bar.index)
        short_exhaustion = self._recent_component("atr_completion", bar.index, Side.SHORT)
        long_exhaustion = self._recent_component("atr_completion", bar.index, Side.LONG)
        short_shape = self._recent_component("reverse_impulse", bar.index, Side.SHORT)
        long_shape = self._recent_component("reverse_impulse", bar.index, Side.LONG)
        short = short_zone is not None and macro_short and micro_short and short_exhaustion and short_reversal
        long = long_zone is not None and macro_long and micro_long and long_exhaustion and long_reversal
        soft_short = (macro_short, micro_short, short_exhaustion, acceleration_signal, volume_signal)
        soft_long = (macro_long, micro_long, long_exhaustion, acceleration_signal, volume_signal)
        score_short = sum(soft_short if self.config.volume_entry_filter else soft_short[:-1])
        score_long = sum(soft_long if self.config.volume_entry_filter else soft_long[:-1])
        if self.config.signal_mode == "SCORE":
            flow_confirmed = (
                not self.config.volume_entry_filter
                or not self.config.score_requires_flow
                or (acceleration_signal and volume_signal)
            )
            score_threshold = self.config.min_soft_score
            if not self.config.volume_entry_filter:
                score_threshold = min(score_threshold, 4)
            short = short_zone is not None and short_shape and score_short >= score_threshold and flow_confirmed and short_reversal
            long = long_zone is not None and long_shape and score_long >= score_threshold and flow_confirmed and long_reversal
        if short and long:
            self.events.append(EngineEvent(bar.index, "AMBIGUOUS_SIGNAL"))
            self.audit.append(self._build_audit(
                bar, atr_previous, "BLOCKED", "AMBIGUOUS_DIRECTION", short_zone, long_zone,
                short_exhaustion, long_exhaustion, volume_signal, acceleration_signal, short_shape, long_shape,
                score_short, score_long,
            ))
            return
        short_pattern = bool(short_zone and short and self._short_pattern(bar, short_zone, atr_previous))
        long_pattern = bool(long_zone and long and self._long_pattern(bar, long_zone, atr_previous))
        short_entry = short and (short_pattern if self.config.signal_mode == "AND" else short_shape)
        long_entry = long and (long_pattern if self.config.signal_mode == "AND" else long_shape)
        if short_entry:
            stop = max(bar.high, self.bars[-2].high if len(self.bars) > 1 else bar.high) + max(self.config.tick_size, short_zone.width)
            self.pending = PendingOrder(Side.SHORT, bar.index, short_zone.zone_id, stop, atr_previous)
            self.events.append(EngineEvent(bar.index, "SIGNAL", Side.SHORT, short_zone.zone_id))
            self.audit.append(self._build_audit(bar, atr_previous, "SIGNAL_SHORT", None, short_zone, long_zone, short_exhaustion, long_exhaustion, volume_signal, acceleration_signal, short_shape, long_shape, short_pattern, long_pattern, score_short, score_long))
        elif long_entry:
            stop = min(bar.low, self.bars[-2].low if len(self.bars) > 1 else bar.low) - max(self.config.tick_size, long_zone.width)
            self.pending = PendingOrder(Side.LONG, bar.index, long_zone.zone_id, stop, atr_previous)
            self.events.append(EngineEvent(bar.index, "SIGNAL", Side.LONG, long_zone.zone_id))
            self.audit.append(self._build_audit(bar, atr_previous, "SIGNAL_LONG", None, short_zone, long_zone, short_exhaustion, long_exhaustion, volume_signal, acceleration_signal, short_shape, long_shape, short_pattern, long_pattern, score_short, score_long))
        else:
            if short_zone is None and long_zone is None:
                reason = "NO_TARGET_ZONE"
            elif not ((macro_short and micro_short) or (macro_long and micro_long)):
                reason = "MARKET_CONTEXT"
            elif not (short_reversal or long_reversal):
                reason = "ART_NOT_REEXPANDED"
            elif not ((short and short_exhaustion) or (long and long_exhaustion)):
                reason = "EXHAUSTION"
            elif not acceleration_signal:
                reason = "ACCELERATION"
            elif not volume_signal:
                reason = "VOLUME"
            elif not (short_shape or long_shape):
                reason = "CANDLE_PATTERN"
            else:
                reason = "CANDLE_CONFIRMATION"
            self.audit.append(self._build_audit(bar, atr_previous, "BLOCKED", reason, short_zone, long_zone, short_exhaustion, long_exhaustion, volume_signal, acceleration_signal, short_shape, long_shape, short_pattern, long_pattern, score_short, score_long))

    def _volume_components(self, bar: Bar) -> tuple[bool, bool]:
        current = volume_spike(self.bars[:-1], bar, self.config)
        previous = False
        if len(self.bars) > 1:
            previous = volume_spike(self.bars[:-2], self.bars[-2], self.config)
        return current, previous

    def _acceleration_components(self, bar: Bar) -> tuple[bool, bool]:
        current = self._body_acceleration(self.bars[:-1], bar)
        previous = False
        if len(self.bars) > 1:
            previous = self._body_acceleration(self.bars[:-2], self.bars[-2])
        return current, previous

    def _short_pattern(self, bar: Bar, zone: Zone, atr_previous: float) -> bool:
        one = (
            self._recent_component("reverse_impulse", bar.index, Side.SHORT)
            and self._recent_component("acceleration", bar.index)
            and (not self.config.volume_entry_filter or self._recent_component("volume_participant", bar.index))
        )
        two = False
        if len(self.bars) > 1:
            previous = self.bars[-2]
            two = (
                previous.high >= zone.min_price and previous.low <= zone.max_price
                and engulfing_short(
                    previous, bar, zone,
                    self.config.zone_signal_mode == "STRICT",
                )
                and self._body_acceleration(self.bars[:-2], previous)
                and (not self.config.volume_entry_filter or self._recent_component("volume_participant", bar.index))
            )
        return one or two

    def _long_pattern(self, bar: Bar, zone: Zone, atr_previous: float) -> bool:
        one = (
            self._recent_component("reverse_impulse", bar.index, Side.LONG)
            and self._recent_component("acceleration", bar.index)
            and (not self.config.volume_entry_filter or self._recent_component("volume_participant", bar.index))
        )
        two = False
        if len(self.bars) > 1:
            previous = self.bars[-2]
            two = (
                previous.high >= zone.min_price and previous.low <= zone.max_price
                and engulfing_long(
                    previous, bar, zone,
                    self.config.zone_signal_mode == "STRICT",
                )
                and self._body_acceleration(self.bars[:-2], previous)
                and (not self.config.volume_entry_filter or self._recent_component("volume_participant", bar.index))
            )
        return one or two

    def _component_window(self, component: str) -> int:
        return getattr(self.config, f"component_window_{component}")

    def _remember_component(self, component: str, active: bool, index: int, side: Side | None = None) -> None:
        sides = (side,) if side is not None else (Side.LONG, Side.SHORT)
        if active:
            for current_side in sides:
                self._component_seen[current_side][component] = index

    def _recent_component(self, component: str, index: int, side: Side | None = None) -> bool:
        sides = (side,) if side is not None else (Side.LONG, Side.SHORT)
        return any(
            (seen := self._component_seen[current_side][component]) is not None
            and index - seen < self._component_window(component)
            for current_side in sides
        )

    def _recent_zone(self, side: Side, index: int) -> Zone | None:
        if not self._recent_component("strong_level", index, side):
            return None
        zone = self._component_zones[side]
        return zone if zone is not None and zone.status is ZoneStatus.ACTIVE else None

    def _manage_position_by_volume(self, bar: Bar, atr_previous: float) -> None:
        """Use a closed-bar volume shock to protect or extend an existing trade."""

        if not self.config.post_entry_volume_management or self.position is None:
            return
        if not volume_spike(self.bars[:-1], bar, self.config) or len(self.bars) < 2:
            return
        position = self.position
        favorable = (
            bar.close > self.bars[-2].close if position.side is Side.LONG
            else bar.close < self.bars[-2].close
        )
        buffer = self.config.volume_stop_buffer_atr_ratio * atr_previous
        if position.side is Side.LONG:
            if favorable:
                position.stop_loss = max(position.stop_loss, position.entry_price, bar.low - buffer)
                position.take_profit += position.initial_risk * self.config.volume_target_extension_r
            else:
                position.stop_loss = max(position.stop_loss, bar.close - buffer)
        else:
            if favorable:
                position.stop_loss = min(position.stop_loss, position.entry_price, bar.high + buffer)
                position.take_profit -= position.initial_risk * self.config.volume_target_extension_r
            else:
                position.stop_loss = min(position.stop_loss, bar.close + buffer)
        self.events.append(EngineEvent(bar.index, "VOLUME_MANAGEMENT", position.side, position.zone_id, bar.close))

    def _short_candle_shape(self, bar: Bar, zone: Zone, atr_previous: float) -> bool:
        reject = self.config.zone_signal_mode not in {"TOUCH", "RELAXED_REJECTION", "NEAR"}
        relaxed_atr = atr_previous * (1.0 - self.config.relaxation_pct / 100.0)
        return pinbar_short(bar, relaxed_atr, self.config.tick_size, zone, reject, self.config.relaxation_pct) or (
            len(self.bars) > 1 and engulfing_short(self.bars[-2], bar, zone, reject, self.config.relaxation_pct)
        )

    def _long_candle_shape(self, bar: Bar, zone: Zone, atr_previous: float) -> bool:
        reject = self.config.zone_signal_mode not in {"TOUCH", "RELAXED_REJECTION", "NEAR"}
        relaxed_atr = atr_previous * (1.0 - self.config.relaxation_pct / 100.0)
        return pinbar_long(bar, relaxed_atr, self.config.tick_size, zone, reject, self.config.relaxation_pct) or (
            len(self.bars) > 1 and engulfing_long(self.bars[-2], bar, zone, reject, self.config.relaxation_pct)
        )

    def _body_acceleration(self, history: Sequence[Bar], current: Bar) -> bool:
        if len(history) < self.config.body_lookback:
            return False
        baseline = sum(body(item) for item in history[-self.config.body_lookback:]) / self.config.body_lookback
        return baseline > 0 and body(current) >= self.config.body_anomaly_ratio * (1.0 - self.config.relaxation_pct / 100.0) * baseline

    def _exhausted(self, index: int, side: Side) -> bool:
        available = self._alternating_pivots(index)
        historical = self._alternating_pivots(index - 1)
        if side is Side.SHORT:
            starts = [pivot for pivot in available if pivot.kind is ZoneType.SUPPORT]
            current_start = starts[-1] if starts else None
        else:
            starts = [pivot for pivot in available if pivot.kind is ZoneType.RESISTANCE]
            current_start = starts[-1] if starts else None
        completed = [abs(historical[i].price - historical[i - 1].price) for i in range(1, len(historical))]
        if current_start is None or len(completed) < self.config.n_waves:
            return False
        distance = self.bars[index].high - current_start.price if side is Side.SHORT else current_start.price - self.bars[index].low
        if self.config.exhaustion_mode == "CURRENT_ATR":
            atr_value = self._atr[index - 1] if index > 0 else None
            threshold = atr_value or 0.0
        else:
            htf_art = (
                self.bars[index].htf_art_long
                if side is Side.LONG
                else self.bars[index].htf_art_short
            )
            if htf_art is None:
                htf_art = self.bars[index].htf_art
            if htf_art is not None:
                threshold = htf_art
            else:
                mean_wave = sum(completed[-self.config.n_waves:]) / self.config.n_waves
                threshold = mean_wave
        return self._micro_context(index, side) and distance >= self.config.exhaustion_eta * (1.0 - self.config.relaxation_pct / 100.0) * threshold

    def _micro_context(self, index: int, side: Side) -> bool:
        if index < 1 or index >= len(self.bars):
            return False
        pivots = self._alternating_pivots(index)
        if not pivots:
            return False
        if side is Side.SHORT:
            return pivots[-1].kind is ZoneType.SUPPORT and self.bars[index].close > self.bars[index - 1].close
        return pivots[-1].kind is ZoneType.RESISTANCE and self.bars[index].close < self.bars[index - 1].close

    def _alternating_pivots(self, index: int) -> list[Pivot]:
        """Build the causal swing stack, resolving consecutive equal types.

        If two highs arrive before a low, only the more extreme high remains in
        the active swing stack. This is an online update made at confirmation
        time, not a retrospective ZigZag calculation.
        """

        if 0 <= index < len(self._swing_snapshots):
            return list(self._swing_snapshots[index])
        # Keep direct state construction useful for unit tests and diagnostics.
        stack: list[Pivot] = []
        for pivot in self.pivots:
            if pivot.confirmed_at > index:
                continue
            if not stack or stack[-1].kind is not pivot.kind:
                stack.append(pivot)
                continue
            more_extreme = (
                pivot.price > stack[-1].price
                if pivot.kind is ZoneType.RESISTANCE
                else pivot.price < stack[-1].price
            )
            if more_extreme:
                stack[-1] = pivot
        return stack

    def _costs(self, bar: Bar | None, atr_value: float | None = None) -> tuple[float, float]:
        spread = self.config.fixed_spread
        slippage = self.config.fixed_slippage
        if self.config.spread_model == "DYNAMIC_FROM_DATA":
            if bar is None or bar.spread is None:
                raise ValueError("dynamic spread requires spread on execution bar")
            spread = bar.spread
        if self.config.slippage_model == "DYNAMIC_FROM_DATA":
            if bar is None or bar.slippage is None:
                raise ValueError("dynamic slippage requires slippage on execution bar")
            slippage = bar.slippage
        if self.config.slippage_model == "VOLATILITY_SCALED" and self.config.slippage_atr_ratio > 0 and atr_value is not None:
            slippage += self.config.slippage_atr_ratio * atr_value
        return spread, slippage

    def _entry_market(self, open_price: float, side: Side, bar: Bar | None = None, atr_value: float | None = None) -> float:
        spread, slippage = self._costs(bar, atr_value)
        half = spread / 2.0
        adjustment = half + slippage
        return _round_to_tick(open_price + adjustment if side is Side.LONG else open_price - adjustment, self.config.tick_size)

    def _exit_market(self, open_price: float, side: Side, bar: Bar | None = None, atr_value: float | None = None) -> float:
        spread, slippage = self._costs(bar, atr_value)
        half = spread / 2.0
        adjustment = half + slippage
        return _round_to_tick(open_price - adjustment if side is Side.LONG else open_price + adjustment, self.config.tick_size)

    def _exit_stop(self, position: Position, market_open: float | None = None, bar: Bar | None = None) -> float:
        spread, slippage = self._costs(bar)
        adjustment = spread / 2.0 + slippage
        if position.side is Side.LONG:
            base = min(position.stop_loss, market_open) if market_open is not None else position.stop_loss
            raw = base - adjustment
        else:
            base = max(position.stop_loss, market_open) if market_open is not None else position.stop_loss
            raw = base + adjustment
        return _round_to_tick(raw, self.config.tick_size)

    def _exit_target(self, position: Position) -> float:
        return _round_to_tick(position.take_profit, self.config.tick_size)

    def _close_position(self, exit_bar: int, exit_price: float, reason: str) -> None:
        if self.position is None:
            return
        position = self.position
        gross = (
            (exit_price - position.entry_price) * position.quantity
            if position.side is Side.LONG
            else (position.entry_price - exit_price) * position.quantity
        )
        fees = (position.entry_price + exit_price) * position.quantity * self.config.commission_rate
        self.trades.append(Trade(
            position.side, position.entry_bar, exit_bar, position.entry_price, exit_price,
            position.quantity, reason, gross - fees,
        ))
        self.events.append(EngineEvent(exit_bar, reason, position.side, position.zone_id, exit_price))
        self.position = None


def validate_zone(zone: Zone, tick_size: float, tolerance: float = 1e-9) -> None:
    if zone.width <= 0 or zone.touches < 0 or zone.age < 0:
        raise ValueError("invalid zone state")
    if abs(zone.min_price - (zone.center - zone.width)) > tolerance:
        raise ValueError("zone min_price invariant violated")
    if abs(zone.max_price - (zone.center + zone.width)) > tolerance:
        raise ValueError("zone max_price invariant violated")
    if zone.eligible_from != zone.created_at + 1:
        raise ValueError("zone eligibility invariant violated")
    if tick_size <= 0:
        raise ValueError("tick_size must be positive")
