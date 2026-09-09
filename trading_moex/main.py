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


def report_startup_state(live_trader) -> None:
    """Логирует сводку конфигурации сканеров/уведомлений без секретов.

    Помогает понять, что фактически включено после применения env.
    """
    logger.info("── Стартовая конфигурация уведомлений ────────────────────────────")
    logger.info("Telegram: %s, chat=%s, proxy=%s",
                "токен задан" if config.TELEGRAM_BOT_TOKEN else "токен ОТСУТСТВУЕТ",
                "задан" if config.TELEGRAM_CHAT_ID else "ОТСУТСТВУЕТ",
                config.TRADER_TG_PROXY or "нет")
    notifiers = [
        ("ROE+P/B", config.TRADER_SIGNALS_ENABLED, config.TRADER_SIGNALS_RUN_ON_STARTUP),
        ("Elliott", config.TRADER_ELLIOTT_ENABLED, config.TRADER_ELLIOTT_RUN_ON_STARTUP),
        ("Fibonacci", config.TRADER_FIB_ENABLED, config.TRADER_FIB_RUN_ON_STARTUP),
        ("MTF", config.TRADER_MTF_ENABLED, config.TRADER_MTF_RUN_ON_STARTUP),
    ]
    for name, enabled, on_startup in notifiers:
        logger.info("Сканер %-9s: enabled=%s, run_on_startup=%s", name, enabled, on_startup)
    logger.info("Live: dry_run=%s, token=%s, стратегия=%s, навыки=%s(%s)",
                config.DRY_RUN,
                "задан" if config.TINKOFF_API_TOKEN else "не задан",
                live_trader.strategy,
                config.TRADER_SKILLS_ENABLED, config.TRADER_SKILLS_MODE)
    logger.info("Watchlist: %s", config.WATCH_TICKERS)
    logger.info("──────────────────────────────────────────────────────────────")


def _dead_tasks(tasks: dict[str, asyncio.Task | None]) -> list[str]:
    """Имена задач, завершившихся не по штатной отмене и с исключением (краш)."""
    dead = []
    for name, task in tasks.items():
        if task is None:
            continue
        # Крашем считаем только завершение с необработанным исключением.
        # Штатное завершение (return) и отмена (cancelled) не считаются.
        if task.done() and not task.cancelled() and task.exception() is not None:
            dead.append(name)
    return dead


async def _notify_dead(tasks: dict[str, asyncio.Task | None], logged: set[str]) -> None:
    """Один проход watchdog: алерт в Telegram по крашнутым и ещё не логированным задачам."""
    from app.signal_notifier import send_telegram_message

    for name in _dead_tasks(tasks):
        if name in logged:
            continue
        task = tasks[name]
        exc = task.exception()
        logger.error("Watchdog: задача %s неожиданно завершилась: %s", name, exc)
        logged.add(name)
        msg = (
            f"⚠️ WATCHDOG MOEX-трейдера\nЗадача «{name}» неожиданно "
            f"завершилась: {exc}\nСканер больше не работает — проверьте логи."
        )
        try:
            await send_telegram_message(msg)
        except Exception:  # noqa: BLE001
            logger.exception("Watchdog: не удалось отправить алерт в Telegram")


async def _watchdog(tasks: dict[str, asyncio.Task | None]) -> None:
    """Мониторинг фоновых задач: алерт в Telegram при неожиданной смерти.

    CancelledError (штатная остановка) игнорируется — алерт только на
    реальный краш (task.done() с исключением).
    """
    logged: set[str] = set()
    while True:
        await asyncio.sleep(300)  # проверка раз в 5 минут
        await _notify_dead(tasks, logged)


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
        live_trader.dry_run, config.POLL_INTERVAL, config.WATCH_TICKERS, live_trader.strategy,
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

    # Запустить фоновый сканер Elliott micro-wave сигналов (ежедневно вечером)
    elliott_task: asyncio.Task | None = None
    if config.TRADER_ELLIOTT_ENABLED:
        from app.elliott_notifier import elliott_scan_loop

        logger.info(
            "Starting Elliott signal notifier (scan daily at %02d:%02d UTC)",
            config.TRADER_ELLIOTT_SCAN_HOUR, config.TRADER_ELLIOTT_SCAN_MINUTE,
        )
        elliott_task = asyncio.create_task(elliott_scan_loop())
    else:
        logger.info("Elliott notifier disabled via TRADER_ELLIOTT_ENABLED")

    # Запустить фоновый сканер Fibonacci-re-tracement сигналов (ежедневно вечером)
    fib_task: asyncio.Task | None = None
    if config.TRADER_FIB_ENABLED:
        from app.fib_notifier import fib_scan_loop

        logger.info(
            "Starting Fibonacci signal notifier (scan daily at %02d:%02d UTC)",
            config.TRADER_FIB_SCAN_HOUR, config.TRADER_FIB_SCAN_MINUTE,
        )
        fib_task = asyncio.create_task(fib_scan_loop())
    else:
        logger.info("Fibonacci notifier disabled via TRADER_FIB_ENABLED")

    # Доскачивание 4h-свечей для watchlist (кроме исключений) перед первым сканом
    fib_data_task: asyncio.Task | None = None
    if config.TRADER_FIB_ENABLED:
        from app.fib_notifier import fib_data_sync_task

        fib_data_task = asyncio.create_task(fib_data_sync_task())

    # Запустить фоновый сканер MTF-сигналов (после закрытия 4h-баров)
    mtf_task: asyncio.Task | None = None
    mtf_data_task: asyncio.Task | None = None
    if config.TRADER_MTF_ENABLED:
        from app.mtf_notifier import mtf_scan_loop, mtf_data_sync_task

        logger.info(
            "Starting MTF Confirmation notifier (scans at %s UTC)",
            ",".join(f"{h:02d}:{m:02d}" for h, m in config.TRADER_MTF_SCANS),
        )
        mtf_task = asyncio.create_task(mtf_scan_loop())
        mtf_data_task = asyncio.create_task(mtf_data_sync_task())
    else:
        logger.info("MTF Confirmation notifier disabled via TRADER_MTF_ENABLED")

    report_startup_state(live_trader)

    # Watchdog: если таск сканера неожиданно умер (исключение вне цикла),
    # поднимаем Telegram-алерт, чтобы падение не осталось незамеченным.
    watched = {
        "ROE": signal_task,
        "Elliott": elliott_task,
        "Fib": fib_task,
        "Fib-data": fib_data_task,
        "MTF": mtf_task,
        "MTF-data": mtf_data_task,
    }
    watchdog_task = asyncio.create_task(_watchdog(watched))

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        watchdog_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watchdog_task
        if signal_task is not None:
            signal_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await signal_task
        if elliott_task is not None:
            elliott_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await elliott_task
        if fib_task is not None:
            fib_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await fib_task
        if fib_data_task is not None:
            fib_data_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await fib_data_task
        if mtf_task is not None:
            mtf_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await mtf_task
        if mtf_data_task is not None:
            mtf_data_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await mtf_data_task
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено")
