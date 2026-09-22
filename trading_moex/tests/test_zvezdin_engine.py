from app.zvezdin_engine import (
    Bar,
    ReversalPhase,
    Side,
    StrategyConfig,
    StrategyEngine,
    Zone,
    ZoneStatus,
    ZoneType,
    atr_wilder,
    is_pivot_high,
    robust_slot_baseline,
    validate_zone,
    volume_spike,
)
from app.zvezdin_backtest import (
    assert_causal_prefix,
    assess_robustness,
    bars_from_dataframe,
    run_dataframe_backtest,
    mark_to_market_pnl,
    m1_bars_by_parent,
    build_run_manifest,
    dataframe_fingerprint,
    summarize_audit,
    summarize_sensitivity,
    summarize_trades,
    sensitivity_grid,
    stress_costs,
    walk_forward_backtest,
    walk_forward_efficiency,
    walk_forward_optimize,
    _closed_htf_wave_ranges,
    _closed_htf_directional_wave_ranges,
    _closed_htf_levels,
)
from app.zvezdin_contract import load_default_config, strategy_config_for_ticker, strategy_config_from_contract
from app.zvezdin_calendar import SessionCalendar, load_calendar
import pandas as pd
import pytest


def bar(index, open_, high, low, close, volume=1000, day=None, slot=None):
    return Bar(index, open_, high, low, close, volume, day, slot)


def test_flat_top_pivot_is_confirmed_only_after_right_shoulder():
    bars = [
        bar(0, 99, 100, 98, 99),
        bar(1, 104, 105, 103, 104),
        bar(2, 109, 110, 108, 109),
        bar(3, 109, 110, 108, 109),
        bar(4, 107, 108, 106, 107),
        bar(5, 106, 107, 105, 106),
    ]
    assert is_pivot_high(bars, 2, 2) is True
    assert is_pivot_high(bars, 3, 2) is False


def _htf_fixture(bucket_highs, bucket_lows):
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=len(bucket_highs) * 16, freq="15min", tz="UTC")
    rows = []
    for bucket, (high, low) in enumerate(zip(bucket_highs, bucket_lows)):
        for _ in range(16):
            rows.append({"open": low, "high": high, "low": low, "close": high, "volume": 1.0})
    return pd.DataFrame(rows, index=timestamps)


def test_wave_atr_uses_last_completed_four_hour_fractal_wave():
    frame = _htf_fixture([100, 110, 105, 120, 108], [90, 100, 95, 105, 100])

    art = _closed_htf_wave_ranges(frame, pivot_q=1)

    # At 12:00, the 04:00-08:00 high and 08:00-12:00 low are not both
    # confirmed yet. At 16:00 the completed high-to-low wave is usable.
    assert pd.isna(art.loc[pd.Timestamp("2026-01-01 12:00", tz="UTC")])
    assert art.loc[pd.Timestamp("2026-01-01 16:00", tz="UTC")] == pytest.approx(15.0)


def test_wave_atr_does_not_use_current_unclosed_four_hour_bucket():
    prefix = _htf_fixture([100, 110, 105, 120, 108], [90, 100, 95, 105, 100])
    extended = _htf_fixture([100, 110, 105, 120, 108, 200], [90, 100, 95, 105, 100, 50])

    prefix_art = _closed_htf_wave_ranges(prefix, pivot_q=1)
    extended_art = _closed_htf_wave_ranges(extended, pivot_q=1)
    cutoff = pd.Timestamp("2026-01-01 19:30", tz="UTC")

    assert extended_art.loc[cutoff] == prefix_art.loc[cutoff] == pytest.approx(15.0)
    assert extended_art.loc[:cutoff].equals(prefix_art.loc[:cutoff])


def test_directional_wave_atr_keeps_up_and_down_wave_averages_separate():
    frame = _htf_fixture(
        [100, 130, 110, 150, 120, 145, 125],
        [90, 100, 95, 105, 100, 110, 105],
    )

    long_art, short_art = _closed_htf_directional_wave_ranges(frame, pivot_q=1, n_waves=2)
    point = pd.Timestamp("2026-01-01 20:00", tz="UTC")

    assert long_art.loc[point] == pytest.approx(55.0)
    assert short_art.loc[point] == pytest.approx(35.0)
    assert long_art.loc[point] != short_art.loc[point]


def test_htf_levels_are_causal_and_have_no_level_in_new_price_area():
    frame = _htf_fixture([100, 130, 110, 150, 120, 145], [90, 100, 95, 105, 100, 110])
    levels = _closed_htf_levels(frame, "1h", pivot_q=1, ltf_bar_minutes=15)
    extended = frame.copy()
    extended.iloc[-16:, extended.columns.get_loc("high")] = 200.0
    extended.iloc[-16:, extended.columns.get_loc("close")] = 195.0
    extended_levels = _closed_htf_levels(extended, "1h", pivot_q=1, ltf_bar_minutes=15)

    cutoff = frame.index[-17]
    assert extended_levels.loc[cutoff].to_dict() == levels.loc[cutoff].to_dict()
    assert levels["support"].notna().any()
    assert levels["resistance"].notna().any()


