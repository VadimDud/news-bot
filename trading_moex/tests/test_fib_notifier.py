"""Tests for Fibonacci retracement signal notifier (synthetic data + isolated DB)."""

import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config as trading_config  # noqa: E402
from app import storage  # noqa: E402
from app.fib_notifier import (  # noqa: E402
    format_fib_signal,
    run_fib_scan,
    _scan_ticker,
    _setup_id,
    _is_stale,
    _params_from_config,
    _dispatch_setup,
    ticker_settings,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(closes, opens=None, freq="h", start="2023-01-01"):
    n = len(closes)
    close = np.array(closes, dtype=float)
    if opens is None:
        opens = np.append(close[0], close[:-1])
    highs = np.maximum(opens, close) + 0.4
    lows = np.minimum(opens, close) - 0.4
    idx = pd.date_range(start, periods=n, freq=freq)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": close,
        "volume": [1000] * n,
    }, index=idx)


def _uptrend_setup(n_cycles=12, up_bars=48, dn_bars=14, seed=3):
    """Uptrend ending inside a retracement setup (bullish, in discount)."""
    rng = np.random.default_rng(seed)
    p, prices = 100.0, []
    for i in range((up_bars + dn_bars) * n_cycles):
        prices.append(p)
        m = i % (up_bars + dn_bars)
        if m < up_bars:
            p += 1.0 + rng.normal(0, 0.2)
        else:
            p -= 2.7
    return prices


def _save_candles(ticker, df, period="1day"):
    out = df.copy()
    out["begin"] = [str(idx.date()) if hasattr(idx, "date") else str(idx) for idx in out.index]
    storage.save_candles(ticker, period, out)


# ---------------------------------------------------------------------------
# _setup_id / format / stale
# ---------------------------------------------------------------------------

class TestSetupId:
    def test_id_from_swing_pair(self):
        assert _setup_id({"swing_low": 167.62, "swing_high": 215.16}) == "167.6200->215.1600"

    def test_none_when_missing(self):
        assert _setup_id({"swing_low": None}) is None


class TestFormat:
    def test_message_contains_key_parts(self):
        info = {
            "close": 179.66, "swing_low": 167.62, "swing_high": 215.16,
            "segment": 47.54, "atr": 2.86, "rsi": 23.9, "factors": 2,
            "trend_up": True, "target_in_price": 191.39,
            "levels": {"50.0%": 191.39, "0% (цель)": 215.16},
        }
        msg = format_fib_signal("SBER", info)
        assert "SBER" in msg
        assert "Фибоначчи" in msg
        assert "191.39" in msg
        assert "0% (цель)" in msg

    def test_short_message_mentions_sale_and_short_levels(self):
        info = {
            "close": 179.66, "swing_low": 150.0, "swing_high": 215.0,
            "segment": 65.0, "atr": 2.86, "rsi": 70.0, "factors": 2,
            "factors_short": 3, "trend_up": False, "in_premium": True,
            "target_in_price": 182.5,
            "levels_short": {"50.0%": 182.5, "0% (цель)": 150.0},
        }
        msg = format_fib_signal("GAZP", info, short=True)
        assert "ПРОДАЖА" in msg
        assert "GAZP" in msg
        assert "swing high" in msg
        assert "182.5" in msg
        assert "swing low" in msg
        assert "Факторов: 3" in msg

    def test_stale_flag_output(self):
        info = {"close": 100, "trend_up": True, "factors": 1,
                "swing_low": 90, "swing_high": 120, "segment": 30,
                "target_in_price": 105, "levels": {}}
        assert "устарели" in format_fib_signal("LKOH", info, stale=True)


