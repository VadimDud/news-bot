#!/usr/bin/env python3
"""Overfit demo: look-ahead parameter search on a small window, test on a large one.

Deliberately cheating experiment (lineage: user request "подобрать, заглядывая в
будущее настройки которые дают эйдж"). The search selects the best
``best-of-N`` parameter combination *on the test window itself* — that is the
look-ahead. Then the same parameters are re-run on the full history and on a
chronological split (earlier part = train, later part = holdout) to show how
much of the apparent edge survives.

This does NOT produce a tradeable result. It quantifies selection bias: how
large a gross backtest looks after searching N configurations on the same
sample, and how quickly it collapses.

It reuses the Fib short 1day config of FIB-SHORT-FUT-LQDT-001: stock short with
borrow carry (70/175 ₽/night) and the 0.05%/side commission + 0.05% slippage of
the original report.

Usage (from trading_moex/):
  python3 scripts/overfit_fib_short.py --db data/trader_4h.db --period 1day \
      --small-start 2025-06-01 --small-end 2026-09-01 --grid fast
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
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
CASH_PER_TICKER = 100_000.0
COMMISSION = 0.0005
SLIPPAGE = 0.0005
CARRY_SMALL = 70.0
CARRY_LARGE = 175.0

# Параметры, которые перебираются. Диапазоны взяты из того, что уже
# присутствует в прод-коде/скриптах проекта, а не выведены из результата.
GRID_FAST = {
    "trend_period": [50, 100, 200],
    "swing_bars": [5, 10],
    "min_rr": [1.0, 1.5],
    "fib_in_low": [0.382, 0.5, 0.618],
    "fib_in_high": [0.618, 0.786],
    "atr_stop_mult": [1.5, 2.5],
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
                "notional": notional,
                "pnl_gross": float(trade.pnlcomm or 0.0),
                "ticker": key,
            })
        super().notify_trade(trade)


def load_df(db: str, ticker: str, period: str) -> pd.DataFrame:
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


def run_window(df: pd.DataFrame, ticker: str, overrides: dict) -> dict:
    cb = _setup_cerebro(_Recorder, base_params(ticker, overrides), CASH_PER_TICKER,
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


def portfolio(frames: dict[str, pd.DataFrame], overrides: dict) -> dict:
    rows = [run_window(df, ticker, overrides) for ticker, df in frames.items() if not df.empty]
    gross = sum(r["gross"] for r in rows)
    carry = sum(r["carry"] for r in rows)
    return {
        "gross": round(gross, 2),
        "carry": round(carry, 2),
        "net": round(gross - carry, 2),
        "trades": sum(r["trades"] for r in rows),
        "active_tickers": sum(1 for r in rows if r["trades"]),
    }


def combos(grid: dict) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--small-start", default="2025-06-01")
    parser.add_argument("--small-end", default="2026-09-01")
    parser.add_argument("--split-at", default="2025-01-01",
                        help="Доп. хронологический раздел для большой истории")
    parser.add_argument("--grid", choices=("fast",), default="fast")
    parser.add_argument("--min-trades", type=int, default=10,
                        help="Мин. сделок в in-sample, чтобы комбинация участвовала в отборе")
    parser.add_argument("--baseline-random", type=int, default=25,
                        help="Сколько случайных комбинаций проверить на out-of-sample")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    frames = {t: load_df(args.db, t, args.period) for t in tickers}
    small = {t: window(df, args.small_start, args.small_end) for t, df in frames.items()}
    full = frames
    train = {t: window(df, None, args.split_at) for t, df in frames.items()}
    test = {t: window(df, args.split_at, None) for t, df in frames.items()}

    grid = GRID_FAST
    space = combos(grid)
    print(f"Сетка: {len(space)} комбинаций; in-sample {args.small_start}..{args.small_end}; "
          f"полная история и хроно-раздел @ {args.split_at}\n")

    # 1) Look-ahead подбор: метрика выбирается НА ТОМ ЖЕ окне, где затем
    #    репортится. Это и есть «заглядывание в будущее» по запросу.
    scored = []
    for params in space:
        result = portfolio(small, params)
        if result["trades"] >= args.min_trades:
            scored.append((params, result))
    if not scored:
        raise SystemExit("Ни одна комбинация не набрала min-trades в in-sample")
    scored.sort(key=lambda item: item[1]["net"], reverse=True)
    best_params, best_small = scored[0]
    print("ТОП-5 in-sample (метрика подобрана на том же окне — look-ahead):")
    for params, result in scored[:5]:
        print(f"  net={result['net']:>10,.0f} gross={result['gross']:>10,.0f} "
              f"trades={result['trades']:>4} {params}")

    selected = {
        "full": portfolio(full, best_params),
        "train": portfolio(train, best_params),
        "test": portfolio(test, best_params),
        "small_in_sample": best_small,
    }

    # 2) Контроль selection bias: случайные (неподобранные) комбинации на
    #    тех же окнах. Если они показывают похожий out-of-sample результат,
    #    «эйдж лучшей» комбинации — артефакт отбора.
    rng = random.Random(args.seed)
    sample = rng.sample(space, min(args.baseline_random, len(space)))
    if best_params in sample:
        sample.remove(best_params)
    random_test = [portfolio(test, params) for params in sample]
    random_full = [portfolio(full, params) for params in sample]

    def stats(values: list[float]) -> dict:
        if not values:
            return {"n": 0}
        ordered = sorted(values)
        return {
            "n": len(values),
            "mean": round(sum(values) / len(values), 2),
            "median": round(ordered[len(ordered) // 2], 2),
            "min": round(ordered[0], 2),
            "max": round(ordered[-1], 2),
        }

    print("\nЛУЧШАЯ (подобрана на in-sample) на разных периодах:")
    for name, result in selected.items():
        print(f"  {name:<16} net={result['net']:>11,.0f} gross={result['gross']:>10,.0f} "
              f"trades={result['trades']:>4} tickers={result['active_tickers']}")

    print(f"\nСлучайные {len(sample)} комбинаций на test и full:")
    print(f"  test net: {stats([r['net'] for r in random_test])}")
    print(f"  full net: {stats([r['net'] for r in random_full])}")

    report = {
        "study": "FIB-OVERFIT-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Look-ahead parameter selection by design; not a tradeable result.",
        "db": args.db,
        "period": args.period,
        "tickers": tickers,
        "costs": {"commission_per_side": COMMISSION, "slippage_per_side": SLIPPAGE,
                  "carry": {"<=100k": CARRY_SMALL, "<=250k": CARRY_LARGE}},
        "windows": {"small": [args.small_start, args.small_end], "split_at": args.split_at},
        "grid": grid,
        "combinations_scored": len(scored),
        "top5": [{"params": p, **r} for p, r in scored[:5]],
        "best": {"params": best_params, "selected": selected},
        "random": {
            "count": len(sample),
            "test_net": stats([r["net"] for r in random_test]),
            "full_net": stats([r["net"] for r in random_full]),
        },
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
