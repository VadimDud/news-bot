#!/usr/bin/env python3
"""Portfolio backtest: scoring R1–R4 variants + solo ticker runs with deposit comparison.

Usage (from repo root, inside or outside container):
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_all.py [--tickers SBER,LKOH] [--cash 100000] [--rate 8.0]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import config as cfg
from app import storage
from app.backtest import run_portfolio_backtest
from app.fundamentals import prepare_fundamentals_series
from app.strategies import ROEPortfolioStrategy

# ── Default tickers (all with candles + fundamentals in local DB) ─────────────
ALL_TICKERS = ["CHMF", "GAZP", "LKOH", "MOEX", "NLMK", "NVTK", "SBER", "T", "TATN"]
CASH = 100_000.0
DEPOSIT_RATE = 8.0  # % годовых (TMON)
COMMISSION = 0.0005  # MOEX fee


def load_data(ticker: str):
    """Load candles + fundamentals + dividends from local DB."""
    raw = storage.get_candles(ticker, "1day")
    if raw.empty:
        return None, None, None
    df = raw.copy()
    df["begin"] = pd.to_datetime(df["begin"])
    df = df.set_index("begin").sort_index()[["open", "high", "low", "close", "volume"]]
    df.index.name = "datetime"

    fund = prepare_fundamentals_series(ticker, df.index.min().date(), df.index.max().date())
    if fund is None or fund.empty:
        return df, None, None

    div_df = storage.load_dividends(ticker)
    return df, fund, div_df if not div_df.empty else None


def deposit_return_pct(days: int, rate: float = 8.0) -> float:
    """Сложный % доход депозита за days дней при rate% годовых."""
    if days <= 0:
        return 0.0
    return ((1 + rate / 100.0 / 365.0) ** days - 1) * 100.0


def base_params(**overrides) -> dict:
    params = dict(
        min_avg_roe=cfg.TRADER_ROE_MIN_AVG_ROE,
        min_single_roe=cfg.TRADER_ROE_MIN_SINGLE_ROE,
        pb_entry=cfg.TRADER_ROE_PB_ENTRY,
        pb_exit=cfg.TRADER_ROE_PB_EXIT,
        roe_exit=cfg.TRADER_ROE_ROE_EXIT,
        max_positions=4,
        rebalance_days=21,
        cash_yield=cfg.TRADER_ROE_CASH_YIELD,
        scoring=1,
        min_score=0.5,
        w_roe=cfg.TRADER_ROE_W_ROE,
        w_pb=cfg.TRADER_ROE_W_PB,
        w_momentum=cfg.TRADER_ROE_W_MOMENTUM,
        w_dividend=cfg.TRADER_ROE_W_DIVIDEND,
        w_stability=cfg.TRADER_ROE_W_STABILITY,
        momentum_months=6,
        stop_loss_pct=0.0,
    )
    params.update(overrides)
    return params


def _print_variant(name: str, res: dict, cash: float, days: int, rate: float):
    if res is None:
        print(f"  {name}: skipped (no data)\n")
        return
    dep_ret = deposit_return_pct(days, rate)
    alpha = res["total_return_pct"] - dep_ret
    dep_beats = sum(
        1 for t in res.get("trades", [])
        if t.get("ret_pct", 0) < deposit_return_pct(max(t.get("days_held", 1), 1), rate)
    )
    total_trades = res.get("trades_total", 0)
    dep_win_pct = dep_beats / total_trades * 100 if total_trades else 0
    print(f"  {name}:")
    print(f"    final_value:     {res['final_value']:.2f}")
    print(f"    total_return:    {res['total_return_pct']:.2f}%")
    print(f"    deposit_return:  {dep_ret:.2f}% (compound {rate}%)")
    print(f"    alpha:           {alpha:+.2f}%")
    print(f"    sharpe:          {res.get('sharpe')}")
    print(f"    max_drawdown:    {res.get('max_drawdown_pct', 0):.2f}%")
    print(f"    trades:          {total_trades}")
    print(f"    win_rate:        {res.get('win_rate_pct', 0):.1f}%")
    print(f"    div_income:      {res.get('dividends_income', 0):.2f}")
    if total_trades:
        print(f"    trades < deposit: {dep_beats}/{total_trades} ({dep_win_pct:.0f}%)")
    print()


def _print_trades(res: dict, rate: float, cash: float):
    trades = res.get("trades", []) if res else []
    if not trades:
        return
    print("    {:<20s} {:>5s} {:>9s} {:>9s} {:>8s} {:>8s} {:>9s}".format(
        "opened", "days", "entry", "exit", "pnl", "ret%", "deposit%"))
    print("    " + "-" * 72)
    for t in trades:
        days = max(t.get("days_held", 0), 1)
        dep_ret = deposit_return_pct(days, rate)
        print("    {:<20s} {:>5d} {:>9.2f} {:>9.2f} {:>8.2f} {:>7.2f}% {:>8.2f}%".format(
            (t.get("opened") or "")[:20],
            t.get("days_held", 0),
            t.get("entry_price", 0),
            t.get("exit_price", 0),
            t.get("pnl", 0),
            t.get("ret_pct", 0),
            dep_ret))
    print()


def main():
    parser = argparse.ArgumentParser(description="ROE+P/B portfolio backtest with deposit comparison")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--cash", type=float, default=CASH)
    parser.add_argument("--rate", type=float, default=DEPOSIT_RATE)
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    cash = args.cash
    rate = args.rate

    # Load data for all tickers
    data_map, fund_map, divs_map = {}, {}, {}
    for t in tickers:
        df, fund, divs = load_data(t)
        if df is None or fund is None:
            print(f"  SKIP {t}: no candles or fundamentals")
            continue
        data_map[t] = df
        fund_map[t] = fund
        if divs is not None:
            divs_map[t] = divs

    if not data_map:
        print("No data available.")
        return

    n_bars = max(len(df) for df in data_map.values())
    days = (max(df.index.max() for df in data_map.values()) - min(df.index.min() for df in data_map.values())).days
    print(f"\n=== ROE+P/B BACKTEST: {len(data_map)} tickers, {days} days, {n_bars} bars ===\n")
    print(f"Cash: {cash:.0f} | Commission: {COMMISSION*100:.2f}% | Deposit rate: {rate}% | Rebalance: 21d\n")

    # ── Portfolio variants (R1–R4) ──────────────────────────────────────────
    print("--- Portfolio variants ---\n")

    # R1: scoring=1, no stop, no dividends
    p1 = base_params(scoring=1, stop_loss_pct=0.0)
    r1 = run_portfolio_backtest(data_map, ROEPortfolioStrategy, p1, fund_map, cash=cash, commission=COMMISSION)
    _print_variant("R1: scoring + no div", r1, cash, days, rate)
    _print_trades(r1, rate, cash)

    # R2: scoring=1, stop_loss=10%, no dividends
    p2 = base_params(scoring=1, stop_loss_pct=10.0)
    r2 = run_portfolio_backtest(data_map, ROEPortfolioStrategy, p2, fund_map, cash=cash, commission=COMMISSION)
    _print_variant("R2: scoring + SL10%", r2, cash, days, rate)
    _print_trades(r2, rate, cash)

    # R3: scoring=1, no stop, with dividends
    p3 = base_params(scoring=1, stop_loss_pct=0.0)
    r3 = run_portfolio_backtest(data_map, ROEPortfolioStrategy, p3, fund_map, cash=cash, commission=COMMISSION, dividends=divs_map or None)
    _print_variant("R3: scoring + dividends", r3, cash, days, rate)
    _print_trades(r3, rate, cash)

    # R4: scoring=1, stop_loss=10%, with dividends (production config)
    p4 = base_params(scoring=1, stop_loss_pct=10.0)
    r4 = run_portfolio_backtest(data_map, ROEPortfolioStrategy, p4, fund_map, cash=cash, commission=COMMISSION, dividends=divs_map or None)
    _print_variant("R4: scoring + SL10% + div (production)", r4, cash, days, rate)
    _print_trades(r4, rate, cash)

    # ── Solo ticker runs (R4 config, max_positions=1) ───────────────────────
    print("--- Solo ticker runs (R4 config, full allocation) ---\n")
    p_solo = base_params(scoring=1, stop_loss_pct=10.0, max_positions=1)
    for t in tickers:
        if t not in data_map:
            continue
        solo_data = {t: data_map[t]}
        solo_fund = {t: fund_map[t]}
        solo_divs = {t: divs_map[t]} if t in divs_map else None
        solo_days = (data_map[t].index.max() - data_map[t].index.min()).days
        solo_res = run_portfolio_backtest(solo_data, ROEPortfolioStrategy, p_solo, solo_fund, cash=cash, commission=COMMISSION, dividends=solo_divs)
        _print_variant(f"{t}", solo_res, cash, solo_days, rate)
        _print_trades(solo_res, rate, cash)


if __name__ == "__main__":
    main()
