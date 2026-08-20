"""Хранение результатов бэктестов и состояния live-сессии в SQLite.

Бэктест выполняется в рабочем потоке, поэтому каждая операция открывает
свежее соединение (простой и потокобезопасный подход).
"""

import json
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from . import config


def _connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS backtest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                ticker TEXT NOT NULL,
                period TEXT NOT NULL,
                strategy TEXT NOT NULL,
                params TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                error TEXT,
                result TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS live_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                added_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                ticker TEXT NOT NULL,
                period TEXT NOT NULL,
                begin TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (ticker, period, begin)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fundamentals (
                ticker TEXT NOT NULL,
                report_date TEXT NOT NULL,
                roe REAL,
                roa REAL,
                book_value_per_share REAL,
                eps REAL,
                equity REAL,
                net_profit REAL,
                revenue REAL,
                source TEXT DEFAULT 'manual',
                PRIMARY KEY (ticker, report_date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dividends (
                ticker TEXT NOT NULL,
                cutoff_date TEXT NOT NULL,
                buy_before TEXT,
                period TEXT,
                dividend_per_share REAL,
                source TEXT DEFAULT 'smartlab',
                PRIMARY KEY (ticker, cutoff_date)
            )
            """
        )
        # graceful-миграция: старые таблицы dividends могли не иметь buy_before
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(dividends)").fetchall()]
            if cols and "buy_before" not in cols:
                conn.execute("ALTER TABLE dividends ADD COLUMN buy_before TEXT")
        except sqlite3.Error:  # pragma: no cover — таблица может быть недоступна
            pass


def create_run(ticker: str, period: str, strategy: str, params: dict, start_date: str, end_date: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO backtest_runs (created_at, ticker, period, strategy, params, start_date, end_date)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                ticker,
                period,
                strategy,
                json.dumps(params, ensure_ascii=False),
                start_date,
                end_date,
            ),
        )
        return cur.lastrowid


def finish_run(run_id: int, result: dict | None, error: str | None = None) -> None:
    with _connect() as conn:
        status = "error" if error else "done"
        conn.execute(
            "UPDATE backtest_runs SET status = ?, error = ?, result = ? WHERE id = ?",
            (status, error, json.dumps(result, ensure_ascii=False) if result else None, run_id),
        )


def get_run(run_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM backtest_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["params"] = json.loads(item["params"]) if item["params"] else {}
    item["result"] = json.loads(item["result"]) if item["result"] else None
    return item


def list_runs(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM backtest_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        item["params"] = json.loads(item["params"]) if item["params"] else {}
        item["result"] = json.loads(item["result"]) if item["result"] else None
        items.append(item)
    return items


def get_live_value(key: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM live_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_live_value(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO live_state (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_setting(key: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, datetime.now(timezone.utc).isoformat()),
        )


def list_watchlist() -> list[str]:
    """Тикеры для live-торговли, отсортированные по времени добавления."""
    with _connect() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist ORDER BY added_at").fetchall()
    return [r["ticker"] for r in rows]


def add_watchlist(ticker: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at) VALUES (?, ?)",
            (ticker, datetime.now(timezone.utc).isoformat()),
        )


def remove_watchlist(ticker: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))


# ── База данных свечей ───────────────────────────────────────────────────────

def save_candles(ticker: str, period: str, df) -> int:
    """Upsert свечей в таблицу ``candles`` (первичный ключ ticker,period,begin).

    ``df`` — DataFrame с колонками begin, open, high, low, close, volume.
    Возвращает количество записанных строк.
    """
    import pandas as pd

    rows = []
    for _, r in df.iterrows():
        begin = r["begin"]
        if isinstance(begin, pd.Timestamp):
            begin = begin.strftime("%Y-%m-%d %H:%M:%S")
        else:
            begin = str(begin)
        rows.append(
            (
                ticker,
                period,
                begin,
                float(r["open"]),
                float(r["high"]),
                float(r["low"]),
                float(r["close"]),
                float(r["volume"]),
            )
        )
    if not rows:
        return 0
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO candles (ticker, period, begin, open, high, low, close, volume)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)


def get_candles(ticker: str, period: str, start: date | None = None, end: date | None = None):
    """Свечи из базы в полуинтервале [start, end), отсортированные по begin.

    ``end`` трактуется включительно как дата — запрос включает весь день ``end``.
    """
    import pandas as pd

    query = "SELECT begin, open, high, low, close, volume FROM candles WHERE ticker = ? AND period = ?"
    params: list = [ticker, period]
    if start is not None:
        query += " AND begin >= ?"
        params.append(start.isoformat())
    if end is not None:
        query += " AND begin < ?"
        params.append((end + timedelta(days=1)).isoformat())
    query += " ORDER BY begin"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    if not rows:
        return pd.DataFrame(columns=["begin", "open", "high", "low", "close", "volume"])
    return pd.DataFrame([dict(r) for r in rows])


def last_candle_time(ticker: str, period: str) -> str | None:
    """Метка (begin) последней сохранённой свечи или None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(begin) AS v FROM candles WHERE ticker = ? AND period = ?", (ticker, period)
        ).fetchone()
    return row["v"] if row else None


def first_candle_time(ticker: str, period: str) -> str | None:
    """Метка (begin) первой сохранённой свечи или None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT MIN(begin) AS v FROM candles WHERE ticker = ? AND period = ?", (ticker, period)
        ).fetchone()
    return row["v"] if row else None


def candle_count(ticker: str, period: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM candles WHERE ticker = ? AND period = ?", (ticker, period)
        ).fetchone()
    return int(row["n"]) if row else 0


# ── Фундаментальные данные (ROE, book value и пр.) ──────────────────────────

def save_fundamentals(ticker: str, df) -> int:
    """Upsert строк фундаментальной отчётности в таблицу ``fundamentals``.

    ``df`` — DataFrame с колонкой ``date`` (YYYY-MM-DD) и опциональными
    ``roe, roa, book_value_per_share, eps, equity, net_profit, revenue``.
    Возвращает количество записанных строк.
    """
    import pandas as pd

    rows = []
    for _, r in df.iterrows():
        date_val = r["date"]
        if isinstance(date_val, pd.Timestamp):
            date_val = date_val.strftime("%Y-%m-%d")
        else:
            date_val = str(date_val)
        rows.append(
            (
                ticker,
                date_val,
                _maybe_float(r.get("roe")),
                _maybe_float(r.get("roa")),
                _maybe_float(r.get("book_value_per_share")),
                _maybe_float(r.get("eps")),
                _maybe_float(r.get("equity")),
                _maybe_float(r.get("net_profit")),
                _maybe_float(r.get("revenue")),
            )
        )
    if not rows:
        return 0
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO fundamentals"
            " (ticker, report_date, roe, roa, book_value_per_share, eps, equity, net_profit, revenue)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)


def load_fundamentals(ticker: str, start: date | None = None, end: date | None = None):
    """Фундаментальная отчётность тикера в полуинтервале [start, end), по report_date.

    Возвращает DataFrame с колонками date, roe, roa, book_value_per_share, eps,
    equity, net_profit, revenue, source.
    """
    import pandas as pd

    query = "SELECT report_date, roe, roa, book_value_per_share, eps, equity, net_profit, revenue, source"
    query += " FROM fundamentals WHERE ticker = ?"
    params: list = [ticker]
    if start is not None:
        query += " AND report_date >= ?"
        params.append(start.isoformat())
    if end is not None:
        query += " AND report_date < ?"
        params.append((end + timedelta(days=1)).isoformat())
    query += " ORDER BY report_date"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    if not rows:
        return pd.DataFrame(
            columns=["date", "roe", "roa", "book_value_per_share", "eps", "equity", "net_profit", "revenue", "source"]
        )
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.rename(columns={"report_date": "date"})
    return df


def list_tickers_with_fundamentals() -> list[str]:
    """Тикеры, для которых в базе есть хотя бы одна строка фундаментальной отчётности."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT ticker FROM fundamentals ORDER BY ticker").fetchall()
    return [r["ticker"] for r in rows]


