#!/usr/bin/env python3
"""Диагностика: улучшают ли Фибоначчи-уровни прибыль Fib-шорта?

Идея: цель текущей стратегии — swing low (0%). Возможно, цены ходят ДАЛЬШЕ
(Fib-расширения 127.2/161.8%), и тогда более дальняя цель даст больше. Также
проверяем Fib-стопы.

Метод — РЕАЛЬНЫЙ бэктест (backtrader) с параметрами:
  - fib_target_mult: цель = entry - mult*(entry - swing_low)  (1.0 = текущая)
  - fib_stop_mult:   стоп = entry + mult*stop_dist            (1.0 = текущая)
Гарантия паритета: при 1.0/1.0 результат == текущий baseline (154 сделки,
+63,844 gross). Считаем net с переносом (70/175 ₽/ночь).

Прод-дефолты остаются 1.0 — поведение не меняется.

Usage (from trading_moex/):
    python3 scripts/backtest_fib_targets.py --db data/trader_4h.db
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
                "open": bt.num2date(trade.dtopen),
                "close": bt.num2date(trade.dtclose),
                "notional": notional, "pnl": float(trade.pnlcomm or 0.0),
            })
        super().notify_trade(trade)


def run(ticker: str, df: pd.DataFrame, tmult: float, smult: float,
        rr_ratio: float | None = None) -> list[dict]:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = -1
    p["flat_mode"] = 0
    p["fib_target_mult"] = tmult
    p["fib_stop_mult"] = smult
    if rr_ratio is not None:
        p["rr_ratio"] = rr_ratio
    cb = _setup_cerebro(_Rec, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def main() -> None:
    ap = argparse.ArgumentParser(description="Fib target/stop multipliers")
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

    def agg(tmult: float, smult: float, rr: float | None = None) -> dict:
        n = w = 0
        gross = carry = 0.0
        for t, df in dfs.items():
            for tr in run(t, df, tmult, smult, rr):
                n += 1
                if tr["pnl"] > 0:
                    w += 1
                gross += tr["pnl"]
                carry += _carry_rate(tr["notional"]) * _nights(
                    tr["open"].date(), tr["close"].date(), wks[t])
        return {"n": n, "win": w / n * 100 if n else 0,
                "gross": gross, "carry": carry, "net": gross - carry}

    print("=== Цель: Fib-расширения (стоп структурный, mult=1.0) ===")
    print(f"  {'target_mult':>11} {'n':>5} {'win%':>6} {'gross':>11} {'carry':>9} {'net':>10}")
    base = None
    for tm in (1.0, 1.272, 1.618, 2.0):
        r = agg(tm, 1.0)
        if tm == 1.0:
            base = r
        print(f"  {tm:>11.3f} {r['n']:>5} {r['win']:>5.1f}% {r['gross']:>+11,.0f} "
              f"{r['carry']:>9,.0f} {r['net']:>+10,.0f}")
    print(f"  (baseline parity: n={base['n']} gross={base['gross']:+,.0f} "
          f"net={base['net']:+,.0f} — должно совпасть с известным +63,844 / +22,929)")

    print("\n=== Стоп: Fib-расширение (цель = swing low, mult=1.0) ===")
    print(f"  {'stop_mult':>9} {'n':>5} {'win%':>6} {'gross':>11} {'carry':>9} {'net':>10}")
    for sm in (1.0, 1.272, 1.618):
        r = agg(1.0, sm)
        print(f"  {sm:>9.3f} {r['n']:>5} {r['win']:>5.1f}% {r['gross']:>+11,.0f} "
              f"{r['carry']:>9,.0f} {r['net']:>+10,.0f}")

    print("\n=== Комбо: Fib-цель + Fib-стоп ===")
    print(f"  {'tmult':>6} {'smult':>6} {'n':>5} {'win%':>6} {'gross':>11} {'net':>10}")
    for tm in (1.272, 1.618):
        for sm in (1.0, 1.272):
            r = agg(tm, sm)
            print(f"  {tm:>6.3f} {sm:>6.3f} {r['n']:>5} {r['win']:>5.1f}% "
                  f"{r['gross']:>+11,.0f} {r['net']:>+10,.0f}")


if __name__ == "__main__":
    main()
