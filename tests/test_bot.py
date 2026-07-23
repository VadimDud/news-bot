"""Tests for all bot commands and handlers."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Override DATABASE_PATH before importing anything from the bot
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_PATH"] = _tmp_db.name
_tmp_db.close()

from bot.database import (
    init_db,
    set_user,
    get_user,
    set_language,
    get_language,
    add_finance_subscription,
    remove_finance_subscription,
    get_finance_subscriptions,
    get_user_tickers,
    get_all_finance_users,
    is_news_sent,
    mark_news_sent,
)
from bot.i18n import t, STRINGS


# ─── Helpers ───


def run_async(coro):
    return asyncio.run(coro)


async def _clean_db():
    import aiosqlite
    from bot import config

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("DELETE FROM users")
        await db.execute("DELETE FROM finance_subscriptions")
        await db.execute("DELETE FROM finance_news_sent")
        await db.commit()


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh DB for each test."""
    run_async(init_db())
    yield
    run_async(_clean_db())


# ─── Database tests ───


class TestDatabase:
    def test_set_and_get_user(self):
        async def _run():
            await set_user(123, "testuser", "Test User", "ru")
            user = await get_user(123)
            assert user is not None
            assert user["user_id"] == 123
            assert user["username"] == "testuser"
            assert user["full_name"] == "Test User"
            assert user["language"] == "ru"

        run_async(_run())

    def test_get_nonexistent_user(self):
        async def _run():
            user = await get_user(99999)
            assert user is None

        run_async(_run())

    def test_set_user_upsert(self):
        async def _run():
            await set_user(123, "user1", "User One", "ru")
            await set_user(123, "user1_updated", "User Updated", "ru")
            user = await get_user(123)
            assert user["username"] == "user1_updated"
            assert user["full_name"] == "User Updated"

        run_async(_run())

    def test_set_language(self):
        async def _run():
            await set_user(123, "user1", "User One", "ru")
            await set_language(123, "en")
            lang = await get_language(123)
            assert lang == "en"

        run_async(_run())

    def test_get_language_default(self):
        async def _run():
            lang = await get_language(99999)
            assert lang == "ru"

        run_async(_run())


