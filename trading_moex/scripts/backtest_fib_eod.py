#!/usr/bin/env python3
"""Сравнение режимов переноса шорт-позиции через ночь/выходные (комиссия брокера).

Комиссия за перенос шорта (фиксированная, зависит от нецинала позиции):
  ≤ 100 000 ₽  — 70 ₽ за ночь
  ≤ 250 000 ₽  — 175 ₽ за ночь
Ночь после пятницы (пт→пн) тарифицируется как 3 ночи (выходные).

Режимы (параметр ``flat_mode`` стратегии):
  0 — держать позицию до цели (по умолчанию);
  1 — закрывать в конце каждого дня и ре-входить утром при живом сетапе;
  2 — закрывать только в пятницу (не переносить через выходные).

Usage (из trading_moex/):
  python3 scripts/backtest_fib_eod.py --tickers T,NLMK,MOEX,LKOH,CHMF,TATN,NVTK,GAZP
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import backtrader as bt  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import FibPullbackStrategy, _FIB_PULLBACK_PARAMS_TUPLE  # noqa: E402

DEFAULT_TICKERS = ["T", "NLMK", "MOEX", "LKOH", "CHMF", "TATN", "NVTK", "GAZP"]

# Параметры бэктеста, совпадающие с продовскими per-ticker настройками (4h шорт).
_PER_TICKER = {
    "MOEX": {"swing_bars": 5, "trend_period": 100},
    "TATN": {"swing_bars": 5, "trend_period": 200},
}


def load_df(ticker: str, db: str, period: str = "4h") -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


class _TradeRecorder(FibPullbackStrategy):
    """Фиксирует сделку (вход/выход, размер, нецинал, pnl) при закрытии."""

    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []
        self._open: dict = {}

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            self._open[key] = (size, entry, entry * size)
        if trade.isclosed:
            size, entry, notional = self._open.pop(key, (0.0, 0.0, 0.0))
            op = bt.num2date(trade.dtopen)
            cl = bt.num2date(trade.dtclose)
            pnl = float(trade.pnlcomm or 0.0)
            self.closed.append(
                {"open": op, "close": cl, "entry": entry + (0 if size else 0),
                 "size": size, "notional": notional, "pnl": pnl, "ticker": key}
            )
        super().notify_trade(trade)


def run_mode(ticker: str, df: pd.DataFrame, flat_mode: int, db: str) -> list[dict]:
    params = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    params.update(dict(confluence_min=1, rsi_oversold=40, rsi_overbought=80,
                       trend_period=100, swing_bars=10, min_rr=1.0,
                       fib_in_low=0.5, fib_in_high=0.618, direction=-1))
    params.update(_PER_TICKER.get(ticker, {}))
    params["flat_mode"] = flat_mode
    cb = _setup_cerebro(_TradeRecorder, params, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def nights_held(op, close) -> int:
    """Взвешенные ночи переноса: будни=1, пт→пн=3 (сб/вс не считаем)."""
    carries = 0
    cur = op.date()
    while cur < close.date():
        nxt = cur + timedelta(days=1)
        if nxt.weekday() == 5:
            carries += 3
        elif nxt.weekday() < 5:
            carries += 1
        cur = nxt
    return carries


def carry_fee(notional: float, nights: int) -> float:
    rate = 70.0 if notional <= 100_000 else 175.0
    return rate * nights


def main() -> None:
    parser = argparse.ArgumentParser(description="Сравнение режимов переноса шорта")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader.db"))
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    results: dict[int, list] = {0: [], 1: [], 2: []}
    for ticker in tickers:
        df = load_df(ticker, args.db)
        for mode in (0, 1, 2):
            closed = run_mode(ticker, df, mode, args.db)
            for tr in closed:
                tr["nights"] = nights_held(tr["open"], tr["close"])
                tr["carry"] = carry_fee(tr["notional"], tr["nights"])
                results[mode].append(tr)

    names = {0: "A. Удержание", 1: "B. EOD-flat", 2: "C. Только пятница"}
    summary = []
    print(f"\n{'Режим':20} {'сделок':>7} {'gross pnl':>12} {'перенос':>10} {'чистый':>10}")
    for mode in (0, 1, 2):
        trs = results[mode]
        gross = sum(t["pnl"] for t in trs)
        carry = sum(t["carry"] for t in trs)
        net = gross - carry
        print(f"{names[mode]:20} {len(trs):>7} {gross:>12,.0f} {carry:>10,.0f} {net:>10,.0f}")
        summary.append((mode, len(trs), gross, carry, net))

    best = max(summary, key=lambda x: x[4])
    print(f"\nЛучший по чистому: {names[best[0]]} (чистый {best[4]:+,.0f} ₽)")


if __name__ == "__main__":
    main()
