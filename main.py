import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from bot import config
from bot.database import (
    init_db, get_due_deletions, remove_deletion,
    cleanup_old_news_sent, cleanup_old_news,
    get_users_expiring_soon, get_active_users_with_assets,
    get_pinned_news, save_pinned_news,
    cleanup_old_delivery_logs,
)
from bot.middlewares import LanguageMiddleware
from bot.handlers import start, language, finance, admin
from bot.retry_utils import async_retry
from bot.rate_limiter import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def cleanup_job(bot: Bot):
    """Single execution: delete expired messages and old DB entries."""
    try:
        due = await get_due_deletions()
        for entry in due:
            try:
                await bot.delete_message(entry["chat_id"], entry["message_id"])
            except Exception:
                pass
            await remove_deletion(entry["id"])

        removed = await cleanup_old_news_sent(max_age_hours=24)
        if removed:
            logger.info(f"Cleaned {removed} old finance_news_sent entries")

        removed_news = await cleanup_old_news(max_age_hours=24)
        if removed_news:
            logger.info(f"Cleaned {removed_news} old news entries")

        removed_logs = await cleanup_old_delivery_logs(max_age_days=30)
        if removed_logs:
            logger.info(f"Cleaned {removed_logs} old delivery log entries")
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


_expiry_sent_today: set[int] = set()


async def expiry_reminder_job(bot: Bot):
    """Single execution: notify users whose subscription expires soon."""
    import datetime
    from bot.i18n import t
    from bot.database import get_language

    try:
        expiring = await get_users_expiring_soon(days=2)
        for user in expiring:
            uid = user["user_id"]
            if uid in _expiry_sent_today:
                continue
            lang = await get_language(uid)
            try:
                await bot.send_message(uid, t(lang, "expiry_reminder"), parse_mode="HTML")
                _expiry_sent_today.add(uid)
                logger.info(f"Sent expiry reminder to {uid}")
            except Exception:
                pass
        now = datetime.datetime.now()
        if now.hour == 9 and now.minute < 2:
            _expiry_sent_today.clear()
    except Exception as e:
        logger.warning(f"Expiry reminder error: {e}")


_cached_news = None
_rate_limiter = RateLimiter(max_per_minute=10)


