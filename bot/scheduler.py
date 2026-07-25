import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def setup_scheduler(bot, cleanup_func, expiry_func, auto_scan_func, auto_scan_interval=1800):
    """Create and configure an AsyncIOScheduler with three periodic jobs.

    Each job calls the corresponding function once per interval.
    The functions must NOT have their own while-True loop.
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        cleanup_func,
        trigger=IntervalTrigger(seconds=60),
        args=[bot],
        id="cleanup",
        name="Cleanup expired messages",
    )

    scheduler.add_job(
        expiry_func,
        trigger=IntervalTrigger(seconds=3600),
        args=[bot],
        id="expiry_reminder",
        name="Expiry reminders",
    )

    scheduler.add_job(
        auto_scan_func,
        trigger=IntervalTrigger(seconds=auto_scan_interval),
        args=[bot],
        id="auto_scan",
        name="Auto-scan news",
    )

    logger.info(
        f"Scheduler configured: cleanup=60s, expiry=3600s, auto_scan={auto_scan_interval}s"
    )
    return scheduler
