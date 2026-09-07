"""Event filter: skip trades near important calendar events (dividends, earnings).

Причина: отсечка дивидендов (ex-div) вызывает ценовой гэп вниз на размер
дивиденда. Шорт рядом с отсечкой может выигрывать на гэпе, лонг — терять.
Фильтр исключает сделки в окне ±N дней от отсечки (или предупреждает).

Данные: таблица ``dividends`` в БД (cutoff_date, buy_before, dividend_per_share).

Usage::

    from app.event_filter import load_dividend_events, in_event_window

    events = load_dividend_events("SBER", db_path)
    mask = in_event_window(ltf_index, events, pre_days=2, post_days=2)
    # mask[i] = True если бар i в запретном окне
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def load_dividend_events(
    ticker: str,
    db_path: str | Path,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    """Загрузить отсечки дивидендов для тикера из БД.

    Возвращает DataFrame с колонками ``cutoff`` (datetime), ``buy_before``
    (datetime), ``dividend`` (float, руб./акцию). Отсортировано по cutoff.
    """
    con = sqlite3.connect(str(db_path))
    query = "SELECT cutoff_date, buy_before, dividend_per_share FROM dividends WHERE ticker = ?"
    params: list = [ticker]
    if start is not None:
        query += " AND cutoff_date >= ?"
        params.append(start.isoformat())
    if end is not None:
        query += " AND cutoff_date < ?"
        params.append((end + timedelta(days=1)).isoformat())
    query += " ORDER BY cutoff_date"
    rows = con.execute(query, params).fetchall()
    con.close()
    if not rows:
        return pd.DataFrame(columns=["cutoff", "buy_before", "dividend"])
    records = []
    for cutoff, buy_before, div in rows:
        records.append({
            "cutoff": pd.Timestamp(cutoff),
            "buy_before": pd.Timestamp(buy_before) if buy_before else pd.Timestamp(cutoff) - pd.Timedelta(days=1),
            "dividend": float(div) if div else 0.0,
        })
    return pd.DataFrame(records)


def in_event_window(
    ltf_index: pd.DatetimeIndex,
    events: pd.DataFrame,
    pre_days: int = 2,
    post_days: int = 2,
) -> pd.Series:
    """Причинная разметка: True если бар ``ltf_index[i]`` в окне ±N дней от отсечки.

    Окно = [cutoff - pre_days, cutoff + post_days] (включительно).
    Для шортов: можно не исключать (гэп вниз = выигрыш шорта).
    Для лонгов: исключать (гэп вниз = убыток лонга).
    """
    if events.empty:
        return pd.Series(False, index=ltf_index)
    mask = np.zeros(len(ltf_index), dtype=bool)
    for _, ev in events.iterrows():
        cutoff = ev["cutoff"]
        window_start = cutoff - pd.Timedelta(days=pre_days)
        window_end = cutoff + pd.Timedelta(days=post_days)
        in_window = (ltf_index >= window_start) & (ltf_index <= window_end)
        if hasattr(in_window, "values"):
            in_window = in_window.values
        mask |= in_window
    return pd.Series(mask, index=ltf_index)


def load_earnings_events(
    ticker: str,
    db_path: str | Path,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    """Загрузить даты отчётности (fundamentals.report_date).

    ⚠️ Качество данных смешанное: report_date часто = конец периода, а не
    дата публикации. Использовать с осторожностью. Рекомендация: только
    дивиденды для автоматического фильтра.
    """
    con = sqlite3.connect(str(db_path))
    query = "SELECT report_date FROM fundamentals WHERE ticker = ?"
    params: list = [ticker]
    if start is not None:
        query += " AND report_date >= ?"
        params.append(start.isoformat())
    if end is not None:
        query += " AND report_date < ?"
        params.append((end + timedelta(days=1)).isoformat())
    query += " ORDER BY report_date"
    rows = con.execute(query, params).fetchall()
    con.close()
    if not rows:
        return pd.DataFrame(columns=["cutoff", "buy_before", "dividend"])
    records = []
    for (rd,) in rows:
        ts = pd.Timestamp(rd)
        records.append({
            "cutoff": ts,
            "buy_before": ts - pd.Timedelta(days=1),
            "dividend": 0.0,
        })
    return pd.DataFrame(records)
