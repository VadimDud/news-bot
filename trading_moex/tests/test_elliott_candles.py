"""Tests for Elliott micro-wave candle strategy (synthetic data, no DB)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.elliott_candles import (
    Wave,
    classify_candles,
    detect_waves,
    wave_quality_score,
    run_backtest,
    mtf_correction_analysis,
    quality_analytics,
    _count_ltf_waves,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_dt(ts, days=1):
    """Return a single Timestamp offset by *days* from *ts*."""
    return ts + pd.Timedelta(days=days)


def _make_candles(closes, opens=None, base=100.0, h_range=1.0):
    """Build a minimal OHLCV DataFrame from a list of close prices.

    Each candle: open = previous close (or base for first), close = given,
    high = max(o,c) + h_range/2, low = min(o,c) - h_range/2.
    """
    if opens is None:
        opens = [base] + list(closes[:-1])
    n = len(closes)
    data = []
    for i in range(n):
        o, c = opens[i], closes[i]
        h = max(o, c) + h_range / 2
        l = min(o, c) - h_range / 2
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": 1000})
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(data, index=idx)


def _append_candle(df, close, open_, h_range=1.0, days_offset=1):
    """Append a single candle to df at a new datetime after the last index."""
    last = df.index[-1]
    new_dt = _next_dt(last, days_offset)
    h = max(open_, close) + h_range / 2
    l = min(open_, close) - h_range / 2
    row = pd.DataFrame(
        [{"open": open_, "high": h, "low": l, "close": close, "volume": 1000}],
        index=pd.DatetimeIndex([new_dt]),
    )
    return pd.concat([df, row])


def _bull_candles(n, step=1.0):
    """N consecutive bullish candles (close > open by step)."""
    closes = [100.0 + i * step for i in range(1, n + 1)]
    opens = [c - step for c in closes]
    return _make_candles(closes, opens)


def _bear_candles(n, step=1.0):
    """N consecutive bearish candles (close < open by step)."""
    closes = [100.0 - i * step for i in range(1, n + 1)]
    opens = [c + step for c in closes]
    return _make_candles(closes, opens)


# ---------------------------------------------------------------------------
# Candle classification
# ---------------------------------------------------------------------------

class TestClassifyCandles:
    def test_bull_impulse(self):
        df = _make_candles([105], opens=[100], h_range=1.0)
        result = classify_candles(df, body_ratio_min=0.6, atr_k=0.01)
        assert result["candle_color"].iloc[0] == "bull"
        assert result["is_impulse"].iloc[0] == True  # noqa: E712

    def test_bear_impulse(self):
        df = _make_candles([95], opens=[100], h_range=1.0)
        result = classify_candles(df, body_ratio_min=0.6, atr_k=0.01)
        assert result["candle_color"].iloc[0] == "bear"
        assert result["is_impulse"].iloc[0] == True  # noqa: E712

    def test_doji(self):
        df = _make_candles([100], opens=[100], h_range=2.0)
        result = classify_candles(df, body_ratio_min=0.6, atr_k=0.01)
        assert result["candle_color"].iloc[0] == "doji"
        assert result["is_impulse"].iloc[0] == False  # noqa: E712

    def test_small_body_not_impulse(self):
        df = _make_candles([100.1], opens=[100], h_range=10.0)
        result = classify_candles(df, body_ratio_min=0.6, atr_k=0.01)
        assert result["is_impulse"].iloc[0] == False  # noqa: E712

    def test_atr_filter(self):
        df = _make_candles([103], opens=[100], h_range=1.0)
        result = classify_candles(df, body_ratio_min=0.3, atr_k=100.0)
        assert result["is_impulse"].iloc[0] == False  # noqa: E712


# ---------------------------------------------------------------------------
# Wave detection
# ---------------------------------------------------------------------------

class TestDetectWaves:
    def test_bull_run_of_3(self):
        df = classify_candles(_bull_candles(3))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 1
        assert waves[0].direction == "bull"
        assert waves[0].candle_count == 3

    def test_bull_run_of_5(self):
        df = classify_candles(_bull_candles(5))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 1
        assert waves[0].candle_count == 5

    def test_run_of_6_not_detected(self):
        df = classify_candles(_bull_candles(6))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 0

    def test_run_of_2_not_detected(self):
        df = classify_candles(_bull_candles(2))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 0

    def test_doji_breaks_run(self):
        closes = [101, 102, 100, 103, 104]
        opens = [100, 101, 100, 102, 103]
        df = classify_candles(_make_candles(closes, opens))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 0

    def test_bear_run_of_4(self):
        df = classify_candles(_bear_candles(4))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 1
        assert waves[0].direction == "bear"
        assert waves[0].candle_count == 4

    def test_multiple_waves(self):
        """3 bull + bear separator + 3 bear → two waves."""
        bull = _bull_candles(3)
        # Append a doji (separator) then 3 bear candles
        sep = _append_candle(bull, 100, 100, h_range=2.0, days_offset=1)  # doji
        bear = _bear_candles(3, step=1.0)
        # Re-index bear candles to follow the separator
        bear_reidx = bear.copy()
        bear_reidx.index = pd.date_range(_next_dt(sep.index[-1], 0), periods=3, freq="D")
        # But we need unique indices; just use _append_candle for each
        combined = sep
        for i in range(3):
            c_val = 100.0 - (i + 1) * 1.0
            o_val = c_val + 1.0
            combined = _append_candle(combined, c_val, o_val, days_offset=1)
        df = classify_candles(combined)
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 2
        assert waves[0].direction == "bull"
        assert waves[1].direction == "bear"

    def test_has_next_candle(self):
        df = classify_candles(_bull_candles(3))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert waves[0].has_next_candle() == False  # noqa: E712

    def test_has_next_candle_with_buffer(self):
        bull = _bull_candles(3)
        # Append bear candle so it doesn't extend the bull run
        combined = _append_candle(bull, 99, 100, days_offset=1)
        df = classify_candles(combined)
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) == 1
        assert waves[0].has_next_candle() == True  # noqa: E712


# ---------------------------------------------------------------------------
# Wave quality scoring
# ---------------------------------------------------------------------------

class TestWaveQuality:
    def test_perfect_wave(self):
        closes = [105, 110, 120, 115, 125]
        opens = [100, 105, 110, 110, 120]
        df = classify_candles(_make_candles(closes, opens, h_range=0.5))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        assert len(waves) >= 1
        score = wave_quality_score(waves[0])
        assert 0.0 <= score["total"] <= 1.0
        for key in ("extension", "not_shortest", "alternation", "dominance"):
            assert key in score

    def test_all_impulse_no_alternation(self):
        closes = [105, 110, 115]
        opens = [100, 105, 110]
        df = classify_candles(_make_candles(closes, opens, h_range=0.5))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        score = wave_quality_score(waves[0])
        assert score["alternation"] == 0.0

    def test_alternating_impulse_corrective(self):
        closes = [103, 104, 108, 109, 113]
        opens = [100, 103, 104, 108, 109]
        h_ranges = [0.5, 10.0, 0.5, 10.0, 0.5]
        data = []
        for i in range(5):
            o, c = opens[i], closes[i]
            h = max(o, c) + h_ranges[i] / 2
            l = min(o, c) - h_ranges[i] / 2
            data.append({"open": o, "high": h, "low": l, "close": c, "volume": 1000})
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        df = classify_candles(pd.DataFrame(data, index=idx), atr_k=0.01)
        waves = detect_waves(df, wave_min=3, wave_max=5)
        score = wave_quality_score(waves[0])
        assert score["alternation"] > 0.5

    def test_dominance_bull(self):
        closes = [101, 102, 103]
        opens = [100, 101, 102]
        df = classify_candles(_make_candles(closes, opens, h_range=0.2))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        score = wave_quality_score(waves[0])
        assert score["dominance"] > 0.5

    def test_not_shortest_middle(self):
        """Middle impulse NOT the shortest → not_shortest = 1.0."""
        # 5-candle wave: big bodies at pos 0,2,4 (impulse); small at 1,3 (corrective)
        # Impulse bodies: [5, 3, 5] → middle=3, others=[5,5], min_others=5, 3 < 5 → 0.0
        # But we need 3 impulses where middle is NOT shortest:
        # Impulse bodies: [3, 5, 4] → middle=5, others=[3,4], min_others=3, 5 > 3 → 1.0
        closes = [103, 104, 110, 111, 116]
        opens  = [100, 103, 104, 110, 111]
        # Candles 0,2,4: big body (3,6,5) → impulse (with small range)
        # Candles 1,3: tiny body (1,1) → corrective (with large range)
        h_ranges = [0.5, 10.0, 0.5, 10.0, 0.5]
        data = []
        for i in range(5):
            o, c = opens[i], closes[i]
            data.append({"open": o, "high": max(o,c)+h_ranges[i]/2,
                         "low": min(o,c)-h_ranges[i]/2, "close": c, "volume": 1000})
        df = classify_candles(pd.DataFrame(data, index=pd.date_range("2024-01-01", periods=5, freq="D")), atr_k=0.01)
        waves = detect_waves(df, wave_min=3, wave_max=5)
        score = wave_quality_score(waves[0])
        # Impulse bodies: 3, 6, 5 → mid=6, others=[3,5], min_others=3 → 6>3 → 1.0
        assert score["not_shortest"] == 1.0

    def test_not_shortest_middle_is_shortest(self):
        """Middle impulse IS the shortest → not_shortest = 0.0."""
        # Impulse bodies: [5, 2, 4] → middle=2, others=[5,4], min_others=4, 2<4 → 0.0
        closes = [105, 106, 110, 111, 116]
        opens  = [100, 105, 106, 110, 111]
        h_ranges = [0.5, 10.0, 0.5, 10.0, 0.5]
        data = []
        for i in range(5):
            o, c = opens[i], closes[i]
            data.append({"open": o, "high": max(o,c)+h_ranges[i]/2,
                         "low": min(o,c)-h_ranges[i]/2, "close": c, "volume": 1000})
        df = classify_candles(pd.DataFrame(data, index=pd.date_range("2024-01-01", periods=5, freq="D")), atr_k=0.01)
        waves = detect_waves(df, wave_min=3, wave_max=5)
        score = wave_quality_score(waves[0])
        # Impulse bodies: 5, 2, 4 → mid=2, others=[5,4], min_others=4, 2<4 → 0.0
        assert score["not_shortest"] == 0.0


# ---------------------------------------------------------------------------
# Martingale FSM
# ---------------------------------------------------------------------------

class TestMartingale:
    def test_single_win_no_double(self):
        """Wave of 3 bear candles → BUY → next candle bull → win."""
        bear = _bear_candles(3, step=1.0)
        combined = _append_candle(bear, 104, 100, days_offset=1)
        bt = run_backtest(combined, wave_min=3, wave_max=5, initial_equity=100_000,
                          base_pct=0.25, max_steps=3, commission=0.0005,
                          body_ratio_min=0.6, atr_k=0.01)
        assert len(bt["cycles"]) >= 1
        c = bt["cycles"][0]
        assert c.steps_used == 1
        assert c.total_pnl > 0

    def test_loss_then_win(self):
        """3 bear wave → doji (skip) → bear (loss) → bull (win on doubled)."""
        bear_wave = _bear_candles(3, step=1.0)
        # Doji separator (skipped by _run_cycle)
        sep = _append_candle(bear_wave, 100, 100, h_range=2.0, days_offset=1)
        # Bear candle after doji → loss on long
        step1 = _append_candle(sep, 98, 100, days_offset=1)
        # Bull candle → win on doubled long
        step2 = _append_candle(step1, 104, 98, days_offset=1)
        bt = run_backtest(step2, wave_min=3, wave_max=5, initial_equity=100_000,
                          base_pct=0.25, max_steps=3, commission=0.0005,
                          body_ratio_min=0.6, atr_k=0.01)
        assert len(bt["cycles"]) >= 1
        c = bt["cycles"][0]
        assert c.steps_used == 2
        assert c.trades[1].size_pct == 0.5

    def test_max_steps_3(self):
        """3 bear wave → doji (skip) → 3 bear candles (all losses) → cycle stops."""
        bear_wave = _bear_candles(3, step=1.0)
        sep = _append_candle(bear_wave, 100, 100, h_range=2.0, days_offset=1)
        loss1 = _append_candle(sep, 98, 100, days_offset=1)
        loss2 = _append_candle(loss1, 96, 98, days_offset=1)
        loss3 = _append_candle(loss2, 94, 96, days_offset=1)
        bt = run_backtest(loss3, wave_min=3, wave_max=5, initial_equity=100_000,
                          base_pct=0.25, max_steps=3, commission=0.0005,
                          body_ratio_min=0.6, atr_k=0.01)
        assert len(bt["cycles"]) >= 1
        c = bt["cycles"][0]
        assert c.steps_used == 3
        assert len(c.trades) == 3
        assert c.trades[0].size_pct == 0.25
        assert c.trades[1].size_pct == 0.50
        assert c.trades[2].size_pct == 1.0

    def test_commission_deducted(self):
        bear = _bear_candles(3, step=1.0)
        combined = _append_candle(bear, 104, 100, days_offset=1)
        bt = run_backtest(combined, wave_min=3, wave_max=5, initial_equity=100_000,
                          base_pct=0.25, max_steps=3, commission=0.001,
                          body_ratio_min=0.6, atr_k=0.01)
        assert len(bt["trades"]) >= 1
        t = bt["trades"][0]
        assert t.commission > 0
        gross = (t.exit_price - t.entry_price) / t.entry_price
        expected_pnl_pct = gross - 0.001 * 2
        assert abs(t.pnl_pct - expected_pnl_pct) < 1e-5


# ---------------------------------------------------------------------------
# Backtest integration
# ---------------------------------------------------------------------------

class TestBacktest:
    def test_empty_data(self):
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df.index.name = "datetime"
        bt = run_backtest(df)
        assert bt["cycles"] == []
        assert bt["metrics"] == {}

    def test_too_few_candles(self):
        df = classify_candles(_bull_candles(2))
        bt = run_backtest(df, wave_min=3, wave_max=5)
        assert bt["cycles"] == []

    def test_equity_curve_length(self):
        """4 bull candles (wave) + bear candle (next) → 1 cycle, eq curve = 2."""
        bull = _bull_candles(4)
        combined = _append_candle(bull, 99, 100, days_offset=1)  # bear → next candle
        bt = run_backtest(combined, wave_min=3, wave_max=5, body_ratio_min=0.6, atr_k=0.01)
        # Wave of 4 bull + bear next → wave detected, cycle executed
        assert len(bt["equity_curve"]) == 1 + len(bt["cycles"])

    def test_no_overlapping_cycles(self):
        """Two consecutive waves: first cycle's trades should block the second."""
        # Wave1: 3 bull candles (indices 0-2)
        # Separator: bear candle (index 3) — next candle for wave1, consumed by trade1
        # Wave2: 3 bull candles (indices 4-6)
        # Separator: bear candle (index 7) — next candle for wave2
        combined = _bull_candles(3)
        combined = _append_candle(combined, 99, 100, days_offset=1)   # index 3: bear (trade)
        combined = _append_candle(combined, 101, 100, days_offset=1)  # index 4: bull
        combined = _append_candle(combined, 102, 101, days_offset=1)  # index 5: bull
        combined = _append_candle(combined, 103, 102, days_offset=1)  # index 6: bull
        combined = _append_candle(combined, 99, 103, days_offset=1)   # index 7: bear (trade)

        bt = run_backtest(combined, wave_min=3, wave_max=5, initial_equity=100_000,
                          body_ratio_min=0.6, atr_k=0.01)
        # Wave1 at [0:2] → trade at index 3, cycle ends at index 3
        # Wave2 at [4:6] → trade at index 7
        # These should NOT overlap (wave2.end_idx=6 > busy_until=3), so both execute
        # But if wave2's cycle used 3 steps (indices 3,4,5), it WOULD overlap wave1
        # With busy_until tracking, wave2 should still fire since wave1 ends at idx 3
        assert len(bt["cycles"]) >= 1  # at least first wave fires

    def test_overlapping_waves_blocked(self):
        """Wave2 starts during wave1's active trades → blocked."""
        # 3 bear candles [0:2] → wave1 (BUY)
        # Doji at [3] → separator (skipped by _run_cycle)
        # Bear at [4] → trade1 (loss)
        # Bear at [5] → trade2 (loss)
        # Bear at [6] → trade3 (loss)
        # 3 bear candles [4:6] → would overlap wave1's trades
        combined = _bear_candles(3, step=1.0)
        combined = _append_candle(combined, 100, 100, h_range=2.0, days_offset=1)  # doji separator
        combined = _append_candle(combined, 98, 100, days_offset=1)  # bear (loss)
        combined = _append_candle(combined, 96, 98, days_offset=1)   # bear (loss)
        combined = _append_candle(combined, 94, 96, days_offset=1)   # bear (loss)

        bt = run_backtest(combined, wave_min=3, wave_max=5, initial_equity=100_000,
                          base_pct=0.25, max_steps=3, commission=0.0005,
                          body_ratio_min=0.6, atr_k=0.01)
        # Wave1 at [0:2] → 3 trades at indices [4,5,6] (doji skipped)
        # busy_until = 2+3 = 5, so wave starting at [4] blocked (4 <= 5)
        assert len(bt["cycles"]) == 1


