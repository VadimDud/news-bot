import asyncio
import os
import sys
import tempfile

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override DATABASE_PATH before importing anything from the bot
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_PATH"] = _tmp_db.name
_tmp_db.close()

# Ensure a bot token exists so web session signing works in tests
os.environ.setdefault("BOT_TOKEN", "test-token-123")

# Disable the APITube aggregator by default so unit tests never hit the API
os.environ["APITUBE_API_KEY"] = ""
os.environ["NEWS_AGG_ENABLED"] = "false"

from bot.database import init_db, close_db, _get_db


async def _clean_db():
    db = await _get_db()
    for table in [
        "users", "finance_subscriptions",
        "pending_deletions", "news", "tracked_assets",
        "pinned_news", "scan_metrics", "news_delivery_log",
        "user_channels", "channel_news", "ai_cache",
        "news_buffer", "user_news_priority", "news_ticker_popularity",
    ]:
        await db.execute(f"DELETE FROM {table}")
    await db.commit()


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize a fresh DB for each test."""
    await close_db()
    await init_db()
    yield
    await _clean_db()
    await close_db()
