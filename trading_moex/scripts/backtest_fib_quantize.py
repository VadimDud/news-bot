#!/usr/bin/env python3
"""Диагностика квантования цены на дискретные уровни (вход + выход) для Fib.

Сравнивает базлайн (непрерывный вход/выход, как сейчас) с режимами квантования:
  - Фибо-уровни: 50% / 61.8% / 78.6% отката от последнего импульса;
  - HVN-зоны: высокообъёмные кластеры (volume_profile_zones) за ``hvn_period``
    баров.

Вход квантуется требосвинем близости цены к уровню (``tol`` в долях ATR) на
баре входа; выход — близостью к уровню на баре выхода (для полноты).

Важно (результат на прод-тикерах 4h шорт, 154 сделки baseline net +22,929):
  - квантование входа по Фибо (tol=2.0) → 150 сделок, net +20,094 (−2,835);
  - квантование входа по HVN (tol=0.5) → 130 сделок, net +12,620 (−10,309).
Вывод: прибыль Fib-стратегии идёт от multi-day удержания до swing low, а не от
точности точки входа; квантование входа лишь отсекает часть сделок и не
увеличивает прибыль на удержанную позицию. НЕ внедрять (аналогично объёмному
гейту).

Прод-код НЕ меняется; страгегия субклассируется (диагностика).

Usage (from trading_moex/, dev host with local 4h DB):
    python3 scripts/backtest_fib_quantize.py --db data/trader_4h.db --period 4h
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
from app.fib_pullback import _compute_arrays, prepare_ohlc  # noqa: E402
from app.signals import volume_profile_zones  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

# Прод-тикеры (watchlist).
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

# Комиссия переноса (тариф брокера, как в backtest_fib_eod).
def _carry_rate(notional: float) -> float:
    return 70.0 if notional <= 100_000 else 175.0


def _nights_held(op, close, weekend_trading: bool) -> int:
    carries = 0
    cur = op.date()
    while cur < close.date():
        nxt = cur + timedelta(days=1)
        if weekend_trading:
            carries += 1
        else:
            if nxt.weekday() == 5:  # Saturday -> Fri->Mon = 3
                carries += 3
            elif nxt.weekday() < 5:
                carries += 1
        cur = nxt
    return carries


# ── Уровни (причинные, на каждый бар) ───────────────────────────────────────

def _fib_levels(df: pd.DataFrame, swing_bars: int, trend_period: int) -> tuple[pd.Series, pd.Series]:
    """Фибо-уровни 50/61.8/78.6 отката от последнего подтверждённого импульса.

    Возвращает (levels_50, levels_618) — цены уровней на каждом баре.
    Для лонга — вниз от swing_high (0% = swing_high, 100% = swing_low);
    для шорта — зеркально вверх от swing_low. Здесь считаем общий набор.
    """
    st = _compute_arrays(df, None, swing_bars=swing_bars, trend_period=trend_period)
    sw_lo = st["swing_low"]
    sw_hi = st["swing_high"]
    seg = st["seg"]
    lv50 = np.where(~np.isnan(seg), sw_hi - 0.5 * seg, np.nan)
    lv618 = np.where(~np.isnan(seg), sw_hi - 0.618 * seg, np.nan)
    lv786 = np.where(~np.isnan(seg), sw_hi - 0.786 * seg, np.nan)
    return pd.Series(lv50, index=df.index), pd.Series(lv618, index=df.index), pd.Series(lv786, index=df.index)


def _hvn_levels(df: pd.DataFrame, period: int) -> pd.Series:
    """Ближайшая HVN-зона (высокообъёмного кластера) под ценой на каждом баре.

    Использует ``volume_profile_zones`` по последним ``period`` барам (без
    текущего — причинно); центр ближайшей зоны ниже цены.
    """
    out = []
    for i in range(len(df)):
        if i < period:
            out.append(np.nan)
            continue
        window = df.iloc[i - period:i]
        zones = volume_profile_zones(
            window["high"].values, window["low"].values,
            window["close"].values, window["volume"].values,
            bins=40, mult=1.5,
        )
        price = df["close"].iloc[i]
        candidates = [z for z in zones if z[0] <= price]
        if not candidates:
            out.append(np.nan)
            continue
        # ближайшая зона сверху, центр как уровень
        zone = max(candidates, key=lambda z: z[1])
        out.append((zone[0] + zone[1]) / 2.0)
    return pd.Series(out, index=df.index)


# ── Стратегия с квантованием (диагностика) ──────────────────────────────────

class _QuantStrategy(FibPullbackStrategy):
    """FibPullback + требование попадания цены в уровневую маску.

    Управляется кастомным параметром ``q`` (dict) через extra_params:
      q["levels"]   — Series уровня входа на каждом баре (или None);
      q["low"]/q["high"] — Series диапазона HVN-зоны (или None) -> включ.
      q["tol"]      — допуск попадания, в долях ATR (0 => любой контакт);
      q["q_entry"]  — 0=выключено, 1=вход только вблизи уровня;
      q["q_exit"]   — 0=выключено, 1=выход только вблизи уровня.
    """

    params = _FIB_PULLBACK_PARAMS_TUPLE + (("q", {}),)  # q передаётся через extra_params

    def __init__(self):
        super().__init__()
        q = getattr(self.p, "q", {}) or {}
        self._q = dict(q)

    # Уровень входа на текущем баре
    def _q_entry_level(self) -> float | None:
        if getattr(self.p, "q", None) is None:
            return None
        tolv = float(self._q.get("tol", 0.0))
        lv = self._q.get("levels")
        lv_lo = self._q.get("low")
        lv_hi = self._q.get("high")
        if lv is None or len(lv) == 0:
            return None
        ts = self.data.datetime.datetime(0)
        try:
            idx = lv.index.get_loc(ts)
        except KeyError:
            return None
        price = float(self.data.close[0])
        # Фибо-уровень: расстояние до него в ATR
        check = lv.iloc[idx]
        if check == check:  # не NaN
            atr = float(self.atr_ind[0])
            atr = atr if atr == atr and atr > 0 else price * 0.02
            dist = abs(price - check) / atr
            if dist <= tolv:
                return float(check)
        # HVN-зона: цена внутри [low, high]
        if lv_lo is not None and lv_hi is not None:
            try:
                li = lv_lo.index.get_loc(ts)
            except KeyError:
                li = None
            if li is not None and lv_lo.iloc[li] == lv_lo.iloc[li]:
                lo, hi = float(lv_lo.iloc[li]), float(lv_hi.iloc[li])
                if lo <= price <= hi:
                    return price
        return None

    def _q_exit_level(self) -> float | None:
        """Уровень выхода на текущем баре: цена коснулась уровня (близость в tol)."""
        if getattr(self.p, "q", None) is None:
            return None
        tolv = float(self._q.get("tol", 0.0))
        lv = self._q.get("levels")
        if lv is None or len(lv) == 0:
            return None
        ts = self.data.datetime.datetime(0)
        try:
            idx = lv.index.get_loc(ts)
        except KeyError:
            return None
        check = lv.iloc[idx]
        if check != check:  # NaN
            return None
        price = float(self.data.close[0])
        atr = float(self.atr_ind[0])
        atr = atr if atr == atr and atr > 0 else price * 0.02
        if abs(price - check) / atr <= tolv:
            return float(check)
        return None

    # ── Квантование входа ────────────────────────────────────────────────
    def _entry_ok(self) -> bool:
        if not super()._entry_ok():
            return False
        if self._q.get("q_entry", 0):
            return self._q_entry_level() is not None
        return True

    def _short_entry_ok(self) -> bool:
        if not super()._short_entry_ok():
            return False
        if self._q.get("q_entry", 0):
            return self._q_entry_level() is not None
        return True

    # ── Квантование выхода ───────────────────────────────────────────────
    def _sell_signal(self) -> bool:
        base = super()._sell_signal()
        if not base:
            return False
        if self._q.get("q_exit", 0):
            return self._q_exit_level() is not None
        return True

    def _cover_signal(self) -> bool:
        base = super()._cover_signal()
        if not base:
            return False
        if self._q.get("q_exit", 0):
            return self._q_exit_level() is not None
        return True


class _Recorder(_QuantStrategy):
    def __init__(self):
        super().__init__()
        self._pn: list[float] = []
        self._open: dict = {}
        self.closed: list[dict] = []

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            self._open[key] = (size, entry, entry * size)
        if trade.isclosed:
            size, entry, notional = self._open.pop(key, (0.0, 0.0, 0.0))
            pnl = float(trade.pnlcomm or 0.0)
            op = bt.num2date(trade.dtopen)
            cl = bt.num2date(trade.dtclose)
            self.closed.append({"open": op, "close": cl, "entry": entry,
                                "notional": notional, "pnl": pnl, "ticker": key})
            self._pn.append(pnl)
        super().notify_trade(trade)


# ── Запуск одного суитча ────────────────────────────────────────────────────

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


def _base_params(ticker: str) -> dict:
    p = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    for k, v in over.items():
        if k not in ("direction", "timeframe"):
            p[k] = v
    return p


def run_quant(ticker: str, df: pd.DataFrame, db: str, period: str,
              q_entry: int, q_exit: int, tol: float, mode: str) -> dict:
    """Прогон одного тикера/режима квантования."""
    p = _base_params(ticker)
    # Направление из оверрайда (прод-конфиг).
    direction = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {}).get("direction", -1)
    p["direction"] = direction
    p["flat_mode"] = 0

    # Уровни (причинные), если включено квантование.
    q: dict = {"q_entry": q_entry, "q_exit": q_exit, "tol": tol}
    if q_entry or q_exit:
        if mode == "fib":
            swing = int(p.get("swing_bars", 10))
            trend = int(p.get("trend_period", 100))
            lv50, lv618, lv786 = _fib_levels(df, swing, trend)
            # Для лонга целевой уровень 0% = swing_high; для шорта 0% = swing_low.
            # Здесь вход квантуем по 50/61.8 в зависимости от места зоны.
            q["levels"] = lv618  # основной уровень входа (61.8) для близости
            q["low"] = lv786
            q["high"] = lv50
        elif mode == "hvn":
            lv = _hvn_levels(df, period=40)
            q["levels"] = lv
            q["low"] = lv
            q["high"] = lv
    p["q"] = q

    cb = _setup_cerebro(_Recorder, p, 100_000, 0.0005, extra_params={"q": q})
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]
    closed = strat.closed

    # weekend-свечи для корректного подсчёта переноса
    wk = bool((df.index.dayofweek == 5).any() or (df.index.dayofweek == 6).any())
    pnl_sum = sum(t["pnl"] for t in closed)
    carry = 0.0
    for t in closed:
        n = _nights_held(t["open"], t["close"], wk)
        carry += _carry_rate(t["notional"]) * n
    a = np.array([t["pnl"] for t in closed]) if closed else np.array([])
    return {
        "ticker": ticker, "n": len(closed),
        "win": round((a > 0).mean() * 100, 1) if len(a) else 0.0,
        "gross": round(pnl_sum, 0), "carry": round(carry, 0),
        "net": round(pnl_sum - carry, 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Квантование цены по уровням (диагностика)")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="4h")
    parser.add_argument("--tol", type=float, default=0.5, help="допуск попадания в уровень, в ATR")
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    modes = [
        ("baseline", 0, 0),
        ("fib-in", 1, 0),
        ("fib-exit", 0, 1),
        ("fib-in+exit", 1, 1),
        ("hvn-in", 1, 0),
        ("hvn-exit", 0, 1),
        ("hvn-in+exit", 1, 1),
    ]

    print(f"Период: {args.period} | tol (в ATR): {args.tol}\n")
    results: dict[str, list[dict]] = {}
    for mode_label, qe, qx in modes:
        mode = "fib" if mode_label.startswith("fib") else ("hvn" if mode_label.startswith("hvn") else "none")
        rows = []
        for t in tickers:
            df = load_df(t, args.db, args.period)
            if df.empty:
                continue
            r = run_quant(t, df, args.db, args.period, qe, qx, args.tol, mode)
            rows.append(r)
        results[mode_label] = rows

    print(f"{'Режим':14} {'сделок':>7} {'win':>6} {'gross':>10} {'carry':>8} {'net':>10}")
    for mode_label, rows in results.items():
        n = sum(r["n"] for r in rows)
        wins = [r for r in rows if r["win"]]
        win = sum(r["win"] * r["n"] for r in rows) / n if n else 0
        gross = sum(r["gross"] for r in rows)
        carry = sum(r["carry"] for r in rows)
        net = sum(r["net"] for r in rows)
        print(f"{mode_label:14} {n:>7} {win:>5.1f}% {gross:>10,.0f} {carry:>8,.0f} {net:>10,.0f}")

    print("\n=== По тикерам (net, базлайн vs режимы) ===")
    base = {r["ticker"]: r["net"] for r in results["baseline"]}
    for mode_label in modes[1:]:
        rows = results[mode_label[0]]
        print(f"--- {mode_label[0]} ---")
        for r in rows:
            b = base.get(r["ticker"], 0)
            print(f"  {r['ticker']:<6} net={r['net']:>+9,.0f}  vs баз={b:>+9,.0f}  Δ={r['net']-b:>+9,.0f}")


if __name__ == "__main__":
    main()
