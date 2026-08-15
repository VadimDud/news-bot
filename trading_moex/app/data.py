"""Загрузка исторических данных с MOEX (AlgoPack) с кэшированием в CSV."""

import logging
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from . import config

logger = logging.getLogger("moex_trader.data")

# Периоды, поддерживаемые moexalgo (обычные свечи доступны без авторизации)
PERIODS = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "60min": "1h",
    "1day": "1D",
    "1week": "1W",
    "1month": "1M",
}

CANDLE_COLUMNS = ["open", "close", "high", "low", "value", "volume"]

CACHE_TTL_SECONDS = 24 * 3600

_MAX_BATCH = 5000


def _ensure_login():
    if config.MOEX_LOGIN and config.MOEX_PASSWORD:
        try:
            from moexalgo.session import authorize

            authorize(config.MOEX_LOGIN, config.MOEX_PASSWORD)
            logger.info("Авторизован на moex.com (Super Candles доступны)")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось авторизоваться на moex.com: %s", exc)
    else:
        logger.info("MOEX_LOGIN/MOEX_PASSWORD не заданы — обычные свечи без авторизации")


def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    """Привести DataFrame свечей MOEX к виду для backtrader (datetime-индекс, OHLCV)."""
    out = df[["begin", "open", "close", "high", "low", "volume"]].copy()
    out["begin"] = pd.to_datetime(out["begin"])
    out = out.set_index("begin").sort_index()
    out.index.name = "datetime"
    out = out[["open", "high", "low", "close", "volume"]]
    return out[~out.index.duplicated(keep="last")]


def _cache_path(ticker: str, period: str, start: date, end: date) -> Path:
    config.CANDLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return config.CANDLE_CACHE_DIR / f"{ticker}_{period}_{start.isoformat()}_{end.isoformat()}.csv"


def fetch_history(ticker: str, period: str, start: date, end: date, use_cache: bool = True) -> pd.DataFrame:
    """Исторические свечи с MOEX. Кэш действителен 24 часа.

    ``ticker`` — код инструмента на MOEX (SBER, LKOH, GMKN, ...).
    """
    if period not in PERIODS:
        raise ValueError(f"Неизвестный период {period!r}; доступно: {', '.join(PERIODS)}")
    if start >= end:
        raise ValueError("Дата начала должна быть раньше даты окончания")
    moex_period = PERIODS[period]

    cache_path = _cache_path(ticker, period, start, end)
    if use_cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            df = pd.read_csv(cache_path, parse_dates=["begin"])
            logger.info("Данные из кэша: %s", cache_path.name)
            return normalize_history(df)

    from moexalgo import Ticker

    _ensure_login()
    logger.info("Загрузка %s %s [%s .. %s] с MOEX", ticker, period, start, end)
    ticker_obj = Ticker(ticker)
    rows: list[dict] = []
    offset = 0
    while True:
        raw = ticker_obj.candles(start, end, period=moex_period, offset=offset)
        batch = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame(raw)
        if batch.empty:
            break
        rows.extend(batch.to_dict("records"))
        if len(batch) < _MAX_BATCH:
            break
        offset += len(batch)

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"MOEX не вернул данных по {ticker} за указанный период")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    return normalize_history(df)


def today() -> date:
    return date.today()


def default_range(days: int = 365) -> tuple[date, date]:
    end = today()
    return end - timedelta(days=days), end
