"""Opt-in read-only market-data lifecycle task."""

from __future__ import annotations

import asyncio
import logging

from . import config
from .tbank_market_data import TBankMarketDataAdapter, stream_to_storage

logger = logging.getLogger(__name__)


async def _resolve_figis(tickers: tuple[str, ...]) -> dict[str, str]:
    """Resolve FIGIs through T-Bank instruments without exposing the token."""
    from tinkoff.invest import AsyncClient  # type: ignore[import-not-found]
    from . import settings, tinkoff_ssl

    tinkoff_ssl.install_ru_ca()
    result: dict[str, str] = {}
    async with AsyncClient(token=settings.tinkoff_token(), app_name="moex-adaptive-readonly") as client:
        for ticker in tickers:
            response = await client.instruments.find_instrument(query=ticker)
            matches = [item for item in response.instruments if item.ticker.upper() == ticker and item.figi]
            if matches:
                result[ticker] = matches[0].figi
    return result


async def market_data_loop() -> None:
    """Run read-only stream when explicitly enabled; otherwise return immediately."""
    if not config.TRADER_MARKET_DATA_ENABLED:
        logger.info("Read-only market-data stream disabled")
        return
    token = __import__("app.settings", fromlist=["tinkoff_token"]).tinkoff_token()
    if not token:
        logger.warning("Read-only market-data stream unavailable: TINKOFF_API_TOKEN missing")
        return
    tickers = tuple(t.upper() for t in config.WATCH_TICKERS)
    try:
        subscriptions = await _resolve_figis(tickers)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Read-only market-data FIGI resolution failed: %s", exc)
        return
    if not subscriptions:
        logger.warning("Read-only market-data stream: no FIGIs resolved")
        return
    adapter = TBankMarketDataAdapter(token, subscriptions, reconnect_delay=config.TRADER_MARKET_DATA_RECONNECT_SEC)
    try:
        await stream_to_storage(adapter, str(config.DB_PATH))
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("Read-only market-data stream stopped unexpectedly")
