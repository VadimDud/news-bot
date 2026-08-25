"""Position Sizing — консервативное определение размера позиции.

По мотивам marian2js/trading-skills/position-sizing.

Правила:
- риск на сделку = risk_pct от equity;
- стоп-лосс по ATR (atr_mult * ATR);
- тейк-профит по R:R (rr_ratio);
- лот = риск-сумма / дистанция стопа;
- лимит позиции: max_position_pct от equity (не более);
- комиссии/проскальзывание вычитаются из суммы риска.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import risk as risk_module
from .context import TradeContext


@dataclass
class SizingResult:
    """Результат расчёта размера позиции."""

    size: int
    risk_amount: float  # реальная сумма риска в рублях
    risk_pct_actual: float  # фактический % риска от equity
    stop_distance: float  # дистанция стопа в рублях
    commission: float  # комиссия на сделку (estimate)
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# ── Константы ────────────────────────────────────────────────────────────────

DEFAULT_COMMISSION_PCT = 0.04  # 0.04% — типичная комиссия MOEX (базовый тариф)
DEFAULT_MAX_POSITION_PCT = 50.0  # макс. % equity на одну позицию
MIN_STOP_DISTANCE_PCT = 0.005  # мин. стоп-дистанция: 0.5% от цены


def size_position(
    ctx: TradeContext,
    commission_pct: float = DEFAULT_COMMISSION_PCT,
    max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
    lot_size: int = 1,
) -> SizingResult:
    """Рассчитать размер позиции по контексту сделки.

    Следует правилу «не сайзить, пока не ясна структура»:
    если стоп не задан или entry = 0 — возвращается size=1 с warning.
    """
    warnings: list[str] = []

    if ctx.entry <= 0:
        warnings.append("entry не задан — размер = 1 (минимум)")
        return SizingResult(
            size=1,
            risk_amount=0,
            risk_pct_actual=0,
            stop_distance=0,
            commission=0,
            warnings=warnings,
        )

    if ctx.stop is None:
        warnings.append("stop не задан — размер = 1 (минимум)")
        return SizingResult(
            size=1,
            risk_amount=0,
            risk_pct_actual=0,
            stop_distance=0,
            commission=0,
            warnings=warnings,
        )

    # Дистанция стопа
    stop_dist = ctx.entry - ctx.stop if ctx.direction == "long" else ctx.stop - ctx.entry
    if stop_dist <= 0:
        warnings.append("стоп за ценой входа — структура некогерентна")
        return SizingResult(
            size=1,
            risk_amount=0,
            risk_pct_actual=0,
            stop_distance=0,
            commission=0,
            warnings=warnings,
        )

    # Проверка минимальной дистанции стопа (от шума)
    min_stop = ctx.entry * MIN_STOP_DISTANCE_PCT
    if stop_dist < min_stop:
        warnings.append(
            f"стоп-дистанция {stop_dist:.2f} < минимальной {min_stop:.2f} "
            f"({MIN_STOP_DISTANCE_PCT*100:.1f}% от цены)"
        )
        stop_dist = min_stop

    # Сумма риска с учётом комиссий
    risk_amount = ctx.equity * (ctx.risk_pct / 100.0)
    commission_per_lot = ctx.entry * (commission_pct / 100.0) * 2  # buy + sell
    total_cost_per_lot = stop_dist + commission_per_lot
    if total_cost_per_lot <= 0:
        warnings.append("cost_per_lot = 0 — невозможно рассчитать размер")
        return SizingResult(
            size=1,
            risk_amount=0,
            risk_pct_actual=0,
            stop_distance=stop_dist,
            commission=0,
            warnings=warnings,
        )

    # Размер: риск-сумма / стоимость лота (стоп + комиссия)
    size = int(risk_amount / total_cost_per_lot)
    size = max(size, 1)

    # Лимит позиции по % equity
    max_value = ctx.equity * (max_position_pct / 100.0)
    max_lots = int(max_value / ctx.entry) if ctx.entry > 0 else 1
    max_lots = max(max_lots, 1)
    if size > max_lots:
        warnings.append(
            f"размер {size} > лимита {max_lots} ({max_position_pct:.0f}% equity)"
        )
        size = max_lots

    # Округление до размера лота (если задан)
    if lot_size > 1:
        size = (size // lot_size) * lot_size
        size = max(size, lot_size)

    # Фактический риск
    actual_risk = size * total_cost_per_lot
    risk_pct_actual = (actual_risk / ctx.equity * 100) if ctx.equity > 0 else 0
    total_commission = size * commission_per_lot

    return SizingResult(
        size=size,
        risk_amount=round(actual_risk, 2),
        risk_pct_actual=round(risk_pct_actual, 2),
        stop_distance=round(stop_dist, 4),
        commission=round(total_commission, 2),
        warnings=warnings,
    )
