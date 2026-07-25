import datetime
import aiosqlite
from pathlib import Path
from . import config

_db_lock = None


async def init_db():
    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_deletions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                delete_at  TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                source     TEXT,
                title      TEXT NOT NULL,
                url        TEXT,
                ticker     TEXT,
                summary    TEXT,
                impact     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_hash ON news(content_hash)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_created ON news(created_at)"
        )
        await db.execute("""
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pinned_news (
                user_id    INTEGER PRIMARY KEY,
                chat_id    INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
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
        await db.execute("""
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

        # ── Migrations ──
        cols = {row[1] for row in await (await db.execute("PRAGMA table_info(users)")).fetchall()}
        if "access_until" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN access_until TEXT")
        if "is_trial_used" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN is_trial_used INTEGER NOT NULL DEFAULT 0")
        # Drop old columns if they exist (SQLite can't DROP COLUMN in older versions)
        # Old subscribed column is ignored — we use access_until now

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


# ── Access / Subscription ──

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
    """Activate trial period for a new user. Only once."""
    user = await get_user(user_id)
    if user and user["is_trial_used"]:
        return False
    until = datetime.datetime.now() + datetime.timedelta(days=days)
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET access_until = ?, is_trial_used = 1 WHERE user_id = ?",
            (until.isoformat(), user_id),
        )
        await db.commit()
    return True


async def grant_access(user_id: int, days: int):
    """Extend or set access by N days from now."""
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
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
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
    """Get users whose access expires within N days (but not yet expired)."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, access_until FROM users "
            "WHERE access_until IS NOT NULL "
            "AND access_until > datetime('now') "
            "AND access_until <= datetime('now', '+' || ? || ' days')",
            (days,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


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


async def get_active_users_with_assets() -> list[dict]:
    """Get users with active access and at least one tracked asset."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT DISTINCT u.user_id, u.language
            FROM users u
            INNER JOIN finance_subscriptions fs ON u.user_id = fs.user_id
            WHERE u.access_until IS NOT NULL
              AND u.access_until > datetime('now')
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


# ── Statistics ──

async def get_total_users() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            return (await cur.fetchone())[0]


async def get_new_users_today() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created) = DATE('now')"
        ) as cur:
            return (await cur.fetchone())[0]


async def get_new_users_this_week() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created >= DATE('now', '-7 days')"
        ) as cur:
            return (await cur.fetchone())[0]


async def get_language_stats() -> dict[str, int]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT language, COUNT(*) as cnt FROM users GROUP BY language"
        ) as cur:
            return {row[0]: row[1] for row in await cur.fetchall()}


async def get_finance_subscribers_count() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM finance_subscriptions"
        ) as cur:
            return (await cur.fetchone())[0]


async def get_finance_tickers_count() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM finance_subscriptions") as cur:
            return (await cur.fetchone())[0]


async def get_news_sent_count() -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM finance_news_sent") as cur:
            return (await cur.fetchone())[0]


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
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
    return {
        "total": total,
        "new_today": new_today,
        "new_week": new_week,
        "lang_ru": lang_stats.get("ru", 0),
        "lang_en": lang_stats.get("en", 0),
        "finance_subs": fin_subs,
        "finance_tickers": fin_tickers,
        "news_sent": news_sent,
    }


# ── Pending deletions ──

async def schedule_deletion(chat_id: int, message_id: int, delay_seconds: int = 7200):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
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
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, chat_id, message_id FROM pending_deletions "
            "WHERE delete_at <= datetime('now')"
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def remove_deletion(deletion_id: int):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("DELETE FROM pending_deletions WHERE id = ?", (deletion_id,))
        await db.commit()


async def cleanup_old_news_sent(max_age_hours: int = 24) -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM finance_news_sent WHERE sent_at < datetime('now', ?)",
            (f"-{max_age_hours} hours",),
        )
        await db.commit()
        return cursor.rowcount


# ── News table (3-stage pipeline) ──

async def is_news_seen(content_hash: str) -> bool:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM news WHERE content_hash = ?", (content_hash,)
        ) as cur:
            return await cur.fetchone() is not None


async def save_news(content_hash: str, source: str, title: str, url: str,
                    ticker: str, summary: str, impact: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO news (content_hash, source, title, url, ticker, summary, impact) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (content_hash, source, title, url, ticker, summary, impact),
        )
        await db.commit()


async def cleanup_old_news(max_age_hours: int = 24) -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM news WHERE created_at < datetime('now', ?)",
            (f"-{max_age_hours} hours",),
        )
        await db.commit()
        return cursor.rowcount


# ── Tracked assets (keyword-based filtering) ──

async def save_tracked_asset(ticker: str, name: str, keywords: list[str],
                              positive_triggers: list[str], negative_triggers: list[str],
                              description: str = ""):
    import json
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
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
    import json
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
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
    import json
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
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
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("DELETE FROM tracked_assets WHERE ticker = ?", (ticker,))
        await db.commit()


async def has_tracked_asset(ticker: str) -> bool:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM tracked_assets WHERE ticker = ?", (ticker,)
        ) as cur:
            return await cur.fetchone() is not None


# ── Pinned news message (edit-in-place) ──

async def get_pinned_news(user_id: int) -> dict | None:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pinned_news WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def save_pinned_news(user_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
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
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("DELETE FROM pinned_news WHERE user_id = ?", (user_id,))
        await db.commit()


# ── Scan metrics ──

async def save_scan_metrics(users_count: int, news_fetched: int, news_matched: int,
                            news_skipped_seen: int, news_skipped_irrelevant: int,
                            messages_sent: int, processing_ms: int):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO scan_metrics
               (users_count, news_fetched, news_matched, news_skipped_seen,
                news_skipped_irrelevant, messages_sent, processing_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (users_count, news_fetched, news_matched, news_skipped_seen,
             news_skipped_irrelevant, messages_sent, processing_ms),
        )
        await db.commit()


async def get_recent_metrics(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM scan_metrics ORDER BY scan_time DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


# ── News delivery audit log ──

async def log_news_delivery(user_id: int, ticker: str, title: str, source: str, impact: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO news_delivery_log (user_id, ticker, title, source, impact) VALUES (?, ?, ?, ?, ?)",
            (user_id, ticker, title, source, impact),
        )
        await db.commit()


async def get_user_delivery_log(user_id: int, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM news_delivery_log WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def cleanup_old_delivery_logs(max_age_days: int = 30) -> int:
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM news_delivery_log WHERE sent_at < datetime('now', ?)",
            (f"-{max_age_days} days",),
        )
        await db.commit()
        return cursor.rowcount
