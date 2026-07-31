import datetime
import json
import aiosqlite
from pathlib import Path
from . import config

_db: aiosqlite.Connection | None = None


async def init_db():
    global _db
    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(config.DATABASE_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA busy_timeout=5000")
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            username      TEXT,
            full_name     TEXT,
            language      TEXT NOT NULL DEFAULT 'ru',
            access_until  TEXT,
            is_trial_used INTEGER NOT NULL DEFAULT 0,
            created       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _db.execute("""
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
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS pending_deletions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            delete_at  TIMESTAMP NOT NULL
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash TEXT NOT NULL,
            user_id    INTEGER NOT NULL,
            source     TEXT,
            title      TEXT NOT NULL,
            url        TEXT,
            ticker     TEXT,
            summary    TEXT,
            impact     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, coltype in (("user_id", "INTEGER"), ("source", "TEXT"), ("url", "TEXT"), ("ticker", "TEXT"), ("summary", "TEXT"), ("impact", "TEXT"), ("created_at", "TIMESTAMP")):
        try:
            await _db.execute(f"ALTER TABLE news ADD COLUMN {col} {coltype}")
        except Exception:
            pass
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_hash ON news(content_hash)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_user_hash ON news(user_id, content_hash)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_created ON news(created_at)"
    )
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS tracked_assets (
            ticker           TEXT PRIMARY KEY,
            name             TEXT,
            keywords_json    TEXT NOT NULL DEFAULT '[]',
            positive_triggers TEXT NOT NULL DEFAULT '[]',
            negative_triggers TEXT NOT NULL DEFAULT '[]',
            description      TEXT,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS pinned_news (
            user_id    INTEGER PRIMARY KEY,
            chat_id    INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS scan_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            users_count INTEGER,
            news_fetched INTEGER,
            news_matched INTEGER,
            news_skipped_seen INTEGER,
            news_skipped_irrelevant INTEGER,
            messages_sent INTEGER,
            processing_ms INTEGER
        )
    """)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS news_delivery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT,
            title TEXT,
            source TEXT,
            impact TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_channels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         TEXT NOT NULL,
            keywords_json TEXT NOT NULL DEFAULT '[]',
            ticker       TEXT,
            source_tags  TEXT NOT NULL DEFAULT '[]',
            topics       TEXT NOT NULL DEFAULT '[]',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, name)
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_channels_user ON user_channels(user_id)"
    )
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS channel_news (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id      INTEGER NOT NULL,
            news_content_hash TEXT NOT NULL,
            matched_keyword TEXT,
            ticker_hint     TEXT,
            impact          TEXT,
            sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES user_channels(id) ON DELETE CASCADE
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_news_channel ON channel_news(channel_id)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_delivery_user ON news_delivery_log(user_id)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_pending_deletions_delete_at ON pending_deletions(delete_at)"
    )

    # ── News buffer: global pool of all fetched news with importance score ──
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS news_buffer (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash    TEXT NOT NULL UNIQUE,
            source          TEXT,
            title           TEXT NOT NULL,
            url             TEXT,
            summary         TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            importance_score REAL NOT NULL DEFAULT 0.5,
            match_count     INTEGER NOT NULL DEFAULT 0,
            is_used         INTEGER NOT NULL DEFAULT 0
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_buffer_hash ON news_buffer(content_hash)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_buffer_importance ON news_buffer(importance_score DESC, created_at DESC)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_buffer_match ON news_buffer(match_count DESC, created_at DESC)"
    )

    # ── User news priority: per-user view of buffer with user-specific score ──
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS user_news_priority (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            content_hash    TEXT NOT NULL,
            ticker          TEXT,
            importance_score REAL NOT NULL DEFAULT 0.5,
            sent_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read         INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (content_hash) REFERENCES news_buffer(content_hash),
            UNIQUE(user_id, content_hash)
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_unp_user ON user_news_priority(user_id, importance_score DESC, sent_at DESC)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_unp_user_unread ON user_news_priority(user_id, is_read, importance_score DESC)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_unp_hash ON user_news_priority(content_hash)"
    )

    # ── News ticker popularity: how many subscribers per ticker per news ──
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS news_ticker_popularity (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash    TEXT NOT NULL,
            ticker          TEXT NOT NULL,
            subscriber_count INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_hash) REFERENCES news_buffer(content_hash),
            UNIQUE(content_hash, ticker)
        )
    """)
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_ntp_ticker_sub ON news_ticker_popularity(ticker, subscriber_count DESC)"
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_ntp_hash_ticker ON news_ticker_popularity(content_hash, ticker)"
    )

    cols = {row[1] for row in await (await _db.execute("PRAGMA table_info(users)")).fetchall()}
    if "access_until" not in cols:
        await _db.execute("ALTER TABLE users ADD COLUMN access_until TEXT")
    if "is_trial_used" not in cols:
        await _db.execute("ALTER TABLE users ADD COLUMN is_trial_used INTEGER NOT NULL DEFAULT 0")

    news_cols = {row[1] for row in await (await _db.execute("PRAGMA table_info(news)")).fetchall()}
    if "user_id" not in news_cols:
        await _db.execute("ALTER TABLE news ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")

    pinned_cols = {row[1] for row in await (await _db.execute("PRAGMA table_info(pinned_news)")).fetchall()}
    if "channel_id" not in pinned_cols:
        await _db.execute("ALTER TABLE pinned_news ADD COLUMN channel_id INTEGER")

    uc_cols = {row[1] for row in await (await _db.execute("PRAGMA table_info(user_channels)")).fetchall()}
    if "source_tags" not in uc_cols:
        await _db.execute("ALTER TABLE user_channels ADD COLUMN source_tags TEXT NOT NULL DEFAULT '[]'")
    if "topics" not in uc_cols:
        await _db.execute("ALTER TABLE user_channels ADD COLUMN topics TEXT NOT NULL DEFAULT '[]'")

    async with _db.execute(
        "SELECT COUNT(*) FROM user_channels"
    ) as cur:
        existing_channels = (await cur.fetchone())[0]
    if existing_channels == 0:
        async with _db.execute(
            "SELECT user_id, ticker, name FROM finance_subscriptions"
        ) as cur:
            old_subs = await cur.fetchall()
        if old_subs:
            for user_id, ticker, name in old_subs:
                ch_name = name if name else ticker
                await _db.execute("""
                    INSERT OR IGNORE INTO user_channels (user_id, name, keywords_json, ticker)
                    VALUES (?, ?, ?, ?)
                """, (user_id, ch_name, json.dumps([ticker.lower()]), ticker.upper()))
            import logging
            logging.getLogger(__name__).info(
                f"Migrated {len(old_subs)} finance_subscriptions to user_channels"
            )

    await _db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _get_db():
    return _db


async def get_user(user_id: int) -> dict | None:
    db = await _get_db()
    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_user(user_id: int, username: str | None, full_name: str, lang: str):
    db = await _get_db()
    await db.execute("""
        INSERT INTO users (user_id, username, full_name, language)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name
    """, (user_id, username, full_name, lang))
    await db.commit()


async def set_language(user_id: int, lang: str):
    db = await _get_db()
    await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    await db.commit()


async def get_language(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user else "ru"


async def has_access(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user["access_until"]:
        return False
    try:
        until = datetime.datetime.fromisoformat(user["access_until"])
        return until > datetime.datetime.now()
    except (ValueError, TypeError):
        return False


async def grant_trial(user_id: int, days: int = 30):
    user = await get_user(user_id)
    if user and user.get("access_until"):
        try:
            if datetime.datetime.fromisoformat(user["access_until"]) > datetime.datetime.now():
                return False
        except (ValueError, TypeError):
            pass
    until = datetime.datetime.now() + datetime.timedelta(days=days)
    db = await _get_db()
    await db.execute(
        "UPDATE users SET access_until = ?, is_trial_used = 1 WHERE user_id = ?",
        (until.isoformat(), user_id),
    )
    await db.commit()
    return True


async def grant_access(user_id: int, days: int):
    user = await get_user(user_id)
    now = datetime.datetime.now()
    if user and user["access_until"]:
        try:
            base = datetime.datetime.fromisoformat(user["access_until"])
            if base > now:
                base = now
        except (ValueError, TypeError):
            base = now
    else:
        base = now
    until = base + datetime.timedelta(days=days)
    db = await _get_db()
    await db.execute(
        "UPDATE users SET access_until = ? WHERE user_id = ?",
        (until.isoformat(), user_id),
    )
    await db.commit()
    return until


async def get_access_info(user_id: int) -> dict:
    user = await get_user(user_id)
    if not user:
        return {"has_access": False, "until": None, "days_left": 0}
    until_str = user["access_until"]
    if not until_str:
        return {"has_access": False, "until": None, "days_left": 0}
    try:
        until = datetime.datetime.fromisoformat(until_str)
        now = datetime.datetime.now()
        delta = until - now
        days_left = max(0, delta.days)
        return {"has_access": until > now, "until": until_str[:10], "days_left": days_left}
    except (ValueError, TypeError):
        return {"has_access": False, "until": None, "days_left": 0}


async def get_users_expiring_soon(days: int = 2) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT user_id, username, access_until FROM users "
        "WHERE access_until IS NOT NULL "
        "AND access_until > datetime('now') "
        "AND access_until <= datetime('now', '+' || ? || ' days')",
        (days,),
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def add_finance_subscription(user_id: int, ticker: str, name: str = ""):
    db = await _get_db()
    await db.execute("""
        INSERT OR IGNORE INTO finance_subscriptions (user_id, ticker, name)
        VALUES (?, ?, ?)
    """, (user_id, ticker.upper(), name))
    await db.commit()
    try:
        await refresh_ticker_popularity(ticker.upper())
    except Exception:
        pass


async def remove_finance_subscription(user_id: int, ticker: str):
    db = await _get_db()
    await db.execute(
        "DELETE FROM finance_subscriptions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker.upper()),
    )
    await db.commit()
    try:
        await refresh_ticker_popularity(ticker.upper())
    except Exception:
        pass


async def get_finance_subscriptions(user_id: int) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT ticker, name FROM finance_subscriptions WHERE user_id = ?",
        (user_id,),
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def get_all_finance_users() -> list[dict]:
    db = await _get_db()
    async with db.execute("SELECT DISTINCT user_id FROM finance_subscriptions") as cur:
        return [dict(row) for row in await cur.fetchall()]


async def get_active_users_with_assets() -> list[dict]:
    db = await _get_db()
    async with db.execute("""
        SELECT DISTINCT u.user_id, u.language
        FROM users u
        INNER JOIN user_channels uc ON u.user_id = uc.user_id
        WHERE u.access_until IS NOT NULL
          AND u.access_until > datetime('now')
    """) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def get_user_tickers(user_id: int) -> list[str]:
    subs = await get_finance_subscriptions(user_id)
    return [s["ticker"] for s in subs]


async def create_channel(user_id: int, name: str, keywords: list[str],
                         ticker: str | None = None,
                         source_tags: list[str] | None = None,
                         topics: list[str] | None = None) -> int | None:
    db = await _get_db()
    try:
        cursor = await db.execute("""
            INSERT INTO user_channels (user_id, name, keywords_json, ticker, source_tags, topics)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, json.dumps(keywords, ensure_ascii=False),
              ticker.upper() if ticker else None,
              json.dumps(source_tags or [], ensure_ascii=False),
              json.dumps(topics or [], ensure_ascii=False)))
        await db.commit()
        return cursor.lastrowid
    except aiosqlite.IntegrityError:
        return None


