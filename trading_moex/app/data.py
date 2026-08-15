"""Загрузка исторических данных с MOEX (AlgoPack) с синхронизацией в базу.

Свечи хранятся в SQLite (таблица ``candles``, ключ ticker+period+begin).
При запросе докачивается только недостающая информация:
- хвост — новые свечи после последней сохранённой;
- бэкфилл — более ранний диапазон, чем первая сохранённая свеча.
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Callable

import pandas as pd

from . import settings
from . import storage

logger = logging.getLogger("moex_trader.data")

# Периоды, поддерживаемые moexalgo (обычные свечи доступны без авторизации)
PERIODS = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "60min": "1h",
    "1day": "1D",
    "1week": "1W",
    "1month": "1M",
}

CANDLE_COLUMNS = ["open", "close", "high", "low", "value", "volume"]

_MAX_BATCH = 5000

# Таймфреймы без нативного интервала на MOEX: moexalgo качает 1-минутные свечи
# и ресэмплит сам, но его resample падает с AttributeError на пустых данных.
# Поэтому для них запрашиваем нативные 1min и ресэмплим сами через pandas.
RESAMPLE_FROM_1MIN = {"5min": "5min", "15min": "15min", "30min": "30min"}

# Известные переименования/делистинги (подсказка в тексте ошибки).
# Проверено 2026-08: FIVE (X5 Group) и остальные тикеры каталога торгуются.
DELISTED_HINTS = {
    "YNDX": "Актуальный тикер — YDEX (МКПАО «Яндекс»).",
}

# Дробление окон загрузки на куски для плавного прогресса (веб-скачивание).
# Каждый кусок — один запрос к MOEX, поэтому прогресс идёт равными шагами,
# а кусок помещается в один батч (< _MAX_BATCH).
DOWNLOAD_CHUNK_DAYS = {
    "1min": 7, "5min": 7, "15min": 7, "30min": 7,
    "60min": 31, "1day": 183, "1week": 365, "1month": 365,
}


def _iter_windows(start: datetime, end: datetime, chunk_days: int):
    """Разбить полуинтервал [start, end) на куски не длиннее chunk_days дней."""
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        yield cur, nxt
        cur = nxt


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


def _fetch_ranges(
    start: date, end: date, period: str, last: str | None, first: str | None, use_cache: bool
) -> list[tuple[datetime, datetime]]:
    """Окна загрузки в полуинтервалах [start_dt, end_dt).

    Если ``use_cache`` и в базе уже есть данные, качаются только недостающие
    куски: хвост (после последней свечи) и бэкфилл (до первой свечи).
    Для ресэмплируемых периодов хвост начинается с начала последнего бакета,
    чтобы он пересобрался из полных минутных свечей.
    """
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)

    if not use_cache or last is None:
        return [(start_dt, end_dt)]

    ranges: list[tuple[datetime, datetime]] = []
    last_ts = pd.Timestamp(last)
    if period in RESAMPLE_FROM_1MIN:
        tail_start = last_ts.to_pydatetime()
    else:
        tail_start = (last_ts + pd.Timedelta(seconds=1)).to_pydatetime()
    if tail_start < end_dt:
        ranges.append((max(start_dt, tail_start), end_dt))

    if first is not None:
        first_ts = pd.Timestamp(first).to_pydatetime()
        if start_dt < first_ts:
            ranges.append((start_dt, min(end_dt, first_ts)))

    return ranges


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


def fetch_history(
    ticker: str,
    period: str,
    start: date,
    end: date,
    use_cache: bool = True,
    progress: Callable[[int], None] | None = None,
) -> pd.DataFrame:
    """Исторические свечи с MOEX, синхронизированные с базой.

    Докачиваются только недостающие куски (хвост после последней сохранённой
    свечи и бэкфилл до первой); результат возвращается из базы за [start, end].

    ``progress`` — необязательный колбэк, получает процент выполнения (0..100).
    Если передан, окна загрузки дробятся на куски по ``DOWNLOAD_CHUNK_DAYS``,
    чтобы прогресс обновлялся равными шагами.
    """
    if period not in PERIODS:
        raise ValueError(f"Неизвестный таймфрейм: {period}")
    if start >= end:
        raise ValueError("Дата начала должна быть раньше даты окончания")
    request_period = "1min" if period in RESAMPLE_FROM_1MIN else PERIODS[period]

    last = storage.last_candle_time(ticker, period)
    first = storage.first_candle_time(ticker, period)
    ranges = _fetch_ranges(start, end, period, last, first, use_cache)

    if progress is not None:
        chunk_days = DOWNLOAD_CHUNK_DAYS.get(period, 31)
        windows = [w for rng in ranges for w in _iter_windows(*rng, chunk_days)]
    else:
        windows = ranges

    new_rows: list[dict] = []
    total = len(windows)
    last_pct = -1
    for i, (win_start, win_end) in enumerate(windows, start=1):
        _ensure_login()
        rows = _fetch_raw(ticker, request_period, win_start, win_end)
        logger.info("Загрузка %s %s [%s .. %s) с MOEX — %s строк", ticker, period, win_start, win_end, len(rows))
        new_rows.extend(rows)
        if progress is not None and total:
            pct = round(i * 100 / total)
            if pct != last_pct:
                progress(pct)
                last_pct = pct

    if new_rows:
        df = pd.DataFrame(new_rows)
        if period in RESAMPLE_FROM_1MIN:
            df = _resample_candles(df, RESAMPLE_FROM_1MIN[period])
        added = storage.save_candles(ticker, period, df)
        logger.info("Синхронизировано: добавлено %s свечей %s %s", added, ticker, period)

    out = storage.get_candles(ticker, period, start=start, end=end)
    if out.empty:
        msg = (
            f"MOEX не вернул данных по {ticker} за {start.isoformat()}..{end.isoformat()}. "
            "Проверьте тикер и даты — возможно, бумага делистингована или не торговалась в этот период."
        )
        hint = DELISTED_HINTS.get(ticker.upper())
        if hint:
            msg += f"\n{hint}"
        raise ValueError(msg)
    if progress is not None and last_pct != 100:
        progress(100)
    return normalize_history(out)


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
