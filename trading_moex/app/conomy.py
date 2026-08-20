"""Авто-загрузка фундаментальной отчётности с conomy.ru.

conomy.ru построен на Nuxt SSR: финансовые данные находятся в JS-объекте
``window.__NUXT__``, где имена табличных строк — переменные (``name:h``),
а часть чисел — литералы. Это хрупкое, поэтому оборачивается в аккуратный
парсер с понятными ошибками; ручной CSV-импорт остаётся как основной путь.

Источники данных:
- ``/investments/issuers/{slug}/financial-statements/{?show=income}`` — отчёт
  о прибылях и убытках,
- ``/investments/issuers/{slug}/financial-statements/{?show=balance}`` —
  бухгалтерский баланс (собственный капитал),
- ``/investments/issuers/{slug}`` — число акций (для book_value_per_share).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger("moex_trader.conomy")

CONOMY_BASE = "https://conomy.ru"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
TIMEOUT = 20

# Строки отчётности, которые нужны для расчёта ROE и book value на акцию.
_INCOME_ROWS = ("Чистая прибыль", "Прибыль за год", "Прибыль за отчетный период", "Чистая прибыль (убыток)")
# Собственный капитал встречается в разных формулировках: банки —
# «Итого собственных средств…»; нефинансовые компании — «Итого капитал» /
# «Итого акционерный капитал…». Берём строку с характерными словами.
_BALANCE_ROWS = ("Итого собственных средств", "Итого акционерный капитал", "Итого капитал")


class ConomyError(Exception):
    """Ошибка получения/разбора данных conomy.ru."""


def _get(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _parse_nuxt_payload(html: str) -> dict[str, Any]:
    """Декодировать ``window.__NUXT__`` в словарь.

    Payload имеет вид ``(function(a,b,c,...){return {...}}(args...))``.
    Излагаем параметры функции по порядку, сопоставляем имя переменной значению
    из хвостового списка и подставляем в литерал. Структура после декодирования
    похожа на JSON (ключи без кавычек) — приводим к JSON и парсим.
    """
    m = re.search(r"window\.__NUXT__=\s*\(function\(([^)]*)\)\{(.*)\}\(([^;]*)\)\);", html, re.S)
    if not m:
        raise ConomyError("Не найден payload __NUXT__ на странице conomy.ru")
    params_src, body, args_src = m.group(1), m.group(2), m.group(3)

    params = [p.strip() for p in params_src.split(",") if p.strip()]

    args = _split_args(args_src)
    if len(params) != len(args):
        raise ConomyError(f"Декодирование conomy.ru: параметров {len(params)}, значений {len(args)}")

    resolved = dict(zip(params, args))
    body_out = _substitute_identifiers(body, resolved)

    # Теперь объект почти JSON: ключи без кавычек, undefined/NaN значения.
    body_out = _js_object_to_json(body_out)
    try:
        return json.loads(body_out)
    except ValueError as exc:
        raise ConomyError(f"Не удалось распарсить данные conomy.ru: {exc}") from exc


def _split_args(src: str) -> list:
    """Разбить список аргументов на верхнем уровне, учитывая кавычки и скобки."""
    parts: list[str] = []
    depth = 0
    buf = []
    i = 0
    quote: str | None = None
    while i < len(src):
        ch = src[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(src):
                buf.append(src[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        parts.append("".join(buf).strip())
    out = []
    for p in parts:
        out.append(_literal_value(p))
    return out


def _literal_value(raw: str):
    raw = raw.strip()
    if not raw:
        return None
    if raw in ("null", "undefined"):
        return None
    if raw in ("true",):
        return True
    if raw in ("false",):
        return False
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return raw[1:-1]
    try:
        return float(raw) if "." in raw else int(raw)
    except ValueError:
        return raw


def _substitute_identifiers(body: str, resolved: dict[str, Any]) -> str:
    """Заменить идентификаторы-переменные на их значения.

    Идём вручную посимвольно, чтобы односимвольные имена (``a``…``z``) не
    задевали содержимое строковых литералов: внутри строки ничего не трогаем.
    Вне строк съедаем целые идентификаторы целиком и заменяем только те,
    что совпадают с именами параметров payload'а.
    """
    body = body.lstrip()
    if body.startswith("return"):
        body = body[len("return"):].lstrip()
    out: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch in ("'", '"'):
            out.append(ch)
            i += 1
            while i < n:
                c = body[i]
                out.append(c)
                if c == "\\" and i + 1 < n:
                    out.append(body[i + 1])
                    i += 2
                    continue
                if c == ch:
                    i += 1
                    break
                i += 1
            continue
        m = re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*", body[i:])
        if m:
            token = m.group(0)
            i += len(token)
            if token in resolved:
                out.append(json.dumps(resolved[token], ensure_ascii=False))
            else:
                out.append(token)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _js_object_to_json(text: str) -> str:
    """Инфраструктурные правки JS-литерала → JSON.

    - ключи без кавычек ``key:`` → ``"key":``
    - ``undefined`` → ``null``, ``NaN`` → ``null``
    """
    text = re.sub(r"([{,])\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:", r'\1"\2":', text)
    text = re.sub(r":\s*undefined\b", ": null", text)
    text = re.sub(r":\s*NaN\b", ": null", text)
    text = re.sub(r"(?<=[:,[{])\s*\.\d+", lambda m: "0" + m.group(0).strip(), text)
    return text


def issuer_slug_for_ticker(ticker: str) -> str:
    """Слаг эмитента на conomy.ru по тикеру.

    Каталог эмитентов сгруппирован по русской первой букве имени компании
    (``/investments/issuers?letter=с`` → ПАО СБЕРБАНК). Перебираем буквы,
    пока не встретим нужный тикер в поле ``ticker:[...]``.
    """
    ticker = ticker.upper()
    letters = "абвгдеёжзийклмнопрстуфхцчшщыэюяabcdefghijklmnopqrstuvwxyz"
    seen: set[str] = set()
    for ch in letters:
        if ch in seen:
            continue
        seen.add(ch)
        html = _get(f"{CONOMY_BASE}/investments/issuers?letter={ch}")
        try:
            payload = _parse_nuxt_payload(html)
        except ConomyError:
            continue
        for issuer in payload.get("data") and payload["data"][0].get("issuers") or []:
            codes = [str(c) for c in issuer.get("ticker") or [] if c]
            if ticker in codes:
                return str(issuer.get("slug") or "")
    raise ConomyError(f"Тикер {ticker} не найден в каталоге эмитентов conomy.ru")


def fetch_statements(ticker: str, show: str, range_years: int = 10) -> dict[str, Any]:
    """Вернуть декодированный payload страницы отчётности."""
    slug = issuer_slug_for_ticker(ticker)
    url = (
        f"{CONOMY_BASE}/investments/issuers/{slug}/financial-statements/"
        f"?type=msfo&period=year&range={range_years}&show={show}"
    )
    html = _get(url)
    return _parse_nuxt_payload(html)


def _extract_table_rows(payload: dict[str, Any]) -> dict[str, list[str]]:
    """Имя строки → значения по годам (таблица_data отчётности)."""
    data0 = payload.get("data") or [{}]
    statements = (data0[0] or {}).get("statements") or {}
    data = statements.get("data") or []
    rows: dict[str, list[str]] = {}
    for table in data:
        for row in table.get("table_data") or []:
            name = row.get("name")
            if not name:
                continue
            values = row.get("values") or []
            rows[str(name)] = [str(v) if v is not None else "" for v in values]
    return rows


def _pick_equity_series(rows: dict[str, list[str]]) -> list[str] | None:
    """Выбрать строку собственного капитала из баланса.

    Предпочитаем более специфичную формулировку: сначала строки для
    акционеров (банковская), затем общий итог капитала.
    """
    matches = [
        (name, values)
        for name, values in rows.items()
        if any(k in name for k in _BALANCE_ROWS)
    ]
    if not matches:
        return None
    matches.sort(key=lambda nv: -len(nv[0]))
    return matches[0][1]


def _clean_num(value: str) -> float | None:
    try:
        f = float(value)
        return f if f == f else None  # NaN
    except (TypeError, ValueError):
        return None


def build_fundamentals(ticker: str, range_years: int = 10) -> pd.DataFrame:
    """Собрать DataFrame(date, roe, book_value_per_share, equity, net_profit).

    ROE = чистая прибыль года / собственный капитал на конец года * 100.
    book_value_per_share = собственный капитал / число акций.
    """
    income = fetch_statements(ticker, "income", range_years)
    balance = fetch_statements(ticker, "balance", range_years)

    inc_rows = _extract_table_rows(income)
    bal_rows = _extract_table_rows(balance)

    net_profit_series = next(
        (v for name, v in inc_rows.items() if any(k in name for k in _INCOME_ROWS)),
        None,
    )
    equity_series = _pick_equity_series(bal_rows)
    years: list[str] = []
    for name, values in inc_rows.items():
        if name == "Период":
            years = values
            break

    if net_profit_series is None:
        raise ConomyError("В отчёте conomy.ru не найдена строка «Чистая прибыль»")
    if equity_series is None:
        raise ConomyError("В балансе conomy.ru не найден собственный капитал")

    shares = _share_count(ticker)

    n = min(len(years), len(net_profit_series), len(equity_series))
    if n == 0:
        raise ConomyError("Пустые данные отчётности conomy.ru")

    rows = []
    for k in range(n):
        year_str = years[k].replace(" г.", "").strip()
        try:
            year = int(year_str[:4])
        except ValueError:
            continue
        net_profit = _clean_num(net_profit_series[k])
        equity = _clean_num(equity_series[k])
        if net_profit is None or equity is None or equity <= 0:
            continue
        roe = net_profit / equity * 100.0
        bvps = equity / shares if shares else None
        if bvps is None or bvps <= 0:
            continue
        rows.append(
            {
                "date": f"{year}-12-31",
                "roe": round(roe, 2),
                "book_value_per_share": round(bvps, 2),
                "equity": round(equity, 2),
                "net_profit": round(net_profit, 2),
            }
        )

    if not rows:
        raise ConomyError("Не удалось посчитать ROE/BVPS из данных conomy.ru")

    df = pd.DataFrame(rows).sort_values("date").drop_duplicates("date", keep="last")
    return df.reset_index(drop=True)


def _share_count(ticker: str) -> float | None:
    """Число акций (АОИ) со страницы эмитента."""
    slug = issuer_slug_for_ticker(ticker)
    html = _get(f"{CONOMY_BASE}/investments/issuers/{slug}")
    m = re.search(r"amount_of_shares:\{type:\"АОИ\",value:([0-9]+)\}", html)
    if m:
        return float(m.group(1))
    m = re.search(r"amount_of_shares:\{type:\"АОИ\",value:\s*([0-9.]+)\s*\}", html)
    return float(m.group(1)) if m else None