class TestStale:
    def test_fresh(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        df = pd.DataFrame({"open": [1]*20, "high": [1]*20, "low": [1]*20,
                           "close": [1]*20, "volume": [1]*20}, index=dates)
        with patch("app.fib_notifier.trading_config") as mc:
            mc.TRADER_SIGNALS_MAX_STALE_DAYS = 1000
            assert _is_stale(df) is False

    def test_old_is_stale(self):
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        df = pd.DataFrame({"open": [1]*5, "high": [1]*5, "low": [1]*5,
                           "close": [1]*5, "volume": [1]*5}, index=dates)
        with patch("app.fib_notifier.trading_config") as mc:
            mc.TRADER_SIGNALS_MAX_STALE_DAYS = 1
            assert _is_stale(df) is True


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

class TestParams:
    def test_params_only_accepts_detector_keys(self, monkeypatch):
        # _params_from_config не должен содержать ключей, не входящих в
        # сигнатуру детектора (mini_rr и т.п.), иначе TypeError.
        with patch("app.fib_notifier.trading_config") as mc:
            mc.TRADER_FIB_SWING_BARS = 10
            mc.TRADER_FIB_FIB_IN_LOW = 0.5
            mc.TRADER_FIB_FIB_IN_HIGH = 0.618
            mc.TRADER_FIB_TREND_PERIOD = 200
            mc.TRADER_FIB_CONFLUENCE_MIN = 1
            mc.TRADER_FIB_RSI_OVERSOLD = 50.0
            mc.TRADER_FIB_REGIME_ADX_MIN = 0.0
            mc.TRADER_FIB_REGIME_ATR_VOL_MAX = 0.0
            params = _params_from_config()
            assert set(params) <= {
                "swing_bars", "fib_in_low", "fib_in_high", "trend_period",
                "confluence_min", "rsi_oversold", "regime_adx_min", "regime_atr_vol_max",
            }


# ---------------------------------------------------------------------------
# Per-ticker settings (БД → TICKER_OVERRIDES → конфиг)
# ---------------------------------------------------------------------------

class TestTickerSettings:
    def test_default_direction_zero_and_config_params(self):
        storage.delete_fib_ticker_setting("ZZZZ")
        s = ticker_settings("ZZZZ")
        assert s["direction"] == 0
        assert "swing_bars" in s["params"]

    def test_saved_setting_overrides_override_and_config(self):
        storage.save_fib_ticker_setting("MTSS", -1, {"swing_bars": 7, "confluence_min": 3})
        s = ticker_settings("MTSS")
        assert s["direction"] == -1
        assert s["params"]["swing_bars"] == 7
        assert s["params"]["confluence_min"] == 3
        storage.delete_fib_ticker_setting("MTSS")

    def test_code_override_applied_without_db_row(self):
        storage.delete_fib_ticker_setting("TATN")
        s = ticker_settings("TATN")
        assert s["direction"] == -1  # из TICKER_OVERRIDES
        assert s["params"]["confluence_min"] == 1
        assert s["timeframe"] == "4h"

    def test_delete_restores_code_override(self):
        storage.save_fib_ticker_setting("GAZP", 1, {"trend_period": 50})
        assert ticker_settings("GAZP")["direction"] == 1
        storage.delete_fib_ticker_setting("GAZP")
        assert ticker_settings("GAZP")["direction"] == -1  # вернулся код-оверрайд

    def test_list_settings_roundtrip(self):
        storage.save_fib_ticker_setting("TESTFIB", 1, {"a": 1.5})
        all_s = storage.list_fib_ticker_settings()
        assert all_s["TESTFIB"]["direction"] == 1
        assert all_s["TESTFIB"]["params"] == {"a": 1.5}
        storage.delete_fib_ticker_setting("TESTFIB")
        assert "TESTFIB" not in storage.list_fib_ticker_settings()

    def test_timeframe_override_sber_stays_1day(self):
        storage.delete_fib_ticker_setting("SBER")
        s = ticker_settings("SBER")
        assert s["timeframe"] == "1day"  # на 4h шорт убыточен — код-оверрайд

    def test_timeframe_db_override_wins(self):
        storage.save_fib_ticker_setting("GAZP", -1, {}, timeframe="1day")
        assert ticker_settings("GAZP")["timeframe"] == "1day"
        storage.delete_fib_ticker_setting("GAZP")
        assert ticker_settings("GAZP")["timeframe"] == "4h"  # вернулся дефолт

    def test_default_timeframe_4h(self):
        storage.delete_fib_ticker_setting("ZZZZ")
        assert ticker_settings("ZZZZ")["timeframe"] == "4h"


# ---------------------------------------------------------------------------
# run_fib_scan (integration with mocked TG)
# ---------------------------------------------------------------------------

class TestRunFibScan:
    async def test_scan_empty_watchlist(self, monkeypatch):
        storage.set_watchlist([])
        monkeypatch.setattr(trading_config, "WATCH_TICKERS", [])
        with patch("app.fib_notifier._send_tg", new_callable=AsyncMock) as mock_send:
            assert await run_fib_scan() == []
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_scan_graceful_on_missing_data(self):
        storage.set_watchlist(["NODATA"])
        assert await run_fib_scan() == []

    @pytest.mark.asyncio
    async def test_scan_end_to_end_sends_once(self):
        # Детерминированно подсовываем готовый setup: проверяем связку
        # дедуп → отправка → запись в БД (без зависимости от стохастики).
        df = _make_df(np.linspace(100, 150, 60), freq="h")
        info = {
            "close": 130.0, "swing_low": 110.0, "swing_high": 150.0,
            "segment": 40.0, "atr": 1.0, "rsi": 25.0, "factors": 2,
            "trend_up": True, "in_discount": True, "in_zone": True,
            "levels": {"50.0%": 130.0, "61.8%": 125.28, "0% (цель)": 150.0},
        }
        storage.set_watchlist(["TEST"])
        with patch("app.fib_notifier._load_candles", return_value=df), \
             patch("app.fib_notifier._load_htf", return_value=None), \
             patch("app.fib_notifier.fib_pullback.detect_latest_setup", return_value=info), \
             patch("app.fib_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TEST")
            assert result is not None and result["sent"] is True
            mock_send.assert_awaited_once()
            assert storage.get_fib_signal("TEST")["setup_id"] == "110.0000->150.0000"
            # второй раз — дедуп, сигнал не уходит повторно
            mock_send.reset_mock()
            assert await _scan_ticker("TEST") is None
            mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_scan_short_setup_sends_and_dedups(self):
        # Лонг-setup нет, шорт-setup есть — сигнал шорт уходит и пишется в
        # fib_short_signals (отдельный дедуп от лонга).
        df = _make_df(np.linspace(150, 100, 60), freq="h")
        info = {
            "close": 105.0, "swing_low": 90.0, "swing_high": 130.0,
            "segment": 40.0, "atr": 1.5, "rsi": 72.0, "factors": 2,
            "factors_short": 3, "trend_up": False, "in_premium": True,
            "levels": {"50.0%": 110.0, "0% (цель)": 90.0},
            "levels_short": {"50.0%": 110.0, "0% (цель)": 90.0},
        }
        storage.set_watchlist(["TEST2"])
        with patch("app.fib_notifier._load_candles", return_value=df), \
             patch("app.fib_notifier._load_htf", return_value=None), \
             patch("app.fib_notifier.fib_pullback.detect_latest_setup", return_value=None), \
             patch("app.fib_notifier.fib_pullback.detect_latest_short_setup", return_value=info), \
             patch("app.fib_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TEST2")
            assert result is not None and result["sent"] is True and result["short"] is True
            mock_send.assert_awaited_once()
            assert storage.get_fib_short_signal("TEST2")["setup_id"] == "90.0000->130.0000"
            # дедуп шорт-сигнала
            mock_send.reset_mock()
            assert await _scan_ticker("TEST2") is None
            mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_scan_short_does_not_cross_dedup_with_long(self):
        # Один и тот же setup_id в short-таблице не блокирует long-сигнал.
        df = _make_df(np.linspace(100, 150, 60), freq="h")
        long_info = {
            "close": 130.0, "swing_low": 110.0, "swing_high": 150.0,
            "segment": 40.0, "atr": 1.0, "rsi": 25.0, "factors": 2,
            "trend_up": True, "in_discount": True,
            "levels": {"50.0%": 130.0, "0% (цель)": 150.0},
        }
        storage.set_watchlist(["TEST3"])
        storage.save_fib_short_signal(
            "TEST3", "110.0000->150.0000",
            swing_low=110.0, swing_high=150.0, retrace=40.0, factors=2,
        )
        with patch("app.fib_notifier._load_candles", return_value=df), \
             patch("app.fib_notifier._load_htf", return_value=None), \
             patch("app.fib_notifier.fib_pullback.detect_latest_setup", return_value=long_info), \
             patch("app.fib_notifier._send_tg", new_callable=AsyncMock, return_value=True) as mock_send:
            result = await _scan_ticker("TEST3")
            assert result is not None and result["sent"] is True
            assert storage.get_fib_signal("TEST3")["setup_id"] == "110.0000->150.0000"
