import asyncio
import datetime
import logging
import sys
import time
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.client.telegram import TelegramAPIServer

from bot import config
from bot.database import (
    init_db, close_db, get_due_deletions, remove_deletion,
    cleanup_old_news,
    get_users_expiring_soon, get_language,
    get_active_users_with_assets, get_all_user_channels,
    get_pinned_news, save_pinned_news,
    get_pinned_news_by_channel,
    is_news_seen, save_news,
    is_channel_news_seen, save_channel_news,
    cleanup_old_delivery_logs, cleanup_old_channel_news,
    save_scan_metrics, log_news_delivery,
    save_news_batch, save_channel_news_batch, log_news_delivery_batch,
    get_all_tracked_assets,
    upsert_news_buffer, upsert_user_news_priority,
    upsert_news_ticker_popularity, dynamic_cleanup_news_buffer,
    refresh_ticker_popularity,
)
from bot.finance import fetch_news
from bot.i18n import t
from bot.middlewares import LanguageMiddleware
from bot.handlers import start, language, finance, admin, channels
from bot.news_processor import (
    global_scan, format_channel_news, compute_hash,
)
from bot.retry_utils import async_retry
from bot.rate_limiter import RateLimiter
from bot.scheduler import setup_scheduler

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
            await asyncio.sleep(0.05)

        removed_news = await         dynamic_cleanup_news_buffer()
        if removed_news:
            logger.info(f"Cleaned {removed_news} old news entries")

        removed_logs = await cleanup_old_delivery_logs(max_age_days=30)
        if removed_logs:
            logger.info(f"Cleaned {removed_logs} old delivery log entries")

        removed_channel_news = await cleanup_old_channel_news(max_age_hours=24)
        if removed_channel_news:
            logger.info(f"Cleaned {removed_channel_news} old channel_news entries")
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


_expiry_sent_today: set[int] = set()


async def expiry_reminder_job(bot: Bot):
    """Single execution: notify users whose subscription expires soon."""
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
            await asyncio.sleep(0.3)
        now = datetime.datetime.now()
        if now.hour == 9 and now.minute < 2:
            _expiry_sent_today.clear()
    except Exception as e:
        logger.warning(f"Expiry reminder error: {e}")


_cached_news = None
_rate_limiter = RateLimiter(max_per_minute=10)