async def get_user_channels(user_id: int) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM user_channels WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ) as cur:
        results = []
        for row in await cur.fetchall():
            d = dict(row)
            d["keywords"] = json.loads(d["keywords_json"])
            d["source_tags"] = json.loads(d.get("source_tags", "[]"))
            d["topics"] = json.loads(d.get("topics", "[]"))
            results.append(d)
        return results


async def get_channel(channel_id: int) -> dict | None:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM user_channels WHERE id = ?", (channel_id,)
    ) as cur:
        row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["keywords"] = json.loads(d["keywords_json"])
        d["source_tags"] = json.loads(d.get("source_tags", "[]"))
        d["topics"] = json.loads(d.get("topics", "[]"))
        return d


async def get_channel_by_name(user_id: int, name: str) -> dict | None:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM user_channels WHERE user_id = ? AND name = ?",
        (user_id, name),
    ) as cur:
        row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["keywords"] = json.loads(d["keywords_json"])
        d["source_tags"] = json.loads(d.get("source_tags", "[]"))
        d["topics"] = json.loads(d.get("topics", "[]"))
        return d


async def update_channel_keywords(channel_id: int, keywords: list[str]):
    db = await _get_db()
    await db.execute(
        "UPDATE user_channels SET keywords_json = ? WHERE id = ?",
        (json.dumps(keywords, ensure_ascii=False), channel_id),
    )
    await db.commit()


