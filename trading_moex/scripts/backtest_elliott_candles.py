#!/usr/bin/env python3
"""CLI backtest for Elliott micro-wave candle strategy.

Usage (from repo root, inside or outside container):
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_elliott_candles.py
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_elliott_candles.py \
        --tickers SBER,LKOH --periods 5min,15min,1day --cash 100000
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_elliott_candles.py --mtf
    PYTHONPATH=trading_moex python3 trading_moex/scripts/backtest_elliott_candles.py --csv results.csv
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import pandas as pd

from app import data, storage
from app.elliott_candles import (
    classify_candles,
    detect_waves,
    run_backtest,
    mtf_correction_analysis,
    quality_analytics,
)

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_TICKERS = ["SBER", "LKOH"]
DEFAULT_PERIODS = ["5min", "15min", "30min", "60min", "1day"]
DEFAULT_CASH = 100_000.0
DEFAULT_DAYS = 365 * 2  # 2 years of data


def load_df(ticker: str, period: str, start: date, end: date) -> pd.DataFrame | None:
    try:
        return data.fetch_history(ticker, period, start, end)
    except Exception as e:
        print(f"  ⚠ {ticker} {period}: загрузка с MOEX не удалась ({e}), пробую кэш...")
        try:
            raw = storage.get_candles(ticker, period, start=start, end=end)
            if raw.empty:
                print(f"  ⚠ {ticker} {period}: кэш пуст")
                return None
            df = raw.copy()
            df["begin"] = pd.to_datetime(df["begin"])
            df = df.set_index("begin").sort_index()
            df.index.name = "datetime"
            df = df[["open", "high", "low", "close", "volume"]]
            df = df[~df.index.duplicated(keep="last")]
            print(f"  ✓ {ticker} {period}: загружено {len(df)} свечей из кэша")
            return df
        except Exception as e2:
            print(f"  ⚠ {ticker} {period}: кэш тоже недоступен ({e2})")
            return None


def print_cycle_summary(cycle, idx: int):
    print(f"  Cycle {idx:3d} | {cycle.wave_start[:16]} → {cycle.wave_end[:16]} "
          f"| wave={cycle.wave_len} {cycle.direction:4s} | q={cycle.quality:.3f} "
          f"| steps={cycle.steps_used} | pnl={cycle.total_pnl:+,.0f}")


def print_metrics(m: dict, ticker: str, period: str):
    if m["total_cycles"] == 0:
        print(f"\n{'='*70}")
        print(f"  {ticker} {period}: нет циклов (мало данных или нет волн)")
        return
    print(f"\n{'='*70}")
    print(f"  {ticker} {period}")
    print(f"{'='*70}")
    print(f"  Циклов:      {m['total_cycles']}  (выигрышных: {m['win_cycles']}, "
          f"проигрышных: {m['loss_cycles']})")
    print(f"  Win rate:    {m['win_rate']*100:.1f}%")
    print(f"  Всего сделок: {m['total_trades']}")
    print(f"  Средний PnL: {m['avg_cycle_pnl']:+,.0f}  (медиана: {m['median_cycle_pnl']:+,.0f})")
    print(f"  Итого PnL:   {m['total_pnl']:+,.0f}  ({m['total_return_pct']:+.2f}%)")
    print(f"  Buy&Hold:    {m['buy_hold_return_pct']:+.2f}%")
    print(f"  Max DD:      {m['max_drawdown_pct']:.2f}%")
    print(f"  Profit factor: {m['profit_factor']:.2f}")
    print(f"  Комиссия:    {m['total_commission']:,.0f}")
    print(f"  Финальный капитал: {m['final_equity']:,.0f}")
    print(f"  Распределение шагов: {m['step_distribution']}")
    if m.get("avg_quality_winning") is not None:
        print(f"  Avg quality (win):  {m['avg_quality_winning']:.4f}")
    if m.get("avg_quality_losing") is not None:
        print(f"  Avg quality (loss): {m['avg_quality_losing']:.4f}")


def run_single_ticker(
    ticker: str,
    periods: list[str],
    start: date,
    end: date,
    cash: float,
    params: dict,
) -> dict:
    """Run backtest for one ticker across multiple periods. Returns results dict."""
    results = {}
    for period in periods:
        print(f"\nЗагрузка {ticker} {period} [{start} .. {end}]...")
        df = load_df(ticker, period, start, end)
        if df is None or df.empty:
            continue
        print(f"  {len(df)} свечей")

        bt = run_backtest(df, initial_equity=cash, **params)
        print_metrics(bt["metrics"], ticker, period)

        if bt["cycles"]:
            print("\n  Последние 10 циклов:")
            for i, c in enumerate(bt["cycles"][-10:]):
                print_cycle_summary(c, i + 1)

        # Quality analytics
        qa = quality_analytics(bt["cycles"])
        if qa["quartiles"]:
            print("\n  Квартили качества:")
            for label, stats in qa["quartiles"].items():
                if stats.get("count", 0) > 0:
                    print(f"    {label:10s}: count={stats['count']:3d}  "
                          f"win_rate={stats.get('win_rate', 0)*100:5.1f}%  "
                          f"avg_pnl={stats.get('avg_pnl', 0):+8,.0f}")

        results[(ticker, period)] = bt
    return results


def run_mtf(
    htf_ticker: str,
    htf_period: str,
    ltf_period: str,
    start: date,
    end: date,
):
    """Run multi-TF correction analytics."""
    print(f"\n{'='*70}")
    print(f"  MTF Analytics: HTF={htf_period} → LTF={ltf_period} ({htf_ticker})")
    print(f"{'='*70}")

    htf_df = load_df(htf_ticker, htf_period, start, end)
    ltf_df = load_df(htf_ticker, ltf_period, start, end)
    if htf_df is None or ltf_df is None:
        print("  Нет данных")
        return

    records = mtf_correction_analysis(htf_df, ltf_df)
    if not records:
        print("  Не найдено коррекций для анализа")
        return

    print(f"  Найдено коррекций: {len(records)}")

    # Count patterns
    patterns = {}
    for r in records:
        p = r["pattern"]
        patterns[p] = patterns.get(p, 0) + 1

    print("  Распределение паттернов:")
    for p, cnt in sorted(patterns.items()):
        pct = cnt / len(records) * 100
        print(f"    {p:10s}: {cnt:4d} ({pct:.1f}%)")

    # Hypothesis check: "HTF correction = 5 LTF waves"
    zigzag_count = patterns.get("zigzag", 0)
    print(f"\n  Гипотеза «коррекция HTF = 5 волн LTF» (зигзаг): "
          f"{zigzag_count}/{len(records)} = {zigzag_count/len(records)*100:.1f}%")

    # Forward returns by pattern
    print("\n  Средняя доходность после коррекции (по паттернам):")
    for p in sorted(set(r["pattern"] for r in records)):
        fwd = [r["fwd_return_pct"] for r in records if r["pattern"] == p and r["fwd_return_pct"] is not None]
        if fwd:
            avg = sum(fwd) / len(fwd)
            print(f"    {p:10s}: avg={avg:+.3f}%  (n={len(fwd)})")


def main():
    parser = argparse.ArgumentParser(description="Elliott micro-wave candle backtest")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                        help="Comma-separated tickers (default: SBER,LKOH)")
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS),
                        help="Comma-separated periods (default: 5min,15min,30min,60min,1day)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help="Days of history to load (default: 730)")
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH,
                        help="Initial equity (default: 100000)")
    parser.add_argument("--commission", type=float, default=0.0005,
                        help="Commission per side (default: 0.0005)")
    parser.add_argument("--base-pct", type=float, default=0.25,
                        help="Base position size as fraction of equity (default: 0.25)")
    parser.add_argument("--max-steps", type=int, default=3,
                        help="Max martingale steps (default: 3)")
    parser.add_argument("--wave-min", type=int, default=3,
                        help="Min candles in a wave (default: 3)")
    parser.add_argument("--wave-max", type=int, default=5,
                        help="Max candles in a wave (default: 5)")
    parser.add_argument("--body-ratio-min", type=float, default=0.6,
                        help="Min body/range ratio for impulse candle (default: 0.6)")
    parser.add_argument("--atr-k", type=float, default=0.5,
                        help="Min body = k*ATR for impulse candle (default: 0.5)")
    parser.add_argument("--mtf", action="store_true",
                        help="Run multi-TF correction analytics")
    parser.add_argument("--mtf-htf", default="1day",
                        help="HTF period for MTF analytics (default: 1day)")
    parser.add_argument("--mtf-ltf", default="60min",
                        help="LTF period for MTF analytics (default: 60min)")
    parser.add_argument("--csv", type=str, default=None,
                        help="Export all trades to CSV file")

    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",")]
    periods = [p.strip() for p in args.periods.split(",")]

    end = date.today()
    start = end - timedelta(days=args.days)

    params = {
        "wave_min": args.wave_min,
        "wave_max": args.wave_max,
        "base_pct": args.base_pct,
        "max_steps": args.max_steps,
        "commission": args.commission,
        "body_ratio_min": args.body_ratio_min,
        "atr_k": args.atr_k,
    }

    print("Elliott Micro-Wave Candle Backtest")
    print(f"  Тикеры:       {tickers}")
    print(f"  Периоды:      {periods}")
    print(f"  Диапазон:     {start} — {end}")
    print(f"  Капитал:      {args.cash:,.0f}")
    print(f"  Параметры:    {params}")

    all_trades = []

    for ticker in tickers:
        results = run_single_ticker(ticker, periods, start, end, args.cash, params)
        for key, bt in results.items():
            all_trades.extend(bt["trades"])

    # MTF analytics
    if args.mtf:
        for ticker in tickers:
            run_mtf(ticker, args.mtf_htf, args.mtf_ltf, start, end)

    # CSV export
    if args.csv and all_trades:
        rows = []
        for t in all_trades:
            rows.append({
                "wave_start": t.wave_start,
                "wave_end": t.wave_end,
                "wave_len": t.wave_len,
                "direction": t.direction,
                "step": t.step,
                "size_pct": t.size_pct,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "commission": t.commission,
                "quality": t.quality,
            })
        pd.DataFrame(rows).to_csv(args.csv, index=False)
        print(f"\n  Экспортировано {len(rows)} сделок → {args.csv}")

    print("\n  Готово.")


if __name__ == "__main__":
    main()
