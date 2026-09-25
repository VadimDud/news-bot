"""HTTP-boundary tests for protected live controls."""

from unittest.mock import AsyncMock
import json

import pytest
from aiohttp import web

from app.web import app as web_app


class _Request:
    def __init__(self, form=None, path="/live"):
        self.form = form or {}
        self.path = path
        self.cookies = {}

    async def post(self):
        return self.form

    async def json(self):
        return self.form


@pytest.mark.asyncio
async def test_reset_endpoint_returns_conflict_while_live(monkeypatch):
    class Trader:
        def reset_circuit_breaker(self):
            raise RuntimeError("Сначала остановите live-цикл")

    monkeypatch.setattr(web_app, "live_trader", Trader())
    response = await web_app.live_reset_circuit(_Request(path="/live/reset-circuit"))

    assert response.status == 409
    assert "остановите live-цикл" in response.text


@pytest.mark.asyncio
async def test_dryrun_endpoint_returns_conflict_while_live(monkeypatch):
    class Trader:
        def set_dry_run(self, value):
            raise RuntimeError("Сначала остановите live-цикл перед сменой режима")

    monkeypatch.setattr(web_app, "live_trader", Trader())
    response = await web_app.live_dryrun(
        _Request({"dry_run": "false"}, path="/live/dryrun")
    )

    assert response.status == 409
    assert "сменой режима" in response.text


@pytest.mark.asyncio
async def test_strategy_error_is_html_escaped(monkeypatch):
    class Trader:
        def set_strategy(self, value):
            raise RuntimeError("bad <strategy>")

    monkeypatch.setattr(web_app, "live_trader", Trader())
    response = await web_app.live_strategy(_Request({"strategy": "rsi"}, "/live/strategy"))

    assert response.status == 200
    assert "bad &lt;strategy&gt;" in response.text
    assert "bad <strategy>" not in response.text


@pytest.mark.asyncio
async def test_protected_live_path_redirects_without_auth(monkeypatch):
    monkeypatch.setattr(web_app, "_effective_password", lambda: "configured")
    monkeypatch.setattr(web_app, "_current_user", lambda request: False)

    async def handler(request):
        return web.Response(text="should not run")

    with pytest.raises(web.HTTPFound) as raised:
        await web_app._auth_middleware(_Request(path="/live"), handler)

    assert raised.value.location == "/login"


@pytest.mark.asyncio
async def test_protected_live_path_reaches_handler_for_authenticated_user(monkeypatch):
    monkeypatch.setattr(web_app, "_effective_password", lambda: "configured")
    monkeypatch.setattr(web_app, "_current_user", lambda request: True)
    handler = AsyncMock(return_value=web.Response(text="ok"))
    request = _Request(path="/live/reset-circuit")

    response = await web_app._auth_middleware(request, handler)

    assert response.text == "ok"
    handler.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_adaptive_maneuver_endpoint_is_dry_run(monkeypatch):
    request = _Request({
        "ticker": "T", "direction": "LONG", "entry_price": 100,
        "current_price": 102, "new_stop_loss": 98, "new_take_profit": 105,
        "quantity": 1, "dry_run": True,
    }, path="/api/adaptive/maneuver")
    response = await web_app.adaptive_maneuver(request)

    assert response.status == 200
    body = json.loads(response.text)
    assert body["status"] == "DRY_RUN_VALIDATED"
    assert body["broker_action"] is None


@pytest.mark.asyncio
async def test_adaptive_candles_endpoint_limits_and_serializes(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(web_app, "_adaptive_frame", lambda ticker: pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=25, freq="15min"),
        "open": [100.0] * 25,
        "high": [101.0] * 25,
        "low": [99.0] * 25,
        "close": [100.5] * 25,
        "volume": [10.0] * 25,
    }))
    request = _Request(path="/api/adaptive/T/candles")
    request.query = {"limit": "10000"}
    request.match_info = {"ticker": "T"}

    response = await web_app.adaptive_candles(request)
    body = json.loads(response.text)

    assert response.status == 200
    assert body["ticker"] == "T"
    assert len(body["candles"]) == 25
    assert set(body["candles"][-1]) == {"time", "open", "high", "low", "close"}


@pytest.mark.asyncio
async def test_market_data_status_never_enables_orders(monkeypatch):
    monkeypatch.setattr(web_app, "config", web_app.config)
    response = await web_app.adaptive_market_data_status(_Request(path="/api/adaptive/market-data/status"))
    body = json.loads(response.text)

    assert response.status == 200
    assert body["orders_enabled"] is False


@pytest.mark.asyncio
async def test_market_data_status_reports_adapter_mode():
    response = await web_app.adaptive_market_data_status(_Request(path="/api/adaptive/market-data/status"))
    body = json.loads(response.text)

    assert body["adapter"] in {"UNAVAILABLE", "read_only_available"}
    assert body["orders_enabled"] is False
