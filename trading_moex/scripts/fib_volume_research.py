#!/usr/bin/env python3
"""Диагностика влияния объёма на прибыльность Fib-сигналов (длин и шортов).

Для каждого исторического Fib-setup (long + short, все тикеры, 4h + 1day)
снимается снимок объёмных фич СТРОГО на баре сигнала/входа (без заглядывания
вперёд — только данные <= бара подтверждения) и сопоставляется с итогом сделки
(win/loss, R-мультипл, pnl %, срок удержания, причина выхода TP/SL).

Вывод:
  - таблицы децилей по каждой фиче -> win-rate, avg R, expectancy, count;
  - корреляционная матрица (Pearson + Spearman) фич против R-мультипла;
  - прямое сравнение: низкий vs высокий объём, доминанта быков vs медведей,
    объёмный всплеск vs тихий вход.

Usage (из trading_moex/):
    python3 scripts/fib_volume_research.py --db data/trader_4h.db --period 4h
    python3 scripts/fib_volume_research.py --db data/trader.db --period 1day
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

import backtrader as bt  # noqa: E402

from app.backtest import _setup_cerebro  # noqa: E402
from app.strategies import (  # noqa: E402
    FibPullbackStrategy,
    TICKER_OVERRIDES,
    _FIB_PULLBACK_PARAMS_TUPLE,
)

# Прод-тикеры (watchlist). 4h-шорты и 1day-лонги — по оверрайдам.
ALL_TICKERS = ["SBER", "LKOH", "GAZP", "TATN", "NVTK", "CHMF", "NLMK", "MOEX", "T", "MTSS"]

# Периоды анализа: параллельный 4h (контейнер) и 1day (хост).
PERIODS = ["4h", "1day"]

_VOL_WIN = 20  # период SMA объёма / окно z-score
_HVN_BINS = 40


# ── Загрузка свечей ───────────────────────────────────────────────────────────

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


# ── Объёмные фичи (векторные, причинные) ──────────────────────────────────────

def _volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """Причинные объёмные фичи на каждом баре (только данные <= текущего бара).

    Возвращает DataFrame с теми же индексами: abs_vol, vol_rel, vol_zscore,
    vol_trend, conf_vol_rel, bull_bear_in, up_down_vol, vol_hvn_dist,
    vol_hvn_dist_below, vol_exp_dir.
    """
    v = df["volume"].astype(float)
    vol_sma = v.rolling(_VOL_WIN, min_periods=5).mean()
    vol_std = v.rolling(_VOL_WIN, min_periods=5).std().replace(0, np.nan)

    out = pd.DataFrame(index=df.index)
    out["abs_vol"] = v
    out["vol_rel"] = v / vol_sma  # относительный объём
    out["vol_zscore"] = (v - vol_sma) / vol_std  # всплеск по волатильности объёма
    # тренд объёма: наклон EMA(5) объёма
    out["vol_trend"] = v.ewm(span=5, adjust=False).mean().diff()

    # Объём свечи-подтверждения — это объём «входа»: отношение к среднему.
    out["conf_vol_rel"] = v / vol_sma

    # Доля быков на баре: закрытие ближе к high (0..1). <0.5 — медведи.
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    out["bull_bear_in"] = ((df["close"] - df["low"]) / rng).fillna(0.5)

    # Баланс объёма: OBV-подобный импульс — суммарный объём растущих vs падающих
    # свечей за окно. >0 — объём концентрируется в восходящих барах (быки).
    up = df["close"].diff()
    up_vol = np.where(up > 0, v, 0.0)
    down_vol = np.where(up < 0, v, 0.0)
    obv = pd.Series(up_vol, index=df.index).rolling(_VOL_WIN, min_periods=5).sum() - \
        pd.Series(down_vol, index=df.index).rolling(_VOL_WIN, min_periods=5).sum()
    out["up_down_vol"] = obv

    # Расширение объёма в направлении сделки. Заполним ниже (знает direction).
    out["vol_exp_dir"] = np.nan

    # Ближайший высокообъёмный узел (HVN) под ценой — расстояние до него (в ATR).
    # Используем простой объёмный профиль (типичная цена, bins=40, mult=1.5).
    from app.signals import volume_profile_levels, volume_profile_zones

    atr = (df["high"] - df["low"]).rolling(14).mean().replace(0, np.nan)
    hvn_below = []
    hvn_above = []
    for i in range(len(df)):
        if i < _VOL_WIN:
            hvn_below.append(np.nan)
            hvn_above.append(np.nan)
            continue
        window = df.iloc[max(0, i - _VOL_WIN):i]  # без текущего бара (<<<)
        highs = window["high"].values
        lows = window["low"].values
        closes = window["close"].values
        vols = window["volume"].values
        price = df["close"].iloc[i]
        sup, res = volume_profile_levels(highs, lows, closes, vols, price,
                                         bins=_HVN_BINS, mult=1.5)
        a = atr.iloc[i]
        a = a if a == a and a > 0 else np.nan
        hvn_below.append((price - sup) / a if (sup is not None and a == a and a > 0) else np.nan)
        hvn_above.append((res - price) / a if (res is not None and a == a and a > 0) else np.nan)

    out["vol_hvn_dist_below"] = hvn_below
    out["vol_hvn_dist_above"] = hvn_above
    # Общая «объёмо-структура»: ближайший узел — какой ближе (отрицательно, если
    # ближе сопротивление сверху -> цена у объёмной «крыши»).
    out["vol_hvn_dist"] = out["vol_hvn_dist_below"].combine_first(out["vol_hvn_dist_above"])
    return out


# ── Стратегия-рекордер ────────────────────────────────────────────────────────

class _ResearchRecorder(FibPullbackStrategy):
    """Полный вывод сделки с привязкой к бару входа (для сопоставления с объёмом)."""

    def __init__(self):
        super().__init__()
        self.closed: list[dict] = []
        self._open: dict = {}
        self._entry_stop: dict = {}

    def notify_trade(self, trade):
        key = getattr(trade.data, "_name", None) or str(id(trade.data))
        if trade.justopened:
            size = abs(float(trade.size))
            entry = float(trade.price) if trade.price else 0.0
            self._open[key] = (size, entry, entry * size)
            st = self._last_state
            i = st.get("idx", len(self._last_state.get("swing_low", [])) - 1) if st else 0
            stop_dist = 0.0
            if st is not None:
                price = float(self.data.close[0])
                if self.position.size < 0:  # шорт: стоп = swing high (структурный)
                    sh = st.get("swing_high")
                    if sh is not None and i < len(sh):
                        v = float(sh[i])
                        if v == v and v > price:
                            stop_dist = v - price
                elif self.position.size > 0:  # лонг: стоп = swing low
                    sl = st.get("swing_low")
                    if sl is not None and i < len(sl):
                        v = float(sl[i])
                        if v == v and 0 < v < price:
                            stop_dist = price - v
            # Прокси риска на 1R: либо структурный стоп, либо ATR*mult.
            stop_dist = stop_dist if stop_dist > price * 0.002 else super()._stop_distance()
            self._entry_stop[key] = stop_dist

        if trade.isclosed:
            size, entry, notional = self._open.pop(key, (0.0, 0.0, 0.0))
            op = bt.num2date(trade.dtopen)
            cl = bt.num2date(trade.dtclose)
            pnl = float(trade.pnlcomm or 0.0)
            stop_dist = self._entry_stop.pop(key, 0.0)
            # Шорт: pnl>0 => прибыль (цена упала к tp), pnl<0 => убыток (стоп).
            reason = "tp" if pnl > 0 else "sl"
            self.closed.append({
                "open": op, "close": cl, "entry": entry, "size": size,
                "notional": notional, "pnl": pnl, "spec_pnl": pnl, "ticker": key,
                "reason": reason, "stop_dist": stop_dist,
            })
        super().notify_trade(trade)


def run_trades(ticker: str, df: pd.DataFrame, db: str, period: str, direction: int) -> list[dict]:
    """Прогон одного направления: вернуть закрытые сделки (без объёмных фич).

    Параметры берутся из продовского ``TICKER_OVERRIDES`` (тот же рецепт, что
    использует live-сканер и прод-бэктест) — чтобы анализ отражал реальные
    сигналы, а не дефолт диагностики.
    """
    base_params = dict((k, v) for k, v in _FIB_PULLBACK_PARAMS_TUPLE)
    over = TICKER_OVERRIDES.get(("fib_pullback", ticker.upper()), {})
    params = {**base_params}
    if over:
        for k, v in over.items():
            if k not in ("direction", "timeframe"):
                params[k] = v
    # Базовые параметры из прод-бэктеста, если перекрытие не задало их явно.
    params.setdefault("confluence_min", 1)
    params.setdefault("rsi_oversold", 40.0)
    params.setdefault("rsi_overbought", 80.0)
    params.setdefault("trend_period", 100)
    params.setdefault("swing_bars", 10)
    params.setdefault("min_rr", 1.0)
    params.setdefault("fib_in_low", 0.50)
    params.setdefault("fib_in_high", 0.618)
    # Явно фиксируем направление (лонг/шорт) — независимо от оверрайда.
    params["direction"] = direction
    params["flat_mode"] = 0  # только удержание — фокус на чистом edge сигнала

    cb = _setup_cerebro(_ResearchRecorder, params, 100_000, 0.0005)
    feed = bt.feeds.PandasData(dataname=df)
    feed._name = ticker
    cb.adddata(feed)
    strat = cb.run(runonce=False)[0]

    # Объёмные фичи на каждого бара (причинные) + привязка к сделкам.
    vfeat = _volume_features(df)
    trades = []
    for tr in strat.closed:
        entry_ts = pd.Timestamp(tr["open"]).tz_localize(None)
        # Ближайший бар <= времени входа (вход исполняется в баре входа).
        pos_idx = vfeat.index.get_indexer([entry_ts], method="nearest")[0]
        if pos_idx < 0:
            continue
        f = vfeat.iloc[pos_idx]
        # R-мультипл = pnl / риск-на-сделку (риск = stop_dist * size).
        risk = tr.get("stop_dist", 0.0) * max(abs(tr.get("size", 0.0)), 1e-9)
        r_mult = (tr["pnl"] / risk) if risk > 0 else 0.0
        trades.append({
            "ticker": ticker, "period": period, "direction": direction,
            "entry": tr["entry"], "exit_reason": tr["reason"],
            "open": tr["open"], "close": tr["close"],
            "pnl": tr["pnl"], "r_mult": r_mult,
            "days": (tr["close"].date() - tr["open"].date()).days,
            **{k: (float(f[k]) if f[k] == f[k] else np.nan) for k in f.index},
        })
    return trades


# ── Отчёт ─────────────────────────────────────────────────────────────────────

def _decile_table(trades: list[dict], feat: str) -> list[dict]:
    """Разбивка по децилям фичи: win-rate, avg R, expectancy, count."""
    rows = []
    vals = np.array([t[feat] for t in trades], dtype=float)
    if len(vals) < 10 or np.isnan(vals).all():
        return rows
    qs = pd.qcut(np.arange(len(vals)), 10, labels=False) if len(vals) >= 10 else None
    pdf = pd.DataFrame({"v": vals, "r": [t["r_mult"] for t in trades],
                        "pnl": [t["pnl"] for t in trades]})
    pdf = pdf.dropna(subset=["v"])
    if len(pdf) < 10:
        return rows
    pdf["bin"] = pd.qcut(pdf["v"], 10, labels=False, duplicates="drop")
    for b, grp in pdf.groupby("bin"):
        rows.append({
            "feat": feat, "bin": str(b), "n": len(grp),
            "lo": round(float(grp["v"].min()), 1), "hi": round(float(grp["v"].max()), 1),
            "win": round((grp["r"] > 0).mean() * 100, 1),
            "avg_r": round(float(grp["r"].mean()), 2),
            "exp": round(float(grp["r"].mean()) * len(grp), 2),
            "pnl": round(float(grp["pnl"].sum()), 0),
        })
    return rows


def _correlations(trades: list[dict], feats: list[str]) -> pd.DataFrame:
    pdf = pd.DataFrame(trades)
    pdf = pdf.dropna(subset=["r_mult"])
    rows = []
    for f in feats:
        if f not in pdf.columns:
            continue
        s = pdf[[f, "r_mult"]].dropna()
        if len(s) < 8 or s[f].nunique() < 4:
            continue
        pear = float(s[f].corr(s["r_mult"])) if s[f].std() and s["r_mult"].std() else np.nan
        # Spearman без scipy: корреляция Пирсона по рангам (pandas-native).
        rk_f = s[f].rank()
        rk_r = s["r_mult"].rank()
        spearm = float(rk_f.corr(rk_r)) if rk_f.std() and rk_r.std() else np.nan
        rows.append({"feature": f, "pearson": round(pear, 3) if pear == pear else np.nan,
                     "spearman": round(spearm, 3) if spearm == spearm else np.nan,
                     "n": len(s)})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Влияние объёма на Fib-сигналы")
    parser.add_argument("--tickers", default=",".join(ALL_TICKERS))
    parser.add_argument("--db", default=str(ROOT / "trading_moex/data/trader_4h.db"))
    parser.add_argument("--period", default="4h")
    parser.add_argument("--direction", default="both", help="long|short|both")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    dirs = [1, -1] if args.direction == "both" else [1 if args.direction == "long" else -1]

    all_trades: list[dict] = []
    for ticker in tickers:
        df = load_df(ticker, args.db, args.period)
        if df.empty:
            print(f"  {ticker}: нет данных {args.period}, пропуск")
            continue
        for direction in dirs:
            trades = run_trades(ticker, df, args.db, args.period, direction)
            all_trades.extend(trades)
            print(f"  {ticker} dir={direction:+d} {args.period}: {len(trades)} сделок")

    if not all_trades:
        print("Нет сделок для анализа")
        return

    print(f"\nВсего сделок: {len(all_trades)}")
    pdf = pd.DataFrame(all_trades)
    n_long = int((pdf["direction"] == 1).sum())
    n_short = int((pdf["direction"] == -1).sum())
    print(f"  Лонги: {n_long}, Шорты: {n_short}")
    print(f"  Win-rate: {(pdf['r_mult'] > 0).mean()*100:.1f}% | "
          f"Avg R: {pdf['r_mult'].mean():+.2f} | "
          f"PNL: {pdf['pnl'].sum():+,.0f} ₽")

    feats = ["vol_rel", "vol_zscore", "vol_trend", "conf_vol_rel", "bull_bear_in",
             "up_down_vol", "vol_hvn_dist", "vol_hvn_dist_below", "abs_vol"]

    print("\n=== Корреляции с R-мультиплом (все сделки) ===")
    corr = _correlations(all_trades, feats)
    if not corr.empty:
        print(corr.to_string(index=False))

    for direction, dw in ((1, "лонг"), (-1, "шорт")):
        sub = [t for t in all_trades if t["direction"] == direction]
        if len(sub) < 10:
            continue
        print(f"\n=== Децили по фиче — {dw} (n={len(sub)}) ===")
        for feat in ["vol_rel", "vol_zscore", "bull_bear_in", "up_down_vol", "conf_vol_rel"]:
            d = _decile_table(sub, feat)
            if not d:
                continue
            print(f"--- {feat} ---")
            for r in d:
                print(f"  bin{r['bin']:>2} [{r['lo']:>6.1f}..{r['hi']:>6.1f}] n={r['n']:>3} "
                      f"win={r['win']:>4.1f}% avgR={r['avg_r']:>+5.2f} exp={r['exp']:>+7.2f} "
                      f"pnl={r['pnl']:>+8,.0f}")


if __name__ == "__main__":
    main()