def test_reversal_setup_requires_impulse_compression_and_reexpansion():
    config = StrategyConfig(atr_period=1, ema_period=1, compression_min_bars=2, compression_max_bars=4)
    engine = StrategyEngine(config)
    engine.zones[1] = Zone(1, ZoneType.SUPPORT, 90.0, 5.0, 0, 0)
    engine._atr = [4.0] * 10

    impulse = Bar(1, 95.0, 96.0, 90.0, 92.0, 1000, 1, 1, htf_art_long=10.0)
    engine.bars = [bar(0, 100.0, 101.0, 99.0, 100.0, day=1, slot=0), impulse]
    engine._update_reversal_setups(impulse, 4.0)
    assert engine.reversal_setups[Side.LONG].phase is ReversalPhase.IMPULSE_REACHED

    compression_1 = Bar(2, 92.0, 93.0, 91.0, 92.0, 1000, 1, 2, htf_art_long=10.0)
    engine.bars.append(compression_1)
    engine._update_reversal_setups(compression_1, 4.0)
    compression_2 = Bar(3, 92.0, 93.0, 91.5, 92.0, 1000, 1, 3, htf_art_long=10.0)
    engine.bars.append(compression_2)
    engine._update_reversal_setups(compression_2, 4.0)
    assert engine.reversal_setups[Side.LONG].phase is ReversalPhase.COMPRESSION

    reexpansion = Bar(4, 92.0, 97.0, 91.0, 96.0, 1000, 1, 4, htf_art_long=10.0)
    engine.bars.append(reexpansion)
    engine._update_reversal_setups(reexpansion, 4.0)
    assert engine.reversal_setups[Side.LONG].phase is ReversalPhase.RE_EXPANSION


def test_zone_geometry_is_frozen_and_validated():
    zone = Zone(1, ZoneType.RESISTANCE, 100.0, 2.0, 10, 11)
    validate_zone(zone, 0.01)
    assert zone.min_price == 98.0
    assert zone.max_price == 102.0
    zone.center = 101.0
    assert zone.min_price == 99.0
    assert zone.width == 2.0


def test_touch_limit_allows_third_and_expires_fourth():
    engine = StrategyEngine(StrategyConfig(max_touches=3))
    zone = Zone(1, ZoneType.RESISTANCE, 100.0, 1.0, 0, 1, touches=2)
    engine.zones[1] = zone
    engine._update_zones(bar(0, 100, 100.5, 99.5, 100), 1.0)
    assert zone.touches == 3
    assert zone.status is ZoneStatus.ACTIVE
    zone.previous_overlap = False
    engine._update_zones(bar(1, 100, 100.5, 99.5, 100), 1.0)
    assert zone.touches == 4
    assert zone.status is ZoneStatus.EXPIRED_TOUCHES


def test_true_breakout_is_directional():
    engine = StrategyEngine(StrategyConfig(true_breakout_beta=0.25))
    resistance = Zone(1, ZoneType.RESISTANCE, 100.0, 1.0, 0, 1)
    support = Zone(2, ZoneType.SUPPORT, 100.0, 1.0, 0, 1)
    engine.zones = {1: resistance, 2: support}
    engine._update_zones(bar(0, 100, 102, 99, 101.6), 2.0)
    assert resistance.status is ZoneStatus.INVALIDATED_BROKEN
    assert support.status is ZoneStatus.ACTIVE


def test_disabled_emergency_exit_only_invalidates_the_zone():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(true_breakout_beta=0.25, emergency_exit=False))
    engine.zones[1] = Zone(1, ZoneType.RESISTANCE, 100.0, 1.0, 0, 1)
    engine.position = Position(Side.SHORT, 0, 100.0, 105.0, 90.0, 1.0, 1)

    engine._update_zones(bar(0, 100, 102, 99, 101.6), 2.0)

    assert engine.zones[1].status is ZoneStatus.INVALIDATED_BROKEN
    assert engine.emergency_zone_id is None


def test_price_discovery_invalidates_broken_zone_without_removing_opposite_zone():
    engine = StrategyEngine(StrategyConfig(true_breakout_beta=0.25, price_discovery_enabled=True))
    resistance = Zone(1, ZoneType.RESISTANCE, 100.0, 1.0, 0, 1)
    support = Zone(2, ZoneType.SUPPORT, 90.0, 1.0, 0, 1)
    engine.zones = {1: resistance, 2: support}

    engine._update_zones(bar(0, 100, 102, 99, 101.6), 2.0)

    assert resistance.status is ZoneStatus.INVALIDATED_BROKEN
    assert support.status is ZoneStatus.ACTIVE


def test_zone_expires_after_idle_period_since_last_touch():
    engine = StrategyEngine(StrategyConfig(max_age_bars=100, zone_idle_max_bars=3))
    zone = Zone(1, ZoneType.SUPPORT, 100.0, 1.0, 0, 1, last_touch_at=0)
    engine.zones[1] = zone

    engine._update_zones(bar(4, 104, 105, 103, 104), 1.0)

    assert zone.status is ZoneStatus.EXPIRED_AGE


