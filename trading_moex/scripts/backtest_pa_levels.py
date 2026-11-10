#!/usr/bin/env python3
"""Бэктест PA-уровней (по промту «Price Action на R/S с анализом ликвидности»).

Для каждого тикера:
  1) ``app.pa_levels.generate_signals`` даёт причинные сигналы на закрытии бара;
  2) вход по open следующего бара; стоп за экстремум паттерна + буфер ATR,
     тейк — ближайшая зона (уже посчитана в сигнале, ≥ rr_min * риск);
  3) внутри бара сначала проверяется стоп (консервативно), затем тейк;
  4) безубыток после ``breakeven_r`` R; трейлинг за последними ``trail_look``
     минимумами/максимумами для лонга/шорта.

Издержки: комиссия + проскальзывание на сторону. Метрики: WinRate, Profit
Factor, max drawdown, средний R, общий net. Печатается таблица сделок.

Без lookahead: сигналы строятся причинно, вход по следующему open.

Usage (from trading_moex/):
    python3 scripts/backtest_pa_levels.py --db data/trader_4h.db --period 1day
    python3 scripts/backtest_pa_levels.py --db data/trader_4h.db --period 4h
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.pa_levels import PALevelParams, generate_signals  # noqa: E402
from app.pa_levels import _atr  # noqa: E402

ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]


def chrono_split(trades: list[dict]) -> tuple[list[dict], list[dict]]:
    """Делит сделки на раннюю/позднюю половины по времени входа (хроно-раздел)."""
    if not trades:
        return [], []
    ordered = sorted(trades, key=lambda t: t["entry_time"])
    mid = len(ordered) // 2
    return ordered[:mid], ordered[mid:]


def random_control_signals(df: pd.DataFrame, n_signals: int, seed: int,
                            rr: float = 2.0, vol_mult: float = 1.5) -> pd.DataFrame:
    """Случайные входы той же частоты, стоп/тейк по ATR (независимый контроль).

    Нужен, чтобы проверить: даёт ли реальная логика уровней edge сверх
    случайного входа с сопоставимой частотой и RRR.
    """
    rng = np.random.default_rng(seed)
    p = PALevelParams()
    atr = _atr(df, p.atr_period).to_numpy(float)
    n = len(df)
    lo_i = max(p.atr_period, 5)
    if n <= lo_i + 1 or n_signals <= 0:
        return pd.DataFrame(columns=["idx", "time", "side", "price", "stop", "target", "reasons"])
    picks = rng.choice(np.arange(lo_i, n - 1), size=min(n_signals, n - lo_i - 1), replace=False)
    rows = []
    for i in sorted(picks.tolist()):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        side = 1 if rng.random() < 0.5 else -1
        price = float(df["close"].iloc[i])
        risk = a * vol_mult
        stop = price - side * risk
        target = price + side * rr * risk
        rows.append({"idx": int(i), "time": df.index[i], "side": side, "price": price,
                     "stop": stop, "target": target, "reasons": ["random"]})
    return pd.DataFrame(rows, columns=["idx", "time", "side", "price", "stop", "target", "reasons"])


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


# LTF → HTF (следующий старший ТФ для фильтра тренда из видео п.1.3).
_HTF_MAP = {"15min": "60min", "30min": "2h", "60min": "4h", "2h": "4h",
            "4h": "1day", "1day": None, "5min": "30min", "1min": "15min"}


def resample_htf(db: str, ticker: str, period: str) -> pd.DataFrame | None:
    """Старший ТФ из БД, если есть; иначе ресемпл LTF в 4x по времени."""
    htf = _HTF_MAP.get(period, None)
    if htf:
        cand = load_df(db, ticker, htf)
        if not cand.empty:
            return cand
    base = load_df(db, ticker, period)
    if base.empty:
        return None
    rule = {"15min": "1h", "30min": "2h", "60min": "4h", "2h": "8h",
            "4h": "1D", "5min": "20min", "1min": "5min"}.get(period)
    if not rule:
        return None
    agg = base.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                   "close": "last", "volume": "sum"}).dropna()
    return agg


def simulate_trades(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    p: PALevelParams,
    commission: float,
    slippage: float,
) -> list[dict]:
    """Прогон управления сделкой по каждому сигналу (вход по следующему open).

    Исполнение:
    * вход по open следующего бара; слип учитывается ОДИН раз на сторону
      (в `cost`), цена входа/выхода — чистые;
    * внутри бара сначала проверяется стоп (консервативно), затем тейк (OCO);
    * безубыток после ``breakeven_r`` R; трейлинг за ``trail_look`` барами;
    * принудительный выход (правило пользователя): если бар закрылся по
      обратную сторону от входа (цена пошла к стопу), не дойдя до цели —
      закрываем по close этого бара (reason="bailout");
    * одна позиция на тикер: новый сигнал на тикере игнорируется, пока
      предыдущая не закрыта (нет наложения/одновременных сделок).
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    idx = df.index
    n = len(df)
    trades = []
    busy_until = -1  # бар, до которого тикер занят (нет наложения позиций)
    for _, s in sorted(signals.iterrows(), key=lambda r: int(r[1]["idx"])):
        i = int(s["idx"])
        entry_bar = i + 1
        if entry_bar >= n or entry_bar <= busy_until:
            continue
        side = int(s["side"])
        entry = o[entry_bar]  # чистая цена входа; слип — в cost
        stop = float(s["stop"])
        target = float(s["target"])
        risk = (entry - stop) if side == 1 else (stop - entry)
        if risk <= 0:
            continue
        be_level = entry + side * p.breakeven_r * risk
        moved_be = False
        exit_price = None
        exit_bar = None
        exit_reason = None
        for j in range(entry_bar, n):
            hi, lo = h[j], l[j]
            # --- проверка стопа (консервативно — первым) ---
            if side == 1 and lo <= stop:
                exit_price, exit_bar, exit_reason = stop, j, "stop"; break
            if side == -1 and hi >= stop:
                exit_price, exit_bar, exit_reason = stop, j, "stop"; break
            # --- тейк ---
            if side == 1 and hi >= target:
                exit_price, exit_bar, exit_reason = target, j, "target"; break
            if side == -1 and lo <= target:
                exit_price, exit_bar, exit_reason = target, j, "target"; break
            # --- принудительный выход: цена закрылась против позиции, не дойдя
            #     до цели (движение к стопу) ---
            if p.bailout_on_drawdown and j > entry_bar:
                if (side == 1 and c[j] < entry) or (side == -1 and c[j] > entry):
                    exit_price, exit_bar, exit_reason = c[j], j, "bailout"; break
            # --- безубыток после breakeven_r ---
            if not moved_be:
                if (side == 1 and hi >= be_level) or (side == -1 and lo <= be_level):
                    stop = entry
                    moved_be = True
            # --- трейлинг за последними trail_look экстремумами ---
            if p.trail_look > 0 and j - entry_bar >= p.trail_look:
                if side == 1:
                    trail = l[j - p.trail_look:j].min() - p.stop_buffer_atr * risk / max(p.rr_min, 1e-9)
                    stop = max(stop, trail)
                else:
                    trail = h[j - p.trail_look:j].max() + p.stop_buffer_atr * risk / max(p.rr_min, 1e-9)
                    stop = min(stop, trail)
        if exit_price is None:
            exit_price, exit_bar, exit_reason = c[-1], n - 1, "eod"
        busy_until = exit_bar  # тикер занят до выхода
        gross = (exit_price - entry) * side
        # слип один раз на сторону (вход + выход); цена входа/выхода чистая
        cost = (entry + exit_price) * commission + (entry + exit_price) * slippage
        net = gross - cost
        trades.append({
            "ticker": s.get("ticker", ""),
            "side": "L" if side == 1 else "S",
            "entry_time": idx[entry_bar],
            "exit_time": idx[exit_bar],
            "entry": round(entry, 4),
            "exit": round(exit_price, 4),
            "stop": round(float(s["stop"]), 4),
            "target": round(float(s["target"]), 4),
            "bars": exit_bar - entry_bar,
            "r_multiple": round(net / risk, 4),
            "pnl": round(net, 2),
            "reason": exit_reason,
            "reasons": "; ".join(s["reasons"]) if isinstance(s.get("reasons"), list) else s.get("reasons", ""),
        })
    return trades


