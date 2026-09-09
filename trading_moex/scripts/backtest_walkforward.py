#!/usr/bin/env python3
"""Walk-forward / out-of-sample validation for Fib and ROE production configs.

The point: parameters were tuned on a single historical window. This checks how
the SAME production config performs on multiple displaced chronological folds,
so we can see whether edge is stable or just a cherry-picked window.

Production config is read from the same sources as the live notifier:
  - Fib: ``strategy_defaults("fib_pullback", ticker)`` (TICKER_OVERRIDES) on the
    per-ticker ``timeframe``.
  - ROE: ``TRADER_ROE_*`` scoring config (backtest_all.py base_params).

Usage (from repo root; 4h data lives in trader_4h.db):
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_walkforward.py \
        --strategy fib --tickers LKOH,T
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_walkforward.py \
        --strategy fib --tickers MTSS,SBER --folds 3
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_walkforward.py \
        --strategy roe --tickers SBER,LKOH,T
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import config as cfg
from app.backtest import run_backtest, run_portfolio_backtest
from app.fundamentals import prepare_fundamentals_series
from app.strategies import FibPullbackStrategy, ROEPortfolioStrategy, strategy_defaults
from app import storage

COMMISSION = 0.0005
DEFAULT_4H_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"


def load_4h_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    df.index.name = "datetime"
    return df[~df.index.duplicated(keep="last")]


def load_day_df(ticker: str) -> pd.DataFrame | None:
    raw = storage.get_candles(ticker, "1day")
    if raw.empty:
        return None
    df = raw.copy()
    df["begin"] = pd.to_datetime(df["begin"])
    df = df.set_index("begin").sort_index()[["open", "high", "low", "close", "volume"]]
    df.index.name = "datetime"
    return df


def fold_ranges(df: pd.DataFrame, folds: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    idx = df.index.unique().sort_values()
    n = len(idx)
    if folds <= 1:
        return [(idx[0], idx[-1])]
    bounds = [i * n // folds for i in range(folds + 1)]
    return [(idx[a], idx[min(b, n - 1)]) for a, b in zip(bounds, bounds[1:])]


def _print_metrics(m: dict, tag: str):
    if m.get("trades_total", 0) == 0:
        print(f"  {tag}: нет сделок  ret={m['total_return_pct']:+.2f}%")
        return
    print(
        f"  {tag}: ret={m['total_return_pct']:+.2f}%  trades={m['trades_total']}  "
        f"win={m['win_rate_pct']:.1f}%  pf={m['profit_factor']}  dd={m['max_drawdown_pct']:.2f}%"
    )


def fib_prod_params(ticker: str) -> dict:
    """Production Fib params for a ticker: defaults + TICKER_OVERRIDES."""
    p = strategy_defaults("fib_pullback", ticker)
    if "min_swing_dist_atr" not in p:
        p["min_swing_dist_atr"] = 2.0
    # direction из оверрайда (как у fib_notifier.ticker_settings)
    from app.strategies import TICKER_OVERRIDES
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    p["direction"] = int(over.get("direction", -1))
    return p


def fib_timeframe(ticker: str) -> str:
    from app.strategies import TICKER_OVERRIDES
    return str(TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {}).get("timeframe", "4h"))


def run_fib(tickers, db, folds):
    for ticker in tickers:
        tf = fib_timeframe(ticker)
        df = load_4h_df(ticker, db, tf)
        if df.empty or len(df) < 60:
            print(f"\n{ticker} {tf}: данных мало/нет")
            continue
        print(f"\n=== FIB walk-forward {ticker} {tf} ({len(df)} bars, {folds} folds) ===")

        ranges = fold_ranges(df, folds)
        rets = []
        for i, (lo, hi) in enumerate(ranges):
            seg = df[(df.index >= lo) & (df.index <= hi)]
            if len(seg) < 60:
                print(f"  fold {i} ({lo.date()}..{hi.date()}): слишком мало баров")
                continue
            params = fib_prod_params(ticker)
            m = run_backtest(seg, FibPullbackStrategy, params, cash=100_000.0, commission=COMMISSION)
            print(f"  fold {i} ({lo.date()}..{hi.date()}, {len(seg)} bars):")
            _print_metrics(m, "prod")
            rets.append(m["total_return_pct"])

        if rets:
            wins = sum(1 for r in rets if r > 0)
            print(
                f"  ── сводка: fold-возвраты {['%+.2f' % r for r in rets]} | "
                f"положительных {wins}/{len(rets)} | avg {sum(rets)/len(rets):+.2f}%"
            )


def roe_prod_params() -> dict:
    return dict(
        min_avg_roe=cfg.TRADER_ROE_MIN_AVG_ROE,
        min_single_roe=cfg.TRADER_ROE_MIN_SINGLE_ROE,
        pb_entry=cfg.TRADER_ROE_PB_ENTRY,
        pb_exit=cfg.TRADER_ROE_PB_EXIT,
        roe_exit=cfg.TRADER_ROE_ROE_EXIT,
        max_positions=4,
        rebalance_days=cfg.TRADER_ROE_REBALANCE_DAYS,
        cash_yield=cfg.TRADER_ROE_CASH_YIELD,
        scoring=1,
        min_score=cfg.TRADER_ROE_MIN_SCORE,
        w_roe=cfg.TRADER_ROE_W_ROE,
        w_pb=cfg.TRADER_ROE_W_PB,
        w_momentum=cfg.TRADER_ROE_W_MOMENTUM,
        w_dividend=cfg.TRADER_ROE_W_DIVIDEND,
        w_stability=cfg.TRADER_ROE_W_STABILITY,
        momentum_months=6,
        stop_loss_pct=cfg.TRADER_ROE_STOP_LOSS_PCT,
    )


def run_roe(tickers):
    data_map, fund_map, divs_map = {}, {}, {}
    for t in tickers:
        df = load_day_df(t)
        if df is None:
            print(f"  SKIP {t}: no candles")
            continue
        fund = prepare_fundamentals_series(t, df.index.min().date(), df.index.max().date())
        if fund is None or fund.empty:
            print(f"  SKIP {t}: no fundamentals")
            continue
        data_map[t] = df
        fund_map[t] = fund
        div_df = storage.load_dividends(t)
        if not div_df.empty:
            divs_map[t] = div_df

    if not data_map:
        print("No data.")
        return

    common_min = max(df.index.min() for df in data_map.values())
    common_max = min(df.index.max() for df in data_map.values())
    print(f"\n=== ROE walk-forward ({len(data_map)} tickers, {common_min.date()}..{common_max.date()}) ===")

    mid = common_min + (common_max - common_min) / 2
    params = roe_prod_params()

    def fold_map(lo, hi):
        dm, fm, dv = {}, {}, {}
        for t, d in data_map.items():
            seg = d[(d.index >= lo) & (d.index <= hi)]
            if len(seg) < 30:
                continue
            dm[t] = seg
            fm[t] = fund_map[t]
            if t in divs_map:
                dv[t] = divs_map[t]
        return dm, fm, dv

    for label, lo, hi in [("IS (1-я половина)", common_min, mid),
                          ("OOS (2-я половина)", mid, common_max)]:
        dm, fm, dv = fold_map(lo, hi)
        if not dm:
            print(f"  {label}: нет данных")
            continue
        res = run_portfolio_backtest(dm, ROEPortfolioStrategy, params, fm,
                                     cash=100_000.0, commission=COMMISSION, dividends=dv or None)
        print(f"  {label} ({lo.date()}..{hi.date()}):")
        _print_metrics(res, "prod")


def main():
    parser = argparse.ArgumentParser(description="Walk-forward / OOS validation")
    parser.add_argument("--strategy", choices=["fib", "roe"], required=True)
    parser.add_argument("--tickers", default="SBER,LKOH")
    parser.add_argument("--db", default=str(DEFAULT_4H_DB), help="fib only")
    parser.add_argument("--folds", type=int, default=4, help="fib only")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    if args.strategy == "fib":
        run_fib(tickers, args.db, args.folds)
    else:
        run_roe(tickers)


if __name__ == "__main__":
    main()
