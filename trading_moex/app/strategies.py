"""Backtrader-стратегии для бэктеста + реестр с описаниями параметров для веб-формы.

Логика повторяет чистые функции из ``signals.py``. Риск-менеджмент по мотивам
Price Action: лот от % риска, стоп-лосс по ATR, тейк по R:R, трендовый фильтр EMA.
"""

import backtrader as bt

from . import risk as risk_module
from . import signals as sig


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


# Общие параметры риск-менеджмента: кортеж для backtrader и список для веб-формы
_RISK_PARAMS_TUPLE = (
    ("risk_pct", 1.0),
    ("atr_period", 14),
    ("atr_stop_mult", 1.5),
    ("rr_ratio", 2.0),
    ("trend_period", 0),
)

# bt-параметры Поглощения — подобраны перебором на YDEX (2025-10..2026-02, бычий период):
# широкий стоп 4 ATR, тейк 1:3, вход выше EMA(150) (перебор trend 0/50/100/150/200 —
# 150 лучший: +4.6% на бычьем окне PF 3.1 и +1.5% за весь год PF 1.2; 200 хуже),
# подтверждение объёмом MOEX (объём >= 1.5*SMA40) и доминирование быков.
# SL/TP по объёмному профилю HVN (vol_profile=1): стоп на HVN-поддержке, тейк на
# HVN-сопротивлении. Перебор на YDEX 30min (b 20/40, p 100/200/400, m 1.2/1.5/2.0):
# b=20 p=400 m=1.2 — полный год +4.2% PF 1.9 (базис ATR +1.5% PF 1.2), бычье окно
# +6.8% PF 5.0 (+4.6% PF 3.1); просадка за год 4.8%→2.2%.
_ENGULFING_PARAMS_TUPLE = (
    ("risk_pct", 1.0),
    ("atr_period", 20),
    ("atr_stop_mult", 4.0),
    ("rr_ratio", 3.0),
    ("trend_period", 150),
    ("trend_vwap", 0),
    ("vol_period", 40),
    ("vol_mult", 1.5),
    ("bull_frac", 0.7),
    ("vol_profile", 1),
    ("profile_bins", 20),
    ("profile_period", 400),
    ("profile_mult", 1.2),
)

