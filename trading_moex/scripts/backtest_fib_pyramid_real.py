#!/usr/bin/env python3
"""Диагностика pyramiding (добавки к Fib-шорту на коррекциях) — РЕАЛЬНЫЙ движок.

Использует FibPullbackStrategy с параметрами fib_pyramid_frac/fib_pyramid_max:
после входа в шорт, если 4h-close выше среднего входа (отскок), добавляется
доля позиции; цель/стоп остаются структурными (swing low / swing high).

Сравнение с baseline (frac=0) и net с переносом (70/175 ₽/ночь).

Usage (from trading_moex/):
    python3 scripts/backtest_fib_pyramid_real.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import backtrader as bt  # noqa: E402
import pandas as pd  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

_4H_SHORT = ["T", "NLMK", "MOEX", "LKOH", "CHMF", "TATN", "NVTK", "GAZP"]


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


def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights(d0, d1, wk: bool) -> int:
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


class _Rec(FibPullbackStrategy):
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
            self.closed.append({
                "open": bt.num2date(trade.dtopen), "close": bt.num2date(trade.dtclose),
                "notional": notional, "pnl": float(trade.pnlcomm or 0.0),
                "max_notional": notional,
            })
        super().notify_trade(trade)


def run(ticker: str, df: pd.DataFrame, frac: float, maxadds: int,
        trigger: int = 0) -> list[dict]:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = -1
    p["flat_mode"] = 0
    p["fib_pyramid_frac"] = frac
    p["fib_pyramid_max"] = maxadds
    p["fib_pyramid_trigger"] = trigger
    cb = _setup_cerebro(_Rec, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def main() -> None:
    ap = argparse.ArgumentParser(description="Fib short pyramiding (real engine)")
    ap.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    args = ap.parse_args()

    dfs = {}
    wks = {}
    for t in _4H_SHORT:
        df = load_df(t, args.db)
        if df.empty:
            continue
        dfs[t] = df
        wks[t] = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())

    def agg(frac: float, maxadds: int, trigger: int = 0) -> dict:
        n = w = 0
        g = c = 0.0
        for t, df in dfs.items():
            for tr in run(t, df, frac, maxadds, trigger):
                n += 1
                w += 1 if tr["pnl"] > 0 else 0
                g += tr["pnl"]
                c += _carry_rate(tr["max_notional"]) * _nights(
                    tr["open"].date(), tr["close"].date(), wks[t])
        return {"n": n, "win": w / n * 100 if n else 0, "gross": g,
                "carry": c, "net": g - c}

    b = agg(0.0, 0)
    print(f"BASELINE: n={b['n']} win={b['win']:.1f}% gross={b['gross']:+,.0f} "
          f"carry={b['carry']:,.0f} net={b['net']:+,.0f}\n")
    print(f"{'trig':>4} {'frac':>6} {'max':>4} {'n':>5} {'win%':>6} {'gross':>11} "
          f"{'carry':>10} {'net':>11}")
    for trigger in (0, 1, 2):
        for frac in (0.25, 0.5):
            for maxadds in (1, 2):
                r = agg(frac, maxadds, trigger)
                print(f"{trigger:>4} {frac:>6.2f} {maxadds:>4} {r['n']:>5} {r['win']:>5.1f}% "
                      f"{r['gross']:>+11,.0f} {r['carry']:>10,.0f} {r['net']:>+11,.0f}")


if __name__ == "__main__":
    main()
