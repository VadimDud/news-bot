"""Юнит-тесты торгового модуля: сигналы на синтетических данных."""

import numpy as np
import pandas as pd
import pytest

from trading_moex.app.signals import (
    donchian_position,
    rsi_position,
    signal_from_position,
    sma_cross_position,
)


def make_df(close_values):
    n = len(close_values)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    close = np.asarray(close_values, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def test_sma_cross_position_up_then_down():
    df = make_df(list(range(50)))
    pos = sma_cross_position(df, fast=5, slow=10)
    assert pos.iloc[0] == 0
    assert pos.iloc[-1] == 1


def test_sma_cross_flat_market_no_position():
    df = make_df([100.0] * 40)
    pos = sma_cross_position(df, fast=5, slow=10)
    assert (pos == 0).all()


def test_rsi_position_oversold_enter_overbought_exit():
    # Падение до перепроданности (вход), потом рост до перекупленности (выход)
    values = list(np.linspace(100, 80, 20)) + list(np.linspace(80, 120, 30))
    df = make_df(values)
    pos = rsi_position(df, period=14, buy_threshold=40, sell_threshold=60)
    arr = pos.to_numpy()
    assert arr[0] == 0
    assert arr.max() == 1  # вошли в позицию на перепроданности
    assert arr[-1] == 0  # вышли на перекупленности


def test_donchian_breakout():
    flat = [100.0] * 25
    df = make_df(flat + [105.0, 106.0])
    pos = donchian_position(df, period=20)
    assert pos.iloc[-1] == 1
    assert pos.iloc[24] == 0


def test_signal_from_position():
    assert signal_from_position(pd.Series([0, 0, 0])) == "hold"
    assert signal_from_position(pd.Series([0, 1])) == "buy"
    assert signal_from_position(pd.Series([1, 0])) == "sell"
    assert signal_from_position(pd.Series([1, 1])) == "hold"
    assert signal_from_position(pd.Series([1])) == "hold"


def test_rsi_bounds():
    df = make_df(list(np.linspace(100, 80, 50)))
    from trading_moex.app.signals import rsi

    values = rsi(df["close"], 14)
    assert values.between(0, 100).all()


# ── Настройки / токены ───────────────────────────────────────────────────────

def test_settings_roundtrip(tmp_path, monkeypatch):
    from trading_moex.app import config, settings, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()

    settings.set("TINKOFF_API_TOKEN", "tok-123")
    settings.set("MOEX_LOGIN", "  user@moex.ru  ")
    settings.set("TRADER_WEB_PASSWORD", "secret")

    assert settings.tinkoff_token() == "tok-123"
    assert settings.moex_login() == "user@moex.ru"
    assert settings.moex_password() == ""
    assert settings.get("TRADER_WEB_PASSWORD") == "secret"


def test_settings_env_fallback(tmp_path, monkeypatch):
    from trading_moex.app import config, settings, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()

    monkeypatch.setattr(config, "MOEX_LOGIN", "env-login")
    assert settings.moex_login() == "env-login"
    assert settings.mask("1234567890") == "1234•••"
    assert settings.mask("") == ""
    assert settings.mask("ab") == "••••"


# ── Список бэктестов / JSON ──────────────────────────────────────────────────

def test_list_runs_parses_result_json(tmp_path, monkeypatch):
    """list_runs() должен распарсить result/params, иначе index.html падает с 500."""
    from trading_moex.app import config, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()

    run_id = storage.create_run(
        "SBER", "1day", "sma_cross", {"fast": 10, "slow": 30},
        "2025-01-01", "2026-01-01",
    )
    storage.finish_run(run_id, {"total_return_pct": 5.5, "n_bars": 100, "trades": []})

    runs = storage.list_runs()
    assert len(runs) == 1
    assert runs[0]["status"] == "done"
    assert runs[0]["params"] == {"fast": 10, "slow": 30}
    assert runs[0]["result"]["total_return_pct"] == 5.5


def test_list_runs_empty_db(tmp_path, monkeypatch):
    from trading_moex.app import config, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()

    assert storage.list_runs() == []


# ── Watchlist ────────────────────────────────────────────────────────────────

def test_watchlist_add_remove(tmp_path, monkeypatch):
    from trading_moex.app import config, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()

    assert storage.list_watchlist() == []

    storage.add_watchlist("SBER")
    storage.add_watchlist("SBER")  # дубликат игнорируется
    storage.add_watchlist("LKOH")
    assert storage.list_watchlist() == ["SBER", "LKOH"]

    storage.remove_watchlist("SBER")
    storage.remove_watchlist("MISSING")  # не падает
    assert storage.list_watchlist() == ["LKOH"]


def test_watchlist_live_priority(tmp_path, monkeypatch):
    from trading_moex.app import config, live, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()
    monkeypatch.setattr(config, "WATCH_TICKERS", ["GAZP"])

    assert live._watchlist() == ["GAZP"]  # фолбэк на env

    storage.add_watchlist("SBER")
    assert live._watchlist() == ["SBER"]  # приоритет у БД


def test_catalog_find():
    from trading_moex.app.catalog import AVAILABLE_TICKER_KEYS, find

    assert "SBER" in AVAILABLE_TICKER_KEYS
    assert find("sber")["ticker"] == "SBER"
    assert find("NOT_EXIST") is None


# ── Риск-менеджмент ─────────────────────────────────────────────────────────

def test_risk_position_size():
    from trading_moex.app.risk import position_size

    # риск 1% от 100 000 = 1000; стоп-дистанция 10 → лот 100
    assert position_size(100_000, 0.01, 10.0, 100.0) == 100
    # округление вниз
    assert position_size(100_000, 0.01, 7.0, 100.0) == 142
    # минимум 1
    assert position_size(100_000, 0.01, 5000.0, 100.0) == 1
    assert position_size(100_000, 0.01, 0.0, 100.0) == 1
    # NaN-дистанция стопа не должна валить расчёт лота
    assert position_size(100_000, 0.01, float("nan"), 100.0) == 1
    assert position_size(100_000, 0.01, -5.0, 100.0) == 1


def test_risk_atr_and_stops():
    import numpy as np
    import pandas as pd

    from trading_moex.app.risk import atr, stop_distance

    close = np.linspace(100, 120, 60)
    df = pd.DataFrame(
        {"open": close, "high": close + 2.0, "low": close - 2.0, "close": close}
    )
    a = atr(df, 14)
    tail = a.iloc[20:]  # первые бары — NaN на прогреве Wilder
    assert tail.notna().all()
    assert (tail > 0).all()
    sd = stop_distance(df, 14, 1.5)
    assert (sd.iloc[20:] > 0).all()
    # дистанция стопа растёт с коэффициентом ATR
    assert stop_distance(df, 14, 3.0).iloc[-1] > sd.iloc[-1]


def test_risk_candle_pattern_helpers():
    from trading_moex.app.risk import atr

    import pandas as pd

    close = [100.0] * 20
    df = pd.DataFrame(
        {"open": close, "high": [x + 1 for x in close], "low": [x - 1 for x in close], "close": close}
    )
    assert atr(df, 14).iloc[-1] > 0


# ── Свечные паттерны / трендовый фильтр ─────────────────────────────────────

def test_is_bullish_pinbar():
    from trading_moex.app.signals import is_bearish_pinbar, is_bullish_pinbar

    # молот: тело 0.2, нижняя тень 2.0 >= 2*тело, верхняя тень 0.1 <= тело
    assert is_bullish_pinbar(10, 10.3, 8, 10.2, 2.0) is True
    # падающая звезда: верхняя тень 0.5 >= 2*тело 0.2, нижняя тень мала
    assert is_bearish_pinbar(10.2, 10.7, 10.1, 10.0, 2.0) is True
    # обычная свеча — не пин-бар
    assert is_bullish_pinbar(10, 10.3, 9.9, 10.2, 2.0) is False


def test_is_bullish_engulfing():
    from trading_moex.app.signals import is_bearish_engulfing, is_bullish_engulfing

    # бычье поглощение: медвежья (110→105) поглощена бычьей (102→112)
    assert is_bullish_engulfing(102, 113, 101, 112, 110, 105) is True
    # медвежье поглощение: бычья (102→112) поглощена медвежьей (113→101)
    assert is_bearish_engulfing(113, 114, 101, 101, 102, 112) is True
    # тела не поглощаются
    assert is_bullish_engulfing(106, 112, 104, 111, 110, 105) is False


def test_pinbar_position_state():
    import numpy as np

    from trading_moex.app.signals import pinbar_position

    n = 50
    close = np.full(n, 100.0)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    # бар 10 — молот: тело 0.2, нижняя тень 2.0, верхняя тень 0.1
    df.loc[10, "open"] = 100.0
    df.loc[10, "high"] = 100.3
    df.loc[10, "low"] = 98.0
    df.loc[10, "close"] = 100.2
    pos = pinbar_position(df)
    assert pos.iloc[10] == 1
    assert pos.iloc[9] == 0


def test_engulfing_position_state():
    import numpy as np

    from trading_moex.app.signals import engulfing_position

    n = 30
    close = np.full(n, 100.0)
    df = pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close})
    # бар 5: медвежий (101→99), бар 6: бычье поглощение (98→102, охват 97..103)
    df.loc[5, "open"], df.loc[5, "close"] = 101.0, 99.0
    df.loc[6, "open"], df.loc[6, "close"] = 98.0, 102.0
    df.loc[6, "low"], df.loc[6, "high"] = 97.0, 103.0
    pos = engulfing_position(df)
    assert pos.iloc[6] == 1
    assert pos.iloc[5] == 0


