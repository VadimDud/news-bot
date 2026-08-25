"""Pre-Trade Check — оркестратор pre-trade workflow.

По мотивам marian2js/trading-skills/pre-trade-check.

Цепочка:
1. Regime → классификация рыночного контекста
2. NewsGuard → проверка негативных новостей
3. RR-check → когерентность entry/stop/target
4. Sizing → консервативный расчёт размера

Короткое замыкание на первом блокере:
- BLOCKED → вход запрещён (первый блокер);
- RESIZE → размер требует корректировки;
- WARN → есть предупреждения, но вход возможен;
- READY → все проверки пройдены.

В автоматическом режиме (LiveTrader): regime + news_guard + rr_check + sizing.
LLM-тейзис — только в ручном режиме (дашборд).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from .context import TradeContext
from .regime import classify_regime
from .rr_check import check_rr
from .sizing import SizingResult, size_position

logger = logging.getLogger("moex_trader.skills.pretrade")

VERDICT_READY = "READY"
VERDICT_WARN = "WARN"
VERDICT_RESIZE = "RESIZE"
VERDICT_BLOCKED = "BLOCKED"


@dataclass
class PretradeReport:
    """Итоговый отчёт pre-trade проверки."""

    verdict: str  # READY | WARN | RESIZE | BLOCKED
    first_blocker: str = ""
    checks: dict = field(default_factory=dict)
    context: TradeContext | None = None
    warnings: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.utcnow())

    def as_dict(self) -> dict:
        """Сериализация для API/дашборда."""
        return {
            "verdict": self.verdict,
            "first_blocker": self.first_blocker,
            "checks": self.checks,
            "warnings": self.warnings,
            "checked_at": self.checked_at.isoformat(),
        }

    def short_report(self) -> str:
        """Краткий человекочитаемый отчёт."""
        parts = [f"Verdict: {self.verdict}"]
        if self.first_blocker:
            parts.append(f"Blocker: {self.first_blocker}")
        if self.warnings:
            parts.append(f"Warnings: {'; '.join(self.warnings[:3])}")
        if self.context:
            parts.append(self.context.short_report())
        return " | ".join(parts)


def check_pretrade(
    ctx: TradeContext,
    regime_df=None,
    *,
    min_rr: float = 1.5,
    max_position_pct: float = 50.0,
    commission_pct: float = 0.04,
    news_blocked: bool = False,
    news_reason: str = "",
) -> PretradeReport:
    """Запустить полный pre-trade-check.

    regime_df — DataFrame свечей для regime-анализа (если None — regime пропускается).
    """
    checks: dict = {}
    warnings: list[str] = []
    blockers: list[str] = []

    # ── 1. Regime ────────────────────────────────────────────────────────────
    if regime_df is not None and not regime_df.empty:
        regime_result = classify_regime(regime_df)
        ctx.regime = regime_result.regime
        ctx.regime_details = regime_result.details
        checks["regime"] = {
            "regime": regime_result.regime,
            "confidence": regime_result.confidence,
            "details": regime_result.details,
        }
        # Предупреждение, но не блокер в v1
        if regime_result.regime == "down":
            warnings.append(regime_result.as_warning())
        elif regime_result.regime == "high_vol":
            warnings.append(regime_result.as_warning())
    else:
        checks["regime"] = {"skipped": True, "reason": "Нет данных"}

    # ── 2. NewsGuard ─────────────────────────────────────────────────────────
    if news_blocked:
        ctx.news_blocked = True
        ctx.news_reason = news_reason
        blockers.append(f"Новости блокируют вход: {news_reason}")
        checks["news_guard"] = {"blocked": True, "reason": news_reason}
    else:
        checks["news_guard"] = {"blocked": False}

    # ── 3. RR-check ──────────────────────────────────────────────────────────
    rr_result = check_rr(ctx, min_rr=min_rr)
    ctx.rr_info = {
        "rr_ratio": rr_result.rr_ratio,
        "ok": rr_result.ok,
    }
    checks["rr_check"] = {
        "rr_ratio": rr_result.rr_ratio,
        "stop_distance": rr_result.stop_distance,
        "target_distance": rr_result.target_distance,
        "ok": rr_result.ok,
        "blockers": rr_result.blockers,
        "warnings": rr_result.warnings,
    }

    if not rr_result.ok:
        # Первый блокер из RR-check
        if rr_result.blockers:
            blockers.append(rr_result.blockers[0])
    warnings.extend(rr_result.warnings)

    # ── 4. Sizing ────────────────────────────────────────────────────────────
    if not blockers:  # Сайзим только если нет блокеров
        sizing_result = size_position(
            ctx,
            commission_pct=commission_pct,
            max_position_pct=max_position_pct,
        )
        ctx.sizing_info = {
            "size": sizing_result.size,
            "risk_amount": sizing_result.risk_amount,
            "risk_pct_actual": sizing_result.risk_pct_actual,
        }
        checks["sizing"] = {
            "size": sizing_result.size,
            "risk_amount": sizing_result.risk_amount,
            "risk_pct_actual": sizing_result.risk_pct_actual,
            "stop_distance": sizing_result.stop_distance,
            "commission": sizing_result.commission,
            "warnings": sizing_result.warnings,
        }
        warnings.extend(sizing_result.warnings)

        if sizing_result.size <= 1 and sizing_result.warnings:
            # Если warnings при size=1 → RESIZE (нужно пересмотреть параметры)
            blockers.append("Размер позиции = 1 (минимум) из-за ограничений")
    else:
        checks["sizing"] = {"skipped": True, "reason": "Есть блокеры выше"}

    # ── Вердикт ──────────────────────────────────────────────────────────────
    if blockers:
        verdict = VERDICT_BLOCKED
        first_blocker = blockers[0]
    elif any("лимит" in w for w in warnings) or checks.get("sizing", {}).get("warnings"):
        verdict = VERDICT_RESIZE
        first_blocker = ""
    elif warnings:
        verdict = VERDICT_WARN
        first_blocker = ""
    else:
        verdict = VERDICT_READY
        first_blocker = ""

    return PretradeReport(
        verdict=verdict,
        first_blocker=first_blocker,
        checks=checks,
        context=ctx,
        warnings=warnings,
    )
