"""Open positions must carry a usable ticker label.

Regression for a defect where ``_collect_metrics`` read ``data._name``, which
backtrader resets to an empty string once the feed is added to a cerebro, and
fell back to ``data._dataname``, which is a DataFrame. Open positions in every
research report therefore had ``ticker: ""``.
"""

import pandas as pd

from app.backtest import run_backtest
from app.strategies import STRATEGIES


def _frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=120, freq="D")
    close = pd.Series(range(120), index=index, dtype=float) + 100.0
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        },
        index=index,
    )


def test_open_position_reports_requested_ticker():
    item = STRATEGIES["zone_break"]
    params = {parameter["key"]: parameter["default"] for parameter in item["params"]}
    result = run_backtest(
        _frame(), item["cls"], params, cash=100_000.0, commission=0.0, slippage=0.0,
        ticker="SBER",
    )
    for position in result["open_positions"]:
        assert position["ticker"] == "SBER"


def test_open_position_ticker_is_never_a_dataframe():
    item = STRATEGIES["zone_break"]
    params = {parameter["key"]: parameter["default"] for parameter in item["params"]}
    result = run_backtest(_frame(), item["cls"], params, cash=100_000.0, ticker="SBER")
    labels = [position["ticker"] for position in result["open_positions"]]
    assert all(isinstance(label, str) for label in labels)


def test_feed_name_rejects_dataframe_dataname():
    from app.backtest import _feed_name

    class FakeFeed:
        _name = ""
        _dataname = pd.DataFrame({"close": [1.0]})

    assert _feed_name(FakeFeed()) == ""
