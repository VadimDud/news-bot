"""Backtrader-стратегии для бэктеста + реестр с описаниями параметров для веб-формы.

Логика повторяет чистые функции из ``signals.py``.
"""

import backtrader as bt


class TradeRecordingStrategy(bt.Strategy):
    """Базовая стратегия, записывающая закрытые сделки для отчёта бэктеста.

    Собственные стратегии наследуйте от этого класса, чтобы в результатах
    бэктеста появлялась таблица сделок.
    """

    def __init__(self):
        self.recorded_trades: list[dict] = []

    def notify_trade(self, trade):
        if trade.isclosed:
            self.recorded_trades.append(
                {
                    "traded": str(bt.num2date(trade.dtclose)),
                    "status": "closed",
                    "pnl": round(float(trade.pnlcomm or 0.0), 2),
                }
            )


class SmaCross(TradeRecordingStrategy):
    params = (("fast", 10), ("slow", 30))

    def __init__(self):
        super().__init__()
        sma_fast = bt.indicators.SMA(self.data.close, period=self.p.fast)
        sma_slow = bt.indicators.SMA(self.data.close, period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(sma_fast, sma_slow)

    def next(self):
        if not self.position:
            if self.crossover[0] > 0:
                self.buy()
        elif self.crossover[0] < 0:
            self.close()


class RSIStrategy(TradeRecordingStrategy):
    params = (("period", 14), ("buy_threshold", 30), ("sell_threshold", 70))

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.period)

    def next(self):
        if not self.position:
            if self.rsi[0] < self.p.buy_threshold:
                self.buy()
        elif self.rsi[0] > self.p.sell_threshold:
            self.close()


class DonchianBreakout(TradeRecordingStrategy):
    params = (("period", 20),)

    def __init__(self):
        super().__init__()
        self.highest = bt.indicators.Highest(self.data.high, period=self.p.period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.p.period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.highest[-1]:
                self.buy()
        elif self.data.close[0] < self.lowest[-1]:
            self.close()


STRATEGIES = {
    "sma_cross": {
        "name": "SMA Crossover",
        "cls": SmaCross,
        "params": [
            {"key": "fast", "label": "Быстрая SMA (период)", "type": "int", "default": 10},
            {"key": "slow", "label": "Медленная SMA (период)", "type": "int", "default": 30},
        ],
    },
    "rsi": {
        "name": "RSI (перепроданность/перекупленность)",
        "cls": RSIStrategy,
        "params": [
            {"key": "period", "label": "Период RSI", "type": "int", "default": 14},
            {"key": "buy_threshold", "label": "Порог покупки (<)", "type": "int", "default": 30},
            {"key": "sell_threshold", "label": "Порог продажи (>)", "type": "int", "default": 70},
        ],
    },
    "donchian": {
        "name": "Donchian Breakout",
        "cls": DonchianBreakout,
        "params": [
            {"key": "period", "label": "Период канала", "type": "int", "default": 20},
        ],
    },
}


def strategy_params_schema(strategy_key: str) -> list[dict]:
    info = STRATEGIES[strategy_key]
    defaults = {p["key"]: p["default"] for p in info["params"]}
    return defaults
