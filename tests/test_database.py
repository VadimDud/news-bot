import datetime
import json
import pytest

from bot.database import (
    set_user, get_user, set_language, get_language,
    has_access, grant_trial, grant_access, get_access_info,
    get_users_expiring_soon,
    add_finance_subscription, remove_finance_subscription,
    get_finance_subscriptions, get_all_finance_users,
    get_active_users_with_assets, get_user_tickers,
    is_news_sent, mark_news_sent,
    create_channel, get_user_channels, get_channel, get_channel_by_name,
    update_channel_keywords, update_channel_name, update_channel_ticker,
    update_channel_source_tags, delete_channel, delete_user_channels,
    get_all_user_channels,
    save_channel_news, is_channel_news_seen, get_channel_news_log,
    cleanup_old_channel_news,
    save_pinned_news, get_pinned_news, get_pinned_news_by_channel,
    remove_pinned_news, remove_pinned_news_by_channel,
    save_scan_metrics, get_recent_metrics,
    log_news_delivery, get_user_delivery_log, cleanup_old_delivery_logs,
    save_tracked_asset, get_tracked_asset, get_all_tracked_assets,
    remove_tracked_asset, has_tracked_asset,
    schedule_deletion, get_due_deletions, remove_deletion,
    cleanup_old_news_sent, cleanup_old_news,
    is_news_seen as is_news_seen_2, save_news,
    get_total_users, get_new_users_today, get_new_users_this_week,
    get_language_stats, get_finance_subscribers_count,
    get_finance_tickers_count, get_user_channels_count,
    get_channels_count, get_news_sent_count, get_full_stats,
    get_all_users,
)

from bot import config


# ── Users ──


class TestUsers:
    async def test_set_and_get_user(self):
        await set_user(123, "testuser", "Test User", "ru")
        user = await get_user(123)
        assert user is not None
        assert user["user_id"] == 123
        assert user["username"] == "testuser"
        assert user["full_name"] == "Test User"
        assert user["language"] == "ru"

    async def test_get_nonexistent_user(self):
        assert await get_user(99999) is None

    async def test_set_user_upsert(self):
        await set_user(123, "user1", "User One", "ru")
        await set_user(123, "user1_updated", "User Updated", "ru")
        user = await get_user(123)
        assert user["username"] == "user1_updated"
        assert user["full_name"] == "User Updated"

    async def test_set_language(self):
        await set_user(123, "user1", "User One", "ru")
        await set_language(123, "en")
        assert await get_language(123) == "en"

    async def test_get_language_default(self):
        assert await get_language(99999) == "ru"

    async def test_username_none(self):
        await set_user(456, None, "No Username", "en")
        user = await get_user(456)
        assert user["username"] is None


# ── Access ──


class TestAccess:
    async def test_has_access_no_user(self):
        assert await has_access(99999) is False

    async def test_has_access_no_expiry(self):
        await set_user(10, "u", "U", "ru")
        assert await has_access(10) is False

    async def test_grant_trial(self):
        await set_user(10, "u", "U", "ru")
        result = await grant_trial(10, days=30)
        assert result is True
        assert await has_access(10) is True

    async def test_grant_trial_already_active(self):
        await set_user(10, "u", "U", "ru")
        await grant_trial(10, days=30)
        result = await grant_trial(10, days=30)
        assert result is False

    async def test_grant_access(self):
        await set_user(10, "u", "U", "ru")
        until = await grant_access(10, days=10)
        assert isinstance(until, datetime.datetime)
        assert await has_access(10) is True

    async def test_get_access_info_no_user(self):
        info = await get_access_info(99999)
        assert info["has_access"] is False
        assert info["days_left"] == 0

    async def test_get_access_info_with_trial(self):
        await set_user(10, "u", "U", "ru")
        await grant_trial(10, days=30)
        info = await get_access_info(10)
        assert info["has_access"] is True
        assert info["days_left"] >= 29

    async def test_get_users_expiring_soon_empty(self):
        result = await get_users_expiring_soon(days=2)
        assert result == []

    async def test_get_users_expiring_soon(self):
        await set_user(10, "u", "U", "ru")
        await grant_access(10, days=1)
        result = await get_users_expiring_soon(days=3)
        assert len(result) == 1
        assert result[0]["user_id"] == 10