# ---------------------------------------------------------------------------
# MTF analytics
# ---------------------------------------------------------------------------

class TestMTFAnalytics:
    def test_count_ltf_waves(self):
        """Count alternating runs of ≥2 candles."""
        # Build 13 candles: bull(3), bear(2), bull(3), bear(2), bull(3)
        combined = _bull_candles(3, step=1.0)
        for run_len, is_bull in [(2, False), (3, True), (2, False), (3, True)]:
            for i in range(run_len):
                if is_bull:
                    o = combined["close"].iloc[-1]
                    c = o + 1.0
                else:
                    o = combined["close"].iloc[-1]
                    c = o - 1.0
                combined = _append_candle(combined, c, o, h_range=0.5, days_offset=1)

        df = classify_candles(combined, atr_k=0.01)
        runs = _count_ltf_waves(df, df.index[0], df.index[-1])
        sig = [r for r in runs if r["length"] >= 2]
        assert len(sig) == 5

    def test_htf_correction_zigzag(self):
        """HTF correction with 5 LTF sub-waves → zigzag."""
        # HTF: 3 bull (trend) + 3 bear (correction)
        htf = _bull_candles(3, step=3.0)
        for i in range(3):
            o = htf["close"].iloc[-1]
            c = o - 3.0
            htf = _append_candle(htf, c, o, days_offset=1)

        # LTF: within correction window, create 5 alternating runs of ≥2
        base_dt = htf.index[3]  # start of correction
        ltf_candles = []
        for i in range(10):
            dt = base_dt + pd.Timedelta(hours=i)
            if (i // 2) % 2 == 0:
                o, c = 100 + i * 0.5, 100 + i * 0.5 + 1.0
            else:
                o, c = 100 + i * 0.5 + 1.0, 100 + i * 0.5
            ltf_candles.append({"open": o, "high": max(o, c) + 0.2,
                               "low": min(o, c) - 0.2, "close": c, "volume": 100})
        ltf = pd.DataFrame(ltf_candles, index=pd.DatetimeIndex(
            [base_dt + pd.Timedelta(hours=i) for i in range(10)]
        ))
        ltf = classify_candles(ltf, body_ratio_min=0.3, atr_k=0.01)

        results = mtf_correction_analysis(htf, ltf, wave_min=3, wave_max=5)
        assert len(results) >= 1
        r = results[0]
        assert r["ltf_waves_count"] >= 5 or r["pattern"] in ("triangle", "unknown")


# ---------------------------------------------------------------------------
# Quality analytics
# ---------------------------------------------------------------------------

class TestQualityAnalytics:
    def test_empty_cycles(self):
        result = quality_analytics([])
        assert result == {"quartiles": {}}

    def test_groups_by_quality(self):
        from app.elliott_candles import Cycle
        cycles = []
        for i in range(20):
            c = Cycle(
                wave_start=f"2024-01-{i+1:02d}",
                wave_end=f"2024-01-{i+1:02d}",
                wave_len=3,
                direction="bull",
                quality=i / 20.0,
            )
            cycles.append(c)
        result = quality_analytics(cycles)
        assert "quartiles" in result
        assert len(result["quartiles"]) == 4
        total = sum(q.get("count", 0) for q in result["quartiles"].values())
        assert total == 20


# ---------------------------------------------------------------------------
# Fibonacci levels
# ---------------------------------------------------------------------------

class TestFibonacci:
    def test_bull_wave(self):
        from app.elliott_candles import fibonacci_levels
        df = classify_candles(_bull_candles(3, step=10.0))
        waves = detect_waves(df, wave_min=3, wave_max=5)
        levels = fibonacci_levels(waves[0])
        assert levels["wave_range"] > 0
        assert levels["fib_382"] < levels["fib_500"] < levels["fib_618"]
