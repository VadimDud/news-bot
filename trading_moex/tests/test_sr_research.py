import pandas as pd

import json

from app.sr_research import (
    ExperimentSpec, pooled_trade_metrics, sanity_checks, select_window,
    write_run_artifacts,
)


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


def test_sanity_checks_require_complete_closed_ledger():
    report = {"results": [{"ticker": "SBER", "status": "ok", "trades_total": 1,
                            "trades": [{"status": "closed"}]}]}
    checks = sanity_checks(report)
    assert checks["passed"] is True


def test_write_run_artifacts_creates_manifest_metrics_checks_and_ledger(tmp_path):
    report = {
        "spec": {"split": "train", "commission": 0.0005, "slippage": 0.0005},
        "data_sha256": "abc", "pooled": {"trades_total": 1},
        "results": [{"ticker": "SBER", "status": "ok", "trades_total": 1,
                     "trades": [{"status": "closed", "pnl": 12.0}]}],
    }
    run_dir = write_run_artifacts(report, tmp_path / "run-001", command="pytest")
    assert json.loads((run_dir / "manifest.json").read_text())["run_id"] == "run-001"
    assert json.loads((run_dir / "checks.json").read_text())["passed"] is True
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "trades.csv.gz").exists()
    execution = json.loads((run_dir / "manifest.json").read_text())["execution"]
    assert execution["commission_per_side"] == 0.0005
    assert execution["slippage_per_side"] == 0.0005
    assert execution["spread"] == "not_modeled"
