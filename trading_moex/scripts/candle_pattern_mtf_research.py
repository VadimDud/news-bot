#!/usr/bin/env python3
"""Multi-timeframe continuation research: LTF signal + HTF zone filter.

Паттерны (zone_break, marubozu, strong_body, engulfing, three_soldiers) на
часовом/4h ТФ как **сигнал**, дневной зона-режим (close > max(high[K]) /
< min(low[K])) как **фильтр-подтверждение**. Замеряем, повышает ли фильтр
вероятность continuation.

Используются данные из БД trader_4h.db:
- LTF: 60min (SBER, T ~1 год), 4h (9 тикеров ~13 мес);
- HTF: 1day (11 тикеров, 2021–2026).

Usage (from trading_moex/):
    python3 scripts/candle_pattern_mtf_research.py
    python3 scripts/candle_pattern_mtf_research.py --pattern zone_break --htf-zone 20
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
WAR_START = pd.Timestamp("2022-02-24")


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
    con = sqlite3.connect(str(db))
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


def available_tickers(db: str, period: str) -> list[str]:
    con = sqlite3.connect(str(db))
    rows = con.execute(
        "SELECT DISTINCT ticker FROM candles WHERE period=?", (period,)
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _halves(df: pd.DataFrame):
    mid = len(df) // 2
    return ("1st_half", df.iloc[:mid]), ("2nd_half", df.iloc[mid:])


def _eras(df: pd.DataFrame):
    war = df.index >= WAR_START
    return ("peace", df[~war]), ("war", df[war])


def _agg_stats(all_stats: list[pd.DataFrame]) -> pd.DataFrame:
    if not all_stats:
        return pd.DataFrame()
    df = pd.concat(all_stats, ignore_index=True)
    if df.empty:
        return df

    def _wavg(grp, col):
        w = grp["n"]
        return round(float(np.average(grp[col], weights=w)), 1) if w.sum() > 0 else 0.0

    out = df.groupby(["label", "side"]).apply(
        lambda grp: pd.Series({
            "total_n": int(grp["n"].sum()),
            "win_pct": _wavg(grp, "win_pct"),
            "base_pct": _wavg(grp, "base_pct"),
            "edge_pct": _wavg(grp, "edge_pct"),
            "mean_atr": round(float(np.average(grp["mean_atr"], weights=grp["n"])), 3) if grp["n"].sum() > 0 else 0.0,
        }),
        include_groups=False,
    ).reset_index()
    out = out[out["total_n"] > 0]
    # z-score по объединённой выборке
    tot_win = []
    for (label, side), grp in df.groupby(["label", "side"]):
        tot_win.append((label, side, int((grp["win_pct"] / 100.0 * grp["n"]).sum())))
    tw = pd.DataFrame(tot_win, columns=["label", "side", "win_n"])
    out = out.merge(tw, on=["label", "side"], how="left")
    base = (out["base_pct"] / 100.0).clip(0.01, 0.99)
    se = np.sqrt(base * (1 - base) / out["total_n"].clip(lower=1))
    out["z"] = ((out["win_n"] / out["total_n"].clip(lower=1)) - base) / se
    out["z"] = out["z"].round(2)
    return out.sort_values(["side", "label"]).reset_index(drop=True)


def _lift_table(all_stats: list[pd.DataFrame]) -> pd.DataFrame:
    """Сводная таблица: lift (confirmed z − no_filter z) по паттернам."""
    if not all_stats:
        return pd.DataFrame()
    df = pd.concat(all_stats, ignore_index=True)
    if df.empty:
        return df

    rows = []
    for (pat, side), grp in df.groupby(["pattern", "side"]):
        nf = grp[grp["label"] == "no_filter"]
        cf = grp[grp["label"] == "confirmed"]
        if nf.empty or cf.empty:
            continue
        rows.append({
            "pattern": pat,
            "side": side,
            "n_nf": int(nf["n"].values[0]),
            "n_cf": int(cf["n"].values[0]),
            "z_nf": float(nf["z"].values[0]),
            "z_cf": float(cf["z"].values[0]),
            "lift_z": round(float(cf["z"].values[0]) - float(nf["z"].values[0]), 2),
            "win_nf": float(nf["win_pct"].values[0]),
            "win_cf": float(cf["win_pct"].values[0]),
            "lift_win": round(float(cf["win_pct"].values[0]) - float(nf["win_pct"].values[0]), 1),
        })
    return pd.DataFrame(rows).sort_values("lift_z", ascending=False)


def _per_ticker_table(all_stats_by_ticker: list[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    """Доля тикеров, где фильтр улучшает edge (confirmed win% > no_filter win%)."""
    rows = []
    for ticker, stats in all_stats_by_ticker:
        if stats.empty:
            continue
        for (pat, side), grp in stats.groupby(["pattern", "side"]):
            nf = grp[grp["label"] == "no_filter"]
            cf = grp[grp["label"] == "confirmed"]
            if nf.empty or cf.empty:
                continue
            rows.append({
                "ticker": ticker, "pattern": pat, "side": side,
                "win_nf": float(nf["win_pct"].values[0]),
                "win_cf": float(cf["win_pct"].values[0]),
                "lift": round(float(cf["win_pct"].values[0]) - float(nf["win_pct"].values[0]), 1),
                "n": int(cf["n"].values[0]),
            })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="MTF continuation research")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--ltf", default="60min", choices=["60min", "4h"])
    parser.add_argument("--pattern", default=None, help="Один паттерн (или все)")
    parser.add_argument("--ltf-zone", type=int, default=20)
    parser.add_argument("--htf-zone", type=int, default=20)
    parser.add_argument("--htf-filter", default="zone", choices=["zone", "ma_single", "ma_cross", "grid"])
    parser.add_argument("--htf-ma-fast", type=int, default=20)
    parser.add_argument("--htf-ma-slow", type=int, default=50)
    parser.add_argument("--htf-atr-neutral", type=float, default=0.0)
    parser.add_argument("--horizon", type=int, default=6, help="Forward bars on LTF")
    parser.add_argument("--min-events", type=int, default=10)
    args = parser.parse_args()

    FILTER_GRID = {
        "zone": {"htf_filter": "zone", "htf_zone": args.htf_zone},
        "ema20": {"htf_filter": "ma_single", "htf_ma_fast": 20},
        "ema50": {"htf_filter": "ma_single", "htf_ma_fast": 50},
        "ema200": {"htf_filter": "ma_single", "htf_ma_fast": 200},
        "ema20_50": {"htf_filter": "ma_cross", "htf_ma_fast": 20, "htf_ma_slow": 50},
        "ema50_200": {"htf_filter": "ma_cross", "htf_ma_fast": 50, "htf_ma_slow": 200},
    }
    if args.htf_filter == "grid":
        filters_to_run = FILTER_GRID
    else:
        fk = {"htf_filter": args.htf_filter, "htf_zone": args.htf_zone,
              "htf_ma_fast": args.htf_ma_fast, "htf_ma_slow": args.htf_ma_slow,
              "htf_atr_neutral": args.htf_atr_neutral}
        filters_to_run = {args.htf_filter: fk}

    ltf_tickers = available_tickers(args.db, args.ltf)
    htf_tickers = available_tickers(args.db, "1day")
    common = sorted(set(ltf_tickers) & set(htf_tickers))
    if not common:
        print(f"Нет тикеров с {args.ltf} + 1day в {args.db}")
        return

    patterns = [args.pattern] if args.pattern else ["zone_break", "marubozu", "strong_body", "engulfing", "three_soldiers"]
    filter_names = list(filters_to_run.keys())
    print(f"=== MTF Research: LTF={args.ltf}, HTF=1day, filters={filter_names}, horizon={args.horizon} ===")
    print(f"Tickers: {', '.join(common)}")

    for filter_name, filter_kw in filters_to_run.items():
        print(f"\n{'#'*70}")
        print(f"FILTER: {filter_name}  params={filter_kw}")
        print(f"{'#'*70}")

        all_agg = []
        per_ticker_agg = []

        for pat in patterns:
            print(f"\n{'='*70}")
            print(f"PATTERN: {pat}")
            print(f"{'='*70}")

            h1_all, h2_all = [], []

            for t in common:
                ltf_df = load_df(t, args.db, args.ltf)
                htf_df = load_df(t, args.db, "1day")
                if len(ltf_df) < 60 or len(htf_df) < 60:
                    continue

                stats = mtf.mtf_stats(
                    ltf_df, htf_df, pattern=pat,
                    ltf_zone=args.ltf_zone, htf_zone=args.htf_zone,
                    horizon=args.horizon, min_events=args.min_events,
                    htf_filter=filter_kw.get("htf_filter", "zone"),
                    htf_ma_fast=filter_kw.get("htf_ma_fast", 20),
                    htf_ma_slow=filter_kw.get("htf_ma_slow", 50),
                    htf_atr_neutral=filter_kw.get("htf_atr_neutral", 0.0),
                )
                if stats.empty:
                    continue
                stats["ticker"] = t
                stats["pattern"] = pat
                stats["filter"] = filter_name
                all_agg.append(stats)
                per_ticker_agg.append((t, stats))

                # halves
                h1_ltf, h2_ltf = _halves(ltf_df)
                h1_htf, h2_htf = _halves(htf_df)
                if len(h1_ltf) >= 30 and len(h1_htf) >= 30:
                    s1 = mtf.mtf_stats(h1_ltf, h1_htf, pattern=pat, ltf_zone=args.ltf_zone,
                                        htf_zone=args.htf_zone, horizon=args.horizon,
                                        min_events=max(3, args.min_events // 2),
                                        htf_filter=filter_kw.get("htf_filter", "zone"),
                                        htf_ma_fast=filter_kw.get("htf_ma_fast", 20),
                                        htf_ma_slow=filter_kw.get("htf_ma_slow", 50),
                                        htf_atr_neutral=filter_kw.get("htf_atr_neutral", 0.0))
                    if not s1.empty:
                        h1_all.append(s1)
                if len(h2_ltf) >= 30 and len(h2_htf) >= 30:
                    s2 = mtf.mtf_stats(h2_ltf, h2_htf, pattern=pat, ltf_zone=args.ltf_zone,
                                        htf_zone=args.htf_zone, horizon=args.horizon,
                                        min_events=max(3, args.min_events // 2),
                                        htf_filter=filter_kw.get("htf_filter", "zone"),
                                        htf_ma_fast=filter_kw.get("htf_ma_fast", 20),
                                        htf_ma_slow=filter_kw.get("htf_ma_slow", 50),
                                        htf_atr_neutral=filter_kw.get("htf_atr_neutral", 0.0))
                    if not s2.empty:
                        h2_all.append(s2)

            # ── Aggregated tables ──
            agg = _agg_stats(all_agg) if all_agg else pd.DataFrame()
            if not agg.empty:
                print(f"\n--- Pooled ({len(common)} tickers) ---")
                _print_mtf_table(agg)

            h1_agg = _agg_stats(h1_all) if h1_all else pd.DataFrame()
            if not h1_agg.empty:
                print(f"\n--- 1st half ---")
                _print_mtf_table(h1_agg)

            h2_agg = _agg_stats(h2_all) if h2_all else pd.DataFrame()
            if not h2_agg.empty:
                print(f"\n--- 2nd half ---")
                _print_mtf_table(h2_agg)

        # ── Lift table per filter+pattern ──
        lift = _lift_table([s for s in all_agg if "pattern" in s.columns])
        if not lift.empty:
            print(f"\n--- Lift: confirmed vs no_filter ({filter_name}) ---")
            print(f"{'pat':16s} {'side':6s} {'n_nf':>5s} {'n_cf':>5s} {'z_nf':>7s} {'z_cf':>7s} {'Δz':>7s} {'win_nf':>7s} {'win_cf':>7s} {'Δwin%':>7s}")
            for _, r in lift.iterrows():
                flag = " ◀" if r["lift_z"] > 0 and r["z_cf"] >= 2.0 else ""
                print(f"{r['pattern']:16s} {r['side']:6s} {r['n_nf']:5d} {r['n_cf']:5d} {r['z_nf']:+7.2f} {r['z_cf']:+7.2f} "
                      f"{r['lift_z']:+7.2f} {r['win_nf']:7.1f} {r['win_cf']:7.1f} {r['lift_win']:+7.1f}{flag}")

    # ── Cross-filter comparison (grid mode) ──
    if len(filters_to_run) > 1 and per_ticker_agg:
        pt = _per_ticker_table(per_ticker_agg)
        if not pt.empty:
            print(f"\n{'='*70}")
            print("CROSS-FILTER COMPARISON: avg lift per filter")
            print(f"{'='*70}")
            g = pt.groupby(["pattern", "side"]).apply(
                lambda grp: pd.Series({
                    "positive_frac": round((grp["lift"] > 0).mean(), 2),
                    "positive_n": int((grp["lift"] > 0).sum()),
                    "total_tickers": int(len(grp)),
                    "avg_lift": round(float(grp["lift"].mean()), 1),
                }),
                include_groups=False,
            ).reset_index()
            g = g.sort_values("avg_lift", ascending=False)
            print(g.to_string(index=False))


def _print_mtf_table(df: pd.DataFrame):
    print(f"{'label':14s} {'side':6s} {'n':>6s} {'win%':>7s} {'base%':>7s} {'edge%':>7s} {'meanATR':>8s} {'z':>7s}")
    for _, r in df.iterrows():
        flag = " ◀" if abs(r["z"]) >= 2.5 else ""
        print(f"{r['label']:14s} {r['side']:6s} {int(r['total_n']):6d} {r['win_pct']:7.1f} "
              f"{r['base_pct']:7.1f} {r['edge_pct']:+7.1f} {r['mean_atr']:+8.3f} {r['z']:+7.2f}{flag}")


if __name__ == "__main__":
    main()
