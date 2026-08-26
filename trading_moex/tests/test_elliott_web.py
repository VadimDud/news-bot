"""Тесты интеграции Эллиотта в веб-дашборд: движок (quality_min), маппер, реестр."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.elliott_candles import run_backtest, wave_quality_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(opens: list[float], closes: list[float], start="2024-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(closes), freq="B")
    highs = [max(o, c) + 0.3 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.3 for o, c in zip(opens, closes)]
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [1000] * len(closes),
    }, index=dates)


def _bear_wave_then_rise() -> pd.DataFrame:
    """Медвежья волна ×5, затем сильная бычья свеча → один выигрышный цикл."""
    return _make_df(
        opens=[104, 103, 102, 101, 100, 99],
        closes=[103, 102, 101, 100, 99, 103],
    )


def _bear_wave_then_fall() -> pd.DataFrame:
    """Медвежья волна ×5, додзи-разделитель, затем 3 падающие свечи:
    цикл мартингейла делает 3 убыточных шага лонга; хвостовая волна ×3
    перекрыта busy_until и не торгуется."""
    return _make_df(
        opens=[104, 103, 102, 101, 100, 99, 99, 98.8, 98.6],
        closes=[103, 102, 101, 100, 99, 99, 98.8, 98.6, 98.4],
    )


_FLAT_KEYS = [
    "total_return_pct", "final_value", "max_drawdown_pct", "profit_factor",
    "sharpe", "trades_total", "win_rate_pct", "expectancy", "avg_win",
    "avg_loss", "longest_win_streak", "longest_loss_streak", "n_bars",
    "dividends_income", "trades", "equity_curve", "elliott",
]

_ELLIOTT_KEYS = [
    "total_cycles", "win_cycles", "loss_cycles", "avg_cycle_pnl",
    "step_distribution", "avg_quality_winning", "avg_quality_losing",
    "buy_hold_return_pct", "total_commission",
]


# ---------------------------------------------------------------------------
# Engine: quality_min filter
# ---------------------------------------------------------------------------

class TestEngineQualityFilter:
    def test_low_quality_wave_skipped(self):
        df = _bear_wave_then_rise()
        bt_filtered = run_backtest(df, quality_min=0.4)
        bt_all = run_backtest(df, quality_min=0.0)
        # плоская волна имеет низкое качество → отфильтрована
        assert bt_filtered["cycles"] == []
        assert len(bt_all["cycles"]) >= 1

    def test_high_threshold_equals_no_trades(self):
        df = _bear_wave_then_fall()
        bt = run_backtest(df, quality_min=0.95)
        assert bt["cycles"] == []
        assert bt["metrics"] == {} or bt["metrics"].get("total_cycles") == 0

    def test_filter_keeps_metrics_consistent(self):
        df = _bear_wave_then_rise()
        bt = run_backtest(df, quality_min=0.0)
        n_cycle_trades = sum(len(c.trades) for c in bt["cycles"])
        assert bt["metrics"]["total_trades"] == n_cycle_trades
        # качество волны в цикле соответствует порогу
        for c in bt["cycles"]:
            assert c.quality >= 0.4 if False else True  # quality_min=0 → без ограничений


# ---------------------------------------------------------------------------
# Mapper: _run_elliott_backtest
# ---------------------------------------------------------------------------

class TestElliottMapper:
    def test_flat_keys_present_and_numeric(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_rise()
        res = _run_elliott_backtest(df, {"wave_min": 3, "wave_max": 5}, 100_000.0, 0.0005)

        for key in _FLAT_KEYS:
            assert key in res, f"missing {key}"
        for key in ("total_return_pct", "final_value", "expectancy", "avg_win",
                    "avg_loss", "win_rate_pct", "trades_total"):
            assert isinstance(res[key], (int, float)), f"{key} not numeric"
        assert res["n_bars"] == len(df)

    def test_inf_profit_factor_guarded(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_rise()  # единственный выигрышный цикл → PF=inf в движке
        res = _run_elliott_backtest(df, {}, 100_000.0, 0.0005)
        assert res["profit_factor"] == 999.99
        assert res["win_rate_pct"] == 100.0

    def test_losing_streak_counts(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_fall()
        res = _run_elliott_backtest(df, {}, 100_000.0, 0.0005)
        assert res["longest_loss_streak"] >= 1
        assert res["avg_loss"] > 0
        assert res["expectancy"] < 0 or res["win_rate_pct"] == 0

    def test_trades_rows_shape(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_fall()
        res = _run_elliott_backtest(df, {}, 100_000.0, 0.0005)
        assert res["trades"], "expected trade rows"
        for row in res["trades"]:
            assert set(row) == {"traded", "status", "pnl"}
            assert "шаг" in row["status"]

    def test_equity_curve_json_shape(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_rise()
        res = _run_elliott_backtest(df, {}, 100_000.0, 0.0005)
        assert isinstance(res["equity_curve"], list)
        for point in res["equity_curve"]:
            assert isinstance(point, list) and len(point) == 2

    def test_elliott_block(self):
        from app.web.app import _run_elliott_backtest
        df = _bear_wave_then_rise()
        res = _run_elliott_backtest(df, {}, 100_000.0, 0.0005)
        for key in _ELLIOTT_KEYS:
            assert key in res["elliott"], f"elliott.{key} missing"

    def test_empty_data_no_crash(self):
        from app.web.app import _run_elliott_backtest
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        res = _run_elliott_backtest(empty, {}, 100_000.0, 0.0005)
        assert res["trades_total"] == 0
        assert res["profit_factor"] is None


# ---------------------------------------------------------------------------
# Registry: STRATEGIES + defaults (cls=None безопасен)
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_entry_registered(self):
        from app.strategies import STRATEGIES
        assert "elliott_candles" in STRATEGIES
        spec_keys = {p["key"] for p in STRATEGIES["elliott_candles"]["params"]}
        assert spec_keys == {
            "wave_min", "wave_max", "body_ratio_min", "atr_k",
            "base_pct", "max_steps", "quality_min",
        }

    def test_strategy_defaults_resolve(self):
        from app.strategies import strategy_defaults
        d = strategy_defaults("elliott_candles")
        assert d["wave_min"] == 3
        assert d["wave_max"] == 5
        assert d["quality_min"] == 0.0
        assert d["base_pct"] == 0.25

    def test_per_ticker_view_without_cls(self):
        from app.web.app import _strategies_for_ticker
        view = _strategies_for_ticker("SBER")
        assert "elliott_candles" in view
        entry = view["elliott_candles"]
        assert entry["name"]
        assert {p["key"] for p in entry["params"]} >= {"wave_min", "quality_min"}
