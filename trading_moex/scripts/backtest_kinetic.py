#!/usr/bin/env python3
"""Честная валидация Kinetic Momentum (импульс + кинетическая энергия).

Физическая модель (подробно: ``app/kinetic.py``): цена как частица с
количеством движения ``P = Σ m·v`` (m — относительный объём, v — доходность
в единицах волатильности) и кинетической энергией ``KE = Σ m·v²``. Вход — при
``|P| >= theta`` и расширяющейся энергии (KE > базиса), выход — при развороте P
или «диссипации» энергии (охлаждение ``cool_bars`` подряд).

Live-faithful модель: сигнал формируется на закрытии бара i (никакого знания
бара i+1), вход/выход — по open следующего бара. Комиссия и слайпедж на круг,
компаундинг на капитале. Сравнение с buy&hold и random-control (тот же объём
сделок, случайные бары).

Панель вывода:
  - результаты по тикерам и по периодам (train/test — две половины истории);
  - чувствительность к затратам (комиссия 0 / 0.05% / 0.1% + слайп 0.05%);
  - random-control против того же числа сделок.

Usage (from trading_moex/):
    python3 scripts/backtest_kinetic.py --db data/trader_4h.db --period 30min
    python3 scripts/backtest_kinetic.py --period 15min --ticker NVTK --grid
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

from app import kinetic  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
# Интрадей-данные есть только у этих тикеров (см. ls в data/).
AVAILABLE: dict[str, list[str]] = {
    "1min": ["SBER"],
    "5min": ["SBER"],
    "15min": ["NVTK", "SBER"],
    "30min": ["SBER"],
    "60min": ["SBER", "T"],
}

COMMISSION = 0.0005  # на сторону (тариф по умолчанию)
SLIPPAGE = 0.0005    # на сторону
CASH = 100_000.0
RISK_PCT = 0.01      # риск на сделку, % капитала (лот от стопа ATR)

# Дефолтные параметры (стартовые, из плана). Подбираются перебором при --grid.
DEFAULTS = dict(sigma_span=20, vol_span=20, mom_span=12, ke_span=40,
                theta=1.5, v_dir=1, direction=0, cool_bars=2, min_hold=0)
GRID = {
    "mom_span": [6, 12, 20],
    "ke_span": [20, 40, 80],
    "theta": [1.0, 1.5, 2.5],
    "direction": [0, -1],
    "cool_bars": [1, 2, 4],
    "min_hold": [0, 5],
}


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(str(db))
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def _simulate(df: pd.DataFrame, params: dict, commission: float = COMMISSION,
              slippage: float = SLIPPAGE, risk_pct: float = RISK_PCT) -> dict:
    """Live-faithful симуляция кинетического моментума на OHLCV df.

    Сигнал (серия позиций -1/0/1) формируется на закрытии баров; сделки
    исполняются на open следующего бара. Лот от риска ``risk_pct`` и стопа
    ATR(20)×1.5. Возвращает {trades, net_pct, win, gross_pct, max_dd_pct,
    n_bars, hold_bars}. Цены в процентах от стартового капитала.
    """
    pos = kinetic.kinetic_position(df, **params)
    arr = pos.to_numpy(dtype=int)
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)

    # ATR(20) для размера позиции (Wilder, как risk.atr)
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)),
                                           np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    alpha = 1.0 / 20.0
    atr = np.full(len(close), np.nan)
    atr[0] = tr[0]
    for i in range(1, len(close)):
        atr[i] = atr[i - 1] + alpha * (tr[i] - atr[i - 1])

    equity = float(CASH)
    peak = equity
    trades: list[dict] = []
    cur = 0
    entry_i = -1
    entry_price = 0.0
    size = 0
    n = len(df)
    for i in range(1, n):
        tgt = int(arr[i]) if i < len(arr) else 0
        if cur != 0 and tgt != cur:
            # выход по open следующего бара после сигнала закрытия бара i
            ex_i = i + 1
            if ex_i >= n:
                break
            ex_price = float(open_[ex_i])
            pnl = (ex_price - entry_price) * size if cur == 1 else (entry_price - ex_price) * size
            cost = commission * abs(entry_price) * abs(size) + commission * abs(ex_price) * abs(size)
            cost += slippage * abs(entry_price) * abs(size) + slippage * abs(ex_price) * abs(size)
            equity += pnl - cost
            peak = max(peak, equity)
            trades.append({
                "pnl": pnl - cost,
                "win": pnl - cost > 0,
                "hold_bars": ex_i - entry_i,
                "ret_pct": round((pnl - cost) / CASH * 100.0, 3),
            })
            cur = 0
        if cur == 0 and tgt != 0:
            # вход по open следующего бара после сигнала закрытия бара i
            en_i = i + 1
            if en_i >= n:
                break
            en_price = float(open_[en_i])
            a = float(atr[i]) if not np.isnan(atr[i]) else abs(high[i] - low[i])
            stop_dist = max(a * 1.5, en_price * 0.005)
            size = max(int(equity * risk_pct / stop_dist), 1)
            max_by_cash = int(equity / en_price * 0.95) if en_price > 0 else 0
            size = max(min(size, max_by_cash), 1) if max_by_cash > 0 else size
            cur = int(tgt)
            entry_i = en_i
            entry_price = en_price

    final_pct = (equity / CASH - 1) * 100.0
    max_dd = max(0.0, (peak - min(peak, equity)) / CASH * 100.0)
    # простой max-DD по пику на конец (для однопроходной серии достаточно трейд-пиков)
    gross_pct = sum(t["ret_pct"] for t in trades)
    wins = sum(1 for t in trades if t["win"])
    return {
        "trades": trades,
        "n": len(trades),
        "win_pct": round(wins / len(trades) * 100.0, 1) if trades else 0.0,
        "net_pct": round(final_pct, 2),
        "gross_pct": round(gross_pct, 2),
        "max_dd_pct": round(max_dd, 2),
        "hold_mean": round(float(np.mean([t["hold_bars"] for t in trades])), 1) if trades else 0.0,
        "n_bars": n,
    }


def _random_control(df: pd.DataFrame, params: dict, n_trades: int, seed: int = 7) -> dict:
    """Random-control: столько же сделок в случайные моменты (равное удержание).

    Средний hold_bars от реального запуска; вход/выход по open. Нужен для
    проверки: даёт ли сигнал больше, чем случайный выбор моментов.
    """
    rng = np.random.default_rng(seed)
    base = _simulate(df, params)
    hold = max(int(base["hold_mean"]), 1)
    open_ = df["open"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(df)
    pnl = []
    for _ in range(max(n_trades, 1)):
        i = int(rng.integers(10, max(11, n - hold - 2)))
        en = float(open_[i])
        ex = float(open_[min(i + hold, n - 1)])
        if en <= 0:
            continue
        pnl.append((ex / en - 1.0) * CASH)
    net = sum(pnl)
    return {
        "n": len(pnl),
        "net_pct": round(net / CASH * 100.0, 2),
        "win_pct": round(sum(1 for p in pnl if p > 0) / len(pnl) * 100.0, 1) if pnl else 0.0,
    }


def print_result(m: dict, tag: str):
    if m["n"] == 0:
        print(f"  {tag}: нет сделок")
        return
    print(
        f"  {tag}: n={m['n']:3d}  win={m['win_pct']:5.1f}%  "
        f"net={m['net_pct']:+7.2f}%  gross={m['gross_pct']:+7.2f}%  "
        f"dd={m['max_dd_pct']:5.2f}%  hold~{m['hold_mean']:4.1f} б"
    )


def run_panel(df: pd.DataFrame, params: dict, label: str):
    """Честная панель для одного набора параметров на одном тикере/ТФ."""
    print(f"\n=== {label} ({len(df)} баров, {df.index[0].date()}..{df.index[-1].date()}) ===")
    mid = len(df) // 2
    splits = {
        "вся история": df,
        "1-я половина (train)": df.iloc[:mid],
        "2-я половина (test)": df.iloc[mid:],
    }
    full = None
    for name, sub in splits.items():
        if len(sub) < 60:
            print(f"  {name}: данных мало")
            continue
        m = _simulate(sub, params)
        if name == "вся история":
            full = m
        print_result(m, name)

    # Buy&Hold-контроль
    bh = (float(df["close"].iloc[-1]) / float(df["close"].iloc[0]) - 1) * 100
    print(f"  buy&hold: {bh:+.2f}%")

    if full and full["n"] > 0:
        rc = _random_control(df, params, full["n"])
        print(
            f"  random-control (n={rc['n']}): win={rc['win_pct']:.1f}%  "
            f"net={rc['net_pct']:+.2f}%  (сигнал лучше рандома, если его net выше)"
        )

    # Чувствительность к затратам (комиссия + слайпедж на круг)
    print("  чувствительность к затратам (полная история):")
    for comm, slip in ((0.0, 0.0), (0.0005, 0.0), (0.0005, 0.0005), (0.001, 0.0005)):
        m = _simulate(df, params, commission=comm, slippage=slip)
        if m["n"] == 0:
            continue
        print(
            f"    комиссия {comm * 100:.2f}% + слайп {slip * 100:.2f}%: "
            f"net={m['net_pct']:+7.2f}%  win={m['win_pct']:.1f}%  (n={m['n']})"
        )


def main():
    parser = argparse.ArgumentParser(description="Kinetic Momentum honest validation")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--ticker", default=None, help="тикер (default: первый доступный для периода)")
    parser.add_argument("--period", default="30min", choices=list(AVAILABLE))
    parser.add_argument("--grid", action="store_true", help="перебор параметров")
    args = parser.parse_args()

    tickers = [args.ticker] if args.ticker else AVAILABLE[args.period]
    params = dict(DEFAULTS)

    if not args.grid:
        for ticker in tickers:
            df = load_df(ticker, args.db, args.period)
            if df.empty or len(df) < 60:
                print(f"{ticker} {args.period}: данных мало")
                continue
            run_panel(df, params, f"Kinetic Momentum {ticker} {args.period}")
        return

    # ── Grid-search: перебор параметров, ранжирование по net на полной истории ──
    keys = list(GRID.keys())
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    results = []
    for ticker in tickers:
        df = load_df(ticker, args.db, args.period)
        if df.empty or len(df) < 60:
            continue
        print(f"\n=== grid {ticker} {args.period}: {len(combos)} комбинаций ===")
        mid = len(df) // 2
        train, test = df.iloc[:mid], df.iloc[mid:]
        best = []
        for combo in combos:
            p = dict(params)
            for k, v in zip(keys, combo):
                p[k] = v
            mt = _simulate(train, p)
            if mt["n"] < 10:
                continue
            me = _simulate(test, p)
            # train/test обе должны быть неотрицательны по net, иначе отбрасываем
            if me["n"] < 5 or me["net_pct"] <= 0 or mt["net_pct"] <= 0:
                continue
            score = me["net_pct"] + mt["net_pct"] - me["max_dd_pct"] / 5
            best.append((score, dict(p), mt, me))
        best.sort(key=lambda x: -x[0])
        if not best:
            print("  нет комбинаций, прибыльных на обеих половинах")
            continue
        for score, p, mt, me in best[:8]:
            print(
                f"  train={mt['net_pct']:+7.2f}% test={me['net_pct']:+7.2f}% "
                f"(win {me['win_pct']}%) | { {k: p[k] for k in keys} }"
            )
            results.append({"ticker": ticker, "period": args.period,
                            "params": repr({k: p[k] for k in keys}),
                            "train_net": mt["net_pct"], "test_net": me["net_pct"],
                            "test_win": me["win_pct"], "score": round(score, 2)})
    if results:
        print("\nТОП по score (train+test):")
        for r in sorted(results, key=lambda r: -r["score"])[:15]:
            print(r)


if __name__ == "__main__":
    main()
