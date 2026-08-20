"""Запуск бэктеста на backtrader и расчёт метрик."""

import logging

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd

logger = logging.getLogger("moex_trader.backtest")


class _EquityCurve(bt.Analyzer):
    """Записывает стоимость портфеля и вложенный в позиции капитал на каждом баре.

    ``curve``: [[ts, total_value], ...]; ``invested_curve``: [[ts, positions_value], ...].
    """

    def start(self):
        self.curve = []
        self.invested_curve = []

    def next(self):
        ts = self.strategy.data.datetime.datetime(0).isoformat()
        self.curve.append([ts, round(float(self.strategy.broker.getvalue()), 2)])
        invested = 0.0
        for d in self.strategy.datas:
            pos = self.strategy.getposition(d)
            if pos.size:
                invested += float(pos.size) * float(d.close[0])
        self.invested_curve.append([ts, round(invested, 2)])


def _setup_cerebro(strategy_cls, params, cash: float, commission: float, extra_params: dict | None = None) -> bt.Cerebro:
    cerebro = bt.Cerebro()
    feed_params = {**params, **(extra_params or {})}
    cerebro.addstrategy(strategy_cls, **feed_params)
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(btanalyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(_EquityCurve, _name="equity")
    return cerebro


def run_backtest(
    df: pd.DataFrame,
    strategy_cls,
    params: dict,
    cash: float = 100_000.0,
    commission: float = 0.0005,
) -> dict:
    """Выполнить бэктест на переданных OHLCV-данных (datetime-индекс).

    Блокирующий вызов — запускать в отдельном потоке.
    """
    cerebro = _setup_cerebro(strategy_cls, params, cash, commission)
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    strat = cerebro.run(runonce=False)[0]
    return _collect_metrics(cerebro, strat, cash, len(df))


def run_portfolio_backtest(
    data_map: dict[str, pd.DataFrame],
    strategy_cls,
    params: dict,
    fundamentals: dict[str, pd.DataFrame] | None = None,
    cash: float = 100_000.0,
    commission: float = 0.0005,
    dividends: dict[str, pd.DataFrame] | None = None,
) -> dict:
    """Портфельный бэктест на нескольких тикерах (по одному data-фиду на тикер).

    ``data_map``: {ticker: OHLCV DataFrame с datetime-индексом};
    ``fundamentals``: {ticker: DataFrame(date, roe, book_value_per_share, ...)}
    передаётся в стратегию параметром ``fundamentals`` (для ROE-портфеля);
    ``dividends``: {ticker: DataFrame(date, dividend)} — дивиденды на отсечке,
    начисляются стратегией за открытые позиции.
    Блокирующий вызов — запускать в отдельном потоке.
    """
    extra = {}
    if fundamentals is not None:
        extra["fundamentals"] = fundamentals
    if dividends is not None:
        extra["dividends"] = dividends
    cerebro = _setup_cerebro(strategy_cls, params, cash, commission, extra_params=extra or None)
    n_bars = 0
    for ticker, df in data_map.items():
        feed = bt.feeds.PandasData(dataname=df)
        feed._name = ticker
        cerebro.adddata(feed)
        n_bars = max(n_bars, len(df))
    strat = cerebro.run(runonce=False)[0]
    return _collect_metrics(cerebro, strat, cash, n_bars)


def _collect_metrics(cerebro, strat, cash: float, n_bars: int) -> dict:
    """Общие анализеры и метрики результата бэктеста."""
    initial = float(cash)
    final = float(strat.broker.getvalue())
    total_return = (final / initial - 1) * 100 if initial else 0.0

    sharpe_val = _extract_sharpe(strat.analyzers.sharpe.get_analysis())

    dd = strat.analyzers.drawdown.get_analysis()
    max_dd = float((dd.get("max") or {}).get("drawdown", 0.0) or 0.0)

    ta = strat.analyzers.trades.get_analysis()
    total_trades = int((ta.get("total") or {}).get("closed", 0))
    won = int((ta.get("won") or {}).get("total", 0))
    lost = int((ta.get("lost") or {}).get("total", 0))
    win_rate = round(won / total_trades * 100, 2) if total_trades else 0.0

    won_pnl = float((ta.get("won") or {}).get("pnl", {}).get("total", 0.0) or 0.0)
    lost_pnl = float((ta.get("lost") or {}).get("pnl", {}).get("total", 0.0) or 0.0)
    avg_win = float((ta.get("won") or {}).get("pnl", {}).get("average", 0.0) or 0.0)
    avg_loss = float((ta.get("lost") or {}).get("pnl", {}).get("average", 0.0) or 0.0)
    profit_factor = round(won_pnl / abs(lost_pnl), 2) if lost_pnl else (None if won_pnl else 0.0)
    expectancy = (win_rate / 100) * avg_win - (1 - win_rate / 100) * abs(avg_loss)
    longest_win_streak = int((ta.get("streak") or {}).get("longest", {}).get("won", 0))
    longest_loss_streak = int((ta.get("streak") or {}).get("longest", {}).get("lost", 0))

    equity = strat.analyzers.equity.curve or [[str(strat.data.datetime.datetime(0).isoformat()), round(initial, 2)]]
    trades = getattr(strat, "recorded_trades", [])[-100:]
    dividends_income = getattr(strat, "_dividends_income", 0.0)

    return {
        "initial_cash": initial,
        "final_value": round(final, 2),
        "total_return_pct": round(total_return, 2),
        "sharpe": sharpe_val,
        "max_drawdown_pct": round(max_dd, 2),
        "trades_total": total_trades,
        "trades_won": won,
        "trades_lost": lost,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "n_bars": int(n_bars),
        "equity_curve": equity,
        "invested_curve": getattr(strat.analyzers.equity, "invested_curve", []),
        "trades": trades,
        "dividends_income": round(dividends_income, 2),
    }


def _extract_sharpe(analysis: dict) -> float | None:
    if not isinstance(analysis, dict):
        return None
    for value in analysis.values():
        if isinstance(value, dict):
            value = value.get("sharperatio")
        if isinstance(value, (int, float)) and value == value:  # не NaN
            return round(float(value), 3)
    return None
