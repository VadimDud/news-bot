"""Elementary technical-analysis detectors (pure pandas, strictly causal).

This module is a **library of building blocks**, not a strategy. Each element
detects one phenomenon and returns it with honest timing metadata so that
elements can later be combined like LEGO without smuggling in look-ahead.

Design rules
------------
* A detector only reads bars ``<= i`` when it emits an event on bar ``i``.
* Every pivot/extreme is **confirmed** ``look`` bars after it forms; the bar at
  which the market could first know it is recorded separately from the bar at
  which the extreme physically sits.
* Detection is separated from trading. Nothing here opens positions, sets stops
  or computes PnL.
* All distances are expressed in ATR units so the same thresholds survive across
  tickers with different ranges.

Elements (first vertical chain)
-------------------------------
1. :func:`swings`            — confirmed fractal highs/lows.
2. :func:`levels`            — horizontal levels built on confirmed swings.
3. :func:`breakouts`         — close beyond a level, fresh.
4. :func:`returns_to_level`  — close back through the broken level.
5. :func:`retests`           — touch of the broken level without closing back.
6. :func:`failures`          — broke, closed back, extended the opposite way.

Each detector returns a :class:`pandas.DataFrame` with one row per event and an
explicit ``known_at`` column (the index value of the bar at which the event
became knowable). Use :func:`assert_causal` in tests to prove that appending
future bars never changes already-emitted events.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .candle_patterns import prepare_ohlc
from .risk import atr as _atr


# ── Small helpers ────────────────────────────────────────────────────────────

def _as_float(arr) -> np.ndarray:
    return np.asarray(arr, dtype=float)


# ── 1. Confirmed swings ──────────────────────────────────────────────────────

def swings(df: pd.DataFrame, look: int = 3, atr_period: int = 14) -> pd.DataFrame:
    """Confirmed fractal swing highs and lows.

    A bar ``j`` is a swing high when ``high[j] >= high[j-look .. j+look]``
    (mirror for lows). It is *confirmed* only at bar ``j + look``: that is the
    first bar at which the right-hand neighbours exist and the comparison could
    be made. The event row therefore carries:

    * ``swing_idx``  — physical bar of the extreme (for drawing a chart);
    * ``known_at``   — index value of bar ``j + look`` (earliest honest use);
    * ``price``      — the extreme value;
    * ``side``       — ``"high"`` or ``"low"``;
    * ``amp_atr``    — strength: how far the extreme stands out from its
      ``look`` neighbours on the opposite side, in ATR units.

    No bar before ``known_at`` may use this swing. Ties are broken so that a
    flat window still yields exactly one pivot (the window's own bar), never a
    spurious duplicate per neighbour.
    """
    df = prepare_ohlc(df)
    look = int(look)
    if look <= 0:
        raise ValueError("look must be >= 1")
    n = len(df)
    cols = ["swing_idx", "known_at", "price", "side", "amp_atr"]
    if n < 2 * look + 1:
        return pd.DataFrame(columns=cols)

    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    atr = _atr(df, atr_period).to_numpy(float)
    idx = df.index

    rows = []
    for j in range(look, n - look):
        win_h = high[j - look: j + look + 1]
        win_l = low[j - look: j + look + 1]
        # A pivot is the *first* bar of a plateau: it must strictly beat the
        # left neighbours and be >= the right ones. This yields exactly one
        # pivot per flat top/bottom instead of one per equal neighbour.
        if high[j] > high[j - look:j].max() and high[j] >= high[j + 1:j + look + 1].max():
            support = low[j - look: j + look + 1].min()
            amp = (high[j] - support) / atr[j] if atr[j] > 0 else np.nan
            rows.append((j, idx[j + look], high[j], "high", amp))
        if low[j] < low[j - look:j].min() and low[j] <= low[j + 1:j + look + 1].min():
            resistance = high[j - look: j + look + 1].max()
            amp = (resistance - low[j]) / atr[j] if atr[j] > 0 else np.nan
            rows.append((j, idx[j + look], low[j], "low", amp))
    return pd.DataFrame(rows, columns=cols)


# ── 2. Levels from confirmed swings ─────────────────────────────────────────

def levels(
    df: pd.DataFrame,
    look: int = 3,
    atr_period: int = 14,
    merge_atr: float = 0.5,
) -> pd.DataFrame:
    """Horizontal levels, one per confirmed swing, merged causally.

    Each level is a horizontal line at the swing price. A newly confirmed swing
    of the same side whose price is within ``merge_atr`` ATR of an existing
    level is folded into that level (running mean). Crucially the merge is done
    in confirmation order and only against swings confirmed at or before the
    new one, so a level never depends on a swing that the market did not yet
    know. The merged level's ``known_at`` is the confirmation time of its most
    recent touch.

    ``touches`` counts how many swings were folded into the level and
    ``level_idx`` is the physical bar of the most recent contributing swing.
    """
    sw = swings(df, look=look, atr_period=atr_period)
    cols = ["level_idx", "known_at", "price", "side", "touches", "amp_atr"]
    if sw.empty:
        return pd.DataFrame(columns=cols)
    df = prepare_ohlc(df)
    atr = _atr(df, atr_period).to_numpy(float)
    idx = df.index

    sw = sw.sort_values("known_at", kind="stable").reset_index(drop=True)
    live: list[dict] = []
    out = []
    for _, s in sw.iterrows():
        side = s["side"]
        p = float(s["price"])
        a = atr[int(s["swing_idx"])]
        tol = merge_atr * a if a > 0 else 0.0
        target = None
        for lv in reversed(live):
            if lv["side"] != side:
                continue
            if abs(lv["price"] - p) <= tol:
                target = lv
                break
        if target is None:
            live.append({
                "side": side, "prices": [p], "amps": [float(s["amp_atr"])],
                "price": p, "known_at": s["known_at"],
                "level_idx": int(s["swing_idx"]), "touches": 1,
            })
        else:
            target["prices"].append(p)
            target["amps"].append(float(s["amp_atr"]))
            target["price"] = float(np.mean(target["prices"]))
            target["known_at"] = s["known_at"]
            target["level_idx"] = int(s["swing_idx"])
            target["touches"] += 1
        cur = live[-1] if target is None else target
        out.append({
            "level_idx": cur["level_idx"],
            "known_at": cur["known_at"],
            "price": cur["price"],
            "side": cur["side"],
            "touches": cur["touches"],
            "amp_atr": float(np.mean(cur["amps"])),
        })
    res = pd.DataFrame(out, columns=cols)
    return res.sort_values("known_at", kind="stable").reset_index(drop=True)


# ── 3. Breakouts ─────────────────────────────────────────────────────────────

def breakouts(
    df: pd.DataFrame,
    lvls: pd.DataFrame,
    max_age_bars: int = 500,
    atr_period: int = 14,
) -> pd.DataFrame:
    """Close beyond a level, fresh.

    For each level, a bullish breakout is the first bar ``i`` with
    ``close[i] > price`` and ``close[i-1] <= price`` while the level was known
    at ``i-1`` (so the level is usable before the breaking close). The event is
    known at the close of bar ``i``. ``dist_atr`` records how far beyond the
    level the close landed, in ATR units, at that bar.

    ``max_age_bars`` stops scanning a level after that many bars, which bounds
    the cost on long histories; a level is "stale" after a full regime change.
    """
    df = prepare_ohlc(df)
    cols = ["bar", "known_at", "level_price", "side", "direction", "dist_atr"]
    if df.empty or lvls.empty:
        return pd.DataFrame(columns=cols)
    close = df["close"].to_numpy(float)
    atr = _atr(df, atr_period).to_numpy(float)
    idx = df.index
    n = len(df)

    rows = []
    for _, lv in lvls.iterrows():
        price = float(lv["price"])
        known_at = lv["known_at"]
        try:
            k0 = int(idx.get_loc(known_at))
        except KeyError:
            continue
        start = max(k0 + 1, 1)
        end = min(n, start + int(max_age_bars))
        for i in range(start, end):
            if close[i] > price and close[i - 1] <= price:
                a = atr[i]
                rows.append((i, idx[i], price, lv["side"], 1,
                             (close[i] - price) / a if a > 0 else np.nan))
                break
            if close[i] < price and close[i - 1] >= price:
                a = atr[i]
                rows.append((i, idx[i], price, lv["side"], -1,
                             (price - close[i]) / a if a > 0 else np.nan))
                break
    res = pd.DataFrame(rows, columns=cols)
    if res.empty:
        return res
    # Two near-equal levels can each fire on the same bar; that is one market
    # fact, not two. Keep the breakout that cleared its level by the most.
    res = res.sort_values(["bar", "direction", "dist_atr"], kind="stable")
    res = res.drop_duplicates(subset=["bar", "direction"], keep="last")
    return res.sort_values(["bar", "direction"], kind="stable").reset_index(drop=True)


# ── 4. Return through the broken level ──────────────────────────────────────

def returns_to_level(
    df: pd.DataFrame,
    brks: pd.DataFrame,
    max_wait_bars: int = 10,
    atr_period: int = 14,
) -> pd.DataFrame:
    """A broken level that price closes back through within ``max_wait_bars``.

    The opposite of a retest: a long breakout that closes back below the level
    before the window expires is a *failed* breakout candidate. This detector
    only reports the event; whether it becomes a failure (see :func:`failures`)
    depends on what price does next.
    """
    df = prepare_ohlc(df)
    cols = ["break_bar", "bar", "known_at", "level_price", "direction", "bars_since"]
    if df.empty or brks.empty:
        return pd.DataFrame(columns=cols)
    close = df["close"].to_numpy(float)
    idx = df.index
    n = len(df)

    rows = []
    for _, b in brks.iterrows():
        i0 = int(b["bar"])
        price = float(b["level_price"])
        direction = int(b["direction"])
        end = min(n, i0 + 1 + int(max_wait_bars))
        for i in range(i0 + 1, end):
            if direction == 1 and close[i] < price:
                rows.append((i0, i, idx[i], price, direction, i - i0))
                break
            if direction == -1 and close[i] > price:
                rows.append((i0, i, idx[i], price, direction, i - i0))
                break
    return pd.DataFrame(rows, columns=cols)


# ── 5. Retests ───────────────────────────────────────────────────────────────

def retests(
    df: pd.DataFrame,
    brks: pd.DataFrame,
    max_wait_bars: int = 10,
    atr_period: int = 14,
) -> pd.DataFrame:
    """Touch of the broken level without closing back through it.

    After a bullish breakout, a retest is a bar whose ``low`` reaches the level
    (``low <= price``) and that closes back above it (``close > price``), within
    ``max_wait_bars`` and without a prior close below the level (that would be
    :func:`returns_to_level`, not a retest). Mirror for bearish breakouts.

    ``dist_atr`` is the distance from the retest close back to the level in ATR.
    """
    df = prepare_ohlc(df)
    cols = ["break_bar", "bar", "known_at", "level_price", "direction", "bars_since", "dist_atr"]
    if df.empty or brks.empty:
        return pd.DataFrame(columns=cols)
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    close = df["close"].to_numpy(float)
    atr = _atr(df, atr_period).to_numpy(float)
    idx = df.index
    n = len(df)

    rows = []
    for _, b in brks.iterrows():
        i0 = int(b["bar"])
        price = float(b["level_price"])
        direction = int(b["direction"])
        end = min(n, i0 + 1 + int(max_wait_bars))
        for i in range(i0 + 1, end):
            a = atr[i]
            if direction == 1:
                if close[i] < price:
                    break  # closed back -> not a retest
                if low[i] <= price < close[i]:
                    rows.append((i0, i, idx[i], price, direction, i - i0,
                                 (close[i] - price) / a if a > 0 else np.nan))
                    break
            else:
                if close[i] > price:
                    break
                if high[i] >= price > close[i]:
                    rows.append((i0, i, idx[i], price, direction, i - i0,
                                 (price - close[i]) / a if a > 0 else np.nan))
                    break
    return pd.DataFrame(rows, columns=cols)


# ── 6. Failures / sweeps ─────────────────────────────────────────────────────

def failures(
    df: pd.DataFrame,
    rets: pd.DataFrame,
    look: int = 3,
    atr_period: int = 14,
    max_wait_bars: int = 20,
) -> pd.DataFrame:
    """A returned breakout that then extends the opposite way past a swing.

    A long breakout that closed back below the level (``rets``) is confirmed as
    a failure only when a *confirmed* swing low that existed before the breakout
    is subsequently undercut by a close, within ``max_wait_bars`` of the return.
    The window matters: a close below an old swing 900 bars later is not the
    same pattern, so an open-ended search would label almost everything a
    failure by sheer passage of time. The event is known at the undercutting
    close.
    """
    df = prepare_ohlc(df)
    cols = ["break_bar", "return_bar", "bar", "known_at", "level_price", "direction"]
    if df.empty or rets.empty:
        return pd.DataFrame(columns=cols)
    close = df["close"].to_numpy(float)
    idx = df.index
    n = len(df)

    sw = swings(df, look=look, atr_period=atr_period)
    lows = sw[sw["side"] == "low"] if not sw.empty else sw
    highs = sw[sw["side"] == "high"] if not sw.empty else sw

    rows = []
    for _, r in rets.iterrows():
        ret_bar = int(r["bar"])
        direction = int(r["direction"])
        # For a failed bullish breakout we want the last confirmed swing low that
        # was known before the breakout, then look for a close below it.
        if direction == 1:
            pool = lows
        else:
            pool = highs
        if pool.empty:
            continue
        known_before = pool[
            pool["known_at"].apply(lambda k: idx.get_loc(k) < ret_bar)
        ]
        if known_before.empty:
            continue
        level_swing = float(known_before.iloc[-1]["price"])
        end = min(n, ret_bar + 1 + int(max_wait_bars))
        for i in range(ret_bar + 1, end):
            if direction == 1 and close[i] < level_swing:
                rows.append((int(r["break_bar"]), ret_bar, i, idx[i],
                             float(r["level_price"]), direction))
                break
            if direction == -1 and close[i] > level_swing:
                rows.append((int(r["break_bar"]), ret_bar, i, idx[i],
                             float(r["level_price"]), direction))
                break
    return pd.DataFrame(rows, columns=cols)


# ── Causal audit helper ──────────────────────────────────────────────────────

def assert_causal(detect, df: pd.DataFrame, cut: int, **kw) -> None:
    """Fail if events emitted before ``cut`` change after appending bars >= cut.

    Runs ``detect`` on the full frame and on ``df.iloc[:cut]`` and compares the
    events whose ``known_at`` lies strictly before ``df.index[cut]``. A detector
    that reads future bars will emit or move such an event and this raises.

    Raises ``AssertionError`` with a short diff when the contract is broken.
    """
    full = detect(df, **kw)
    head = detect(df.iloc[:cut], **kw)
    boundary = df.index[cut]
    f_before = full[full["known_at"].apply(lambda k: k < boundary)]
    h = head
    if len(f_before) != len(h):
        raise AssertionError(
            f"{getattr(detect, '__name__', 'detector')}: {len(h)} events before "
            f"{boundary} with truncated data vs {len(f_before)} with full data"
        )
    common = [c for c in f_before.columns if c != "known_at"]
    if len(common):
        f_vals = f_before[common].reset_index(drop=True)
        h_vals = h[common].reset_index(drop=True)
        try:
            pd.testing.assert_frame_equal(f_vals, h_vals, check_dtype=False)
        except AssertionError as exc:
            raise AssertionError(
                f"{getattr(detect, '__name__', 'detector')}: events before "
                f"{boundary} differ when future bars are removed: {exc}"
            ) from exc