# ── Finance subscriptions ──


class TestFinanceSubscriptions:
    async def test_add_subscription(self):
        await set_user(100, "u1", "User 1", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        subs = await get_finance_subscriptions(100)
        assert len(subs) == 1
        assert subs[0]["ticker"] == "SBER"

    async def test_add_subscription_uppercase(self):
        await set_user(100, "u1", "User 1", "ru")
        await add_finance_subscription(100, "sber", "sber")
        subs = await get_finance_subscriptions(100)
        assert subs[0]["ticker"] == "SBER"

    async def test_add_duplicate(self):
        await set_user(100, "u1", "User 1", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        await add_finance_subscription(100, "SBER", "SBER")
        subs = await get_finance_subscriptions(100)
        assert len(subs) == 1

    async def test_remove_subscription(self):
        await set_user(100, "u1", "User 1", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        await add_finance_subscription(100, "GAZP", "GAZP")
        await remove_finance_subscription(100, "SBER")
        subs = await get_finance_subscriptions(100)
        assert len(subs) == 1
        assert subs[0]["ticker"] == "GAZP"

    async def test_remove_nonexistent(self):
        await set_user(100, "u1", "User 1", "ru")
        await remove_finance_subscription(100, "NOPE")
        subs = await get_finance_subscriptions(100)
        assert len(subs) == 0

    async def test_get_user_tickers(self):
        await set_user(100, "u1", "User 1", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        await add_finance_subscription(100, "GAZP", "GAZP")
        tickers = await get_user_tickers(100)
        assert set(tickers) == {"SBER", "GAZP"}

    async def test_get_all_finance_users(self):
        await set_user(100, "u1", "User 1", "ru")
        await set_user(200, "u2", "User 2", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        await add_finance_subscription(200, "GAZP", "GAZP")
        users = await get_all_finance_users()
        ids = [u["user_id"] for u in users]
        assert 100 in ids
        assert 200 in ids

    async def test_get_active_users_with_assets(self):
        await set_user(100, "u1", "User 1", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "Ch1", ["keyword1"])
        result = await get_active_users_with_assets()
        ids = [u["user_id"] for u in result]
        assert 100 in ids

    async def test_get_active_users_no_channels(self):
        await set_user(100, "u1", "User 1", "ru")
        await grant_trial(100, days=30)
        result = await get_active_users_with_assets()
        assert len(result) == 0

    async def test_full_flow_add_remove(self):
        uid = 500
        await set_user(uid, "flow_user", "Flow User", "ru")
        await add_finance_subscription(uid, "SBER", "SBER")
        await add_finance_subscription(uid, "GAZP", "GAZP")
        await add_finance_subscription(uid, "YDEX", "YDEX")
        subs = await get_finance_subscriptions(uid)
        assert len(subs) == 3

        await remove_finance_subscription(uid, "GAZP")
        subs = await get_finance_subscriptions(uid)
        assert len(subs) == 2
        tickers = [s["ticker"] for s in subs]
        assert "GAZP" not in tickers

        await remove_finance_subscription(uid, "SBER")
        await remove_finance_subscription(uid, "YDEX")
        assert len(await get_finance_subscriptions(uid)) == 0

    async def test_multiple_users_independent(self):
        await set_user(1001, "u1", "User 1", "ru")
        await set_user(1002, "u2", "User 2", "en")
        await add_finance_subscription(1001, "SBER", "SBER")
        await add_finance_subscription(1002, "GAZP", "GAZP")
        assert len(await get_finance_subscriptions(1001)) == 1
        assert len(await get_finance_subscriptions(1002)) == 1
        await remove_finance_subscription(1001, "SBER")
        assert len(await get_finance_subscriptions(1002)) == 1


# ── News dedup ──


class TestNewsDedup:
    async def test_mark_and_check(self):
        assert await is_news_sent("Test Title") is False
        await mark_news_sent("Test Title", "РБК")
        assert await is_news_sent("Test Title") is True


# ── User Channels ──


class TestUserChannels:
    async def test_create_channel(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Финансы", ["финансы", "деньги"])
        assert ch_id is not None
        assert ch_id > 0

    async def test_create_channel_with_ticker_and_tags(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Газпром", ["газпром", "gazp"], "GAZP", ["finance", "macro"])
        ch = await get_channel(ch_id)
        assert ch["ticker"] == "GAZP"
        assert ch["source_tags"] == ["finance", "macro"]

    async def test_create_duplicate_returns_none(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Финансы", ["финансы"])
        assert ch_id is not None
        ch_id2 = await create_channel(100, "Финансы", ["другое"])
        assert ch_id2 is None

    async def test_get_user_channels(self):
        await set_user(100, "u1", "U", "ru")
        await create_channel(100, "Ch1", ["k1"])
        await create_channel(100, "Ch2", ["k2"])
        channels = await get_user_channels(100)
        assert len(channels) == 2

    async def test_get_channel(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["k1", "k2"])
        ch = await get_channel(ch_id)
        assert ch["name"] == "Ch1"
        assert ch["keywords"] == ["k1", "k2"]
        assert ch["source_tags"] == []

    async def test_get_channel_nonexistent(self):
        assert await get_channel(99999) is None

    async def test_get_channel_by_name(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "My Channel", ["kw"])
        ch = await get_channel_by_name(100, "My Channel")
        assert ch["id"] == ch_id

    async def test_get_channel_by_name_nonexistent(self):
        assert await get_channel_by_name(100, "Nope") is None

    async def test_update_keywords(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["old"])
        await update_channel_keywords(ch_id, ["new1", "new2"])
        ch = await get_channel(ch_id)
        assert ch["keywords"] == ["new1", "new2"]

    async def test_update_name(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Old", ["kw"])
        await update_channel_name(ch_id, "New")
        ch = await get_channel(ch_id)
        assert ch["name"] == "New"

    async def test_update_ticker(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await update_channel_ticker(ch_id, "SBER")
        ch = await get_channel(ch_id)
        assert ch["ticker"] == "SBER"

    async def test_clear_ticker(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"], "SBER")
        await update_channel_ticker(ch_id, None)
        ch = await get_channel(ch_id)
        assert ch["ticker"] is None

    async def test_update_source_tags(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await update_channel_source_tags(ch_id, ["finance", "crypto"])
        ch = await get_channel(ch_id)
        assert ch["source_tags"] == ["finance", "crypto"]

    async def test_delete_channel(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await delete_channel(ch_id)
        assert await get_channel(ch_id) is None

    async def test_delete_user_channels(self):
        await set_user(100, "u1", "U", "ru")
        await create_channel(100, "Ch1", ["k1"])
        await create_channel(100, "Ch2", ["k2"])
        await delete_user_channels(100)
        assert len(await get_user_channels(100)) == 0

    async def test_get_all_user_channels(self):
        await set_user(100, "u1", "U", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "Ch1", ["kw"])
        all_ch = await get_all_user_channels()
        assert any(ch["user_id"] == 100 for ch in all_ch)

    async def test_get_all_user_channels_no_access(self):
        await set_user(100, "u1", "U", "ru")
        await create_channel(100, "Ch1", ["kw"])
        all_ch = await get_all_user_channels()
        assert len(all_ch) == 0


# ── Channel news ──


class TestChannelNews:
    async def test_save_and_check_channel_news(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_channel_news(ch_id, "hash1", "keyword1", "SBER", "POSITIVE")
        assert await is_channel_news_seen(ch_id, "hash1") is True
        assert await is_channel_news_seen(ch_id, "hash2") is False

    async def test_get_channel_news_log(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_channel_news(ch_id, "h1", "k1", "T1", "POSITIVE")
        await save_channel_news(ch_id, "h2", "k2", "T2", "NEGATIVE")
        log = await get_channel_news_log(ch_id)
        assert len(log) == 2

    async def test_cleanup_old_channel_news(self):
        import aiosqlite
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_channel_news(ch_id, "old_hash", "k", "T", "NEUTRAL")
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE channel_news SET sent_at = datetime('now', '-25 hours') WHERE news_content_hash = 'old_hash'"
            )
            await db.commit()
        removed = await cleanup_old_channel_news(max_age_hours=24)
        assert removed == 1

    async def test_cleanup_keeps_recent(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_channel_news(ch_id, "fresh", "k", "T", "POSITIVE")
        removed = await cleanup_old_channel_news(max_age_hours=24)
        assert removed == 0
        assert await is_channel_news_seen(ch_id, "fresh") is True


# ── Pinned news ──


class TestPinnedNews:
    async def test_save_and_get_pinned(self):
        await set_user(100, "u1", "U", "ru")
        await save_pinned_news(100, chat_id=200, message_id=300)
        pinned = await get_pinned_news(100)
        assert pinned is not None
        assert pinned["chat_id"] == 200
        assert pinned["message_id"] == 300

    async def test_save_pinned_with_channel_id(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_pinned_news(100, chat_id=200, message_id=300, channel_id=ch_id)
        pinned = await get_pinned_news_by_channel(ch_id)
        assert pinned is not None
        assert pinned["message_id"] == 300

    async def test_update_pinned_with_channel_id(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_pinned_news(100, chat_id=200, message_id=300, channel_id=ch_id)
        await save_pinned_news(100, chat_id=200, message_id=400, channel_id=ch_id)
        pinned = await get_pinned_news_by_channel(ch_id)
        assert pinned["message_id"] == 400

    async def test_remove_pinned(self):
        await set_user(100, "u1", "U", "ru")
        await save_pinned_news(100, chat_id=200, message_id=300)
        await remove_pinned_news(100)
        assert await get_pinned_news(100) is None

    async def test_remove_pinned_by_channel(self):
        await set_user(100, "u1", "U", "ru")
        ch_id = await create_channel(100, "Ch1", ["kw"])
        await save_pinned_news(100, chat_id=200, message_id=300, channel_id=ch_id)
        await remove_pinned_news_by_channel(ch_id)
        assert await get_pinned_news_by_channel(ch_id) is None

    async def test_get_pinned_nonexistent(self):
        assert await get_pinned_news(99999) is None
        assert await get_pinned_news_by_channel(99999) is None


# ── Scan metrics ──


class TestScanMetrics:
    async def test_save_and_get_metrics(self):
        await save_scan_metrics(10, 100, 50, 30, 50, 40, 1500)
        metrics = await get_recent_metrics(limit=5)
        assert len(metrics) == 1
        assert metrics[0]["users_count"] == 10
        assert metrics[0]["news_fetched"] == 100
        assert metrics[0]["messages_sent"] == 40

    async def test_multiple_metrics_ordered(self):
        await save_scan_metrics(1, 10, 5, 3, 5, 4, 100)
        await save_scan_metrics(2, 20, 10, 6, 10, 8, 200)
        metrics = await get_recent_metrics(limit=2)
        assert len(metrics) == 2
        counts = [m["users_count"] for m in metrics]
        assert 1 in counts
        assert 2 in counts

    async def test_empty_metrics(self):
        metrics = await get_recent_metrics()
        assert metrics == []


# ── Delivery log ──


class TestDeliveryLog:
    async def test_log_and_get(self):
        await set_user(100, "u1", "U", "ru")
        await log_news_delivery(100, "SBER", "Title", "РБК", "POSITIVE")
        log = await get_user_delivery_log(100)
        assert len(log) == 1
        assert log[0]["ticker"] == "SBER"
        assert log[0]["impact"] == "POSITIVE"

    async def test_cleanup_old_delivery_logs(self):
        import aiosqlite
        await set_user(100, "u1", "U", "ru")
        await log_news_delivery(100, "SBER", "Title", "РБК", "POSITIVE")
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE news_delivery_log SET sent_at = datetime('now', '-31 days') WHERE user_id = 100"
            )
            await db.commit()
        removed = await cleanup_old_delivery_logs(max_age_days=30)
        assert removed == 1
        assert len(await get_user_delivery_log(100)) == 0


# ── Tracked assets ──


class TestTrackedAssets:
    async def test_save_and_get(self):
        await save_tracked_asset("SBER", "Сбербанк", ["сбер", "bank"], ["рост"], ["падение"])
        asset = await get_tracked_asset("SBER")
        assert asset is not None
        assert asset["name"] == "Сбербанк"
        assert asset["keywords"] == ["сбер", "bank"]
        assert asset["positive_triggers"] == ["рост"]
        assert asset["negative_triggers"] == ["падение"]

    async def test_get_nonexistent(self):
        assert await get_tracked_asset("NOPE") is None

    async def test_has_tracked_asset(self):
        assert await has_tracked_asset("SBER") is False
        await save_tracked_asset("SBER", "Сбербанк", ["сбер"], ["рост"], ["падение"])
        assert await has_tracked_asset("SBER") is True

    async def test_upsert(self):
        await save_tracked_asset("SBER", "v1", ["k1"], ["p1"], ["n1"])
        await save_tracked_asset("SBER", "v2", ["k2"], ["p2"], ["n2"])
        asset = await get_tracked_asset("SBER")
        assert asset["name"] == "v2"
        assert asset["keywords"] == ["k2"]

    async def test_get_all(self):
        await save_tracked_asset("SBER", "SBER", ["k"], ["p"], ["n"])
        await save_tracked_asset("GAZP", "GAZP", ["k"], ["p"], ["n"])
        all_assets = await get_all_tracked_assets()
        assert len(all_assets) == 2

    async def test_remove(self):
        await save_tracked_asset("SBER", "SBER", ["k"], ["p"], ["n"])
        await remove_tracked_asset("SBER")
        assert await get_tracked_asset("SBER") is None


# ── Pending deletions ──


class TestPendingDeletions:
    async def test_schedule_and_get_immediate(self):
        await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
        due = await get_due_deletions()
        assert len(due) == 1
        assert due[0]["chat_id"] == 100

    async def test_schedule_future(self):
        await schedule_deletion(chat_id=100, message_id=1, delay_seconds=7200)
        due = await get_due_deletions()
        assert len(due) == 0

    async def test_remove_deletion(self):
        await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
        due = await get_due_deletions()
        await remove_deletion(due[0]["id"])
        assert len(await get_due_deletions()) == 0

    async def test_multiple(self):
        await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
        await schedule_deletion(chat_id=100, message_id=2, delay_seconds=-1)
        await schedule_deletion(chat_id=200, message_id=3, delay_seconds=-1)
        assert len(await get_due_deletions()) == 3


# ── Cleanup ──


class TestCleanup:
    async def test_cleanup_old_news_sent(self):
        import aiosqlite
        await mark_news_sent("Old News", "РБК")
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE finance_news_sent SET sent_at = datetime('now', '-25 hours') WHERE title = 'Old News'"
            )
            await db.commit()
        removed = await cleanup_old_news_sent(max_age_hours=24)
        assert removed == 1
        assert await is_news_sent("Old News") is False

    async def test_cleanup_keeps_recent_news_sent(self):
        await mark_news_sent("Fresh", "РБК")
        removed = await cleanup_old_news_sent(max_age_hours=24)
        assert removed == 0
        assert await is_news_sent("Fresh") is True

    async def test_cleanup_old_news(self):
        import aiosqlite
        await save_news("old1", 100, "РБК", "Old", "", "SBER", "Old", "NEUTRAL")
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE news SET created_at = datetime('now', '-25 hours') WHERE content_hash = 'old1'"
            )
            await db.commit()
        removed = await cleanup_old_news(max_age_hours=24)
        assert removed == 1

    async def test_cleanup_keeps_recent_news(self):
        await save_news("fresh", 100, "РБК", "Fresh", "", "SBER", "Fresh", "POSITIVE")
        removed = await cleanup_old_news(max_age_hours=24)
        assert removed == 0


# ── News table ──


class TestNewsTable:
    async def test_save_and_check_news(self):
        h = "abc123def456"
        assert await is_news_seen_2(h, 100) is False
        await save_news(h, 100, "РБК", "Test title", "https://example.com", "SBER", "Summary", "POSITIVE")
        assert await is_news_seen_2(h, 100) is True

    async def test_news_dedup(self):
        await save_news("hash1", 100, "РБК", "News 1", "", "SBER", "Sum", "NEUTRAL")
        assert await is_news_seen_2("hash1", 100) is True
        assert await is_news_seen_2("hash1", 200) is False

    async def test_cleanup_old_news(self):
        import aiosqlite
        await save_news("old1", 100, "РБК", "Old", "", "SBER", "Old", "NEUTRAL")
        async with aiosqlite.connect(config.DATABASE_PATH) as db:
            await db.execute(
                "UPDATE news SET created_at = datetime('now', '-25 hours') WHERE content_hash = 'old1'"
            )
            await db.commit()
        removed = await cleanup_old_news(max_age_hours=24)
        assert removed == 1
        assert await is_news_seen_2("old1", 100) is False


# ── Statistics ──


class TestStatistics:
    async def test_total_users_empty(self):
        assert await get_total_users() == 0

    async def test_total_users(self):
        await set_user(1, "u1", "U1", "ru")
        await set_user(2, "u2", "U2", "en")
        assert await get_total_users() == 2

    async def test_new_users_today(self):
        await set_user(1, "u1", "U1", "ru")
        assert await get_new_users_today() >= 1

    async def test_new_users_this_week(self):
        await set_user(1, "u1", "U1", "ru")
        assert await get_new_users_this_week() >= 1

    async def test_language_stats(self):
        await set_user(1, "u1", "U1", "ru")
        await set_user(2, "u2", "U2", "en")
        await set_user(3, "u3", "U3", "ru")
        stats = await get_language_stats()
        assert stats["ru"] == 2
        assert stats["en"] == 1

    async def test_finance_subs_count(self):
        await set_user(1, "u1", "U1", "ru")
        await set_user(2, "u2", "U2", "ru")
        await add_finance_subscription(1, "SBER", "SBER")
        await add_finance_subscription(1, "GAZP", "GAZP")
        await add_finance_subscription(2, "YDEX", "YDEX")
        assert await get_finance_subscribers_count() == 2

    async def test_finance_tickers_count(self):
        await set_user(1, "u1", "U1", "ru")
        await add_finance_subscription(1, "SBER", "SBER")
        await add_finance_subscription(1, "GAZP", "GAZP")
        assert await get_finance_tickers_count() == 2

    async def test_user_channels_count(self):
        await set_user(1, "u1", "U1", "ru")
        await create_channel(1, "Ch1", ["k"])
        assert await get_user_channels_count() == 1

    async def test_channels_count(self):
        await set_user(1, "u1", "U1", "ru")
        await create_channel(1, "Ch1", ["k1"])
        await create_channel(1, "Ch2", ["k2"])
        assert await get_channels_count() == 2

    async def test_news_sent_count(self):
        await mark_news_sent("N1", "S")
        await mark_news_sent("N2", "S")
        assert await get_news_sent_count() == 2

    async def test_full_stats(self):
        await set_user(1, "u1", "U1", "ru")
        await set_user(2, "u2", "U2", "en")
        await add_finance_subscription(1, "SBER", "SBER")
        await create_channel(1, "Ch1", ["k"])
        await mark_news_sent("N1", "S")
        stats = await get_full_stats()
        assert stats["total"] == 2
        assert stats["lang_ru"] == 1
        assert stats["lang_en"] == 1
        assert stats["finance_subs"] == 1
        assert stats["finance_tickers"] == 1
        assert stats["news_sent"] == 1
        assert stats["channels"] == 1

    async def test_get_all_users(self):
        await set_user(1, "u1", "U1", "ru")
        await set_user(2, "u2", "U2", "en")
        users = await get_all_users()
        assert len(users) == 2
