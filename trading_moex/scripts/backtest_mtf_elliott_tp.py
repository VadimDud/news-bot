#!/usr/bin/env python3
"""MTF + Elliott-wave TP backtest.

Entry: MTF signal (zone_break 4h + daily zone, bars 4/8/12 UTC) — same as
backtest_mtf_confirm.py.

Take-profit: TP = entry ± k × wave1_amplitude (wave 1-2 pair on a given TF).
- wave1_amplitude = high - low of the impulse wave (wave 1)
- wave 1-2 pair: two consecutive waves of opposite direction
- wave 2 must complete BEFORE the signal bar (causality)
- For long: wave 1 = bull, wave 2 = bear; TP = entry + k × L
- For short: wave 1 = bear, wave 2 = bull; TP = entry - k × L

Exit:
- TP hit within N bars (check each bar's high/low for limit fill)
- Time-cap: close at bar entry_bar + N if TP not hit
- No stop-loss

Usage (from trading_moex/):
    python3 scripts/backtest_mtf_elliott_tp.py
    python3 scripts/backtest_mtf_elliott_tp.py --wave-tf 1day --k 1.618 --time-cap 12
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
from app.elliott_candles import classify_candles, detect_waves  # noqa: E402

DEFAULT_DB = ROOT / "trading_moex" / "data" / "trader_4h.db"
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

DEPOSIT = 100_000.0
COMMISSION_PCT = 0.05
SLIPPAGE_PCT = 0.05
TOTAL_COST_PCT = 2 * (COMMISSION_PCT + SLIPPAGE_PCT)  # 0.2% round-trip


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


def _build_wave12_pairs(classified_df: pd.DataFrame) -> list[dict]:
    """Find consecutive opposite-direction wave pairs on classified df.

    Returns list of dicts:
      {pair_end_idx, direction, wave1_start, wave1_end, wave1_amp,
       wave2_start, wave2_end, wave2_low, wave2_high}

    direction = 'long'  → wave1=bull(impulse), wave2=bear(correction), TP above
    direction = 'short' → wave1=bear(impulse), wave2=bull(correction), TP below
    """
    waves = detect_waves(classified_df)
    if len(waves) < 2:
        return []

    pairs = []
    for i in range(len(waves) - 1):
        w1 = waves[i]
        w2 = waves[i + 1]
        if w1.direction == w2.direction:
            continue
        # wave 1 = impulse, wave 2 = correction
        if w1.direction == "bull":
            direction = "long"
        else:
            direction = "short"
        # wave1 amplitude = high - low over the wave1 candles
        w1_slice = classified_df.iloc[w1.start_idx:w1.end_idx + 1]
        w1_amp = float(w1_slice["high"].max() - w1_slice["low"].min())
        # wave2 extremes for sanity
        w2_slice = classified_df.iloc[w2.start_idx:w2.end_idx + 1]
        pairs.append({
            "pair_end_idx": w2.end_idx,  # last bar of wave 2
            "direction": direction,
            "wave1_start": w1.start_idx,
            "wave1_end": w1.end_idx,
            "wave1_amp": w1_amp,
            "wave2_start": w2.start_idx,
            "wave2_end": w2.end_idx,
            "wave2_low": float(w2_slice["low"].min()),
            "wave2_high": float(w2_slice["high"].max()),
        })
    return pairs


def last_wave12_before(classified_df: pd.DataFrame, signal_idx: int) -> dict | None:
    """Find the last completed wave 1-2 pair before signal_idx (causality).

    pair_end_idx must be < signal_idx (wave 2 finished before signal bar).
    """
    pairs = _build_wave12_pairs(classified_df)
    # filter: pair completed strictly before signal bar
    valid = [p for p in pairs if p["pair_end_idx"] < signal_idx]
    if not valid:
        return None
    return valid[-1]  # most recent


def honest_trades_elliott(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    wave_tf: str = "4h",
    k: float = 1.0,
    time_cap: int = 12,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    signal_hours: list[int] | None = None,
) -> list[dict]:
    """MTF entry + Elliott-wave TP.

    Entry on open of bar after signal. TP = entry ± k × wave1_amplitude.
    Exit: limit fill within time_cap bars, or close at time_cap.
    """
    ltf = mtf.prepare_ohlc(ltf_df)
    htf = mtf.prepare_ohlc(htf_df)
    if len(ltf) < max(ltf_zone, 50) + time_cap + 5 or len(htf) < htf_zone + 5:
        return []

    sig = mtf.mtf_signal(ltf, htf, pattern=pattern, ltf_zone=ltf_zone,
                          htf_zone=htf_zone, direction=direction)

    # Classify wave TF for Elliott wave detection
    if wave_tf == "4h":
        wave_df = classify_candles(ltf_df.copy())
    else:
        wave_df = classify_candles(htf_df.copy())

    # Build signal hours mask
    if signal_hours:
        sig_mask = ~ltf.index.to_series().dt.hour.isin(signal_hours)
    else:
        sig_mask = pd.Series(False, index=ltf.index)

    sig_np = sig.to_numpy(dtype=int)
    opens = ltf["open"].to_numpy(dtype=float)
    closes = ltf["close"].to_numpy(dtype=float)
    highs = ltf["high"].to_numpy(dtype=float)
    lows = ltf["low"].to_numpy(dtype=float)
    ltf_index = ltf.index  # for time lookup on wave TF

    trades = []
    in_trade = False
    entry_bar = 0
    entry_side = 0
    tp_price = 0.0

    for i in range(len(sig_np) - 1):
        if not in_trade:
            if sig_np[i] != 0 and not sig_mask.iloc[i + 1]:
                # Signal at bar i → entry at bar i+1
                side = sig_np[i]
                entry_bar = i + 1
                entry_side = side
                entry_price = opens[entry_bar]

                # Find wave 1-2 pair before signal bar on wave TF
                signal_time = ltf.index[i]
                # Map signal time to wave_df index position
                # For 4h: same df. For 1day: find the day containing signal_time
                if wave_tf == "4h":
                    wave_pos = wave_df.index.searchsorted(signal_time, side="right") - 1
                else:
                    wave_pos = wave_df.index.searchsorted(signal_time, side="right") - 1

                if wave_pos < 0:
                    continue

                pair = last_wave12_before(wave_df, wave_pos)
                if pair is None:
                    continue
                if (side == 1 and pair["direction"] != "long") or \
                   (side == -1 and pair["direction"] != "short"):
                    continue

                L = pair["wave1_amp"]
                if L <= 0:
                    continue

                if side == 1:
                    tp_price = entry_price + k * L
                else:
                    tp_price = entry_price - k * L

                in_trade = True
                tp_hit_bar = None
        else:
            bars_held = i - entry_bar + 1
            # Check if TP was hit during this bar
            if tp_hit_bar is None:
                if entry_side == 1:
                    # long: TP is above entry
                    if highs[i] >= tp_price:
                        tp_hit_bar = i
                else:
                    # short: TP is below entry
                    if lows[i] <= tp_price:
                        tp_hit_bar = i

            # Time-cap exit or TP hit
            if bars_held >= time_cap or i == len(sig_np) - 2 or tp_hit_bar is not None:
                if tp_hit_bar is not None:
                    exit_price = tp_price
                    exit_bar = tp_hit_bar
                else:
                    exit_bar = min(entry_bar + time_cap, len(opens) - 1)
                    exit_price = closes[exit_bar]

                entry_price = opens[entry_bar]
                if entry_side == 1:
                    pnl_pct = (exit_price / entry_price - 1.0) * 100.0
                else:
                    pnl_pct = (1.0 - exit_price / entry_price) * 100.0

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": exit_bar if tp_hit_bar is None else tp_hit_bar,
                    "side": "long" if entry_side == 1 else "short",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "tp_price": tp_price,
                    "wave1_amp": pair["wave1_amp"],
                    "tp_hit": tp_hit_bar is not None,
                    "pnl_pct": pnl_pct,
                    "pnl_net_pct": pnl_pct - TOTAL_COST_PCT,
                    "bars_held": (exit_bar if tp_hit_bar is None else tp_hit_bar) - entry_bar,
                })
                in_trade = False
    return trades


def run_backtest(
    ticker: str,
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    wave_tf: str = "4h",
    k: float = 1.0,
    time_cap: int = 12,
    pattern: str = "zone_break",
    ltf_zone: int = 20,
    htf_zone: int = 20,
    direction: int = 0,
    signal_hours: list[int] | None = None,
) -> dict:
    trades = honest_trades_elliott(
        ltf_df, htf_df, wave_tf=wave_tf, k=k, time_cap=time_cap,
        pattern=pattern, ltf_zone=ltf_zone, htf_zone=htf_zone,
        direction=direction, signal_hours=signal_hours,
    )
    if not trades:
        return {
            "ticker": ticker, "trades": 0, "win_raw": 0, "win_net": 0,
            "pnl_net": 0, "avg_pnl_net_pct": 0, "max_dd_pct": 0,
            "sharpe": 0, "tp_hits": 0, "tp_hit_rate": 0,
        }

    pnls = np.array([t["pnl_net_pct"] for t in trades])
    wins_raw = np.array([t["pnl_pct"] for t in trades])
    tp_hits = sum(1 for t in trades if t["tp_hit"])
    n = len(pnls)
    win_raw = float((wins_raw > 0).sum()) / n * 100.0
    win_net = float((pnls > 0).sum()) / n * 100.0
    pnl_net = float(pnls.sum())
    avg_pnl = float(pnls.mean())
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(dd.max()) if len(dd) > 0 else 0.0
    if len(pnls) > 1 and pnls.std() > 0:
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
    }


def _split_eras(ltf_df, htf_df):
    mid_date = ltf_df.index[len(ltf_df) // 2]
    h1_ltf, h2_ltf = ltf_df[ltf_df.index < mid_date], ltf_df[ltf_df.index >= mid_date]
    h1_htf, h2_htf = htf_df[htf_df.index < mid_date], htf_df[htf_df.index >= mid_date]
    return [
        ("1st_half", h1_ltf, h1_htf),
        ("2nd_half", h2_ltf, h2_htf),
    ]


def main():
    parser = argparse.ArgumentParser(description="MTF + Elliott-wave TP backtest")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--ltf", default="4h", choices=["60min", "4h"])
    parser.add_argument("--wave-tf", default="4h", choices=["4h", "1day"],
                        help="TF for wave 1-2 detection")
    parser.add_argument("--k", type=float, default=1.0,
                        help="TP multiplier on wave1 amplitude (1.0 or 1.618)")
    parser.add_argument("--time-cap", type=int, default=12,
                        help="Max bars to hold (time-cap exit at close)")
    parser.add_argument("--pattern", default="zone_break")
    parser.add_argument("--ltf-zone", type=int, default=20)
    parser.add_argument("--htf-zone", type=int, default=20)
    parser.add_argument("--direction", type=int, default=0)
    parser.add_argument("--signal-hours", type=str, default="4,8,12",
                        help="Allowed signal-bar hours UTC (comma-separated)")
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

    # Baseline: close + 6 bars (same as backtest_mtf_confirm)
    print(f"=== MTF + Elliott TP: wave_tf={args.wave_tf} k={args.k} time_cap={args.time_cap} ===")
    print(f"Pattern={args.pattern}, LTF={args.ltf}, HTF=1day, cost={TOTAL_COST_PCT:.2f}%")
    print(f"Signal hours (UTC): {allowed_hours}")
    print(f"Tickers: {', '.join(common)}\n")

    # Grid: (wave_tf, k, time_cap) + baseline
    configs = [
        ("4h",  1.0,   6,  "baseline_4h_h6"),
        ("4h",  1.0,  12,  "Elliott_4h_k1_h12"),
        ("4h",  1.0,  24,  "Elliott_4h_k1_h24"),
        ("4h",  1.618, 6,  "Elliott_4h_k1618_h6"),
        ("4h",  1.618, 12, "Elliott_4h_k1618_h12"),
        ("4h",  1.618, 24, "Elliott_4h_k1618_h24"),
        ("1day", 1.0,   6, "Elliott_1d_k1_h6"),
        ("1day", 1.0,  12, "Elliott_1d_k1_h12"),
        ("1day", 1.0,  24, "Elliott_1d_k1_h24"),
        ("1day", 1.618, 6, "Elliott_1d_k1618_h6"),
        ("1day", 1.618, 12, "Elliott_1d_k1618_h12"),
        ("1day", 1.618, 24, "Elliott_1d_k1618_h24"),
    ]

    # For baseline, use simple time-cap without Elliott TP (wave_tf irrelevant)
    all_grid_results = []

    for cfg_wtf, cfg_k, cfg_h, cfg_name in configs:
        results = []
        halves = {"1st_half": [], "2nd_half": []}

        for ticker in common:
            ltf_df = load_df(ticker, args.db, args.ltf)
            htf_df = load_df(ticker, args.db, "1day")
            if len(ltf_df) < 60 or len(htf_df) < 60:
                continue

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
        total_tp = int(df["tp_hits"].sum())
        avg_tp_rate = df["tp_hit_rate"].mean()

        halves_summary = {}
        for name in ["1st_half", "2nd_half"]:
            hr = halves[name]
            if not hr:
                continue
            hdf = pd.DataFrame(hr)
            halves_summary[name] = {
                "trades": int(hdf["trades"].sum()),
                "win": hdf["win_net"].mean(),
                "pnl": hdf["pnl_net"].sum(),
                "pos": (hdf["pnl_net"] > 0).sum(),
                "total": len(hr),
            }

        all_grid_results.append({
            "name": cfg_name,
            "wave_tf": cfg_wtf,
            "k": cfg_k,
            "time_cap": cfg_h,
            "trades": total_trades,
            "win_net": round(avg_win, 1),
            "pnl_net": round(total_pnl, 2),
            "sharpe": round(avg_sharpe, 2),
            "pos_tickers": pos_tickers,
            "total_tickers": len(common),
            "tp_hits": total_tp,
            "tp_hit_rate": round(avg_tp_rate, 1),
            "halves": halves_summary,
        })

    # Print summary table
    print(f"{'config':28s} {'trades':>6s} {'win%':>6s} {'pnl%':>8s} {'sharpe':>7s} {'pos':>5s} {'tp%':>6s}")
    print("-" * 78)
    for r in all_grid_results:
        flag = " ◀" if r["pnl_net"] > 0 else ""
        print(f"{r['name']:28s} {r['trades']:6d} {r['win_net']:6.1f} {r['pnl_net']:+8.2f} "
              f"{r['sharpe']:7.2f} {r['pos_tickers']:2d}/{r['total_tickers']}"
              f" {r['tp_hit_rate']:5.1f}%{flag}")

    # Halves detail for best config
    if all_grid_results:
        best = max(all_grid_results, key=lambda x: x["pnl_net"])
        print(f"\n=== Best: {best['name']} (pnl={best['pnl_net']:+.2f}%) ===")
        for half_name in ["1st_half", "2nd_half"]:
            h = best["halves"].get(half_name)
            if h:
                print(f"  {half_name}: trades={h['trades']}, win={h['win']:.1f}%, "
                      f"pnl={h['pnl']:+.2f}%, pos={h['pos']}/{h['total']}")

    # Per-ticker detail for best config
    if all_grid_results:
        best = max(all_grid_results, key=lambda x: x["pnl_net"])
        cfg_wtf, cfg_k, cfg_h = best["wave_tf"], best["k"], best["time_cap"]
        print(f"\n=== Per-ticker detail: {best['name']} ===")
        print(f"{'ticker':8s} {'trades':>6s} {'win%':>6s} {'pnl%':>8s} {'sharpe':>7s} {'tp%':>6s}")
        print("-" * 50)
        for ticker in common:
            ltf_df = load_df(ticker, args.db, args.ltf)
            htf_df = load_df(ticker, args.db, "1day")
            if len(ltf_df) < 60 or len(htf_df) < 60:
                continue
            res = run_backtest(
                ticker, ltf_df, htf_df,
                wave_tf=cfg_wtf, k=cfg_k, time_cap=cfg_h,
                pattern=args.pattern, ltf_zone=args.ltf_zone,
                htf_zone=args.htf_zone, direction=args.direction,
                signal_hours=allowed_hours,
            )
            if res["trades"] > 0:
                flag = " ◀" if res["pnl_net"] > 0 else ""
                print(f"{ticker:8s} {res['trades']:6d} {res['win_net']:6.1f} "
                      f"{res['pnl_net']:+8.2f} {res['sharpe']:7.2f} "
                      f"{res['tp_hit_rate']:5.1f}%{flag}")


if __name__ == "__main__":
    main()
