"""Tests for Position Sizing skill."""

import pytest

from app.skills.context import TradeContext
from app.skills.sizing import SizingResult, size_position


# ── Basic sizing ─────────────────────────────────────────────────────────────

def test_sizing_basic_long():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        equity=1_000_000,
        risk_pct=1.0,
    )
    result = size_position(ctx, commission_pct=0)  # без комиссий для точного расчёта
    # risk = 1% of 1M = 10000; stop_dist = 10; size = 10000/10 = 1000
    assert result.size == 1000
    assert result.risk_amount > 0
    assert result.stop_distance == 10.0


def test_sizing_basic_short():
    ctx = TradeContext(
        ticker="LKOH",
        direction="short",
        entry=7000.0,
        stop=7100.0,
        equity=100_000_000,
        risk_pct=2.0,
    )
    result = size_position(ctx, commission_pct=0, max_position_pct=100.0)
    # risk = 2% of 100M = 2_000_000; stop_dist = 100; raw size = 20_000
    # max = 100% of 100M / 7000 = 14285 → capped
    assert result.size == 14285
    assert result.stop_distance == 100.0
    assert any("лимит" in w for w in result.warnings)


# ── Edge cases ───────────────────────────────────────────────────────────────

def test_sizing_no_entry():
    ctx = TradeContext(ticker="SBER", direction="long", entry=0, equity=1_000_000)
    result = size_position(ctx)
    assert result.size == 1
    assert any("entry не задан" in w for w in result.warnings)


def test_sizing_no_stop():
    ctx = TradeContext(ticker="SBER", direction="long", entry=250.0, equity=1_000_000)
    result = size_position(ctx)
    assert result.size == 1
    assert any("stop не задан" in w for w in result.warnings)


def test_sizing_stop_above_entry():
    ctx = TradeContext(
        ticker="SBER", direction="long", entry=250.0, stop=260.0, equity=1_000_000
    )
    result = size_position(ctx)
    assert result.size == 1
    assert any("стоп за ценой входа" in w for w in result.warnings)


# ── Max position limit ───────────────────────────────────────────────────────

def test_sizing_max_position_limit():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,  # нормальный стоп = 10
        equity=10_000_000,
        risk_pct=10.0,  # высокий риск чтобы size превысил лимит
    )
    result = size_position(ctx, commission_pct=0, max_position_pct=10.0)
    # risk = 10% of 10M = 1_000_000; stop_dist = 10; raw size = 100_000
    # max = 10% of 10M / 250 = 4000 лотов
    assert result.size <= 4000
    assert any("лимит" in w for w in result.warnings)


# ── Commission impact ────────────────────────────────────────────────────────

def test_sizing_with_commission():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        equity=1_000_000,
        risk_pct=1.0,
    )
    result_no_comm = size_position(ctx, commission_pct=0)
    result_with_comm = size_position(ctx, commission_pct=0.1)
    # С комиссией размер должен быть меньше
    assert result_with_comm.size <= result_no_comm.size


# ── Min stop distance ────────────────────────────────────────────────────────

def test_sizing_min_stop_distance():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=249.5,  # 0.2% стоп
        equity=1_000_000,
        risk_pct=1.0,
    )
    result = size_position(ctx)
    # min_stop = 250 * 0.005 = 1.25
    # size should use adjusted stop_dist
    assert result.size > 0


# ── Result structure ─────────────────────────────────────────────────────────

def test_sizing_result_has_all_fields():
    ctx = TradeContext(
        ticker="SBER",
        direction="long",
        entry=250.0,
        stop=240.0,
        equity=1_000_000,
        risk_pct=1.0,
    )
    result = size_position(ctx)
    assert isinstance(result, SizingResult)
    assert result.size > 0
    assert result.risk_amount >= 0
    assert result.risk_pct_actual >= 0
    assert result.commission >= 0
