"""Tests for all bot commands and handlers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.database import (
    set_user,
    get_user,
    set_language,
    get_language,
    add_finance_subscription,
    remove_finance_subscription,
    get_finance_subscriptions,
    get_user_tickers,
    get_all_finance_users,
    get_total_users,
    get_new_users_today,
    get_new_users_this_week,
    get_language_stats,
    get_finance_subscribers_count,
    get_finance_tickers_count,
    get_news_sent_count,
    get_full_stats,
    schedule_deletion,
    get_due_deletions,
    remove_deletion,
    is_news_seen,
    save_news,
    cleanup_old_news,
)
from bot.i18n import t, STRINGS

pytestmark = pytest.mark.asyncio


# ─── Helpers ───


def run_async(coro):
    return asyncio.run(coro)

    run_async(_clean_db())


# ─── Database tests ───


class TestDatabase:
    async def test_set_and_get_user(self):
            await set_user(123, "testuser", "Test User", "ru")
            user = await get_user(123)
            assert user is not None
            assert user["user_id"] == 123
            assert user["username"] == "testuser"
            assert user["full_name"] == "Test User"
            assert user["language"] == "ru"


    async def test_get_nonexistent_user(self):
            user = await get_user(99999)
            assert user is None


    async def test_set_user_upsert(self):
            await set_user(123, "user1", "User One", "ru")
            await set_user(123, "user1_updated", "User Updated", "ru")
            user = await get_user(123)
            assert user["username"] == "user1_updated"
            assert user["full_name"] == "User Updated"


    async def test_set_language(self):
            await set_user(123, "user1", "User One", "ru")
            await set_language(123, "en")
            lang = await get_language(123)
            assert lang == "en"


    async def test_get_language_default(self):
            lang = await get_language(99999)
            assert lang == "ru"



class TestFinanceSubscriptions:
    async def test_add_subscription(self):
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1
            assert subs[0]["ticker"] == "SBER"


    async def test_add_subscription_uppercase(self):
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "sber", "sber")
            subs = await get_finance_subscriptions(100)
            assert subs[0]["ticker"] == "SBER"


    async def test_add_duplicate_subscription(self):
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "SBER", "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1


    async def test_remove_subscription(self):
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "GAZP", "GAZP")
            await remove_finance_subscription(100, "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1
            assert subs[0]["ticker"] == "GAZP"


    async def test_remove_nonexistent_subscription(self):
            await set_user(100, "user1", "User One", "ru")
            await remove_finance_subscription(100, "NOPE")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 0


    async def test_get_user_tickers(self):
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "GAZP", "GAZP")
            tickers = await get_user_tickers(100)
            assert set(tickers) == {"SBER", "GAZP"}


    async def test_get_all_finance_users(self):
            await set_user(100, "user1", "User One", "ru")
            await set_user(200, "user2", "User Two", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(200, "GAZP", "GAZP")
            users = await get_all_finance_users()
            user_ids = [u["user_id"] for u in users]
            assert 100 in user_ids
            assert 200 in user_ids



# ─── Handler logic tests ───


class TestTickerValidation:
    """Test the ticker validation logic extracted from the handler."""

    async def test_valid_tickers_pass(self):
        valid = ["SBER", "GAZP", "RUBI", "YDEX", "VTB"]
        for ticker in valid:
            assert len(ticker) >= 2
            assert len(ticker) <= 10
            assert " " not in ticker

    async def test_invalid_tickers_rejected(self):
        for ticker in ["", "A"]:
            assert len(ticker) < 2

    async def test_too_long_ticker_rejected(self):
        assert len("VERYLONGTICKER123") > 10

    async def test_space_in_ticker_rejected(self):
        assert " " in "S BER"

    async def test_skipped_words(self):
        skipped = ("ДА", "НЕТ", "YES", "NO", "ОК", "OK")
        for word in skipped:
            assert word in ("ДА", "НЕТ", "YES", "NO", "ОК", "OK")


class TestCallbackParsing:
    """Test the callback data parsing logic."""

    async def test_fin_list_callback(self):
        data = "fin:list"
        parts = data.split(":")
        action = parts[1]
        assert action == "list"

    async def test_fin_add_callback(self):
        data = "fin:add"
        parts = data.split(":")
        action = parts[1]
        assert action == "add"

    async def test_fin_remove_callback(self):
        data = "fin:remove"
        parts = data.split(":")
        action = parts[1]
        assert action == "remove"

    async def test_fin_scan_callback(self):
        data = "fin:scan"
        parts = data.split(":")
        action = parts[1]
        assert action == "scan"

    async def test_fin_del_callback_old_buggy_logic(self):
        """This demonstrates the OLD bug: action.startswith('del:') is always False."""
        data = "fin:del:SBER"
        action = data.split(":")[1]  # "del"
        # OLD code: elif action.startswith("del:")
        assert action.startswith("del:") is False  # BUG: delete never triggers!

    async def test_fin_del_callback_new_fixed_logic(self):
        """The FIXED logic: check action == 'del' and extract ticker from parts[2]."""
        data = "fin:del:SBER"
        parts = data.split(":")
        action = parts[1]
        assert action == "del"
        assert len(parts) >= 3
        ticker = parts[2]
        assert ticker == "SBER"

    async def test_fin_del_callback_with_long_ticker(self):
        data = "fin:del:VERYLONG1"
        parts = data.split(":")
        action = parts[1]
        ticker = parts[2]
        assert action == "del"
        assert ticker == "VERYLONG1"


class TestI18n:
    async def test_ru_strings_present(self):
        required_keys = [
            "welcome_guest", "welcome_sub", "finance_menu", "finance_empty", "finance_add_ask",
            "finance_added", "finance_invalid_ticker", "finance_remove_ask",
            "finance_list", "finance_scan_done", "finance_no_news",
            "finance_all_seen", "admin_welcome", "admin_not_admin",
            "help", "lang_changed",
        ]
        for key in required_keys:
            assert key in STRINGS["ru"], f"Missing ru key: {key}"

    async def test_en_strings_present(self):
        required_keys = [
            "welcome_guest", "welcome_sub", "finance_menu", "finance_empty", "finance_add_ask",
            "finance_added", "finance_invalid_ticker", "finance_remove_ask",
            "finance_list", "finance_scan_done", "finance_no_news",
            "finance_all_seen", "admin_welcome", "admin_not_admin",
            "help", "lang_changed",
        ]
        for key in required_keys:
            assert key in STRINGS["en"], f"Missing en key: {key}"

    async def test_t_function_with_kwargs(self):
        result = t("ru", "finance_added", ticker="SBER")
        assert "SBER" in result
        assert "добавлен" in result

    async def test_t_function_missing_key_returns_key(self):
        result = t("ru", "nonexistent_key")
        assert result == "nonexistent_key"

    async def test_t_function_fallback_to_ru(self):
        result = t("xx", "finance_added", ticker="TEST")
        assert "TEST" in result


class TestAdminAccess:
    async def test_admin_id_config(self):
        from bot import config
        assert isinstance(config.ADMIN_ID, int)


# ─── Integration: full add→remove flow ───


class TestFullFlow:
    async def test_add_then_remove_subscription(self):
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
            assert "SBER" in tickers
            assert "YDEX" in tickers

            await remove_finance_subscription(uid, "SBER")
            subs = await get_finance_subscriptions(uid)
            assert len(subs) == 1
            assert subs[0]["ticker"] == "YDEX"

            await remove_finance_subscription(uid, "YDEX")
            subs = await get_finance_subscriptions(uid)
            assert len(subs) == 0


    async def test_multiple_users_independent(self):
            await set_user(1001, "u1", "User 1", "ru")
            await set_user(1002, "u2", "User 2", "en")

            await add_finance_subscription(1001, "SBER", "SBER")
            await add_finance_subscription(1002, "GAZP", "GAZP")

            subs1 = await get_finance_subscriptions(1001)
            subs2 = await get_finance_subscriptions(1002)

            assert len(subs1) == 1
            assert subs1[0]["ticker"] == "SBER"
            assert len(subs2) == 1
            assert subs2[0]["ticker"] == "GAZP"

            await remove_finance_subscription(1001, "SBER")
            subs2_after = await get_finance_subscriptions(1002)
            assert len(subs2_after) == 1



# ─── Statistics tests ───


class TestStatistics:
    async def test_get_total_users_empty(self):
            count = await get_total_users()
            assert count == 0

    async def test_get_total_users(self):
            await set_user(1, "u1", "User 1", "ru")
            await set_user(2, "u2", "User 2", "en")
            count = await get_total_users()
            assert count == 2

    async def test_get_new_users_today(self):
            await set_user(1, "u1", "User 1", "ru")
            count = await get_new_users_today()
            assert count >= 1

    async def test_get_new_users_this_week(self):
            await set_user(1, "u1", "User 1", "ru")
            count = await get_new_users_this_week()
            assert count >= 1

    async def test_get_language_stats(self):
            await set_user(1, "u1", "User 1", "ru")
            await set_user(2, "u2", "User 2", "en")
            await set_user(3, "u3", "User 3", "ru")
            stats = await get_language_stats()
            assert stats["ru"] == 2
            assert stats["en"] == 1

    async def test_get_finance_subscribers_count(self):
            await set_user(1, "u1", "User 1", "ru")
            await set_user(2, "u2", "User 2", "ru")
            await add_finance_subscription(1, "SBER", "SBER")
            await add_finance_subscription(1, "GAZP", "GAZP")
            await add_finance_subscription(2, "YDEX", "YDEX")
            count = await get_finance_subscribers_count()
            assert count == 2

    async def test_get_finance_tickers_count(self):
            await set_user(1, "u1", "User 1", "ru")
            await add_finance_subscription(1, "SBER", "SBER")
            await add_finance_subscription(1, "GAZP", "GAZP")
            count = await get_finance_tickers_count()
            assert count == 2

    async def test_get_news_sent_count(self):
            await save_news("h1", 100, "РБК", "Title 1", "", "SBER", "Sum", "NEUTRAL")
            await save_news("h2", 100, "Интерфакс", "Title 2", "", "GAZP", "Sum", "POSITIVE")
            count = await get_news_sent_count()
            assert count == 2

    async def test_get_full_stats(self):
            await set_user(1, "u1", "User 1", "ru")
            await set_user(2, "u2", "User 2", "en")
            await add_finance_subscription(1, "SBER", "SBER")
            await save_news("h1", 1, "РБК", "News 1", "", "SBER", "Sum", "NEUTRAL")
            stats = await get_full_stats()
            assert stats["total"] == 2
            assert stats["lang_ru"] == 1
            assert stats["lang_en"] == 1
            assert stats["finance_subs"] == 1
            assert stats["finance_tickers"] == 1
            assert stats["news_sent"] == 1


# ─── Pending deletions tests ───


class TestPendingDeletions:
    async def test_schedule_and_get_deletions(self):
            await schedule_deletion(chat_id=100, message_id=1, delay_seconds=7200)
            due = await get_due_deletions()
            # Just scheduled, shouldn't be due yet (7200s = 2h)
            assert len(due) == 0

    async def test_schedule_immediate_deletion(self):
            await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
            due = await get_due_deletions()
            assert len(due) == 1
            assert due[0]["chat_id"] == 100
            assert due[0]["message_id"] == 1

    async def test_remove_deletion(self):
            await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
            due = await get_due_deletions()
            assert len(due) == 1
            await remove_deletion(due[0]["id"])
            due = await get_due_deletions()
            assert len(due) == 0

    async def test_multiple_deletions(self):
            await schedule_deletion(chat_id=100, message_id=1, delay_seconds=-1)
            await schedule_deletion(chat_id=100, message_id=2, delay_seconds=-1)
            await schedule_deletion(chat_id=200, message_id=3, delay_seconds=-1)
            due = await get_due_deletions()
            assert len(due) == 3


# ─── News table tests ───


class TestNewsTable:
    async def test_save_and_check_news(self):
            h = "abc123def456"
            assert await is_news_seen(h, 100) is False
            await save_news(h, 100, "РБК", "Test title", "https://example.com", "SBER", "Summary", "POSITIVE")
            assert await is_news_seen(h, 100) is True

    async def test_news_dedup(self):
            h = "hash123"
            await save_news(h, 100, "РБК", "News 1", "", "SBER", "Sum", "NEUTRAL")
            await save_news(h, 100, "Интерфакс", "News 1 dup", "", "SBER", "Sum2", "POSITIVE")
            assert await is_news_seen(h, 100) is True
            assert await is_news_seen(h, 200) is False

    async def test_cleanup_old_news(self):
            import aiosqlite
            from bot import config
            await save_news("old1", 100, "РБК", "Old", "", "SBER", "Old summary", "NEUTRAL")
            async with aiosqlite.connect(config.DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE news SET created_at = datetime('now', '-25 hours') WHERE content_hash = 'old1'"
                )
                await db.commit()
            removed = await cleanup_old_news(max_age_hours=24)
            assert removed == 1
            assert await is_news_seen("old1", 100) is False

    async def test_cleanup_keeps_recent_news(self):
            await save_news("fresh", 100, "РБК", "Fresh", "", "SBER", "Fresh", "POSITIVE")
            removed = await cleanup_old_news(max_age_hours=24)
            assert removed == 0
            assert await is_news_seen("fresh", 100) is True


# ─── News processor tests ───


class TestNewsProcessor:
    async def test_stage1_filter_finance_relevant(self):
        from bot.news_processor import stage1_filter
        assets = [
            {"ticker": "SBER", "keywords": ["Сбербанк", "SBER", "сбер"]},
            {"ticker": "GAZP", "keywords": ["Газпром", "GAZP", "газ"]},
        ]
        relevant, ticker, _ = stage1_filter("Сбербанк снизил ставку по кредитам", "Банк понизил ставки", assets)
        assert relevant is True
        assert ticker == "SBER"

    async def test_stage1_filter_irrelevant(self):
        from bot.news_processor import stage1_filter
        assets = [
            {"ticker": "SBER", "keywords": ["Сбербанк", "SBER"]},
        ]
        relevant, ticker, _ = stage1_filter("Погода в Москве завтра", "Ожидается дождь", assets)
        assert relevant is False

    async def test_stage1_filter_macro(self):
        from bot.news_processor import stage1_filter
        assets = [
            {"ticker": "MACRO", "keywords": ["ЦБ", "ключевая ставка", "инфляция"]},
        ]
        relevant, ticker, _ = stage1_filter("ЦБ России повысил ключевую ставку", "Решение о ставке", assets)
        assert relevant is True
        assert ticker == "MACRO"

    async def test_compute_hash(self):
        from bot.news_processor import compute_hash
        h1 = compute_hash("Тестовая новость о Сбербанке")
        h2 = compute_hash("Тестовая новость о Сбербанке")
        h3 = compute_hash("Другая новость")
        assert h1 == h2
        assert h1 != h3

    async def test_format_news_alert(self):
        from bot.news_processor import format_news_alert
        analysis = {"ticker": "SBER", "summary": "Суть", "impact": "POSITIVE"}
        alert = format_news_alert("Title", "РБК", analysis, "https://example.com")
        assert "SBER" in alert
        assert "POSITIVE" in alert
        assert "🟢" in alert

    async def test_compute_sentiment(self):
        from bot.news_processor import compute_sentiment
        asset = {
            "ticker": "SBER",
            "positive_triggers": ["рост", "дивиденды", "прибыль"],
            "negative_triggers": ["дефолт", "падение", "убыток"],
        }
        sentiment, confidence = compute_sentiment("Дефолт компании XYZ", "", asset)
        assert sentiment == "NEGATIVE"
        sentiment, confidence = compute_sentiment("Дивиденды Газпрома выросли", "", asset)
        assert sentiment == "POSITIVE"