def test_uncertain_level_rsi_requires_reversal_out_of_extreme():
    engine = StrategyEngine(StrategyConfig(uncertain_rsi_enabled=True, rsi_oversold=35, rsi_overbought=65))
    engine.reversal_setups[Side.LONG].level_state = "STALE_ATR"
    engine._rsi = [30.0, 29.0]
    assert not engine._uncertain_level_rsi_ok(bar(1, 100, 101, 99, 100), Side.LONG)
    engine._rsi = [30.0, 31.0]
    assert engine._uncertain_level_rsi_ok(bar(1, 100, 101, 99, 100), Side.LONG)

    engine.reversal_setups[Side.SHORT].level_state = "STALE_ATR"
    engine._rsi = [70.0, 71.0]
    assert not engine._uncertain_level_rsi_ok(bar(1, 100, 101, 99, 100), Side.SHORT)
    engine._rsi = [70.0, 69.0]
    assert engine._uncertain_level_rsi_ok(bar(1, 100, 101, 99, 100), Side.SHORT)


def test_active_level_does_not_require_rsi():
    engine = StrategyEngine(StrategyConfig(uncertain_rsi_enabled=True))
    engine.reversal_setups[Side.LONG].level_state = "ACTIVE_ZONE"
    engine._rsi = [50.0, 50.0]
    assert engine._uncertain_level_rsi_ok(bar(1, 100, 101, 99, 100), Side.LONG)


def test_session_boundary_closes_position_at_previous_day_close():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(commission_rate=0.0, flat_at_day_boundary=True))
    engine.bars.append(bar(0, 100.0, 101.0, 99.0, 100.0, day="2026-01-01"))
    engine.position = Position(Side.LONG, 0, 100.0, 95.0, 110.0, 1.0, 1)

    engine.on_bar(bar(1, 102.0, 103.0, 101.0, 102.0, day="2026-01-02"), emit_signals=False)

    assert engine.position is None
    assert engine.trades[0].reason == "CLOSED_SESSION"
    assert engine.trades[0].exit_bar == 0
    assert engine.trades[0].exit_price == 100.0


def test_rvol_uses_only_prior_days_and_robust_floor():
    history = [
        bar(i, 100, 101, 99, 100, 1000, day=i, slot=0)
        for i in range(20)
    ]
    current = bar(20, 100, 101, 99, 100, 2600, day=20, slot=0)
    baseline = robust_slot_baseline(history, current, 20)
    assert baseline == (1000, 50.0)
    assert volume_spike(history, current, StrategyConfig(rvol_days=20)) is True


def test_wilder_atr_seed_is_not_available_early():
    bars = [bar(i, 100, 102, 98, 100) for i in range(3)]
    values = atr_wilder(bars, 3)
    assert values[:2] == [None, None]
    assert values[2] == 4.0


def test_emergency_exit_has_priority_over_pending_entry():
    config = StrategyConfig(tick_size=0.01, fixed_spread=0.2, fixed_slippage=0.1)
    engine = StrategyEngine(config)
    from app.zvezdin_engine import PendingOrder, Position

    engine.position = Position(Side.SHORT, 0, 100.0, 105.0, 90.0, 1.0, 1)
    engine.pending = PendingOrder(Side.LONG, 0, 2, 95.0, 2.0)
    engine.emergency_zone_id = 1
    engine.bars.append(bar(0, 100, 101, 99, 100))
    engine._atr = [2.0]
    engine._open_phase(bar(1, 102.5, 103, 102, 102.5))
    assert engine.position is None
    assert engine.pending is None
    assert engine.trades[0].reason == "CLOSED_EMERGENCY"
    assert engine.trades[0].exit_price == 102.7


def test_pivot_is_not_registered_before_right_shoulder_closes():
    prefix = [
        bar(0, 99, 100, 98, 99),
        bar(1, 104, 105, 103, 104),
        bar(2, 109, 110, 108, 109),
    ]
    engine_a = StrategyEngine(StrategyConfig(pivot_q=2, atr_period=1, ema_period=1))
    engine_b = StrategyEngine(StrategyConfig(pivot_q=2, atr_period=1, ema_period=1))
    for current in prefix:
        engine_a.on_bar(current)
    for current in prefix:
        engine_b.on_bar(current)
    assert engine_a.pivots == []
    assert engine_b.pivots == []
    assert engine_a.events == engine_b.events


def test_synthetic_path_uses_order_when_levels_are_on_different_segments():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(tick_size=0.01))
    engine.position = Position(Side.SHORT, 0, 100.0, 105.0, 90.0, 1.0, 1)
    # Bullish path is O -> L -> H -> C, so TP is reached before SL.
    engine.process_intrabar(bar(1, 98, 106, 89, 99))
    assert engine.trades[0].reason == "CLOSED_TP"
    assert engine.trades[0].exit_price == 90.0


def test_doji_collision_always_uses_stop():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(tick_size=0.01))
    engine.position = Position(Side.LONG, 0, 100.0, 95.0, 110.0, 1.0, 1)
    engine.process_intrabar(bar(1, 100, 111, 94, 100))
    assert engine.trades[0].reason == "CLOSED_SL"
    assert engine.trades[0].exit_price == 95.0


def test_stop_gap_uses_actual_market_open():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(tick_size=0.01, fixed_spread=0.2, fixed_slippage=0.1))
    engine.position = Position(Side.SHORT, 0, 100.0, 105.0, 90.0, 1.0, 1)
    engine.process_intrabar(bar(1, 108.0, 109.0, 107.0, 108.5))
    assert engine.trades[0].exit_price == 108.2


