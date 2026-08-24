"""Юнит-тесты торгового модуля: сигналы на синтетических данных."""

import asyncio

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


def test_volume_confirms():
    from trading_moex.app.signals import volume_confirms

    # фильтр выключен (period = 0) — всегда True
    assert volume_confirms(1.0, 1000.0, 1.5, 0) is True
    # объём >= множитель * среднее
    assert volume_confirms(2000.0, 1000.0, 1.5, 20) is True
    assert volume_confirms(1400.0, 1000.0, 1.5, 20) is False
    assert volume_confirms(1000.0, 1000.0, 1.0, 20) is True
    # NaN/нулевое среднее (тёплый период) — достаточно ненулевого объёма
    assert volume_confirms(5.0, float("nan"), 1.5, 20) is True
    assert volume_confirms(5.0, 0.0, 1.5, 20) is True
    assert volume_confirms(0.0, float("nan"), 1.5, 20) is False


def test_bulls_dominate():
    from trading_moex.app.signals import bulls_dominate

    # выключено (frac = 0)
    assert bulls_dominate(110, 90, 100, 0) is True
    # close в верхних 70% диапазона — быки
    assert bulls_dominate(110, 90, 104, 0.7) is True   # (104-90)/20 = 0.7
    assert bulls_dominate(110, 90, 100, 0.7) is False  # (100-90)/20 = 0.5
    # нулевой диапазон — нельзя определить
    assert bulls_dominate(100, 100, 100, 0.7) is False


def test_volume_profile_levels():
    from trading_moex.app.signals import volume_profile_levels

    # однобокий объём: основной объём у нижней границы -> поддержка внизу
    highs = [102.0] * 5 + [101.0]
    lows = [100.0] * 5 + [100.0]
    closes = [101.0] * 6
    vols = [100.0] * 5 + [1000.0]  # огромный объём на последней свече у 100
    sup, res = volume_profile_levels(highs, lows, closes, vols, price=101.5, bins=20, mult=1.5)
    assert sup is not None and sup < 101.5
    assert res is None or res > 101.5

    # NaN-бары (тёплый период) пропускаются
    sup2, res2 = volume_profile_levels([float("nan")] * 3, [float("nan")] * 3,
                                       [float("nan")] * 3, [float("nan")] * 3,
                                       price=100.0, bins=20, mult=1.5)
    assert sup2 is None and res2 is None



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

def test_ma_helpers():
    from trading_moex.app.signals import (
        ma_golden_cross,
        ma_pullback,
        ma_slope_up,
        ma_spread,
        ma_stacked,
    )

    assert ma_stacked(51, 50, 49) is True
    assert ma_stacked(49, 50, 51) is False
    assert ma_stacked(50, 50, 49) is False

    assert ma_golden_cross(fast_prev=49, mid_prev=50, fast=51, mid=50) is True
    assert ma_golden_cross(fast_prev=51, mid_prev=50, fast=51, mid=50) is False
    assert ma_golden_cross(fast_prev=49, mid_prev=50, fast=49.5, mid=50) is False

    assert ma_slope_up(50, 51) is True
    assert ma_slope_up(51, 50) is False

    assert ma_pullback(low=100, close=102, mid=101) is True
    assert ma_pullback(low=102, close=100, mid=101) is False

    # разжатие: в стекинге «игла» = mid - slow
    assert ma_spread(102, 100, 98, atr=10, min_spread=0.1) is True   # needle 2 >= 1
    assert ma_spread(102, 100, 98, atr=25, min_spread=0.1) is False  # needle 2 < 2.5
    assert ma_spread(102, 100, 98, atr=0, min_spread=0.1) is False   # нет ATR — нельзя судить