def test_trend_filter_blocks_countertrend_entries():
    import numpy as np

    from trading_moex.app.signals import apply_trend_filter, rsi_position

    n = 300
    close = 200 - 0.4 * np.arange(n) + np.sin(np.arange(n) / 5) * 12
    df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close})
    df.index = pd.date_range("2024-01-01", periods=n, freq="D")
    pos = rsi_position(df, period=14, buy_threshold=30, sell_threshold=70)
    assert int((pos.diff() == 1).sum()) >= 1  # RSI входит на просадках
    filtered = apply_trend_filter(pos, df["close"], 200)
    assert int((filtered.diff() == 1).sum()) == 0  # EMA200-фильтр блокирует


def test_trend_filter_disabled():
    import numpy as np

    from trading_moex.app.signals import apply_trend_filter, rsi_position

    n = 100
    close = np.linspace(100, 150, n)
    df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close})
    pos = rsi_position(df, period=14)
    assert apply_trend_filter(pos, df["close"], 0).equals(pos)


# ── Бэктест с риск-стратегиями ──────────────────────────────────────────────

def test_backtest_smoke_with_risk_strategies():
    import numpy as np
    import pandas as pd

    from trading_moex.app.backtest import run_backtest
    from trading_moex.app.strategies import STRATEGIES

    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.linspace(100, 130, n) + np.sin(np.arange(n) / 7) * 3
    df = pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1000.0},
        index=idx,
    )
    for key in STRATEGIES:
        params = {p["key"]: p["default"] for p in STRATEGIES[key]["params"]}
        res = run_backtest(df, STRATEGIES[key]["cls"], params, cash=100_000, commission=0.0005)
        assert "profit_factor" in res
        assert "expectancy" in res
        assert "longest_win_streak" in res
        assert "n_bars" in res


