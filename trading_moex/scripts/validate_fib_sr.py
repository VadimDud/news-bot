#!/usr/bin/env python3
"""Валидация FIB-SR-001: хроно train/test + контроль случайными уровнями.

Лучший вариант брекета (sr_min_sl: sr_tp_mode=2, sr_sl_mode=1) сравнивается с
baseline на хронологическом разделе (train < split, test >= split). Дополнительно
"случайные уровни" — тот же брекет, но позиции уровней заменены случайными
ценами в диапазоне истории (сид фиксирован). Если случайные уровни дают такой
же прирост, edge объясняется не структурой S/R, а артефактом (например, тем,
что любой близкий уровень сокращает удержание).

Метрика: gross (перенос исключён, чтобы изолировать сигнальный edge) и net с
переносом. Тикеры — прод-набор Fib short 1day.

Usage (from trading_moex/):
    python3 scripts/validate_fib_sr.py --db data/trader_4h.db --period 1day \
        --split-at 2025-01-01 --random-seeds 20
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import backtrader as bt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
CASH_PER_TICKER = 100_000.0
COMMISSION = 0.0005
SLIPPAGE = 0.0005
CARRY_SMALL = 70.0
CARRY_LARGE = 175.0

BASELINE = {}
SR_MIN_SL = {"sr_tp_mode": 2, "sr_sl_mode": 1}


def load_df(db: str, ticker: str, period: str) -> pd.DataFrame:
    con = __import__("sqlite3").connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def window(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    out = df
    if start:
        out = out[out.index >= pd.Timestamp(start)]
    if end:
        out = out[out.index < pd.Timestamp(end)]
    return out


def base_params(ticker: str, overrides: dict) -> dict:
    params = dict(_FIB_PULLBACK_PARAMS_TUPLE)
    for key, value in TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {}).items():
        if key not in ("direction", "timeframe"):
            params[key] = value
    params["direction"] = -1
    params["flat_mode"] = 0
    params.update(overrides)
    return params


def _has_weekend(df: pd.DataFrame) -> bool:
    dow = df.index.dayofweek
    return bool((dow == 5).any() or (dow == 6).any())


def nights_held(op, close, weekend_trading: bool) -> int:
    carries = 0
    cur = op.date()
    while cur < close.date():
        nxt = cur + timedelta(days=1)
        if weekend_trading:
            carries += 1
        elif nxt.weekday() == 5:
            carries += 3
        elif nxt.weekday() < 5:
            carries += 1
        cur = nxt
    return carries


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
                "notional": notional,
                "pnl_gross": float(trade.pnlcomm or 0.0),
            })
        super().notify_trade(trade)


class _RandomLevels(_Recorder):
    """Same bracket as parent, but S/R positions are random prices.

    Uses a per-instance seeded RNG to draw the level that the bracket consumes.
    """

    _seed_counter = 0

    def __init__(self):
        super().__init__()
        _RandomLevels._seed_counter += 1
        self._rng = np.random.default_rng(self._seed_counter)

    def _sr_levels(self) -> list[float]:
        price = float(self.data.close[0])
        if price <= 0:
            return []
        # Случайное число уровней (3..7), распределённых в ±15% от цены.
        n = int(self._rng.integers(3, 8))
        return list(self._rng.uniform(price * 0.85, price * 1.15, n))


def run_window(df: pd.DataFrame, ticker: str, overrides: dict, cls=_Recorder) -> dict:
    cb = _setup_cerebro(cls, base_params(ticker, overrides), CASH_PER_TICKER,
                        COMMISSION, slippage=SLIPPAGE)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    weekend = _has_weekend(df)
    gross = carry = 0.0
    for trade in strat.closed:
        gross += trade["pnl_gross"]
        nights = nights_held(trade["open"], trade["close"], weekend)
        rate = CARRY_SMALL if trade["notional"] <= 100_000 else CARRY_LARGE
        carry += rate * nights
    return {"gross": gross, "carry": carry, "net": gross - carry, "trades": len(strat.closed)}


def portfolio(frames: dict[str, pd.DataFrame], overrides: dict, cls=_Recorder) -> dict:
    rows = [run_window(df, ticker, overrides, cls) for ticker, df in frames.items() if not df.empty]
    gross = sum(r["gross"] for r in rows)
    carry = sum(r["carry"] for r in rows)
    return {
        "gross": round(gross, 2),
        "carry": round(carry, 2),
        "net": round(gross - carry, 2),
        "trades": sum(r["trades"] for r in rows),
        "tickers": sum(1 for r in rows if r["trades"]),
    }


def fmt(label: str, r: dict) -> str:
    return (f"  {label:<26} gross={r['gross']:>10,.0f} carry={r['carry']:>9,.0f} "
            f"net={r['net']:>10,.0f} trades={r['trades']:>4}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--split-at", default="2025-01-01")
    parser.add_argument("--random-seeds", type=int, default=20,
                        help="Сколько случайных прогонов уровней")
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    frames = {t: load_df(args.db, t, args.period) for t in tickers}
    train = {t: window(df, None, args.split_at) for t, df in frames.items()}
    test = {t: window(df, args.split_at, None) for t, df in frames.items()}

    print(f"FIB-SR-001 validation | хроно-раздел @ {args.split_at}\n")

    res = {}
    for name, overrides in (("baseline", BASELINE), ("sr_min_sl", SR_MIN_SL)):
        res[name] = {
            "full": portfolio(frames, overrides),
            "train": portfolio(train, overrides),
            "test": portfolio(test, overrides),
        }

    print("Портфель (gross / carry / net):")
    for name in ("baseline", "sr_min_sl"):
        for part in ("full", "train", "test"):
            print(fmt(f"{name} {part}", res[name][part]))
        print()

    # Прирост sr_min_sl над baseline по gross в каждом окне.
    print("Δ(mut sr_min_sl − baseline):")
    deltas = {}
    for part in ("full", "train", "test"):
        d = {k: round(res["sr_min_sl"][part][k] - res["baseline"][part][k], 2)
             for k in ("gross", "net", "trades")}
        deltas[part] = d
        print(f"  {part:<6} gross={d['gross']:>+10,.0f} net={d['net']:>+10,.0f} "
              f"trades={d['trades']:>+4}")

    # Контроль: те же брекет-настройки, но случайные уровни.
    random_gross = []
    for _ in range(args.random_seeds):
        r = portfolio(test, SR_MIN_SL, cls=_RandomLevels)
        random_gross.append(r["gross"])
    arr = np.array(random_gross)
    real_delta = deltas["test"]["gross"]
    p_ge = float((arr >= real_delta).mean()) if len(arr) else 1.0
    print(f"\nСлучайные уровни (test, {len(arr)} прогонов), Δgross над baseline:")
    print(f"  mean={arr.mean():>+10,.0f} median={np.median(arr):>+10,.0f} "
          f"min={arr.min():>+10,.0f} max={arr.max():>+10,.0f}")
    print(f"  Δgross реального S/R = {real_delta:>+10,.0f}; "
          f"p(случайный ≥ реального) = {p_ge:.2f}")

    verdict = "supported" if real_delta > 0 and p_ge < 0.10 else "not supported"
    if deltas["train"]["gross"] <= 0 or deltas["test"]["gross"] <= 0:
        verdict = "not supported (edge absent in a split half)"
    print(f"\nВЕРДИКТ: {verdict}")

    report = {
        "study": "FIB-SR-001-validation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db": args.db,
        "period": args.period,
        "tickers": tickers,
        "split_at": args.split_at,
        "results": res,
        "deltas": deltas,
        "random_control": {
            "runs": len(arr),
            "test_delta_gross_mean": round(float(arr.mean()), 2),
            "test_delta_gross_median": round(float(np.median(arr)), 2),
            "p_random_ge_real": round(p_ge, 4),
        },
        "verdict": verdict,
    }
    if args.run_dir:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        print(f"\nАртефакты: {run_dir}")


if __name__ == "__main__":
    main()
