"""Reproducible research helpers for the support/resistance strategy.

This module deliberately keeps experiment orchestration separate from the live
signal path. It reports per-ticker results and pooled PnL; it never sums ticker
percentage returns as if they were a portfolio return.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from .backtest import run_backtest
from .strategies import STRATEGIES


DEFAULT_TICKERS = ("CHMF", "GAZP", "LKOH", "MOEX", "MTSS", "NLMK", "NVTK", "SBER", "T", "TATN")


@dataclass(frozen=True)
class ExperimentSpec:
    db_path: str = "data/trader_4h.db"
    period: str = "15min"
    scenario_mode: int = 2
    commission: float = 0.0005
    cash_per_ticker: float = 100_000.0
    start: str | None = None
    end: str | None = None
    split: str = "full"
    split_at: str = "2026-04-01"
    tickers: tuple[str, ...] = DEFAULT_TICKERS


def load_candles(db_path: str, ticker: str, period: str) -> pd.DataFrame:
    """Load one sorted, deduplicated OHLCV series from the research database."""
    query = """
        SELECT begin, open, high, low, close, volume
        FROM candles
        WHERE ticker = ? AND period = ?
        ORDER BY begin
    """
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query(query, connection, params=(ticker, period), parse_dates=["begin"])
    frame = frame.drop_duplicates("begin").set_index("begin").sort_index()
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"invalid candle index for {ticker}/{period}")
    return frame


def select_window(frame: pd.DataFrame, spec: ExperimentSpec) -> pd.DataFrame:
    """Apply a chronological experiment window without changing its rows."""
    result = frame
    if spec.start:
        result = result[result.index >= pd.Timestamp(spec.start)]
    if spec.end:
        result = result[result.index < pd.Timestamp(spec.end)]
    if spec.split == "train":
        result = result[result.index < pd.Timestamp(spec.split_at)]
    elif spec.split == "test":
        result = result[result.index >= pd.Timestamp(spec.split_at)]
    elif spec.split != "full":
        raise ValueError(f"unsupported split: {spec.split}")
    return result


def pooled_trade_metrics(results: Iterable[dict]) -> dict:
    """Pool money metrics across independent equal-cash runs.

    Percentage returns remain per-ticker in the output. ``pooled_pnl`` is the
    additive quantity and ``equal_weight_return_pct`` is the mean of returns.
    Profit factor is calculated from pooled winning and losing PnL.
    """
    items = list(results)
    initial = sum(float(item.get("initial_cash", 0.0)) for item in items)
    final = sum(float(item.get("final_value", 0.0)) for item in items)
    pooled_pnl = final - initial
    wins = sum(max(float(item.get("avg_win", 0.0)), 0.0) * int(item.get("trades_won", 0)) for item in items)
    losses = sum(abs(min(float(item.get("avg_loss", 0.0)), 0.0)) * int(item.get("trades_lost", 0)) for item in items)
    returns = [float(item.get("total_return_pct", 0.0)) for item in items]
    return {
        "runs": len(items),
        "initial_cash": round(initial, 2),
        "final_value": round(final, 2),
        "pooled_pnl": round(pooled_pnl, 2),
        "pooled_return_pct": round(pooled_pnl / initial * 100, 4) if initial else 0.0,
        "equal_weight_return_pct": round(sum(returns) / len(returns), 4) if returns else 0.0,
        "trades_total": sum(int(item.get("trades_total", 0)) for item in items),
        "trades_won": sum(int(item.get("trades_won", 0)) for item in items),
        "trades_lost": sum(int(item.get("trades_lost", 0)) for item in items),
        "profit_factor": round(wins / losses, 4) if losses else (None if wins else 0.0),
    }


def run_experiment(spec: ExperimentSpec) -> dict:
    """Run one immutable experiment and return a JSON-serializable report."""
    item = STRATEGIES["support_resistance_mtf"]
    params = {parameter["key"]: parameter["default"] for parameter in item["params"]}
    params.update({"scenario_mode": spec.scenario_mode, "close_at_eod": 0})
    results = []
    for ticker in spec.tickers:
        frame = select_window(load_candles(spec.db_path, ticker, spec.period), spec)
        if frame.empty:
            results.append({"ticker": ticker, "status": "empty", "n_bars": 0})
            continue
        result = run_backtest(
            frame,
            item["cls"],
            params,
            cash=spec.cash_per_ticker,
            commission=spec.commission,
        )
        results.append({"ticker": ticker, "status": "ok", "n_bars": len(frame), **result})
    valid = [result for result in results if result["status"] == "ok"]
    return {
        "spec": asdict(spec),
        "strategy": "support_resistance_mtf",
        "params": params,
        "data_sha256": data_fingerprint(spec),
        "pooled": pooled_trade_metrics(valid),
        "results": results,
    }


def data_fingerprint(spec: ExperimentSpec) -> str:
    """Hash the selected raw rows so reports can be reproduced and compared."""
    digest = hashlib.sha256()
    for ticker in spec.tickers:
        frame = select_window(load_candles(spec.db_path, ticker, spec.period), spec)
        digest.update(ticker.encode())
        digest.update(frame.to_csv().encode())
    return digest.hexdigest()


def write_report(report: dict, output: str | Path) -> None:
    Path(output).write_text(json.dumps(report, ensure_ascii=True, indent=2, default=str) + "\n")
