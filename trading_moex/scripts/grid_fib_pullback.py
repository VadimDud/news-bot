#!/usr/bin/env python3
"""Grid-search параметров Fib pullback по тикерам (per-ticker подбор).

Двухступенчатый перебор:
  1) Быстрый симулятор (векторный сигнал + брекет по swing-уровням на входе)
     — ранжирует конфиги по матожиданию на сделку;
  2) Реальный бэктестер (backtrader) — верифицирует top-N конфигов.

Входные данные — локальный кэш ``data/trader.db`` (MOEX с хоста недоступен).

Usage (из trading_moex/):
    python3 scripts/grid_fib_pullback.py --tickers MTSS,GAZP --direction -1 --top 5
    python3 scripts/grid_fib_pullback.py --direction -1 --top 5 --verify-only
    python3 scripts/grid_fib_pullback.py --direction 1 --top 5
"""
from __future__ import annotations

import argparse
import itertools
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app import fib_pullback as fibp  # noqa: E402

DEFAULT_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

# Пространство перебора (ключевые параметры направления).
GRID = {
    "swing_bars": [5, 10, 20],
    "trend_period": [50, 100, 200],
    "zone": [(0.382, 0.5), (0.5, 0.618), (0.618, 0.786)],
    "confluence_min": [1, 2],
    "rsi_thr": [30.0, 40.0, 50.0] if False else None,  # подставляется по направлению
}


def _grid_axes(direction: int) -> list[tuple[str, list]]:
    rsi = [30.0, 40.0, 50.0] if direction >= 0 else [70.0, 75.0, 80.0]
    return [
        ("swing_bars", GRID["swing_bars"]),
        ("trend_period", GRID["trend_period"]),
        ("zone", GRID["zone"]),
        ("confluence_min", GRID["confluence_min"]),
        ("rsi_thr", rsi),
    ]


def load_df(ticker: str, db_path: str) -> pd.DataFrame:
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles WHERE ticker=? ORDER BY begin",
        con, params=(ticker,),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def _simulate(df: pd.DataFrame, direction: int, params: dict) -> list[float]:
    """Быстрый симулятор: сигнал позиции → брекет по структуре на входе.

    Лонг: тейк = swing high (0%), стоп = swing low. Шорт — зеркально.
    Выход также по развороту тренда (EMA) на закрытии бара — как в стратегии.
    """
    df = fibp.prepare_ohlc(df)
    pos = fibp.fib_pullback_signal(df, direction=direction, **params)
    p = pos.values
    n = len(p)
    c = df["close"].values
    st = fibp._compute_arrays(
        df, None,
        swing_bars=params["swing_bars"], trend_period=params["trend_period"],
        confluence_min=params["confluence_min"],
    )
    sl = st["swing_low"]
    sh = st["swing_high"]
    ema = df["close"].ewm(span=params["trend_period"], adjust=False).mean().values
    pnls: list[float] = []
    for i in range(1, n):
        if p[i] == 1 and p[i - 1] != 1:
            entry = c[i]
            tgt, stop = sh[i], sl[i]
            for j in range(i + 1, n):
                if not np.isnan(tgt) and c[j] >= tgt:
                    pnls.append((tgt - entry) / entry)
                    break
                if not np.isnan(stop) and c[j] <= stop:
                    pnls.append((c[j] - entry) / entry)
                    break
                if not np.isnan(ema[j]) and c[j] < ema[j]:
                    pnls.append((c[j] - entry) / entry)
                    break
        elif p[i] == -1 and p[i - 1] != -1:
            entry = c[i]
            tgt, stop = sl[i], sh[i]
            for j in range(i + 1, n):
                if not np.isnan(tgt) and c[j] <= tgt:
                    pnls.append((entry - c[j]) / entry)
                    break
                if not np.isnan(stop) and c[j] >= stop:
                    pnls.append((entry - c[j]) / entry)
                    break
                if not np.isnan(ema[j]) and c[j] > ema[j]:
                    pnls.append((entry - c[j]) / entry)
                    break
    return pnls


def _config_key(direction: int, combo: dict) -> tuple:
    return (combo["swing_bars"], combo["trend_period"], combo["zone"], combo["confluence_min"], combo["rsi_thr"])


