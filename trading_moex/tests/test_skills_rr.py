"""Tests for Risk-Reward Sanity Check skill."""

import pytest

from app.skills.context import TradeContext
from app.skills.rr_check import RRResult, check_rr


# ── Basic checks ─────────────────────────────────────────────────────────────

def test_rr_good_long():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,  # стоп 10
        target=270.0,  # тейк 20
        atr=5.0,
    )
    result = check_rr(ctx)
    assert result.ok is True
    assert result.rr_ratio == 2.0


def test_rr_good_short():
    ctx = TradeContext(
        ticker="LKOH",
        direction="short",
        entry=7000.0,
        stop=7100.0,  # стоп 100
        target=6800.0,  # тейк 200
        atr=50.0,
    )
    result = check_rr(ctx)
    assert result.ok is True
    assert result.rr_ratio == 2.0


# ── Low R:R blocker ─────────────────────────────────────────────────────────

def test_rr_low_ratio_blocked():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,  # стоп 10
        target=255.0,  # тейк 5 → R:R = 0.5
        atr=5.0,
    )
    result = check_rr(ctx)
    assert result.ok is False
    assert result.rr_ratio == 0.5
    assert any("R:R" in b for b in result.blockers)


def test_rr_custom_min_ratio():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=268.0,  # R:R = 1.8
        atr=5.0,
    )
    result = check_rr(ctx, min_rr=2.0)
    assert result.ok is False
    assert result.rr_ratio == 1.8


# ── Edge cases ───────────────────────────────────────────────────────────────

def test_rr_no_entry():
    ctx = TradeContext(ticker="SBER")
    result = check_rr(ctx)
    assert result.ok is False
    assert any("entry не задан" in b for b in result.blockers)


def test_rr_no_stop():
    ctx = TradeContext(ticker="SBER", entry=250.0)
    result = check_rr(ctx)
    assert result.ok is False
    assert any("stop не задан" in b for b in result.blockers)


def test_rr_no_target():
    ctx = TradeContext(ticker="SBER", entry=250.0, stop=240.0)
    result = check_rr(ctx)
    assert result.ok is False
    assert any("target не задан" in b for b in result.blockers)


def test_rr_stop_above_entry():
    ctx = TradeContext(
        ticker="SBER", direction="long", entry=250.0, stop=260.0, target=240.0
    )
    result = check_rr(ctx)
    assert result.ok is False


def test_rr_target_below_entry_long():
    ctx = TradeContext(
        ticker="SBER", direction="long", entry=250.0, stop=240.0, target=245.0
    )
    result = check_rr(ctx)
    assert result.ok is False
    assert any("нет потенциала" in b for b in result.blockers)


# ── ATR warnings ─────────────────────────────────────────────────────────────

def test_rr_stop_too_narrow():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=249.5,  # стоп 0.5 при ATR=5 → 0.1×ATR
        target=260.0,
        atr=5.0,
    )
    result = check_rr(ctx, min_atr_stop=0.2)
    assert result.ok is True
    assert any("узкий" in w for w in result.warnings)


def test_rr_stop_too_wide():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=230.0,  # стоп 20 при ATR=5 → 4×ATR
        target=290.0,
        atr=5.0,
    )
    result = check_rr(ctx, max_atr_stop=3.0)
    assert result.ok is True
    assert any("широкий" in w for w in result.warnings)


def test_rr_target_too_far():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=300.0,  # тейк 50 при ATR=5 → 10×ATR
        atr=5.0,
    )
    result = check_rr(ctx, max_atr_target=8.0)
    assert result.ok is True
    assert any("маловероятно" in w for w in result.warnings)


# ── Target % warning ─────────────────────────────────────────────────────────

def test_rr_target_too_far_pct():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        target=350.0,  # 40% от цены
        atr=5.0,
    )
    result = check_rr(ctx)
    assert result.ok is True
    # target_dist = 100; 100/250*100 = 40%
    assert any("40.0%" in w for w in result.warnings)
