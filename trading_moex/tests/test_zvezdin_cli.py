import json
from pathlib import Path

import pandas as pd

from app.zvezdin_engine import StrategyConfig
from scripts.backtest_zvezdin import build_parser, load_csv, load_sqlite_candles, main, parse_multipliers, run_cli


def make_csv(tmp_path):
    path = tmp_path / "candles.csv"
    pd.DataFrame(
        {
            "datetime": pd.date_range("2025-01-01", periods=8, freq="D", tz="UTC"),
            "open": [100 + i for i in range(8)],
            "high": [101 + i for i in range(8)],
            "low": [99 + i for i in range(8)],
            "close": [100.5 + i for i in range(8)],
            "volume": [1000] * 8,
        }
    ).to_csv(path, index=False)
    return path


def args_for(parser, *extra):
    return parser.parse_args(["--input", *extra])


def test_cli_single_returns_json_safe_result(tmp_path):
    path = make_csv(tmp_path)
    args = build_parser().parse_args(["--input", str(path), "--mode", "single"])
    result = run_cli(args)
    assert result["trades"] == []
    json.dumps(result, allow_nan=False)


def test_cli_applies_ticker_profile_from_contract(tmp_path):
    path = make_csv(tmp_path)
    contract = tmp_path / "contract.json"
    document = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "zvezdin_default_config_v1_1.json").read_text()
    )
    document["ticker_profiles"] = {"TEST": {"component_window_volume_participant": 8}}
    contract.write_text(json.dumps(document), encoding="utf-8")
    args = build_parser().parse_args([
        "--input", str(path), "--ticker", "TEST", "--config", str(contract), "--mode", "single",
    ])
    result = run_cli(args)
    assert result["manifest"]["config"]["component_window_volume_participant"] == 8


def test_cli_wfo_and_stress_modes(tmp_path):
    path = make_csv(tmp_path)
    parser = build_parser()
    wfo_args = parser.parse_args([
        "--input", str(path), "--mode", "wfo", "--train-bars", "3", "--test-bars", "2",
    ])
    wfo = run_cli(wfo_args)
    assert len(wfo["folds"]) == 2

    stress_args = parser.parse_args([
        "--input", str(path), "--mode", "stress", "--multipliers", "1,2",
    ])
    assert len(run_cli(stress_args)["results"]) == 2


def test_cli_sensitivity_reads_grid_file(tmp_path):
    path = make_csv(tmp_path)
    grid_path = tmp_path / "grid.json"
    grid_path.write_text(json.dumps({"risk_reward_ratio": [2.0, 2.5]}), encoding="utf-8")
    args = build_parser().parse_args([
        "--input", str(path), "--mode", "sensitivity", "--grid", str(grid_path),
    ])
    result = run_cli(args)
    assert [item["parameters"]["risk_reward_ratio"] for item in result["results"]] == [2.0, 2.5]


def test_load_csv_does_not_sort_or_fill(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame(
        {
            "datetime": ["2025-01-02", "2025-01-01"],
            "open": [100, 100], "high": [101, 101], "low": [99, 99],
            "close": [100, 100], "volume": [1, 1],
        }
    ).to_csv(path, index=False)
    frame = load_csv(path)
    assert frame.index[0] > frame.index[1]


def test_cli_accepts_m1_input(tmp_path):
    parent_path = make_csv(tmp_path)
    m1_path = tmp_path / "m1.csv"
    pd.DataFrame(
        {
            "datetime": pd.date_range("2025-01-01", periods=8, freq="D", tz="UTC"),
            "open": [100 + i for i in range(8)],
            "high": [101 + i for i in range(8)],
            "low": [99 + i for i in range(8)],
            "close": [100.5 + i for i in range(8)],
            "volume": [1000] * 8,
        }
    ).to_csv(m1_path, index=False)
    args = build_parser().parse_args([
        "--input", str(parent_path), "--m1-input", str(m1_path), "--m1-bar-minutes", "1440",
    ])
    result = run_cli(args)
    assert result["trades"] == []


def test_cli_report_contains_robustness_gate(tmp_path):
    path = make_csv(tmp_path)
    args = build_parser().parse_args([
        "--input", str(path), "--mode", "report", "--train-bars", "3", "--test-bars", "2",
        "--min-oos-trades", "0",
    ])
    result = run_cli(args)
    assert "robustness" in result
    assert "failures" in result["robustness"]


def test_cli_report_can_include_sensitivity_summary(tmp_path):
    path = make_csv(tmp_path)
    grid_path = tmp_path / "grid.json"
    grid_path.write_text(json.dumps({"risk_reward_ratio": [2.0, 2.5, 3.0]}), encoding="utf-8")
    args = build_parser().parse_args([
        "--input", str(path), "--mode", "report", "--train-bars", "3", "--test-bars", "2",
        "--grid", str(grid_path), "--min-oos-trades", "0",
    ])
    result = run_cli(args)
    assert result["sensitivity"] is not None
    assert result["sensitivity"]["combinations"] == 3


def test_cli_report_supports_is_only_optimization(tmp_path):
    path = make_csv(tmp_path)
    grid_path = tmp_path / "grid.json"
    grid_path.write_text(json.dumps({"risk_reward_ratio": [2.0, 2.5]}), encoding="utf-8")
    args = build_parser().parse_args([
        "--input", str(path), "--mode", "report", "--optimize", "--grid", str(grid_path),
        "--train-bars", "3", "--test-bars", "2", "--min-oos-trades", "0",
    ])
    result = run_cli(args)
    assert result["walk_forward"]["manifest"]["mode"] == "wfo_optimized"
    assert all("selected_parameters" in fold for fold in result["walk_forward"]["folds"])


def test_cli_fail_on_quality_gate_returns_nonzero_and_writes_report(tmp_path):
    path = make_csv(tmp_path)
    output = tmp_path / "report.json"
    code = main([
        "--input", str(path), "--mode", "report", "--train-bars", "3", "--test-bars", "2",
        "--min-oos-trades", "0", "--fail-on-quality-gate", "--output", str(output),
    ])
    assert code == 1
    assert json.loads(output.read_text(encoding="utf-8"))["robustness"]["passed"] is False


def test_multiplier_parser_rejects_invalid_values():
    import pytest

    assert parse_multipliers("1, 2.5") == (1.0, 2.5)
    with pytest.raises(ValueError, match="multipliers"):
        parse_multipliers("1,nan")
    with pytest.raises(ValueError, match="multipliers"):
        parse_multipliers("-1")


def test_sqlite_candles_loader(tmp_path):
    import sqlite3

    database = tmp_path / "candles.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE candles (ticker TEXT, period TEXT, begin TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
        connection.execute("INSERT INTO candles VALUES ('SBER', '1h', '2025-01-01T10:00:00Z', 100, 101, 99, 100.5, 1000)")
        connection.commit()
    frame = load_sqlite_candles(database, "SBER", "1h")
    assert len(frame) == 1 and frame.iloc[0]["close"] == 100.5


def test_sqlite_loader_rejects_empty_symbol(tmp_path):
    import sqlite3
    import pytest

    database = tmp_path / "empty.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE candles (ticker TEXT, period TEXT, begin TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    with pytest.raises(ValueError, match="no candles"):
        load_sqlite_candles(database, "SBER", "1h")