def test_dynamic_execution_costs_use_bar_values():
    from app.zvezdin_engine import Position
    import pytest

    config = StrategyConfig(
        spread_model="DYNAMIC_FROM_DATA",
        slippage_model="DYNAMIC_FROM_DATA",
        fixed_spread=0.0,
        fixed_slippage=0.0,
        commission_rate=0.0,
    )
    engine = StrategyEngine(config)
    engine.position = Position(Side.SHORT, 0, 100.0, 105.0, 90.0, 1.0, 1)
    with pytest.raises(ValueError, match="dynamic spread"):
        engine._exit_market(108.0, Side.SHORT, bar(1, 108.0, 109.0, 107.0, 108.5))
    engine.process_intrabar(Bar(2, 108.0, 109.0, 107.0, 108.5, 1, spread=0.2, slippage=0.1), 2)
    assert engine.trades[0].exit_price == 108.2


def test_volatility_scaled_slippage_uses_atr():
    config = StrategyConfig(slippage_model="VOLATILITY_SCALED", slippage_atr_ratio=0.5, tick_size=0.01)
    engine = StrategyEngine(config)
    assert engine._entry_market(100.0, Side.LONG, Bar(0, 100, 101, 99, 100, 1), 2.0) == 101.0


def test_zone_signal_modes_change_target_selection_deterministically():
    base = Bar(0, 100.0, 101.0, 99.0, 100.5, 1000.0)
    strict = StrategyEngine(StrategyConfig(zone_signal_mode="STRICT", atr_period=1, ema_period=1))
    touch = StrategyEngine(StrategyConfig(zone_signal_mode="TOUCH", atr_period=1, ema_period=1))
    for engine in (strict, touch):
        engine.bars.append(base)
        engine._atr.append(1.0)
        engine._ema.append(100.0)
        engine.zones[1] = Zone(1, ZoneType.RESISTANCE, 100.0, 1.0, 0, 0)
    assert strict._select_zone(base, Side.SHORT) is None
    assert touch._select_zone(base, Side.SHORT) is not None


def test_relaxation_pct_is_bounded_and_changes_acceleration_threshold():
    import pytest

    with pytest.raises(ValueError, match="relaxation_pct"):
        StrategyConfig(relaxation_pct=101)
    strict = StrategyEngine(StrategyConfig(body_lookback=2, body_anomaly_ratio=2.0, relaxation_pct=0))
    relaxed = StrategyEngine(StrategyConfig(body_lookback=2, body_anomaly_ratio=2.0, relaxation_pct=3))
    history = [bar(0, 100, 101, 99, 101), bar(1, 100, 101, 99, 101)]
    current = bar(2, 100, 101.97, 99, 101.97)
    assert strict._body_acceleration(history, current) is False
    assert relaxed._body_acceleration(history, current) is True


def test_relaxation_runs_through_zone_creation():
    engine = StrategyEngine(StrategyConfig(atr_period=1, ema_period=1, relaxation_pct=3))
    bars = [
        bar(0, 100, 101, 99, 100),
        bar(1, 101, 103, 100, 102),
        bar(2, 102, 102, 99, 100),
    ]
    for current in bars:
        engine.on_bar(current)
    assert engine.status is not None


def test_score_mode_uses_hard_shape_and_soft_score_threshold():
    config = StrategyConfig(signal_mode="SCORE", min_soft_score=3)
    assert config.signal_mode == "SCORE"
    assert config.min_soft_score == 3
    assert config.score_requires_flow is True


def test_volume_management_is_disabled_by_default_and_can_move_trade_levels():
    from app.zvezdin_engine import Position

    config = StrategyConfig(
        post_entry_volume_management=True,
        volume_entry_filter=False,
        volume_stop_buffer_atr_ratio=0.1,
        volume_target_extension_r=0.5,
        commission_rate=0.0,
    )
    engine = StrategyEngine(config)
    engine.bars = [
        bar(i, 100, 101, 99, 100, 1000, day=i, slot=0)
        for i in range(20)
    ]
    engine._atr = [1.0] * 20
    engine.position = Position(Side.LONG, 0, 100.0, 95.0, 102.0, 1.0, 1, 5.0)
    current = bar(20, 100, 104, 99, 103, 3000, day=20, slot=0)
    engine.bars.append(current)

    engine._manage_position_by_volume(current, 1.0)

    assert engine.position.stop_loss == pytest.approx(100.0)
    assert engine.position.take_profit == pytest.approx(104.5)
    assert engine.events[-1].event == "VOLUME_MANAGEMENT"


def test_volume_management_can_protect_profit_on_the_next_bar():
    from app.zvezdin_engine import Position

    config = StrategyConfig(
        post_entry_volume_management=True,
        volume_entry_filter=False,
        volume_stop_buffer_atr_ratio=0.1,
        commission_rate=0.0,
    )
    engine = StrategyEngine(config)
    engine.bars = [bar(i, 100, 101, 99, 100, 1000, day=i, slot=0) for i in range(20)]
    engine._atr = [1.0] * 20
    engine.position = Position(Side.LONG, 0, 100.0, 95.0, 110.0, 1.0, 1, 10.0)
    volume_bar = bar(20, 100, 106, 99, 105, 3000, day=20, slot=0)
    engine.bars.append(volume_bar)
    engine._manage_position_by_volume(volume_bar, 1.0)

    engine.process_intrabar(bar(21, 105, 105, 99.5, 100, 1000, day=20, slot=1))

    assert engine.trades[0].reason == "CLOSED_SL"
    assert engine.trades[0].exit_price == pytest.approx(100.0)


