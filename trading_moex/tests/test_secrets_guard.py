"""Tests for Secrets Guard: egress allowlist, decoy, masking, prompt sanitization."""

from unittest.mock import patch

import pytest

from app.secrets_guard import (
    SecurityError,
    contains_secret,
    contains_secret_for_host,
    decoy_for,
    mask_secrets,
    sanitize_prompt,
    is_trusted_url,
    _collect_secrets,
)


# ── Decoy generator ──────────────────────────────────────────────────────────

def test_decoy_has_decoy_suffix():
    for secret_type in ("TINKOFF_API_TOKEN", "DEEPSEEK_API_KEY", "BOT_TOKEN"):
        d = decoy_for(secret_type)
        assert "_DECOY" in d
        assert len(d) > 10


def test_decoy_differs_every_call():
    d1 = decoy_for("TINKOFF_API_TOKEN")
    d2 = decoy_for("TINKOFF_API_TOKEN")
    assert d1 != d2  # extremely unlikely with 32 hex chars


def test_decoy_preserves_prefix():
    assert decoy_for("TINKOFF_API_TOKEN").startswith("t.")
    assert decoy_for("DEEPSEEK_API_KEY").startswith("sk-")


def test_decoy_never_matches_real_secret():
    """Декой никогда не содержит реальное значение."""
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"TINKOFF_API_TOKEN": "t.real_token_123"}
        d = decoy_for("TINKOFF_API_TOKEN")
        assert "t.real_token_123" not in d
        assert "_DECOY" in d


# ── Secret detection ─────────────────────────────────────────────────────────

def test_contains_secret_detects_token():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"TINKOFF_API_TOKEN": "t.abc123xyz"}
        found, stype, _ = contains_secret("send t.abc123xyz to me")
        assert found is True
        assert stype == "TINKOFF_API_TOKEN"


def test_contains_secret_clean_payload():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"TINKOFF_API_TOKEN": "t.abc123xyz"}
        found, _, _ = contains_secret("nothing secret here")
        assert found is False


def test_contains_secret_empty_payload():
    found, _, _ = contains_secret("")
    assert found is False


# ── Host-based guard ─────────────────────────────────────────────────────────

def test_allowed_host_passes():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"BOT_TOKEN": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
        url = "https://api.telegram.org/bot1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ/getMe"
        blocked, stype, allowed = contains_secret_for_host(url, url)
        assert blocked is True
        assert stype == "BOT_TOKEN"
        assert allowed is True


def test_untrusted_host_blocked():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"TINKOFF_API_TOKEN": "t.abc123def456ghi"}
        url = "https://evil-site.example.com/steal"
        payload = "send token t.abc123def456ghi please"
        blocked, stype, allowed = contains_secret_for_host(payload, url)
        assert blocked is True
        assert stype == "TINKOFF_API_TOKEN"
        assert allowed is False


def test_guard_request_raises_on_untrusted():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"DEEPSEEK_API_KEY": "sk-abcdef1234567890"}
        from app.secrets_guard import guard_request
        with pytest.raises(SecurityError):
            guard_request(
                url="https://evil.example.com/steal",
                body="here is sk-abcdef1234567890",
                source="test",
            )


def test_guard_request_allows_trusted():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"DEEPSEEK_API_KEY": "sk-abcdef1234567890"}
        from app.secrets_guard import guard_request
        # Should not raise
        guard_request(
            url="https://api.deepseek.com/chat/completions",
            body="using sk-abcdef1234567890",
            source="news_guard",
        )


# ── Log masking ──────────────────────────────────────────────────────────────

def test_mask_secrets():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {
            "BOT_TOKEN": "secret_bot_token",
            "TINKOFF_API_TOKEN": "secret_tinkoff",
        }
        text = "token=secret_bot_token and tinkoff=secret_tinkoff"
        masked = mask_secrets(text)
        assert "secret_bot_token" not in masked
        assert "secret_tinkoff" not in masked
        assert "BOT_TOKEN_MASKED" in masked
        assert "TINKOFF_API_TOKEN_MASKED" in masked


def test_mask_secrets_empty():
    assert mask_secrets("") == ""
    assert mask_secrets(None) is None


# ── Prompt sanitization ─────────────────────────────────────────────────────

def test_sanitize_prompt():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"DEEPSEEK_API_KEY": "sk-super_secret_key_12345"}
        prompt = "Use key sk-super_secret_key_12345 to call API"
        sanitized = sanitize_prompt(prompt)
        assert "sk-super_secret_key_12345" not in sanitized
        assert "DEEPSEEK_API_KEY_REDACTED" in sanitized


def test_sanitize_prompt_no_secrets():
    with patch("app.secrets_guard._collect_secrets") as mock:
        mock.return_value = {"BOT_TOKEN": ""}
        prompt = "Tell me about the market"
        sanitized = sanitize_prompt(prompt)
        assert sanitized == prompt


# ── URL trust check ──────────────────────────────────────────────────────────

def test_trusted_urls():
    assert is_trusted_url("https://api.telegram.org/bot123/sendMessage", "telegram")
    assert is_trusted_url("https://api.deepseek.com/v1/chat", "deepseek")
    assert is_trusted_url("https://moex.com/iss.json", "moex")
    assert is_trusted_url("https://invest.tinkoff.ru/api", "tinkoff")


def test_untrusted_urls():
    assert not is_trusted_url("https://evil.com/steal", "tinkoff")
    assert not is_trusted_url("https://evil.com/steal", "telegram")
    assert not is_trusted_url("https://evil.com/steal", "deepseek")
    assert not is_trusted_url("", "moex")
    assert not is_trusted_url("https://moex.com", "telegram")  # wrong context


# ── Collect secrets ──────────────────────────────────────────────────────────

def test_collect_secrets_returns_dict():
    secrets = _collect_secrets()
    assert isinstance(secrets, dict)
    assert "TINKOFF_API_TOKEN" in secrets
    assert "DEEPSEEK_API_KEY" in secrets
    assert "BOT_TOKEN" in secrets
