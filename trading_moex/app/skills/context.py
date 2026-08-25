"""Trade Context — компактная схема, передаваемая между скиллами.

Аналог markdown Trade Context из marian2js/trading-skills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TradeContext:
    """Контекст сделки, передаваемый между скиллами."""

    ticker: str
    direction: str = ""  # "long" | "short" | ""
    entry: float = 0.0
    stop: float | None = None
    target: float | None = None
    equity: float = 100_000.0
    risk_pct: float = 1.0  # % от equity
    atr: float = 0.0
    atr_period: int = 14
    atr_mult: float = 1.5
    rr_ratio: float = 2.0
    timeframe: str = ""  # "intraday" | "swing" | "position" | ""

    # Режим рынка (заполняется regime-скиллом)
    regime: str = ""  # "trend_up" | "range" | "down" | "high_vol" | ""
    regime_details: dict = field(default_factory=dict)

    # Новостной контекст (из NewsGuard)
    news_blocked: bool = False
    news_reason: str = ""

    # Тезис (из thesis-validation, ручной режим)
    thesis_verdict: str = ""  # "ready" | "not_ready" | "unclear" | ""
    thesis_missing: list[str] = field(default_factory=list)

    # Данные о свежести
    candles_fresh: bool = True
    data_staleness_hours: float = 0.0
    checked_at: datetime = field(default_factory=lambda: datetime.utcnow())

    # Дополнительные метрики от скиллов
    sizing_info: dict[str, Any] = field(default_factory=dict)
    rr_info: dict[str, Any] = field(default_factory=dict)

    def short_report(self) -> str:
        """Краткий человекочитаемый отчёт."""
        parts = [f"{self.ticker}: {self.direction or '?'}"]
        if self.entry:
            parts.append(f"entry={self.entry:.2f}")
        if self.stop:
            parts.append(f"stop={self.stop:.2f}")
        if self.target:
            parts.append(f"target={self.target:.2f}")
        if self.regime:
            parts.append(f"regime={self.regime}")
        if self.news_blocked:
            parts.append(f"NEWS_BLOCKED({self.news_reason})")
        if self.sizing_info.get("size"):
            parts.append(f"size={self.sizing_info['size']}")
        return " | ".join(parts)
