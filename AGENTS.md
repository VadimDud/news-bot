# AGENTS.md

## Project

Telegram bot for thematic news feeds with AI analysis. Python 3.12+ (Docker uses 3.12-slim, README claims 3.14+). SQLite via aiosqlite, aiogram 3.30, APScheduler.

## Commands

```bash
# Unit tests (uses temp DB, auto-cleaned between tests)
pytest tests/ -q

# Live integration test (bot must be running, sends real Telegram messages)
python test_bot_api.py --chat <chat_id>

# Run the bot
python main.py

# Docker
docker compose up -d
```

No linter, formatter, or type checker is configured. No CI workflows exist.

## Deployment

After every code change, always push to GitHub:

```bash
git add -A && git commit -m "<message>" && git push origin master
```

## Architecture

- `main.py` — entry point, APScheduler setup, background jobs (cleanup, expiry reminders, auto-scan)
- `bot/config.py` — loads `.env` via python-dotenv, all config as module-level vars
- `bot/database.py` — all SQLite queries, schema defined via `CREATE TABLE IF NOT EXISTS` (no migration tool)
- `bot/finance.py` — RSS feed parser with caching
- `bot/news_processor.py` — 4-stage pipeline: filter → sentiment → dedup → distribution
- `bot/handlers/` — aiogram routers: `start.py`, `channels.py`, `finance.py`, `admin.py`, `language.py`
- `bot/i18n.py` — ru/en localization
- `bot/sources.py` — RSS source catalog by category (9 categories)

## Key Conventions

- Database path configurable via `DATABASE_PATH` env var (default: `data/bot.db`). Docker mounts `./dbdata` to `/app/dbdata`.
- Schema changes are inline `CREATE TABLE IF NOT EXISTS` — no separate migration step. If you alter schema, the column won't appear in existing DBs. Handle gracefully.
- Tests use `pytest-asyncio` with `asyncio_mode = auto` (see `pytest.ini`). Each test gets a fresh temp DB via `conftest.py`.
- `test_bot_api.py` at repo root is a **separate** live test, not part of `pytest tests/`. It sends real Telegram messages.
- Admin command is `/vadman`, not `/admin` (the latter is intentionally ignored).
- `.env` is required; copy from `.env.example`. `BOT_TOKEN` and `ADMIN_ID` are mandatory.

## Gotchas

- `config.py` reads env at import time as module-level constants. Changing env after import won't take effect.
- Docker healthcheck queries SQLite directly at `/app/dbdata/bot.db` — don't change the DB path without updating `docker-compose.yml`.
- `bot.log` is gitignored but written to by the bot when running locally.
- `.mimocode/` is a separate tool's directory, gitignored — ignore it.
