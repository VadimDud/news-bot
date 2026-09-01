"""Backtrader-стратегии для бэктеста + реестр с описаниями параметров для веб-формы.

Логика повторяет чистые функции из ``signals.py``. Риск-менеджмент по мотивам
Price Action: лот от % риска, стоп-лосс по ATR, тейк по R:R, трендовый фильтр EMA.
"""

import logging

import backtrader as bt
import numpy as np
import pandas as pd

from . import fib_pullback as fibp
from . import risk as risk_module
from . import signals as sig
from .news_guard import NewsGuard

logger = logging.getLogger("moex_trader.strategies")


class TradeRecordingStrategy(bt.Strategy):
    """Базовая стратегия, записывающая закрытые сделки для отчёта бэктеста.

    Собственные стратегии наследуйте от этого класса, чтобы в результатах
    бэктеста появлялась таблица сделок.  Записываются также дата входа,
    удержание (дней), цена входа/выхода и доходность %.
    """

    def __init__(self):
        self.recorded_trades: list[dict] = []
        self._trade_cost: dict[str, tuple[float, float, float]] = {}

    def notify_trade(self, trade):
        ticker = getattr(trade.data, "_name", None) or trade.getdataname()
        if trade.justopened:
            price = float(trade.price) if trade.price else 0.0
            size = abs(float(trade.size)) if trade.size else 0.0
            self._trade_cost[ticker] = (price * size, size, price, float(trade.size))
        if trade.isclosed:
            cost, orig_size, entry_price, signed_size = self._trade_cost.pop(ticker, (0.0, 0.0, 0.0, 1.0))
            pnl = float(trade.pnlcomm or 0.0)
            ret_pct = round(pnl / cost * 100.0, 2) if cost > 0 else 0.0
            entry_dt = bt.num2date(trade.dtopen) if trade.dtopen else None
            close_dt = bt.num2date(trade.dtclose) if trade.dtclose else None
            days_held = (close_dt.date() - entry_dt.date()).days if entry_dt and close_dt else 0
            # Цена выхода по знаку позиции: лонг exit=entry+pnl/qty, шорт exit=entry-pnl/qty.
            if orig_size > 0:
                per = pnl / orig_size
                exit_price = round(entry_price + per if signed_size >= 0 else entry_price - per, 2)
            else:
                exit_price = 0.0
            self.recorded_trades.append(
                {
                    "opened": str(entry_dt) if entry_dt else None,
                    "days_held": days_held,
                    "entry_price": round(entry_price, 2),
                    "exit_price": exit_price,
                    "ret_pct": ret_pct,
                    "traded": str(close_dt) if close_dt else None,
                    "status": "closed",
                    "pnl": round(pnl, 2),
                    "ticker": ticker,
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
    ("scale_in", 0),
    ("scale_out", 0),
    ("scale_parts", 3),
    ("scale_dist", 1.0),
    ("scale_out_interval", 1),
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
_SCALE_PARAMS = [
    {"key": "scale_in", "label": "Усреднение входа: N сделок (1 = да)", "type": "int", "default": 0},
    {"key": "scale_out", "label": "Выход частями: N продаж (1 = да)", "type": "int", "default": 0},
    {"key": "scale_parts", "label": "Усреднение: число сделок", "type": "int", "default": 3},
    {"key": "scale_dist", "label": "Усреднение: шаг лимиток, ATR", "type": "float", "default": 1.0},
    {"key": "scale_out_interval", "label": "Выход: интервал продаж, свечей", "type": "int", "default": 1},
]
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
    *_SCALE_PARAMS,
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
        # состояние усреднения входа (усреднение) и выхода (выход частями)
        self._avg_orders: list = []
        self._scale_active = False
        self._scale_stop = 0.0
        self._scale_target = 0.0
        self._scale_out_left = 0
        self._scale_out_tranche = 0
        self._scale_out_pending = 0

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

    def _scaled_stop_distance(self) -> float:
        """Дистанция риска при усреднении входа: стоп ниже среднего входа.

        Средний вход усреднённой позиции на (parts-1)/2 шага ниже первой
        сделки, поэтому дистанция риска больше ATR-стопа на эту величину.
        """
        parts = max(int(getattr(self.p, "scale_parts", 3)), 1)
        dist = float(getattr(self.p, "scale_dist", 1.0))
        return self._stop_distance() + dist * (parts - 1) / 2.0 * self._atr_value()

    def _risk_size(self) -> int:
        price = float(self.data.close[0])
        stop_dist = self._scaled_stop_distance() if self._use_scale_in() else self._stop_distance()
        size = risk_module.position_size(
            float(self.broker.getvalue()), self._risk_fraction(), stop_dist, price
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
        if self._use_scale_in():
            # усреднение входа: первая часть рынком, остальные — лимитками
            parts = max(int(getattr(self.p, "scale_parts", 3)), 1)
            per = max(int(size / parts), 1)
            self.buy(size=per)
        else:
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
            if order.isbuy():
                if self._scale_active and order in self._avg_orders:
                    # лимитка усреднения исполнилась — перевыставить брекет на новый размер
                    self._avg_orders = [o for o in self._avg_orders if o is not order]
                    self._place_scaled_bracket()
                elif self._use_scale_in() and not self._scale_active:
                    self._start_scale_plan(order)
                else:
                    self._sl_order = None
                    self._tp_order = None
                    self._place_bracket()
            else:
                # позиция закрыта (стоп/тейк/выход частями) — снять всё лишнее
                self._cancel_avg()
                for pending in (self._sl_order, self._tp_order):
                    if pending is not None and pending is not order:
                        self.cancel(pending)
                self._sl_order = None
                self._tp_order = None
                self._scale_active = False
        elif order.status in (bt.Order.Canceled, bt.Order.Rejected, bt.Order.Margin, bt.Order.Expired):
            self._avg_orders = [o for o in self._avg_orders if o is not order]
            if order is self._sl_order:
                self._sl_order = None
            if order is self._tp_order:
                self._tp_order = None

    def _cancel_bracket(self) -> None:
        for order in (self._sl_order, self._tp_order):
            if order is not None and order.status in (
                bt.Order.Submitted,
                bt.Order.Accepted,
                bt.Order.Partial,
            ):
                self.cancel(order)
        self._sl_order = None
        self._tp_order = None

    def _cancel_avg(self) -> None:
        for order in self._avg_orders:
            if order.status in (bt.Order.Submitted, bt.Order.Accepted, bt.Order.Partial):
                self.cancel(order)
        self._avg_orders = []

    def _start_scale_plan(self, order) -> None:
        """Разложить вход на N сделок: рынок + лимитки ниже через scale_dist*ATR."""
        parts = max(int(getattr(self.p, "scale_parts", 3)), 1)
        dist = float(getattr(self.p, "scale_dist", 1.0))
        ref = float(order.executed.price)
        atr = self._atr_value()
        stop_dist = self._stop_distance()
        levels, _avg, stop, target = sig.scale_plan(
            ref, atr, parts, dist, stop_dist, float(self.p.rr_ratio),
        )
        self._scale_stop = stop
        self._scale_target = target
        self._avg_orders = []
        for k, level in enumerate(levels):
            if level < ref * 0.85:  # предохранитель от абсурдно низких уровней
                break
            self._avg_orders.append(
                self.buy(exectype=bt.Order.Limit, price=level, size=order.executed.size)
            )
        self._scale_active = True
        self._place_scaled_bracket()

    def _place_scaled_bracket(self) -> None:
        """Стоп на scale_stop, тейк на scale_target, покрывающие всю позицию."""
        if self.position.size <= 0 or not self._scale_active:
            return
        self._cancel_bracket()
        self._sl_order = self.sell(exectype=bt.Order.Stop, price=self._scale_stop, size=self.position.size)
        self._tp_order = self.sell(exectype=bt.Order.Limit, price=self._scale_target, size=self.position.size)

    def _use_scale_in(self) -> bool:
        return int(getattr(self.p, "scale_in", 0)) > 0

    def _use_scale_out(self) -> bool:
        return int(getattr(self.p, "scale_out", 0)) > 0

    def _step_scale_out(self) -> None:
        """Выход частями: продажа следующей доли по барам (вызывается из next)."""
        if self._scale_out_left <= 0:
            return
        if self._scale_out_pending > 0:
            self._scale_out_pending -= 1
            return
        size = min(self._scale_out_tranche, self.position.size)
        if size > 0:
            self.sell(size=size)
            self._scale_out_left -= 1
        if self._scale_out_left <= 0 or self.position.size <= 0:
            self._scale_out_left = 0

    def _exit(self) -> None:
        if self._scale_out_left > 0:
            return  # уже выходим частями
        self._cancel_bracket()
        self._cancel_avg()
        if not self.position:
            return
        if self._use_scale_out() and self.position.size > 1:
            # выход частями: первая продажа рынком, остальные — по барам
            parts = max(int(getattr(self.p, "scale_parts", 3)), 1)
            self._scale_out_tranche = max(int(self.position.size / parts), 1)
            self._scale_out_left = parts - 1
            self._scale_out_pending = max(int(getattr(self.p, "scale_out_interval", 1)), 1) - 1
            self.sell(size=self._scale_out_tranche)
        else:
            self.close()

    def _trend_exit(self) -> bool:
        """Закрыть позицию при развороте тренда. Возвращает True, если вышли."""
        if self.position and not self._trend_up():
            self._exit()
            return True
        return False

    # Общий шаблон длинной стратегии: каждый бар степаем выход, проверяем тренд,
    # входим по _buy_signal() без позиции, выходим по _sell_signal() в позиции.
    def next(self):
        self._step_scale_out()
        if self._trend_exit():
            return
        if not self.position:
            if self._buy_signal():
                self._open_long()
        elif self._sell_signal():
            self._exit()

    def _buy_signal(self) -> bool:
        return False

    def _sell_signal(self) -> bool:
        return False


class SmaCross(RiskAwareStrategy):
    params = (("fast", 10), ("slow", 30)) + _RISK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        sma_fast = bt.indicators.SMA(self.data.close, period=int(self.p.fast))
        sma_slow = bt.indicators.SMA(self.data.close, period=int(self.p.slow))
        self.crossover = bt.indicators.CrossOver(sma_fast, sma_slow)

    def _buy_signal(self) -> bool:
        return self.crossover[0] > 0

    def _sell_signal(self) -> bool:
        return self.crossover[0] < 0


class RSIStrategy(RiskAwareStrategy):
    params = (("period", 14), ("buy_threshold", 30), ("sell_threshold", 70)) + _RISK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=int(self.p.period), safediv=True)

    def _buy_signal(self) -> bool:
        return self.rsi[0] < self.p.buy_threshold

    def _sell_signal(self) -> bool:
        return self.rsi[0] > self.p.sell_threshold


# bt-параметры Donchian — подобраны перебором на дневных данных 10 ликвидных
# тикеров MOEX (CHMF..TATN, 2021-08..2026-08, buy&hold −26%): period=30, стоп
# 1.5 ATR, R:R 2.0, вход только выше EMA(50). Перебор train/test
# (2021-08..2024-08 / 2024-08..2026-08): period 15/20/30/40/60 × стоп
# 1.0/1.5/2.0/2.5 × trend 0/50/100/200 — лучший баланс дал 30/1.5/50:
# train +7.1% PF 1.56, test −1.4% DD 6.5% против текущего sma_cross (+5.6%/
# −2.8%) и базового donchian 20/1.5/0 (+8.6%/−3.4%). Трендовый фильтр EMA(50)
# уполовинивает потери в медвежьем хвосте 2024-2026.
_DONCHIAN_PARAMS_TUPLE = (
    ("period", 30),
    ("risk_pct", 1.0),
    ("atr_period", 14),
    ("atr_stop_mult", 1.5),
    ("rr_ratio", 2.0),
    ("trend_period", 50),
)


class DonchianBreakout(RiskAwareStrategy):
    params = _DONCHIAN_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.highest = bt.indicators.Highest(self.data.high, period=int(self.p.period))
        self.lowest = bt.indicators.Lowest(self.data.low, period=int(self.p.period))

    def _buy_signal(self) -> bool:
        return self.data.close[0] > self.highest[-1]

    def _sell_signal(self) -> bool:
        return self.data.close[0] < self.lowest[-1]


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
    ("scale_in", 0),
    ("scale_out", 0),
    ("scale_parts", 3),
    ("scale_dist", 1.0),
    ("scale_out_interval", 1),
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

    def _buy_signal(self) -> bool:
        return self._bull()

    def _sell_signal(self) -> bool:
        return self._bear()


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

    def _buy_signal(self) -> bool:
        return self._bull()

    def _sell_signal(self) -> bool:
        return self._bear()


# Параметры MA-трендовой стратегии. Подобраны перебором на YDEX 30min
# (бычье окно 2025-10..2026-02 и полный год 2025-08..2026-08, +60min):
# стек 20/100/200 (медленная MA — фильтр большого тренда), наклон 5 баров,
# вход по откату к средней, без фильтра цены>медленной (sf=0), разжатие линий
# 0.1 ATR (sp=0.1 vs 0.0: +7.4%/+4.2% vs +5.2%/+1.2% на 30min up/full).
# Итог 30min: бычье окно +7.4% PF 1.94, полный год +4.2% PF 1.34 (40 сделок).
# Классический стек 50/100/200 на полном году убыточен (-6.3%) — не дефолт.
_MA_TREND_PARAMS_TUPLE = (
    ("risk_pct", 1.0),
    ("ma_fast", 20),
    ("ma_mid", 100),
    ("ma_slow", 200),
    ("slope_bars", 5),
    ("enter_pullback", 1),
    ("use_slow_filter", 0),
    ("spread_min", 0.1),
    ("atr_period", 20),
    ("atr_stop_mult", 4.0),
    ("rr_ratio", 3.0),
    ("trend_period", 0),
    ("trend_vwap", 0),
    ("vol_period", 0),
    ("vol_mult", 1.5),
    ("bull_frac", 0.7),
    ("vol_profile", 0),
    ("profile_bins", 40),
    ("profile_period", 200),
    ("profile_mult", 1.5),
    ("scale_in", 0),
    ("scale_out", 0),
    ("scale_parts", 3),
    ("scale_dist", 1.0),
    ("scale_out_interval", 1),
)


class MATrendStrategy(RiskAwareStrategy):
    """Трендовая стратегия на стекинге скользящих средних.

    Компоненты методики MA-trend:
    - ``ma_fast/ma_mid/ma_slow`` — стек из трёх SMA (по умолчанию 50/100/200);
    - ``slope_bars`` — подтверждение моментума: быстрая MA растёт N баров;
    - вход: золотое сечение (пересечение fast/mid вверх) — старт тренда, либо
      откат к mid (``enter_pullback``) — вход на динамической поддержке;
    - ``use_slow_filter`` — фильтр «большой картины»: цена выше медленной MA
      (аналог тренда старшего таймфрейма);
    - ``spread_min`` — «разжатие» линий (expansion): в сжатие MA (боковик)
      не входим. 0 — компонент выключен;
    - выход: быстрая MA ниже средней (тренд сломан) или цена ниже медленной.
    """

    params = _MA_TREND_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.sma_f = bt.indicators.SMA(self.data.close, period=int(self.p.ma_fast))
        self.sma_m = bt.indicators.SMA(self.data.close, period=int(self.p.ma_mid))
        self.sma_s = bt.indicators.SMA(self.data.close, period=int(self.p.ma_slow))

    def _stacked(self) -> bool:
        f, m, s = float(self.sma_f[0]), float(self.sma_m[0]), float(self.sma_s[0])
        if f != f or m != m or s != s:
            return False  # тёплый период SMA
        return sig.ma_stacked(f, m, s)

    def _slope_up(self) -> bool:
        bars = int(self.p.slope_bars)
        if bars <= 0:
            return True
        cur, prev = float(self.sma_f[0]), float(self.sma_f[-bars])
        if cur != cur or prev != prev:
            return False
        return sig.ma_slope_up(prev, cur)

    def _golden_cross(self) -> bool:
        f0, m0 = float(self.sma_f[0]), float(self.sma_m[0])
        f1, m1 = float(self.sma_f[-1]), float(self.sma_m[-1])
        for x in (f0, m0, f1, m1):
            if x != x:
                return False
        return sig.ma_golden_cross(f1, m1, f0, m0)

    def _pullback(self) -> bool:
        m = float(self.sma_m[0])
        if m != m:
            return False
        return sig.ma_pullback(float(self.data.low[0]), float(self.data.close[0]), m)

    def _slow_filter(self) -> bool:
        if not int(self.p.use_slow_filter):
            return True
        s = float(self.sma_s[0])
        if s != s:
            return False
        return float(self.data.close[0]) > s

    def _expanded(self) -> bool:
        min_spread = float(self.p.spread_min)
        if min_spread <= 0:
            return True
        f, m, s = float(self.sma_f[0]), float(self.sma_m[0]), float(self.sma_s[0])
        for x in (f, m, s):
            if x != x:
                return False
        atr = self._atr_value()
        return sig.ma_spread(f, m, s, atr, min_spread)

    def _long_signal(self) -> bool:
        if not (self._stacked() and self._slope_up() and self._slow_filter()):
            return False
        if not self._expanded():
            return False  # сжатие линий MA — боковик, входа нет
        if self._golden_cross():
            return True
        return bool(int(self.p.enter_pullback)) and self._pullback()

    def _long_exit(self) -> bool:
        f, m = float(self.sma_f[0]), float(self.sma_m[0])
        if f == f and m == m and f < m:
            return True
        s = float(self.sma_s[0])
        return s == s and float(self.data.close[0]) < s

    def _buy_signal(self) -> bool:
        return self._long_signal()

    def _sell_signal(self) -> bool:
        return self._long_exit()


# Параметры медвежьей стратегии Vol Profile Breakdown (пробой зоны высокого
# объёма HVN вниз + ретест + вход в шорт до следующей зоны B). Логика по
# методике Bearish Volume Profile Breakdown (Auction Market Theory):
# баланс в HVN A -> импульс вниз -> ретест нижней границы -> шорт до HVN B.
# Стоп за верх зоны A, тейк перед верхом зоны B, RR-фильтр отсекает плохие.
# Параметры подбираются перебором на YDEX 30m/60m (defaults могут быть
# перекрыты per-ticker оверрайдами TICKER_OVERRIDES).
_VOL_BREAKDOWN_PARAMS_TUPLE = (
    ("risk_pct", 1.0),
    ("atr_period", 14),
    ("atr_stop_mult", 0.5),
    ("take_atr_mult", 0.25),
    ("min_rr", 1.5),
    ("profile_bins", 20),
    ("profile_period", 100),
    ("profile_mult", 1.5),
    ("retest_bars", 3),
    ("candle_confirm", 0),
    ("pin_shadow", 0.6),
    ("vol_period", 20),
    ("vol_mult", 1.5),
)


class VolProfileBreakdownStrategy(TradeRecordingStrategy):
    """Медвежий пробой зоны высокого объёма (HVN) с ретестом.

    Методика Bearish Volume Profile Breakdown: рынок балансируется в зоне
    HVN A (аккумуляция), затем продавец продавливает цену вниз (импульс),
    цена откатывается к нижней границе A (ретест) и входит в шорт; тейк —
    перед следующей нижестоящей зоной высокого объёма (HVN B), стоп — за
    верхнюю границу A с запасом ATR.

    Этапы (конечный автомат в ``next``):
      SCAN           — ищем свежий пробой низа зоны A;
      SEARCH_RETEST  — ждём отката: High заходит в зону A снизу;
      (вход)         — шорт на закрытии свечи ретеста (+свечной фильтр);
      IN_POSITION    — обычный брекет: стоп и тейк на зонах.
    ``candle_confirm=0`` — вход по касанию, без свечного фильтра; ``1`` —
    требуется пинарь-шорт/медвежье поглощение + всплеск объёма.
    """

    params = _VOL_BREAKDOWN_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self.atr_ind = bt.indicators.ATR(self.data, period=int(self.p.atr_period))
        if int(self.p.vol_period) > 0:
            self.vol_sma = bt.indicators.SMA(self.data.volume, period=int(self.p.vol_period))
        else:
            self.vol_sma = None
        self._state = "SCAN"
        self._zone_a: tuple[float, float] | None = None
        self._zone_b: tuple[float, float] | None = None
        self._wait = 0
        self._sl_order = None
        self._tp_order = None

    def _atr_value(self) -> float:
        v = float(self.atr_ind[0])
        return 0.0 if v != v or v <= 0 else v

    def _zones(self) -> list[tuple[float, float]]:
        period = max(int(self.p.profile_period), 2)
        bins = max(int(self.p.profile_bins), 5)
        mult = float(self.p.profile_mult)
        return sig.volume_profile_zones(
            self.data.high.get(ago=-period, size=period),
            self.data.low.get(ago=-period, size=period),
            self.data.close.get(ago=-period, size=period),
            self.data.volume.get(ago=-period, size=period),
            bins, mult,
        )

    def _reset(self) -> None:
        self._state = "SCAN"
        self._zone_a = None
        self._zone_b = None
        self._wait = 0

    # ── ШАГ 1-2: пробой низа зоны A ─────────────────────────────────────────
    def _scan(self) -> bool:
        zones = self._zones()
        c0 = float(self.data.close[0])
        c1 = float(self.data.close[-1])
        for z in zones:  # по возрастанию цены
            if z[1] <= c0:
                continue  # зона целиком ниже текущей цены
            if c0 < z[0] and c1 >= z[0]:
                # свежий пробой низа зоны (пред. свеча была >= низа)
                self._zone_a = z
                break
        if self._zone_a is None:
            return False
        # B = ближайшая зона строго ниже A
        b = None
        for z in zones:
            if z[1] < self._zone_a[0]:
                b = z
            else:
                break
        self._zone_b = b
        self._state = "SEARCH_RETEST"
        self._wait = 0
        return True

    # ── ШАГ 3: ретест + свечной фильтр ──────────────────────────────────────
    def _in_retest_zone(self) -> bool:
        a = self._zone_a
        h = float(self.data.high[0])
        return a[0] <= h <= a[1]

    def _candle_ok(self) -> bool:
        if not int(self.p.candle_confirm):
            return True
        o, h, l, c = map(float, (self.data.open[0], self.data.high[0],
                                 self.data.low[0], self.data.close[0]))
        rng = h - l
        shooting = rng > 0 and (h - c) / rng > float(self.p.pin_shadow)
        engulf = c < o and c < float(self.data.close[-1])
        vol_ok = True
        if self.vol_sma is not None:
            avg = float(self.vol_sma[0])
            vol_ok = (avg != avg or avg <= 0) or float(self.data.volume[0]) >= float(self.p.vol_mult) * avg
        return (shooting or engulf) and vol_ok

    def _search_retest(self) -> bool:
        if self._in_retest_zone() and self._candle_ok():
            self._enter_short()
            return True
        self._wait += 1
        if self._wait > int(self.p.retest_bars):
            self._reset()
        return False

    # ── ШАГ 4: ордер + риск-менеджмент ──────────────────────────────────────
    def _enter_short(self) -> None:
        a = self._zone_a
        b = self._zone_b
        atr = self._atr_value()
        if atr <= 0:
            self._reset()
            return
        entry = float(self.data.close[0])
        sl = a[1] + float(self.p.atr_stop_mult) * atr
        tp = (b[1] + float(self.p.take_atr_mult) * atr) if b else entry - (sl - entry)
        risk = sl - entry
        reward = entry - tp
        if risk <= 0 or reward <= 0:
            self._reset()
            return
        if reward / risk < float(self.p.min_rr):
            self._reset()  # низкий Risk/Reward — отмена
            return
        size = risk_module.position_size(
            float(self.broker.getvalue()), float(self.p.risk_pct) / 100.0, risk, entry
        )
        if size <= 0:
            self._reset()
            return
        # Ограничитель маржи: в бэктест-брокере backtrader закрывающий брекет
        # (buy-stop + buy-limit) отклоняется, когда номинал шорта >= капитала
        # (broker margin-reject). Держим номинал шорта строго ниже капитала,
        # чтобы стоп и тейк могли исполниться.
        equity = float(self.broker.getvalue())
        max_size = int(equity / entry * 0.9) if entry > 0 else size
        size = min(size, max_size)
        if size <= 0:
            self._reset()
            return
        self._sl_price = sl
        self._tp_price = tp
        self.sell(size=size)
        self._state = "IN_POSITION"

    def _place_bracket(self) -> None:
        if self.position.size >= 0 or self._sl_order is not None:
            return
        self._sl_order = self.buy(exectype=bt.Order.Stop, price=self._sl_price,
                                  size=-self.position.size)
        self._tp_order = self.buy(exectype=bt.Order.Limit, price=self._tp_price,
                                  size=-self.position.size)

    def _cancel_pending_bracket(self, keep) -> None:
        for pending in (self._sl_order, self._tp_order):
            if pending is not None and pending is not keep and pending.status in (
                bt.Order.Submitted, bt.Order.Accepted, bt.Order.Partial
            ):
                self.cancel(pending)

    def notify_order(self, order):
        if order.status == bt.Order.Completed:
            # сняли позицию шорта целиком либо частично
            if self.position.size == 0:
                self._cancel_pending_bracket(keep=order)
                self._reset()
                self._sl_order = self._tp_order = None
        elif order.status in (bt.Order.Canceled, bt.Order.Rejected, bt.Order.Margin):
            if order is self._sl_order:
                self._sl_order = None
            if order is self._tp_order:
                self._tp_order = None

    def next(self):
        if self.position.size < 0:
            self._place_bracket()
            return
        if not self.position.size and self._state == "IN_POSITION":
            self._reset()
        if self._state == "SCAN":
            self._scan()
        elif self._state == "SEARCH_RETEST":
            self._search_retest()


# bt-параметры Фибоначчи-ретрейсмента (трендовое продолжение). Логика повторяет
# ``fib_pullback``: вход по откату в зону [fib_in_low..fib_in_high] от импульса
# swing low → swing high при тренде вверх, с конфлюэнцией (зона + свеча + RSI)
# и фильтром market regime (EMA-тренд, потолок волатильности ATR, опц. ADX).
# Режим по умолчанию универсален; per-ticker рецепт подбирается перебором в
# TICKER_OVERRIDES по аналогии с pinbar/другими стратегиями.
_FIB_PULLBACK_PARAMS_TUPLE = (
    ("risk_pct", 1.0),
    ("direction", 1),
    ("atr_period", 20),
    ("atr_stop_mult", 1.5),
    ("rr_ratio", 2.0),
    ("trend_period", 200),
    ("swing_bars", 10),
    ("min_swing_dist_atr", 2.0),
    ("fib_in_low", 0.50),
    ("fib_in_high", 0.618),
    ("fib_tp", 0.0),
    ("confluence_min", 2),
    ("confirm_candle", 1),
    ("rsi_period", 14),
    ("rsi_oversold", 40.0),
    ("rsi_overbought", 85.0),
    ("regime_adx_min", 0.0),
    ("regime_atr_vol_max", 0.0),
    ("use_htf", 0),
    ("htf_trend_period", 50),
    ("sl_beyond_swing", 1),
    ("min_rr", 1.5),
    ("daily_drawdown_pct", 0.0),
)


class FibPullbackStrategy(RiskAwareStrategy):
    """Фибоначчи ретрейсмент (трендовое продолжение) на структуре рынка.

    Длинный вход на откате к зоне 50–61.8 % от последнего импульса (swing low →
    swing high) при восходящем тренде и конфлюэнции факторов:
    зона Фибо + свечной паттерн (пинбар/поглощение) + RSI перепроданность.

    Риск-менеджмент: стоп за экстремум swing low (``sl_beyond_swing``) либо по
    ATR; лот от ``risk_pct``; вход отменяется, если RRR ниже ``min_rr``;
    ``daily_drawdown_pct`` (0=выкл) блокирует новые входы при дневной просадке.

    Расчёт состояния полностью переиспользует чистые функции ``fib_pullback``
    на окне свечей (паритет с live/pandas-сигналом и юнит-тестами).
    """

    params = _FIB_PULLBACK_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self._last_state: dict = {}
        self._last_swing_low: float | None = None
        self._last_swing_high: float | None = None
        self._day_peak: float | None = None
        self._day_date = None
        # Окно истории для расчёта пивотов: по сути всей доступной истории
        # (кап — только чтобы сдерживать расход памяти). Пивоты — подтверждённые
        # локальные экстремумы, зависящие от прошлого; усечённое окно (например,
        # 2*swing_bars) не воспроизводит их и расходится с live-сигналом.
        self._window = 1000

    # ── Окно свечей → чистое состояние fib_pullback ─────────────────────────
    def _fib_frame(self) -> pd.DataFrame:
        m = min(int(self.data.buflen()), int(self._window))
        m = max(m, 2)

        def col(name):
            line = getattr(self.data, name)
            return [float(line[-k]) for k in range(m - 1, -1, -1)]

        return pd.DataFrame(
            {
                "open": col("open"),
                "high": col("high"),
                "low": col("low"),
                "close": col("close"),
                "volume": col("volume"),
            },
            index=range(m),
        )

    def _fib_state(self) -> dict:
        df = self._fib_frame()
        params = {
            "swing_bars": int(self.p.swing_bars),
            "min_swing_dist_atr": float(self.p.min_swing_dist_atr),
            "trend_period": int(self.p.trend_period),
            "htf_trend_period": int(self.p.htf_trend_period),
            "use_htf": int(getattr(self.p, "use_htf", 0)),
            "regime_adx_min": float(getattr(self.p, "regime_adx_min", 0.0)),
            "regime_atr_vol_max": float(getattr(self.p, "regime_atr_vol_max", 0.0)),
            "fib_in_low": float(self.p.fib_in_low),
            "fib_in_high": float(self.p.fib_in_high),
            "fib_tp": float(getattr(self.p, "fib_tp", 0.0)),
            "confluence_min": int(self.p.confluence_min),
            "confirm_candle": int(getattr(self.p, "confirm_candle", 1)),
            "rsi_period": int(getattr(self.p, "rsi_period", 14)),
            "rsi_oversold": float(self.p.rsi_oversold),
            "rsi_overbought": float(self.p.rsi_overbought),
        }
        st = fibp._compute_arrays(df, None, **params)
        i = len(df) - 1
        st["close"] = df["close"].values
        st["idx"] = i
        self._last_state = st
        sl = st["swing_low"][i]
        self._last_swing_low = None if (isinstance(sl, float) and sl != sl) or sl is None else float(sl)
        if isinstance(sl, float) and sl != sl:
            self._last_swing_low = None
        sh = st["swing_high"][i]
        self._last_swing_high = None if (isinstance(sh, float) and sh != sh) or sh is None else float(sh)
        return st

    def _entry_ok(self) -> bool:
        st = self._last_state
        i = st["idx"]
        # RRR-гейт: цель (0 %) vs стоп — минимум min_rr.
        price = float(self.data.close[0])
        stop_dist = self._stop_distance()
        tgt = st["target"][i]
        if not (np.isnan(tgt) or tgt <= price):
            reward = tgt - price
            if stop_dist > 0 and reward / stop_dist < float(self.p.min_rr):
                return False
        return fibp._entry_ok(st, i)

    def _buy_signal(self) -> bool:
        if self._drawdown_blocked():
            return False
        self._fib_state()
        return self._entry_ok()

    def _sell_signal(self) -> bool:
        if not self._last_state:
            self._fib_state()
        return fibp._exit_ok(self._last_state, self._last_state["idx"])

    # ── Шорт-плечо (direction=-1 / 0) ────────────────────────────────────────
    def _short_entry_ok(self) -> bool:
        st = self._last_state
        i = st["idx"]
        # RRR-гейт для шорта: цель (swing low) vs стоп — минимум min_rr.
        price = float(self.data.close[0])
        stop_dist = self._short_stop_distance()
        tgt = st["target_short"][i]
        if not (np.isnan(tgt) or tgt >= price):
            reward = price - tgt
            if stop_dist > 0 and reward / stop_dist < float(self.p.min_rr):
                return False
        return fibp._entry_ok_short(st, i)

    def _short_signal(self) -> bool:
        if self._drawdown_blocked():
            return False
        self._fib_state()
        return self._short_entry_ok()

    def _cover_signal(self) -> bool:
        if not self._last_state:
            self._fib_state()
        return fibp._exit_ok_short(self._last_state, self._last_state["idx"])

    # ── Структурный стоп для шорта (за экстремум swing high) ────────────────
    def _short_stop_distance(self) -> float:
        if int(getattr(self.p, "sl_beyond_swing", 1)) and self._last_swing_high is not None:
            price = float(self.data.close[0])
            if self._last_swing_high > price:
                dist = self._last_swing_high - price
                if dist >= price * 0.002:
                    return dist
        return super()._stop_distance()

    # ── Структурный стоп за экстремум swing low ─────────────────────────────
    def _stop_distance(self) -> float:
        if int(getattr(self.p, "sl_beyond_swing", 1)) and self._last_swing_low is not None:
            price = float(self.data.close[0])
            if price > self._last_swing_low:
                dist = price - self._last_swing_low
                if dist >= price * 0.002:
                    return dist
        return super()._stop_distance()

    # ── Дневной drawdown cutoff ──────────────────────────────────────────────
    def _drawdown_blocked(self) -> bool:
        limit = float(getattr(self.p, "daily_drawdown_pct", 0.0) or 0.0)
        if limit <= 0 or self._day_peak is None or self._day_peak <= 0:
            return False
        dd = (self._day_peak - float(self.broker.getvalue())) / self._day_peak
        return dd >= limit / 100.0

    def _update_day_peak(self) -> None:
        value = float(self.broker.getvalue())
        dt = self.data.datetime.date(0)
        if self._day_date != dt:
            self._day_date = dt
            self._day_peak = value
        else:
            self._day_peak = max(self._day_peak, value)

    # ── Шорт-ордера (вход sell, закрытие buy) ────────────────────────────────
    def _open_short(self) -> None:
        if self._trend_up():
            return
        stop_dist = self._short_stop_distance()
        price = float(self.data.close[0])
        size = risk_module.position_size(
            float(self.broker.getvalue()), self._risk_fraction(), stop_dist, price
        )
        if size <= 0:
            return
        max_by_cash = int(float(self.broker.getcash()) / price * 0.95) if price > 0 else 0
        size = max(min(size, max_by_cash), 1) if max_by_cash > 0 else size
        if size > 0:
            self.sell(size=size)  # SL/TP выставляются в notify_order после исполнения

    def _place_short_bracket(self) -> None:
        if self.position.size >= 0:
            return
        price = float(self.data.close[0])
        stop_dist = self._short_stop_distance()
        if stop_dist <= 0:
            return
        stop = price + stop_dist  # стоп выше входа
        # Тейк — Фибо-цель 0% (swing low на входе); 2R от стопа — только фолбэк.
        # Бэктест 2021-2026: тейк по swing low даёт перевес на MTSS/GAZP/CHMF/NVTK,
        # тейк 2R недостижим и шорт убыточен.
        target = None
        st = self._last_state
        sl_arr = st.get("swing_low") if st else None
        if sl_arr is not None and st.get("idx") is not None:
            v = float(sl_arr[st["idx"]])
            if v == v and v > 0 and v < price:  # не NaN и ниже входа
                target = v
        if target is None or not (0 < target < price):
            # фолбэк 2R от стопа
            target = price - stop_dist * float(self.p.rr_ratio)
        if not (0 < target < price):
            # последний пол: тейк на 0.5% ниже входа, но всегда положительный
            target = price * 0.995
        size = abs(self.position.size)
        self._sl_order = self.buy(exectype=bt.Order.Stop, price=stop, size=size)
        self._tp_order = self.buy(exectype=bt.Order.Limit, price=target, size=size)

    def _cover(self) -> None:
        self._cancel_bracket()
        if self.position.size < 0:
            self.close()

    def notify_order(self, order):
        if order.status != bt.Order.Completed:
            self._avg_orders = [o for o in self._avg_orders if o is not order]
            if order is self._sl_order:
                self._sl_order = None
            if order is self._tp_order:
                self._tp_order = None
            return
        size = self.position.size
        if order.isbuy():
            if size > 0:
                # вход в лонг исполнился — выставить брекет
                self._sl_order = None
                self._tp_order = None
                self._place_bracket()
            elif size == 0:
                # выход из шорта (покрытие/стоп/тейк) — снять лишнее
                for pending in (self._sl_order, self._tp_order):
                    if pending is not None and pending is not order:
                        self.cancel(pending)
                self._sl_order = None
                self._tp_order = None
        else:
            # sell
            if size < 0:
                # вход в шорт исполнился — выставить шорт-брекет
                self._sl_order = None
                self._tp_order = None
                self._place_short_bracket()
            elif size == 0:
                # выход из лонга — снять лишнее
                for pending in (self._sl_order, self._tp_order):
                    if pending is not None and pending is not order:
                        self.cancel(pending)
                self._sl_order = None
                self._tp_order = None

    def next(self):
        self._update_day_peak()
        direction = int(getattr(self.p, "direction", 1))
        size = self.position.size
        if size > 0:  # в лонге
            exit_sig = self._sell_signal()
            if direction <= 0:
                self._fib_state()
                exit_sig = exit_sig or self._short_entry_ok()
            if exit_sig:
                self._exit()
        elif size < 0:  # в шорте
            cover_sig = self._cover_signal()
            if direction >= 0:
                self._fib_state()
                cover_sig = cover_sig or self._entry_ok()
            if cover_sig:
                self._cover()
        else:  # без позиции
            if self._drawdown_blocked():
                return
            self._fib_state()
            if direction >= 0 and self._entry_ok():
                self._open_long()
            elif direction <= 0 and self._short_entry_ok():
                self._open_short()


# Параметры фундаментальной портфельной стратегии ROE + P/B. Логика повторяет
# ``signals.roe_pb_signal``, но мульти-дата: портфель (несколько тикеров)
# с равными долями. Вход при цене <= 0.8 стоимости капитала и высоком среднем
# за 10 лет ROE; выход при цене >= стоимости капитала или падении ROE.
_ROE_PORTFOLIO_PARAMS_TUPLE = (
    ("min_avg_roe", 15.0),
    ("min_single_roe", 12.0),
    ("pb_entry", 0.8),
    ("pb_exit", 1.5),
    ("pb_exit_partial", 1.2),  # при цене ≥ этого продаём часть позиции
    ("partial_frac", 0.5),     # доля позиции, продаваемая при pb_exit_partial
    ("roe_exit", 12.0),
    ("max_positions", 4),      # каждая сделка ≈ 100% / max_positions депозита
    ("rebalance_days", 2),
    ("cash_yield", 8.0),  # годовая доходность денежной подушки (фонд TMON), %
    ("fundamentals", None),  # {ticker: DataFrame(date, roe, book_value_per_share)} — подаётся извне
    ("dividends", None),       # {ticker: DataFrame(date, dividend)} — дивиденды на отсечке, подаются извне
    # Multi-factor скоринг: вместо жёстких AND-условий входа — взвешенная оценка.
    # scoring=0 — старая AND-логика (avg_roe >= min_avg_roe и т.д.); scoring=1 —
    # покупка top-N по composite score из факторов ROE/PB/momentum/дивиденды.
    ("scoring", 0),
    ("w_roe", 1.0),            # вес фактора «качество ROE» (avg_roe)
    ("w_pb", 1.0),             # вес фактора «дешевизна» (цена / BVPS)
    ("w_momentum", 0.5),       # вес фактора «моментум» (возврат за momentum_months)
    ("w_dividend", 0.5),       # вес фактора «дивидендная доходность»
    ("w_stability", 0.5),      # вес фактора «стабильность ROE» (min_roe / avg_roe)
    ("min_score", 0.4),        # мин. composite score (0-1) для входа в scoring-режиме
    ("momentum_months", 6),    # период моментума (месяцев) в scoring-режиме
    # News Guard: блокировка входа при негативных новостях (0 = выкл, 1 = вкл)
    ("news_guard", 0),
    # Стоп-лосс: 0 = выключен, 10 = 10% от цены входа (проверяется каждый бар)
    ("stop_loss_pct", 0.0),
)


class ROEPortfolioStrategy(TradeRecordingStrategy):
    """Фундаментальный портфель: равные доли в бумагах с дешёвым капиталом.

    На каждый ``rebalance_days`` баров проверяются все тикеры (data-фиды):
    - кандидат: средний ROE за ``min_avg_roe`` лет >= ``min_avg_roe`` И
      годовой ROE >= ``min_single_roe`` И цена <= ``pb_entry`` * BVPS;
    - позиция закрывается при цене >= ``pb_exit`` * BVPS или ROE < ``roe_exit``.

    Фундаментальные данные подаются параметром ``fundamentals`` — словарь
    ``{ticker: DataFrame}`` из prepare_fundamentals_series (колонки date, roe,
    book_value_per_share, avg_roe, min_roe; даты в виде строк YYYY-MM-DD).

    Доли равные: каждый вход покупает на ``1 / max_positions`` от капитала.
    """

    params = _ROE_PORTFOLIO_PARAMS_TUPLE

    def __init__(self):
        super().__init__()
        self._fundamentals = {}
        self._dividends = {}
        for d in self.datas:
            ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
            fund_df = (self.p.fundamentals or {}).get(ticker)
            if fund_df is not None:
                self._fundamentals[ticker] = self._index_by_date(fund_df)
            div_df = (self.p.dividends or {}).get(ticker)
            if div_df is not None:
                self._dividends[ticker] = self._index_dividends(div_df)
        self._bar = 0
        self._last_bar_date = None
        self._first_bar = True
        self._days_since_rebalance = 0
        self._ff_cache: dict[str, dict] = {}
        self._div_paid: set[tuple[str, object]] = set()
        self._entry_dates: dict[str, object] = {}
        self._partial_sold: set[str] = set()
        self._pb_history: dict[str, list[float]] = {}  # trailing P/B для percentile scoring
        self._entry_prices: dict[str, float] = {}      # цена входа для стоп-лосса
        self._div_accrued: dict[str, float] = {}       # накопленные дивы для total-return стопа
        # News Guard: lazy-init экземпляра (создаётся только при news_guard=1)
        self._news_guard_instance: NewsGuard | None = None
        self._news_blocked_log: list[str] = []

    def _get_news_guard(self) -> NewsGuard:
        if self._news_guard_instance is None:
            self._news_guard_instance = NewsGuard()
        return self._news_guard_instance

    def _is_news_blocked(self, ticker: str, dt) -> bool:
        """Проверка блокировки входа из-за негативных новостей."""
        if not int(getattr(self.p, "news_guard", 0)):
            return False
        guard = self._get_news_guard()
        blocked, reason = guard.is_blocked(ticker, dt)
        if blocked:
            self._news_blocked_log.append(f"{dt.date()} {ticker}: {reason}")
        return blocked

    def _index_dividends(self, df):
        """Дивиденды в {timestamp(отсечки): (dividend_руб, buy_before_ts | None)}.

        Право на дивиденд даёт владение НА дату отсечки, а для этого нужно
        купить бумагу не позже ``buy_before`` (T-1 от отсечки). Стратегия
        проверяет, что позиция была открыта на buy_before.

        Векторная реализация: iterrows в pandas 3 на смешанных колонках
        (datetime + float + str) превращает nan → NaT, ломая присваивание.
        """
        dts = pd.to_datetime(df["date"], format="mixed", errors="coerce")
        amounts = pd.to_numeric(df["dividend"], errors="coerce")
        bbs = (
            pd.to_datetime(df["buy_before"], errors="coerce")
            if "buy_before" in df.columns
            else pd.Series(pd.NaT, index=df.index)
        )
        mask = dts.notna() & amounts.notna()
        return {
            ts: (float(amt), None if pd.isna(bb) else pd.Timestamp(bb))
            for ts, amt, bb in zip(dts[mask], amounts[mask], bbs[mask])
        }

    def _payout(self, ticker: str, dt, size: int) -> float:
        """Дивиденд за позицию при покупке до даты отсечки.

        Начисляется, если позиция открыта на ``buy_before`` (T-1) — день перед
        отсечкой, последний для покупки с правом на дивиденд. В момент,
        когда стратегия смотрит на бар отсечки, проверяется, что акция куплена
        до неё включительно по buy_before.
        """
        if size <= 0:
            return 0.0
        ts = pd.Timestamp(dt.date())
        key = (ticker, ts)
        if key in self._div_paid:
            return 0.0  # не платим дважды за одну отсечку
        entry = self._dividends.get(ticker) or {}
        item = entry.get(ts)
        if item is None:
            return 0.0
        dividend_per_share, buy_before = item
        if buy_before is None or not self._entry_dates.get(ticker):
            return 0.0  # нет данных о покупке — не начисляем
        if self._entry_dates[ticker] <= buy_before:
            self._div_paid.add(key)
            return float(dividend_per_share) * size
        return 0.0

    def _index_by_date(self, df):
        out = df.copy()
        out["_dt"] = pd.to_datetime(out["date"])
        out = out.set_index("_dt").sort_index()
        return out

    def _ff(self, ticker: str, dt):
        """Forward-fill отчётности на дату dt (включая сам день)."""
        fund = self._fundamentals.get(ticker)
        if fund is None or fund.empty:
            return None
        if ticker not in self._ff_cache:
            self._ff_cache[ticker] = {}
        cache = self._ff_cache[ticker]
        key = pd.Timestamp(dt.date())
        if key in cache:
            return cache[key]
        before = fund[fund.index <= key]
        row = before.iloc[-1] if not before.empty else None
        cache[key] = row
        return row

    def _float_col(self, row, key):
        val = row.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def _avg_roe_value(self, row):
        return self._float_col(row, "avg_roe")

    def _roe_value(self, row):
        return self._float_col(row, "roe")

    def _bvps_value(self, row):
        return self._float_col(row, "book_value_per_share")

    def _roe_stability_value(self, row):
        return self._float_col(row, "roe_stability")

    def _dividend_trailing_yield(self, ticker: str, price: float, dt=None) -> float:
        """Дивидендная доходность за последние 12 месяцев от даты бара, % от цены.

        ``dt`` — текущая дата бара (или datetime); если не задана — текущий момент
        (для обратной совместимости).
        """
        if price <= 0:
            return 0.0
        divs = self._dividends.get(ticker) or {}
        if not divs:
            return 0.0
        dt_now = pd.Timestamp(dt.date()) if dt is not None else pd.Timestamp.now()
        cutoff_lower = dt_now - pd.DateOffset(months=12)
        total = 0.0
        for ts, (amount, _) in divs.items():
            if cutoff_lower <= ts <= dt_now:
                total += float(amount or 0.0)
        return total * 100.0 / price if total > 0 else 0.0

    def _momentum_return(self, d, months: int) -> float | None:
        """Возврат за months месяцев, если данных на период хватает."""
        lookback = max(1, int(months * 21))
        if len(d) > lookback:
            base = float(d.close[-lookback])
            if base > 0:
                return float(d.close[0]) / base - 1.0
        return None

    def _compute_score(self, ticker: str, dt, d) -> float:
        """Взвешенный composite score тикера (0-1) в scoring-режиме.

        Факторы: качество ROE (avg_roe/30), дешевизна (price/BVPS относительно
        pb_entry), моментум, дивидендная доходность, стабильность ROE.
        """
        row = self._ff(ticker, dt)
        if row is None:
            return 0.0
        price = float(d.close[0])
        if price <= 0:
            return 0.0

        # 1) Качество ROE: avg_roe / 30 (30%+ = полный балл).
        avg_roe = self._avg_roe_value(row)
        s_roe = min(avg_roe / 30.0, 1.0) if avg_roe is not None else 0.0

        # 2) Дешевизна: percentile P/B за trailing momentum_months окно
        #    (совпадает с _pb_percentile_score в signals.py)
        bvps = self._bvps_value(row)
        if bvps and bvps > 0:
            current_pb = price / bvps
            pb_window_size = int(self.p.momentum_months) * 21
            pb_hist = self._pb_history.get(ticker, [])
            if len(pb_hist) >= 5:
                hist_arr = pd.Series(pb_hist[-pb_window_size:])
                pct = (hist_arr <= current_pb).mean()
                s_pb = 1.0 - float(pct)
            else:
                s_pb = 0.5  # слишком мало данных — нейтральный балл
        else:
            s_pb = 0.0

        # 3) Моментум: возврат за momentum_months, нормируем ±30% → [0, 1].
        ret = self._momentum_return(d, int(self.p.momentum_months))
        if ret is None:
            s_mom = 0.5  # нет данных — нейтральный балл, чтобы не отбрасывать тикер
        else:
            s_mom = max(min((ret + 0.30) / 0.60, 1.0), 0.0)

        # 4) Дивидендная доходность: от суммы дивидендов за 12 мес / цену.
        dy = self._dividend_trailing_yield(ticker, price, dt)
        s_div = min(dy / 8.0, 1.0)

        # 5) Стабильность ROE: min_roe / avg_roe (0-1 из фундаментального ряда).
        st = self._roe_stability_value(row)
        s_stab = st if st is not None else 0.0

        total_w = (
            float(self.p.w_roe) + float(self.p.w_pb) + float(self.p.w_momentum)
            + float(self.p.w_dividend) + float(self.p.w_stability)
        )
        if total_w <= 0:
            return 0.0
        composite = (
            s_roe * float(self.p.w_roe) + s_pb * float(self.p.w_pb)
            + s_mom * float(self.p.w_momentum) + s_div * float(self.p.w_dividend)
            + s_stab * float(self.p.w_stability)
        ) / total_w
        return round(composite, 4)

    def next(self):
        dt = self.data.datetime.datetime(0)
        self._bar += 1
        cur_date = dt.date()
        # Прошедшие календарные дни с прошлого бара (для intraday обычно 0,
        # для дневных баров — 1; в выходные/праздники на месячных фидах — больше).
        elapsed = 0 if self._last_bar_date is None else (cur_date - self._last_bar_date).days
        self._last_bar_date = cur_date
        if self._first_bar:
            self._first_bar = False
            self._days_since_rebalance = int(self.p.rebalance_days)
        # Денежная подушка в фонде денежного рынка (TMON): свободный кэш приносит
        # доход по ставке cash_yield (% годовых), начисляется каждый календарный
        # день (не каждЫй бар — иначе на нижних таймфреймах доходность
        # раздувалась бы числом баров в сутках). При покупке бумаг кэш уходит
        # в акции (эквивалент продажи доли фонда), при продаже — возвращается.
        if elapsed > 0:
            cash = self.broker.getcash()
            if cash > 0 and float(getattr(self.p, "cash_yield", 0.0) or 0.0) > 0:
                daily = (float(self.p.cash_yield) / 100.0) / 365.0
                self.broker.add_cash(cash * daily * elapsed)
        # Дивиденды: начисляются на дату отсечки за открытую позицию (каждый бар,
        # не только в дни ребаланса).
        if self.p.dividends:
            for d in self.datas:
                ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
                pos = self.getposition(d)
                if pos.size <= 0:
                    continue
                if len(d) < len(self.data):
                    continue  # фид не догнал текущую дату портфеля
                amount = self._payout(ticker, dt, pos.size)
                if amount:
                    self.broker.add_cash(amount)
                    self._dividends_income = getattr(self, "_dividends_income", 0.0) + amount
                    # Accumulate per-share dividend for total-return stop
                    per_share = amount / pos.size if pos.size > 0 else 0.0
                    self._div_accrued[ticker] = self._div_accrued.get(ticker, 0.0) + per_share
        # Обновление истории P/B (каждый бар) — нужна для percentile scoring.
        if int(self.p.scoring) == 1:
            pb_window = int(self.p.momentum_months) * 21
            for d in self.datas:
                ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
                if len(d) < len(self.data):
                    continue
                row = self._ff(ticker, dt)
                if row is None:
                    continue
                bvps = self._bvps_value(row)
                if bvps and bvps > 0:
                    price_val = float(d.close[0])
                    if price_val > 0:
                        pb = price_val / bvps
                        hist = self._pb_history.setdefault(ticker, [])
                        hist.append(pb)
                        if len(hist) > pb_window:
                            hist[:] = hist[-pb_window:]
        # Стоп-лосс: проверяется каждый бар (вне гейта ребаланса).
        # Total-return: эффективный вход = цена − накопленные дивиденды.
        stop_pct = float(getattr(self.p, "stop_loss_pct", 0.0) or 0.0)
        if stop_pct > 0:
            for d in self.datas:
                ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
                if len(d) < len(self.data):
                    continue
                pos = self.getposition(d)
                if pos.size <= 0:
                    continue
                entry = self._entry_prices.get(ticker)
                if entry is not None:
                    accrued = self._div_accrued.get(ticker, 0.0)
                    effective_entry = max(entry - accrued, 0.0)
                    price_now = float(d.close[0])
                    if price_now <= effective_entry * (1 - stop_pct / 100.0):
                        self.close(data=d)
                        self._entry_prices.pop(ticker, None)
                        self._entry_dates.pop(ticker, None)
                        self._div_accrued.pop(ticker, None)
                        logger.info("STOP-LOSS %s: entry=%.2f accrued=%.2f effective=%.2f current=%.2f stop=%.1f%%",
                                    ticker, entry, accrued, effective_entry, price_now, stop_pct)
        # Ребаланс по календарным дням (не по числу баров): входам/выходам
        # достаточно одного раза в rebalance_days дней независимо от таймфрейма.
        self._days_since_rebalance += elapsed
        if self._days_since_rebalance < int(self.p.rebalance_days):
            return
        self._days_since_rebalance = 0

        # 1) Закрытие позиций:
        #    - ROE упал ниже порога или цена >= pb_exit*BVPS → закрываем всю позицию
        #    - цена >= pb_exit_partial*BVPS (и ещё не продавалась частично) →
        #      продаём долю partial_frac, остаток оставляем
        for d in self.datas:
            ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
            pos = self.getposition(d)
            if pos.size <= 0:
                continue
            row = self._ff(ticker, dt)
            if row is None:
                continue
            bvps = self._bvps_value(row)
            roe = self._roe_value(row)
            price = float(d.close[0])
            # полный выход: по ROE или по цене pb_exit*BVPS
            if (bvps and price >= float(self.p.pb_exit) * bvps) or (roe is not None and roe < float(self.p.roe_exit)):
                self.close(data=d)
                self._entry_dates.pop(ticker, None)
                self._entry_prices.pop(ticker, None)
                self._div_accrued.pop(ticker, None)
                continue
            # частичный выход: цена >= pb_exit_partial*BVPS → продаём часть позиции
            if (
                bvps
                and price >= float(self.p.pb_exit_partial) * bvps
                and ticker not in self._partial_sold
                and self.p.partial_frac > 0
            ):
                sell_size = max(1, int(pos.size * float(self.p.partial_frac)))
                if sell_size >= pos.size:
                    self.close(data=d)
                    self._entry_dates.pop(ticker, None)
                    self._entry_prices.pop(ticker, None)
                    self._div_accrued.pop(ticker, None)
                else:
                    self.sell(data=d, size=sell_size)
                    self._partial_sold.add(ticker)

        # 2) Открытие: докупаем, пока есть свободные доли, но не больше max_positions.
        open_positions = sum(1 for d in self.datas if self.getposition(d).size > 0)
        if open_positions >= int(self.p.max_positions):
            return
        target_weight = 1.0 / int(self.p.max_positions)

        if int(self.p.scoring) == 1:
            # Scoring-режим: считаем composite score для всех свободных тикеров,
            # сортируем по убыванию и берём top-N с score >= min_score.
            candidates: list[tuple[float, object, str]] = []
            for d in self.datas:
                ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
                if self.getposition(d).size > 0:
                    continue
                score = self._compute_score(ticker, dt, d)
                candidates.append((score, d, ticker))
            candidates.sort(key=lambda x: x[0], reverse=True)
            for score, d, ticker in candidates:
                if open_positions >= int(self.p.max_positions):
                    break
                if score < float(self.p.min_score):
                    break  # отсортировано по убыванию — дальше только хуже
                if self._is_news_blocked(ticker, dt):
                    continue  # негативные новости — пропускаем тикер
                price = float(d.close[0])
                if price <= 0:
                    continue
                size = int(float(self.broker.getvalue()) * target_weight / price)
                if size <= 0:
                    continue
                this_value = float(self.broker.getvalue()) * target_weight
                if this_value > float(self.broker.getcash()):
                    size = int(float(self.broker.getcash()) / price * 0.95)
                if size > 0:
                    if ticker not in self._entry_dates:
                        self._entry_dates[ticker] = pd.Timestamp(dt.date())
                    self._entry_prices[ticker] = price
                    self._div_accrued[ticker] = 0.0
                    self._partial_sold.discard(ticker)
                    self.buy(data=d, size=size)
                    open_positions += 1
            return

        for d in self.datas:
            if open_positions >= int(self.p.max_positions):
                break
            ticker = getattr(d, "_name", None) or (d._dataname if isinstance(d._dataname, str) else "") or ""
            if self.getposition(d).size > 0:
                continue
            row = self._ff(ticker, dt)
            if row is None:
                continue
            avg_roe = self._avg_roe_value(row)
            roe = self._roe_value(row)
            bvps = self._bvps_value(row)
            price = float(d.close[0])
            if avg_roe is None or roe is None or bvps is None or price <= 0:
                continue
            if self._is_news_blocked(ticker, dt):
                continue  # негативные новости — пропускаем тикер
            if avg_roe >= float(self.p.min_avg_roe) and roe >= float(self.p.min_single_roe) and price <= float(self.p.pb_entry) * bvps:
                size = int(float(self.broker.getvalue()) * target_weight / price)
                if size <= 0:
                    continue
                this_value = float(self.broker.getvalue()) * target_weight
                if this_value > float(self.broker.getcash()):
                    size = int(float(self.broker.getcash()) / price * 0.95)
                if size > 0:
                    if ticker not in self._entry_dates:
                        self._entry_dates[ticker] = pd.Timestamp(dt.date())
                    self._entry_prices[ticker] = price
                    self._div_accrued[ticker] = 0.0
                    self._partial_sold.discard(ticker)
                    self.buy(data=d, size=size)
                    open_positions += 1


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
            {"key": "period", "label": "Период канала", "type": "int", "default": 30},
            {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
            {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 14},
            {"key": "atr_stop_mult", "label": "Стоп, ATR", "type": "float", "default": 1.5},
            {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 2.0},
            {"key": "trend_period", "label": "Трендовый EMA (0 = выкл)", "type": "int", "default": 50},
        ],
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
            *_SCALE_PARAMS,
        ],
    },
    "ma_trend": {
        "name": "MA-тренд (стекинг скользящих)",
        "cls": MATrendStrategy,
        "params": [
            {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
            {"key": "ma_fast", "label": "Быстрая MA (период)", "type": "int", "default": 20},
            {"key": "ma_mid", "label": "Средняя MA (период)", "type": "int", "default": 100},
            {"key": "ma_slow", "label": "Медленная MA (период)", "type": "int", "default": 200},
            {"key": "slope_bars", "label": "Наклон быстрой MA, баров (0 = выкл)", "type": "int", "default": 5},
            {"key": "enter_pullback", "label": "Вход по откату к средней (1 = да)", "type": "int", "default": 1},
            {"key": "use_slow_filter", "label": "Фильтр большого тренда: цена > медл. MA (1 = да)", "type": "int", "default": 0},
            {"key": "spread_min", "label": "Разжатие MA, x ATR (0 = выкл)", "type": "float", "default": 0.1},
            {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 20},
            {"key": "atr_stop_mult", "label": "Стоп, ATR", "type": "float", "default": 4.0},
            {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 3.0},
            {"key": "trend_period", "label": "Трендовый EMA (0 = выкл)", "type": "int", "default": 0},
            {"key": "trend_vwap", "label": "Трендовый по объёму VWMA (1 = да, 0 = нет)", "type": "int", "default": 0},
            {"key": "vol_period", "label": "Объём: период среднего (0 = выкл)", "type": "int", "default": 0},
            {"key": "vol_mult", "label": "Объём: мин. кратность среднего", "type": "float", "default": 1.5},
            {"key": "bull_frac", "label": "Доля быков на свече входа (0 = выкл)", "type": "float", "default": 0.7},
            {"key": "vol_profile", "label": "SL/TP по объёмному профилю HVN (1 = да)", "type": "int", "default": 0},
            {"key": "profile_bins", "label": "Профиль: число бинов цен", "type": "int", "default": 40},
            {"key": "profile_period", "label": "Профиль: окно свечей", "type": "int", "default": 200},
            {"key": "profile_mult", "label": "Профиль: порог объёма (x среднего)", "type": "float", "default": 1.5},
            *_SCALE_PARAMS,
        ],
    },
    "engulfing": {
        "name": "Поглощение (Engulfing)",
        "cls": EngulfingStrategy,
        "params": _ENGULFING_PARAMS,
    },
    "vol_breakdown": {
        "name": "Медвежий пробой HVN (Vol Profile Breakdown)",
        "cls": VolProfileBreakdownStrategy,
        "params": [
            {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
            {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 14},
            {"key": "atr_stop_mult", "label": "Стоп: за верх зоны A, x ATR", "type": "float", "default": 0.5},
            {"key": "take_atr_mult", "label": "Тейк: перед верхом зоны B, x ATR", "type": "float", "default": 0.25},
            {"key": "min_rr", "label": "Мин. коэффициент риск/доход (RR)", "type": "float", "default": 1.5},
            {"key": "profile_bins", "label": "Профиль: число бинов цен", "type": "int", "default": 20},
            {"key": "profile_period", "label": "Профиль: окно свечей", "type": "int", "default": 100},
            {"key": "profile_mult", "label": "Профиль: порог объёма (x среднего)", "type": "float", "default": 1.5},
            {"key": "retest_bars", "label": "Окно ретеста, баров", "type": "int", "default": 3},
            {"key": "candle_confirm", "label": "Свечное подтверждение входа (1 = да)", "type": "int", "default": 0},
            {"key": "pin_shadow", "label": "Пин-бар шорт: доля верхней тени", "type": "float", "default": 0.6},
            {"key": "vol_period", "label": "Подтверждение объёма: период (0 = выкл)", "type": "int", "default": 20},
            {"key": "vol_mult", "label": "Подтверждение объёма: множитель", "type": "float", "default": 1.5},
        ],
    },
    "roe_portfolio": {
        "name": "ROE + P/B (портфель равных долей)",
        "cls": ROEPortfolioStrategy,
        "params": [
            {"key": "min_avg_roe", "label": "Мин. средний ROE за 10 лет, %", "type": "float", "default": 15.0},
            {"key": "min_single_roe", "label": "Мин. годовой ROE, %", "type": "float", "default": 12.0},
            {"key": "pb_entry", "label": "Вход: цена ≤ (этого) × BVPS", "type": "float", "default": 0.8},
            {"key": "pb_exit", "label": "Полный выход: цена ≥ (этого) × BVPS", "type": "float", "default": 1.5},
            {"key": "pb_exit_partial", "label": "Частичная продажа: цена ≥ (этого) × BVPS", "type": "float", "default": 1.2},
            {"key": "partial_frac", "label": "Частичная продажа: доля позиции", "type": "float", "default": 0.5},
            {"key": "roe_exit", "label": "Выход: годовой ROE ниже, %", "type": "float", "default": 12.0},
            {"key": "max_positions", "label": "Макс. позиций (≈ 100%/N депозита на сделку)", "type": "int", "default": 4},
            {"key": "rebalance_days", "label": "Ребаланс, дней", "type": "int", "default": 2},
            {"key": "cash_yield", "label": "Денежный фонд (TMON): доходность, % годовых", "type": "float", "default": 8.0},
            {"key": "scoring", "label": "Режим: 0 = AND-логика, 1 = multi-factor скоринг", "type": "int", "default": 0},
            {"key": "w_roe", "label": "Скоринг: вес качества ROE", "type": "float", "default": 1.0},
            {"key": "w_pb", "label": "Скоринг: вес дешевизны (P/B)", "type": "float", "default": 1.0},
            {"key": "w_momentum", "label": "Скоринг: вес моментума", "type": "float", "default": 0.5},
            {"key": "w_dividend", "label": "Скоринг: вес дивидендной доходности", "type": "float", "default": 0.5},
            {"key": "w_stability", "label": "Скоринг: вес стабильности ROE", "type": "float", "default": 0.5},
            {"key": "min_score", "label": "Скоринг: мин. composite score для входа", "type": "float", "default": 0.4},
            {"key": "momentum_months", "label": "Скоринг: период моментума, мес", "type": "int", "default": 6},
            {"key": "news_guard", "label": "News Guard: блокировка входа при негативных новостях (1 = вкл)", "type": "int", "default": 0},
            {"key": "stop_loss_pct", "label": "Стоп-лосс: 0 = выключен, иначе % от цены входа", "type": "float", "default": 0.0},
        ],
    },
    "fib_pullback": {
        "name": "Фибоначчи ретрейсмент (трендовое продолжение)",
        "cls": FibPullbackStrategy,
        "params": [
            {"key": "risk_pct", "label": "Риск на сделку, %", "type": "float", "default": 1.0},
            {"key": "swing_bars", "label": "Свинг-пивоты: окно N свечей", "type": "int", "default": 10},
            {"key": "min_swing_dist_atr", "label": "Мин. ход импульса, x ATR", "type": "float", "default": 2.0},
            {"key": "fib_in_low", "label": "Зона отката: нижняя граница (0.5 = 50%)", "type": "float", "default": 0.50},
            {"key": "fib_in_high", "label": "Зона отката: верхняя граница (0.618 = 61.8%)", "type": "float", "default": 0.618},
            {"key": "fib_tp", "label": "Цель: доля хода от 0% (0 = экстремум)", "type": "float", "default": 0.0},
            {"key": "confluence_min", "label": "Конфлюэнция: мин. факторов (1 зона, 2 свеча, 3 RSI)", "type": "int", "default": 2},
            {"key": "confirm_candle", "label": "Свечное подтверждение (пинбар/поглощение) (1 = да)", "type": "int", "default": 1},
            {"key": "rsi_period", "label": "Период RSI", "type": "int", "default": 14},
            {"key": "rsi_oversold", "label": "RSI охлаждения моментума (вход ниже)", "type": "float", "default": 40.0},
            {"key": "rsi_overbought", "label": "RSI перекупленности (выход)", "type": "float", "default": 85.0},
            {"key": "regime_adx_min", "label": "Market regime: мин. ADX (0 = выкл)", "type": "float", "default": 0.0},
            {"key": "regime_atr_vol_max", "label": "Market regime: потолок ATR/цена (0 = выкл)", "type": "float", "default": 0.0},
            {"key": "use_htf", "label": "Фильтр тренда старшего ТФ (1 = да)", "type": "int", "default": 0},
            {"key": "htf_trend_period", "label": "HTF: период EMA тренда", "type": "int", "default": 50},
            {"key": "atr_period", "label": "Период ATR", "type": "int", "default": 20},
            {"key": "atr_stop_mult", "label": "Стоп, ATR (резервный)", "type": "float", "default": 1.5},
            {"key": "rr_ratio", "label": "Тейк / стоп (R:R)", "type": "float", "default": 2.0},
            {"key": "trend_period", "label": "Трендовый EMA (0 = выкл; длинный фильтр, напр. 200 SMA)", "type": "int", "default": 200},
            {"key": "sl_beyond_swing", "label": "Стоп за экстремум swing low (1 = да)", "type": "int", "default": 1},
            {"key": "min_rr", "label": "Мин. риск/доход для входа (RR)", "type": "float", "default": 1.5},
            {"key": "daily_drawdown_pct", "label": "Дневная просадка-блокировка, % (0 = выкл)", "type": "float", "default": 0.0},
            {"key": "direction", "label": "Направление: 1=только лонг, -1=только шорт, 0=оба", "type": "int", "default": 1},
        ],
    },
    "elliott_candles": {
        "name": "Эллиотт микро-волны (контртренд + мартингейл)",
        "cls": None,
        "params": [
            {"key": "wave_min", "label": "Мин. длина волны, свечей", "type": "int", "default": 3},
            {"key": "wave_max", "label": "Макс. длина волны, свечей", "type": "int", "default": 5},
            {"key": "body_ratio_min", "label": "Импульс: тело ≥ доли диапазона", "type": "float", "default": 0.6},
            {"key": "atr_k", "label": "Импульс: тело ≥ k×ATR(14)", "type": "float", "default": 0.5},
            {"key": "base_pct", "label": "Шаг 1 мартингейла, доля капитала", "type": "float", "default": 0.25},
            {"key": "max_steps", "label": "Макс. шагов удвоения", "type": "int", "default": 3},
            {"key": "quality_min", "label": "Фильтр качества волны 0..1 (0 = выкл)", "type": "float", "default": 0.0},
        ],
    },
}


# Дефолты параметров под конкретный тикер (per-ticker overrides).
# Ключ — (strategy_key, ticker); значения — полный набор параметров стратегии.
# Заполняются бэктестовым перебором: каждая стратегия имеет свой «рецепт» под
# тикер, и единый глобальный дефолт, угаданный под YDEX, на других тикерах
# (напр. SBER) уходит в минус. TICKER_OVERRIDES применяются поверх глобальных
# дефолтов в веб-форме и при выборе стратегии.
# SBER Pinbar — перебор (wick 3.5, стоп 5 ATR, R:R 2.5, объём 40/2.0, быки 0.5,
# HVN bins 50): полн. год 30m +2.9% PF 2.7, 60m +1.7% PF 2.7 (против −5.0%/−1.2%
# глобальных). Глобальные (YDEX) дефолты эти параметры не заменяют.
# Fib pullback short — отобранные бумаги (4h-сканер по умолчанию, ресемпл из 1h).
# Только эти бумаги торгуют в шорт; direction=-1 (шорт), timeframe=4h.
# Результаты бэктеста 4h (2025-08..2026-09, ~400 дней, тейк=swing low):
#   MOEX  +13627 (n=29, win 66%) — sb5/tp100
#   T     +10896 (n=20, win 80%) — sb10/tp100
#   NLMK  +10294 (n=14, win 79%) — sb10/tp100
#   LKOH  +9854  (n=15, win 67%) — sb10/tp100
#   TATN  +8419  (n=19, win 63%) — sb5/tp200
#   CHMF  +8025  (n=21, win 57%) — sb10/tp100
#   NVTK  +3201  (n=20, win 40%) — sb10/tp100
#   GAZP  +1864  (n=14, win 50%) — sb10/tp100
#   MTSS  убыточен на 4h — остаётся на 1day (дневной шорт +4872)
#   SBER  убыточен на 4h — остаётся на 1day (полное окно +25257)
# Лонг на 4h: CHMF +2819 (n=7, win 43%), остальные — убыток; лонг не включён.
_FIB_SHORT_OVERRIDES = {
    "MTSS": {
        "direction": -1,
        "timeframe": "1day",
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "GAZP": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "CHMF": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "NVTK": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "TATN": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 200,
        "swing_bars": 5,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "SBER": {
        "direction": -1,
        "timeframe": "1day",
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 50,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.618,
        "fib_in_high": 0.786,
    },
    "LKOH": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "NLMK": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "MOEX": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 5,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
    "T": {
        "direction": -1,
        "confluence_min": 1,
        "rsi_oversold": 40.0,
        "rsi_overbought": 80.0,
        "trend_period": 100,
        "swing_bars": 10,
        "min_rr": 1.0,
        "fib_in_low": 0.50,
        "fib_in_high": 0.618,
    },
}

TICKER_OVERRIDES: dict[tuple[str, str], dict] = {
    ("pinbar", "SBER"): {
        "wick_ratio": 3.5,
        "atr_stop_mult": 5.0,
        "rr_ratio": 2.5,
        "trend_period": 150,
        "vol_period": 40,
        "vol_mult": 2.0,
        "bull_frac": 0.5,
        "vol_profile": 1,
        "profile_bins": 50,
        "profile_period": 100,
        "profile_mult": 1.2,
    },
    **{("fib_pullback", t): p for t, p in _FIB_SHORT_OVERRIDES.items()},
}


def strategy_params_schema(strategy_key: str) -> list[dict]:
    info = STRATEGIES[strategy_key]
    defaults = {p["key"]: p["default"] for p in info["params"]}
    return defaults


def strategy_defaults(strategy_key: str, ticker: str | None = None) -> dict:
    """Дефолтные параметры стратегии, при наличии — с per-ticker переопределением."""
    defaults = strategy_params_schema(strategy_key)
    if ticker:
        override = TICKER_OVERRIDES.get((strategy_key, ticker.upper()))
        if override:
            defaults = {**defaults, **override}
    return defaults
