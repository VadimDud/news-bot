"""Скринер кандидатов по фундаментальным данным.

Ищет в загруженной отчётности бумаги с высоким средним ROE и ценой ниже
стоимости капитала. Кандидаты могут быть сужены авто-сканом высококапитализа-
ционных бумаг MOEX (ISS) — чтобы не анализировать весь каталог вручную.
"""

from __future__ import annotations

from . import fundamentals
from . import storage


def _row_for(ticker: str, years: int = 10) -> dict:
    latest = fundamentals.get_latest_fundamentals(ticker)
    if latest is None:
        return {"ticker": ticker, "error": "нет отчётности"}
    stats = storage.fundamentals_stats(ticker)
    avg_roe = fundamentals.get_avg_roe(ticker, years=years)
    min_roe = fundamentals.get_min_roe(ticker, years=years)
    bvps = latest.get("book_value_per_share")
    price = None
    pb = None
    if bvps:
        price = fundamentals.get_current_price_iss(ticker)
    if price and bvps:
        pb = round(float(price) / float(bvps), 3)
    return {
        "ticker": ticker,
        "name": fundamentals_catalog_name(ticker),
        "avg_roe": avg_roe,
        "min_roe": min_roe,
        "roe_latest": storage.to_float(latest.get("roe")),
        "bvps": _round2(bvps),
        "price": price,
        "pb": pb,
        "report_count": stats.get("count", 0),
        "report_from": stats.get("min_date"),
        "report_to": stats.get("max_date"),
    }


def _round2(value) -> float | None:
    f = storage.to_float(value)
    return round(f, 2) if f is not None else None


def fundamentals_catalog_name(ticker: str) -> str:
    """Название из каталога или ISS-скана, иначе просто тикер."""
    try:
        from .catalog import find

        item = find(ticker)
        if item:
            return item["name"]
    except ImportError:
        pass
    return ticker


def screen_catalog(
    min_avg_roe: float = 15.0,
    min_single_roe: float = 12.0,
    pb_entry: float = 0.8,
    years: int = 10,
    tickers: list[str] | None = None,
) -> list[dict]:
    """Оценить заранее загруженные тикеры и вернуть кандидатов.

    Если ``tickers`` не задан — тикеры берутся из базы отчётности. Каждая
    строка помечается ``candidate`` (True/False) и ``needs_oe`` (все ли годы
    заполнены — слабое место входного критерия).
    Все тикеры оцениваются; ``candidate`` только для прошедших условия.
    """
    if tickers is None:
        tickers = storage.list_tickers_with_fundamentals()
    rows = []
    for t in sorted(set(tickers)):
        row = _row_for(t, years=years)
        candidate = (
            row.get("avg_roe") is not None
            and row.get("avg_roe") >= min_avg_roe
            and row.get("roe_latest") is not None
            and row.get("roe_latest") >= min_single_roe
            and row.get("pb") is not None
            and row.get("pb") <= pb_entry
        )
        row["candidate"] = bool(candidate)
        rows.append(row)
    rows.sort(key=lambda r: (not r["candidate"], -(r.get("avg_roe") or 0.0)))
    return rows


def scan_moex_candidates(
    min_avg_roe: float = 15.0,
    min_single_roe: float = 12.0,
    pb_entry: float = 0.8,
    years: int = 10,
    min_market_cap: float = fundamentals.DEFAULT_MIN_MARKET_CAP,
    min_volume_rub: float = fundamentals.DEFAULT_MIN_VOLUME_RUB,
    list_levels: list[int] | None = None,
) -> list[dict]:
    """Авто-скан: только высококапитализационные бумаги с данными в базе.

    Сначала из ISS берутся высококапитализационные акции (typo), затем среди
    них оценивается отчётность из базы. Тикеры без загруженной отчётности
    получают ``error``-строку и не считаются кандидатами.
    """
    scanned = fundamentals.scan_high_cap(min_market_cap, min_volume_rub, list_levels)
    tickers = [s["ticker"] for s in scanned]
    with_funds = [t for t in tickers if t in set(storage.list_tickers_with_fundamentals())]
    return screen_catalog(
        min_avg_roe=min_avg_roe,
        min_single_roe=min_single_roe,
        pb_entry=pb_entry,
        years=years,
        tickers=with_funds,
    )