def fundamentals_stats(ticker: str) -> dict:
    """Статистика загруженной отчётности: число строк и диапазон дат."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, MIN(report_date) AS mn, MAX(report_date) AS mx"
            " FROM fundamentals WHERE ticker = ?",
            (ticker,),
        ).fetchone()
    if row is None or not row["n"]:
        return {"ticker": ticker, "count": 0, "min_date": None, "max_date": None}
    return {"ticker": ticker, "count": int(row["n"]), "min_date": row["mn"], "max_date": row["mx"]}


def delete_fundamentals(ticker: str) -> int:
    """Удалить все строки отчётности тикера. Возвращает число удалённых строк."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM fundamentals WHERE ticker = ?", (ticker,))
    return cur.rowcount


def _maybe_float(value) -> float | None:
    try:
        if value is None or value != value:  # None или NaN
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


# ── Дивиденды ───────────────────────────────────────────────────────────────

def save_dividends(ticker: str, df) -> int:
    """Upsert дивидендных выплат в таблицу ``dividends``.

    ``df`` — DataFrame с колонками ``cutoff_date`` (YYYY-MM-DD), ``dividend_per_share``
    и опциональными ``buy_before``, ``period``. Возвращает количество записанных строк.
    """
    import pandas as pd

    rows = []
    for _, r in df.iterrows():
        cd = r["cutoff_date"]
        if isinstance(cd, pd.Timestamp):
            cd = cd.strftime("%Y-%m-%d")
        else:
            cd = str(cd)
        bb = r.get("buy_before")
        if bb is not None:
            bb = bb.strftime("%Y-%m-%d") if isinstance(bb, pd.Timestamp) else str(bb)
        rows.append(
            (
                ticker,
                cd,
                bb,
                str(r.get("period")) if r.get("period") is not None else None,
                _maybe_float(r.get("dividend_per_share")),
            )
        )
    if not rows:
        return 0
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO dividends (ticker, cutoff_date, buy_before, period, dividend_per_share)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    return len(rows)


def load_dividends(ticker: str, start: date | None = None, end: date | None = None):
    """Дивиденды тикера в [start, end), отсортированные по cutoff_date.

    Возвращает DataFrame с колонками date (отсечки), buy_before, period, dividend.
    """
    import pandas as pd

    query = "SELECT cutoff_date, buy_before, period, dividend_per_share FROM dividends WHERE ticker = ?"
    params: list = [ticker]
    if start is not None:
        query += " AND cutoff_date >= ?"
        params.append(start.isoformat())
    if end is not None:
        query += " AND cutoff_date < ?"
        params.append((end + timedelta(days=1)).isoformat())
    query += " ORDER BY cutoff_date"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    if not rows:
        return pd.DataFrame(columns=["date", "buy_before", "period", "dividend"])
    df = pd.DataFrame([dict(r) for r in rows])
    return df.rename(columns={"cutoff_date": "date", "dividend_per_share": "dividend"})


def list_tickers_with_dividends() -> list[str]:
    """Тикеры, для которых в базе есть хотя бы одна выплата."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT ticker FROM dividends ORDER BY ticker").fetchall()
    return [r["ticker"] for r in rows]


def delete_dividends(ticker: str) -> int:
    """Удалить все выплаты по тикеру. Возвращает число удалённых строк."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM dividends WHERE ticker = ?", (ticker,))
    return cur.rowcount
