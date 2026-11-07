#!/usr/bin/env python3
"""Сравнение вариантов брекета Fib-short с S/R-уровнями (1day).

Варианты (поле ``variant``):
  baseline   — Fib-цель = swing low, стоп за swing high / ATR (прод).
  sr_tp      — цель = ближайший S/R-кластер под входом (sr_tp_mode=1).
  sr_tp_min  — цель = минимум(Fib-цель, S/R), т.е. ближе к входу (sr_tp_mode=2).
  sr_tp_sl   — как sr_tp + стоп за ближайшим S/R сверху (sr_sl_mode=1).
  sr_min_sl  — как sr_tp_min + S/R-стоп.

Метрики на тикер и итого: сделок, win%, gross, перенос (carry), net, PF.
Перенос моделируется по остаточному нециналу (70/175 ₽/ночь, weekend-aware).

Usage (from trading_moex/):
    python3 scripts/backtest_fib_sr.py --db data/trader_4h.db --period 1day
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

from scripts.backtest_fib_longish import (  # noqa: E402
    ALL_TICKERS,
    _base_params,
    _carry_rate,
    _nights_between,
    load_df,
)

import backtrader as bt  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import FibPullbackStrategy  # noqa: E402

VARIANTS: dict[str, dict] = {
    "baseline": {},
    "sr_tp": {"sr_tp_mode": 1},
    "sr_tp_min": {"sr_tp_mode": 2},
    "sr_tp_sl": {"sr_tp_mode": 1, "sr_sl_mode": 1},
    "sr_min_sl": {"sr_tp_mode": 2, "sr_sl_mode": 1},
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
            pnl = float(trade.pnlcomm or 0.0)
            self.closed.append({
                "open": bt.num2date(trade.dtopen),
                "close": bt.num2date(trade.dtclose),
                "notional": notional,
                "pnl": pnl,
            })
        super().notify_trade(trade)


def _profit_factor(pnls: list[float]) -> float:
    gains = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    return gains / losses if losses > 0 else float("inf")


def run_variant(ticker: str, df, params: dict) -> list[dict]:
    p = dict(params)
    cb = _setup_cerebro(_Recorder, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    return cb.run(runonce=False)[0].closed


def main() -> None:
    parser = argparse.ArgumentParser(description="Fib short: S/R в TP/SL")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    frames = {}
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if not df.empty:
            frames[t] = df

    summary: dict[str, dict] = {}
    for name, extra in VARIANTS.items():
        print(f"\n=== {name} {' '.join(f'{k}={v}' for k, v in extra.items())} ===")
        print(f"{'ticker':<6} {'сделок':>6} {'win%':>5} {'gross':>10} {'carry':>8} {'net':>10} {'PF':>5}")
        tn = tw = 0
        tg = tc = 0.0
        all_pnl: list[float] = []
        for t, df in frames.items():
            p = _base_params(t, -1)
            p.update(extra)
            wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
            trades = run_variant(t, df, p)
            pnls = [x["pnl"] for x in trades]
            g = sum(pnls)
            c = sum(_carry_rate(x["notional"]) * _nights_between(x["open"].date(), x["close"].date(), wk)
                    for x in trades)
            n = len(pnls)
            w = sum(1 for x in pnls if x > 0)
            tn += n
            tw += w
            tg += g
            tc += c
            all_pnl.extend(pnls)
            print(f"{t:<6} {n:>6} {w/n*100 if n else 0:>5.1f} {g:>10,.0f} {c:>8,.0f} "
                  f"{g-c:>10,.0f} {_profit_factor(pnls):>5.2f}")
        net = tg - tc
        summary[name] = {"n": tn, "win": tw / tn * 100 if tn else 0.0,
                         "gross": tg, "carry": tc, "net": net, "pf": _profit_factor(all_pnl)}
        print(f"ИТОГО: сделок={tn} win={summary[name]['win']:.1f}% gross={tg:+,.0f} "
              f"carry={tc:,.0f} NET={net:+,.0f} PF={summary[name]['pf']:.2f}")

    print("\n=== СВОДКА ===")
    print(f"{'variant':<12} {'сделок':>6} {'win%':>5} {'gross':>10} {'net':>10} {'PF':>5}")
    for name, s in summary.items():
        print(f"{name:<12} {s['n']:>6} {s['win']:>5.1f} {s['gross']:>10,.0f} {s['net']:>10,.0f} {s['pf']:>5.2f}")


if __name__ == "__main__":
    main()
