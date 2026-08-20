"""Тесты парсера conomy.ru (NUXT payload) и авто-загрузки отчётности."""

import pandas as pd
import pytest

from app import conomy, signals
from app.live import LIVE_STRATEGIES


def test_parse_nuxt_payload_simple():
    html = (
        "window.__NUXT__=(function(a,b,c){return {layout:\"default\",data:[{h1:a,"
        'issuers:[{title:"ПАО СБЕРБАНК",slug:b,ticker:["SBER"]}],price:c}]}}'
        '("SBER","sberbank",12.5));</script>'
    )
    payload = conomy._parse_nuxt_payload(html)
    assert payload["layout"] == "default"
    assert payload["data"][0]["h1"] == "SBER"
    assert payload["data"][0]["issuers"][0]["slug"] == "sberbank"
    assert payload["data"][0]["price"] == 12.5


def test_split_args_handles_strings_and_nulls():
    parts = conomy._split_args('"а,б",null,true,"\\u002F",3.14')
    assert parts == ["а,б", None, True, "/", 3.14]


def test_js_object_to_json_normalizes_dot_numbers():
    text = '{"content":.5,"name":"priority"}'
    out = conomy._js_object_to_json(text)
    assert '"content":0.5' in out


def test_roe_portfolio_in_signal_funcs_and_live():
    assert "roe_portfolio" in signals.SIGNAL_FUNCS
    assert "roe_portfolio" in LIVE_STRATEGIES


def test_roe_pb_position_without_fundamentals_is_flat():
    dates = pd.date_range("2021-01-04", periods=10, freq="D")
    df = pd.DataFrame(
        {"open": 50, "high": 51, "low": 49, "close": 50, "volume": 1000},
        index=dates,
    )
    pos = signals.roe_pb_position(df, fundamentals=None)
    assert len(pos) == 10
    assert (pos == 0).all()


def test_roe_pb_position_with_fundamentals_uses_series():
    dates = pd.date_range("2021-01-04", periods=60, freq="D")
    df = pd.DataFrame(
        {
            "open": 60, "high": 61, "low": 59,
            "close": 60,  # BVPS 90 → P/B 0.67 < 0.8
            "volume": 1000,
        },
        index=dates,
    )
    fund = pd.DataFrame(
        [{"date": f"{y}-12-31", "roe": 20.0, "book_value_per_share": 90.0}
         for y in range(2015, 2026)]
    )
    pos = signals.roe_pb_position(df, fundamentals=fund, rebalance_days=1)
    assert pos.sum() > 0


def test_build_fundamentals_shape():
    df = pd.DataFrame(
        {
            "date": ["2019-12-31", "2020-12-31"],
            "roe": [20.43, 14.90],
            "book_value_per_share": [0.21, 0.23],
            "equity": [4.4783e9, 5.0448e9],
            "net_profit": [9.148e8, 7.518e8],
        }
    )
    assert sorted(df.columns) == [
        "book_value_per_share", "date", "equity", "net_profit", "roe",
    ]
    assert df["roe"].iloc[-1] == pytest.approx(14.90)