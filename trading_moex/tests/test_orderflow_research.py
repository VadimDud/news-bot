from __future__ import annotations

import pandas as pd
import pytest

from app.market_data import BookSnapshot, TradeEvent, persist_events
from app.orderflow_research import evaluate_orderflow_scenarios, load_orderflow_bars, summarize_scenarios


def test_orderflow_bars_and_scenarios_are_causal(tmp_path) -> None:
    db_path = tmp_path / "flow.db"
    base = pd.Timestamp("2026-01-01 10:00", tz="UTC")
    persist_events(db_path, trades=tuple(
        TradeEvent("T", (base + pd.Timedelta(minutes=minute)).to_pydatetime(), 100, 10, "BUY")
        for minute in (1, 2, 3, 16)
    ), books=(BookSnapshot("T", (base + pd.Timedelta(minutes=4)).to_pydatetime(), ((99, 100),), ((101, 10),)),))
    bars = load_orderflow_bars(db_path, "T")
    candles = pd.DataFrame({
        "timestamp": [base, base + pd.Timedelta(minutes=15), base + pd.Timedelta(minutes=30), base + pd.Timedelta(minutes=45), base + pd.Timedelta(minutes=60)],
        "close": [100, 100.1, 100.2, 100.3, 101],
        "volume": [30, 30, 30, 30, 30],
    })
    events = evaluate_orderflow_scenarios(bars, candles, min_coverage=0.5, book_threshold=0.1, horizon=1)
    assert list(events["scenario"]) == ["CONTINUATION_LONG"]
    assert events.iloc[0]["forward_return"] == pytest.approx(0.001)


def test_scenario_summary_reports_wilson_interval() -> None:
    events = pd.DataFrame({"scenario": ["A", "A", "A"], "forward_return": [0.1, -0.1, 0.2]})
    summary = summarize_scenarios(events)
    row = summary.iloc[0]
    assert row["samples"] == 3
    assert row["win_rate"] == 2 / 3
    assert 0 <= row["ci_low"] <= row["win_rate"] <= row["ci_high"] <= 1