# ── Live: уровни SL/TP в сигналах ────────────────────────────────────────────

def _fake_live_trader(strategy: str, df):
    from trading_moex.app.live import LiveTrader

    trader = LiveTrader()
    trader.set_strategy(strategy)

    async def fake_candles(client, figi):
        return df

    trader._candles_df = fake_candles
    return trader


async def test_live_signals_stop_target_on_hold():
    """Удерживаемая позиция (hold) должна нести уровни SL/TP, иначе live их не проверяет."""
    close = np.linspace(100, 140, 60)
    df = pd.DataFrame(
        {"open": close, "high": close + 1.0, "low": close - 1.0, "close": close, "volume": 1000.0}
    )
    trader = _fake_live_trader("sma_cross", df)
    signals = await trader._compute_signals(None, {"TEST": "figi"})
    info = signals["TEST"]
    assert info["action"] == "hold"  # уже в позиции, не вход
    assert info["stop"] is not None and info["stop"] == info["stop"]
    assert info["target"] is not None and info["target"] == info["target"]
    assert info["stop"] < df["close"].iloc[-1] < info["target"]


async def test_live_signals_buy_has_stop_target():
    """Сигнал входа тоже несёт уровни SL/TP."""
    n = 60
    close = np.linspace(110, 100, 35).tolist()  # плавный спад
    close += [100.0] * (n - 35 - 1)  # флэт
    close += [120.0]  # скачок на последнем баре: SMA10 пересекает SMA30 → buy
    close = np.array(close)
    df = pd.DataFrame(
        {"open": close, "high": close + 1.0, "low": close - 1.0, "close": close, "volume": 1000.0}
    )
    trader = _fake_live_trader("sma_cross", df)
    signals = await trader._compute_signals(None, {"TEST": "figi"})
    info = signals["TEST"]
    assert info["action"] == "buy"
    assert info["stop"] is not None and info["stop"] < df["close"].iloc[-1]
    assert info["target"] is not None and info["target"] > df["close"].iloc[-1]


async def test_live_signals_nan_atr_fallback():
    """Короткая история при большом периоде ATR (NaN) не должна давать NaN-уровни."""
    close = np.linspace(100, 140, 40)
    df = pd.DataFrame(
        {"open": close, "high": close + 1.0, "low": close - 1.0, "close": close, "volume": 1000.0}
    )
    trader = _fake_live_trader("sma_cross", df)
    trader.strategy_params["atr_period"] = 200  # ATR целиком NaN на 40 барах
    signals = await trader._compute_signals(None, {"TEST": "figi"})
    info = signals["TEST"]
    assert info["stop"] is not None and info["stop"] == info["stop"]
    assert info["stop"] < df["close"].iloc[-1] < info["target"]

