"""Тесты скринера ROE + P/B (ISS-запросы замоканы)."""

import pytest

from app import fundamentals, storage
from app.fundamentals_screener import screen_catalog


def _csv_text(rows: str) -> str:
    return "date,roe,book_value_per_share\n" + rows


@pytest.fixture
def cheap_high_roe_fundamentals():
    """Тикер с высоким ROE и дешёвым капиталом (BVPS 230 → P/B 0.65 при цене 150)."""
    imports = []
    for ticker, roe, bvps in [("SBER", 20.0, 230.0), ("NOTANDID", 10.0, 230.0), ("EXPENSIVE", 20.0, 100.0)]:
        rows = "".join(f"{y}-12-31,{roe},{bvps}\n" for y in range(2016, 2026))
        n = funds_import(ticker, rows)
        imports.append(n)
    return imports


def funds_import(ticker: str, rows: str) -> int:
    return fundamentals.import_fundamentals(ticker, _csv_text(rows))


def test_screen_finds_candidate(monkeypatch):
    funds_import("SBER", "".join(f"{y}-12-31,20.0,230.0\n" for y in range(2016, 2026)))
    funds_import("WEAK", "".join(f"{y}-12-31,5.0,230.0\n" for y in range(2016, 2026)))
    monkeypatch.setattr(fundamentals, "get_current_price_iss", lambda t: {"SBER": 150.0, "WEAK": 100.0}[t])

    rows = screen_catalog(min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8)
    by_ticker = {r["ticker"]: r for r in rows}
    assert by_ticker["SBER"]["candidate"] is True
    assert by_ticker["SBER"]["avg_roe"] == 20.0
    assert by_ticker["SBER"]["pb"] == pytest.approx(150.0 / 230.0, abs=0.01)
    assert by_ticker["WEAK"]["candidate"] is False


def test_screen_price_above_entry_rejected(monkeypatch):
    funds_import("SBER", "".join(f"{y}-12-31,20.0,230.0\n" for y in range(2016, 2026)))
    monkeypatch.setattr(fundamentals, "get_current_price_iss", lambda t: 200.0)  # P/B 0.87 > 0.8

    rows = screen_catalog(min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8)
    assert rows[0]["candidate"] is False


def test_screen_filter_tickers(monkeypatch):
    funds_import("SBER", "".join(f"{y}-12-31,20.0,230.0\n" for y in range(2016, 2026)))
    funds_import("LKOH", "".join(f"{y}-12-31,22.0,400.0\n" for y in range(2016, 2026)))
    monkeypatch.setattr(fundamentals, "get_current_price_iss", lambda t: 150.0)

    rows = screen_catalog(tickers=["LKOH"])
    assert len(rows) == 1
    assert rows[0]["ticker"] == "LKOH"


def test_screen_ticker_without_fundamentals():
    rows = screen_catalog(tickers=["NOSUCH"])
    assert rows[0]["ticker"] == "NOSUCH"
    assert "error" in rows[0]
    assert rows[0]["candidate"] is False