def test_current_atr_exhaustion_uses_the_current_move_not_old_wave_size():
    from app.zvezdin_engine import Pivot

    pivots = [
        Pivot(0, 0, 100.0, ZoneType.SUPPORT),
        Pivot(1, 0, 110.0, ZoneType.RESISTANCE),
        Pivot(2, 0, 102.0, ZoneType.SUPPORT),
        Pivot(3, 0, 112.0, ZoneType.RESISTANCE),
        Pivot(4, 0, 104.0, ZoneType.SUPPORT),
    ]
    bars = [bar(0, 100, 100, 99, 99), bar(1, 105, 105, 104, 104), bar(2, 102, 102, 101, 101), bar(3, 104, 105, 103, 104.5)]

    wave_engine = StrategyEngine(StrategyConfig(n_waves=4, exhaustion_mode="WAVE_ATR"))
    current_engine = StrategyEngine(StrategyConfig(n_waves=4, exhaustion_mode="CURRENT_ATR"))
    for engine in (wave_engine, current_engine):
        engine.bars = bars
        engine.pivots = pivots
        engine._atr = [1.0, 1.0, 1.0, 1.0]

    assert wave_engine._exhausted(3, Side.SHORT) is False
    assert current_engine._exhausted(3, Side.SHORT) is True


def test_wave_stack_replaces_weaker_same_type_pivot():
    from app.zvezdin_engine import Pivot

    engine = StrategyEngine()
    engine.pivots = [
        Pivot(1, 1, 100.0, ZoneType.RESISTANCE),
        Pivot(2, 2, 102.0, ZoneType.RESISTANCE),
        Pivot(3, 3, 95.0, ZoneType.SUPPORT),
        Pivot(4, 4, 94.0, ZoneType.SUPPORT),
        Pivot(5, 5, 101.0, ZoneType.RESISTANCE),
    ]
    stack = engine._alternating_pivots(5)
    assert [pivot.price for pivot in stack] == [102.0, 94.0, 101.0]


def test_contract_loads_into_runtime_config():
    config = load_default_config()
    assert config.pivot_q == 3
    assert config.rvol_days == 20
    assert config.fixed_spread == 0.0
    assert config.component_window_acceleration == 1


def test_contract_applies_per_ticker_profile_without_changing_base():
    document = load_default_config_document()
    document["ticker_profiles"] = {
        "SBER": {
            "component_window_acceleration": 1,
            "component_window_atr_completion": 8,
            "component_window_strong_level": 1,
            "component_window_volume_participant": 8,
            "component_window_reverse_impulse": 2,
        }
    }
    profile = strategy_config_for_ticker(document, "sber")
    base = strategy_config_from_contract(load_default_config_document())
    assert profile.component_window_atr_completion == 8
    assert profile.component_window_volume_participant == 8
    assert base.component_window_atr_completion == 1


def test_contract_rejects_inconsistent_cross_field_values():
    document = load_default_config_document()
    document["hyperparameters"]["zone_cluster_atr_ratio"] = 0.1
    document["hyperparameters"]["zone_width_atr_ratio"] = 0.2
    import pytest

    with pytest.raises(ValueError, match="zone width ratio"):
        strategy_config_from_contract(document)


def test_contract_schema_rejects_unknown_runtime_fields():
    document = load_default_config_document()
    document["unexpected"] = True
    import pytest

    with pytest.raises(ValueError, match="Additional properties"):
        strategy_config_from_contract(document)


def load_default_config_document():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "config" / "zvezdin_default_config_v1_1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataframe_adapter_rejects_bad_ohlcv_and_runs_empty_result():
    frame = pd.DataFrame(
        {
            "open": [100.0, 101.0], "high": [101.0, 102.0],
            "low": [99.0, 100.0], "close": [100.5, 101.5], "volume": [10, 11],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="h", tz="UTC"),
    )
    bars = bars_from_dataframe(frame)
    assert bars[0].day == "2025-01-01"
    result = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    assert result.trades == ()
    assert result.final_realized_pnl == 0.0


def test_dataframe_adapter_rejects_non_monotonic_index():
    import pytest

    frame = pd.DataFrame(
        {"open": [100.0, 101.0], "high": [101.0, 102.0], "low": [99.0, 100.0], "close": [100.0, 101.0], "volume": [1.0, 1.0]},
        index=pd.to_datetime(["2025-01-02", "2025-01-01"]),
    )
    with pytest.raises(ValueError, match="monotonic"):
        bars_from_dataframe(frame)


