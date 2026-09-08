#!/usr/bin/env python3
"""Hybrid exit backtest: Elliott TP + baseline fallback.

Strategy:
- Take ALL MTF signals (no wave filter — same as baseline)
- When a wave 1-2 pair exists on wave_tf: set TP = entry ± k × wave1_amp
  - Exit at TP if hit within time_cap bars
  - Otherwise exit at close after time_cap bars
- When NO wave 1-2 pair exists: exit at close after 6 bars (baseline)

This combines:
- 100% of baseline trades (no filter)
- Better exits when Elliott wave structure is present

Usage (from trading_moex/):
    python3 scripts/backtest_mtf_hybrid.py
    python3 scripts/backtest_mtf_hybrid.py --wave-tf 1day --k 1.618 --time-cap 12
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
from app.elliott_candles import classify_candles  # noqa: E402
from scripts.backtest_mtf_elliott_tp import (  # noqa: E402
    load_df, _build_wave12_pairs, last_wave12_before,
    _summarize_trades, _split_eras,
)
from scripts.backtest_mtf_confirm import honest_trades as baseline_trades  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

DEPOSIT = 100_000.0
COMMISSION_PCT = 0.05
SLIPPAGE_PCT = 0.05
TOTAL_COST_PCT = 2 * (COMMISSION_PCT + SLIPPAGE_PCT)


def honest_trades_hybrid(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    wave_tf: str = "4h",
    k: float = 1.618,
    time_cap: int = 12,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    signal_hours: list[int] | None = None,
) -> list[dict]:
    """Hybrid: Elliott TP when wave pair exists, close+6 baseline otherwise.

    Takes ALL signals (no wave filter). When wave 1-2 pair found, uses TP exit.
    When no pair found, exits at close after 6 bars (baseline behavior).
    """
    ltf = mtf.prepare_ohlc(ltf_df)
    htf = mtf.prepare_ohlc(htf_df)
    if len(ltf) < max(ltf_zone, 50) + time_cap + 5 or len(htf) < htf_zone + 5:
        return []

    sig = mtf.mtf_signal(ltf, htf, pattern=pattern, ltf_zone=ltf_zone,
                          htf_zone=htf_zone, direction=direction,
                          causal_daily=True)

    # Classify wave TF for Elliott wave detection
    wave_df = classify_candles(
        ltf_df.copy() if wave_tf == "4h" else htf_df.copy()
    )

    # Build signal hours mask (shifted: signal bar hour → entry bar)
    if signal_hours:
        signal_ok = ltf.index.to_series().dt.hour.isin(signal_hours)
        entry_mask = signal_ok.shift(1, fill_value=False)
    else:
        entry_mask = pd.Series(True, index=ltf.index)

    sig_np = sig.to_numpy(dtype=int)
    opens = ltf["open"].to_numpy(dtype=float)
    closes = ltf["close"].to_numpy(dtype=float)
    highs = ltf["high"].to_numpy(dtype=float)
    lows = ltf["low"].to_numpy(dtype=float)

    trades = []
    in_trade = False
    entry_bar = 0
    entry_side = 0
    tp_price = 0.0
    has_tp = False
    baseline_horizon = 6  # fixed baseline exit horizon

    for i in range(len(sig_np) - 1):
        if not in_trade:
            if sig_np[i] != 0 and entry_mask.iloc[i + 1]:
                side = sig_np[i]
                entry_bar = i + 1
                entry_side = side
                entry_price = opens[entry_bar]

                # Try to find wave 1-2 pair for Elliott TP
                signal_time = ltf.index[i]
                if wave_tf == "4h":
                    wave_pos = wave_df.index.searchsorted(signal_time, side="right") - 1
                else:
                    completed_mask = wave_df.index < signal_time.normalize()
                    wave_pos = int(completed_mask.sum()) - 1 if completed_mask.any() else -1

                pair = None
                if wave_pos >= 0:
                    pair = last_wave12_before(wave_df, wave_pos)

                if pair is not None and \
                   ((side == 1 and pair["direction"] == "long") or
                    (side == -1 and pair["direction"] == "short")):
                    L = pair["wave1_amp"]
                    if L > 0:
                        if side == 1:
                            tp_price = entry_price + k * L
                        else:
                            tp_price = entry_price - k * L
                        has_tp = True
                    else:
                        has_tp = False
                else:
                    has_tp = False

                in_trade = True
                tp_hit_bar = None
                # Use appropriate time cap
                current_cap = time_cap if has_tp else baseline_horizon
        else:
            bars_held = i - entry_bar + 1
            current_cap = time_cap if has_tp else baseline_horizon

            # Check if TP was hit during this bar (only when we have TP)
            if has_tp and tp_hit_bar is None:
                if entry_side == 1 and highs[i] >= tp_price:
                    tp_hit_bar = i
                elif entry_side == -1 and lows[i] <= tp_price:
                    tp_hit_bar = i

            # Exit: TP hit, time-cap, or end of data
            if bars_held >= current_cap or i == len(sig_np) - 2 or tp_hit_bar is not None:
                if tp_hit_bar is not None:
                    exit_price = tp_price
                    exit_bar = tp_hit_bar
                    exit_type = "tp"
                else:
                    exit_bar = min(entry_bar + current_cap, len(opens) - 1)
                    exit_price = closes[exit_bar]
                    exit_type = "baseline" if not has_tp else "timecap"

                entry_price = opens[entry_bar]
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
                    "tp_price": tp_price if has_tp else 0.0,
                    "wave1_amp": pair["wave1_amp"] if pair else 0.0,
                    "has_tp": has_tp,
                    "tp_hit": tp_hit_bar is not None,
                    "exit_type": exit_type,
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
    wave_tf: str = "4h",
    k: float = 1.618,
    time_cap: int = 12,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    signal_hours: list[int] | None = None,
) -> dict:
    trades = honest_trades_hybrid(
        ltf_df, htf_df, wave_tf=wave_tf, k=k, time_cap=time_cap,
        pattern=pattern, ltf_zone=ltf_zone, htf_zone=htf_zone,
        direction=direction, signal_hours=signal_hours,
    )
    if not trades:
        return {
            "ticker": ticker, "trades": 0, "win_raw": 0, "win_net": 0,
            "pnl_net": 0, "avg_pnl_net_pct": 0, "max_dd_pct": 0,
            "sharpe": 0, "tp_hits": 0, "tp_hit_rate": 0,
            "baseline_exits": 0, "tp_exits": 0, "tc_exits": 0,
        }

    pnls = np.array([t["pnl_net_pct"] for t in trades])
    wins_raw = np.array([t["pnl_pct"] for t in trades])
    tp_hits = sum(1 for t in trades if t["tp_hit"])
    baseline_exits = sum(1 for t in trades if t["exit_type"] == "baseline")
    tp_exits = sum(1 for t in trades if t["exit_type"] == "tp")
    tc_exits = sum(1 for t in trades if t["exit_type"] == "timecap")
    n = len(pnls)
    win_raw = float((wins_raw > 0).sum()) / n * 100.0
    win_net = float((pnls > 0).sum()) / n * 100.0
    pnl_net = float(pnls.sum())
    avg_pnl = float(pnls.mean())
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(dd.max()) if len(dd) > 0 else 0.0
    if n > 1 and pnls.std() > 0:
        trades_per_year = 252.0 / max(time_cap, 1)
        sharpe = float(pnls.mean() / pnls.std() * np.sqrt(trades_per_year))
    else:
        sharpe = 0.0

    return {
        "ticker": ticker,
        "trades": n,
        "win_raw": round(win_raw, 1),
        "win_net": round(win_net, 1),
        "pnl_net": round(pnl_net, 2),
        "avg_pnl_net_pct": round(avg_pnl, 2),
        "max_dd_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "tp_hits": tp_hits,
        "tp_hit_rate": round(tp_hits / n * 100, 1),
        "baseline_exits": baseline_exits,
        "tp_exits": tp_exits,
        "tc_exits": tc_exits,
    }


def main():
    parser = argparse.ArgumentParser(description="MTF hybrid exit backtest")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--ltf", default="4h")
    parser.add_argument("--wave-tf", default="1day", choices=["4h", "1day"])
    parser.add_argument("--k", type=float, default=1.618)
    parser.add_argument("--time-cap", type=int, default=12)
    parser.add_argument("--pattern", default="zone_break")
    parser.add_argument("--ltf-zone", type=int, default=20)
    parser.add_argument("--htf-zone", type=int, default=20)
    parser.add_argument("--direction", type=int, default=0)
    parser.add_argument("--signal-hours", type=str, default="4,8,12")
    args = parser.parse_args()

    allowed_hours = sorted(set(int(x.strip()) for x in args.signal_hours.split(",") if x.strip())) if args.signal_hours else []

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

    print(f"=== HYBRID EXIT: Elliott TP + baseline fallback ===")
    print(f"wave_tf={args.wave_tf}, k={args.k}, time_cap={args.time_cap}")
    print(f"Pattern={args.pattern}, cost={TOTAL_COST_PCT:.2f}%")
    print(f"Signal hours (UTC): {allowed_hours}")
    print(f"Tickers: {', '.join(common)}\n")

    # Configs to test
    configs = [
        ("baseline", "BASELINE_close6 (control)", None, None, 6),
        ("hybrid",   "HYBRID_1d_k1618_h12", "1day", 1.618, 12),
        ("hybrid",   "HYBRID_1d_k1618_h6",  "1day", 1.618, 6),
        ("hybrid",   "HYBRID_4h_k1618_h12", "4h",   1.618, 12),
        ("hybrid",   "HYBRID_1d_k1_h12",    "1day", 1.0,   12),
    ]

    all_results = []

    for cfg_type, cfg_name, cfg_wtf, cfg_k, cfg_h in configs:
        results = []
        halves = {"1st_half": [], "2nd_half": []}

        for ticker in common:
            ltf_df = load_df(ticker, args.db, args.ltf)
            htf_df = load_df(ticker, args.db, "1day")
            if len(ltf_df) < 60 or len(htf_df) < 60:
                continue

            if cfg_type == "baseline":
                from app import mtf_confirm as _mtf_base
                event_mask = None
                if allowed_hours:
                    ltf_prepared = _mtf_base.prepare_ohlc(ltf_df)
                    signal_ok = ltf_prepared.index.to_series().dt.hour.isin(allowed_hours)
                    event_mask = ~signal_ok.shift(1, fill_value=True)
                trades = baseline_trades(
                    ltf_df, htf_df, pattern=args.pattern, ltf_zone=args.ltf_zone,
                    htf_zone=args.htf_zone, direction=args.direction,
                    horizon=cfg_h, event_mask=event_mask,
                )
                res = _summarize_trades(
                    ticker,
                    [t["pnl_pct"] for t in trades],
                    [t["pnl_net_pct"] for t in trades],
                    0, cfg_h,
                )
                res["baseline_exits"] = res["trades"]
                res["tp_exits"] = 0
                res["tc_exits"] = 0
            else:
                res = run_backtest(
                    ticker, ltf_df, htf_df,
                    wave_tf=cfg_wtf, k=cfg_k, time_cap=cfg_h,
                    pattern=args.pattern, ltf_zone=args.ltf_zone,
                    htf_zone=args.htf_zone, direction=args.direction,
                    signal_hours=allowed_hours,
                )
            results.append(res)

            for name, h_ltf, h_htf in _split_eras(ltf_df, htf_df):
                if len(h_ltf) >= 30 and len(h_htf) >= 30:
                    if cfg_type == "baseline":
                        from app import mtf_confirm as _mtf_base
                        h_event_mask = None
                        if allowed_hours:
                            h_ltf_p = _mtf_base.prepare_ohlc(h_ltf)
                            h_signal_ok = h_ltf_p.index.to_series().dt.hour.isin(allowed_hours)
                            h_event_mask = ~h_signal_ok.shift(1, fill_value=True)
                        h_trades = baseline_trades(
                            h_ltf, h_htf, pattern=args.pattern, ltf_zone=args.ltf_zone,
                            htf_zone=args.htf_zone, direction=args.direction,
                            horizon=cfg_h, event_mask=h_event_mask,
                        )
                        hr = _summarize_trades(
                            ticker,
                            [t["pnl_pct"] for t in h_trades],
                            [t["pnl_net_pct"] for t in h_trades],
                            0, cfg_h,
                        )
                    else:
                        hr = run_backtest(
                            ticker, h_ltf, h_htf,
                            wave_tf=cfg_wtf, k=cfg_k, time_cap=cfg_h,
                            pattern=args.pattern, ltf_zone=args.ltf_zone,
                            htf_zone=args.htf_zone, direction=args.direction,
                            signal_hours=allowed_hours,
                        )
                    halves[name].append(hr)

        if not results:
            continue

        df = pd.DataFrame(results)
        total_trades = int(df["trades"].sum())
        avg_win = df["win_net"].mean()
        total_pnl = df["pnl_net"].sum()
        avg_sharpe = df["sharpe"].mean()
        pos_tickers = (df["pnl_net"] > 0).sum()
        total_tp = int(df.get("tp_hits", pd.Series([0])).sum())
        total_base = int(df.get("baseline_exits", pd.Series([0])).sum())
        total_tc = int(df.get("tc_exits", pd.Series([0])).sum())

        halves_summary = {}
        for half_name in ["1st_half", "2nd_half"]:
            hr = halves[half_name]
            if not hr:
                continue
            hdf = pd.DataFrame(hr)
            halves_summary[half_name] = {
                "trades": int(hdf["trades"].sum()),
                "win": hdf["win_net"].mean(),
                "pnl": hdf["pnl_net"].sum(),
                "pos": (hdf["pnl_net"] > 0).sum(),
                "total": len(hr),
            }

        all_results.append({
            "name": cfg_name,
            "trades": total_trades,
            "win_net": round(avg_win, 1),
            "pnl_net": round(total_pnl, 2),
            "sharpe": round(avg_sharpe, 2),
            "pos_tickers": pos_tickers,
            "total_tickers": len(common),
            "tp_hits": total_tp,
            "baseline_exits": total_base,
            "tc_exits": total_tc,
            "halves": halves_summary,
        })

    # Print summary
    print(f"{'config':32s} {'trades':>6s} {'win%':>6s} {'pnl%':>8s} {'sharpe':>7s} {'pos':>5s} {'base':>5s} {'tp':>4s} {'tc':>4s}")
    print("-" * 88)
    for r in all_results:
        flag = " ◀" if r["pnl_net"] > 0 else ""
        print(f"{r['name']:32s} {r['trades']:6d} {r['win_net']:6.1f} {r['pnl_net']:+8.2f} "
              f"{r['sharpe']:7.2f} {r['pos_tickers']:2d}/{r['total_tickers']}"
              f" {r['baseline_exits']:5d} {r['tp_hits']:4d} {r['tc_exits']:4d}{flag}")

    # Best config halves
    if all_results:
        best = max(all_results, key=lambda x: x["pnl_net"])
        print(f"\n=== Best: {best['name']} (pnl={best['pnl_net']:+.2f}%) ===")
        for half_name in ["1st_half", "2nd_half"]:
            h = best["halves"].get(half_name)
            if h:
                print(f"  {half_name}: trades={h['trades']}, win={h['win']:.1f}%, "
                      f"pnl={h['pnl']:+.2f}%, pos={h['pos']}/{h['total']}")

    # Detail for best hybrid config
    hybrids = [r for r in all_results if "HYBRID" in r["name"]]
    if hybrids:
        best = max(hybrids, key=lambda x: x["pnl_net"])
        best_wtf = "1day" if "1d" in best["name"] else "4h"
        best_k = 1.618 if "k1618" in best["name"] else 1.0
        best_h = 12 if "h12" in best["name"] else 6
        print(f"\n=== Per-ticker: {best['name']} ===")
        print(f"{'ticker':8s} {'trades':>6s} {'win%':>6s} {'pnl%':>8s} {'base':>5s} {'tp':>4s} {'tc':>4s}")
        print("-" * 52)
        for ticker in common:
            ltf_df = load_df(ticker, args.db, args.ltf)
            htf_df = load_df(ticker, args.db, "1day")
            if len(ltf_df) < 60 or len(htf_df) < 60:
                continue
            res = run_backtest(
                ticker, ltf_df, htf_df,
                wave_tf=best_wtf, k=best_k, time_cap=best_h,
                pattern=args.pattern, ltf_zone=args.ltf_zone,
                htf_zone=args.htf_zone, direction=args.direction,
                signal_hours=allowed_hours,
            )
            if res["trades"] > 0:
                flag = " ◀" if res["pnl_net"] > 0 else ""
                print(f"{ticker:8s} {res['trades']:6d} {res['win_net']:6.1f} "
                      f"{res['pnl_net']:+8.2f} {res['baseline_exits']:5d} "
                      f"{res['tp_hits']:4d} {res['tc_exits']:4d}{flag}")


if __name__ == "__main__":
    main()
