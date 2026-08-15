"""Хранение результатов бэктестов и состояния live-сессии в SQLite.

Бэктест выполняется в рабочем потоке, поэтому каждая операция открывает
свежее соединение (простой и потокобезопасный подход).
"""

import json
import sqlite3
import time
from datetime import datetime, timezone

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
    return [dict(r) for r in rows]


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
