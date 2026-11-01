"""Tests for safe live configuration validation."""

from app import config


def test_live_config_accepts_safe_dry_run(monkeypatch):
    monkeypatch.setattr(config, "POLL_INTERVAL", 60)
    monkeypatch.setattr(config, "WATCH_TICKERS", ["SBER"])
    monkeypatch.setattr(config, "TRADER_MAX_POSITION_PCT", 50.0)
    monkeypatch.setattr(config, "TRADER_MAX_DAILY_LOSS_PCT", 2.0)
    monkeypatch.setattr(config, "TRADER_MAX_DRAWDOWN_PCT", 10.0)

    errors, warnings = config.live_config_issues(dry_run=True)

    assert errors == []
    assert warnings == []


def test_live_config_rejects_live_without_credentials(monkeypatch):
    monkeypatch.setattr(config, "POLL_INTERVAL", 60)
    monkeypatch.setattr(config, "WATCH_TICKERS", ["SBER"])
    monkeypatch.setattr(config, "TRADER_MAX_POSITION_PCT", 50.0)
    monkeypatch.setattr(config, "TINKOFF_API_TOKEN", "")
    errors, _ = config.live_config_issues(
        dry_run=False,
        web_password_configured=False,
        token_configured=False,
    )

    assert any("TRADER_WEB_PASSWORD" in error for error in errors)
    assert any("TINKOFF_API_TOKEN" in error for error in errors)


def test_live_config_rejects_invalid_limits(monkeypatch):
    monkeypatch.setattr(config, "TRADER_MAX_POSITION_PCT", 0.0)
    monkeypatch.setattr(config, "TRADER_MAX_DAILY_LOSS_PCT", -1.0)

    errors, _ = config.live_config_issues(dry_run=True)

    assert any("TRADER_MAX_POSITION_PCT" in error for error in errors)
    assert any("отрицательными" in error for error in errors)
