"""Tests for Pre-Trade Check orchestrator."""

import numpy as np
import pandas as pd
import pytest

from app.skills.context import TradeContext
from app.skills.pretrade import PretradeReport, check_pretrade, VERDICT_READY, VERDICT_WARN, VERDICT_RESIZE, VERDICT_BLOCKED


def _make_candles(n: int = 250, trend: float = 0.001, vol: float = 0.01) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    returns = np.random.normal(trend, vol, n)
    prices = 250.0 * np.cumprod(1 + returns)
    return pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    }, index=dates)


# ── READY scenario ───────────────────────────────────────────────────────────

def test_pretrade_ready():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
        risk_pct=1.0,
    )
    df = _make_candles(n=250, trend=0.001)
    report = check_pretrade(ctx, regime_df=df)
    assert report.verdict == VERDICT_READY
    assert report.first_blocker == ""
    assert "regime" in report.checks
    assert "rr_check" in report.checks
    assert "sizing" in report.checks


# ── BLOCKED by news ──────────────────────────────────────────────────────────

def test_pretrade_blocked_by_news():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
    )
    report = check_pretrade(
        ctx,
        regime_df=None,
        news_blocked=True,
        news_reason="3 негативных новости",
    )
    assert report.verdict == VERDICT_BLOCKED
    assert "Новости" in report.first_blocker


# ── BLOCKED by bad RR ───────────────────────────────────────────────────────

def test_pretrade_blocked_by_rr():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=255.0,  # R:R = 0.5
    )
    report = check_pretrade(ctx)
    assert report.verdict == VERDICT_BLOCKED
    assert "R:R" in report.first_blocker


# ── WARN from regime ─────────────────────────────────────────────────────────

def test_pretrade_warn_regime():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
    )
    df = _make_candles(n=250, trend=-0.002, vol=0.01)  # downtrend
    report = check_pretrade(ctx, regime_df=df)
    # Regime warning but no blocker
    assert report.verdict in (VERDICT_WARN, VERDICT_READY)
    assert report.checks["regime"]["regime"] in ("down", "trend_down")


# ── WARN from high vol ───────────────────────────────────────────────────────

def test_pretrade_warn_high_vol():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
    )
    df = _make_candles(n=250, trend=0.0, vol=0.1)  # high vol
    report = check_pretrade(ctx, regime_df=df)
    assert report.verdict in (VERDICT_WARN, VERDICT_READY)


# ── Sizing ───────────────────────────────────────────────────────────────────

def test_pretrade_sizing_info():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
        risk_pct=1.0,
    )
    report = check_pretrade(ctx)
    sizing = report.checks["sizing"]
    assert sizing["size"] > 0
    assert sizing["risk_amount"] > 0


# ── No data ──────────────────────────────────────────────────────────────────

def test_pretrade_no_regime_data():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
    )
    report = check_pretrade(ctx, regime_df=None)
    assert report.checks["regime"]["skipped"] is True


# ── Short report ─────────────────────────────────────────────────────────────

def test_pretrade_short_report():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
        equity=1_000_000,
    )
    report = check_pretrade(ctx)
    text = report.short_report()
    assert "READY" in text or "SBER" in text


# ── as_dict ──────────────────────────────────────────────────────────────────

def test_pretrade_as_dict():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=270.0,
    )
    report = check_pretrade(ctx)
    d = report.as_dict()
    assert "verdict" in d
    assert "checks" in d
    assert "warnings" in d
    assert "checked_at" in d