async def auto_scan_job(bot: Bot):
    """Single execution: auto-scan news and send/edit to active subscribers."""
    global _cached_news
    import time
    from bot.finance import fetch_finance_news
    from bot.news_processor import (
        stage1_filter, compute_sentiment, stage2_hybrid,
        format_news_batch, compute_hash,
    )
    from bot.database import (
        get_all_tracked_assets, is_news_seen, save_news,
        get_active_users_with_assets, get_pinned_news, save_pinned_news,
        save_scan_metrics, log_news_delivery,
    )
    start_time = time.monotonic()
    metrics = {
        "users_count": 0, "news_fetched": 0, "news_matched": 0,
        "news_skipped_seen": 0, "news_skipped_irrelevant": 0, "messages_sent": 0,
    }

    try:
        users = await get_active_users_with_assets()
        if not users:
            logger.info("Auto-scan: no active users with assets, skipping")
            return

        metrics["users_count"] = len(users)
        logger.info(f"Auto-scan: found {len(users)} active users")
        tracked_assets = await get_all_tracked_assets()
        if not tracked_assets:
            logger.info("Auto-scan: no tracked assets configured, skipping")
            return

        logger.info(f"Auto-scan: {len(tracked_assets)} tracked assets: {[a['ticker'] for a in tracked_assets]}")
        try:
            news = await fetch_finance_news()
            _cached_news = news
        except Exception as e:
            logger.warning(f"Auto-scan: fetch failed ({e}), using cache")
            news = _cached_news

        if not news:
            logger.info("Auto-scan: no news fetched")
            return

        metrics["news_fetched"] = len(news)
        logger.info(f"Auto-scan: fetched {len(news)} news items")
        for user in users:
            uid = user["user_id"]
            lang = user.get("language", "ru")
            batch_items = []
            skipped_seen = 0
            skipped_irrelevant = 0

            for item in news[:20]:
                title = item["title"]
                content_hash = compute_hash(title)

                if await is_news_seen(content_hash):
                    skipped_seen += 1
                    continue

                is_relevant, matched_ticker, matched_asset = stage1_filter(
                    title, item["summary"], tracked_assets
                )
                if not is_relevant:
                    skipped_irrelevant += 1
                    continue

                impact, confidence = compute_sentiment(title, item["summary"], matched_asset)

                if confidence == "low" or impact == "NEUTRAL":
                    ai_impact = await stage2_hybrid(title, item["summary"], matched_asset, confidence)
                    if ai_impact:
                        impact = ai_impact

                summary = item["summary"][:200] if item["summary"] else title[:200]

                await save_news(
                    content_hash, item["source"], title, item.get("link", ""),
                    matched_ticker, summary, impact,
                )

                logger.info(f"Auto-scan: MATCH [{item['source']}] {title[:50]} -> {matched_ticker} ({impact})")
                await log_news_delivery(uid, matched_ticker, title, item["source"], impact)
                batch_items.append({
                    "title": title,
                    "source": item["source"],
                    "ticker": matched_ticker,
                    "summary": summary,
                    "impact": impact,
                    "link": item.get("link", ""),
                })

            metrics["news_matched"] += len(batch_items)
            metrics["news_skipped_seen"] += skipped_seen
            metrics["news_skipped_irrelevant"] += skipped_irrelevant
            logger.info(f"Auto-scan: user {uid} - {len(batch_items)} matched, {skipped_seen} seen, {skipped_irrelevant} irrelevant")

            if not batch_items:
                continue

            if not await _rate_limiter.can_send(uid):
                wait = await _rate_limiter.get_wait_time(uid)
                logger.info(f"Auto-scan: rate limited for {uid}, wait {wait:.0f}s")
                continue

            messages = format_news_batch(batch_items, lang)

            pinned = await get_pinned_news(uid)
            edited = False
            if pinned and messages:
                try:
                    await bot.edit_message_text(
                        messages[0],
                        chat_id=pinned["chat_id"],
                        message_id=pinned["message_id"],
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                    await save_pinned_news(uid, pinned["chat_id"], pinned["message_id"])
                    await _rate_limiter.record_send(uid)
                    metrics["messages_sent"] += 1
                    logger.info(f"Auto-scan: edited pinned message for {uid} ({len(batch_items)} news)")
                    edited = True
                except Exception as e:
                    logger.warning(f"Auto-scan: edit failed for {uid}: {e}")

            if not edited:
                sent_ok = False
                for msg_text in messages:
                    try:
                        msg = await bot.send_message(uid, msg_text, parse_mode="HTML", disable_web_page_preview=True)
                        await save_pinned_news(uid, uid, msg.message_id)
                        await _rate_limiter.record_send(uid)
                        sent_ok = True
                    except Exception as e:
                        logger.warning(f"Auto-scan: failed to send to {uid}: {e}")
                        break
                if sent_ok:
                    metrics["messages_sent"] += len(messages)
                if messages:
                    logger.info(f"Auto-scan: sent {len(messages)} message(s) to {uid} ({len(batch_items)} news)")

    except Exception as e:
        logger.warning(f"Auto-scan error: {e}")
    finally:
        processing_ms = int((time.monotonic() - start_time) * 1000)
        try:
            await save_scan_metrics(
                metrics["users_count"], metrics["news_fetched"], metrics["news_matched"],
                metrics["news_skipped_seen"], metrics["news_skipped_irrelevant"],
                metrics["messages_sent"], processing_ms,
            )
            logger.info(
                f"Auto-scan metrics: users={metrics['users_count']}, "
                f"fetched={metrics['news_fetched']}, matched={metrics['news_matched']}, "
                f"sent={metrics['messages_sent']}, time={processing_ms}ms"
            )
        except Exception as e:
            logger.warning(f"Failed to save scan metrics: {e}")


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Check your .env file.")
        sys.exit(1)

    logger.info("Initializing database...")
    await init_db()

    logger.info("Starting bot...")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    if config.HTTP_PROXY:
        logger.info(f"Using HTTP proxy for Telegram API: {config.HTTP_PROXY}")
        bot.session = AiohttpSession(proxy=config.HTTP_PROXY)
    elif config.TELEGRAM_API_SERVER:
        logger.info(f"Using Telegram API mirror: {config.TELEGRAM_API_SERVER}")
        from aiogram.client.telegram import TelegramAPIServer
        bot.session.api = TelegramAPIServer.from_base(config.TELEGRAM_API_SERVER)
    dp = Dispatcher()

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_routers(
        start.router,
        language.router,
        admin.router,
        finance.router,
    )

    logger.info("Bot is now polling. Press Ctrl+C to stop.")

    from bot.scheduler import setup_scheduler
    scheduler = setup_scheduler(
        bot,
        cleanup_func=cleanup_job,
        expiry_func=expiry_reminder_job,
        auto_scan_func=auto_scan_job,
        auto_scan_interval=config.AUTO_SCAN_INTERVAL,
    )
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
