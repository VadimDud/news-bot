#!/usr/bin/env python3
"""Fib-short на разных таймфреймах: 1day / 2h / 4h / 15min.

Одна и та же логика Fib-short (direction=-1, flat_mode=0, единые параметры)
прогоняется на каждом ТФ, где хватает данных. Сделки считаются один раз, затем
оцениваются три ноги издержек (как в backtest_fib_short_futures_lqdt):

  stock       — шорт акциями (перенос 70/175 ₽/ночь);
  futures     — фьючерс (0.02%/сторона, ГО 20%, LQDT 16%/год на свободную маржу);
  fut_no_lqdt — контроль: фьючерс без дохода LQDT (собственный edge сигнала).

Покрытие данных (см. data/trader_4h.db):
  1day  11 тикеров, 2010..2026
  2h    10 тикеров, 2025-08..2026-09
  4h     9 тикеров, 2025-07..2026-09
  15min 10 тикеров, 2025-08..2026-09
  (60/30/5/1min — 1-2 тикера, для кросс-секции не годятся.)

Usage (from trading_moex/):
    python3 scripts/backtest_fib_timeframes.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import backtrader as bt  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import FibPullbackStrategy, TICKER_OVERRIDES, _FIB_PULLBACK_PARAMS_TUPLE  # noqa: E402

from scripts.backtest_fib_short_futures_lqdt import (  # noqa: E402
    CASH_PER_TICKER,
    CostModel,
    build_ledger,
    load_df,
    nights_held,
    summarize,
)

TF_TICKERS = {
    "1day": ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"],
    "2h": ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"],
    "4h": ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T"],
    "15min": ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"],
}


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
            self.closed.append({
                "open": bt.num2date(trade.dtopen),
                "close": bt.num2date(trade.dtclose),
                "entry": entry,
                "size": size,
                "notional": notional,
                "pnl_gross": float(trade.pnlcomm or 0.0),
                "ticker": key,
            })
        super().notify_trade(trade)


def base_params(ticker: str) -> dict:
    """Единый прод-оверрайд, но ТФ берём извне (не из TICKER_OVERRIDES)."""
    p = dict(_FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = -1
    p["flat_mode"] = 0
    return p


def run_ticker(ticker: str, df) -> list[dict]:
    cb = _setup_cerebro(_Recorder, base_params(ticker), CASH_PER_TICKER, 0.0)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def _has_weekend(df) -> bool:
    if df.empty:
        return False
    dow = df.index.dayofweek
    return bool((dow == 5).any() or (dow == 6).any())


def main() -> None:
    parser = argparse.ArgumentParser(description="Fib-short на разных ТФ")
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--timeframes", default="1day,2h,4h,15min")
    parser.add_argument("--lqdt-annual-pct", type=float, default=16.0)
    args = parser.parse_args()

    lqdt_daily = args.lqdt_annual_pct / 365.0
    legs = {
        "stock": CostModel(name="stock", commission_per_side=0.0, slippage_per_side=0.0,
                           carry_flat=70.0, carry_large=175.0),
        "futures": CostModel(name="futures", commission_per_side=0.0002, slippage_per_side=0.0002,
                             margin_rate=0.20, lqdt_daily_pct=lqdt_daily, lqdt_on_free_margin=True),
        "fut_no_lqdt": CostModel(name="fut_no_lqdt", commission_per_side=0.0002, slippage_per_side=0.0002,
                                 margin_rate=0.20, lqdt_daily_pct=lqdt_daily, lqdt_on_free_margin=False),
    }

    print(f"{'TF':<7} {'тик':>4} {'сдел':>5} {'win%':>5} {'gross/tr':>9} "
          f"{'stock NET':>11} {'fut NET':>11} {'fut_noLQDT':>11} {'ret%':>7}")
    for tf in [t.strip() for t in args.timeframes.split(",") if t.strip()]:
        tickers = TF_TICKERS.get(tf, [])
        all_trades: list[dict] = []
        weekend = False
        used = 0
        for t in tickers:
            df = load_df(t, args.db, tf)
            if df.empty or len(df) < 200:
                continue
            used += 1
            weekend = weekend or _has_weekend(df)
            all_trades.extend(run_ticker(t, df))
        if not all_trades:
            print(f"{tf:<7} (нет сделок)")
            continue
        # Капитал = тикеры × 100k (выделен на тикер), а не на сделку.
        capital = max(used, 1) * CASH_PER_TICKER
        s = {name: summarize(name, build_ledger(all_trades, weekend, cm), capital)
             for name, cm in legs.items()}
        n = len(all_trades)
        gross = sum(x["pnl_gross"] for x in all_trades)
        win = sum(1 for x in all_trades if x["pnl_gross"] > 0) / n * 100
        print(f"{tf:<7} {used:>4} {n:>5} {win:>5.1f} {gross/n:>9.0f} "
              f"{s['stock']['net_pnl']:>11,.0f} {s['futures']['net_pnl']:>11,.0f} "
              f"{s['fut_no_lqdt']['net_pnl']:>11,.0f} {s['futures']['net_return_pct']:>7.1f}")

    print(f"\nLQDT {args.lqdt_annual_pct:.1f}%/год; фьючерс 0.02%/стор., ГО 20%. "
          f"gross/tr — собственный edge сигнала на сделку (не зависит от переноса/LQDT).")


if __name__ == "__main__":
    main()
