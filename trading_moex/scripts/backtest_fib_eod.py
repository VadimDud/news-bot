#!/usr/bin/env python3
"""Сравнение режимов переноса шорт-позиции через ночь/выходные (комиссия брокера).

Комиссия за перенос шорта (фиксированная, зависит от нецинала позиции):
  ≤ 100 000 ₽  — 70 ₽ за ночь
  ≤ 250 000 ₽  — 175 ₽ за ночь

С марта 2025 MOEX торгуется по выходным (сессии 08:00–16:00, объём ~10–16%
от будней). Если для тикера есть weekend-свечи — каждая календарная ночь
считается как 1 (рынок открыт, позиция может закрыться). Если weekend-свечей
нет (ранние данные до марта 2025) — старая формула: пт→пн = 3 ночи.

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


def _has_weekend_candles(df: pd.DataFrame) -> bool:
    """Определяет, торгуется ли тикер по выходным (есть ли свечи на сб/вс)."""
    if df.empty:
        return False
    dow = df.index.dayofweek  # 0=Mon .. 6=Sun
    return bool((dow == 5).any() or (dow == 6).any())


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


def nights_held(op, close, weekend_trading: bool = False) -> int:
    """Ночи переноса.

    *weekend_trading=True* (MOEX торгуется по выходным, с марта 2025):
      каждая календарная ночь = 1 (пт→сб=1, сб→вс=1, вс→пн=1).

    *weekend_trading=False* (старые данные, weekend-сессий нет):
      пт→пн = 3 ночи (тариф за 3 выходных), остальные = 1.
    """
    carries = 0
    cur = op.date()
    while cur < close.date():
        nxt = cur + timedelta(days=1)
        if weekend_trading:
            carries += 1
        else:
            if nxt.weekday() == 5:  # Saturday -> Fri->Mon = 3
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
    weekend_info: dict[str, bool] = {}
    for ticker in tickers:
        df = load_df(ticker, args.db)
        wk = _has_weekend_candles(df)
        weekend_info[ticker] = wk
        label = "есть weekend-свечи" if wk else "нет weekend-свечей"
        print(f"  {ticker}: {label} ({len(df)} баров)")
        for mode in (0, 1, 2):
            closed = run_mode(ticker, df, mode, args.db)
            for tr in closed:
                tr["nights"] = nights_held(tr["open"], tr["close"], weekend_trading=wk)
                tr["carry"] = carry_fee(tr["notional"], tr["nights"])
                results[mode].append(tr)

    print()
    names = {0: "A. Удержание", 1: "B. EOD-flat", 2: "C. Только пятница"}
    summary = []
    print(f"{'Режим':20} {'сделок':>7} {'gross pnl':>12} {'перенос':>10} {'чистый':>10}")
    for mode in (0, 1, 2):
        trs = results[mode]
        gross = sum(t["pnl"] for t in trs)
        carry = sum(t["carry"] for t in trs)
        net = gross - carry
        print(f"{names[mode]:20} {len(trs):>7} {gross:>12,.0f} {carry:>10,.0f} {net:>10,.0f}")
        summary.append((mode, len(trs), gross, carry, net))

    best = max(summary, key=lambda x: x[4])
    print(f"\nЛучший по чистому: {names[best[0]]} (чистый {best[4]:+,.0f} ₽)")

    # Детализация по тикерам
    print(f"\n{'Тикер':<8} {'Режим':<20} {'сделок':>7} {'gross':>10} {'ночей':>6} {'перенос':>8} {'чистый':>10}")
    for ticker in tickers:
        for mode in (0, 1, 2):
            trs = [t for t in results[mode] if t["ticker"] == ticker]
            if not trs:
                continue
            gross = sum(t["pnl"] for t in trs)
            nights = sum(t["nights"] for t in trs)
            carry = sum(t["carry"] for t in trs)
            net = gross - carry
            print(f"{ticker:<8} {names[mode]:<20} {len(trs):>7} {gross:>10,.0f} {nights:>6} {carry:>8,.0f} {net:>10,.0f}")
        if ticker != tickers[-1]:
            print()


if __name__ == "__main__":
    main()
