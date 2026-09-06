#!/usr/bin/env python3
"""Диагностика стратегии A: частичная фиксация (partial TP) + sizing под carry.

Гипотеза: Fib-шорт держит всю позицию до swing low (edge), но перенос через
ночь/выходные съедает 64% gross. Если частично выйти (``partial_frac``) на
промежуточном Фибо-уровне (``partial_at``), то:
  - остаточный нецинал меньше -> меньше 70₽/ночь на оставшуюся часть;
  - часть прибыли реализована раньше, остаток держится до swing low (edge
    multi-day удержания сохраняется).

Диагностика (прод-код НЕ меняется; стратегия субклассируется):
  - partial_frac ∈ {0 (baseline), 0.5, 0.75}
  - partial_at   ∈ {38.2%, 50%} — уровень ретрейсмента для частичного тейка
  - risk_pct     ∈ {1.0 (текущее), 1.5, 2.0, 2.5, 3.0} — где notional пересекает
    тир 100k (70₽/ночь -> 175₽/ночь)
Метрика каждой комбинации: сделок, win, gross, перенос, net (на депо 100k).

Перенос моделируется по ОСТАТОЧНОМУ нециналу после частичного выхода (а не по
начальному, как в прошлых скриптах).

Usage (from trading_moex/, dev host with local 4h DB):
    python3 scripts/backtest_fib_partial.py --db data/trader_4h.db --period 4h
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


# ── carry-модель по остаточному нециналу ─────────────────────────────────────

def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights_between(d0, d1, weekend_trading: bool) -> int:
    carries = 0
    cur = d0
    while cur < d1:
        nxt = cur + timedelta(days=1)
        if weekend_trading:
            carries += 1
        else:
            if nxt.weekday() == 5:
                carries += 3
            elif nxt.weekday() < 5:
                carries += 1
        cur = nxt
    return carries


# ── Стратегия с частичным тейком ─────────────────────────────────────────────

class _PartialLog(FibPullbackStrategy):
    """Записывает каждую сделку: entry/exit, нецинал, pnl, плюс -- при включённом
    частичном тейке -- точку и нецинал после partial-закрытия.

    Для диагностики достаточно закрытых сделок (вход/выход, нецинал, pnl);
    частичный тейк при этом моделируется в ``run_ticker`` поверх полного выхода.
    """

    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []
        self._open: dict = {}

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            # Цель шорта = swing low (из _last_state, вычисленного на баре входа).
            sl = self._last_state.get("swing_low") if self._last_state else None
            slv = None
            if sl is not None and self._last_state.get("idx") is not None:
                i = self._last_state["idx"]
                if i < len(sl) and sl[i] == sl[i]:
                    slv = float(sl[i])
            self._open[key] = (size, entry, entry * size, slv)
        if trade.isclosed:
            size, entry, notional, slv = self._open.pop(key, (0.0, 0.0, 0.0, None))
            op = bt.num2date(trade.dtopen)
            cl = bt.num2date(trade.dtclose)
            pnl = float(trade.pnlcomm or 0.0)
            self.closed.append({
                "open": op, "close": cl, "entry": entry, "size": size,
                "notional": notional, "pnl": pnl, "ticker": key,
                "swing_low": slv,
            })
        super().notify_trade(trade)


def _base_params(ticker: str, risk_pct: float) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = -1
    p["flat_mode"] = 0
    p["risk_pct"] = risk_pct
    return p


def run_ticker(ticker: str, df: pd.DataFrame, db: str, period: str, risk_pct: float) -> list[dict]:
    """Прогнать полноразмерный выход (без partial) — записать базовые сделки.

    Возвращает закрытые сделки с entry/exit/notional/pnl/swing_low.
    """
    p = _base_params(ticker, risk_pct)
    cb = _setup_cerebro(_PartialLog, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def partial_outcome(tr: dict, partial_frac: float, partial_at: float, weekend_trading: bool) -> dict:
    """Смоделировать частичный тейк поверх сделки полного выхода.

    Для шорта: вход в premium-зоне (цена выше), цель — swing low (цена ниже).
    Промежуточный ретрейсмент ``partial_at`` — на какой доле пути от входа к
    цели закрывается partial_frac позиции.

    Возвращает {gross, carry, days, residual_notional}.
    """
    entry = tr["entry"]
    size = tr["size"]
    notional = tr["notional"]
    swing_low = tr.get("swing_low")
    # Цель --- реальная (swing low на входе); если недоступна — полный выход.
    if partial_frac <= 0 or not swing_low:
        carry = _carry_rate(notional) * _nights_between(
            tr["open"].date(), tr["close"].date(), weekend_trading)
        return {"gross": tr["pnl"], "carry": carry,
                "days": (tr["close"].date() - tr["open"].date()).days,
                "residual_notional": notional, "partial": False}

    move = entry - swing_low  # >0, расстояние до цели (для шорта)
    if move <= 0:
        carry = _carry_rate(notional) * _nights_between(
            tr["open"].date(), tr["close"].date(), weekend_trading)
        return {"gross": tr["pnl"], "carry": carry,
                "days": (tr["close"].date() - tr["open"].date()).days,
                "residual_notional": notional, "partial": False}

    # Промежуточный уровень частичного тейка (ниже входа, выше swing_low).
    partial_price = entry - partial_at * move
    # Partial срабатывает ТОЛЬКО если цена дошла до уровня (двигалась к цели):
    # сделка-победитель (pnl>0) прошла через partial_price → lock части прибыли.
    # Сделка-проигрыш (pnl<=0) ушла вверх к стопу → уровень не достигнут, partial
    # НЕ срабатывает → остаётся полный убыток.
    if tr["pnl"] <= 0:
        carry = _carry_rate(notional) * _nights_between(
            tr["open"].date(), tr["close"].date(), weekend_trading)
        return {"gross": tr["pnl"], "carry": carry,
                "days": (tr["close"].date() - tr["open"].date()).days,
                "residual_notional": notional, "partial": False}

    # Победитель: цена пересекла partial_price по пути к цели (swing low).
    # Закрытая часть реализует прибыль на уровне partial_price.
    partial_gross = (entry - partial_price) * (partial_frac * size)
    # Остаток выходит по действительному pnl сделки пропорционально оставшейся
    # доле (полный pnl приходился на полный size, остаётся (1-frac)). Выход
    # остатка — к цели (swing low), как и в полной сделке.
    residual_gross = tr["pnl"] * (1 - partial_frac)
    total_gross = partial_gross + residual_gross
    # carry: до частичного тейка — полный нецинал, после — остаточный.
    total_days = max((tr["close"].date() - tr["open"].date()).days, 0)
    days_to_partial = min(int(round(total_days * partial_at)), total_days)
    d_partial = tr["open"].date() + timedelta(days=days_to_partial)
    residual_notional = (1 - partial_frac) * notional
    carry = (
        _carry_rate(notional) * _nights_between(tr["open"].date(), d_partial, weekend_trading)
        + _carry_rate(residual_notional) * _nights_between(d_partial, tr["close"].date(), weekend_trading)
    )
    return {"gross": total_gross, "carry": carry, "days": total_days,
            "residual_notional": residual_notional, "partial": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Partial TP + carry-sizing диагностика")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="4h")
    parser.add_argument("--risk", default="1.0,1.5,2.0,2.5,3.0")
    parser.add_argument("--frac", default="0,0.5,0.75")
    parser.add_argument("--at", default="0.382,0.5")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    risks = [float(x) for x in args.risk.split(",") if x.strip()]
    fracs = [float(x) for x in args.frac.split(",") if x.strip()]
    ats = [float(x) for x in args.at.split(",") if x.strip()]

    print(f"Период: {args.period} | risk_pct={risks} | partial_frac={fracs} | partial_at={ats}\n")

    cache: dict[tuple[str, float], dict] = {}
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if df.empty:
            continue
        for risk in risks:
            trades = run_ticker(t, df, args.db, args.period, risk)
            wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
            cache[(t, risk)] = {"trades": trades, "wk": wk}

    header = f"{'risk':>5} {'frac':>5} {'at':>5} {'сделок':>7} {'win':>6} {'gross':>9} {'carry':>8} {'net':>9}"
    print(header)
    print("-" * len(header))

    results: dict[tuple[float, float, float], dict] = {}
    for risk in risks:
        for frac in fracs:
            for at in ats:
                tot_n = 0
                tot_win = 0.0
                tot_gross = 0.0
                tot_carry = 0.0
                for t in tickers:
                    k = (t, risk)
                    if k not in cache:
                        continue
                    for tr in cache[k]["trades"]:
                        out = partial_outcome(tr, frac, at, cache[k]["wk"])
                        tot_n += 1
                        if out["gross"] > 0:
                            tot_win += 1
                        tot_gross += out["gross"]
                        tot_carry += out["carry"]
                net = tot_gross - tot_carry
                results[(risk, frac, at)] = {
                    "n": tot_n, "gross": round(tot_gross, 0),
                    "carry": round(tot_carry, 0), "net": round(net, 0),
                }
                win = round(tot_win / tot_n * 100, 1) if tot_n else 0
                print(f"{risk:>5.1f} {frac:>5.2f} {at:>5.3f} {tot_n:>7} {win:>5.1f}% "
                      f"{tot_gross:>9,.0f} {tot_carry:>8,.0f} {net:>9,.0f}")

    base = results.get((1.0, 0.0, 0.382), {"net": None})
    print(f"\nBaseline (risk=1.0, frac=0): net={base['net']:,}")
    best = max(results, key=lambda k: results[k]["net"])
    print(f"Лучший: risk={best[0]}, frac={best[1]}, at={best[2]} -> net={results[best]['net']:,.0f}")


if __name__ == "__main__":
    main()