def test_strategy_defaults_per_ticker():
    from trading_moex.app.strategies import strategy_defaults

    base = strategy_defaults("pinbar", None)
    # per-ticker оверрайд применяется только к SBER
    sber = strategy_defaults("pinbar", "SBER")
    assert sber["wick_ratio"] == 3.5
    assert sber["atr_stop_mult"] == 5.0
    assert sber["rr_ratio"] == 2.5
    assert sber["bull_frac"] == 0.5
    assert sber["profile_bins"] == 50
    # глобальные и остальные тикеры не меняются
    assert strategy_defaults("pinbar", "YDEX") == base
    assert strategy_defaults("pinbar", "LKOH") == base
    # оверрайд частичный: остальные ключи берутся из глобальных дефолтов
    assert sber["atr_period"] == base["atr_period"]
    assert sber["risk_pct"] == base["risk_pct"]


def test_volume_profile_zones():
    from trading_moex.app.signals import volume_profile_zones

    # высокий объём в верхнем кластере -> одна зона вверху
    highs = [102, 102, 92, 92, 82, 82] + [102, 92, 82] * 3
    lows = [100, 100, 90, 90, 80, 80] + [100, 90, 80] * 3
    closes = [101, 101, 91, 91, 81, 81] + [101, 91, 81] * 3
    vols = [1000, 900, 200, 200, 200, 200] + [100, 100, 100] * 3
    zones = volume_profile_zones(highs, lows, closes, vols, bins=10, mult=1.3)
    # зоны идут по возрастанию цены, у каждой (bottom, top)
    assert zones == sorted(zones)
    for b, t in zones:
        assert b < t
    # верхний (самый дорогой) кластер должен быть зоной с самым большим боком
    assert zones[-1][1] > 100.0

    # NaN-бары (тёплый период) — пустой список, без исключения
    assert volume_profile_zones(
        [float("nan")] * 3, [float("nan")] * 3, [float("nan")] * 3, [float("nan")] * 3,
        bins=10, mult=1.3,
    ) == []


def test_scale_plan():
    from trading_moex.app.signals import scale_plan

    levels, avg, stop, target = scale_plan(ref=100.0, atr=2.0, parts=3, dist=1.0, stop_dist=4.0, rr=3.0)
    assert levels == [98.0, 96.0]              # 100 - 1*2, 100 - 2*2
    assert abs(avg - 98.0) < 1e-9              # 100 - 1*2 = 98
    assert abs(stop - 92.0) < 1e-9             # 100 - 2*2 - 4 = 92
    assert abs(target - 110.0) < 1e-9          # 98 + 4*3 = 110
    # риск на акцию = стоп-дистанция + (parts-1)/2 шагов ATR
    assert abs((avg - stop) - (4.0 + 1.0 * 2.0)) < 1e-9


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


def test_backtest_smoke_with_scale_in_out():
    import numpy as np
    import pandas as pd

    from trading_moex.app.backtest import run_backtest
    from trading_moex.app.strategies import STRATEGIES

    n = 400
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = np.linspace(100, 130, n) + np.sin(np.arange(n) / 7) * 3
    df = pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1000.0},
        index=idx,
    )
    for key in ("pinbar", "engulfing"):
        params = {p["key"]: p["default"] for p in STRATEGIES[key]["params"]}
        params["scale_in"] = 1
        params["scale_out"] = 1
        res = run_backtest(df, STRATEGIES[key]["cls"], params, cash=100_000, commission=0.0005)
        assert "profit_factor" in res
        assert "trades_total" in res


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


# ── Скачивание данных тикера с MOEX ──────────────────────────────────────────

def test_data_to_csv():
    from trading_moex.app.data import to_csv

    idx = pd.date_range("2025-01-01", periods=3, freq="D", name="datetime")
    df = pd.DataFrame(
        {
            "open": [1.0, 2.0, 3.0],
            "high": [1.5, 2.5, 3.5],
            "low": [0.9, 1.9, 2.9],
            "close": [1.2, 2.2, 3.2],
            "volume": [10, 20, 30],
        },
        index=idx,
    )
    csv_text = to_csv(df)
    assert csv_text.splitlines()[0] == "datetime,open,high,low,close,volume"
    assert "2025-01-01" in csv_text
    assert "3.5" in csv_text


# ── MOEX данные: ресэмпл и пустые ответы ─────────────────────────────────────

