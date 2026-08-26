"""Candle-based Elliott micro-wave strategy: classification, wave detection,
quality scoring, Martingale back-test and multi-timeframe analytics.

Design (from user brief):
- One candle = impulse (body) + correction (wick).
- A "wave" = run of 3–5 same-color candles (body closes same direction).
- Direction: counter-trend fade — after bull wave SELL, after bear wave BUY.
- Position held exactly one candle (open→close).
- Martingale: 25 % / 50 % / 100 % of equity (max 3 trades per cycle).
- Wave quality: micro-Elliott rules (extension, not-shortest, alternation, dominance).
- Multi-TF: analytics only — check whether HTF correction decomposes into
  5 LTF waves (zigzag hypothesis) vs 3 (flat) vs overlapping (triangle).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Candle classification
# ---------------------------------------------------------------------------

def _atr(series: pd.DataFrame, period: int = 14) -> pd.Series:
    """True Range → rolling ATR."""
    h, l, prev_c = series["high"], series["low"], series["close"].shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def classify_candles(
    df: pd.DataFrame,
    body_ratio_min: float = 0.6,
    atr_period: int = 14,
    atr_k: float = 0.5,
) -> pd.DataFrame:
    """Add columns: ``body_ratio``, ``body_abs``, ``is_impulse``, ``candle_color``.

    An impulse candle satisfies **both**:
        body_ratio  >= body_ratio_min          (clean directional move)
        body_abs    >= atr_k * ATR(14)          (absolute size filter)

    ``candle_color``: 'bull' if close > open, 'bear' if close < open, 'doji' if equal.
    """
    out = df.copy()
    out["body_abs"] = (out["close"] - out["open"]).abs()
    rng = (out["high"] - out["low"]).replace(0, np.nan)
    out["body_ratio"] = out["body_abs"] / rng

    atr = _atr(out, atr_period)
    out["atr"] = atr

    out["is_impulse"] = (out["body_ratio"] >= body_ratio_min) & (out["body_abs"] >= atr_k * atr)

    color = np.where(out["close"] > out["open"], "bull",
                     np.where(out["close"] < out["open"], "bear", "doji"))
    out["candle_color"] = color
    return out


# ---------------------------------------------------------------------------
# Wave detection (run of same-color candles)
# ---------------------------------------------------------------------------

@dataclass
class Wave:
    start_idx: int          # position in df (iloc)
    end_idx: int            # inclusive
    direction: Literal["bull", "bear"]
    candle_count: int
    df: pd.DataFrame = field(repr=False)   # full OHLCV DataFrame

    @property
    def start_dt(self):
        return self.df.index[self.start_idx]

    @property
    def end_dt(self):
        return self.df.index[self.end_idx]

    @property
    def next_open(self):
        """Entry price = open of the candle *after* the wave."""
        if self.end_idx + 1 < len(self.df):
            return float(self.df["open"].iloc[self.end_idx + 1])
        return None

    @property
    def next_close(self):
        """Exit price = close of the candle *after* the wave."""
        if self.end_idx + 1 < len(self.df):
            return float(self.df["close"].iloc[self.end_idx + 1])
        return None

    def has_next_candle(self) -> bool:
        return self.end_idx + 1 < len(self.df)

    def sub_candles(self) -> pd.DataFrame:
        """Slice of df for candles in this wave."""
        return self.df.iloc[self.start_idx : self.end_idx + 1]


def detect_waves(
    df: pd.DataFrame,
    wave_min: int = 3,
    wave_max: int = 5,
) -> list[Wave]:
    """Find runs of same non-doji color candles with length in [wave_min, wave_max]."""
    colors = df["candle_color"].values
    waves: list[Wave] = []
    i = 0
    n = len(colors)
    while i < n:
        c = colors[i]
        if c == "doji":
            i += 1
            continue
        j = i
        while j < n and colors[j] == c:
            j += 1
        run_len = j - i
        if wave_min <= run_len <= wave_max:
            waves.append(Wave(
                start_idx=i, end_idx=j - 1,
                direction=c,  # type: ignore[arg-type]
                candle_count=run_len,
                df=df,
            ))
        i = j
    return waves


# ---------------------------------------------------------------------------
# Wave quality scoring (micro-Elliott rules)
# ---------------------------------------------------------------------------

def wave_quality_score(wave: Wave) -> dict:
    """Score a wave on 4 micro-Elliott criteria → total 0..1.

    Returns dict: ``{total, extension, not_shortest, alternation, dominance,
    impulse_count, impulse_positions}``
    """
    sub = wave.sub_candles()
    impulse_mask = sub["is_impulse"]
    n_impulses = int(impulse_mask.sum())
    n_total = len(sub)

    # --- 1. Extension: max body at middle position (2-3 of 5, middle of 3) ---
    extension = 0.0
    if n_impulses >= 2:
        bodies = sub["body_abs"]
        max_pos = bodies.argmax()  # iloc within sub
        # "middle" = positions with indices [len//3 .. 2*len//3]
        lo = n_total // 3
        hi = 2 * n_total // 3
        if lo <= max_pos <= hi:
            extension = 1.0
        elif abs(max_pos - n_total // 2) <= 1:
            extension = 0.5  # near middle

    # --- 2. Not-shortest: middle impulse body is not the shortest ---
    # Elliott rule: wave 3 is never the shortest of waves 1/3/5.
    # Here "middle" impulse = analog of wave 3.
    not_shortest = 0.0
    if n_impulses >= 3:
        imp_bodies = sub.loc[impulse_mask, "body_abs"].values
        mid = len(imp_bodies) // 2
        others = np.delete(imp_bodies, mid)
        min_others = others.min()
        if imp_bodies[mid] > min_others:
            not_shortest = 1.0   # strictly not the shortest
        elif imp_bodies[mid] == min_others and np.sum(imp_bodies == min_others) > 1:
            not_shortest = 0.5  # tied for shortest with at least one other
    elif n_impulses >= 2:
        not_shortest = 1.0  # can't be shortest with only 2

    # --- 3. Alternation: impulse/corrective transitions ---
    alternation = 0.0
    if n_total >= 3:
        transitions = 0
        alt_transitions = 0
        for k in range(1, n_total):
            prev_imp = bool(sub["is_impulse"].iloc[k - 1])
            curr_imp = bool(sub["is_impulse"].iloc[k])
            transitions += 1
            if prev_imp != curr_imp:
                alt_transitions += 1
        alternation = alt_transitions / transitions
    elif n_total >= 2:
        alternation = 1.0

    # --- 4. Body dominance: net progress / total path ---
    dominance = 0.0
    direction = 1 if wave.direction == "bull" else -1
    net_progress = (sub["close"].iloc[-1] - sub["open"].iloc[0]) * direction
    total_path = (sub["high"] - sub["low"]).sum()
    if total_path > 0:
        dominance = max(0.0, min(1.0, net_progress / total_path))

    total = 0.30 * extension + 0.25 * not_shortest + 0.20 * alternation + 0.25 * dominance

    return {
        "total": round(total, 4),
        "extension": round(extension, 4),
        "not_shortest": round(not_shortest, 4),
        "alternation": round(alternation, 4),
        "dominance": round(dominance, 4),
        "impulse_count": n_impulses,
    }


# ---------------------------------------------------------------------------
# Fibonacci ratios (analytics)
# ---------------------------------------------------------------------------

def fibonacci_levels(wave: Wave) -> dict:
    """Typical Fibonacci retracement expectations for the next corrective move.

    Returns the expected depth in price of a 50 % and 61.8 % retrace of the
    wave's total directional move.
    """
    sub = wave.sub_candles()
    if wave.direction == "bull":
        total = float(sub["high"].max() - sub["open"].iloc[0])
    else:
        total = float(sub["open"].iloc[0] - sub["low"].min())
    return {
        "wave_range": round(total, 4),
        "fib_382": round(total * 0.382, 4),
        "fib_500": round(total * 0.500, 4),
        "fib_618": round(total * 0.618, 4),
    }


# ---------------------------------------------------------------------------
# Martingale FSM + back-test
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_dt: str
    direction: Literal["long", "short"]
    step: int              # 1, 2, or 3 (attempt within cycle)
    size_pct: float        # fraction of initial equity (0.25, 0.50, 1.0)
    entry_price: float
    exit_price: float
    pnl: float             # after commission
    pnl_pct: float
    commission: float
    wave_start: str
    wave_end: str
    wave_len: int
    quality: float


@dataclass
class Cycle:
    wave_start: str
    wave_end: str
    wave_len: int
    direction: Literal["bull", "bear"]   # wave direction (signal is opposite)
    quality: float
    trades: list[Trade] = field(default_factory=list)

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def total_pnl_pct(self) -> float:
        return sum(t.pnl_pct * t.size_pct for t in self.trades)

    @property
    def steps_used(self) -> int:
        return len(self.trades)

    @property
    def won(self) -> bool:
        return self.total_pnl > 0


def _run_cycle(
    df: pd.DataFrame,
    wave: Wave,
    equity: float,
    base_pct: float = 0.25,
    max_steps: int = 3,
    commission: float = 0.0005,
) -> tuple[Cycle, float, int]:
    """Execute a Martingale cycle starting after *wave*.

    Returns (cycle, new_equity, last_consumed_idx).
    """
    fade_dir = "long" if wave.direction == "bear" else "short"
    cycle = Cycle(
        wave_start=str(wave.start_dt),
        wave_end=str(wave.end_dt),
        wave_len=wave.candle_count,
        direction=wave.direction,
        quality=wave_quality_score(wave)["total"],
    )

    cur_idx = wave.end_idx + 1
    equity_at_start = equity
    step = 0
    last_consumed = cur_idx - 1

    while step < max_steps and cur_idx < len(df):
        # Skip doji candles — no trade on indecision
        if df["candle_color"].iloc[cur_idx] == "doji":
            cur_idx += 1
            continue

        step += 1
        entry = float(df["open"].iloc[cur_idx])
        exit_ = float(df["close"].iloc[cur_idx])
        size_pct = base_pct * (2 ** (step - 1))
        size_value = equity_at_start * min(size_pct, 1.0)  # cap at 100 %

        if fade_dir == "long":
            gross_pct = (exit_ - entry) / entry
        else:
            gross_pct = (entry - exit_) / entry

        cost = commission * 2  # both sides
        net_pct = gross_pct - cost
        pnl = size_value * net_pct

        cycle.trades.append(Trade(
            entry_dt=str(df.index[cur_idx]),
            direction=fade_dir,
            step=step,
            size_pct=size_pct,
            entry_price=entry,
            exit_price=exit_,
            pnl=round(pnl, 2),
            pnl_pct=round(net_pct, 6),
            commission=round(size_value * cost, 2),
            wave_start=str(wave.start_dt),
            wave_end=str(wave.end_dt),
            wave_len=wave.candle_count,
            quality=cycle.quality,
        ))
        equity += pnl
        last_consumed = cur_idx

        if pnl >= 0:
            break  # cycle won

        cur_idx += 1  # next candle for doubled position

    return cycle, equity, last_consumed


def run_backtest(
    df: pd.DataFrame,
    wave_min: int = 3,
    wave_max: int = 5,
    base_pct: float = 0.25,
    max_steps: int = 3,
    commission: float = 0.0005,
    body_ratio_min: float = 0.6,
    atr_period: int = 14,
    atr_k: float = 0.5,
    initial_equity: float = 100_000,
) -> dict:
    """Full back-test on a single ticker/period DataFrame.

    Returns dict with ``cycles``, ``trades``, ``equity_curve``,
    ``metrics``.
    """
    if df.empty or len(df) < wave_min + 1:
        return {"cycles": [], "trades": [], "equity_curve": [], "metrics": {}}

    classified = classify_candles(df, body_ratio_min, atr_period, atr_k)
    waves = detect_waves(classified, wave_min, wave_max)

    equity = initial_equity
    all_cycles: list[Cycle] = []
    equity_curve: list[tuple[str, float]] = [(str(classified.index[0]), equity)]
    busy_until = -1  # last index occupied by an ongoing cycle

    for wave in waves:
        if not wave.has_next_candle():
            continue
        # Skip if this wave overlaps with a previous cycle's active trades
        if wave.end_idx <= busy_until:
            continue
        cycle, equity, last_consumed = _run_cycle(classified, wave, equity, base_pct, max_steps, commission)
        all_cycles.append(cycle)
        equity_curve.append((str(wave.next_open), round(equity, 2)))
        busy_until = last_consumed

    all_trades = [t for c in all_cycles for t in c.trades]
    metrics = _compute_metrics(all_cycles, all_trades, initial_equity, equity, classified)

    return {
        "cycles": all_cycles,
        "trades": all_trades,
        "equity_curve": equity_curve,
        "metrics": metrics,
    }


def _compute_metrics(
    cycles: list[Cycle],
    trades: list[Trade],
    initial: float,
    final: float,
    df: pd.DataFrame,
) -> dict:
    if not cycles:
        return {"total_cycles": 0, "total_trades": 0}

    pnls = [c.total_pnl for c in cycles]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # max drawdown from equity curve
    running = initial
    peak = running
    max_dd = 0.0
    for c in cycles:
        running += c.total_pnl
        peak = max(peak, running)
        dd = (peak - running) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # step distribution
    step_dist = {}
    for c in cycles:
        s = c.steps_used
        step_dist[s] = step_dist.get(s, 0) + 1

    # commission total
    total_comm = sum(t.commission for t in trades)

    # average quality of winning vs losing cycles
    win_q = [c.quality for c in cycles if c.won]
    loss_q = [c.quality for c in cycles if not c.won]

    # buy & hold
    bh_return = (float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0])

    # profit factor: sum of net winning PnL / abs(sum of net losing PnL)
    net_wins = sum(t.pnl for t in trades if t.pnl > 0)
    net_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))

    return {
        "total_cycles": len(cycles),
        "total_trades": len(trades),
        "win_cycles": len(wins),
        "loss_cycles": len(losses),
        "win_rate": round(len(wins) / len(cycles), 4) if cycles else 0,
        "avg_cycle_pnl": round(np.mean(pnls), 2) if pnls else 0,
        "median_cycle_pnl": round(float(np.median(pnls)), 2) if pnls else 0,
        "total_pnl": round(sum(pnls), 2),
        "total_return_pct": round((final - initial) / initial * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "buy_hold_return_pct": round(bh_return * 100, 2),
        "total_commission": round(total_comm, 2),
        "profit_factor": round(net_wins / net_losses, 2) if net_losses > 0 else float("inf"),
        "step_distribution": step_dist,
        "avg_quality_winning": round(float(np.mean(win_q)), 4) if win_q else None,
        "avg_quality_losing": round(float(np.mean(loss_q)), 4) if loss_q else None,
        "final_equity": round(final, 2),
    }


# ---------------------------------------------------------------------------
# Multi-TF correction analytics
# ---------------------------------------------------------------------------

def _count_ltf_waves(ltf_df: pd.DataFrame, start_dt, end_dt) -> list[dict]:
    """Within [start_dt, end_dt] (inclusive both ends) on the LTF,
    count alternating same-color runs (waves), excluding doji.

    Returns list of dicts: ``{color, length}``.
    """
    window = ltf_df[(ltf_df.index >= start_dt) & (ltf_df.index <= end_dt)]
    if window.empty:
        return []

    colors = window["candle_color"].values
    runs: list[dict] = []
    i = 0
    while i < len(colors):
        c = colors[i]
        if c == "doji":
            i += 1
            continue
        j = i
        while j < len(colors) and colors[j] == c:
            j += 1
        runs.append({"color": c, "length": j - i, "start_idx": i, "end_idx": j - 1})
        i = j
    return runs


def mtf_correction_analysis(
    htf_df: pd.DataFrame,
    ltf_df: pd.DataFrame,
    wave_min: int = 3,
    wave_max: int = 5,
) -> list[dict]:
    """Check HTF trend-correction pattern vs LTF sub-wave decomposition.

    1. Detect HTF trend = run of same-color candles (length >= wave_min).
    2. After trend ends, detect correction window = opposite-color run.
    3. Map correction window to LTF candles, count sub-waves (alternating runs of ≥2).
    4. Classify:
       - ``zigzag``: correction decomposes into ~5 LTF waves (with alternation).
       - ``flat``: ~3 waves.
       - ``triangle``: 5+ overlapping waves.
       - ``unknown``: other.
    5. Record forward return on HTF (next candle after correction).

    Returns list of correction records.
    """
    htf = classify_candles(htf_df, body_ratio_min=0.6, atr_period=14, atr_k=0.5)
    ltf = classify_candles(ltf_df, body_ratio_min=0.6, atr_period=14, atr_k=0.5)

    htf_colors = htf["candle_color"].values
    results: list[dict] = []
    i = 0
    n = len(htf_colors)

    while i < n:
        c = htf_colors[i]
        if c == "doji":
            i += 1
            continue
        # detect trend run
        j = i
        while j < n and htf_colors[j] == c:
            j += 1
        trend_len = j - i
        if trend_len < wave_min:
            i = j
            continue

        trend_start_dt = htf.index[i]
        trend_end_dt = htf.index[j - 1]

        # detect correction run after trend
        if j >= n:
            break
        cor_color = "bear" if c == "bull" else "bull"
        k = j
        while k < n and htf_colors[k] == cor_color:
            k += 1
        cor_len = k - j
        if cor_len < 2:
            i = k
            continue

        cor_start_dt = htf.index[j]
        cor_end_dt = htf.index[k - 1]

        # LTF sub-wave count
        ltf_runs = _count_ltf_waves(ltf, cor_start_dt, cor_end_dt)
        significant_runs = [r for r in ltf_runs if r["length"] >= 2]
        n_ltf_waves = len(significant_runs)

        # classify
        if n_ltf_waves == 5:
            pattern = "zigzag"
        elif n_ltf_waves == 3:
            pattern = "flat"
        elif n_ltf_waves >= 6:
            pattern = "triangle"
        else:
            pattern = "unknown"

        # forward return: next HTF candle after correction
        fwd_return = None
        if k < n:
            fwd_open = float(htf["open"].iloc[k])
            fwd_close = float(htf["close"].iloc[k])
            if cor_color == "bull":
                fwd_return = (fwd_close - fwd_open) / fwd_open
            else:
                fwd_return = (fwd_open - fwd_close) / fwd_open

        results.append({
            "trend_direction": c,
            "trend_len": trend_len,
            "trend_start": str(trend_start_dt),
            "trend_end": str(trend_end_dt),
            "correction_len": cor_len,
            "correction_start": str(cor_start_dt),
            "correction_end": str(cor_end_dt),
            "ltf_waves_count": n_ltf_waves,
            "ltf_runs": ltf_runs,
            "pattern": pattern,
            "fwd_return_pct": round(fwd_return * 100, 4) if fwd_return is not None else None,
        })

        i = k

    return results


# ---------------------------------------------------------------------------
# Quality analytics across cycles
# ---------------------------------------------------------------------------

def quality_analytics(cycles: list[Cycle]) -> dict:
    """Group cycles by quality quartile, compute win-rate & avg PnL per group."""
    if not cycles:
        return {"quartiles": {}}

    scores = [c.quality for c in cycles]
    q25 = float(np.percentile(scores, 25)) if scores else 0
    q50 = float(np.percentile(scores, 50)) if scores else 0
    q75 = float(np.percentile(scores, 75)) if scores else 1

    quartiles = {"low": [], "mid_low": [], "mid_high": [], "high": []}
    for c in cycles:
        q = c.quality
        if q <= q25:
            quartiles["low"].append(c)
        elif q <= q50:
            quartiles["mid_low"].append(c)
        elif q <= q75:
            quartiles["mid_high"].append(c)
        else:
            quartiles["high"].append(c)

    summary = {}
    for label, group in quartiles.items():
        if not group:
            summary[label] = {"count": 0}
            continue
        pnls = [c.total_pnl for c in group]
        wins = [p for p in pnls if p > 0]
        summary[label] = {
            "count": len(group),
            "win_rate": round(len(wins) / len(group), 4),
            "avg_pnl": round(float(np.mean(pnls)), 2),
            "avg_quality": round(float(np.mean([c.quality for c in group])), 4),
        }

    return {"quartiles": summary, "thresholds": {"q25": q25, "q50": q50, "q75": q75}}
