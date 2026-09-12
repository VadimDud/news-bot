#!/usr/bin/env python3
"""MTF + Fibonacci correction (2h) — diagnostic only.

Расширение `backtest_mtf_2h.py`: после 4h-сигнала MTF (strong_body + 2h zone)
вход НЕ сразу, а после завершения коррекции, измеренной по ЗАКРЫТЫМ 2h-барам.
Выход НЕ меняется: close исходного entry_bar+horizon (6) 4h-баров от сигнала.

Ключевая семантика (причинная, без lookahead):
  - сигнал на close 4h-бара i;
  - «исходный» entry_bar = i+1, «исходный» exit_bar = i+1+horizon;
  - коррекция отслеживается по 2h-барам, закрытым к моменту соответствующего
    4h-бара (begin+2h <= 4h-bar time), в окне до исходного exit_bar;
  - вход по open первого 4h-бара после подтверждения коррекции (>= i+1 и < exit_bar);
  - выход по close исходного exit_bar (держание сокращается на ожидание).

Варианты (--mode):
  baseline       — вход сразу (как backtest_mtf_2h)
  fib_382_618    — ждать касания зоны 38.2–61.8% коррекции
  fib_50_618     — зона 50–61.8%
  fib_618_786    — зона 61.8–78.6%
  fib_reversal   — зона 38.2–61.8% + разворотная 2h-свеча по направлению сигнала
  fib_resume     — зона + возврат цены в направлении исходного сигнала
  all            — прогнать все варианты

Прод-код НЕ меняется.

Usage (from trading_moex/):
    python3 scripts/backtest_mtf_fib.py --db data/trader_4h.db --mode all
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
DEPOSIT = 100_000.0
COMMISSION_PCT = 0.05
SLIPPAGE_PCT = 0.05
TOTAL_COST_PCT = 2 * (COMMISSION_PCT + SLIPPAGE_PCT)


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


# ── Fibonacci correction on completed 2h bars ───────────────────────────────

def _swing_levels(c2h: pd.DataFrame) -> tuple[float, float]:
    """Причинный swing low/high по последним 2h-барам (фрактал 2 бара)."""
    highs = c2h["high"].to_numpy(dtype=float)
    lows = c2h["low"].to_numpy(dtype=float)
    n = len(c2h)
    if n < 5:
        return float("nan"), float("nan")
    sh = float(np.max(highs[-40:]))
    sl = float(np.min(lows[-40:]))
    return sl, sh


def fib_zone_state(c2h: pd.DataFrame, side: int, zone: tuple[float, float]) -> tuple[bool, bool]:
    """Касание Fib-зоны коррекции по последнему ЗАКРЫТОМУ 2h-бару.

    Для шорта (side=-1): сигнал bear → ждём коррекцию ВВЕРХ к Fib-уровням от
    последнего импульса вниз (swing high→low); цена в зоне [lo,hi] от retrace.
    Для лонга — зеркально. Возвращает (в_зоне, направление_подтверждено).
    """
    if len(c2h) < 8:
        return False, False
    sl, sh = _swing_levels(c2h)
    if not (sh > sl):
        return False, False
    seg = sh - sl
    last = c2h.iloc[-1]
    lo_f, hi_f = zone
    if side < 0:  # short: коррекция вверх от swing low
        level_lo = sl + lo_f * seg
        level_hi = sl + hi_f * seg
        in_zone = (last["low"] <= level_hi) and (last["high"] >= level_lo)
        # разворот: медвежья свеча (close<open), close в нижней половине
        bearish = last["close"] < last["open"]
        return bool(in_zone), bool(bearish)
    else:  # long: коррекция вниз от swing high
        level_hi = sh - lo_f * seg
        level_lo = sh - hi_f * seg
        in_zone = (last["high"] >= level_lo) and (last["low"] <= level_hi)
        bullish = last["close"] > last["open"]
        return bool(in_zone), bool(bullish)


def _confirm_mode(in_zone: bool, reversal: bool, resume: bool, mode: str) -> bool:
    if mode in ("fib_382_618", "fib_50_618", "fib_618_786"):
        return in_zone
    if mode == "fib_reversal":
        return in_zone and reversal
    if mode == "fib_resume":
        return in_zone and resume
    return in_zone


ZONES = {
    "fib_382_618": (0.382, 0.618),
    "fib_50_618": (0.50, 0.618),
    "fib_618_786": (0.618, 0.786),
    "fib_reversal": (0.382, 0.618),
    "fib_resume": (0.382, 0.618),
}


def honest_trades_fib(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    c2h_df: pd.DataFrame,
    pattern: str,
    ltf_zone: int,
    htf_zone: int,
    horizon: int,
    direction: int,
    mode: str,
    event_mask: pd.Series | None,
) -> list[dict]:
    """Сделки MTF с ожиданием 2h Fibonacci-коррекции (выход неизменный)."""
    ltf = mtf.prepare_ohlc(ltf_df)
    htf = mtf.prepare_ohlc(htf_df)
    c2h = mtf.prepare_ohlc(c2h_df)
    if len(ltf) < max(ltf_zone, 50) + horizon + 5 or len(htf) < htf_zone + 5:
        return []

    sig = mtf.mtf_signal(ltf, htf, pattern=pattern, ltf_zone=ltf_zone,
                         htf_zone=htf_zone, direction=direction, causal_daily=False)
    sig_np = sig.to_numpy(dtype=int)
    opens = ltf["open"].to_numpy(dtype=float)
    closes = ltf["close"].to_numpy(dtype=float)
    ltf_idx = ltf.index
    ev_mask = event_mask.to_numpy(dtype=bool) if event_mask is not None else np.zeros(len(ltf), dtype=bool)
    c2h_idx = c2h.index

    zone = ZONES.get(mode, (0.382, 0.618))
    trades = []
    i = 0
    while i < len(sig_np) - 1:
        if sig_np[i] == 0 or ev_mask[i + 1]:
            i += 1
            continue
        side = int(sig_np[i])
        entry_bar0 = i + 1
        exit_bar0 = min(entry_bar0 + horizon, len(opens) - 1)
        if entry_bar0 >= len(opens) or exit_bar0 <= entry_bar0:
            i += 1
            continue

        if mode == "baseline":
            entry_bar = entry_bar0
        else:
            # ищем подтверждение коррекции на 4h-барах [entry_bar0 .. exit_bar0-1]
            entry_bar = None
            for j in range(entry_bar0, exit_bar0):
                t = ltf_idx[j]
                # 2h-бары, ЗАКРЫТЫЕ к t: begin+2h <= t
                closed2h = c2h_idx + pd.Timedelta(hours=2) <= t
                if not closed2h.any():
                    continue
                window = c2h.loc[closed2h]
                in_zone, reversal = fib_zone_state(window, side, zone)
                # resume (причинно): последний ЗАКРЫТЫЙ 2h-бар уже развернулся
                # в сторону сигнала (для шорта — медвежья 2h-свеча)
                last2h = window.iloc[-1] if len(window) else None
                if last2h is not None:
                    resume = (last2h["close"] < last2h["open"]) if side < 0 else (last2h["close"] > last2h["open"])
                else:
                    resume = False
                if _confirm_mode(in_zone, reversal, resume, mode):
                    entry_bar = j
                    break
            if entry_bar is None:
                # коррекция не подтвердилась — вход пропущен
                i = exit_bar0
                continue

        entry_price = opens[entry_bar]
        exit_price = closes[exit_bar0]
        if side == 1:
            pnl_pct = (exit_price / entry_price - 1.0) * 100.0
        else:
            pnl_pct = (1.0 - exit_price / entry_price) * 100.0
        # MAE/MFE по 4h-барам удержания [entry_bar .. exit_bar0]
        seg_h = ltf["high"].to_numpy(dtype=float)[entry_bar:exit_bar0 + 1]
        seg_l = ltf["low"].to_numpy(dtype=float)[entry_bar:exit_bar0 + 1]
        if side == 1:
            mfe = (seg_h.max() / entry_price - 1.0) * 100.0
            mae = (seg_l.min() / entry_price - 1.0) * 100.0
        else:
            mfe = (1.0 - seg_l.min() / entry_price) * 100.0
            mae = (1.0 - seg_h.max() / entry_price) * 100.0
        trades.append({
            "signal_bar": i,
            "entry_bar": entry_bar,
            "exit_bar": exit_bar0,
            "side": "long" if side == 1 else "short",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "pnl_net_pct": pnl_pct - TOTAL_COST_PCT,
            "bars_held": exit_bar0 - entry_bar,
            "wait_bars": entry_bar - entry_bar0,
            "mae_pct": float(mae),
            "mfe_pct": float(mfe),
            "entry_date": str(ltf_idx[entry_bar].date()),
        })
        i = exit_bar0
    return trades


def summarize(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0, "win_net": 0.0, "pnl_net_pct": 0.0,
                "avg_net": 0.0, "max_dd_pct": 0.0, "avg_wait": 0.0,
                "avg_mae": 0.0, "avg_mfe": 0.0}
    pnls = np.array([t["pnl_net_pct"] for t in trades])
    waits = np.array([t["wait_bars"] for t in trades])
    maes = np.array([t.get("mae_pct", 0.0) for t in trades])
    mfes = np.array([t.get("mfe_pct", 0.0) for t in trades])
    cum = np.cumsum(pnls)
    dd = np.maximum.accumulate(cum) - cum
    return {
        "trades": len(trades),
        "win_net": round(float((pnls > 0).mean()) * 100, 1),
        "pnl_net_pct": round(float(pnls.sum()), 2),
        "avg_net": round(float(pnls.mean()), 2),
        "max_dd_pct": round(float(dd.max()) if len(dd) else 0.0, 2),
        "avg_wait": round(float(waits.mean()), 2),
        "avg_mae": round(float(maes.mean()), 2),
        "avg_mfe": round(float(mfes.mean()), 2),
    }


def signal_hours_mask(ltf_df, allowed_hours):
    if not allowed_hours:
        return None
    ltf = mtf.prepare_ohlc(ltf_df)
    signal_mask = ~ltf.index.to_series().dt.hour.isin(allowed_hours)
    return signal_mask.shift(1, fill_value=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="MTF + 2h Fibonacci correction (diagnostic)")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--pattern", default="strong_body")
    parser.add_argument("--ltf-zone", type=int, default=20)
    parser.add_argument("--htf-zone", type=int, default=15)
    parser.add_argument("--horizon", type=int, default=6)
    parser.add_argument("--direction", type=int, default=-1)
    parser.add_argument("--signal-hours", type=str, default="4,8,12")
    parser.add_argument("--mode", default="all")
    args = parser.parse_args()

    modes = (["baseline", "fib_382_618", "fib_50_618", "fib_618_786",
              "fib_reversal", "fib_resume"] if args.mode == "all" else [args.mode])
    allowed_hours = sorted(set(int(x.strip()) for x in args.signal_hours.split(",") if x.strip())) if args.signal_hours else []

    con = sqlite3.connect(args.db)
    ltf_t = {r[0] for r in con.execute("SELECT DISTINCT ticker FROM candles WHERE period='4h'")}
    htf_t = {r[0] for r in con.execute("SELECT DISTINCT ticker FROM candles WHERE period='2h'")}
    con.close()
    common = sorted(ltf_t & htf_t)
    print(f"=== MTF + 2h Fib correction | pattern={args.pattern} dir={args.direction} "
          f"horizon={args.horizon} cost={TOTAL_COST_PCT:.2f}% ===\n")
    print(f"Tickers ({len(common)}): {', '.join(common)}\n")

    for mode in modes:
        all_tr = []
        n_signals = 0
        n_filled = 0
        for ticker in common:
            ltf = load_df(ticker, args.db, "4h")
            htf = load_df(ticker, args.db, "2h")
            c2h = htf  # коррекция считается по тем же 2h-барам
            if len(ltf) < 60 or len(htf) < 60:
                continue
            em = signal_hours_mask(ltf, allowed_hours)
            tr = honest_trades_fib(ltf, htf, c2h, args.pattern, args.ltf_zone,
                                   args.htf_zone, args.horizon, args.direction, mode, em)
            if mode != "baseline":
                # сколько сигналов было (без коррекции) для оценки доли входов
                base = honest_trades_fib(ltf, htf, c2h, args.pattern, args.ltf_zone,
                                         args.htf_zone, args.horizon, args.direction,
                                         "baseline", em)
                n_signals += len(base)
                n_filled += len(tr)
            all_tr.extend(tr)
        s = summarize(all_tr)
        fill = f" fills={n_filled}/{n_signals} ({n_filled/n_signals*100:.0f}%)" if n_signals else ""
        print(f"[{mode:14}] trades={s['trades']:>3} win_net={s['win_net']:>5.1f}% "
              f"net={s['pnl_net_pct']:>+8.2f}% avg={s['avg_net']:>+6.2f}% "
              f"maxDD={s['max_dd_pct']:>6.2f}% wait={s['avg_wait']:.2f} "
              f"MAE={s['avg_mae']:>+6.2f}% MFE={s['avg_mfe']:>+6.2f}%{fill}")

        # разбивка по половинам периода (устойчивость)
        if all_tr:
            dates = sorted(t["entry_date"] for t in all_tr)
            mid = dates[len(dates) // 2]
            e1 = summarize([t for t in all_tr if t["entry_date"] < mid])
            e2 = summarize([t for t in all_tr if t["entry_date"] >= mid])
            print(f"{'':18}  1st_half: n={e1['trades']:>2} net={e1['pnl_net_pct']:>+7.2f}% | "
                  f"2nd_half: n={e2['trades']:>2} net={e2['pnl_net_pct']:>+7.2f}%")


if __name__ == "__main__":
    main()
