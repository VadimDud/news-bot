import pandas as pd

from app.sr_research import ExperimentSpec, pooled_trade_metrics, select_window


def test_select_window_is_chronological_and_does_not_mutate_input():
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    frame = pd.DataFrame({"close": [1, 2, 3, 4]}, index=index)
    selected = select_window(frame, ExperimentSpec(split="test", split_at="2026-01-03"))
    assert selected["close"].tolist() == [3, 4]
    assert frame["close"].tolist() == [1, 2, 3, 4]


def test_pooled_metrics_do_not_sum_percentage_returns():
    results = [
        {"initial_cash": 100_000, "final_value": 101_000, "total_return_pct": 1, "trades_total": 2, "trades_won": 1, "trades_lost": 1, "avg_win": 2_000, "avg_loss": -1_000},
        {"initial_cash": 100_000, "final_value": 99_000, "total_return_pct": -1, "trades_total": 2, "trades_won": 1, "trades_lost": 1, "avg_win": 1_000, "avg_loss": -1_500},
    ]
    pooled = pooled_trade_metrics(results)
    assert pooled["pooled_pnl"] == 0
    assert pooled["pooled_return_pct"] == 0
    assert pooled["equal_weight_return_pct"] == 0
    assert pooled["profit_factor"] == 1.2