async def update_channel_name(channel_id: int, name: str):
    db = await _get_db()
    await db.execute(
        "UPDATE user_channels SET name = ? WHERE id = ?",
        (name, channel_id),
    )
    await db.commit()


async def update_channel_ticker(channel_id: int, ticker: str | None):
    db = await _get_db()
    await db.execute(
        "UPDATE user_channels SET ticker = ? WHERE id = ?",
        (ticker.upper() if ticker else None, channel_id),
    )
    await db.commit()


async def update_channel_source_tags(channel_id: int, source_tags: list[str]):
    db = await _get_db()
    await db.execute(
        "UPDATE user_channels SET source_tags = ? WHERE id = ?",
        (json.dumps(source_tags, ensure_ascii=False), channel_id),
    )
    await db.commit()


async def update_channel_topics(channel_id: int, topics: list[str]):
    db = await _get_db()
    await db.execute(
        "UPDATE user_channels SET topics = ? WHERE id = ?",
        (json.dumps(topics, ensure_ascii=False), channel_id),
    )
    await db.commit()


async def delete_channel(channel_id: int):
    db = await _get_db()
    await db.execute("DELETE FROM user_channels WHERE id = ?", (channel_id,))
    await db.commit()


async def delete_user_channels(user_id: int):
    db = await _get_db()
    await db.execute("DELETE FROM user_channels WHERE user_id = ?", (user_id,))
    await db.commit()