_RISK_PARAMS = [
    {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
    {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 14},
    {"key": "atr_stop_mult", "label": "Стоп, ATR", "type": "float", "default": 1.5},
    {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 2.0},
    {"key": "trend_period", "label": "Трендовый EMA (0 = выкл)", "type": "int", "default": 0},
]

# Дефолты Поглощения подобраны перебором на YDEX (2025-10..2026-02, бычий период,
# дивиденды 80 руб./год, последняя выплата 28.04.2025 вне окна): широкий стоп 4 ATR,
# тейк 1:3, вход только выше EMA(150), подтверждение объёмом MOEX.
# На 30min: бычье окно +4.6% PF 3.1; за весь год +1.5% PF 1.2 (единственный
# положительный вариант из trend 0/50/100/150/200).
_ENGULFING_PARAMS = [
    {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
    {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 20},
    {"key": "atr_stop_mult", "label": "Стоп, ATR", "type": "float", "default": 4.0},
    {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 3.0},
    {"key": "trend_period", "label": "Трендовый EMA (0 = выкл)", "type": "int", "default": 150},
    {"key": "trend_vwap", "label": "Трендовый по объёму VWMA (1 = да, 0 = нет)", "type": "int", "default": 0},
    {"key": "vol_period", "label": "Объём: период среднего (0 = выкл)", "type": "int", "default": 40},
    {"key": "vol_mult", "label": "Объём: мин. кратность среднего", "type": "float", "default": 1.5},
    {"key": "bull_frac", "label": "Доля быков на свече входа (0 = выкл)", "type": "float", "default": 0.7},
    {"key": "vol_profile", "label": "SL/TP по объёмному профилю HVN (1 = да)", "type": "int", "default": 1},
    {"key": "profile_bins", "label": "Профиль: число бинов цен", "type": "int", "default": 20},
    {"key": "profile_period", "label": "Профиль: окно свечей", "type": "int", "default": 400},
    {"key": "profile_mult", "label": "Профиль: порог объёма (x среднего)", "type": "float", "default": 1.2},
]


class RiskAwareStrategy(TradeRecordingStrategy):
    """Базовая стратегия с риск-менеджментом.

    - лот рассчитывается от ``risk_pct`` риска и дистанции стопа (ATR);
    - при входе ставится стоп-лосс по ATR и тейк-профит с соотношением R:R;
    - длинные позиции открываются только выше EMA ``trend_period`` (0 — выкл).
    """

    def __init__(self):
        super().__init__()
        self.atr_ind = bt.indicators.ATR(self.data, period=int(self.p.atr_period))
        self._sl_order = None
        self._tp_order = None
        if int(self.p.trend_period) > 0:
            if getattr(self.p, "trend_vwap", 0):
                # трендовый индикатор по объёму (VWMA): SUM(price*vol)/SUM(vol)
                vsum = bt.indicators.SumN(
                    self.data.close * self.data.volume, period=int(self.p.trend_period)
                )
                vvol = bt.indicators.SumN(self.data.volume, period=int(self.p.trend_period))
                self.ema_ind = vsum / vvol
            else:
                self.ema_ind = bt.indicators.EMA(self.data.close, period=int(self.p.trend_period))
        else:
            self.ema_ind = None
        if int(getattr(self.p, "vol_period", 0)) > 0:
            self.vol_avg = bt.indicators.SMA(self.data.volume, period=int(self.p.vol_period))
        else:
            self.vol_avg = None

    # ── риск / тренд ─────────────────────────────────────────────────────────

    def _risk_fraction(self) -> float:
        return float(self.p.risk_pct) / 100.0

    def _atr_value(self) -> float:
        val = float(self.atr_ind[0])
        return 0.0 if val != val or val <= 0 else val  # защита от NaN

    def _stop_distance(self) -> float:
        price = float(self.data.close[0])
        if self._use_profile():
            sup, _ = self._profile_levels()
            if sup is not None:
                dist = price - sup
                if dist >= price * 0.002:  # не впритык к цене
                    return dist
        atr_dist = self._atr_value() * float(self.p.atr_stop_mult)
        return max(atr_dist, price * 0.005)  # минимум 0.5% цены

    def _trend_up(self) -> bool:
        if self.ema_ind is None:
            return True
        return float(self.data.close[0]) > float(self.ema_ind[0])

    def _volume_confirms(self) -> bool:
        """Объём свечи паттерна не ниже среднего с множителем (подтверждение сигнала)."""
        if self.vol_avg is None:
            return True
        return sig.volume_confirms(
            float(self.data.volume[0]), float(self.vol_avg[0]),
            float(getattr(self.p, "vol_mult", 0.0)), int(getattr(self.p, "vol_period", 0)),
        )

    def _bulls_dominate(self) -> bool:
        """Доля покупок на свече: close ближе к high, чем к low (быки двигают цену)."""
        return sig.bulls_dominate(
            float(self.data.high[0]), float(self.data.low[0]),
            float(self.data.close[0]), float(getattr(self.p, "bull_frac", 0.0)),
        )

    def _use_profile(self) -> bool:
        return bool(getattr(self.p, "vol_profile", 0))

    def _profile_levels(self) -> tuple[float | None, float | None]:
        """HVN поддержка/сопротивление из объёмного профиля последних свечей."""
        period = max(int(getattr(self.p, "profile_period", 200)), 2)
        bins = max(int(getattr(self.p, "profile_bins", 40)), 5)
        mult = float(getattr(self.p, "profile_mult", 1.5))
        return sig.volume_profile_levels(
            self.data.high.get(ago=-period, size=period),
            self.data.low.get(ago=-period, size=period),
            self.data.close.get(ago=-period, size=period),
            self.data.volume.get(ago=-period, size=period),
            float(self.data.close[0]), bins, mult,
        )

    def _risk_size(self) -> int:
        price = float(self.data.close[0])
        size = risk_module.position_size(
            float(self.broker.getvalue()), self._risk_fraction(), self._stop_distance(), price
        )
        # Не превышать ~95% свободного кэша (защита от гигантских лотов при узком стопе)
        max_by_cash = int(float(self.broker.getcash()) / price * 0.95) if price > 0 else 0
        return max(min(size, max_by_cash), 1) if max_by_cash > 0 else size

    def _open_long(self) -> None:
        if not self._trend_up():
            return
        size = self._risk_size()
        if size <= 0:
            return
        self.buy(size=size)  # SL/TP выставляются в notify_order после исполнения

    def _place_bracket(self) -> None:
        """Выставить стоп-лосс и тейк-профит по открытой позиции.

        Режим ``vol_profile``: стоп на ближайшей HVN-поддержке, тейк на
        ближайшем HVN-сопротивлении (объёмный профиль). Иначе — ATR-стоп и
        тейк по R:R.
        """
        if self.position.size <= 0:
            return
        price = float(self.data.close[0])
        stop_dist = self._stop_distance()
        if self._use_profile():
            sup, res = self._profile_levels()
            stop = sup if sup is not None else price - stop_dist
            min_gap = price * 0.002
            if price - stop < min_gap:
                stop = price - stop_dist
            if res is not None and res > price + min_gap:
                target = res
            else:
                target = price + max(price - stop, min_gap) * float(self.p.rr_ratio)
        else:
            stop = price - stop_dist
            target = price + stop_dist * float(self.p.rr_ratio)
        self._sl_order = self.sell(exectype=bt.Order.Stop, price=stop, size=self.position.size)
        self._tp_order = self.sell(exectype=bt.Order.Limit, price=target, size=self.position.size)

    def notify_order(self, order):
        if order.status == bt.Order.Completed:
            if order.isbuy() and self.position.size > 0:
                # вход исполнился — ставим стоп и тейк
                self._sl_order = None
                self._tp_order = None
                self._place_bracket()
            else:
                # позиция закрыта (стоп/тейк/сигнальный выход) — снять вторую ногу
                for pending in (self._sl_order, self._tp_order):
                    if pending is not None and pending is not order:
                        self.cancel(pending)
                self._sl_order = None
                self._tp_order = None
        elif order.status in (bt.Order.Canceled, bt.Order.Rejected, bt.Order.Margin, bt.Order.Expired):
            if order is self._sl_order:
                self._sl_order = None
            if order is self._tp_order:
                self._tp_order = None

    def _exit(self) -> None:
        for order in (self._sl_order, self._tp_order):
            if order is not None and order.status in (
                bt.Order.Submitted,
                bt.Order.Accepted,
                bt.Order.Partial,
            ):
                self.cancel(order)
        self._sl_order = None
        self._tp_order = None
        if self.position:
            self.close()

    def _trend_exit(self) -> bool:
        """Закрыть позицию при развороте тренда. Возвращает True, если вышли."""
        if self.position and not self._trend_up():
            self._exit()
            return True
        return False


class SmaCross(RiskAwareStrategy):
    params = (("fast", 10), ("slow", 30)) + _RISK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        sma_fast = bt.indicators.SMA(self.data.close, period=int(self.p.fast))
        sma_slow = bt.indicators.SMA(self.data.close, period=int(self.p.slow))
        self.crossover = bt.indicators.CrossOver(sma_fast, sma_slow)

    def next(self):
        if self._trend_exit():
            return
        if not self.position:
            if self.crossover[0] > 0:
                self._open_long()
        elif self.crossover[0] < 0:
            self._exit()


class RSIStrategy(RiskAwareStrategy):
    params = (("period", 14), ("buy_threshold", 30), ("sell_threshold", 70)) + _RISK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=int(self.p.period), safediv=True)

    def next(self):
        if self._trend_exit():
            return
        if not self.position:
            if self.rsi[0] < self.p.buy_threshold:
                self._open_long()
        elif self.rsi[0] > self.p.sell_threshold:
            self._exit()


class DonchianBreakout(RiskAwareStrategy):
    params = (("period", 20),) + _RISK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.highest = bt.indicators.Highest(self.data.high, period=int(self.p.period))
        self.lowest = bt.indicators.Lowest(self.data.low, period=int(self.p.period))

    def next(self):
        if self._trend_exit():
            return
        if not self.position:
            if self.data.close[0] > self.highest[-1]:
                self._open_long()
        elif self.data.close[0] < self.lowest[-1]:
            self._exit()


# bt-параметры Pinbar — подобраны перебором на YDEX (2025-08..2026-08, 30min):
# объёмные фильтры (vol 40/1.5, bull 0.7) как у Поглощения + тень/тело 2.5,
# широкий стоп 4.5 ATR, тейк 1:3, вход выше EMA(250). Без фильтров стратегия
# убыточна (-45%/год); с ними: бычье окно +8.4% PF 5.9, полный год +3.7% PF 1.5
# (лучше Поглощения на обоих окнах). Стоп 5.0/5.5 ATR хуже — 4.5 оптимален.
# SL/TP по объёмному профилю HVN (vol_profile=1): b=50 p=100 m=1.2 — бычье окно
# +10.9% PF 7.1, полный год +4.2% PF 1.5 (базис ATR +8.4% PF 5.9 / +3.7% PF 1.5).
_PINBAR_PARAMS_TUPLE = (
    ("wick_ratio", 2.5),
    ("risk_pct", 1.0),
    ("atr_period", 20),
    ("atr_stop_mult", 4.5),
    ("rr_ratio", 3.0),
    ("trend_period", 250),
    ("trend_vwap", 0),
    ("vol_period", 40),
    ("vol_mult", 1.5),
    ("bull_frac", 0.7),
    ("vol_profile", 1),
    ("profile_bins", 50),
    ("profile_period", 100),
    ("profile_mult", 1.2),
)


class PinbarStrategy(RiskAwareStrategy):
    """Молот / падающая звезда. Вход на бычьем пин-баре, выход — по SL/TP или медвежьему.

    Подтверждение как у Поглощения: ``vol_period``/``vol_mult`` — объём свечи
    не ниже среднего с множителем; ``bull_frac`` — доля «бычьей» силы свечи.
    """

    params = _PINBAR_PARAMS_TUPLE

    def _bull(self) -> bool:
        return (
            sig.is_bullish_pinbar(
                float(self.data.open[0]), float(self.data.high[0]),
                float(self.data.low[0]), float(self.data.close[0]), float(self.p.wick_ratio),
            )
            and self._volume_confirms()
            and self._bulls_dominate()
        )

    def _bear(self) -> bool:
        return sig.is_bearish_pinbar(
            float(self.data.open[0]), float(self.data.high[0]),
            float(self.data.low[0]), float(self.data.close[0]), float(self.p.wick_ratio),
        )

    def next(self):
        if self._trend_exit():
            return
        if not self.position:
            if self._bull():
                self._open_long()
        elif self._bear():
            self._exit()


class EngulfingStrategy(RiskAwareStrategy):
    """Бычье/медвежье поглощение. Вход на бычьем, выход — по SL/TP или медвежьему.

    Объём MOEX (колонка volume) учитывается:
    - ``vol_period``/``vol_mult`` — подтверждение: объём свечи паттерна не ниже
      среднего (SMA) с множителем; 0 — фильтр выключен;
    - ``bull_frac`` — доля «бычьего» объёма на свече входа (положение close
      в диапазоне high-low): покупатели доминируют, если (close-low)/(high-low)
      не ниже порога. 0 — выключено.
    """

    params = _ENGULFING_PARAMS_TUPLE

    def _bull(self) -> bool:
        return (
            sig.is_bullish_engulfing(
                float(self.data.open[0]), float(self.data.high[0]),
                float(self.data.low[0]), float(self.data.close[0]),
                float(self.data.open[-1]), float(self.data.close[-1]),
            )
            and self._volume_confirms()
            and self._bulls_dominate()
        )

    def _bear(self) -> bool:
        return sig.is_bearish_engulfing(
            float(self.data.open[0]), float(self.data.high[0]),
            float(self.data.low[0]), float(self.data.close[0]),
            float(self.data.open[-1]), float(self.data.close[-1]),
        )

    def next(self):
        if self._trend_exit():
            return
        if not self.position:
            if self._bull():
                self._open_long()
        elif self._bear():
            self._exit()


STRATEGIES = {
    "sma_cross": {
        "name": "SMA Crossover",
        "cls": SmaCross,
        "params": [
            {"key": "fast", "label": "Быстрая SMA (период)", "type": "int", "default": 10},
            {"key": "slow", "label": "Медленная SMA (период)", "type": "int", "default": 30},
        ] + _RISK_PARAMS,
    },
    "rsi": {
        "name": "RSI (перепроданность/перекупленность)",
        "cls": RSIStrategy,
        "params": [
            {"key": "period", "label": "Период RSI", "type": "int", "default": 14},
            {"key": "buy_threshold", "label": "Порог покупки (<)", "type": "int", "default": 30},
            {"key": "sell_threshold", "label": "Порог продажи (>)", "type": "int", "default": 70},
        ] + _RISK_PARAMS,
    },
    "donchian": {
        "name": "Donchian Breakout",
        "cls": DonchianBreakout,
        "params": [
            {"key": "period", "label": "Период канала", "type": "int", "default": 20},
        ] + _RISK_PARAMS,
    },
    "pinbar": {
        "name": "Pinbar (молот / падающая звезда)",
        "cls": PinbarStrategy,
        "params": [
            {"key": "wick_ratio", "label": "Тень / тело", "type": "float", "default": 2.5},
            {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
            {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 20},
            {"key": "atr_stop_mult", "label": "Стоп, ATR", "type": "float", "default": 4.5},
            {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 3.0},
            {"key": "trend_period", "label": "Трендовый EMA (0 = выкл)", "type": "int", "default": 250},
            {"key": "trend_vwap", "label": "Трендовый по объёму VWMA (1 = да, 0 = нет)", "type": "int", "default": 0},
            {"key": "vol_period", "label": "Объём: период среднего (0 = выкл)", "type": "int", "default": 40},
            {"key": "vol_mult", "label": "Объём: мин. кратность среднего", "type": "float", "default": 1.5},
            {"key": "bull_frac", "label": "Доля быков на свече входа (0 = выкл)", "type": "float", "default": 0.7},
            {"key": "vol_profile", "label": "SL/TP по объёмному профилю HVN (1 = да)", "type": "int", "default": 1},
            {"key": "profile_bins", "label": "Профиль: число бинов цен", "type": "int", "default": 50},
            {"key": "profile_period", "label": "Профиль: окно свечей", "type": "int", "default": 100},
            {"key": "profile_mult", "label": "Профиль: порог объёма (x среднего)", "type": "float", "default": 1.2},
        ],
    },
    "engulfing": {
        "name": "Поглощение (Engulfing)",
        "cls": EngulfingStrategy,
        "params": _ENGULFING_PARAMS,
    },
}


def strategy_params_schema(strategy_key: str) -> list[dict]:
    info = STRATEGIES[strategy_key]
    defaults = {p["key"]: p["default"] for p in info["params"]}
    return defaults
