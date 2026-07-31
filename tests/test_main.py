import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock bot.scheduler before main.py tries to import it
mock_scheduler = MagicMock()
mock_scheduler.NO_INTERVAL = None
sys.modules["bot.scheduler"] = MagicMock()
sys.modules["bot.scheduler"].setup_scheduler = MagicMock(return_value=mock_scheduler)

from bot.database import set_user, grant_trial, create_channel
from bot.rate_limiter import RateLimiter


def _make_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))
    bot.edit_message_text = AsyncMock()
    return bot


class TestAutoScanRateLimiter:
    """auto_scan_job must save to channel_news BEFORE the rate limit check."""

    async def test_save_before_rate_limit_prevents_reprocessing(self):
        from main import auto_scan_job

        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "Тестовая лента", ["новость"])

        bot = _make_bot()

        fake_news = [{"title": "Экстренная новость", "source": "Test", "link": "", "summary": "Текст"}]

        rate_limiter_mock = AsyncMock()
        rate_limiter_mock.can_send.return_value = False
        rate_limiter_mock.get_wait_time.return_value = 10.0

        save_news_mock = AsyncMock()

        with patch("main.fetch_news", new_callable=AsyncMock, return_value=fake_news):
            with patch("main.save_channel_news_batch", new=save_news_mock):
                with patch("main._rate_limiter", rate_limiter_mock):
                    await auto_scan_job(bot)

        save_news_mock.assert_called()
        call_items = save_news_mock.call_args[0][0]
        assert len(call_items) == 1
        assert "channel_id" in call_items[0]
        assert "content_hash" in call_items[0]
        assert call_items[0]["content_hash"] is not None

    async def test_no_active_users_skips_scan(self):
        from main import auto_scan_job
        bot = _make_bot()

        with patch("main.get_active_users_with_assets", new_callable=AsyncMock, return_value=[]):
            await auto_scan_job(bot)

        bot.send_message.assert_not_called()
