"""Точка входа MOEX-торгового контейнера: веб-дашборд + управление live-циклом."""

import asyncio
import contextlib
import logging
import sys

from aiohttp import web

from app import config, storage
from app.web.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("moex_trader")


async def main() -> None:
    storage.init_db()

    from app import tinkoff_ssl

    if not tinkoff_ssl.install_ru_ca():
        logger.warning("Российские CA не установлены — T-Bank API может быть недоступен")

    from app.live import live_trader
    from app import settings as app_settings

    live_trader.tickers = list(config.WATCH_TICKERS)

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEB_HOST, config.WEB_PORT)
    await site.start()
    logger.info("MOEX Trader dashboard: http://%s:%s", config.WEB_HOST, config.WEB_PORT)
    logger.info(
        "Dry-run=%s, poll=%ss, тикеры=%s, стратегия=%s",
        config.DRY_RUN, config.POLL_INTERVAL, config.WATCH_TICKERS, live_trader.strategy,
    )

    if not app_settings.tinkoff_token():
        logger.warning("TINKOFF_API_TOKEN не задан — live-торговля недоступна, только бэктест")

    # Запустить фоновый сканер сигналов (ежедневно после открытия рынка)
    signal_task: asyncio.Task | None = None
    if config.TRADER_SIGNALS_ENABLED:
        from app.signal_notifier import scan_loop

        logger.info(
            "Starting signal notifier scheduler (scan daily at %02d:%02d UTC)",
            config.TRADER_SIGNALS_SCAN_HOUR, config.TRADER_SIGNALS_SCAN_MINUTE,
        )
        signal_task = asyncio.create_task(scan_loop())
    else:
        logger.info("Signal notifier disabled via TRADER_SIGNALS_ENABLED")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        if signal_task is not None:
            signal_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await signal_task
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено")
