"""Risk-Reward Sanity Check — проверка когерентности entry/stop/target.

По мотивам marian2js/trading-skills/risk-reward-sanity-check.

Проверки:
- R:R >= минимального порога;
- стоп в разумных границах ATR (не слишком шумный, не слишком широкий);
- тейк-профит не за пределами реалистичного диапазона;
-.failure modes: стоп внутри ATR-шума, тейк дальше ликвидности.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .context import TradeContext


@dataclass
class RRResult:
    """Результат проверки risk/reward."""

    ok: bool
    rr_ratio: float
    stop_distance: float
    target_distance: float
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Константы ────────────────────────────────────────────────────────────────

DEFAULT_MIN_RR = 1.5  # минимальное R:R для входа
DEFAULT_MAX_ATR_MULT_STOP = 4.0  # стоп шире 4×ATR — подозрительно
DEFAULT_MIN_ATR_MULT_STOP = 0.2  # стоп уже 0.2×ATR — слишком шумный
DEFAULT_MAX_ATR_MULT_TARGET = 8.0  # тейк дальше 8×ATR — маловероятен


def check_rr(
    ctx: TradeContext,
    min_rr: float = DEFAULT_MIN_RR,
    max_atr_stop: float = DEFAULT_MAX_ATR_MULT_STOP,
    min_atr_stop: float = DEFAULT_MIN_ATR_MULT_STOP,
    max_atr_target: float = DEFAULT_MAX_ATR_MULT_TARGET,
) -> RRResult:
    """Проверить когерентность структуры сделки entry/stop/target.

    Следует правилу «не сайзить, пока не ясна структура»:
    если R:R не проходит — это блокер, не просто варнинг.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    if ctx.entry <= 0:
        blockers.append("entry не задан")
        return RRResult(ok=False, rr_ratio=0, stop_distance=0, target_distance=0, blockers=blockers)

    if ctx.stop is None:
        blockers.append("stop не задан")
        return RRResult(ok=False, rr_ratio=0, stop_distance=0, target_distance=0, blockers=blockers)

    if ctx.target is None:
        blockers.append("target не задан")
        return RRResult(ok=False, rr_ratio=0, stop_distance=0, target_distance=0, blockers=blockers)

    # Дистанции
    is_long = ctx.direction == "long" or (ctx.direction == "" and ctx.stop < ctx.entry)
    if is_long:
        stop_dist = ctx.entry - ctx.stop
        target_dist = ctx.target - ctx.entry
    else:
        stop_dist = ctx.stop - ctx.entry
        target_dist = ctx.entry - ctx.target

    if stop_dist <= 0:
        blockers.append("стоп за ценой входа")
        return RRResult(ok=False, rr_ratio=0, stop_distance=0, target_distance=0, blockers=blockers)

    if target_dist <= 0:
        blockers.append("тейк за ценой входа (нет потенциала прибыли)")
        return RRResult(ok=False, rr_ratio=0, stop_distance=stop_dist, target_distance=0, blockers=blockers)

    # R:R
    rr = target_dist / stop_dist

    # 1) Минимальный R:R
    if rr < min_rr:
        blockers.append(f"R:R = {rr:.2f} < минимального {min_rr:.2f}")

    # 2) Стоп vs ATR: слишком узкий (шум) или слишком широкий
    if ctx.atr > 0:
        atr_stop_ratio = stop_dist / ctx.atr
        if atr_stop_ratio < min_atr_stop:
            warnings.append(
                f"стоп {atr_stop_ratio:.2f}×ATR — слишком узкий, будет выбит шумом"
            )
        if atr_stop_ratio > max_atr_stop:
            warnings.append(
                f"стоп {atr_stop_ratio:.2f}×ATR — слишком широкий, "
                f"риск не оправдан потенциалом"
            )

        # 3) Тейк vs ATR: слишком далеко
        atr_target_ratio = target_dist / ctx.atr
        if atr_target_ratio > max_atr_target:
            warnings.append(
                f"тейк {atr_target_ratio:.2f}×ATR — маловероятно достичь за разумное время"
            )

    # 4) Тейк-профит: проверка ликвидности (если тейк > 30% от цены — подозрительно)
    if ctx.entry > 0:
        target_pct = target_dist / ctx.entry * 100
        if target_pct > 30:
            warnings.append(
                f"тейк {target_pct:.1f}% от цены — маловероятно достичь за одну сделку"
            )

    ok = len(blockers) == 0

    return RRResult(
        ok=ok,
        rr_ratio=round(rr, 2),
        stop_distance=round(stop_dist, 4),
        target_distance=round(target_dist, 4),
        blockers=blockers,
        warnings=warnings,
    )
