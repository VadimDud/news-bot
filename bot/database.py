import aiosqlite
from pathlib import Path
from . import config

_db_lock = None


async def init_db():
    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                full_name TEXT,
                language  TEXT NOT NULL DEFAULT 'ru',
                created   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS finance_subscriptions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                ticker    TEXT NOT NULL,
                name      TEXT,
                created   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, ticker)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS finance_news_sent (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT NOT NULL,
                source    TEXT,
                sent_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def _get_db():
    return await aiosqlite.connect(config.DATABASE_PATH)


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def set_user(user_id: int, username: str | None, full_name: str, lang: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, language)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name, lang))
        await db.commit()


async def set_language(user_id: int, lang: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id)
        )
        await db.commit()


async def get_language(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user else "ru"


# ── Finance subscriptions ──

async def add_finance_subscription(user_id: int, ticker: str, name: str = ""):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO finance_subscriptions (user_id, ticker, name)
            VALUES (?, ?, ?)
        """, (user_id, ticker.upper(), name))
        await db.commit()


async def remove_finance_subscription(user_id: int, ticker: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM finance_subscriptions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        )
        await db.commit()


async def get_finance_subscriptions(user_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT ticker, name FROM finance_subscriptions WHERE user_id = ?",
            (user_id,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_all_finance_users() -> list[dict]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT DISTINCT user_id FROM finance_subscriptions
        """) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_user_tickers(user_id: int) -> list[str]:
    subs = await get_finance_subscriptions(user_id)
    return [s["ticker"] for s in subs]


async def is_news_sent(title: str) -> bool:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM finance_news_sent WHERE title = ?", (title,)
        ) as cur:
            return await cur.fetchone() is not None


async def mark_news_sent(title: str, source: str = ""):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO finance_news_sent (title, source) VALUES (?, ?)",
            (title, source),
        )
        await db.commit()