async def get_all_user_channels() -> list[dict]:
    db = await _get_db()
    async with db.execute("""
        SELECT uc.*, u.language
        FROM user_channels uc
        INNER JOIN users u ON uc.user_id = u.user_id
        WHERE u.access_until IS NOT NULL
          AND u.access_until > datetime('now')
    """) as cur:
        results = []
        for row in await cur.fetchall():
            d = dict(row)
            d["keywords"] = json.loads(d["keywords_json"])
            d["source_tags"] = json.loads(d.get("source_tags", "[]"))
            d["topics"] = json.loads(d.get("topics", "[]"))
            results.append(d)
        return results


async def save_channel_news(channel_id: int, news_content_hash: str,
                            matched_keyword: str, ticker_hint: str = "",
                            impact: str = "NEUTRAL"):
    db = await _get_db()
    await db.execute("""
        INSERT INTO channel_news (channel_id, news_content_hash, matched_keyword, ticker_hint, impact)
        VALUES (?, ?, ?, ?, ?)
    """, (channel_id, news_content_hash, matched_keyword, ticker_hint, impact))
    await db.commit()


async def is_channel_news_seen(channel_id: int, news_content_hash: str) -> bool:
    db = await _get_db()
    async with db.execute(
        "SELECT 1 FROM channel_news WHERE channel_id = ? AND news_content_hash = ?",
        (channel_id, news_content_hash),
    ) as cur:
        return await cur.fetchone() is not None


async def get_channel_news_log(channel_id: int, limit: int = 50) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM channel_news WHERE channel_id = ? ORDER BY sent_at DESC LIMIT ?",
        (channel_id, limit),
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def cleanup_old_channel_news(max_age_hours: int = 24) -> int:
    db = await _get_db()
    cursor = await db.execute(
        "DELETE FROM channel_news WHERE sent_at < datetime('now', ?)",
        (f"-{max_age_hours} hours",),
    )
    await db.commit()
    return cursor.rowcount


async def get_total_users() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(*) FROM users") as cur:
        return (await cur.fetchone())[0]


async def get_new_users_today() -> int:
    db = await _get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM users WHERE DATE(created) = DATE('now')"
    ) as cur:
        return (await cur.fetchone())[0]


async def get_new_users_this_week() -> int:
    db = await _get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM users WHERE created >= DATE('now', '-7 days')"
    ) as cur:
        return (await cur.fetchone())[0]


async def get_language_stats() -> dict[str, int]:
    db = await _get_db()
    async with db.execute(
        "SELECT language, COUNT(*) as cnt FROM users GROUP BY language"
    ) as cur:
        return {row[0]: row[1] for row in await cur.fetchall()}


async def get_finance_subscribers_count() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(DISTINCT user_id) FROM finance_subscriptions") as cur:
        return (await cur.fetchone())[0]


async def get_finance_tickers_count() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(*) FROM finance_subscriptions") as cur:
        return (await cur.fetchone())[0]


async def get_user_channels_count() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(DISTINCT user_id) FROM user_channels") as cur:
        return (await cur.fetchone())[0]


