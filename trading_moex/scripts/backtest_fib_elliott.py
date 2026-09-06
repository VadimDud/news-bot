#!/usr/bin/env python3
"""Диагностика Elliott-фильтра для Fib pullback (качество импульса/коррекции).

Идея: теория Эллиотта говорит, что трендовый вход на откате ценен только если
импульс, от которого идёт откат, — «качественная» волна (растяжение, чередование,
доминанта), а коррекция — завершённая структура (A-B-C), а не случайный бар.

Скрипт: для каждой сделки Fib (шорт и лонг, прод-параметры) считает ПРИЧИННЫЕ
(только данные до бара входа) Elliott-фичи импульсной ноги и отката, строит
децили фич против win/avg-R/net и прогоняет гейт-sweep с пересчётом net
(с переносом). Сравнение с baseline (шорт 4h: +22,929 net).

Usage (from trading_moex/):
    python3 scripts/backtest_fib_elliott.py --db data/trader_4h.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "trading_moex"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import backtrader as bt  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app import elliott_candles as ec  # noqa: E402
from app.fib_pullback import _compute_arrays  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

_4H_SHORT = ["T", "NLMK", "MOEX", "LKOH", "CHMF", "TATN", "NVTK", "GAZP"]
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]
DEPOSIT = 100_000.0


def load_df(ticker: str, db: str, period: str) -> pd.DataFrame:
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


def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights_between(d0, d1, wk: bool) -> int:
    c = 0
    cur = d0
    while cur < d1:
        nxt = cur + timedelta(days=1)
        if wk:
            c += 1
        else:
            if nxt.weekday() == 5:
                c += 3
            elif nxt.weekday() < 5:
                c += 1
        cur = nxt
    return c


class _Recorder(FibPullbackStrategy):
    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []
        self._open: dict = {}

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            st = self._last_state
            slv = None
            shv = None
            if st is not None and st.get("idx") is not None:
                i = st["idx"]
                sl = st.get("swing_low")
                sh = st.get("swing_high")
                if sl is not None and i < len(sl) and sl[i] == sl[i]:
                    slv = float(sl[i])
                if sh is not None and i < len(sh) and sh[i] == sh[i]:
                    shv = float(sh[i])
            self._open[key] = (size, entry, entry * size, slv, shv)
        if trade.isclosed:
            size, entry, notional, slv, shv = self._open.pop(
                key, (0.0, 0.0, 0.0, None, None))
            op = bt.num2date(trade.dtopen)
            cl = bt.num2date(trade.dtclose)
            pnl = float(trade.pnlcomm or 0.0)
            self.closed.append({
                "open": op, "close": cl, "entry": entry, "size": size,
                "notional": notional, "pnl": pnl, "swing_low": slv,
                "swing_high": shv, "ticker": key,
            })
        super().notify_trade(trade)


def _base_params(ticker: str, direction: int) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    p["direction"] = direction
    p["flat_mode"] = 0
    return p


def run_ticker(ticker: str, df: pd.DataFrame, db: str, period: str,
               direction: int) -> list[dict]:
    p = _base_params(ticker, direction)
    cb = _setup_cerebro(_Recorder, p, DEPOSIT, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    return strat.closed


def _find_leg(df: pd.DataFrame, idx: int, swing_low: float | None,
              swing_high: float | None, direction: int, swing_bars: int) -> dict:
    """Найти импульсную ногу и откат (причинно) для бара входа idx.

    Импульсная нога: от последнего подтверждённого swing-экстремума (за
    swing_bars баров до idx) до другого. Поиск по совпадению значений в
    low/high сериях (причинный, только прошлые бары <= idx).
    """
    lo = df["low"].values
    hi = df["high"].values
    cl = df["close"].values
    op = df["open"].values
    start = max(0, idx - 600)

    # индекс подтверждённого swing (значение найдено в окне, сдвиг >= swing_bars)
    sl_idx = None
    sh_idx = None
    if swing_low is not None:
        cands = [k for k in range(start, idx - swing_bars + 1)
                 if lo[k] == swing_low]
        if cands:
            sl_idx = cands[-1]
    if swing_high is not None:
        cands = [k for k in range(start, idx - swing_bars + 1)
                 if hi[k] == swing_high]
        if cands:
            sh_idx = cands[-1]

    out: dict = {"imp_bars": 0, "imp_pct": 0.0, "imp_ratio": np.nan,
                 "imp_body_atr": np.nan, "dominance": np.nan, "alternation": 0,
                 "retr_bars": 0, "retr_runs": 0, "retr_depth": np.nan,
                 "leg_ok": 0}
    if sl_idx is None or sh_idx is None:
        return out
    leg_start = min(sl_idx, sh_idx)
    leg_end = max(sl_idx, sh_idx)
    if leg_end <= leg_start:
        return out
    out["leg_ok"] = 1

    seg = abs(hi[leg_end] - lo[leg_start])
    if lo[leg_start] > 0:
        out["imp_pct"] = seg / lo[leg_start] * 100.0
    out["imp_bars"] = leg_end - leg_start

    # характеристики ноги: импульсность тел, доминанта, чередование
    bodies = np.abs(cl[leg_start + 1:leg_end + 1] - op[leg_start + 1:leg_end + 1])
    rngs = np.abs(hi[leg_start + 1:leg_end + 1] - lo[leg_start + 1:leg_end + 1])
    if len(bodies):
        ratios = bodies / np.where(rngs > 0, rngs, np.nan)
        out["imp_ratio"] = float(np.nanmean(ratios))
        # ATR-прокси по диапазону бара
        atr_px = float(np.nanmean(rngs))
        if atr_px > 0:
            out["imp_body_atr"] = float(np.nanmean(bodies) / atr_px)
        net = hi[leg_end] - lo[leg_start] if sl_idx < sh_idx else hi[leg_start] - lo[leg_end]
        path = float(np.nansum(np.abs(cl[leg_start:leg_end + 1] -
                                       cl[leg_start - 1:leg_end])))
        out["dominance"] = float(net / path) if path > 0 else 0.0
    # чередование: число внутренних разворотов (серии одноцветных)
    colors = np.sign(np.diff(cl[leg_start:leg_end + 1]))
    runs = 0
    prev = 0
    for c in colors:
        if c != 0 and c != prev:
            runs += 1
            prev = c
    out["alternation"] = runs

    # откат: от экстремума ноги до бара входа
    ext_idx = leg_end
    out["retr_bars"] = max(idx - ext_idx, 0)
    if out["retr_bars"] > 0:
        retr_cl = cl[ext_idx:idx + 1]
        retr_sign = np.sign(np.diff(retr_cl))
        runs = 0
        prev = 0
        for c in retr_sign:
            if c != 0 and c != prev:
                runs += 1
                prev = c
        out["retr_runs"] = runs
        # глубина отката: (цена - swing_low)/seg (для шорта) или зеркально
        if sl_idx < sh_idx:  # нога вверх (импульс лонга)
            depth = (hi[leg_end] - cl[idx]) / seg if seg > 0 else np.nan
        else:  # нога вниз (импульс шорта)
            depth = (cl[idx] - lo[leg_end]) / seg if seg > 0 else np.nan
        out["retr_depth"] = float(depth) if depth == depth else np.nan
    return out


def annotate_trades(trades: list[dict], df: pd.DataFrame, ticker: str,
                    direction: int) -> list[dict]:
    """Привязать сделки к бару входа и посчитать Elliott-фичи."""
    p = _base_params(ticker, direction)
    swing_bars = int(p.get("swing_bars", 10))
    out = []
    for tr in trades:
        ts = pd.Timestamp(tr["open"])
        pos = df.index.get_indexer([ts], method="nearest")[0]
        if pos < 0:
            continue
        feat = _find_leg(df, pos, tr.get("swing_low"), tr.get("swing_high"),
                         direction, swing_bars)
        out.append({**tr, "idx": pos, **feat})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Elliott-фильтр для Fib")
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    args = parser.parse_args()
    db = args.db

    # Шорт 4h (базлайн +22,929)
    print("Сбор сделок: Fib short 4h ...")
    short_trades: list[dict] = []
    for t in _4H_SHORT:
        df = load_df(t, db, "4h")
        if df.empty:
            continue
        wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
        trs = run_ticker(t, df, db, "4h", -1)
        for tr in trs:
            tr["wk"] = wk
            tr["carry"] = _carry_rate(tr["notional"]) * _nights_between(
                tr["open"].date(), tr["close"].date(), wk)
        short_trades.extend(annotate_trades(trs, df, t, -1))

    print("Сбор сделок: Fib long 4h ...")
    long_trades: list[dict] = []
    for t in ALL_TICKERS:
        df = load_df(t, db, "4h")
        if df.empty:
            continue
        wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
        trs = run_ticker(t, df, db, "4h", 1)
        for tr in trs:
            tr["wk"] = wk
            tr["carry"] = _carry_rate(tr["notional"]) * _nights_between(
                tr["open"].date(), tr["close"].date(), wk)
        long_trades.extend(annotate_trades(trs, df, t, 1))

    def _report(name: str, trades: list[dict]) -> pd.DataFrame:
        d = pd.DataFrame(trades)
        g = d["pnl"].sum()
        c = d["carry"].sum()
        n = len(d)
        w = (d["pnl"] > 0).mean() * 100 if n else 0
        print(f"\n{name}: n={n} win={w:.1f}% gross={g:+,.0f} carry={c:,.0f} "
              f"net={g-c:+,.0f}")
        return d

    sd = _report("BASELINE short 4h (без фильтра)", short_trades)
    ld = _report("BASELINE long 4h (без фильтра)", long_trades)

    # Децили фич
    feats = ["imp_pct", "imp_ratio", "imp_body_atr", "dominance", "alternation",
             "retr_bars", "retr_runs", "retr_depth"]
    for name, d, lbl in (("SHORT", sd, "short"), ("LONG", ld, "long")):
        print(f"\n=== Децили фич — {name} ===")
        for f in feats:
            sub = d.dropna(subset=[f])
            if len(sub) < 20:
                continue
            sub = sub.copy()
            sub["bin"] = pd.qcut(sub[f], 5, labels=False, duplicates="drop")
            line = f"  {f:14}: "
            for b, grp in sub.groupby("bin"):
                line += (f"[{b}:n{len(grp)} w{(grp['pnl']>0).mean()*100:.0f}% "
                         f"g{grp['pnl'].mean():+.0f}] ")
            print(line)

    # Гейт-sweep по качеству импульса и завершённости коррекции
    print("\n=== Гейт-sweep (net с переносом) ===")
    print(f"  {'гейт':38} {'short net':>12} {'short n':>8} {'long net':>12} {'long n':>8}")

    def _gated(d: pd.DataFrame, cond: pd.Series) -> dict:
        sub = d[cond]
        if sub.empty:
            return {"net": 0.0, "n": 0, "win": 0.0}
        return {"net": float(sub["pnl"].sum() - sub["carry"].sum()),
                "n": len(sub),
                "win": float((sub["pnl"] > 0).mean() * 100)}

    gates = {
        "imp_pct >= 5%": lambda d: d["imp_pct"] >= 5,
        "imp_pct >= 10%": lambda d: d["imp_pct"] >= 10,
        "imp_ratio >= 0.6": lambda d: d["imp_ratio"] >= 0.6,
        "imp_ratio >= 0.8": lambda d: d["imp_ratio"] >= 0.8,
        "dominance >= 0.3": lambda d: d["dominance"] >= 0.3,
        "dominance >= 0.5": lambda d: d["dominance"] >= 0.5,
        "alternation >= 3": lambda d: d["alternation"] >= 3,
        "alternation >= 5": lambda d: d["alternation"] >= 5,
        "retr_bars >= 3": lambda d: d["retr_bars"] >= 3,
        "retr_bars >= 5": lambda d: d["retr_bars"] >= 5,
        "retr_runs >= 2": lambda d: d["retr_runs"] >= 2,
        "retr_runs >= 3": lambda d: d["retr_runs"] >= 3,
        "retr_depth 0.3-0.8": lambda d: (d["retr_depth"] >= 0.3) & (d["retr_depth"] <= 0.8),
        "imp_ratio>=0.6 & alt>=3": lambda d: (d["imp_ratio"] >= 0.6) & (d["alternation"] >= 3),
        "imp_ratio>=0.6 & retr_bars>=3": lambda d: (d["imp_ratio"] >= 0.6) & (d["retr_bars"] >= 3),
        "imp_pct>=5 & dominance>=0.3": lambda d: (d["imp_pct"] >= 5) & (d["dominance"] >= 0.3),
    }
    for gname, cond in gates.items():
        gs = _gated(sd, cond(sd))
        gl = _gated(ld, cond(ld))
        print(f"  {gname:38} {gs['net']:>+12,.0f} {gs['n']:>8} "
              f"{gl['net']:>+12,.0f} {gl['n']:>8}")

    print("\nBaseline short: n=154 net=+22,929 | baseline long: n=91 net=-86,600")


if __name__ == "__main__":
    main()
