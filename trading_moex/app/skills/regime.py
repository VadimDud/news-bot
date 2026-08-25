"""Market Regime Analysis — классификация рыночного режима.

По мотивам marian2js/trading-skills/market-regime-analysis.

Режимы:
- trend_up: EMA200 растёт, ATR стабилен, бычий тренд;
- trend_down: EMA200 падает, медвежий тренд;
- range: цена вокруг EMA200, нет чёткого тренда;
- high_vol: ATR выше нормы, волатильность расширена.

Используются готовые индикаторы из signals.py (EMA200, ATR).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .. import risk as risk_module


@dataclass
class RegimeResult:
    """Результат анализа рыночного режима."""

    regime: str  # "trend_up" | "trend_down" | "range" | "high_vol"
    confidence: float  # 0.0 - 1.0
    details: dict

    def as_warning(self) -> str:
        """Человекочитаемое предупреждение (для гейта)."""
        if self.regime == "down":
            return "Рынок в нисходящем тренде — входы не рекомендуются"
        if self.regime == "high_vol":
            return "Высокая волатильность — расширяйте стопы или уменьшайте размер"
        if self.regime == "range":
            return "Боковой рынок — ставки на пробой могут не сработать"
        return ""


# ── Константы ────────────────────────────────────────────────────────────────

EMA_LONG_PERIOD = 200  # EMA для определения долгосрочного тренда
ATR_PERCENTILE_WINDOW = 100  # окно для расчёта среднего ATR


def classify_regime(
    df: pd.DataFrame,
    ema_period: int = EMA_LONG_PERIOD,
    atr_period: int = 14,
) -> RegimeResult:
    """Классифицировать рыночный режим по свечам.

    df должен содержать OHLCV и быть отсортирован по времени.
    Минимум ~200 баров для EMA200.
    """
    details: dict = {}

    if df.empty or len(df) < max(ema_period, ATR_PERCENTILE_WINDOW):
        return RegimeResult(
            regime="range",
            confidence=0.1,
            details={"error": f"Недостаточно данных ({len(df)} баров)"},
        )

    # EMA для тренда
    ema = df["close"].ewm(span=ema_period, adjust=False).mean()
    ema_current = float(ema.iloc[-1])
    ema_prev = float(ema.iloc[-5]) if len(ema) >= 5 else ema_current
    price = float(df["close"].iloc[-1])

    # ATR для волатильности
    atr_series = risk_module.atr(df, period=atr_period)
    atr_current = float(atr_series.iloc[-1])

    details["price"] = round(price, 2)
    details["ema200"] = round(ema_current, 2)
    details["atr"] = round(atr_current, 4)

    # Классификация
    regime = "range"
    confidence = 0.5

    # ATR как % от цены — абсолютная мера волатильности
    atr_pct_of_price = (atr_current / price * 100) if price > 0 else 0
    details["atr_pct_of_price"] = round(atr_pct_of_price, 2)

    # ATR-среднее за окно для определения роста волатильности
    atr_long_avg = atr_series.rolling(ATR_PERCENTILE_WINDOW, min_periods=20).mean()
    atr_long_avg_val = float(atr_long_avg.iloc[-1]) if not pd.isna(atr_long_avg.iloc[-1]) else atr_current
    atr_expansion = atr_current / atr_long_avg_val if atr_long_avg_val > 0 else 1.0
    details["atr_expansion"] = round(atr_expansion, 2)

    # Высокая волатильность: ATR > 4% от цены ИЛИ ATR расширился > 2× относительно среднего
    high_vol_absolute = atr_pct_of_price >= 4.0
    high_vol_expansion = atr_expansion >= 2.0
    if high_vol_absolute or high_vol_expansion:
        regime = "high_vol"
        confidence = min(0.7 + atr_expansion * 0.1, 0.95)
        details["reason"] = (
            f"ATR {atr_pct_of_price:.1f}% от цены"
            + (f", расширение {atr_expansion:.1f}×" if high_vol_expansion else "")
        )
        return RegimeResult(regime=regime, confidence=confidence, details=details)

    # Тренд: цена vs EMA200 + направление EMA
    above_ema = price > ema_current
    ema_rising = ema_current > ema_prev
    ema_falling = ema_current < ema_prev

    if above_ema and ema_rising:
        regime = "trend_up"
        confidence = 0.75
        details["reason"] = "Цена выше EMA200, EMA растёт"
    elif not above_ema and ema_falling:
        regime = "trend_down"
        confidence = 0.75
        details["reason"] = "Цена ниже EMA200, EMA падает"
    else:
        regime = "range"
        confidence = 0.6
        details["reason"] = (
            "Цена около EMA200, нет чёткого тренда"
        )

    return RegimeResult(regime=regime, confidence=confidence, details=details)
