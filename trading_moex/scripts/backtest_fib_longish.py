#!/usr/bin/env python3
"""Проверка кандидаток для «второй рабочей стратегии»: Fib long + 1day-шорт.

Считает net (gross - перенос) для:
  1) Fib long на 4h (направление +1) — все тикеры;
  2) Fib long на 1day (направление +1) — все тикеры;
  3) Fib short на 1day (направление -1) — все тикеры (здесь SBER/MTSS — ниша).

Конфиг из прод TICKER_OVERRIDES; направление задаётся явно этим скриптом.
Перенос моделируется по остаточному нециналу (70/175 ₽/ночь, weekend-aware).

Usage (from trading_moex/, dev host):
    python3 scripts/backtest_fib_longish.py --db data/trader_4h.db --period 4h --direction 1
    python3 scripts/backtest_fib_longish.py --db data/trader_4h.db --period 1day --direction 1
    python3 scripts/backtest_fib_longish.py --db data/trader_4h.db --period 1day --direction -1
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
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
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


def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights_between(d0, d1, wk: bool) -> int:
    c = 0
    cur = d0
    while cur < d1:
        nxt = cur + timedelta(days=1)
        if wk:
            c += 1
        else:
            if nxt.weekday() == 5:
                c += 3
            elif nxt.weekday() < 5:
                c += 1
        cur = nxt
    return c


class _Recorder(FibPullbackStrategy):
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
            self.closed.append({
                "open": op, "close": cl, "entry": entry, "size": size,
                "notional": notional, "pnl": pnl, "ticker": key,
            })
        super().notify_trade(trade)


def _base_params(ticker: str, direction: int) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = direction
    p["flat_mode"] = 0
    # длинные параметры: тренд = лонг-конфигурация (rsi_oversold для входа лонга)
    if direction == 1:
        p.setdefault("rsi_oversold", 40.0)
        p.setdefault("rsi_overbought", 80.0)
    return p


def run_ticker(ticker: str, df: pd.DataFrame, db: str, period: str, direction: int) -> list[dict]:
    p = _base_params(ticker, direction)
    cb = _setup_cerebro(_Recorder, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def main() -> None:
    parser = argparse.ArgumentParser(description="Fib long / 1day-short проверка")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", required=True)
    parser.add_argument("--direction", type=int, required=True)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    direction = args.direction
    lb = "LONG" if direction == 1 else "SHORT"

    print(f"Fib {lb} | период={args.period} | направление={direction:+d}\n")
    print(f"{'ticker':<6} {'сделок':>6} {'win%':>5} {'gross':>10} {'carry':>8} {'net':>10} {'noCarryNet':>10}")
    tot_n = tot_w = 0
    tot_gross = tot_carry = 0.0
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if df.empty:
            continue
        wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
        trades = run_ticker(t, df, args.db, args.period, direction)
        g = sum(x["pnl"] for x in trades)
        c = sum(_carry_rate(x["notional"]) * _nights_between(x["open"].date(), x["close"].date(), wk)
                for x in trades)
        n = len(trades)
        w = sum(1 for x in trades if x["pnl"] > 0)
        tot_n += n
        tot_w += w
        tot_gross += g
        tot_carry += c
        print(f"{t:<6} {n:>6} {w/n*100 if n else 0:>5.1f} {g:>10,.0f} {c:>8,.0f} {g-c:>10,.0f} {g:>10,.0f}")

    net = tot_gross - tot_carry
    print(f"\nИТОГО ({lb}, {args.period}): сделок={tot_n} win={tot_w/tot_n*100 if tot_n else 0:.1f}% "
          f"gross={tot_gross:+,.0f} carry={tot_carry:,.0f} NET={net:+,.0f}")
    print(f"(без переноса gross={tot_gross:+,.0f}; перенос = {tot_carry/tot_gross*100 if tot_gross else 0:.0f}% gross)")


if __name__ == "__main__":
    main()