async def get_channels_count() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(*) FROM user_channels") as cur:
        return (await cur.fetchone())[0]


async def get_news_sent_count() -> int:
    db = await _get_db()
    async with db.execute("SELECT COUNT(*) FROM news") as cur:
        return (await cur.fetchone())[0]


async def get_all_users() -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT user_id, username, full_name, language, access_until, created FROM users ORDER BY created DESC"
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def get_full_stats() -> dict:
    total = await get_total_users()
    new_today = await get_new_users_today()
    new_week = await get_new_users_this_week()
    lang_stats = await get_language_stats()
    fin_subs = await get_finance_subscribers_count()
    fin_tickers = await get_finance_tickers_count()
    news_sent = await get_news_sent_count()
    user_channels = await get_user_channels_count()
    channels = await get_channels_count()
    return {
        "total": total,
        "new_today": new_today,
        "new_week": new_week,
        "lang_ru": lang_stats.get("ru", 0),
        "lang_en": lang_stats.get("en", 0),
        "finance_subs": fin_subs,
        "finance_tickers": fin_tickers,
        "news_sent": news_sent,
        "user_channels": user_channels,
        "channels": channels,
    }


async def schedule_deletion(chat_id: int, message_id: int, delay_seconds: int = 7200):
    db = await _get_db()
    if delay_seconds >= 0:
        await db.execute(
            "INSERT INTO pending_deletions (chat_id, message_id, delete_at) "
            "VALUES (?, ?, datetime('now', '+' || ? || ' seconds'))",
            (chat_id, message_id, delay_seconds),
        )
    else:
        await db.execute(
            "INSERT INTO pending_deletions (chat_id, message_id, delete_at) "
            "VALUES (?, ?, datetime('now', '-' || ? || ' seconds'))",
            (chat_id, message_id, abs(delay_seconds)),
        )
    await db.commit()


async def get_due_deletions() -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT id, chat_id, message_id FROM pending_deletions "
        "WHERE delete_at <= datetime('now')"
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def remove_deletion(deletion_id: int):
    db = await _get_db()
    await db.execute("DELETE FROM pending_deletions WHERE id = ?", (deletion_id,))
    await db.commit()


async def is_news_seen(content_hash: str, user_id: int) -> bool:
    db = await _get_db()
    async with db.execute(
        "SELECT 1 FROM news WHERE content_hash = ? AND user_id = ?", (content_hash, user_id)
    ) as cur:
        return await cur.fetchone() is not None


async def save_news(content_hash: str, user_id: int, source: str, title: str, url: str,
                    ticker: str, summary: str, impact: str):
    db = await _get_db()
    await db.execute(
        "INSERT INTO news (content_hash, user_id, source, title, url, ticker, summary, impact) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (content_hash, user_id, source, title, url, ticker, summary, impact),
    )
    await db.commit()


# ── News buffer (new system) ──

