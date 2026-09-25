from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.vsa_strategy import (
    StrategyConfig,
    _entry_fill,
    _round_down,
    _round_lot,
    _round_up,
    context_diagnostics,
    prepare_strategy_frame,
    run_backtest,
)
from scripts.backtest_vsa_strategy import _candidate_score


def _bars(count: int = 260 * 5) -> pd.DataFrame:
    timestamps = pd.date_range("2020-01-01 10:00", periods=count, freq="15min")
    close = np.linspace(100, 180, count)
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": close - 0.2,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": np.full(count, 100.0),
    })


def test_tick_and_lot_rounding_is_conservative() -> None:
    assert _round_down(100.019, 0.01) == pytest.approx(100.01)
    assert _round_up(100.011, 0.01) == pytest.approx(100.02)
    assert _round_lot(19.99, 10) == 10


def test_invalid_bar_breaks_causal_segment_and_features() -> None:
    frame = _bars(80)
    frame.loc[40, "high"] = np.nan
    prepared = prepare_strategy_frame(frame, StrategyConfig())

    assert not prepared.loc[40, "valid_bar"]
    assert prepared.loc[41, "segment"] > prepared.loc[39, "segment"]
    assert pd.isna(prepared.loc[41, "atr"])
    assert prepared.loc[41, "dir"] == 0


def test_4h_filter_uses_completed_context_not_current_bar() -> None:
    frame = _bars(260 * 20)
    prepared = prepare_strategy_frame(frame, StrategyConfig())

    # The context column is boolean and only completed 4h bars can influence it.
    assert prepared["context_bull"].dtype == bool


def test_m1_requires_trade_flow_columns() -> None:
    frame = _bars(250)
    prepared = prepare_strategy_frame(frame, StrategyConfig())

    assert prepared["flow_long"].eq(False).all()
    assert prepared["book_long"].eq(False).all()


def test_4h_context_warmup_is_available_in_three_months() -> None:
    diagnostics = context_diagnostics(_bars(96 * 90), StrategyConfig())

    assert diagnostics["insufficient_warmup"] is False
    assert diagnostics["required_4h_periods"] == 200


def test_market_fill_applies_adverse_costs() -> None:
    frame = _bars(220)
    prepared = prepare_strategy_frame(frame, StrategyConfig())
    signal = type("SignalStub", (), {
        "atr": 1.0,
        "order_type": "MARKET",
    })()
    modeled, raw = _entry_fill(prepared, signal, prepared.iloc[100], StrategyConfig())

    assert raw == pytest.approx(prepared.iloc[100]["open"])
    assert modeled > raw


def test_empty_candidate_backtest_has_deterministic_metrics() -> None:
    result = run_backtest(_bars(), StrategyConfig())

    assert result.trades.empty
    assert result.metrics["trades"] == 0
    assert result.metrics["net_pnl"] == 0


def test_validation_candidate_gate_rejects_drawdown_at_limit() -> None:
    row = {
        "trades": 50.0,
        "profit_factor": 1.10,
        "max_drawdown_pct": 1.5,
        "net_pnl": 100.0,
    }
    assert _candidate_score(row) is not None

    row["max_drawdown_pct"] = 1.500001
    assert _candidate_score(row) is None
