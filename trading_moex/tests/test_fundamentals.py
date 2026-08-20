"""Тесты CSV-импорта, хранения и расчёта показателей фундаментальных данных."""

import pandas as pd
import pytest

from app import fundamentals, storage


def _csv_text(rows: str) -> str:
    return "date,roe,book_value_per_share,revenue\n" + rows


@pytest.fixture
def sample_csv():
    return _csv_text(
        "2016-12-31,22.5,74.3,1000\n"
        "2017-12-31,24.1,89.9,1100\n"
        "2018-12-31,25.0,105.0,1200\n"
        "2019-12-31,20.0,120.0,1300\n"
        "2020-12-31,21.5,140.0,1400\n"
        "2021-12-31,23.0,165.0,1500\n"
        "2022-12-31,18.0,180.0,1600\n"
        "2023-12-31,19.5,200.0,1700\n"
        "2024-12-31,17.0,215.0,1800\n"
        "2025-12-31,16.5,230.0,1900\n"
    )


def test_parse_fundamentals_csv_columns(sample_csv):
    df = fundamentals.parse_fundamentals_csv(sample_csv, default_ticker="SBER")
    assert set(df.columns) >= {"date", "roe", "book_value_per_share", "revenue", "ticker"}
    assert df["ticker"].iloc[0] == "SBER"
    assert len(df) == 10


def test_parse_fundamentals_csv_dot_format():
    csv_text = "date,roe,book_value_per_share\n31.12.2020,21.5,140.0\n"
    df = fundamentals.parse_fundamentals_csv(csv_text, default_ticker="LKOH")
    assert str(df["date"].iloc[0])[:10] == "2020-12-31"


def test_parse_fundamentals_csv_negative_roe_ok():
    csv_text = "date,roe,book_value_per_share\n2020-12-31,-25.0,140.0\n"
    df = fundamentals.parse_fundamentals_csv(csv_text, default_ticker="TEST")
    assert df["roe"].iloc[0] == -25.0


def test_parse_fundamentals_csv_missing_required_raises():
    with pytest.raises(ValueError, match="не содержит колонок"):
        fundamentals.parse_fundamentals_csv("date,revenue\n2020-01-01,5\n")


def test_parse_fundamentals_csv_bad_bvps_raises():
    with pytest.raises(ValueError, match="book_value_per_share"):
        fundamentals.parse_fundamentals_csv("date,roe,book_value_per_share\n2020-01-01,10,0\n")


def test_save_load_roundtrip(sample_csv):
    n = fundamentals.import_fundamentals("sber", sample_csv)
    assert n == 10
    assert storage.list_tickers_with_fundamentals() == ["SBER"]
    df = storage.load_fundamentals("SBER")
    assert len(df) == 10
    assert df.iloc[0]["roe"] == 22.5


def test_load_fundamentals_window(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    import datetime

    df = storage.load_fundamentals("SBER", start=datetime.date(2020, 1, 1), end=datetime.date(2022, 1, 1))
    years = df["date"].str[:4].tolist()
    assert years == ["2020", "2021"]


def test_delete_fundamentals(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    assert storage.delete_fundamentals("SBER") == 10
    assert storage.list_tickers_with_fundamentals() == []


def test_get_avg_roe(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    avg = fundamentals.get_avg_roe("SBER", years=10)
    assert avg is not None
    expected = round((22.5 + 24.1 + 25.0 + 20.0 + 21.5 + 23.0 + 18.0 + 19.5 + 17.0 + 16.5) / 10, 2)
    assert avg == expected


def test_get_min_roe(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    assert fundamentals.get_min_roe("SBER", years=10) == 16.5


def test_get_avg_roe_insufficient_data():
    csv_text = _csv_text("2024-12-31,17.0,215.0,1800\n")
    fundamentals.import_fundamentals("SBER", csv_text)
    assert fundamentals.get_avg_roe("SBER", years=10) is None


def test_get_latest_fundamentals(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    latest = fundamentals.get_latest_fundamentals("SBER")
    assert latest["date"] == "2025-12-31"
    assert latest["roe"] == 16.5


def test_prepare_fundamentals_series(sample_csv):
    import datetime

    fundamentals.import_fundamentals("SBER", sample_csv)
    out = fundamentals.prepare_fundamentals_series(
        "SBER", start=datetime.date(2025, 1, 1), end=datetime.date(2025, 1, 5)
    )
    assert len(out) == 5
    assert out["book_value_per_share"].iloc[0] == 215.0
    assert out["avg_roe"].iloc[0] == pytest.approx(21.18, abs=0.01)  # среднее за 2016..2024


def test_fundamentals_stats(sample_csv):
    fundamentals.import_fundamentals("SBER", sample_csv)
    stats = storage.fundamentals_stats("SBER")
    assert stats["count"] == 10
    assert stats["min_date"] == "2016-12-31"
    assert stats["max_date"] == "2025-12-31"