def test_backtest_result_is_json_serializable():
    import json

    frame = pd.DataFrame(
        {"open": [100.0], "high": [101.0], "low": [99.0], "close": [100.5], "volume": [10]},
        index=pd.date_range("2025-01-01", periods=1, freq="h", tz="UTC"),
    )
    result = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    payload = result.as_dict()
    assert payload["open_position"] is None
    assert json.loads(json.dumps(payload, allow_nan=False))["trades"] == []
    assert payload["manifest"]["run_sha256"]
    assert payload["manifest"]["input_sha256"]


def test_run_manifest_is_stable_and_changes_with_data_or_config():
    frame = pd.DataFrame(
        {"open": [100.0, 101.0], "high": [101.0, 102.0], "low": [99.0, 100.0], "close": [100.0, 101.0], "volume": [1.0, 1.0]},
        index=pd.date_range("2025-01-01", periods=2, freq="D"),
    )
    config = StrategyConfig(atr_period=1, ema_period=1)
    first = build_run_manifest(frame, config, "single", 1.0)
    second = build_run_manifest(frame.copy(), config, "single", 1.0)
    assert first == second
    changed_data = frame.copy()
    changed_data.loc[changed_data.index[-1], "close"] = 101.5
    assert dataframe_fingerprint(changed_data) != first["input_sha256"]
    changed_config = StrategyConfig(atr_period=2, ema_period=1)
    assert build_run_manifest(frame, changed_config, "single", 1.0)["config_sha256"] != first["config_sha256"]


def test_open_position_has_mark_to_market_and_equity_pnl():
    from app.zvezdin_engine import Position

    position = Position(Side.LONG, 1, 100.0, 95.0, 110.0, 2.0, 1)
    config = StrategyConfig(fixed_spread=0.2, fixed_slippage=0.1, commission_rate=0.0)
    result = summarize_trades([], open_position=position, terminal_mark_price=105.0, config=config)
    assert mark_to_market_pnl(position, 105.0, config) == pytest.approx(9.6)
    assert result.final_realized_pnl == 0.0
    assert result.unrealized_pnl == pytest.approx(9.6)
    assert result.equity_pnl == pytest.approx(9.6)
    assert result.open_position["side"] is Side.LONG


def test_equity_curve_drawdown_includes_floating_loss():
    result = summarize_trades(
        [],
        terminal_mark_price=95.0,
        open_position=None,
        equity_curve=(
            {"bar": 0, "realized_pnl": 0.0, "unrealized_pnl": 0.0, "equity_pnl": 0.0},
            {"bar": 1, "realized_pnl": 0.0, "unrealized_pnl": -25.0, "equity_pnl": -25.0},
            {"bar": 2, "realized_pnl": 0.0, "unrealized_pnl": -10.0, "equity_pnl": -10.0},
        ),
    )
    assert result.max_drawdown == 25.0
    assert len(result.equity_curve) == 3
    assert result.as_dict()["equity_curve"][1]["equity_pnl"] == -25.0


def test_final_liquidation_adds_closed_end_trade():
    from app.zvezdin_engine import Position

    engine = StrategyEngine(StrategyConfig(commission_rate=0.0))
    engine.position = Position(Side.SHORT, 0, 100.0, 110.0, 80.0, 1.0, 1)
    engine._close_position(2, engine._exit_market(95.0, Side.SHORT), "CLOSED_END")
    assert engine.trades[0].reason == "CLOSED_END"
    assert engine.trades[0].net_pnl == 5.0


def test_prefix_causality_check():
    bars = [bar(i, 100, 101 + (i % 2), 99, 100 + (i % 2)) for i in range(12)]
    assert_causal_prefix(bars, cutoff=6, config=StrategyConfig(atr_period=2, ema_period=2, pivot_q=2))