def test_resample_candles_1min_to_15min():
    from trading_moex.app.data import _resample_candles

    t0 = pd.Timestamp("2026-07-01 07:00:00")
    rows = []
    for i in range(45):
        ts = t0 + pd.Timedelta(minutes=i)
        rows.append(
            {
                "begin": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "end": (ts + pd.Timedelta(seconds=59)).strftime("%Y-%m-%d %H:%M:%S"),
                "open": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                "close": 100.5 + i,
                "volume": 10,
                "value": 1000.0,
            }
        )
    out = _resample_candles(pd.DataFrame(rows), "15min")
    assert len(out) == 3
    first = out.iloc[0]
    assert first["begin"] == t0
    assert first["open"] == 100.0
    assert first["close"] == 114.5  # close последней минуты бакета (i=14)
    assert first["high"] == 115.0
    assert first["low"] == 99.0
    assert first["volume"] == 150
    assert out.iloc[-1]["begin"] == t0 + pd.Timedelta(minutes=30)


def test_resample_candles_skips_empty_buckets():
    from trading_moex.app.data import _resample_candles

    t0 = pd.Timestamp("2026-07-01 07:00:00")
    rows = [
        {
            "begin": t0.strftime("%Y-%m-%d %H:%M:%S"),
            "end": (t0 + pd.Timedelta(seconds=59)).strftime("%Y-%m-%d %H:%M:%S"),
            "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
            "volume": 10, "value": 1000.0,
        },
        {
            # следующая свеча — через час (обеденный перерыв MOEX): пустые бакеты между ними
            "begin": (t0 + pd.Timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "end": (t0 + pd.Timedelta(hours=1, seconds=59)).strftime("%Y-%m-%d %H:%M:%S"),
            "open": 110.0, "high": 111.0, "low": 109.0, "close": 110.5,
            "volume": 10, "value": 1000.0,
        },
    ]
    out = _resample_candles(pd.DataFrame(rows), "15min")
    assert len(out) == 2
    assert (out["volume"] == 10).all()


def test_fetch_history_empty_moex_raises_clear_error(tmp_path, monkeypatch):
    from datetime import date as d

    from trading_moex.app import config, data as moex_data, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    monkeypatch.setattr(config, "CANDLE_CACHE_DIR", tmp_path / "candles")
    storage.init_db()
    monkeypatch.setattr(moex_data, "_fetch_raw", lambda *a, **k: [])
    with pytest.raises(ValueError, match="(?s)не вернул данных.*делистингована.*YDEX"):
        moex_data.fetch_history("YNDX", "15min", d(2025, 8, 15), d(2026, 8, 15), use_cache=False)


def test_fetch_history_empty_unknown_ticker_without_hint(tmp_path, monkeypatch):
    from datetime import date as d

    from trading_moex.app import config, data as moex_data, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    monkeypatch.setattr(config, "CANDLE_CACHE_DIR", tmp_path / "candles")
    storage.init_db()
    monkeypatch.setattr(moex_data, "_fetch_raw", lambda *a, **k: [])
    with pytest.raises(ValueError) as exc:
        moex_data.fetch_history("SBER", "15min", d(2025, 8, 15), d(2026, 8, 15), use_cache=False)
    assert "YDEX" not in str(exc.value)


def test_fetch_history_resamples_non_native_period(tmp_path, monkeypatch):
    from datetime import date as d

    from trading_moex.app import config, data as moex_data, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    monkeypatch.setattr(config, "CANDLE_CACHE_DIR", tmp_path / "candles")
    storage.init_db()

    t0 = pd.Timestamp("2026-07-01 07:00:00")
    rows = []
    for i in range(30):
        ts = t0 + pd.Timedelta(minutes=i)
        rows.append(
            {
                "begin": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "end": (ts + pd.Timedelta(seconds=59)).strftime("%Y-%m-%d %H:%M:%S"),
                "open": 100.0 + i, "high": 101.0 + i, "low": 99.0 + i,
                "close": 100.5 + i, "volume": 10, "value": 1000.0,
            }
        )
    requested_periods = []
    monkeypatch.setattr(
        moex_data,
        "_fetch_raw",
        lambda ticker, period, start, end: (requested_periods.append(period), rows)[1],
    )

    df = moex_data.fetch_history("SBER", "15min", d(2026, 7, 1), d(2026, 7, 2), use_cache=False)
    assert requested_periods == ["1min"]  # качаем нативные 1min, ресэмплим сами
    assert len(df) == 2
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index[0] == t0  # datetime-индекс для backtrader

    # нативный период идёт как есть, без ресэмпла
    requested_periods.clear()
    df = moex_data.fetch_history("SBER", "1day", d(2026, 7, 1), d(2026, 7, 2), use_cache=False)
    assert requested_periods == ["1D"]
    assert len(df) == len(rows)

    # 30min тоже ненативный — качаем 1min, ресэмплим в 1 бакет 30 минут
    requested_periods.clear()
    df = moex_data.fetch_history("SBER", "30min", d(2026, 7, 1), d(2026, 7, 2), use_cache=False)
    assert requested_periods == ["1min"]
    assert len(df) == 1
    assert df.index[0] == t0


# ── Синхронизация данных с базой ─────────────────────────────────────────────

def _mock_trader_config(tmp_path, monkeypatch):
    from trading_moex.app import config, storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    monkeypatch.setattr(config, "CANDLE_CACHE_DIR", tmp_path / "candles")
    storage.init_db()
    return storage


def test_storage_candles_upsert_and_range(tmp_path, monkeypatch):
    from datetime import date

    storage = _mock_trader_config(tmp_path, monkeypatch)

    df = pd.DataFrame(
        {
            "begin": ["2026-07-01 10:00:00", "2026-07-01 10:15:00", "2026-07-02 10:00:00"],
            "open": [1, 2, 3], "high": [1.5, 2.5, 3.5], "low": [0.5, 1.5, 2.5],
            "close": [1.2, 2.2, 3.2], "volume": [10, 20, 30],
        }
    )
    assert storage.save_candles("SBER", "15min", df) == 3
    assert storage.candle_count("SBER", "15min") == 3
    assert storage.first_candle_time("SBER", "15min") == "2026-07-01 10:00:00"
    assert storage.last_candle_time("SBER", "15min") == "2026-07-02 10:00:00"

    # upsert: тот же begin перезаписывается, дублей нет
    upd = df.copy()
    upd.loc[0, "close"] = 9.9
    storage.save_candles("SBER", "15min", upd)
    assert storage.candle_count("SBER", "15min") == 3

    # диапазон [start, end] включает весь день end
    day1 = storage.get_candles("SBER", "15min", start=date(2026, 7, 1), end=date(2026, 7, 1))
    assert len(day1) == 2
    assert day1.iloc[0]["close"] == 9.9
    assert storage.candle_count("LKOH", "15min") == 0  # периоды изолированы


def test_fetch_history_incremental_tail_only(tmp_path, monkeypatch):
    """Если в базе есть данные до 10.07 — качается только хвост после этой даты."""
    from datetime import date as d

    from trading_moex.app import data as moex_data

    storage = _mock_trader_config(tmp_path, monkeypatch)

    existing = pd.DataFrame(
        {
            "begin": ["2026-07-01", "2026-07-02", "2026-07-10"],
            "open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101],
            "close": [100.5, 101.5, 102.5], "volume": [10, 10, 10],
        }
    )
    storage.save_candles("SBER", "1day", existing)

    calls = []
    new_rows = [
        {"begin": "2026-07-11", "end": "2026-07-11", "open": 110, "high": 111, "low": 109,
         "close": 110.5, "volume": 10, "value": 1000.0},
        {"begin": "2026-07-12", "end": "2026-07-12", "open": 111, "high": 112, "low": 110,
         "close": 111.5, "volume": 10, "value": 1000.0},
    ]

    def fake_fetch_raw(ticker, period, start, end):
        calls.append((ticker, period, start, end))
        return new_rows

    monkeypatch.setattr(moex_data, "_fetch_raw", fake_fetch_raw)

    df = moex_data.fetch_history("SBER", "1day", d(2026, 7, 1), d(2026, 7, 15), use_cache=True)
    assert len(calls) == 1
    _, period, start, _ = calls[0]
    assert period == "1D"
    # старт загрузки — ровно после последней сохранённой свечи (10.07 00:00:00 + 1с)
    assert start == pd.Timestamp("2026-07-10") + pd.Timedelta(seconds=1)
    # результат: существующие + новые, отсортированные
    assert len(df) == 5
    assert df.index[0] == pd.Timestamp("2026-07-01")
    assert df.index[-1] == pd.Timestamp("2026-07-12")
    assert storage.candle_count("SBER", "1day") == 5


def test_fetch_history_backfill_before_stored(tmp_path, monkeypatch):
    """Запрошенный диапазон раньше первой сохранённой свечи — докачивается бэкфилл."""
    from datetime import date as d

    from trading_moex.app import data as moex_data

    storage = _mock_trader_config(tmp_path, monkeypatch)

    existing = pd.DataFrame(
        {
            "begin": ["2026-07-05", "2026-07-10"],
            "open": [102, 105], "high": [103, 106], "low": [101, 104],
            "close": [102.5, 105.5], "volume": [10, 10],
        }
    )
    storage.save_candles("SBER", "1day", existing)

    calls = []
    backfill_rows = [
        {"begin": "2026-07-01", "end": "2026-07-01", "open": 100, "high": 101, "low": 99,
         "close": 100.5, "volume": 10, "value": 1000.0},
        {"begin": "2026-07-03", "end": "2026-07-03", "open": 101, "high": 102, "low": 100,
         "close": 101.5, "volume": 10, "value": 1000.0},
    ]

    def fake_fetch_raw(ticker, period, start, end):
        calls.append((start, end))
        if start < pd.Timestamp("2026-07-05"):
            return backfill_rows
        return []  # хвоста нет

    monkeypatch.setattr(moex_data, "_fetch_raw", fake_fetch_raw)

    df = moex_data.fetch_history("SBER", "1day", d(2026, 7, 1), d(2026, 7, 15), use_cache=True)
    # два окна: хвост (10.07+, пусто) и бэкфилл [01.07, 05.07)
    assert len(calls) == 2
    starts = sorted((start for start, _ in calls))
    assert starts[0] == pd.Timestamp("2026-07-01")  # бэкфилл
    assert starts[1] == pd.Timestamp("2026-07-10") + pd.Timedelta(seconds=1)  # хвост
    backfill_start, backfill_end = min(calls, key=lambda c: c[0])
    assert backfill_end == pd.Timestamp("2026-07-05")  # до первой сохранённой свечи
    assert len(df) == 4  # 2 бэкфилла + 2 существующих
    assert df.index[0] == pd.Timestamp("2026-07-01")
    assert storage.candle_count("SBER", "1day") == 4


def test_fetch_history_no_new_data_keeps_db(tmp_path, monkeypatch):
    """Хвост пуст (данные уже актуальны) — база не меняется, результат из базы."""
    from datetime import date as d

    from trading_moex.app import data as moex_data

    storage = _mock_trader_config(tmp_path, monkeypatch)

    existing = pd.DataFrame(
        {
            "begin": ["2026-07-01", "2026-07-02"],
            "open": [100, 101], "high": [101, 102], "low": [99, 100],
            "close": [100.5, 101.5], "volume": [10, 10],
        }
    )
    storage.save_candles("SBER", "1day", existing)

    calls = []
    monkeypatch.setattr(moex_data, "_fetch_raw", lambda *a, **k: (calls.append(a), [])[1])

    df = moex_data.fetch_history("SBER", "1day", d(2026, 7, 1), d(2026, 7, 2), use_cache=True)
    assert calls  # хвост запрашивался
    assert len(df) == 2
    assert storage.candle_count("SBER", "1day") == 2


def test_fetch_history_use_cache_false_reloads_full_range(tmp_path, monkeypatch):
    """use_cache=False — полная перезагрузка диапазона, несмотря на базу."""
    from datetime import date as d

    from trading_moex.app import data as moex_data

    storage = _mock_trader_config(tmp_path, monkeypatch)

    existing = pd.DataFrame(
        {
            "begin": ["2026-07-01"],
            "open": [100], "high": [101], "low": [99],
            "close": [100.5], "volume": [10],
        }
    )
    storage.save_candles("SBER", "1day", existing)

    calls = []
    rows = [
        {"begin": "2026-07-01", "end": "2026-07-01", "open": 200, "high": 201, "low": 199,
         "close": 200.5, "volume": 20, "value": 2000.0},
        {"begin": "2026-07-02", "end": "2026-07-02", "open": 201, "high": 202, "low": 200,
         "close": 201.5, "volume": 20, "value": 2000.0},
    ]
    monkeypatch.setattr(moex_data, "_fetch_raw", lambda *a, **k: (calls.append(a), rows)[1])

    df = moex_data.fetch_history("SBER", "1day", d(2026, 7, 1), d(2026, 7, 2), use_cache=False)
    assert len(calls) == 1
    _, period, start, _ = calls[0]
    assert period == "1D"
    assert start == pd.Timestamp("2026-07-01")  # полный диапазон с начала
    assert len(df) == 2
    assert df["open"].iloc[0] == 200  # перезаписано свежими данными


def test_fetch_history_progress_callback(tmp_path, monkeypatch):
    """С колбэком прогресса окна дробятся на чанки и процент идёт равными шагами."""
    from datetime import date as d

    from trading_moex.app import data as moex_data

    _mock_trader_config(tmp_path, monkeypatch)

    calls = []

    def fake_fetch_raw(ticker, period, start, end):
        calls.append(start)
        return [
            {
                "begin": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end": start.strftime("%Y-%m-%d %H:%M:%S"),
                "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                "volume": 10, "value": 1000.0,
            }
        ]

    monkeypatch.setattr(moex_data, "_fetch_raw", fake_fetch_raw)

    progress = []
    df = moex_data.fetch_history(
        "SBER", "1min", d(2026, 6, 1), d(2026, 6, 22), use_cache=False,
        progress=progress.append,
    )
    assert progress == [25, 50, 75, 100]  # 4 окна по 7 дней, монотонно до 100
    assert len(calls) == 4
    assert len(df) == 4


async def test_backtest_job_flow(tmp_path, monkeypatch):
    """Job-поток бэктеста: start -> status(done) -> редирект на страницу результата."""
    from aiohttp.test_utils import TestClient, TestServer

    from trading_moex.app import config, data as moex_data, settings, storage
    from trading_moex.app.web import app as web_app

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()
    settings.set("TRADER_WEB_PASSWORD", "testpass")

    idx = pd.date_range("2025-06-01", periods=100, freq="D")
    close = np.linspace(100, 110, 100)
    df = pd.DataFrame(
        {"open": close, "high": close + 1.0, "low": close - 1.0, "close": close, "volume": 1000.0},
        index=idx,
    )
    df.index.name = "datetime"
    monkeypatch.setattr(moex_data, "fetch_history", lambda *a, **k: df)
    monkeypatch.setattr(
        web_app, "run_backtest",
        lambda *a, **k: {"total_return_pct": 5.5, "n_bars": 100, "trades": [], "equity_curve": []},
    )

    app = web_app.create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        # без авторизации — редирект на логин
        resp = await client.post("/backtest/run", data={"ticker": "SBER"}, allow_redirects=False)
        assert resp.status == 302

        await client.post("/login", data={"password": "testpass"}, allow_redirects=False)

        resp = await client.post(
            "/backtest/run",
            data={
                "ticker": "SBER", "period": "1day", "strategy": "sma_cross",
                "start": "2025-06-01", "end": "2025-09-01", "cash": "100000", "commission": "0.0005",
            },
        )
        assert resp.status == 200
        job_id = (await resp.json())["job_id"]

        for _ in range(100):
            status = await client.get(f"/backtest/status?job_id={job_id}")
            data = await status.json()
            if data["state"] != "running":
                break
            await asyncio.sleep(0.01)
        assert data["state"] == "done"
        assert data["percent"] == 100

        resp = await client.get(f"/backtest/result?job_id={job_id}", allow_redirects=False)
        assert resp.status == 302
        assert resp.headers["Location"] == "/backtest/1"

        run = storage.get_run(1)
        assert run is not None and run["status"] == "done"
        assert run["result"]["total_return_pct"] == 5.5

        # результат редиректит один раз
        resp = await client.get(f"/backtest/result?job_id={job_id}", allow_redirects=False)
        assert resp.status == 200  # задача уже удалена -> страница «Задача не найдена»
        assert "Задача не найдена" in await resp.text()
    finally:
        await client.close()


async def test_backtest_job_error_and_validation(tmp_path, monkeypatch):
    """Ошибка бэктеста -> state=error; невалидные данные -> 400."""
    from aiohttp.test_utils import TestClient, TestServer

    from trading_moex.app import config, data as moex_data, settings, storage
    from trading_moex.app.web import app as web_app

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    storage.init_db()
    settings.set("TRADER_WEB_PASSWORD", "testpass")

    def fake_fetch_history(ticker, period, start, end, use_cache=True, progress=None):
        raise ValueError("MOEX не вернул данных по TEST")

    monkeypatch.setattr(moex_data, "fetch_history", fake_fetch_history)

    app = web_app.create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        await client.post("/login", data={"password": "testpass"}, allow_redirects=False)

        # старт раньше конца — валидация
        resp = await client.post(
            "/backtest/run",
            data={"ticker": "SBER", "start": "2025-06-10", "end": "2025-06-01"},
        )
        assert resp.status == 400

        # некорректный капитал
        resp = await client.post(
            "/backtest/run",
            data={"ticker": "SBER", "cash": "abc"},
        )
        assert resp.status == 400

        resp = await client.post(
            "/backtest/run",
            data={
                "ticker": "SBER", "period": "1day", "strategy": "sma_cross",
                "start": "2025-06-01", "end": "2025-09-01", "cash": "100000", "commission": "0.0005",
            },
        )
        assert resp.status == 200
        job_id = (await resp.json())["job_id"]

        for _ in range(100):
            status = await client.get(f"/backtest/status?job_id={job_id}")
            data = await status.json()
            if data["state"] != "running":
                break
            await asyncio.sleep(0.01)
        assert data["state"] == "error"
        assert "MOEX не вернул данных" in (data["error"] or "")

        resp = await client.get(f"/backtest/result?job_id={job_id}")
        assert resp.status == 200
        assert "Ошибка бэктеста" in await resp.text()

        # неизвестный job
        resp = await client.get(f"/backtest/status?job_id=nope")
        assert resp.status == 404
    finally:
        await client.close()


def test_index_dividends_vectorized():
    """_index_dividends handles missing buy_before and invalid rows without crashing."""
    from trading_moex.app.strategies import ROEPortfolioStrategy

    strategy = type("_MockStrat", (), {"_index_dividends": ROEPortfolioStrategy._index_dividends})()

    df = pd.DataFrame({
        "date": ["2025-06-01", "2025-09-01", "2025-12-01"],
        "dividend": [10.5, 0.0, 20.0],
        "buy_before": ["2025-05-30", "2025-08-29", "2025-11-28"],
    })
    result = strategy._index_dividends(df)
    assert len(result) == 3
    assert result[pd.Timestamp("2025-06-01")] == (10.5, pd.Timestamp("2025-05-30"))
    assert result[pd.Timestamp("2025-12-01")] == (20.0, pd.Timestamp("2025-11-28"))

    # missing buy_before → (amount, None), no crash
    df_missing = pd.DataFrame({
        "date": ["2025-06-01"],
        "dividend": [5.0],
    })
    result2 = strategy._index_dividends(df_missing)
    assert len(result2) == 1
    ts, (amount, bb) = next(iter(result2.items()))
    assert amount == 5.0
    assert bb is None

    # invalid date and NaN dividend → row dropped silently
    df_bad = pd.DataFrame({
        "date": ["not-a-date", "2025-06-01"],
        "dividend": [float("nan"), 3.0],
        "buy_before": ["2025-05-30", "2025-05-30"],
    })
    result3 = strategy._index_dividends(df_bad)
    assert len(result3) == 1


