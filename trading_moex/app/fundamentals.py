"""Фундаментальные данные: CSV-импорт отчётности и сканирование MOEX ISS.

История (ROE, book value) загружается пользователем вручную через CSV —
надёжнее скрейпинга и не требует внешних лицензируемых источников. Текущая
цена и капитализация берутся из MOEX ISS (бесплатно, без авторизации).
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime

import pandas as pd
import requests

from . import storage

logger = logging.getLogger("moex_trader.fundamentals")

ISS_BASE = "https://iss.moex.com/iss"
ISS_TIMEOUT = 15

# Суммарная капитализация верхней/серединной части рынка для фильтра «высококапитализационные».
DEFAULT_MIN_MARKET_CAP = 10_000_000_000.0  # 10 млрд ₽
DEFAULT_MIN_VOLUME_RUB = 1_000_000.0       # 1 млн ₽ в день


# ── CSV-импорт ──────────────────────────────────────────────────────────────

def parse_fundamentals_csv(content: str | bytes, default_ticker: str | None = None) -> pd.DataFrame:
    """Разобрать CSV с фундаментальной отчётностью.

    Обязательные колонки: ``date`` (YYYY-MM-DD, DD.MM.YYYY или MM/DD/YYYY),
    ``roe`` (%), ``book_value_per_share`` (₽). Опциональные: ``roa, eps,
    equity, net_profit, revenue, ticker``. Индексная колонка ``ticker`` (если
    есть) переопределяет ``default_ticker``.

    Валидация: ROE в диапазоне [-100, 1000], book_value_per_share > 0.
    Возвращает DataFrame с колонками date, roe, book_value_per_share, ...
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    df = pd.read_csv(io.StringIO(content))

    required = {"date", "roe", "book_value_per_share"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"CSV не содержит колонок: {', '.join(sorted(missing))}. Нужны date, roe, book_value_per_share.")

    df["date"] = df["date"].map(_parse_report_date)
    if df["date"].isna().any():
        raise ValueError("Некорректная дата в CSV. Используйте формат YYYY-MM-DD, DD.MM.YYYY или MM/DD/YYYY.")

    for col in ("roe", "book_value_per_share"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad_roe = df["roe"].notna() & ~df["roe"].between(-100, 1000)
    if bad_roe.any():
        raise ValueError("ROE вне диапазона [-100, 1000].")
    bad_bv = df["book_value_per_share"].fillna(0) <= 0
    if bad_bv.any():
        raise ValueError("book_value_per_share должна быть положительной.")

    for col in ("roa", "eps", "equity", "net_profit", "revenue"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        for t in df["ticker"]:
            if t and t != "NAN":
                default_ticker = t
        df = df.drop(columns=["ticker"])
    df["ticker"] = default_ticker.upper().strip() if default_ticker else ""

    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df


def _parse_report_date(value) -> pd.Timestamp | None:
    if isinstance(value, pd.Timestamp):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            continue
    try:  # NaN и т.п.
        return pd.NaT if float(text) != float(text) else None
    except ValueError:
        return None


def import_fundamentals(ticker: str, content: str | bytes) -> int:
    """Разобрать CSV и сохранить в БД. Возвращает число записей."""
    df = parse_fundamentals_csv(content, default_ticker=ticker)
    return storage.save_fundamentals(ticker.upper().strip(), df)


# ── MOEX ISS: текущие цена/капитализация и авто-скан ───────────────────────

def _iss_json(url: str) -> dict:
    resp = requests.get(url, params={"iss.meta": "off"}, timeout=ISS_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_moex_iss_securities(board: str = "TQBR") -> list[dict]:
    """Список бумаг доски (securities + marketdata) с MOEX ISS.

    Возвращает список с ключами: ticker, name, shortname, price, prevprice,
    market_cap, value_today, num_trades, sectype, listlevel, status, issuesize.
    """
    url = f"{ISS_BASE}/engines/stock/markets/shares/boards/{board}/securities.json"
    data = _iss_json(url)

    securities = _block_rows(data.get("securities", {}))
    marketdata = _block_rows(data.get("marketdata", {}))

    out = []
    for sec in securities.values():
        md = marketdata.get(sec.get("SECID", ""), {})
        price = _num(md.get("LAST")) or _num(md.get("CLOSEPRICE")) or _num(sec.get("PREVPRICE"))
        out.append(
            {
                "ticker": sec.get("SECID"),
                "name": sec.get("SECNAME"),
                "shortname": sec.get("SHORTNAME"),
                "price": price,
                "prevprice": _num(sec.get("PREVPRICE")),
                "market_cap": _num(md.get("ISSUECAPITALIZATION")),
                "value_today": _num(md.get("VALTODAY")),
                "num_trades": _num(md.get("NUMTRADES")),
                "sectype": sec.get("SECTYPE"),
                "listlevel": sec.get("LISTLEVEL"),
                "status": sec.get("STATUS"),
                "issuesize": _num(sec.get("ISSUESIZE")),
            }
        )
    return out


def _block_rows(block: dict) -> dict[str, dict]:
    """Конвертирует block {"columns": [...], "data": [[...], ...]} в {SECID: row dict}."""
    columns = block.get("columns", [])
    rows = block.get("data", [])
    result = {}
    for raw in rows:
        if not isinstance(raw, list) or len(raw) < len(columns):
            continue
        row = dict(zip(columns, raw))
        key = row.get("SECID")
        if key:
            result[key] = row
    return result


def _num(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def scan_high_cap(
    min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
    min_volume_rub: float = DEFAULT_MIN_VOLUME_RUB,
    list_levels: list[int] | None = None,
) -> list[dict]:
    """Автоматически отобрать высококапитализационные акции MOEX.

    Фильтр: тип EQIN (обыкновенные акции), капитализация >= min_market_cap,
    оборот дня >= min_volume_rub, уровень листинга в list_levels (None-все).
    Возвращает отсортированный по капитализации (убывание) список.
    """
    levels = set(list_levels) if list_levels else None
    result = []
    for sec in fetch_moex_iss_securities():
        if sec["sectype"] not in ("1", "2", "EQIN"):  # 1 = обыкновенные, 2 = привилегированные акции
            continue
        if sec["market_cap"] is None or sec["market_cap"] < min_market_cap:
            continue
        if sec["value_today"] is not None and sec["value_today"] < min_volume_rub:
            continue
        if levels is not None and sec["listlevel"] and sec["listlevel"] not in levels:
            continue
        result.append(sec)
    result.sort(key=lambda x: x["market_cap"], reverse=True)
    return result


def get_current_price_iss(ticker: str) -> float | None:
    """Текущая цена тикера на основной доске TQBR (LAST или закрытие)."""
    for s in fetch_moex_iss_securities():
        if s["ticker"] == ticker.upper():
            return s["price"]
    return None


# ── Дивиденды SmartLab ──────────────────────────────────────────────────────

SMARTLAB_DIVIDEND_URL = "https://smart-lab.ru/q/{ticker}/dividend/"

# Скрипт/URL SmartLab отдаёт таблицу «Выплаченные дивиденды»: Тикер, дата T-1,
# дата отсечки, Период, дивиденд, Цена акции, Див. доходность. Достаточно
# полей Тикер/дата отсечки/Период/дивиденд.
_SL_DIV_CELLS = {"SBERP": "SBER", "GAZPRAP": "GAZP"}  # префы дублируют ао — игнорируем


def _fetch_smartlab_dividends(ticker: str) -> list[dict]:
    """Скрейп истории дивидендных выплат тикера со smart-lab.ru/q/{t}/dividend/.

    Возвращает [{date (отсечки), dividend (₽/акцию), period}] или пустой список.
    """
    import re

    url = SMARTLAB_DIVIDEND_URL.format(ticker=ticker)
    resp = requests.get(url, timeout=ISS_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        logger.warning("SmartLab дивиденды %s: HTTP %s", ticker, resp.status_code)
        return []

    text = resp.text
    # секция «Выплаченные дивиденды …»: строки <tr><td>SBER</td><td>T-1</td>
    # <td>отсечка</td><td>Период</td><td>дивиденд₽</td>...
    out: list[dict] = []
    in_paid = False
    seen = set()
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", text, re.S):
        cells = [
            re.sub(r"<[^>]*>", "", c).replace("&nbsp;", " ").replace("\xa0", " ").replace("₽", "").strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        ]
        if not cells:
            continue
        if cells[0] and "Выплаченные дивиденды" in " ".join(cells):
            in_paid = True
            continue
        if not in_paid:
            continue
        # stop after this block: next header row after paid table ends
        if cells[0] in ("Тикер",) or (cells[0] and cells[0] == cells[0].title() and len(cells) == 1):
            if cells[0] == "Тикер":
                continue
            in_paid = False
            break
        if len(cells) < 5 or not cells[0]:
            break
        sl_ticker = cells[0]
        sl_ticker = _SL_DIV_CELLS.get(sl_ticker, sl_ticker)
        if sl_ticker != ticker:
            continue
        buy_before = _parse_sl_russian_date(cells[1])  # дата T-1 — последний день покупки
        cutoff = _parse_sl_russian_date(cells[2])      # дата отсечки (реестр)
        div = _parse_rub(cells[4])
        if buy_before is None or cutoff is None or div is None:
            continue
        key = (cutoff.isoformat(), div, cells[3])
        if key in seen:  # префы SBERP/GAZPRAP дублируют ао — берём одну
            continue
        seen.add(key)
        out.append(
            {
                "date": cutoff.isoformat(),
                "buy_before": buy_before.isoformat(),
                "dividend": div,
                "period": key[2],
            }
        )
    return out


def _parse_sl_russian_date(value: str) -> date | None:
    """Парсит даты SmartLab вида DD.MM.YYYY."""
    from datetime import datetime

    value = (value or "").strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_rub(value: str) -> float | None:
    """Парсит сумму вида '37,64' или '37,64 ₽' (запятая как разделитель)."""
    value = (value or "").replace("%", "").strip()
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def load_dividends_smartlab(ticker: str) -> tuple[int, list[dict]]:
    """Загрузить дивиденды со SmartLab в базу (upsert), вернуть (count, rows)."""
    rows = _fetch_smartlab_dividends(ticker)
    if rows:
        import pandas as pd

        df = pd.DataFrame(rows)[["date", "buy_before", "dividend", "period"]].rename(
            columns={"date": "cutoff_date", "dividend": "dividend_per_share"}
        )

        storage.save_dividends(ticker, df)
    return len(rows), rows


# ── Расчёт показателей по загруженной отчётности ───────────────────────────

def _annual_roe_rows(ticker: str) -> list[tuple[str, float | None]]:
    """ROE по календарным годам: для каждого года берём последнюю строку отчётности."""
    df = storage.load_fundamentals(ticker)
    if df.empty:
        return []
    df = df.copy()
    df["year"] = df["date"].str[:4]
    out = []
    for year, group in df.groupby("year"):
        latest = group.sort_values("date").iloc[-1]
        roe = latest.get("roe")
        out.append((year, _float_or_none(roe)))
    return out


def _float_or_none(value) -> float | None:
    try:
        if value is None or (isinstance(value, float) and value != value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def get_avg_roe(ticker: str, years: int = 10) -> float | None:
    """Среднее арифметическое годовых ROE за ``years`` последних лет.

    None, если данных меньше половины запрошенного периода (консервативно).
    """
    rows = _annual_roe_rows(ticker)
    rows = [(y, r) for y, r in rows if r is not None]
    rows = rows[-years:]
    if len(rows) < max(years // 2, 1):
        return None
    return round(sum(r for _, r in rows) / len(rows), 2)


def get_min_roe(ticker: str, years: int = 10) -> float | None:
    """Минимальный годовой ROE за период (None, если данных нет)."""
    rows = [(y, r) for y, r in _annual_roe_rows(ticker) if r is not None]
    rows = rows[-years:]
    if not rows:
        return None
    return min(r for _, r in rows)


def get_latest_fundamentals(ticker: str) -> dict | None:
    """Последняя строка отчётности: {date, roe, book_value_per_share, ...}."""
    df = storage.load_fundamentals(ticker)
    if df.empty:
        return None
    return df.iloc[-1].to_dict()


def get_pb_ratio(ticker: str) -> float | None:
    """P/B = текущая цена (ISS) / последняя book_value_per_share."""
    latest = get_latest_fundamentals(ticker)
    if latest is None or not latest.get("book_value_per_share"):
        return None
    bvps = float(latest["book_value_per_share"])
    price = get_current_price_iss(ticker)
    if not price or bvps <= 0:
        return None
    return round(price / bvps, 3)


def get_fundamentals_timeseries(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Временной ряд ROE/BV на каждый календарный день в [start, end].

    Квартальные данные расширяются вперёд (forward-fill): до следующей строки
    отчётности действует последнее известное значение. Используются все строки
    отчётности (включая более ранние, чем start), чтобы начало интервала было
    заполнено корректно.
    """
    df = storage.load_fundamentals(ticker)
    if df.empty:
        return df
    df = df[df["date"] <= end.isoformat()]
    ds = pd.date_range(start=start, end=end, freq="D")
    out = pd.DataFrame(index=ds)
    out["roe"] = pd.NA
    out["book_value_per_share"] = pd.NA
    for _, row in df.iterrows():
        out.loc[row["date"]:, "roe"] = row["roe"]
        out.loc[row["date"]:, "book_value_per_share"] = row["book_value_per_share"]
    if not df.empty:
        out.loc[ds[0], ["roe", "book_value_per_share"]] = df.iloc[0][["roe", "book_value_per_share"]].to_dict()
    return out.ffill().reset_index().rename(columns={"index": "date"})


def prepare_fundamentals_series(ticker: str, start: date, end: date, years: int = 10) -> pd.DataFrame:
    """Ежедневный ряд для бэктеста: roe, book_value_per_share, avg_roe, min_roe.

    ``avg_roe`` — среднее по последним значениям ROE за ``years`` календарных
    лет (по одному значению на год); ``min_roe`` — минимум за тот же период.
    None/NaN, если данных недостаточно — стратегия такой тикер не берёт.
    """
    df = storage.load_fundamentals(ticker)
    if df.empty:
        return pd.DataFrame()
    df = df[df["date"] <= end.isoformat()]

    yearly: dict[str, float | None] = {}
    for year, group in df.groupby(df["date"].str[:4]):
        latest = group.sort_values("date").iloc[-1]["roe"]
        yearly[year] = _float_or_none(latest)

    ds = pd.date_range(start=start, end=end, freq="D")
    out = pd.DataFrame(index=ds)
    out["roe"] = pd.NA
    out["book_value_per_share"] = pd.NA
    for _, row in df.iterrows():
        out.loc[row["date"]:, "roe"] = row["roe"]
        out.loc[row["date"]:, "book_value_per_share"] = row["book_value_per_share"]
    out = out.ffill()

    avg, mn = [], []
    for ts in ds:
        window = [yearly.get(str(y)) for y in range(ts.year - years + 1, ts.year + 1)]
        valid = [v for v in window if v is not None]
        avg.append(round(sum(valid) / len(valid), 2) if valid else None)
        mn.append(min(valid) if valid else None)
    out["avg_roe"] = avg
    out["min_roe"] = mn
    return out.reset_index().rename(columns={"index": "date"})