async def auto_scan_job(bot: Bot):
    """Single execution: auto-scan news and send/edit to active subscribers per channel."""
    global _cached_news
    start_time = time.monotonic()
    metrics = {
        "users_count": 0, "news_fetched": 0, "news_matched": 0,
        "news_skipped_seen": 0, "news_skipped_irrelevant": 0, "messages_sent": 0,
    }

    try:
        users = await get_active_users_with_assets()
        if not users:
            logger.info("Auto-scan: no active users with channels, skipping")
            return

        metrics["users_count"] = len(users)
        logger.info(f"Auto-scan: found {len(users)} active users")

        all_channels = await get_all_user_channels()
        if not all_channels:
            logger.info("Auto-scan: no user channels configured, skipping")
            return

        logger.info(f"Auto-scan: {len(all_channels)} channels from {len(users)} users")

        # Collect union of all source_tags from active channels
        all_tags = set()
        for ch in all_channels:
            for tag in ch.get("source_tags", []):
                all_tags.add(tag)

        try:
            news = await fetch_news(list(all_tags) if all_tags else None)
            _cached_news = news
        except Exception as e:
            logger.warning(f"Auto-scan: fetch failed ({e}), using cache")
            news = _cached_news

        if not news:
            logger.info("Auto-scan: no news fetched")
            return

        metrics["news_fetched"] = len(news)
        logger.info(f"Auto-scan: fetched {len(news)} news items")

        channel_results, buffer_updates = await global_scan(news, all_channels)

        # Write to news_buffer
        tickers_refreshed = set()
        for buf in buffer_updates:
            await upsert_news_buffer(
                content_hash=buf["content_hash"],
                source=buf["source"],
                title=buf["title"],
                url=buf["url"],
                summary=buf["summary"],
                importance_score=buf["importance_score"],
                match_count=buf["match_count"],
                is_used=buf["is_used"],
            )
            for ticker, sc in buf.get("subscriber_counts", {}).items():
                await upsert_news_ticker_popularity(
                    content_hash=buf["content_hash"],
                    ticker=ticker,
                    subscriber_count=sc,
                )
                if ticker not in tickers_refreshed:
                    await refresh_ticker_popularity(ticker)
                    tickers_refreshed.add(ticker)

        if not channel_results:
            logger.info("Auto-scan: no matches found for any channel")
            return

        total_matched = sum(len(v) for v in channel_results.values())
        metrics["news_matched"] = total_matched
        logger.info(f"Auto-scan: {total_matched} matches across {len(channel_results)} channels")

        for channel_id, matched_items in channel_results.items():
            # Find channel owner
            channel = next((ch for ch in all_channels if ch["id"] == channel_id), None)
            if not channel:
                continue
            uid = channel["user_id"]
            lang = channel.get("language", "ru")

            # Filter already-seen news for this channel
            new_items = []
            for item in matched_items:
                if await is_channel_news_seen(channel_id, item["content_hash"]):
                    metrics["news_skipped_seen"] += 1
                    continue
                new_items.append(item)

            if not new_items:
                continue

            # Save news to channel_news + user_news_priority BEFORE rate limit check
            # so we don't reprocess the same news endlessly
            cn_items = []
            n_items = []
            dl_items = []
            for item in new_items:
                cn_items.append({
                    "channel_id": channel_id,
                    "content_hash": item["content_hash"],
                    "matched_keyword": item.get("matched_keyword", ""),
                    "ticker_hint": item.get("ticker_hint", ""),
                    "impact": item["impact"],
                })
                n_items.append({
                    "content_hash": item["content_hash"],
                    "user_id": uid,
                    "source": item["source"],
                    "title": item["title"],
                    "link": item.get("link", ""),
                    "ticker_hint": item.get("ticker_hint", ""),
                    "summary": item["summary"],
                    "impact": item["impact"],
                })
                dl_items.append({
                    "user_id": uid,
                    "ticker_hint": item.get("ticker_hint", ""),
                    "title": item["title"],
                    "source": item["source"],
                    "impact": item["impact"],
                })
                await upsert_user_news_priority(
                    user_id=uid,
                    content_hash=item["content_hash"],
                    ticker=item.get("ticker_hint", ""),
                    importance_score=item.get("importance_score", 0.5),
                )
                await refresh_ticker_popularity(item.get("ticker_hint", "").upper())
            await save_channel_news_batch(cn_items)
            await save_news_batch(n_items)
            await log_news_delivery_batch(dl_items)

            if not await _rate_limiter.can_send(uid):
                wait = await _rate_limiter.get_wait_time(uid)
                logger.info(f"Auto-scan: rate limited for {uid}, wait {wait:.0f}s, saved {len(new_items)} items")
                continue

            messages = format_channel_news(channel["name"], new_items, lang)

            # Send/edit pinned message per channel
            pinned = await get_pinned_news_by_channel(channel_id)
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
                    await save_pinned_news(uid, pinned["chat_id"], pinned["message_id"], channel_id)
                    await _rate_limiter.record_send(uid)
                    metrics["messages_sent"] += 1
                    logger.info(f"Auto-scan: edited pinned msg for channel {channel['name']} ({len(new_items)} news)")
                    edited = True
                except Exception as e:
                    logger.warning(f"Auto-scan: edit failed for channel {channel['name']}: {e}")

            if not edited:
                sent_ok = False
                for i, msg_text in enumerate(messages):
                    try:
                        msg = await bot.send_message(uid, msg_text, parse_mode="HTML", disable_web_page_preview=True)
                        await save_pinned_news(uid, uid, msg.message_id, channel_id)
                        await _rate_limiter.record_send(uid)
                        sent_ok = True
                    except Exception as e:
                        logger.warning(f"Auto-scan: failed to send to {uid}: {e}")
                        break
                    if i < len(messages) - 1:
                        await asyncio.sleep(0.3)
                if sent_ok:
                    metrics["messages_sent"] += len(messages)
                if messages:
                    logger.info(f"Auto-scan: sent {len(messages)} msg(s) for channel {channel['name']} ({len(new_items)} news)")

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
        bot.session.api = TelegramAPIServer.from_base(config.TELEGRAM_API_SERVER)
    dp = Dispatcher()

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_routers(
        start.router,
        language.router,
        admin.router,
        finance.router,
        channels.router,
    )

    logger.info("Bot is now polling. Press Ctrl+C to stop.")

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
        await close_db()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