async def upsert_news_buffer(content_hash: str, source: str, title: str, url: str,
                              summary: str, importance_score: float, match_count: int = 0,
                              is_used: int = 0) -> bool:
    db = await _get_db()
    existing = await (await db.execute(
        "SELECT importance_score, id FROM news_buffer WHERE content_hash = ?", (content_hash,)
    )).fetchone()
    if existing:
        if importance_score > existing["importance_score"]:
            await db.execute("""
                UPDATE news_buffer SET
                    source = ?, title = ?, url = ?, summary = ?,
                    importance_score = ?, match_count = match_count + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE content_hash = ?
            """, (source, title, url, summary, importance_score, match_count, content_hash))
            await db.commit()
            return True
        else:
            await db.execute("""
                UPDATE news_buffer SET
                    match_count = match_count + ?, updated_at = CURRENT_TIMESTAMP
                WHERE content_hash = ?
            """, (match_count, content_hash))
            await db.commit()
            return False
    await db.execute("""
        INSERT INTO news_buffer (content_hash, source, title, url, summary, importance_score,
                                  match_count, is_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (content_hash, source, title, url, summary, importance_score, match_count, is_used))
    await db.commit()
    return True


async def upsert_user_news_priority(user_id: int, content_hash: str, ticker: str | None,
                                     importance_score: float):
    db = await _get_db()
    existing = await (await db.execute(
        "SELECT importance_score FROM user_news_priority WHERE user_id = ? AND content_hash = ?",
        (user_id, content_hash),
    )).fetchone()
    if existing:
        if importance_score > existing["importance_score"]:
            await db.execute("""
                UPDATE user_news_priority
                SET importance_score = ?, sent_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND content_hash = ?
            """, (importance_score, user_id, content_hash))
    else:
        await db.execute("""
            INSERT INTO user_news_priority (user_id, content_hash, ticker, importance_score)
            VALUES (?, ?, ?, ?)
        """, (user_id, content_hash, ticker, importance_score))
    await db.commit()


async def upsert_news_ticker_popularity(content_hash: str, ticker: str, subscriber_count: int):
    db = await _get_db()
    await db.execute("""
        INSERT INTO news_ticker_popularity (content_hash, ticker, subscriber_count)
        VALUES (?, ?, ?)
        ON CONFLICT(content_hash, ticker) DO UPDATE SET
            subscriber_count = excluded.subscriber_count
    """, (content_hash, ticker, subscriber_count))
    await db.commit()


async def refresh_news_buffer_usage(content_hash: str):
    db = await _get_db()
    await db.execute(
        "UPDATE news_buffer SET is_used = 1 WHERE content_hash = ?",
        (content_hash,),
    )
    await db.commit()


async def get_news_for_user(user_id: int, limit: int = 20,
                            only_unread: bool = False,
                            min_score: float = 0.0) -> list[dict]:
    db = await _get_db()
    query = """
        SELECT nb.*, unp.importance_score as user_score,
               unp.is_read, unp.sent_at, unp.ticker
        FROM news_buffer nb
        INNER JOIN user_news_priority unp ON nb.content_hash = unp.content_hash
        WHERE unp.user_id = ?
    """
    params: list = [user_id]
    if only_unread:
        query += " AND unp.is_read = 0"
    if min_score > 0.0:
        query += " AND unp.importance_score >= ?"
        params.append(min_score)
    query += " ORDER BY unp.importance_score DESC, nb.created_at DESC LIMIT ?"
    params.append(limit)
    async with db.execute(query, params) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def get_top_news_by_popularity(ticker: str | None = None, limit: int = 10) -> list[dict]:
    db = await _get_db()
    if ticker:
        query = """
            SELECT nb.*, ntp.subscriber_count, ntp.ticker
            FROM news_buffer nb
            INNER JOIN news_ticker_popularity ntp ON nb.content_hash = ntp.content_hash
            WHERE ntp.ticker = ?
            ORDER BY nb.importance_score DESC, ntp.subscriber_count DESC
            LIMIT ?
        """
        async with db.execute(query, (ticker, limit)) as cur:
            return [dict(row) for row in await cur.fetchall()]
    else:
        query = """
            SELECT nb.*, COALESCE(SUM(ntp.subscriber_count), 0) as total_subscribers
            FROM news_buffer nb
            LEFT JOIN news_ticker_popularity ntp ON nb.content_hash = ntp.content_hash
            WHERE nb.is_used = 0
            GROUP BY nb.id
            ORDER BY nb.importance_score DESC, total_subscribers DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_news_summary(user_id: int) -> dict:
    db = await _get_db()
    async with db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
            COALESCE(MAX(importance_score), 0.0) as max_score
        FROM user_news_priority WHERE user_id = ?
    """, (user_id,)) as cur:
        row = await cur.fetchone()
        result = dict(row) if row else {"total": 0, "unread": 0, "max_score": 0.0}
    async with db.execute("""
        SELECT COUNT(*) as available
        FROM news_buffer
        WHERE is_used = 1
    """) as cur:
        row = await cur.fetchone()
        result["available"] = row[0] if row else 0
    return result


async def refresh_ticker_popularity(ticker: str):
    db = await _get_db()
    sub_count = await (await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM finance_subscriptions WHERE ticker = ?",
        (ticker.upper(),),
    )).fetchone()
    total = sub_count[0] if sub_count else 0
    uc_count = await (await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_channels WHERE ticker = ?",
        (ticker.upper(),),
    )).fetchone()
    total += uc_count[0] if uc_count else 0
    await db.execute("""
        UPDATE news_ticker_popularity
        SET subscriber_count = ?
        WHERE ticker = ?
    """, (total, ticker.upper()))
    await db.commit()
    return total


async def get_max_ticker_subscriber_count() -> int:
    db = await _get_db()
    async with db.execute("""
        SELECT MAX(cnt) FROM (
            SELECT COUNT(DISTINCT user_id) as cnt FROM finance_subscriptions GROUP BY ticker
            UNION ALL
            SELECT COUNT(DISTINCT user_id) as cnt FROM user_channels WHERE ticker IS NOT NULL GROUP BY ticker
        )
    """) as cur:
        row = await cur.fetchone()
        return row[0] if row and row[0] else 1


async def dynamic_cleanup_news_buffer() -> int:
    db = await _get_db()
    cursor = await db.execute("""
        DELETE FROM news_buffer
        WHERE (importance_score >= 0.7 AND created_at < datetime('now', '-7 days'))
           OR (importance_score >= 0.3 AND importance_score < 0.7 AND created_at < datetime('now', '-3 days'))
           OR (importance_score < 0.3 AND created_at < datetime('now', '-24 hours'))
    """)
    deleted_buffer = cursor.rowcount
    cursor2 = await db.execute("""
        DELETE FROM user_news_priority
        WHERE content_hash NOT IN (SELECT content_hash FROM news_buffer)
    """)
    cursor3 = await db.execute("""
        DELETE FROM news_ticker_popularity
        WHERE content_hash NOT IN (SELECT content_hash FROM news_buffer)
    """)
    await db.commit()
    return deleted_buffer


async def get_all_news_buffer_hashes() -> set[str]:
    db = await _get_db()
    async with db.execute("SELECT content_hash FROM news_buffer") as cur:
        return {row[0] for row in await cur.fetchall()}


async def get_subscriber_count_for_ticker(ticker: str) -> int:
    db = await _get_db()
    sub = await (await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM finance_subscriptions WHERE ticker = ?",
        (ticker.upper(),),
    )).fetchone()
    uc = await (await db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM user_channels WHERE ticker = ?",
        (ticker.upper(),),
    )).fetchone()
    return (sub[0] if sub else 0) + (uc[0] if uc else 0)


async def cleanup_old_news(max_age_hours: int = 24) -> int:
    db = await _get_db()
    cursor = await db.execute(
        "DELETE FROM news WHERE created_at < datetime('now', ?)",
        (f"-{max_age_hours} hours",),
    )
    await db.commit()
    return cursor.rowcount


async def save_tracked_asset(ticker: str, name: str, keywords: list[str],
                              positive_triggers: list[str], negative_triggers: list[str],
                              description: str = ""):
    db = await _get_db()
    await db.execute("""
        INSERT INTO tracked_assets (ticker, name, keywords_json, positive_triggers, negative_triggers, description, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(ticker) DO UPDATE SET
            name = excluded.name,
            keywords_json = excluded.keywords_json,
            positive_triggers = excluded.positive_triggers,
            negative_triggers = excluded.negative_triggers,
            description = excluded.description,
            updated_at = datetime('now')
    """, (ticker, name, json.dumps(keywords, ensure_ascii=False),
          json.dumps(positive_triggers, ensure_ascii=False),
          json.dumps(negative_triggers, ensure_ascii=False), description))
    await db.commit()


async def get_tracked_asset(ticker: str) -> dict | None:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM tracked_assets WHERE ticker = ?", (ticker,)
    ) as cur:
        row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["keywords"] = json.loads(d["keywords_json"])
        d["positive_triggers"] = json.loads(d["positive_triggers"])
        d["negative_triggers"] = json.loads(d["negative_triggers"])
        return d


async def get_all_tracked_assets() -> list[dict]:
    db = await _get_db()
    async with db.execute("SELECT * FROM tracked_assets") as cur:
        results = []
        for row in await cur.fetchall():
            d = dict(row)
            d["keywords"] = json.loads(d["keywords_json"])
            d["positive_triggers"] = json.loads(d["positive_triggers"])
            d["negative_triggers"] = json.loads(d["negative_triggers"])
            results.append(d)
        return results


async def remove_tracked_asset(ticker: str):
    db = await _get_db()
    await db.execute("DELETE FROM tracked_assets WHERE ticker = ?", (ticker,))
    await db.commit()


async def has_tracked_asset(ticker: str) -> bool:
    db = await _get_db()
    async with db.execute(
        "SELECT 1 FROM tracked_assets WHERE ticker = ?", (ticker,)
    ) as cur:
        return await cur.fetchone() is not None


async def get_pinned_news(user_id: int) -> dict | None:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM pinned_news WHERE user_id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_pinned_news_by_channel(channel_id: int) -> dict | None:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM pinned_news WHERE channel_id = ?", (channel_id,)
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def save_pinned_news(user_id: int, chat_id: int, message_id: int,
                           channel_id: int | None = None):
    db = await _get_db()
    if channel_id is not None:
        existing = await (await db.execute(
            "SELECT user_id FROM pinned_news WHERE channel_id = ?", (channel_id,)
        )).fetchone()
        if existing:
            await db.execute("""
                UPDATE pinned_news SET chat_id = ?, message_id = ?, updated_at = datetime('now')
                WHERE channel_id = ?
            """, (chat_id, message_id, channel_id))
        else:
            await db.execute("""
                INSERT INTO pinned_news (user_id, chat_id, message_id, channel_id, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (user_id, chat_id, message_id, channel_id))
        await db.commit()
    else:
        await db.execute("""
            INSERT INTO pinned_news (user_id, chat_id, message_id, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                message_id = excluded.message_id,
                updated_at = datetime('now')
        """, (user_id, chat_id, message_id))
        await db.commit()


async def remove_pinned_news(user_id: int):
    db = await _get_db()
    await db.execute("DELETE FROM pinned_news WHERE user_id = ?", (user_id,))
    await db.commit()


async def remove_pinned_news_by_channel(channel_id: int):
    db = await _get_db()
    await db.execute("DELETE FROM pinned_news WHERE channel_id = ?", (channel_id,))
    await db.commit()


async def save_scan_metrics(users_count: int, news_fetched: int, news_matched: int,
                            news_skipped_seen: int, news_skipped_irrelevant: int,
                            messages_sent: int, processing_ms: int):
    db = await _get_db()
    await db.execute(
        "INSERT INTO scan_metrics "
        "(users_count, news_fetched, news_matched, news_skipped_seen, "
        " news_skipped_irrelevant, messages_sent, processing_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (users_count, news_fetched, news_matched, news_skipped_seen,
         news_skipped_irrelevant, messages_sent, processing_ms),
    )
    await db.commit()


async def get_recent_metrics(limit: int = 10) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM scan_metrics ORDER BY scan_time DESC LIMIT ?", (limit,)
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def log_news_delivery(user_id: int, ticker: str, title: str, source: str, impact: str):
    db = await _get_db()
    await db.execute(
        "INSERT INTO news_delivery_log (user_id, ticker, title, source, impact) VALUES (?, ?, ?, ?, ?)",
        (user_id, ticker, title, source, impact),
    )
    await db.commit()


async def get_user_delivery_log(user_id: int, limit: int = 50) -> list[dict]:
    db = await _get_db()
    async with db.execute(
        "SELECT * FROM news_delivery_log WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?",
        (user_id, limit),
    ) as cur:
        return [dict(row) for row in await cur.fetchall()]


async def save_news_batch(items: list[dict]) -> int:
    db = await _get_db()
    for item in items:
        await db.execute(
            "INSERT INTO news (content_hash, user_id, source, title, url, ticker, summary, impact) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (item["content_hash"], item["user_id"], item["source"], item["title"],
             item.get("link", ""), item.get("ticker_hint", ""),
             item["summary"], item["impact"]),
        )
    await db.commit()
    return len(items)


async def save_channel_news_batch(items: list[dict]) -> int:
    db = await _get_db()
    for item in items:
        await db.execute("""
            INSERT INTO channel_news (channel_id, news_content_hash, matched_keyword, ticker_hint, impact)
            VALUES (?, ?, ?, ?, ?)
        """, (item["channel_id"], item["content_hash"],
              item.get("matched_keyword", ""), item.get("ticker_hint", ""),
              item["impact"]))
    await db.commit()
    return len(items)


async def log_news_delivery_batch(items: list[dict]) -> int:
    db = await _get_db()
    for item in items:
        await db.execute(
            "INSERT INTO news_delivery_log (user_id, ticker, title, source, impact) VALUES (?, ?, ?, ?, ?)",
            (item["user_id"], item.get("ticker_hint", ""),
             item["title"], item["source"], item["impact"]),
        )
    await db.commit()
    return len(items)


async def cleanup_old_delivery_logs(max_age_days: int = 30) -> int:
    db = await _get_db()
    cursor = await db.execute(
        "DELETE FROM news_delivery_log WHERE sent_at < datetime('now', ?)",
        (f"-{max_age_days} days",),
    )
    await db.commit()
    return cursor.rowcount
