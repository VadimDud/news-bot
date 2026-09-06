#!/usr/bin/env python3
"""Диагностика корзинки одновременных Fib-шорт сигналов (вход во все + выход по первому TP).

Гипотеза: когда несколько тикеров получают шорт-сигнал почти одновременно, войти
во все как в корзину, а закрыть все, когда ПЕРВЫЙ достигнет своего тейка (swing
low). Сравнивается с независимым baseline (каждый по своему тейку).

Оси кластеризации «одновременности»:
  - bar:    строгий один 4h-бар;
  - day:    тот же календарный день;
  - window: скользящее окно N 4h-баров.

Правила входа/выхода:
  - each_tp (control): каждый тикер независимо по своему тейку;
  - all_first_tp (ваша идея): войти во все, закрыть все, когда ПЕРВЫЙ достигнет
    тейка (по пути цены, причинно).

Метрика: net (gross - перенос), число корзин, win-rate, макс. одновременных
позиций (риск концентрации).

Прод-код НЕ меняется. Диагностика.

Usage (from trading_moex/, dev host with local 4h DB):
    python3 scripts/backtest_fib_basket.py --db data/trader_4h.db --period 4h
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

# Тикеры, фактически работающие на 4h-шорт в проде (MTSS/SBER — на 1day).
_4H_SHORT = ["T", "NLMK", "MOEX", "LKOH", "CHMF", "TATN", "NVTK", "GAZP"]


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


# ── Прогон тикера: закрытые шорт-сделки ──────────────────────────────────────

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
                "notional": notional, "pnl": pnl, "swing_low": slv, "ticker": key,
            })
        super().notify_trade(trade)


def _base_params(ticker: str) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = -1
    p["flat_mode"] = 0
    return p


def run_ticker(ticker: str, df: pd.DataFrame, db: str, period: str) -> list[dict]:
    p = _base_params(ticker)
    cb = _setup_cerebro(_Recorder, p, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def trade_carry(tr: dict, wk: bool) -> float:
    return _carry_rate(tr["notional"]) * _nights_between(
        tr["open"].date(), tr["close"].date(), wk)


# ── Причинный расчёт: момент достижения цели после входа ─────────────────────

def tp_reach_ts(df: pd.DataFrame, entry_ts, target: float):
    """Первый бар после entry_ts, где low <= target (шорт). Возвращает ts или None."""
    sub = df.loc[df.index >= entry_ts]
    if sub.empty:
        return None
    hit = sub.index[sub["low"] <= target]
    return hit[0] if len(hit) else None


def close_price_at(df: pd.DataFrame, entry_ts, ts) -> float:
    """Цена закрытия на баре ts (или последнем <= ts), если ts после entry."""
    sub = df.loc[(df.index >= entry_ts) & (df.index <= ts)]
    if sub.empty:
        return float(df.loc[df.index <= entry_ts, "close"].iloc[-1]) \
            if len(df.loc[df.index <= entry_ts]) else float(df["close"].iloc[-1])
    return float(sub["close"].iloc[-1])


# ── Кластерные ключи ─────────────────────────────────────────────────────────

def _day_key(tr) -> str:
    return tr["open"].date().isoformat()


def _bar_key(tr) -> str:
    return tr["open"].strftime("%Y-%m-%d %H:%M")


def _window_key(tr, bars: int) -> str:
    """Окно из ``bars`` последовательных 4h-баров в рамках дня (partitions)."""
    bar_of_day = tr["open"].hour // 4  # 4h-бар: 0..5
    bucket = bar_of_day // max(bars, 1)
    return tr["open"].strftime("%Y-%m-%d") + f" w{bucket}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Корзинка одновременных Fib-шорт")
    parser.add_argument("--tickers", default=",".join(_4H_SHORT))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="4h")
    parser.add_argument("--windows", default="2,3,4")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    windows = [int(x) for x in args.windows.split(",") if x.strip()]

    # Собрать сделки + df всех тикеров.
    trade_list: dict[str, list[dict]] = {}
    df_map: dict[str, pd.DataFrame] = {}
    all_trades: list[dict] = []
    for t in tickers:
        df = load_df(t, args.db, args.period)
        if df.empty:
            continue
        df_map[t] = df
        wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
        trs = run_ticker(t, df, args.db, args.period)
        for tr in trs:
            tr["ticker"] = t
            tr["wk"] = wk
            all_trades.append(tr)
        trade_list[t] = trs

    print(f"Тикеров: {len(tickers)} | всего независимых сделок: {len(all_trades)}")
    base_gross = sum(t["pnl"] for t in all_trades)
    base_carry = sum(trade_carry(t, t["wk"]) for t in all_trades)
    base_win = sum(1 for t in all_trades if t["pnl"] > 0) / len(all_trades) * 100
    print(f"Baseline (независимо): gross={base_gross:+,.0f} carry={base_carry:,.0f} "
          f"net={base_gross-base_carry:+,.0f} win={base_win:.0f}%")

    axes = [
        ("bar", _bar_key, 1),
        ("day", _day_key, 1),
        *[("window" + str(n), lambda tr, n=n: _window_key(tr, n), n) for n in windows],
    ]

    def _cluster_net(cluster: list[dict], mode: str) -> dict:
        """Обработка одной корзинки (>=2 тикера) по правилу mode."""
        if mode == "each_tp":
            gross = sum(x["pnl"] for x in cluster)
            carry = sum(trade_carry(x, x["wk"]) for x in cluster)
            wins = sum(1 for x in cluster if x["pnl"] > 0)
            return {"gross": gross, "carry": carry, "net": gross - carry,
                    "n": len(cluster), "wins": wins, "max_conc": len(cluster)}

        # all_first_tp: момент первого тейка среди тикеров корзинки (по пути цены).
        tp_events = []
        for x in cluster:
            df = df_map[x["ticker"]]
            tgt = x["swing_low"] or (x["entry"] * 0.95)
            ts = tp_reach_ts(df, x["open"], tgt)
            if ts is not None:
                tp_events.append((ts, x))
        if not tp_events:
            # никто не достиг цели — независимо
            gross = sum(x["pnl"] for x in cluster)
            carry = sum(trade_carry(x, x["wk"]) for x in cluster)
            wins = sum(1 for x in cluster if x["pnl"] > 0)
            return {"gross": gross, "carry": carry, "net": gross - carry,
                    "n": len(cluster), "wins": wins, "max_conc": len(cluster)}

        tp_events.sort(key=lambda e: e[0])
        tp_time = tp_events[0][0]
        gross = carry = 0.0
        wins = 0
        for x in cluster:
            df = df_map[x["ticker"]]
            exit_price = close_price_at(df, x["open"], tp_time)
            g = (x["entry"] - exit_price) * x["size"]
            gross += g
            wins += 1 if g > 0 else 0
            carry += _carry_rate(x["notional"]) * _nights_between(
                x["open"].date(), tp_time.date(), x["wk"])
        return {"gross": gross, "carry": carry, "net": gross - carry,
                "n": len(cluster), "wins": wins, "max_conc": len(cluster)}

    for name, key, _bn in axes:
        clusters: dict[str, list[dict]] = {}
        for tr in all_trades:
            clusters.setdefault(key(tr), []).append(tr)

        print(f"\n{'='*70}\nОсь кластеризации: {name}")
        sizes = [len(v) for v in clusters.values()]
        n2 = sum(1 for v in clusters.values() if len(v) >= 2)
        n3 = sum(1 for v in clusters.values() if len(v) >= 3)
        print(f"  кластеров: {len(clusters)} | avg={np.mean(sizes):.2f} | max={max(sizes)} "
              f"| с >=2: {n2} | с >=3: {n3}")

        for threshold in (2, 3):
            cl = {k: v for k, v in clusters.items() if len(v) >= threshold}
            if not cl:
                continue
            rows = {}
            for mode in ("each_tp", "all_first_tp"):
                agg = {"gross": 0.0, "carry": 0.0, "net": 0.0, "n": 0, "wins": 0, "max_conc": 0}
                for grp in cl.values():
                    r = _cluster_net(grp, mode)
                    for kk in ("gross", "carry", "net", "n", "wins"):
                        agg[kk] += r[kk]
                    # макс. число одновременных позиций в одной корзинке
                    agg["max_conc"] = max(agg["max_conc"], r["max_conc"])
                win = agg["wins"] / agg["n"] * 100 if agg["n"] else 0
                rows[mode] = agg
            # базлайн на подмножестве именно этих кластерных сделок
            base_sub_g = sum(x["pnl"] for grp in cl.values() for x in grp)
            base_sub_c = sum(trade_carry(x, x["wk"]) for grp in cl.values() for x in grp)
            e = rows["each_tp"]
            b = rows["all_first_tp"]
            print(f"  [>= {threshold} тикеров, {len(cl)} корзин]")
            print(f"    each_tp   (control) net={e['net']:+,.0f} gross={e['gross']:+,.0f} "
                  f"carry={e['carry']:,.0f} win={e['wins']/e['n']*100 if e['n'] else 0:.0f}% "
                  f"максКонц={e['max_conc']}")
            print(f"    ALL1st_TP (ваша идея) net={b['net']:+,.0f} gross={b['gross']:+,.0f} "
                  f"carry={b['carry']:,.0f} win={b['wins']/b['n']*100 if b['n'] else 0:.0f}% "
                  f"максКонц={b['max_conc']}")
            print(f"    независимо на подмножестве      net={base_sub_g-base_sub_c:+,.0f}")


if __name__ == "__main__":
    main()
