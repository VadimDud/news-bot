"""Загрузка исторических данных с MOEX (AlgoPack) с кэшированием в CSV."""

import logging
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from . import config
from . import settings

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

# Таймфреймы без нативного интервала на MOEX: moexalgo качает 1-минутные свечи
# и ресэмплит сам, но его resample падает с AttributeError на пустых данных.
# Поэтому для них запрашиваем нативные 1min и ресэмплим сами через pandas.
RESAMPLE_FROM_1MIN = {"5min": "5min", "15min": "15min"}


def _resample_candles(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Ресэмпл 1-минутных свечей (begin) в более крупный таймфрейм.

    Границы бакетов от полуночи, метка = начало бакета — как у moexalgo.
    Пустые бакеты (неторговые паузы) отбрасываются.
    """
    out = df.copy()
    out["begin"] = pd.to_datetime(out["begin"])
    return (
        out.set_index("begin")
        .resample(rule, closed="left", label="left")
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            value=("value", "sum"),
        )
        .dropna()
        .reset_index()
    )


def _ensure_login():
    login_value = settings.moex_login()
    password_value = settings.moex_password()
    if login_value and password_value:
        try:
            from moexalgo.session import authorize

            authorize(login_value, password_value)
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


def _fetch_raw(ticker: str, period: str, start: date, end: date) -> list[dict]:
    """Свечи с MOEX через moexalgo (нативный таймфрейм, без ресэмпла)."""
    from moexalgo import Ticker

    ticker_obj = Ticker(ticker)
    rows: list[dict] = []
    offset = 0
    while True:
        raw = ticker_obj.candles(start, end, period=period, offset=offset)
        batch = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame(raw)
        if batch.empty:
            break
        rows.extend(batch.to_dict("records"))
        if len(batch) < _MAX_BATCH:
            break
        offset += len(batch)
    return rows


def fetch_history(ticker: str, period: str, start: date, end: date, use_cache: bool = True) -> pd.DataFrame:
    """Исторические свечи с MOEX. Кэш действителен 24 часа.

    ``ticker`` — код инструмента на MOEX (SBER, LKOH, GMKN, ...).
    """
    if period not in PERIODS:
        raise ValueError(f"Неизвестный период {period!r}; доступно: {', '.join(PERIODS)}")
    if start >= end:
        raise ValueError("Дата начала должна быть раньше даты окончания")
    moex_period = PERIODS[period]
    request_period = "1min" if period in RESAMPLE_FROM_1MIN else moex_period

    cache_path = _cache_path(ticker, period, start, end)
    if use_cache and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            df = pd.read_csv(cache_path, parse_dates=["begin"])
            logger.info("Данные из кэша: %s", cache_path.name)
            return normalize_history(df)

    _ensure_login()
    logger.info("Загрузка %s %s [%s .. %s] с MOEX", ticker, period, start, end)
    df = pd.DataFrame(_fetch_raw(ticker, request_period, start, end))
    if df.empty:
        raise ValueError(
            f"MOEX не вернул данных по {ticker} за {start.isoformat()}..{end.isoformat()}. "
            "Проверьте тикер и даты — возможно, бумага делистингована или не торговалась в этот период."
        )

    if period in RESAMPLE_FROM_1MIN:
        df = _resample_candles(df, RESAMPLE_FROM_1MIN[period])

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    return normalize_history(df)


def to_csv(df: pd.DataFrame) -> str:
    """Экспорт нормализованных свечей в CSV-строку (datetime,open,high,low,close,volume)."""
    out = df.reset_index().copy()
    out.rename(columns={out.columns[0]: "datetime"}, inplace=True)
    return out.to_csv(index=False)


def today() -> date:
    return date.today()


def default_range(days: int = 365) -> tuple[date, date]:
    end = today()
    return end - timedelta(days=days), end