def metrics(trades: list[dict], pct_of: float = 100_000.0) -> dict:
    if not trades:
        return {"trades": 0, "winrate": 0.0, "pf": None, "avg_r": 0.0,
                "max_dd": 0.0, "net": 0.0}
    r = np.array([t["r_multiple"] for t in trades])
    pnl = np.array([t["pnl"] for t in trades])
    wins = r[r > 0]
    losses = r[r < 0]
    gains = float(wins.sum())
    loss = float(-losses.sum())
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    return {
        "trades": len(trades),
        "winrate": round(len(wins) / len(trades) * 100, 1),
        "pf": round(gains / loss, 3) if loss > 0 else None,
        "avg_r": round(float(r.mean()), 3),
        "max_dd": round(abs(float(dd.min())), 2),
        "net": round(float(pnl.sum()), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="1day")
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--direction", type=int, default=0, help="0=оба, 1=только лонг, -1=только шорт")
    parser.add_argument("--min-touches", type=int, default=3)
    parser.add_argument("--vol-mult", type=float, default=1.5)
    parser.add_argument("--rr-min", type=float, default=2.0)
    parser.add_argument("--use-htf", type=int, default=0,
                        help="Фильтр тренда старшего ТФ (видео п.1.3)")
    parser.add_argument("--require-compression", type=int, default=0,
                        help="Триггер сжатия диапазона (видео п.2.4)")
    parser.add_argument("--compress-body-ratio", type=float, default=0.35)
    parser.add_argument("--compress-range-atr", type=float, default=0.6)
    parser.add_argument("--compress-after-return", type=int, default=1,
                        help="Сжатие ищем ПОСЛЕ возврата (последовательность видео)")
    parser.add_argument("--impulse-atr-min", type=float, default=0.0,
                        help="Мин. глубина пробоя в ATR (импульсный); 0 = без порога")
    parser.add_argument("--bailout-on-drawdown", type=int, default=0,
                        help="Принудительный выход при движении к стопу (правило пользователя)")
    parser.add_argument("--chrono", type=int, default=0,
                        help="Печать хроно-разбиения (ранняя/поздняя половины)")
    parser.add_argument("--oos-split", default="",
                        help="Дата YYYY-MM-DD: сделки до = train, от неё = OOS")
    parser.add_argument("--random-seed", type=int, default=-1,
                        help="≥0: контроль случайных входов с этим seed")
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    p = PALevelParams(min_touches=args.min_touches, vol_mult=args.vol_mult,
                      rr_min=args.rr_min, direction=args.direction,
                      use_htf=args.use_htf, require_compression=args.require_compression,
                      compress_body_ratio=args.compress_body_ratio,
                      compress_range_atr=args.compress_range_atr,
                      compress_after_return=args.compress_after_return,
                      impulse_atr_min=args.impulse_atr_min,
                      bailout_on_drawdown=args.bailout_on_drawdown)

    print(f"PA levels | период={args.period} | direction={args.direction} | "
          f"min_touches={args.min_touches} vol_mult={args.vol_mult} rr_min={args.rr_min}")
    print(f"издержки: {args.commission*100:.3f}% комиссия + {args.slippage*100:.3f}% слип /сторону\n")

    all_trades: list[dict] = []
    per_ticker = {}
    for t in tickers:
        df = load_df(args.db, t, args.period)
        if df.empty:
            continue
        htf_df = resample_htf(args.db, t, args.period) if args.use_htf else None
        sig = generate_signals(df, p, htf_df)
        sig["ticker"] = t
        trades = simulate_trades(df, sig, p, args.commission, args.slippage)
        all_trades.extend(trades)
        m = metrics(trades)
        per_ticker[t] = m
        print(f"{t:<5} сделок={m['trades']:>3} win={m['winrate']:>5.1f}% "
              f"PF={str(m['pf']):>6} avgR={m['avg_r']:>+6.2f} "
              f"maxDD={m['max_dd']:>9,.0f} net={m['net']:>+10,.0f}")

    total = metrics(all_trades)
    print(f"\nИТОГО сделок={total['trades']} win={total['winrate']}% PF={total['pf']} "
          f"avgR={total['avg_r']:+.3f} maxDD={total['max_dd']:,.0f} NET={total['net']:+,.0f}")

    chrono = {}
    if args.chrono and all_trades:
        early, late = chrono_split(all_trades)
        for name, part in (("ранняя", early), ("поздняя", late)):
            m = metrics(part)
            chrono[name] = m
            print(f"  хроно {name:<8}: сделок={m['trades']:>3} PF={str(m['pf']):>6} "
                  f"avgR={m['avg_r']:>+6.2f} NET={m['net']:>+9,.0f}")

    random_m = None
    if args.oos_split and all_trades:
        cut = pd.Timestamp(args.oos_split)
        train = [t for t in all_trades if pd.Timestamp(t["entry_time"]) < cut]
        oos = [t for t in all_trades if pd.Timestamp(t["entry_time"]) >= cut]
        for name, part in (("train", train), (f"OOS≥{args.oos_split}", oos)):
            if not part:
                print(f"  {name:<18}: нет сделок")
                continue
            m = metrics(part)
            chrono[name] = m
            print(f"  {name:<18}: сделок={m['trades']:>3} PF={str(m['pf']):>6} "
                  f"avgR={m['avg_r']:>+6.2f} NET={m['net']:>+9,.0f}")

    random_m = None
    if args.random_seed >= 0 and all_trades:
        rand_trades = []
        for t in tickers:
            df = load_df(args.db, t, args.period)
            if df.empty:
                continue
            n_real = sum(1 for tr in all_trades if tr.get("ticker") == t)
            sig = random_control_signals(df, n_real, args.random_seed, rr=args.rr_min,
                                         vol_mult=args.vol_mult)
            if sig.empty:
                continue
            rt = simulate_trades(df, sig, p, args.commission, args.slippage)
            for tr in rt:
                tr["ticker"] = t
            rand_trades.extend(rt)
        random_m = metrics(rand_trades)
        print(f"  контроль random: сделок={random_m['trades']:>3} PF={str(random_m['pf']):>6} "
              f"avgR={random_m['avg_r']:>+6.2f} NET={random_m['net']:>+9,.0f}")

    # таблица сделок (кратко)
    if all_trades:
        df_trades = pd.DataFrame(all_trades)
        print("\nПоследние 20 сделок:")
        cols = ["ticker", "side", "entry_time", "entry", "exit", "r_multiple", "reason", "reasons"]
        print(df_trades[cols].tail(20).to_string(index=False))

    report = {
        "study": "PA-LEVELS-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db": args.db,
        "period": args.period,
        "params": vars(p),
        "costs": {"commission": args.commission, "slippage": args.slippage},
        "per_ticker": per_ticker,
        "total": total,
    }
    if args.run_dir:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        if all_trades:
            pd.DataFrame(all_trades).to_csv(run_dir / "trades.csv.gz",
                                            index=False, compression="gzip")
        print(f"\nАртефакты: {run_dir}")


if __name__ == "__main__":
    main()
