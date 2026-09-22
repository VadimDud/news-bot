#!/usr/bin/env python3
"""Диагностика реверса на стопе (flip_on_stop) для Fib-шорта — РЕАЛЬНЫЙ движок.

Идея: если шорт-сигнал Fib отработан, но цена пробила структурный уровень
(swing high) вверх и свеча закрылась за ним — вместо простого стопа открыть
ЛОНГ («перекладка» позиции). Зеркально для лонга. Цель — забрать движение
против исходного сетапа, когда рынок сломал структуру.

Сравнение с baseline (flip_on_stop=0) и net с переносом (70/175 ₽/ночь).

Usage (from trading_moex/):
    python3 scripts/backtest_fib_flip.py --db data/trader_4h.db
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


def run(ticker: str, df: pd.DataFrame, flip: int, direction: int = -1) -> list[dict]:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = direction
    p["flat_mode"] = 0
    p["flip_on_stop"] = flip
    cb = _setup_cerebro(_Rec, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def main() -> None:
    ap = argparse.ArgumentParser(description="Fib flip-on-stop (real engine)")
    ap.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    ap.add_argument("--direction", type=int, default=-1)
    ap.add_argument("--tickers", default=",".join(_4H_SHORT),
                    help="тикеры через запятую")
    ap.add_argument("--per-ticker", action="store_true",
                    help="вывести разбивку по тикерам (медленнее)")
    ap.add_argument("--start", default=None, help="начало периода YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="конец периода YYYY-MM-DD")
    ap.add_argument("--flips", default="0,1,2",
                    help="режимы flip через запятую")
    args = ap.parse_args()

    dfs = {}
    wks = {}
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    for t in tickers:
        df = load_df(t, args.db)
        if args.start:
            df = df[df.index >= pd.Timestamp(args.start)]
        if args.end:
            df = df[df.index < pd.Timestamp(args.end) + pd.Timedelta(days=1)]
        if df.empty:
            continue
        dfs[t] = df
        wks[t] = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())

    def agg(flip: int) -> dict:
        n = w = 0
        g = c = 0.0
        for t, df in dfs.items():
            for tr in run(t, df, flip, args.direction):
                n += 1
                w += 1 if tr["pnl"] > 0 else 0
                g += tr["pnl"]
                c += _carry_rate(tr["max_notional"]) * _nights(
                    tr["open"].date(), tr["close"].date(), wks[t])
        return {"n": n, "win": w / n * 100 if n else 0, "gross": g,
                "carry": c, "net": g - c}

    modes = [int(v.strip()) for v in args.flips.split(",") if v.strip()]
    if 0 not in modes:
        modes.insert(0, 0)
    b = agg(0)
    print(f"BASELINE flip=0: n={b['n']} win={b['win']:.1f}% gross={b['gross']:+,.0f} "
          f"carry={b['carry']:,.0f} net={b['net']:+,.0f}\n")
    print(f"{'flip':>4} {'n':>5} {'win%':>6} {'gross':>12} {'carry':>11} {'net':>12} "
          f"{'vs base':>12}")
    for flip in modes:
        if flip == 0:
            continue
        r = agg(flip)
        print(f"{flip:>4} {r['n']:>5} {r['win']:>5.1f}% {r['gross']:>+12,.0f} "
              f"{r['carry']:>11,.0f} {r['net']:>+12,.0f} {r['net']-b['net']:>+12,.0f}")

    if args.per_ticker:
        # Per-ticker: где реверс помогает/вредит
        print(f"\n{'ticker':>7} {'n0':>5} {'n1':>5} {'win0':>6} {'win1':>6} "
              f"{'net0':>11} {'net1':>11}")
        for t, df in dfs.items():
            row = {}
            for flip in (0, 1):
                trs = run(t, df, flip, args.direction)
                n = len(trs)
                w = sum(1 for x in trs if x["pnl"] > 0)
                g = sum(x["pnl"] for x in trs)
                c = sum(_carry_rate(x["max_notional"]) * _nights(
                    x["open"].date(), x["close"].date(), wks[t]) for x in trs)
                row[flip] = (n, w / n * 100 if n else 0.0, g - c)
            print(f"{t:>7} {row[0][0]:>5} {row[1][0]:>5} {row[0][1]:>5.1f}% "
                  f"{row[1][1]:>5.1f}% {row[0][2]:>+11,.0f} {row[1][2]:>+11,.0f}")


if __name__ == "__main__":
    main()
