"""Causal statistics for stored T-Bank trades and order-book snapshots."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


def load_orderflow_bars(db_path: str | Path, ticker: str, period: str = "15min") -> pd.DataFrame:
    """Aggregate raw events into bars; missing order-flow remains NaN, not zero."""
    if period != "15min":
        raise ValueError("only 15min bars are currently supported")
    with sqlite3.connect(Path(db_path).expanduser()) as connection:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        trades = pd.read_sql_query(
            "SELECT event_ts, quantity, aggressor FROM adaptive_trades WHERE ticker = ? ORDER BY event_ts",
            connection, params=(ticker.upper(),),
        ) if "adaptive_trades" in tables else pd.DataFrame()
        books = pd.read_sql_query(
            "SELECT event_ts, payload FROM adaptive_books WHERE ticker = ? ORDER BY event_ts",
            connection, params=(ticker.upper(),),
        ) if "adaptive_books" in tables else pd.DataFrame()
    if trades.empty and books.empty:
        return pd.DataFrame(columns=["timestamp", "buy_volume", "sell_volume", "known_volume", "delta", "flow_coverage", "book_imbalance", "book_spread"])
    for frame in (trades, books):
        if not frame.empty:
            frame["event_ts"] = pd.to_datetime(frame["event_ts"], utc=True)
            frame["bar"] = frame["event_ts"].dt.floor(period)
    if trades.empty:
        flow = pd.DataFrame()
    else:
        trades["buy_volume"] = trades["quantity"].where(trades["aggressor"].eq("BUY"), 0.0)
        trades["sell_volume"] = trades["quantity"].where(trades["aggressor"].eq("SELL"), 0.0)
        flow = trades.groupby("bar").agg(
            buy_volume=("buy_volume", "sum"), sell_volume=("sell_volume", "sum"),
            known_volume=("quantity", lambda values: float(values[trades.loc[values.index, "aggressor"].isin(["BUY", "SELL"])].sum())),
        )
        flow["delta"] = flow["buy_volume"] - flow["sell_volume"]
    if books.empty:
        book = pd.DataFrame()
    else:
        def book_values(payload: str) -> tuple[float, float]:
            import json
            data = json.loads(payload)
            bids, asks = data["bids"], data["asks"]
            bid_size = sum(float(level[1]) for level in bids)
            ask_size = sum(float(level[1]) for level in asks)
            total = bid_size + ask_size
            imbalance = (bid_size - ask_size) / total if total else np.nan
            spread = (float(asks[0][0]) - float(bids[0][0])) / ((float(asks[0][0]) + float(bids[0][0])) / 2)
            return imbalance, spread
        values = books["payload"].map(book_values)
        books["book_imbalance"] = values.map(lambda value: value[0])
        books["book_spread"] = values.map(lambda value: value[1])
        book = books.groupby("bar").agg(book_imbalance=("book_imbalance", "last"), book_spread=("book_spread", "last"))
    result = flow.join(book, how="outer").sort_index().reset_index(names="timestamp")
    if "known_volume" not in result:
        result["known_volume"] = np.nan
    result["flow_coverage"] = np.nan
    result["delta_ratio"] = result["delta"].div(result["known_volume"].replace(0, np.nan))
    return result


def evaluate_orderflow_scenarios(
    bars: pd.DataFrame,
    candles: pd.DataFrame,
    *,
    min_coverage: float = 0.80,
    delta_threshold: float = 0.10,
    book_threshold: float = 0.20,
    horizon: int = 4,
) -> pd.DataFrame:
    """Evaluate fixed continuation, exhaustion, and conflict scenarios causally."""
    required = {"timestamp", "close", "volume"}
    if not required.issubset(candles.columns):
        raise ValueError(f"candles missing: {sorted(required - set(candles.columns))}")
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    left = bars.copy()
    right = candles[["timestamp", "close", "volume"]].copy()
    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True)
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True)
    merged = left.merge(right, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    for column in ("known_volume", "delta", "delta_ratio", "book_imbalance", "book_spread"):
        if column not in merged:
            merged[column] = np.nan
    merged["flow_coverage"] = merged["known_volume"].div(merged["volume"].replace(0, np.nan))
    merged["flow_ready"] = merged["flow_coverage"].ge(min_coverage)
    merged["flow_buy"] = merged["flow_ready"] & merged["delta_ratio"].ge(delta_threshold)
    merged["flow_sell"] = merged["flow_ready"] & merged["delta_ratio"].le(-delta_threshold)
    merged["book_buy"] = merged["book_imbalance"].ge(book_threshold)
    merged["book_sell"] = merged["book_imbalance"].le(-book_threshold)
    merged["scenario"] = "NONE"
    merged.loc[merged["flow_buy"] & merged["book_buy"], "scenario"] = "CONTINUATION_LONG"
    merged.loc[merged["flow_sell"] & merged["book_sell"], "scenario"] = "CONTINUATION_SHORT"
    merged.loc[merged["flow_buy"] & merged["book_sell"], "scenario"] = "CONFLICT_BUY_FLOW_SELL_BOOK"
    merged.loc[merged["flow_sell"] & merged["book_buy"], "scenario"] = "CONFLICT_SELL_FLOW_BUY_BOOK"
    merged["forward_return"] = merged["close"].shift(-horizon).div(merged["close"]) - 1.0
    return merged.loc[merged["scenario"].ne("NONE") & merged["forward_return"].notna()].copy()


def summarize_scenarios(events: pd.DataFrame) -> pd.DataFrame:
    """Return count, mean return, win rate, and Wilson 95% interval per scenario."""
    rows = []
    for scenario, group in events.groupby("scenario", sort=True):
        returns = group["forward_return"].astype(float)
        n = len(returns)
        wins = int((returns > 0).sum())
        z = 1.959963984540054
        denominator = 1 + z * z / n
        center = (wins / n + z * z / (2 * n)) / denominator
        margin = z * np.sqrt((wins / n) * (1 - wins / n) / n + z * z / (4 * n * n)) / denominator
        rows.append({"scenario": scenario, "samples": n, "mean_return": returns.mean(), "win_rate": wins / n, "ci_low": max(0.0, center - margin), "ci_high": min(1.0, center + margin)})
    return pd.DataFrame(rows, columns=["scenario", "samples", "mean_return", "win_rate", "ci_low", "ci_high"])