def fast_grid(ticker: str, direction: int, db_path: str) -> list[tuple[dict, dict]]:
    """Перебор на быстром симуляторе: возвращает отсортированный список (params, stats)."""
    df = load_df(ticker, db_path)
    axes = _grid_axes(direction)
    keys = [k for k, _ in axes]
    results: list[tuple[dict, dict]] = []
    for combo_vals in itertools.product(*[v for _, v in axes]):
        combo = dict(zip(keys, combo_vals))
        lo, hi = combo["zone"]
        params = {
            "swing_bars": combo["swing_bars"],
            "trend_period": combo["trend_period"],
            "confluence_min": combo["confluence_min"],
            "fib_in_low": lo,
            "fib_in_high": hi,
        }
        if direction >= 0:
            params["rsi_oversold"] = combo["rsi_thr"]
            params["rsi_overbought"] = 85.0
        else:
            params["rsi_overbought"] = combo["rsi_thr"]
            params["rsi_oversold"] = 40.0
        params["min_rr"] = 1.0
        pnls = _simulate(df, direction, params)
        if not pnls:
            continue
        a = np.array(pnls)
        stats = {
            "n": len(a),
            "win_pct": round((a > 0).mean() * 100, 1),
            "exp_pct": round(a.mean() * 100, 2),
            "tot_pct": round(a.sum() * 100, 2),
        }
        results.append((params, stats))
    # Ранжирование: матожидание при достаточной выборке (n >= 4)
    def score(item):
        _, st_ = item
        if st_["n"] < 4:
            return (-1e9,)
        return (st_["exp_pct"], st_["n"])
    results.sort(key=score, reverse=True)
    return results


def verify(ticker: str, direction: int, params: dict, db_path: str) -> dict:
    """Реальный бэктест одного конфига."""
    import backtrader as bt

    from app.backtest import _setup_cerebro
    from app.strategies import FibPullbackStrategy, _FIB_PULLBACK_PARAMS_TUPLE

    class Spy(FibPullbackStrategy):
        def __init__(self):
            super().__init__()
            self._pn: list[float] = []

        def notify_trade(self, trade):
            if trade.isclosed:
                self._pn.append(float(trade.pnlcomm or 0))
            super().notify_trade(trade)

    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    p.update(params)
    p["direction"] = direction
    cb = _setup_cerebro(Spy, p, 100_000, 0.0005)
    cb.adddata(bt.feeds.PandasData(dataname=load_df(ticker, db_path)))
    strat = cb.run(runonce=False)[0]
    pnls = strat._pn
    if not pnls:
        return {"n": 0}
    a = np.array(pnls)
    return {
        "n": len(a),
        "win_pct": round((a > 0).mean() * 100, 1),
        "exp": round(float(a.mean()), 1),
        "tot": round(float(a.sum()), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid-search Fib pullback per-ticker")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--direction", type=int, default=-1, help="1 лонг / -1 шорт")
    parser.add_argument("--top", type=int, default=5, help="сколько конфигов верифицировать бэктестом")
    parser.add_argument("--verify-only", action="store_true", help="пропустить быстрый перебор")
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader.db"))
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    cache: dict[str, list[tuple[dict, dict]]] = {}
    for ticker in tickers:
        ranked = fast_grid(ticker, args.direction, args.db)
        cache[ticker] = ranked
        top3 = ranked[:3]
        print(f"\n=== {ticker} dir={args.direction} — топ быстрого перебора ===")
        for params, stats in top3:
            print(f"  {stats} | {params}")

    print("\n=== Верификация реальным бэктестером ===")
    for ticker in tickers:
        for params, stats in cache[ticker][: args.top]:
            v = verify(ticker, args.direction, params, args.db)
            if v["n"] == 0:
                print(f"{ticker}: sim {stats} | BT: нет сделок")
                continue
            print(
                f"{ticker}: sim n={stats['n']} exp={stats['exp_pct']:+.2f}% | "
                f"BT n={v['n']} win={v['win_pct']:.0f}% exp={v['exp']:+.0f} tot={v['tot']:+.0f}"
                f" | {params['swing_bars']}/{params['trend_period']}/"
                f"{params['fib_in_low']}-{params['fib_in_high']}/conf{params['confluence_min']}"
            )


if __name__ == "__main__":
    main()
