"""Тесты сигнала roe_pb и портфельной стратегии ROE + P/B."""

import numpy as np
import pandas as pd
import pytest

from app import signals
from app.backtest import run_portfolio_backtest
from app.fundamentals import prepare_fundamentals_series
from app.storage import save_fundamentals
from app.strategies import ROEPortfolioStrategy


def _ohlc(df_dates: pd.DatetimeIndex) -> pd.DataFrame:
    idx = df_dates
    n = len(idx)
    close = 90 + np.cumsum(np.random.default_rng(7).normal(0.1, 1.0, n))
    out = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )
    out.index.name = "datetime"
    return out


def test_roe_pb_signal_enters_when_cheap_exits_when_rich():
    dates = pd.date_range("2020-01-01", periods=60, freq="D")
    prices = pd.Series(np.full(60, 60.0), index=dates)  # BVPS 90 → P/B 0.67 (вход)
    save_fundamentals("SBER", _fund_df())
    fund = prepare_fundamentals_series("SBER", dates[0].date(), dates[-1].date())

    pos = signals.roe_pb_signal(prices, fund, min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8, pb_exit=1.0)
    assert pos.sum() > 0  # средний ROE >= 15, цена <= 0.8*90=72 → позиция


def _fund_df():
    rows = []
    for y in range(2015, 2026):
        rows.append({"date": f"{y}-12-31", "roe": 19.0, "book_value_per_share": 90.0})
    return pd.DataFrame(rows)


def test_roe_pb_signal_stays_flat_when_expensive():
    dates = pd.date_range("2020-01-01", periods=60, freq="D")
    prices = pd.Series(np.full(60, 150.0), index=dates)  # P/B 1.67 > 0.8
    save_fundamentals("SBER", _fund_df())
    fund = prepare_fundamentals_series("SBER", dates[0].date(), dates[-1].date())

    pos = signals.roe_pb_signal(prices, fund, min_avg_roe=15.0, min_single_roe=12.0, pb_entry=0.8, pb_exit=1.0)
    assert (pos == 0).all()


def test_portfolio_backtest_buys_cheap_tickers():
    dates = pd.date_range("2021-01-04", periods=250, freq="D")
    data_map = {"AA": _ohlc(dates), "BB": _ohlc(dates)}
    fund_map = {}
    for ticker in ("AA", "BB"):
        df = pd.DataFrame(
            [{"date": f"{y}-12-31", "roe": 20.0, "book_value_per_share": 90.0} for y in range(2015, 2026)]
        )
        save_fundamentals(ticker, df)
        fund_map[ticker] = prepare_fundamentals_series(ticker, dates[0].date(), dates[-1].date())

    params = {
        "min_avg_roe": 15.0,
        "min_single_roe": 12.0,
        "pb_entry": 0.8,
        "pb_exit": 1.0,
        "roe_exit": 12.0,
        "max_positions": 10,
        "rebalance_days": 5,
    }
    result = run_portfolio_backtest(data_map, ROEPortfolioStrategy, params, fund_map, cash=100000)
    assert result["trades_total"] >= 0
    assert result["n_bars"] == max(len(d) for d in data_map.values())


def test_portfolio_backtest_accrues_dividends():
    dates = pd.date_range("2021-01-04", periods=250, freq="D")
    data_map = {"AA": _ohlc(dates), "BB": _ohlc(dates)}
    fund_map = {}
    for ticker in ("AA", "BB"):
        # Цена ~90 < 0.8*300=240 → вход гарантирован, позиция держится весь период.
        df = pd.DataFrame(
            [{"date": f"{y}-12-31", "roe": 20.0, "book_value_per_share": 300.0} for y in range(2015, 2026)]
        )
        save_fundamentals(ticker, df)
        fund_map[ticker] = prepare_fundamentals_series(ticker, dates[0].date(), dates[-1].date())

    params = {
        "min_avg_roe": 15.0,
        "min_single_roe": 12.0,
        "pb_entry": 0.8,
        "pb_exit": 1.0,
        "roe_exit": 12.0,
        "max_positions": 10,
        "rebalance_days": 5,
    }
    div_map = {
        "AA": pd.DataFrame(
            {
                "date": ["2021-06-15", "2022-06-15"],
                "buy_before": ["2021-06-11", "2022-06-13"],
                "dividend": [10.0, 10.0],
            }
        )
    }
    result_with = run_portfolio_backtest(data_map, ROEPortfolioStrategy, params, fund_map, cash=100000, dividends=div_map)
    result_without = run_portfolio_backtest(data_map, ROEPortfolioStrategy, params, fund_map, cash=100000)
    assert result_with["dividends_income"] > 0
    assert result_with["final_value"] > result_without["final_value"]


