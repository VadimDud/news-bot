#!/usr/bin/env python3
"""Честная проверка MTF-стратегии: LTF паттерн + HTF зона-фильтр.

Live-faithful модель:
- Сигнал на закрытии LTF-бара (паттерн + HTF фильтр)
- Вход на open следующего LTF-бара
- Выход на close бара через horizon баров (фиксированный горизонт)
- Комиссия 0.05%/сторона + slippage 0.05% (по умолчанию)

Usage (from trading_moex/):
    python3 scripts/backtest_mtf_confirm.py
    python3 scripts/backtest_mtf_confirm.py --pattern zone_break --ltf 4h
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app import mtf_confirm as mtf  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

DEPOSIT = 100_000.0
COMMISSION_PCT = 0.05  # per side
SLIPPAGE_PCT = 0.05    # per side
TOTAL_COST_PCT = 2 * (COMMISSION_PCT + SLIPPAGE_PCT)  # round trip


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period=? ORDER BY begin",
        con, params=(ticker, period),
    )
    con.close()
    if df.empty:
        return df
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def honest_trades(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    horizon: int = 6,
    direction: int = 0,
    min_hold: int = 0,
    event_mask: pd.Series | None = None,
) -> list[dict]:
    """Live-faithful сделки: сигнал на close, вход на open следующего бара.

    ``event_mask`` — boolean Series (aligned to LTF index), True = бар в запретном
    окне (отсечка дивидендов и т.п.), вход запрещён.
    """
    ltf = mtf.prepare_ohlc(ltf_df)
    htf = mtf.prepare_ohlc(htf_df)
    if len(ltf) < max(ltf_zone, 50) + horizon + 5 or len(htf) < htf_zone + 5:
        return []

    sig = mtf.mtf_signal(ltf, htf, pattern=pattern, ltf_zone=ltf_zone,
                          htf_zone=htf_zone, direction=direction)
    sig_np = sig.to_numpy(dtype=int)
    opens = ltf["open"].to_numpy(dtype=float)
    closes = ltf["close"].to_numpy(dtype=float)
    highs = ltf["high"].to_numpy(dtype=float)
    lows = ltf["low"].to_numpy(dtype=float)
    ev_mask = event_mask.to_numpy(dtype=bool) if event_mask is not None else np.zeros(len(ltf), dtype=bool)

    trades = []
    in_trade = False
    entry_bar = 0
    entry_side = 0

    for i in range(len(sig_np) - 1):
        if not in_trade:
            if sig_np[i] != 0 and not ev_mask[i + 1]:  # проверяем entry_bar = i+1
                entry_bar = i + 1
                entry_side = sig_np[i]
                in_trade = True
        else:
            bars_held = i - entry_bar + 1
            if bars_held >= horizon or i == len(sig_np) - 2:
                exit_bar = min(entry_bar + horizon, len(opens) - 1)
                entry_price = opens[entry_bar]
                exit_price = closes[exit_bar]
                # Для шорта: PnL = (entry - exit) / entry
                if entry_side == 1:
                    pnl_pct = (exit_price / entry_price - 1.0) * 100.0
                else:
                    pnl_pct = (1.0 - exit_price / entry_price) * 100.0
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": exit_bar,
                    "side": "long" if entry_side == 1 else "short",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "pnl_net_pct": pnl_pct - TOTAL_COST_PCT,
                    "bars_held": exit_bar - entry_bar,
                })
                in_trade = False
    return trades


def run_backtest(
    ticker: str,
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    horizon: int = 6,
    direction: int = 0,
    event_mask: pd.Series | None = None,
) -> dict:
    """Полный бэктест для одного тикера."""
    trades = honest_trades(ltf_df, htf_df, pattern=pattern, ltf_zone=ltf_zone,
                           htf_zone=htf_zone, horizon=horizon, direction=direction,
                           event_mask=event_mask)
    if not trades:
        return {
            "ticker": ticker, "trades": 0, "win_raw": 0, "win_net": 0,
            "pnl_net": 0, "pnl_net_pct": 0, "avg_pnl_net_pct": 0,
            "max_dd_pct": 0, "sharpe": 0,
        }

    pnls = np.array([t["pnl_net_pct"] for t in trades])
    wins_raw = np.array([t["pnl_pct"] for t in trades])
    n = len(pnls)
    win_raw = float((wins_raw > 0).sum()) / n * 100.0
    win_net = float((pnls > 0).sum()) / n * 100.0
    pnl_net = float(pnls.sum())
    avg_pnl = float(pnls.mean())
    # Max DD of cumulative pnl
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(dd.max()) if len(dd) > 0 else 0.0
    # Sharpe (annualized, ~252 trading days / horizon)
    if len(pnls) > 1 and pnls.std() > 0:
        trades_per_year = 252.0 / max(horizon, 1)
        sharpe = float(pnls.mean() / pnls.std() * np.sqrt(trades_per_year))
    else:
        sharpe = 0.0

    return {
        "ticker": ticker,
        "trades": n,
        "win_raw": round(win_raw, 1),
        "win_net": round(win_net, 1),
        "pnl_net": round(pnl_net, 2),
        "pnl_net_pct": round(pnl_net, 2),
        "avg_pnl_net_pct": round(avg_pnl, 2),
        "max_dd_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
    }


def _split_eras(ltf_df, htf_df):
    # Split both LTF and HTF by the SAME calendar date (midpoint of LTF)
    mid_date = ltf_df.index[len(ltf_df) // 2]
    h1_ltf, h2_ltf = ltf_df[ltf_df.index < mid_date], ltf_df[ltf_df.index >= mid_date]
    h1_htf, h2_htf = htf_df[htf_df.index < mid_date], htf_df[htf_df.index >= mid_date]
    return [
        ("1st_half", h1_ltf, h1_htf),
        ("2nd_half", h2_ltf, h2_htf),
    ]


def signal_hours_mask(ltf_df, allowed_hours):
    """Build entry mask from allowed signal-bar hours.

    Signal at bar i (hour S) → entry at bar i+1.  To allow signals at
    specific hours, shift the mask so that bar i+1 is masked when bar i
    is not in ``allowed_hours``.
    """
    if not allowed_hours:
        return None
    ltf = mtf.prepare_ohlc(ltf_df)
    signal_mask = ~ltf.index.to_series().dt.hour.isin(allowed_hours)
    entry_mask = signal_mask.shift(1, fill_value=True)
    return entry_mask


def main():
    parser = argparse.ArgumentParser(description="MTF honest backtest")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--ltf", default="4h", choices=["60min", "4h"])
    parser.add_argument("--pattern", default="zone_break")
    parser.add_argument("--ltf-zone", type=int, default=20)
    parser.add_argument("--htf-zone", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--direction", type=int, default=0, help="1=long, -1=short, 0=both")
    parser.add_argument("--exclude-div-days", type=int, default=0,
                        help="Исключить входы в окне ±N дней от отсечки дивидендов (0=выкл)")
    parser.add_argument("--signal-hours", type=str, default="",
                        help="Разрешённые часы UTC для СИГНАЛЬНЫХ баров (запятые, напр. '4,8,12'). "
                             "Пустая строка = все часы.")
    args = parser.parse_args()

    from app.event_filter import load_dividend_events, in_event_window  # noqa: E402

    con = sqlite3.connect(args.db)
    ltf_rows = con.execute("SELECT DISTINCT ticker FROM candles WHERE period=?", (args.ltf,)).fetchall()
    htf_rows = con.execute("SELECT DISTINCT ticker FROM candles WHERE period='1day'").fetchall()
    con.close()
    ltf_tickers = [r[0] for r in ltf_rows]
    htf_tickers = [r[0] for r in htf_rows]
    common = sorted(set(ltf_tickers) & set(htf_tickers))
    if not common:
        print(f"Нет тикеров с {args.ltf} + 1day в {args.db}")
        return

    print(f"=== MTF Honest Backtest: {args.pattern} | LTF={args.ltf} zone={args.ltf_zone} | HTF=1day zone={args.htf_zone} ===")
    print(f"Horizon={args.horizon} bars, cost={TOTAL_COST_PCT:.2f}%/round-trip, direction={args.direction}")
    if args.exclude_div_days > 0:
        print(f"Dividend filter: ±{args.exclude_div_days} days around ex-div")
    allowed_hours = sorted(set(int(x.strip()) for x in args.signal_hours.split(",") if x.strip())) if args.signal_hours else []
    if allowed_hours:
        print(f"Signal hours (UTC): {allowed_hours}")
    print(f"Tickers: {', '.join(common)}\n")

    all_results = []
    halves_results = {"1st_half": [], "2nd_half": []}

    for ticker in common:
        ltf_df = load_df(ticker, args.db, args.ltf)
        htf_df = load_df(ticker, args.db, "1day")
        if len(ltf_df) < 60 or len(htf_df) < 60:
            continue

        # Build combined mask: dividend + signal hours
        event_mask = None
        if args.exclude_div_days > 0:
            ltf_prepared = mtf.prepare_ohlc(ltf_df)
            div_events = load_dividend_events(ticker, args.db)
            if not div_events.empty:
                event_mask = in_event_window(ltf_prepared.index, div_events,
                                             pre_days=args.exclude_div_days,
                                             post_days=args.exclude_div_days)
        hour_mask = signal_hours_mask(ltf_df, allowed_hours)
        if event_mask is not None and hour_mask is not None:
            event_mask = event_mask | hour_mask
        elif hour_mask is not None:
            event_mask = hour_mask

        res = run_backtest(ticker, ltf_df, htf_df, pattern=args.pattern,
                           ltf_zone=args.ltf_zone, htf_zone=args.htf_zone,
                           horizon=args.horizon, direction=args.direction,
                           event_mask=event_mask)
        all_results.append(res)

        # Halves
        for name, h_ltf, h_htf in _split_eras(ltf_df, htf_df):
            if len(h_ltf) >= 30 and len(h_htf) >= 30:
                h_event_mask = None
                if args.exclude_div_days > 0:
                    h_div_events = load_dividend_events(ticker, args.db)
                    if not h_div_events.empty:
                        h_event_mask = in_event_window(h_ltf.index, h_div_events,
                                                       pre_days=args.exclude_div_days,
                                                       post_days=args.exclude_div_days)
                h_hour_mask = signal_hours_mask(h_ltf, allowed_hours)
                if h_event_mask is not None and h_hour_mask is not None:
                    h_event_mask = h_event_mask | h_hour_mask
                elif h_hour_mask is not None:
                    h_event_mask = h_hour_mask

                hr = run_backtest(ticker, h_ltf, h_htf, pattern=args.pattern,
                                  ltf_zone=args.ltf_zone, htf_zone=args.htf_zone,
                                  horizon=args.horizon, direction=args.direction,
                                  event_mask=h_event_mask)
                halves_results[name].append(hr)

    if not all_results:
        print("Нет результатов")
        return

    df = pd.DataFrame(all_results)

    print(f"{'ticker':8s} {'trades':>6s} {'win_raw':>8s} {'win_net':>8s} {'pnl_net%':>9s} "
          f"{'avg/pnl':>8s} {'maxDD%':>7s} {'sharpe':>7s}")
    print("-" * 70)
    for _, r in df.iterrows():
        flag = " ◀" if r["pnl_net_pct"] > 0 else ""
        print(f"{r['ticker']:8s} {int(r['trades']):6d} {r['win_raw']:8.1f} {r['win_net']:8.1f} "
              f"{r['pnl_net_pct']:+9.2f} {r['avg_pnl_net_pct']:+8.2f} {r['max_dd_pct']:7.2f} {r['sharpe']:7.2f}{flag}")

    total_trades = int(df["trades"].sum())
    avg_win_raw = df["win_raw"].mean()
    avg_win_net = df["win_net"].mean()
    total_pnl = df["pnl_net_pct"].sum()
    avg_sharpe = df["sharpe"].mean()
    positive_tickers = (df["pnl_net_pct"] > 0).sum()

    print(f"\n--- Summary ({len(common)} tickers) ---")
    print(f"Total trades: {total_trades}")
    print(f"Avg win% (raw): {avg_win_raw:.1f}%")
    print(f"Avg win% (net): {avg_win_net:.1f}%")
    print(f"Total pnl%: {total_pnl:+.2f}%")
    print(f"Avg sharpe: {avg_sharpe:.2f}")
    print(f"Positive tickers: {positive_tickers}/{len(common)} ({positive_tickers/len(common)*100:.0f}%)")

    for name in ["1st_half", "2nd_half"]:
        hr = halves_results[name]
        if not hr:
            continue
        hdf = pd.DataFrame(hr)
        ht = int(hdf["trades"].sum())
        hw = hdf["win_net"].mean()
        hp = hdf["pnl_net_pct"].sum()
        hp_pos = (hdf["pnl_net_pct"] > 0).sum()
        print(f"\n--- {name} ({len(hr)} tickers) ---")
        print(f"Trades: {ht}, Avg win_net: {hw:.1f}%, Total pnl%: {hp:+.2f}%, Positive: {hp_pos}/{len(hr)}")


if __name__ == "__main__":
    main()
