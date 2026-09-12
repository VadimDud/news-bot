#!/usr/bin/env python3
"""Long Fib без переноса (нет одалживания) — реальный бэктест.

Пользователь: шорт требует одалживания и платит перенос (70/175 ₽/ночь), а лонг
— нет. Проверяем long-only БЕЗ carry: только комиссия + слайпедж.

Считаем реальным backtrader-бэктестором (паритет с прод-кодом):
  - период 4h и 1day, все тикеры;
  - gross/net (перенос НЕ вычитается);
  - сравнение с buy&hold.

Использует ту же FibPullbackStrategy; комиссия+слайпедж моделируются в брокере
как суммарная ставка за сторону.

Usage (from trading_moex/):
    python3 scripts/backtest_fib_long_nocarry.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
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

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
COMMISSION = 0.0005   # 0.05% на сторону
SLIPPAGE = 0.0005     # 0.05% на сторону


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


class _Rec(FibPullbackStrategy):
    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []

    def notify_trade(self, trade):
        if trade.isclosed:
            self.closed.append({"pnl": float(trade.pnlcomm or 0.0)})
        super().notify_trade(trade)


def _params(ticker: str, direction: int) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = direction
    p["flat_mode"] = 0
    return p


def run(ticker: str, df: pd.DataFrame, direction: int) -> list[dict]:
    cb = _setup_cerebro(_Rec, _params(ticker, direction), 100_000,
                        COMMISSION + SLIPPAGE)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def main() -> None:
    ap = argparse.ArgumentParser(description="Long Fib no-carry (real backtest)")
    ap.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    ap.add_argument("--periods", default="4h,1day")
    args = ap.parse_args()

    for period in [x.strip() for x in args.periods.split(",") if x.strip()]:
        print(f"\n=== LONG {period} без переноса | cost {2*(COMMISSION+SLIPPAGE)*100:.2f}% round-trip ===")
        tot_n = tot_w = 0
        net = 0.0
        for t in ALL_TICKERS:
            df = load_df(t, args.db, period)
            if len(df) < 60:
                continue
            trs = run(t, df, 1)
            if not trs:
                continue
            g = sum(x["pnl"] for x in trs)
            n = len(trs)
            w = sum(1 for x in trs if x["pnl"] > 0)
            tot_n += n
            tot_w += w
            net += g
            print(f"  {t:<6} n={n:>3} win={w/n*100:>4.0f}% net={g:>+10,.0f}")
        print(f"  ИТОГО: n={tot_n} win={tot_w/tot_n*100 if tot_n else 0:.1f}% net={net:+,.0f}")

        rets = [(load_df(t, args.db, period)["close"].iloc[-1] /
                 load_df(t, args.db, period)["close"].iloc[0] - 1) * 100_000
                for t in ALL_TICKERS if len(load_df(t, args.db, period)) >= 60]
        print(f"  Buy&Hold (сумма на 100к по тикерам): {sum(rets):+,.0f}")


if __name__ == "__main__":
    main()