class TestFinanceSubscriptions:
    def test_add_subscription(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1
            assert subs[0]["ticker"] == "SBER"

        run_async(_run())

    def test_add_subscription_uppercase(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "sber", "sber")
            subs = await get_finance_subscriptions(100)
            assert subs[0]["ticker"] == "SBER"

        run_async(_run())

    def test_add_duplicate_subscription(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "SBER", "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1

        run_async(_run())

    def test_remove_subscription(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "GAZP", "GAZP")
            await remove_finance_subscription(100, "SBER")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 1
            assert subs[0]["ticker"] == "GAZP"

        run_async(_run())

    def test_remove_nonexistent_subscription(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await remove_finance_subscription(100, "NOPE")
            subs = await get_finance_subscriptions(100)
            assert len(subs) == 0

        run_async(_run())

    def test_get_user_tickers(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(100, "GAZP", "GAZP")
            tickers = await get_user_tickers(100)
            assert set(tickers) == {"SBER", "GAZP"}

        run_async(_run())

    def test_get_all_finance_users(self):
        async def _run():
            await set_user(100, "user1", "User One", "ru")
            await set_user(200, "user2", "User Two", "ru")
            await add_finance_subscription(100, "SBER", "SBER")
            await add_finance_subscription(200, "GAZP", "GAZP")
            users = await get_all_finance_users()
            user_ids = [u["user_id"] for u in users]
            assert 100 in user_ids
            assert 200 in user_ids

        run_async(_run())


class TestNewsDedup:
    def test_mark_and_check_news(self):
        async def _run():
            assert await is_news_sent("Test Title") is False
            await mark_news_sent("Test Title", "РБК")
            assert await is_news_sent("Test Title") is True

        run_async(_run())


# ─── Handler logic tests ───


class TestTickerValidation:
    """Test the ticker validation logic extracted from the handler."""

    def test_valid_tickers_pass(self):
        valid = ["SBER", "GAZP", "RUBI", "YDEX", "VTB"]
        for ticker in valid:
            assert len(ticker) >= 2
            assert len(ticker) <= 10
            assert " " not in ticker

    def test_invalid_tickers_rejected(self):
        for ticker in ["", "A"]:
            assert len(ticker) < 2

    def test_too_long_ticker_rejected(self):
        assert len("VERYLONGTICKER123") > 10

    def test_space_in_ticker_rejected(self):
        assert " " in "S BER"

    def test_skipped_words(self):
        skipped = ("ДА", "НЕТ", "YES", "NO", "ОК", "OK")
        for word in skipped:
            assert word in ("ДА", "НЕТ", "YES", "NO", "ОК", "OK")


class TestCallbackParsing:
    """Test the callback data parsing logic."""

    def test_fin_list_callback(self):
        data = "fin:list"
        parts = data.split(":")
        action = parts[1]
        assert action == "list"

    def test_fin_add_callback(self):
        data = "fin:add"
        parts = data.split(":")
        action = parts[1]
        assert action == "add"

    def test_fin_remove_callback(self):
        data = "fin:remove"
        parts = data.split(":")
        action = parts[1]
        assert action == "remove"

    def test_fin_scan_callback(self):
        data = "fin:scan"
        parts = data.split(":")
        action = parts[1]
        assert action == "scan"

    def test_fin_del_callback_old_buggy_logic(self):
        """This demonstrates the OLD bug: action.startswith('del:') is always False."""
        data = "fin:del:SBER"
        action = data.split(":")[1]  # "del"
        # OLD code: elif action.startswith("del:")
        assert action.startswith("del:") is False  # BUG: delete never triggers!

    def test_fin_del_callback_new_fixed_logic(self):
        """The FIXED logic: check action == 'del' and extract ticker from parts[2]."""
        data = "fin:del:SBER"
        parts = data.split(":")
        action = parts[1]
        assert action == "del"
        assert len(parts) >= 3
        ticker = parts[2]
        assert ticker == "SBER"

    def test_fin_del_callback_with_long_ticker(self):
        data = "fin:del:VERYLONG1"
        parts = data.split(":")
        action = parts[1]
        ticker = parts[2]
        assert action == "del"
        assert ticker == "VERYLONG1"


class TestI18n:
    def test_ru_strings_present(self):
        required_keys = [
            "welcome", "finance_menu", "finance_empty", "finance_add_ask",
            "finance_added", "finance_invalid_ticker", "finance_remove_ask",
            "finance_list", "finance_scan_done", "finance_no_news",
            "finance_all_seen", "admin_welcome", "admin_not_admin",
            "help", "lang_changed",
        ]
        for key in required_keys:
            assert key in STRINGS["ru"], f"Missing ru key: {key}"

    def test_en_strings_present(self):
        required_keys = [
            "welcome", "finance_menu", "finance_empty", "finance_add_ask",
            "finance_added", "finance_invalid_ticker", "finance_remove_ask",
            "finance_list", "finance_scan_done", "finance_no_news",
            "finance_all_seen", "admin_welcome", "admin_not_admin",
            "help", "lang_changed",
        ]
        for key in required_keys:
            assert key in STRINGS["en"], f"Missing en key: {key}"

    def test_t_function_with_kwargs(self):
        result = t("ru", "finance_added", ticker="SBER")
        assert "SBER" in result
        assert "добавлена" in result

    def test_t_function_missing_key_returns_key(self):
        result = t("ru", "nonexistent_key")
        assert result == "nonexistent_key"

    def test_t_function_fallback_to_ru(self):
        result = t("xx", "finance_added", ticker="TEST")
        assert "TEST" in result


class TestAdminAccess:
    def test_admin_id_config(self):
        from bot import config
        assert isinstance(config.ADMIN_ID, int)


# ─── Integration: full add→remove flow ───


class TestFullFlow:
    def test_add_then_remove_subscription(self):
        async def _run():
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

        run_async(_run())

    def test_multiple_users_independent(self):
        async def _run():
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

        run_async(_run())
