#!/usr/bin/env python3
"""Автономная демонстрация PA-уровней: синтетика + загрузка CSV/ccxt/yfinance.

Это «вариант B» из запроса: standalone-пример кода без привязки к БД проекта.
Показывает полный конвейер на синтетических данных и как подключить реальный
источник (CSV, ccxt для крипты, yfinance для акций).

Бэктест — тот же, что в ``scripts/backtest_pa_levels.py`` (стоп/тейк/безубыток/
трейлинг, издержки), но данные берутся из выбранного источника.

Usage:
    # синтетика
    python3 scripts/pa_levels_demo.py --source synthetic
    # CSV с колонками time,open,high,low,close,volume
    python3 scripts/pa_levels_demo.py --source csv --csv-path data.csv
    # ccxt (Binance, BTC/USDT, 1h, последние 1000 свечей)
    python3 scripts/pa_levels_demo.py --source ccxt --symbol BTC/USDT --timeframe 1h
    # yfinance (SBER.ME, 1d)
    python3 scripts/pa_levels_demo.py --source yfinance --symbol SBER.ME --interval 1d
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.pa_levels import PALevelParams, generate_signals  # noqa: E402
from scripts.backtest_pa_levels import metrics, simulate_trades  # noqa: E402


def synthetic_ohlcv(n: int = 1500, seed: int = 7) -> pd.DataFrame:
    """Генерирует OHLCV со сменой трендов и объёмными всплесками."""
    rng = np.random.default_rng(seed)
    price = [100.0]
    vol = []
    for i in range(n):
        # тренд меняется каждые ~200 баров
        drift = 0.03 if (i // 200) % 2 == 0 else -0.03
        price.append(price[-1] * (1 + drift * 0.05 + rng.normal(0, 0.01)))
        vol.append(float(rng.lognormal(10, 0.5)))
    close = np.array(price[1:])
    open_ = np.array(price[:-1])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.004, n)))
    vol = np.array(vol)
    # редкие объёмные всплески — для VSA/sweep
    spikes = rng.choice(n, size=n // 40, replace=False)
    vol[spikes] *= 4.0
    idx = pd.date_range("2023-01-01", periods=n, freq="h")
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": vol}, index=idx)


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    time_col = next((cols[k] for k in ("time", "datetime", "date", "begin") if k in cols), None)
    if time_col is None:
        raise SystemExit("CSV должен содержать колонку time/datetime/date")
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col).sort_index()
    renames = {cols[k]: k for k in ("open", "high", "low", "close", "volume") if k in cols}
    df = df.rename(columns=renames)
    need = {"open", "high", "low", "close", "volume"}
    if not need.issubset(df.columns):
        raise SystemExit(f"CSV не содержит {need - set(df.columns)}")
    return df[list(need)]


def load_ccxt(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    try:
        import ccxt  # type: ignore
    except ImportError:
        raise SystemExit("Установите ccxt: pip install ccxt")
    ex = ccxt.binance()
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df.set_index("ts")


def load_yfinance(symbol: str, interval: str) -> pd.DataFrame:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        raise SystemExit("Установите yfinance: pip install yfinance")
    raw = yf.download(symbol, interval=interval, auto_adjust=True)
    if raw.empty:
        raise SystemExit(f"yfinance не вернул данные для {symbol}")
    raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
    return raw[["open", "high", "low", "close", "volume"]].dropna()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("synthetic", "csv", "ccxt", "yfinance"),
                        default="synthetic")
    parser.add_argument("--csv-path", default="data.csv")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0005)
    args = parser.parse_args()

    if args.source == "synthetic":
        df = synthetic_ohlcv()
        label = "synthetic(hourly)"
    elif args.source == "csv":
        df = load_csv(args.csv_path)
        label = f"csv:{args.csv_path}"
    elif args.source == "ccxt":
        df = load_ccxt(args.symbol, args.timeframe, args.limit)
        label = f"ccxt:{args.symbol} {args.timeframe}"
    else:
        df = load_yfinance(args.symbol, args.interval)
        label = f"yfinance:{args.symbol} {args.interval}"

    print(f"Источник: {label} | баров: {len(df)} | {df.index.min()} .. {df.index.max()}")

    p = PALevelParams()
    sig = generate_signals(df, p)
    sig["ticker"] = label
    print(f"Сигналов: {len(sig)} "
          f"(long={int((sig['side'] == 1).sum()) if len(sig) else 0}, "
          f"short={int((sig['side'] == -1).sum()) if len(sig) else 0})")

    trades = simulate_trades(df, sig, p, args.commission, args.slippage)
    m = metrics(trades)
    print(f"\nСделок={m['trades']} win={m['winrate']}% PF={m['pf']} "
          f"avgR={m['avg_r']:+.3f} maxDD={m['max_dd']:,.2f} NET={m['net']:+,.2f}")

    if trades:
        cols = ["side", "entry_time", "entry", "exit", "r_multiple", "reason", "reasons"]
        print("\nСделки:")
        print(pd.DataFrame(trades)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
