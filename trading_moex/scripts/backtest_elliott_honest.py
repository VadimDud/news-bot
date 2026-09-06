#!/usr/bin/env python3
"""Честная проверка Elliott micro-wave стратегии на 10M депозите с мартингейлом.

⚠️ КРИТИЧЕСКИЙ ВЫВОД (2026-09): прод-бэктест elliott_candles.run_backtest
содержит LOOKAHEAD-БАГ. detect_waves считает волну завершённой только когда
следующая свеча уже ДРУГОГО цвета — и вход делается на open этой подтверждающей
свечи, чьё направление (close>open или close<open) УЖЕ ИЗВЕСТНО по построению.
Fade-направление противоположно волне == совпадает с направлением подтверждающей
свечи -> win 98.8%, «прибыль» — тавтология. В live цвет следующей свечи неизвестен.

Этот скрипт моделирует live-faithful: сигнал в момент закрытия свечи, завершающей
волну L=3..5 (без знания следующей), вход на open следующей, выход на close той же.

Live-faithful результаты (10 тикеров, 1day, 10M депозит):
  - raw (без мартингейла): win 52.8%, gross +0.08%/сделку — после комиссии ~0,
    край отсутствует;
  - качество РЕАЛЬНО отбирает: q>=0.8 -> win 61.1%, gross +0.36% (324 сделки);
    после комиссии 0.1% -> +0.26%/сделку; 8 из 10 тикеров положительны;
  - мартингейл 25→50→100 на всех сигналах: maxDD 521% депозита (РАЗОРЕНИЕ);
  - мартингейл на q>=0.8: win циклов 92%, 26 трёхшаговых потерь, maxDD 25.5%,
    net ~+4.5M на 10M за ~5 лет (SBER 15 лет) — выживает, но тонкий край.

Вердикт по 5 условиям «стратегия работает»:
  1. raw>0 — ТОЛЬКО при q>=0.8 (частично);
  2. переживает затраты — тонкий край +0.26%/сделку, умирает при slippage 0.1%;
  3. устойчивость по тикерам — 8/10 при q>=0.8 (частично);
  4. maxDD — без фильтра мартингейл разоряет; q>=0.8 -> 25.5% (погранично);
  5. quality отбирает — ДА (q>=0.8 лучше q<0.4: 61% vs 52% win).

Прод-бэктест НЕ соответствует реальности; не доверять его цифрам.

Usage (from trading_moex/):
    python3 scripts/backtest_elliott_honest.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app import elliott_candles as ec  # noqa: E402

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
DEPOSIT = 10_000_000.0
WAR_START = pd.Timestamp("2022-02-24")


def load_df(ticker: str, db: str) -> pd.DataFrame:
    con = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT begin AS dt, open, high, low, close, volume FROM candles"
        " WHERE ticker=? AND period='1day' ORDER BY begin",
        con, params=(ticker,),
    )
    con.close()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    return df[~df.index.duplicated(keep="last")]


def live_faithful_signals(df: pd.DataFrame, wave_min: int = 3, wave_max: int = 5,
                          quality_min: float = 0.0) -> list[dict]:
    """Live-faithful сигналы: волна L=3..5 завершена на закрытии свечи i —
    сигнал становится известен ТОЛЬКО тогда, вход на open свечи i+1 (цвет
    следующей свечи неизвестен). Без lookahead прод-бэктеста.

    Возвращает [{sig_idx, fade, quality, open_next, close_next}].
    """
    classified = ec.classify_candles(df, body_ratio_min=0.6, atr_period=14, atr_k=0.5)
    colors = classified["candle_color"].values
    n = len(colors)
    out: list[dict] = []
    i = 0
    while i < n:
        c = colors[i]
        if c == "doji":
            i += 1
            continue
        j = i
        while j < n and colors[j] == c:
            j += 1
        run_len = j - i
        # В live при каждом закрытии свечи, продлевающей серию до L∈[3..5],
        # фиксируется волна длины L (следующая свеча ещё не известна).
        for L in range(wave_min, min(run_len, wave_max) + 1):
            sig_idx = i + L - 1
            if sig_idx + 1 >= n:
                break
            wave = ec.Wave(start_idx=i, end_idx=sig_idx, direction=c,
                           candle_count=L, df=classified)
            q = ec.wave_quality_score(wave)["total"]
            if quality_min > 0 and q < quality_min:
                continue
            fade = "long" if c == "bear" else "short"
            out.append({
                "sig_idx": sig_idx,
                "fade": fade,
                "quality": q,
                "open_next": float(df["open"].iloc[sig_idx + 1]),
                "close_next": float(df["close"].iloc[sig_idx + 1]),
                "date": str(df.index[sig_idx]),
            })
        i = j
    return out


def _run_steps(df: pd.DataFrame, wave: ec.Wave, equity_start: float, base_pct: float,
               max_steps: int, commission: float, slippage: float) -> dict:
    """Мартингейл-цикл с честным пошаговым компаундингом и слайпеджем.

    Возвращает: {trades: [...], pnl_sum, steps, equity_after, worst_eq}.
    """
    fade_dir = "long" if wave.direction == "bear" else "short"
    cur_idx = wave.end_idx + 1
    equity = equity_start
    worst_eq = equity
    step = 0
    trades = []
    while step < max_steps and cur_idx < len(df):
        if df["candle_color"].iloc[cur_idx] == "doji":
            cur_idx += 1
            continue
        step += 1
        entry = float(df["open"].iloc[cur_idx])
        exit_ = float(df["close"].iloc[cur_idx])
        size_pct = base_pct * (2 ** (step - 1))
        size_value = equity * min(size_pct, 1.0)
        if fade_dir == "long":
            e = entry * (1 + slippage)
            x = exit_ * (1 - slippage)
            gross_pct = (x - e) / e
        else:
            e = entry * (1 - slippage)
            x = exit_ * (1 + slippage)
            gross_pct = (e - x) / e
        net_pct = gross_pct - 2 * commission
        pnl = size_value * net_pct
        trades.append({"dir": fade_dir, "step": step, "size": size_value,
                       "net_pct": net_pct, "pnl": pnl})
        equity += pnl
        worst_eq = min(worst_eq, equity)
        if pnl >= 0:
            break
        cur_idx += 1
    return {"trades": trades, "pnl_sum": equity - equity_start,
            "steps": step, "equity_after": equity, "worst_eq": worst_eq}


def run_cycle_sim(df: pd.DataFrame, waves: list[ec.Wave], quality_min: float,
                  base_pct: float, max_steps: int, commission: float,
                  slippage: float, deposit: float, martingale: bool = True) -> dict:
    """Полный прогон по волнам: мартингейл (или raw без удвоения).

    При martingale=False — один шаг 25% на волну, без удвоения.
    """
    equity = deposit
    peak = equity
    max_dd = 0.0
    cycles = []
    busy_until = -1
    for wave in waves:
        if not wave.has_next_candle():
            continue
        if wave.end_idx <= busy_until:
            continue
        q = ec.wave_quality_score(wave)["total"]
        if quality_min > 0 and q < quality_min:
            continue
        if not martingale:
            r = _run_steps(df, wave, equity, base_pct, 1, commission, slippage)
        else:
            r = _run_steps(df, wave, equity, base_pct, max_steps, commission, slippage)
        equity = r["equity_after"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - r["worst_eq"])
        cycles.append({"wave_end": str(wave.end_dt), "dir": wave.direction,
                       "quality": q, "steps": r["steps"], "pnl": r["pnl_sum"],
                       "equity": equity})
        busy_until = wave.end_idx + r["steps"] - 1 if r["steps"] else wave.end_idx
    return {"cycles": cycles, "final_equity": equity, "max_dd": max_dd,
            "max_dd_pct": max_dd / deposit * 100}


def _report(cycles: list[dict], deposit: float, label: str, max_dd: float = 0.0) -> None:
    if not cycles:
        print(f"{label:44} нет циклов")
        return
    pnls = np.array([c["pnl"] for c in cycles])
    n_win = int((pnls > 0).sum())
    n3 = sum(1 for c in cycles if c["steps"] == 3 and c["pnl"] <= 0)
    final = deposit + float(pnls.sum())
    # Истинный maxDD по последовательности циклов (в порядке завершения)
    eq = deposit
    peak = eq
    mdd = 0.0
    for c in cycles:
        eq += c["pnl"]
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    print(f"{label:44} циклов={len(cycles):>4} win={n_win/len(cycles)*100:>5.1f}% "
          f"net={final-deposit:>+12,.0f} ({(final-deposit)/deposit*100:+.2f}%) "
          f"maxDD={mdd:>10,.0f} ({mdd/deposit*100:.2f}%) "
          f"3шаг-потерь={n3:>3} p5_цикл={np.percentile(pnls,5):>+10,.0f}")


def _trade_signal(sig: dict, equity: float, base_pct: float, max_steps: int,
                  commission: float, slippage: float, df: pd.DataFrame,
                  martingale: bool = True) -> dict:
    """Мартингейл-цикл от одного live-сигнала: шаги на последующих свечах.

    Шаг k: вход open[сиг_idx+k], выход close[сиг_idx+k] (цвет неизвестен заранее).
    """
    e = equity
    step = 0
    trades = []
    idx = sig["sig_idx"]
    while step < max_steps and idx + 1 < len(df):
        idx += 1
        o = float(df["open"].iloc[idx])
        cl = float(df["close"].iloc[idx])
        size = e * min(base_pct * (2 ** step), 1.0)
        if sig["fade"] == "long":
            en = o * (1 + slippage)
            ex = cl * (1 - slippage)
            gross = (ex - en) / en
        else:
            en = o * (1 - slippage)
            ex = cl * (1 + slippage)
            gross = (en - ex) / en
        pnl = size * (gross - 2 * commission)
        trades.append({"step": step + 1, "pnl": pnl})
        e += pnl
        step += 1
        if pnl >= 0:
            break
        if not martingale:
            break
    return {"pnl_sum": e - equity, "steps": step, "equity_after": e}


def main() -> None:
    parser = argparse.ArgumentParser(description="Elliott честная проверка (10M)")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--quality", type=float, default=0.0)
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    print(f"Elliott 10M LIVE-FAITHFUL | депозит={DEPOSIT:,.0f} ₽ | "
          f"комиссия={args.commission*100:.2f}% | слайпедж={args.slippage*100:.2f}%\n")
    print("(сигнал на закрытии свечи, завершающей волну L=3..5; вход на open "
          "следующей — без знания её цвета; lookahead прод-бэктеста устранён)\n")

    # Кэш сигналов (live-faithful) и df
    ticker_sig: dict[str, list[dict]] = {}
    ticker_df: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = load_df(t, args.db)
        if df.empty:
            continue
        ticker_df[t] = df
        ticker_sig[t] = live_faithful_signals(df, 3, 5, quality_min=args.quality)

    # ── B. Raw без мартингейла по тикерам (главный вопрос «есть ли сигнал») ──
    print("B. Raw-сигнал БЕЗ мартингейла (один шаг 25% на волну), по тикерам:")
    agg_gross = []
    for t in tickers:
        sigs = ticker_sig.get(t, [])
        df = ticker_df.get(t)
        if df is None:
            continue
        gs = []
        for s in sigs:
            r = _trade_signal(s, DEPOSIT, 0.25, 1, args.commission, args.slippage,
                              df, martingale=False)
            gs.append(r["pnl_sum"])
        if not gs:
            continue
        a = np.array(gs)
        agg_gross.extend(gs)
        print(f"    {t:<6} n={len(a):>4} win={(a>0).mean()*100:>5.1f}% "
              f"net_mean={a.mean()/DEPOSIT*100:+.3f}% net={a.sum():>+12,.0f}")
    if agg_gross:
        a = np.array(agg_gross)
        print(f"    ИТОГО: n={len(a):>4} win={(a>0).mean()*100:>5.1f}% "
              f"net_mean={a.mean()/DEPOSIT*100:+.3f}% net={a.sum():>+12,.0f}")

    # ── A. Мартингейл live-faithful по порогам качества ─────────────────────
    print("\nA. Мартингейл 25→50→100 (live-faithful) по порогам качества:")
    for qmin in (0.0, 0.4, 0.6, 0.8):
        equity = DEPOSIT
        peak = equity
        mdd = 0.0
        wins = 0
        cycles = 0
        lost3 = 0
        ruin = False
        for t in tickers:
            df = ticker_df.get(t)
            if df is None:
                continue
            sigs = live_faithful_signals(df, 3, 5, quality_min=qmin)
            for s in sigs:
                r = _trade_signal(s, equity, 0.25, 3, args.commission,
                                  args.slippage, df, martingale=True)
                cycles += 1
                if r["pnl_sum"] > 0:
                    wins += 1
                if r["steps"] == 3 and r["pnl_sum"] <= 0:
                    lost3 += 1
                equity = r["equity_after"]
                peak = max(peak, equity)
                mdd = max(mdd, peak - equity)
                if equity <= 0:
                    ruin = True
        if cycles:
            print(f"    q>={qmin}: циклов={cycles:>4} win={wins/cycles*100:>5.1f}% "
                  f"3шаг-потерь={lost3:>3} net={equity-DEPOSIT:>+13,.0f} "
                  f"maxDD={mdd/DEPOSIT*100:>5.1f}% разорение={ruin}")

    # ── C. Sweep затрат при q>=0.8 (лучший порог) ───────────────────────────
    print("\nC. Sweep затрат (мартингейл, q>=0.8, все тикеры):")
    print(f"    {'комиссия':>9} {'слайпедж':>9} {'net':>14} {'win%':>6} {'maxDD%':>7}")
    for comm in (0.0005, 0.001, 0.002, 0.003):
        for slip in (0.0, 0.0005, 0.001):
            equity = DEPOSIT
            peak = equity
            mdd = 0.0
            wins = 0
            cycles = 0
            for t in tickers:
                df = ticker_df.get(t)
                if df is None:
                    continue
                for s in live_faithful_signals(df, 3, 5, quality_min=0.8):
                    r = _trade_signal(s, equity, 0.25, 3, comm, slip, df,
                                      martingale=True)
                    cycles += 1
                    wins += 1 if r["pnl_sum"] > 0 else 0
                    equity = r["equity_after"]
                    peak = max(peak, equity)
                    mdd = max(mdd, peak - equity)
            if not cycles:
                continue
            print(f"    {comm*100:>7.2f}% {slip*100:>7.2f}% "
                  f"{equity-DEPOSIT:>14,.0f} {wins/cycles*100:>6.1f} {mdd/DEPOSIT*100:>7.1f}")

    # ── D. Качество: реальный wave_quality_score vs результат ───────────────
    print("\nD. Качество (live-faithful, raw): q-бакеты vs win/gross:")
    allq = []
    for t in tickers:
        df = ticker_df.get(t)
        if df is None:
            continue
        for s in live_faithful_signals(df, 3, 5, quality_min=0.0):
            if s["fade"] == "long":
                gross = (s["close_next"] - s["open_next"]) / s["open_next"]
            else:
                gross = (s["open_next"] - s["close_next"]) / s["open_next"]
            allq.append({"q": s["quality"], "gross": gross})
    qdf = pd.DataFrame(allq)
    for lo, hi, lbl in ((0, 0.4, "q<0.4"), (0.4, 0.6, "0.4-0.6"),
                        (0.6, 0.8, "0.6-0.8"), (0.8, 1.01, "q>=0.8")):
        g = qdf[(qdf["q"] >= lo) & (qdf["q"] < hi)]
        if len(g):
            print(f"    {lbl:10}: n={len(g):>4} win={(g['gross']>0).mean()*100:>5.1f}% "
                  f"gross_mean={g['gross'].mean()*100:+.3f}% "
                  f"gross_med={g['gross'].median()*100:+.3f}%")

    # ── E. Режим: мирный vs военный ─────────────────────────────────────────
    print("\nE. Режим (мартингейл, q>=0.8):")
    for label, mask in (("мирный", lambda idx: idx < WAR_START),
                        ("военный", lambda idx: idx >= WAR_START)):
        equity = DEPOSIT
        wins = 0
        cycles = 0
        for t in tickers:
            df = ticker_df.get(t)
            if df is None:
                continue
            dfw = df[mask(df.index)]
            if len(dfw) < 20:
                continue
            for s in live_faithful_signals(dfw, 3, 5, quality_min=0.8):
                r = _trade_signal(s, equity, 0.25, 3, args.commission,
                                  args.slippage, dfw, martingale=True)
                cycles += 1
                wins += 1 if r["pnl_sum"] > 0 else 0
                equity = r["equity_after"]
        if cycles:
            print(f"    {label:8}: циклов={cycles:>4} win={wins/cycles*100:>5.1f}% "
                  f"net={equity-DEPOSIT:>+13,.0f}")

    # ── F. Рандом-контроль ──────────────────────────────────────────────────
    print("\nF. Рандом-контроль (случайные интрадей-входы, q>=0.8 частота):")
    rng = np.random.default_rng(42)
    n_sig = sum(len(live_faithful_signals(df, 3, 5, quality_min=0.8))
                for df in ticker_df.values())
    rand_pnls = []
    for t in tickers:
        df = ticker_df.get(t)
        if df is None:
            continue
        n = len(live_faithful_signals(df, 3, 5, quality_min=0.8))
        for _ in range(n):
            idx = rng.integers(5, len(df))
            entry = float(df["open"].iloc[idx])
            exit_ = float(df["close"].iloc[idx])
            dirc = rng.integers(0, 2)
            gross = (exit_ - entry) / entry if dirc == 0 else (entry - exit_) / entry
            rand_pnls.append(DEPOSIT * 0.25 * (gross - 2 * args.commission))
    if rand_pnls:
        ra = np.array(rand_pnls)
        print(f"    n={len(ra):>4} win={(ra>0).mean()*100:>5.1f}% "
              f"net={ra.sum():>+14,.0f} avg={ra.mean():>+10,.0f}")


    # ── G. Вариант «ровно 5 свечей одного цвета» (запрос пользователя) ───────
    # 5 свечей одного цвета -> fade (bull->short, bear->long), вход на open
    # следующей свечи, выход на close следующей свечи (конец следующего дня).
    print("\nG. Вариант 'ровно 5 свечей одного цвета' (live-faithful):")
    sig5: dict[str, list[dict]] = {}
    for t in tickers:
        df = ticker_df.get(t)
        if df is None:
            continue
        classified = ec.classify_candles(df, 0.6, 14, 0.5)
        colors = classified["candle_color"].values
        nlen = len(colors)
        out = []
        i = 0
        while i < nlen:
            c = colors[i]
            if c == "doji":
                i += 1
                continue
            j = i
            while j < nlen and colors[j] == c:
                j += 1
            if j - i >= 5:
                sig_idx = i + 4
                if sig_idx + 1 < nlen:
                    wave = ec.Wave(start_idx=i, end_idx=sig_idx, direction=c,
                                   candle_count=5, df=classified)
                    q = ec.wave_quality_score(wave)["total"]
                    fade = "long" if c == "bear" else "short"
                    out.append({"sig_idx": sig_idx, "fade": fade, "quality": q})
            i = j
        sig5[t] = out

    # raw-статистика
    all_g = []
    for t, lst in sig5.items():
        df = ticker_df[t]
        for s in lst:
            o = float(df["open"].iloc[s["sig_idx"] + 1])
            cl = float(df["close"].iloc[s["sig_idx"] + 1])
            gross = (cl - o) / o if s["fade"] == "long" else (o - cl) / o
            all_g.append({"q": s["quality"], "gross": gross, "win": gross > 0})
    gd = pd.DataFrame(all_g)
    if len(gd):
        print(f"    raw: n={len(gd):>4} win={(gd['win']).mean()*100:>5.1f}% "
              f"gross_mean={gd['gross'].mean()*100:+.3f}% "
              f"gross_med={gd['gross'].median()*100:+.3f}%")
        for lo, hi, lbl in ((0, 0.4, "q<0.4"), (0.4, 0.6, "0.4-0.6"),
                            (0.6, 0.8, "0.6-0.8"), (0.8, 1.01, "q>=0.8")):
            g = gd[(gd["q"] >= lo) & (gd["q"] < hi)]
            if len(g):
                print(f"    {lbl:10}: n={len(g):>4} win={(g['win']).mean()*100:>5.1f}% "
                      f"gross_mean={g['gross'].mean()*100:+.3f}%")

    # мартингейл на L=5
    print("    Мартингейл 25→50→100 на L=5:")
    for qmin in (0.0, 0.4, 0.8):
        equity = DEPOSIT
        peak = equity
        mdd = 0.0
        wins = 0
        cycles = 0
        lost3 = 0
        for t, lst in sig5.items():
            df = ticker_df[t]
            for s in lst:
                if s["quality"] < qmin:
                    continue
                e = equity
                step = 0
                ok = False
                for k in range(1, 4):
                    idx = s["sig_idx"] + k
                    if idx >= len(df):
                        break
                    o = float(df["open"].iloc[idx])
                    cl = float(df["close"].iloc[idx])
                    size = e * min(0.25 * 2 ** step, 1.0)
                    gross = (cl - o) / o if s["fade"] == "long" else (o - cl) / o
                    pnl = size * (gross - 2 * args.commission)
                    e += pnl
                    step += 1
                    if pnl >= 0:
                        ok = True
                        break
                cycles += 1
                wins += 1 if ok else 0
                if step == 3 and not ok:
                    lost3 += 1
                equity = e
                peak = max(peak, equity)
                mdd = max(mdd, peak - equity)
        if cycles:
            print(f"    q>={qmin}: циклов={cycles:>4} win={wins/cycles*100:>5.1f}% "
                  f"3шаг-потерь={lost3:>3} net={equity-DEPOSIT:>+13,.0f} "
                  f"maxDD={mdd/DEPOSIT*100:>5.1f}%")


if __name__ == "__main__":
    main()
