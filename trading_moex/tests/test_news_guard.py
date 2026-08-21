"""Tests for News Guard: AI severity, cache, user overrides, blocking logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app import storage
from app.news_guard import NewsGuard, _rule_based_severity, _hash_title


# ── Content hash ─────────────────────────────────────────────────────────────

def test_hash_title_deterministic():
    h1 = _hash_title("Сбербанк снизил дивиденды на 30%")
    h2 = _hash_title("Сбербанк снизил дивиденды на 30%")
    assert h1 == h2
    assert len(h1) == 64  # 4 x 16-hex


def test_hash_title_different_for_different_titles():
    h1 = _hash_title("Сбербанк снизил дивиденды")
    h2 = "а" * 100  # different length to ensure different hash
    h2_hash = _hash_title(h2)
    assert h1 != h2_hash


# ── Rule-based severity ─────────────────────────────────────────────────────

def test_rule_based_catastrophic():
    result = _rule_based_severity("Дефолт компании", "")
    assert result["severity"] < -0.5


def test_rule_based_severe_negative():
    result = _rule_based_severity("Компанияreports убыток за квартал", "")
    assert result["severity"] < 0


def test_rule_based_mild_positive():
    result = _rule_based_severity("Компания reports рост выручки", "")
    assert result["severity"] > 0


def test_rule_based_neutral():
    result = _rule_based_severity("Обычная новость без триггеров", "")
    assert result["severity"] == 0.0


def test_rule_based_strong_positive():
    result = _rule_based_severity("Рекордная прибыль компании", "мажорн")
    assert result["severity"] >= 0.5


# ── User overrides ───────────────────────────────────────────────────────────

def test_user_override_block():
    storage.set_user_override("hash1", "SBER", "block", "Санкции")
    overrides = storage.get_user_overrides("SBER")
    assert len(overrides) == 1
    assert overrides[0]["action"] == "block"
    assert overrides[0]["reason"] == "Санкции"


def test_user_override_ignore():
    storage.set_user_override("hash2", "SBER", "ignore")
    overrides = storage.get_user_overrides("SBER")
    assert len(overrides) == 1
    assert overrides[0]["action"] == "ignore"


def test_user_override_reset():
    storage.set_user_override("hash3", "SBER", "block")
    storage.set_user_override("hash3", "SBER", "none")
    overrides = storage.get_user_overrides("SBER")
    assert len(overrides) == 0


def test_user_override_get_single():
    storage.set_user_override("hash4", "SBER", "block", "test")
    o = storage.get_user_override("hash4", "SBER")
    assert o is not None
    assert o["action"] == "block"


def test_user_override_get_single_none():
    o = storage.get_user_override("nonexistent", "SBER")
    assert o is None


# ── News cache ───────────────────────────────────────────────────────────────

def test_cache_news_sentiment():
    storage.cache_news_sentiment(
        content_hash="abc123",
        ticker="SBER",
        title="Сбер объявил дивиденды",
        summary="Дивиденды 25 руб",
        impact="POSITIVE",
        severity=0.7,
        reason="Высокие дивиденды",
        source="rbc",
        created_at="2026-01-01T12:00:00",
    )
    cached = storage.get_cached_sentiments("SBER")
    assert len(cached) == 1
    assert cached[0]["severity"] == 0.7
    assert cached[0]["impact"] == "POSITIVE"


def test_cache_news_sentiment_upsert():
    storage.cache_news_sentiment("h1", "SBER", "title1", "", "NEUTRAL", None, None, None, "2026-01-01")
    storage.cache_news_sentiment("h1", "SBER", "title2", "", "NEGATIVE", -0.8, "bad", None, "2026-01-01")
    cached = storage.get_cached_sentiments("SBER")
    assert len(cached) == 1
    assert cached[0]["severity"] == -0.8


def test_get_pending_severity():
    storage.cache_news_sentiment("p1", "SBER", "title", "", "NEUTRAL", None, None, None, "2026-01-01")
    storage.cache_news_sentiment("p2", "SBER", "title2", "", "POSITIVE", 0.5, "ok", None, "2026-01-01")
    pending = storage.get_pending_severity("SBER")
    assert len(pending) == 1
    assert pending[0]["content_hash"] == "p1"


def test_get_cached_sentiments_since():
    storage.cache_news_sentiment("s1", "SBER", "old", "", "NEUTRAL", 0.0, None, None, "2026-01-01")
    storage.cache_news_sentiment("s2", "SBER", "new", "", "POSITIVE", 0.5, None, None, "2026-06-01")
    cached = storage.get_cached_sentiments("SBER", since_iso="2026-03-01")
    assert len(cached) == 1
    assert cached[0]["title"] == "new"


# ── NewsGuard.is_blocked ─────────────────────────────────────────────────────

def test_not_blocked_when_no_news():
    guard = NewsGuard(lookback_hours=48, max_negative=2)
    blocked, reason = guard.is_blocked("SBER")
    assert not blocked
    assert reason == ""


def test_blocked_by_user_override():
    storage.set_user_override("hash_block", "SBER", "block", "Санкции")
    guard = NewsGuard(lookback_hours=48, max_negative=2)
    blocked, reason = guard.is_blocked("SBER")
    assert blocked
    assert "Санкции" in reason


def test_not_blocked_when_user_ignore():
    now = datetime.now(timezone.utc)
    # Cache 3 negative news
    for i in range(3):
        storage.cache_news_sentiment(
            f"neg{i}", "SBER", f"Bad news {i}", "", "NEGATIVE", -0.7, "bad", None,
            (now - timedelta(hours=i)).isoformat(),
        )
    # User ignores ALL of them
    for i in range(3):
        storage.set_user_override(f"neg{i}", "SBER", "ignore")
    guard = NewsGuard(lookback_hours=48, max_negative=2)
    blocked, reason = guard.is_blocked("SBER")
    assert not blocked  # all negatives are ignored by user


def test_blocked_by_severity_threshold():
    now = datetime.now(timezone.utc)
    for i in range(3):
        storage.cache_news_sentiment(
            f"sev{i}", "SBER", f"Bad {i}", "", "NEGATIVE", -0.8, "catastrophic", None,
            (now - timedelta(hours=i)).isoformat(),
        )
    guard = NewsGuard(lookback_hours=48, max_negative=2, severity_threshold=-0.5)
    blocked, reason = guard.is_blocked("SBER")
    assert blocked


def test_not_blocked_when_mild_negatives():
    now = datetime.now(timezone.utc)
    # Only 1 negative — below max_negative=2 threshold
    storage.cache_news_sentiment(
        "mild1", "SBER", "Slight concern", "", "NEGATIVE", -0.3, "minor", None,
        (now - timedelta(hours=1)).isoformat(),
    )
    guard = NewsGuard(lookback_hours=48, max_negative=2)
    blocked, reason = guard.is_blocked("SBER")
    assert not blocked


def test_not_blocked_outside_lookback():
    old = datetime.now(timezone.utc) - timedelta(hours=100)
    for i in range(5):
        storage.cache_news_sentiment(
            f"old{i}", "SBER", f"Old bad {i}", "", "NEGATIVE", -0.9, "old", None,
            (old + timedelta(hours=i)).isoformat(),
        )
    guard = NewsGuard(lookback_hours=48, max_negative=2)
    blocked, reason = guard.is_blocked("SBER")
    assert not blocked  # news are too old


def test_news_guard_scoring_mode_integration():
    """Scoring mode with news_guard=1: verify param exists."""
    from app.strategies import ROEPortfolioStrategy, _ROE_PORTFOLIO_PARAMS_TUPLE
    param_keys = [p[0] for p in _ROE_PORTFOLIO_PARAMS_TUPLE]
    assert "news_guard" in param_keys
