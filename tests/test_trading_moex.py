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