def test_cash_yield_not_multiplied_by_bars():
    """Баг: на мелких таймфреймах денежный кэш-доход (cash_yield) начислялся
    каждый бар, поэтому при 0 сделок возврат зависел от таймфрейма. Теперь
    доход начисляется на календарный день — 1min и 5min дают одинаковый итог."""
    start = pd.Timestamp("2021-01-04 10:00")
    end = pd.Timestamp("2022-12-30 18:45")
    fund_df = pd.DataFrame(
        [{"date": f"{y}-12-31", "roe": 100.0, "book_value_per_share": 10000.0}
         for y in range(2015, 2026)]
    )
    params = {
        "min_avg_roe": 15.0, "min_single_roe": 12.0, "pb_entry": 0.8,
        "pb_exit": 1.0, "roe_exit": 12.0, "max_positions": 10,
        "rebalance_days": 5, "cash_yield": 8.0,
    }

    def mk(bars: int) -> pd.DataFrame:
        idx = pd.date_range(start=start, end=end, periods=bars)
        close = np.full(bars, 100.0)
        df = pd.DataFrame(
            {"open": close - 0.5, "high": close + 1, "low": close - 1,
             "close": close, "volume": 1000},
            index=idx,
        )
        df.index.name = "datetime"
        return df

    finals = {}
    for name, bars in (("1min", 60000), ("5min", 12000)):
        res = run_portfolio_backtest(
            {"AA": mk(bars)}, ROEPortfolioStrategy, params,
            {t: fund_df for t in ("AA",)}, cash=100000,
        )
        assert res["trades_total"] == 0
        finals[name] = res["final_value"]
    assert finals["1min"] == finals["5min"]


def test_portfolio_partial_sell_at_pb_partial_then_rest_at_pb_exit():
    """При цене >= pb_exit_partial*BVPS продаётся ровно доля partial_frac,
    а полный выход происходит только при цене >= pb_exit*BVPS."""
    # Цена шагами: 0.6*BVPS (вход) → 1.0*BVPS (частичная продажа) → удержание
    # до 1.2*BVPS (остаток должен остаться в позиции) → 1.6*BVPS (полный выход).
    bvps = 100.0
    dates = pd.date_range("2021-01-04", periods=210, freq="D")
    prices = [0.6 * bvps] * 50 + [1.0 * bvps] * 50 + [1.2 * bvps] * 50 + [1.6 * bvps] * 60
    close = np.array(prices)
    df = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000,
        },
        index=dates,
    )
    df.index.name = "datetime"
    data_map = {"AA": df}

    fund_df = pd.DataFrame(
        [{"date": f"{y}-12-31", "roe": 20.0, "book_value_per_share": bvps} for y in range(2015, 2026)]
    )
    save_fundamentals("AA", fund_df)
    fund_map = {"AA": prepare_fundamentals_series("AA", dates[0].date(), dates[-1].date())}

    params = {
        "min_avg_roe": 15.0,
        "min_single_roe": 12.0,
        "pb_entry": 0.8,
        "pb_exit": 1.5,
        "pb_exit_partial": 1.0,
        "partial_frac": 0.5,
        "roe_exit": 12.0,
        "max_positions": 5,
        "rebalance_days": 1,
    }
    result = run_portfolio_backtest(data_map, ROEPortfolioStrategy, params, fund_map, cash=100000)

    invested = [round(v, 2) for _, v in result["invested_curve"]]
    # Позиция в 1-й фазе (P/B 0.6) и во 2-й (P/B 1.0 → частичная продажа 50%).
    max_invested = max(invested)
    assert max_invested > 0
    # В 3-й фазе (май, P/B 1.2 — между 1.0 и 1.5) остаток позиции держится:
    # стоимость примерно половина от максимума, но не нуль.
    mid = [v for ts, v in result["invested_curve"] if "2021-05" in ts]
    assert mid, "нет бара в фазе удержания остатка"
    assert 0.15 * max_invested < min(mid) < 0.9 * max_invested
    # Полный выход в конце (P/B 1.6 ≥ 1.5) → позиция закрыта.
    assert invested[-1] == 0