def test_audit_has_one_causal_record_per_closed_bar():
    frame = pd.DataFrame(
        {"open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101], "close": [100, 101, 102], "volume": [1, 1, 1]},
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    result = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    assert [record["bar"] for record in result.as_dict()["audit"]] == [0, 1, 2]
    assert result.as_dict()["audit"][0]["block_reason"] == "ATR_WARMUP"
    assert {
        "micro_short", "micro_long", "acceleration", "volume_spike",
        "pattern_short", "pattern_long", "decision", "block_reason",
    }.issubset(result.as_dict()["audit"][1])


def test_audit_uses_no_target_zone_reason_after_indicator_warmup():
    frame = pd.DataFrame(
        {"open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101], "close": [100, 101, 102], "volume": [1, 1, 1]},
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    result = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    reasons = [record["block_reason"] for record in result.as_dict()["audit"]]
    assert reasons[-1] == "NO_TARGET_ZONE"


def test_audit_summary_counts_reasons_and_component_rates():
    frame = pd.DataFrame(
        {"open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101], "close": [100, 101, 102], "volume": [1, 1, 1]},
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    result = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    summary = result.audit_summary
    assert summary["bars"] == 3
    assert summary["block_reasons"]["ATR_WARMUP"] == 1
    assert summary["signal_count"] == 0
    assert 0.0 <= summary["component_pass_rates"]["volume_spike"] <= 1.0
    assert summarize_audit(result.audit) == summary


def test_robustness_report_fails_empty_validation_explicitly():
    from app.zvezdin_backtest import WalkForwardResult

    empty = WalkForwardResult((), summarize_trades([]), None)
    report = assess_robustness(empty)
    assert report.passed is False
    assert "has_folds" in report.failures
    assert "minimum_oos_trades" in report.failures


def test_robustness_report_passes_configured_thresholds():
    from app.zvezdin_backtest import BacktestResult, WalkForwardFold, WalkForwardResult

    profitable = summarize_trades([])
    profitable = BacktestResult(
        profitable.trades, profitable.events, 10.0, 0.0, 1.0, None,
        equity_pnl=10.0,
    )
    fold = WalkForwardFold(0, 0, 10, 10, 20, profitable, profitable, 0.8)
    wfo = WalkForwardResult((fold,), profitable, 0.8)
    report = assess_robustness(wfo, min_oos_trades=0)
    assert report.passed is True


def test_robustness_thresholds_reject_non_finite_values():
    from app.zvezdin_backtest import WalkForwardResult

    import pytest

    empty = WalkForwardResult((), summarize_trades([]), None)
    with pytest.raises(ValueError, match="thresholds"):
        assess_robustness(empty, min_wfe=float("nan"))
    with pytest.raises(ValueError, match="thresholds"):
        assess_robustness(empty, min_profitable_oos_fraction=1.1)


def test_sensitivity_summary_detects_stable_neighbors():
    from app.zvezdin_backtest import BacktestResult, SensitivityResult

    def result(pnl):
        return BacktestResult((), (), pnl, 0.0, 0.0, None, equity_pnl=pnl)

    summary = summarize_sensitivity(tuple(
        SensitivityResult({"risk_reward_ratio": value}, result(pnl))
        for value, pnl in ((2.0, 8.0), (2.5, 10.0), (3.0, 8.5))
    ))
    assert summary.passed is True
    assert summary.neighbor_count == 2
    assert summary.neighbor_median_ratio == pytest.approx(0.825)


def test_sensitivity_summary_rejects_sharp_peak():
    from app.zvezdin_backtest import BacktestResult, SensitivityResult

    def result(pnl):
        return BacktestResult((), (), pnl, 0.0, 0.0, None, equity_pnl=pnl)

    summary = summarize_sensitivity(tuple(
        SensitivityResult({"risk_reward_ratio": value}, result(pnl))
        for value, pnl in ((2.0, 1.0), (2.5, 10.0), (3.0, 1.0))
    ))
    assert summary.passed is False
    assert "sharp_peak" in summary.failures


def test_audit_prefix_does_not_change_when_future_bars_are_added():
    base = pd.DataFrame(
        {"open": [100, 101], "high": [101, 102], "low": [99, 100], "close": [100, 101], "volume": [1, 1]},
        index=pd.date_range("2025-01-01", periods=2, freq="D"),
    )
    extended = pd.concat([
        base,
        pd.DataFrame(
            {"open": [102], "high": [103], "low": [101], "close": [102], "volume": [1]},
            index=pd.date_range("2025-01-03", periods=1, freq="D"),
        ),
    ])
    config = StrategyConfig(atr_period=1, ema_period=1)
    first = run_dataframe_backtest(base, config).as_dict()["audit"]
    second = run_dataframe_backtest(extended, config).as_dict()["audit"][:2]
    assert first == second


def test_walk_forward_uses_non_overlapping_oos_windows():
    frame = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(12)],
            "high": [101.0 + i for i in range(12)],
            "low": [99.0 + i for i in range(12)],
            "close": [100.5 + i for i in range(12)],
            "volume": [1000.0] * 12,
        },
        index=pd.date_range("2025-01-01", periods=12, freq="D", tz="UTC"),
    )
    result = walk_forward_backtest(
        frame,
        StrategyConfig(atr_period=1, ema_period=1),
        train_bars=4,
        test_bars=2,
        step_bars=2,
    )
    assert [(fold.train_start, fold.train_end, fold.test_start, fold.test_end) for fold in result.folds] == [
        (0, 4, 4, 6), (2, 6, 6, 8), (4, 8, 8, 10), (6, 10, 10, 12)
    ]
    assert result.aggregate_oos.final_realized_pnl == 0.0


def test_walk_forward_efficiency_is_none_without_profitable_is():
    frame = pd.DataFrame(
        {"open": [100, 101], "high": [101, 102], "low": [99, 100], "close": [100, 101], "volume": [1, 1]},
        index=pd.date_range("2025-01-01", periods=2, freq="D"),
    )
    empty = run_dataframe_backtest(frame, StrategyConfig(atr_period=1, ema_period=1))
    assert walk_forward_efficiency(empty, empty, frame, frame) is None


def test_sensitivity_grid_and_cost_stress_are_isolated():
    frame = pd.DataFrame(
        {"open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101], "close": [100, 101, 102], "volume": [1, 1, 1]},
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    config = StrategyConfig(atr_period=1, ema_period=1)
    grid = sensitivity_grid(frame, config, {"risk_reward_ratio": [2.0, 2.5]})
    assert [item.parameters["risk_reward_ratio"] for item in grid] == [2.0, 2.5]
    stress = stress_costs(frame, config, (1.0, 2.0))
    assert [item.parameters["cost_multiplier"] for item in stress] == [1.0, 2.0]
    assert config.fixed_spread == 0.0


def test_wfo_and_grid_reject_invalid_controls():
    import pytest

    frame = pd.DataFrame(
        {"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1]},
        index=pd.date_range("2025-01-01", periods=1, freq="D"),
    )
    config = StrategyConfig(atr_period=1, ema_period=1)
    with pytest.raises(ValueError, match="train_bars"):
        walk_forward_backtest(frame, config, train_bars=0)
    with pytest.raises(ValueError, match="unknown sensitivity"):
        sensitivity_grid(frame, config, {"not_a_parameter": [1]})
    with pytest.raises(ValueError, match="non-negative"):
        stress_costs(frame, config, (-1.0,))


def test_wfo_rejects_negative_warmup():
    import pytest

    frame = pd.DataFrame(
        {"open": [100, 101], "high": [101, 102], "low": [99, 100], "close": [100, 101], "volume": [1, 1]},
        index=pd.date_range("2025-01-01", periods=2, freq="D"),
    )
    with pytest.raises(ValueError, match="warmup_bars"):
        walk_forward_backtest(frame, StrategyConfig(atr_period=1, ema_period=1), 1, 1, warmup_bars=-1)


def test_wfo_warmup_accepts_omitted_config():
    frame = pd.DataFrame(
        {"open": [100, 101, 102, 103], "high": [101, 102, 103, 104], "low": [99, 100, 101, 102], "close": [100, 101, 102, 103], "volume": [1, 1, 1, 1]},
        index=pd.date_range("2025-01-01", periods=4, freq="D"),
    )
    result = walk_forward_backtest(frame, train_bars=2, test_bars=1, warmup_bars=1)
    assert len(result.folds) == 2


def test_optimized_wfo_selects_parameters_only_on_is_window():
    frame = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(8)],
            "high": [101.0 + i for i in range(8)],
            "low": [99.0 + i for i in range(8)],
            "close": [100.5 + i for i in range(8)],
            "volume": [1000.0] * 8,
        },
        index=pd.date_range("2025-01-01", periods=8, freq="D"),
    )
    result = walk_forward_optimize(
        frame,
        StrategyConfig(atr_period=1, ema_period=1),
        {"risk_reward_ratio": [2.0, 2.5]},
        train_bars=3,
        test_bars=2,
    )
    assert len(result.folds) == 2
    assert all(fold.selected_parameters in ({"risk_reward_ratio": 2.0}, {"risk_reward_ratio": 2.5}) for fold in result.folds)
    assert result.manifest["mode"] == "wfo_optimized"


def test_m1_bars_are_attached_to_half_open_parent_intervals():
    parent_index = pd.date_range("2025-01-01 10:00", periods=2, freq="h", tz="UTC")
    m1_index = pd.date_range("2025-01-01 10:00", periods=3, freq="30min", tz="UTC")
    parent = pd.DataFrame(
        {"open": [100, 101], "high": [101, 102], "low": [99, 100], "close": [100, 101], "volume": [1, 1]},
        index=parent_index,
    )
    m1 = pd.DataFrame(
        {"open": [100, 100.5, 101], "high": [100.5, 101, 101.5], "low": [99.5, 100, 100.5], "close": [100.2, 100.8, 101.2], "volume": [1, 1, 1]},
        index=m1_index,
    )
    attached = m1_bars_by_parent(m1, parent, m1_bar_minutes=30)
    assert [item.index for item in attached[0]] == [0, 1]
    assert [item.index for item in attached[1]] == [2]


def test_m1_mapping_rejects_out_of_range_data():
    import pytest

    parent = pd.DataFrame(
        {"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1]},
        index=pd.date_range("2025-01-01 10:00", periods=1, tz="UTC"),
    )
    m1 = pd.DataFrame(
        {"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1]},
        index=pd.date_range("2025-01-01 09:59", periods=1, tz="UTC"),
    )
    with pytest.raises(ValueError, match="outside parent intervals"):
        m1_bars_by_parent(m1, parent)


def test_calendar_excludes_holidays_and_early_close_days_from_rvol():
    calendar = SessionCalendar(
        holidays=frozenset({"2025-01-02"}),
        early_closes={"2025-01-03": 630},
    )
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 100.0],
            "high": [101.0] * 4,
            "low": [99.0] * 4,
            "close": [100.0] * 4,
            "volume": [1000.0] * 4,
        },
        index=pd.to_datetime([
            "2025-01-01 10:00", "2025-01-02 10:00",
            "2025-01-03 10:00", "2025-01-04 10:00",
        ], utc=True),
    )
    bars = bars_from_dataframe(frame, session_start_minute=600, session_end_minute=1080, calendar=calendar)
    assert bars[0].valid_session is True and bars[0].rvol_valid_day is True
    assert bars[1].valid_session is False and bars[1].rvol_valid_day is False
    assert bars[2].valid_session is True and bars[2].rvol_valid_day is False
    assert bars[3].valid_session is True and bars[3].rvol_valid_day is True


def test_calendar_loader_reads_example_shape(tmp_path):
    path = tmp_path / "calendar.json"
    path.write_text('{"holidays":["2025-01-01"],"early_closes":{"2025-01-02":825}}', encoding="utf-8")
    calendar = load_calendar(path)
    assert calendar.is_holiday("2025-01-01")
    assert calendar.close_minute("2025-01-02", 1125) == 825
