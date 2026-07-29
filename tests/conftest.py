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

from bot.database import init_db


async def _clean_db():
    import aiosqlite
    from bot import config

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        for table in [
            "users", "finance_subscriptions", "finance_news_sent",
            "pending_deletions", "news", "tracked_assets",
            "pinned_news", "scan_metrics", "news_delivery_log",
            "user_channels", "channel_news",
        ]:
            await db.execute(f"DELETE FROM {table}")
        await db.commit()


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize a fresh DB for each test."""
    await init_db()
    yield
    await _clean_db()
