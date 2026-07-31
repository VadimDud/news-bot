"""Web interface for the Tech News Bot.

Standalone aiohttp server that lets users enter feed configuration
(name, keywords, ticker, source categories, topics) from a browser
instead of typing it in Telegram.

Run:
    python web_app.py

The Telegram connection/auth is not wired up yet: the user enters their
Telegram user_id manually. Replace it with the Telegram Login Widget when
connecting the web interface to the bot.
"""

import asyncio
import html
import logging
import sys
from pathlib import Path
from string import Template

from aiohttp import web

from bot import config
from bot import database as db
from bot.sources import get_source_tags_display
from bot.topics import get_topics_display

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "web" / "templates"


def _read_template(name: str) -> Template:
    return Template((_TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def _page(title: str, content: str) -> web.Response:
    base = _read_template("base.html")
    body = base.substitute(title=html.escape(title), content=content)
    return web.Response(text=body, content_type="text/html", charset="utf-8")


def _esc(value) -> str:
    return html.escape(str(value))


async def _require_user(request: web.Request) -> tuple[int | None, str | None]:
    """Resolve and authorize the user, returning (user_id, error_text)."""
    raw = request.query.get("user_id", "").strip()
    try:
        user_id = int(raw)
    except (TypeError, ValueError):
        return None, "Укажите корректный Telegram ID (число)."
    user = await db.get_user(user_id)
    if user is None:
        return None, "Вы не зарегистрированы в боте. Отправьте /start боту в Telegram и повторите попытку."
    if not await db.has_access(user_id):
        return user_id, "Доступ ещё не активирован. Нажмите «Попробовать бесплатно» в боте."
    return user_id, None


def _error_page(error: str) -> web.Response:
    content = (
        f'<div class="card"><div class="notice error">{_esc(error)}</div>'
        f'<a class="btn" href="/">Вернуться на главную</a></div>'
    )
    return _page("Ошибка", content)


def _parse_channel_form(data) -> dict:
    name = data.get("name", "").strip()
    keywords = [kw.strip() for kw in data.get("keywords", "").split(",") if kw.strip()]
    ticker = data.get("ticker", "").strip()
    valid_tags = {tag["id"] for tag in get_source_tags_display()}
    source_tags = [t for t in data.getall("source_tags", []) if t in valid_tags]
    valid_topics = {info["id"] for info in get_topics_display()}
    topics = [t for t in data.getall("topics", []) if t in valid_topics]
    return {
        "name": name,
        "keywords": keywords,
        "ticker": ticker,
        "source_tags": source_tags,
        "topics": topics,
    }


def _validate_channel_form(values: dict) -> list[str]:
    errors = []
    if not values["name"] or len(values["name"]) > 50:
        errors.append("Название ленты должно содержать от 1 до 50 символов.")
    if not values["keywords"]:
        errors.append("Укажите хотя бы одно ключевое слово.")
    return errors


def _source_tags_display() -> list[dict]:
    return get_source_tags_display()


def _topics_display() -> list[dict]:
    return get_topics_display()


def _channel_card(ch: dict, user_id: int) -> str:
    kw = ", ".join(ch["keywords"])
    lines = []
    if ch.get("ticker"):
        lines.append(f'<div class="meta">Тикер: <code>{_esc(ch["ticker"])}</code></div>')
    if ch.get("source_tags"):
        names = [t["name"] for t in _source_tags_display() if t["id"] in ch["source_tags"]]
        lines.append(f'<div class="meta">Источники: {_esc(", ".join(names) or ", ".join(ch["source_tags"]))}</div>')
    else:
        lines.append('<div class="meta">Источники: все</div>')
    if ch.get("topics"):
        names = [t["name"] for t in _topics_display() if t["id"] in ch["topics"]]
        lines.append(f'<div class="meta">Тематики: {_esc(", ".join(names) or ", ".join(ch["topics"]))}</div>')
    else:
        lines.append('<div class="meta">Тематики: не выбраны (автоопределение)</div>')
    card = _read_template("channel_card.html").substitute(
        name=_esc(ch["name"]),
        keywords=_esc(kw),
        meta="\n".join(lines),
        id=ch["id"],
        user_id=user_id,
    )
    return card


def _channel_form_page(user_id: int, values: dict, action: str, title: str,
                       error: str | None = None) -> web.Response:
    selected_tags = set(values.get("source_tags", []))
    selected_topics = set(values.get("topics", []))
    source_options = "\n".join(
        f'<label><input type="checkbox" name="source_tags" value="{t["id"]}"'
        f'{" checked" if t["id"] in selected_tags else ""}> {_esc(t["name"])}</label>'
        for t in _source_tags_display()
    )
    topic_options = "\n".join(
        f'<label><input type="checkbox" name="topics" value="{t["id"]}"'
        f'{" checked" if t["id"] in selected_topics else ""}> {_esc(t["name"])}</label>'
        for t in _topics_display()
    )
    notice = f'<div class="notice error">{_esc(error)}</div>' if error else ""
    content = _read_template("channel_form.html").substitute(
        notice=notice,
        form_title=_esc(title),
        form_action=action,
        user_id=user_id,
        name=_esc(values.get("name", "")),
        keywords=_esc(", ".join(values.get("keywords", []))),
        ticker=_esc(values.get("ticker", "")),
        source_options=source_options,
        topic_options=topic_options,
    )
    return _page(title, content)


# ── Routes ──

async def index(request: web.Request) -> web.Response:
    content = _read_template("index.html").substitute()
    return _page("Вход — Tech News Bot", content)


async def channels(request: web.Request) -> web.Response:
    user_id, error = await _require_user(request)
    if error:
        return _error_page(error)
    chans = await db.get_user_channels(user_id)
    if chans:
        channels_list = "\n".join(_channel_card(ch, user_id) for ch in chans)
    else:
        channels_list = '<div class="card"><div class="empty">У вас пока нет лент. Создайте первую!</div></div>'
    content = _read_template("channels.html").substitute(
        user_id=user_id,
        channels_list=channels_list,
    )
    return _page("Мои ленты", content)


async def channel_new(request: web.Request) -> web.Response:
    user_id, error = await _require_user(request)
    if error:
        return _error_page(error)
    return _channel_form_page(user_id, {}, action="/channels", title="Создание ленты")


async def channel_create(request: web.Request) -> web.Response:
    data = await request.post()
    try:
        user_id = int(data.get("user_id", "").strip())
    except (TypeError, ValueError):
        return _error_page("Укажите корректный Telegram ID (число).")
    if not await db.has_access(user_id):
        return _error_page("Доступ ещё не активирован.")

    values = _parse_channel_form(data)
    errors = _validate_channel_form(values)
    if errors:
        return _channel_form_page(
            user_id, values, action="/channels",
            title="Создание ленты", error=" ".join(errors),
        )
    ticker = values["ticker"].upper() if values["ticker"] else None
    channel_id = await db.create_channel(
        user_id, values["name"], values["keywords"],
        ticker, values["source_tags"], values["topics"],
    )
    if channel_id is None:
        return _channel_form_page(
            user_id, values, action="/channels",
            title="Создание ленты",
            error="Лента с таким названием уже существует.",
        )
    raise web.HTTPFound(f"/channels?user_id={user_id}")


async def channel_edit(request: web.Request) -> web.Response:
    user_id, error = await _require_user(request)
    if error:
        return _error_page(error)
    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page("Лента не найдена.")
    values = {
        "name": ch["name"],
        "keywords": ch["keywords"],
        "ticker": ch.get("ticker") or "",
        "source_tags": ch.get("source_tags") or [],
        "topics": ch.get("topics") or [],
    }
    return _channel_form_page(
        user_id, values, action=f"/channels/{channel_id}",
        title="Редактирование ленты",
    )


async def channel_update(request: web.Request) -> web.Response:
    data = await request.post()
    try:
        user_id = int(data.get("user_id", "").strip())
    except (TypeError, ValueError):
        return _error_page("Укажите корректный Telegram ID (число).")
    if not await db.has_access(user_id):
        return _error_page("Доступ ещё не активирован.")

    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page("Лента не найдена.")

    values = _parse_channel_form(data)
    errors = _validate_channel_form(values)
    if errors:
        return _channel_form_page(
            user_id, values, action=f"/channels/{channel_id}",
            title="Редактирование ленты", error=" ".join(errors),
        )

    ticker = values["ticker"].upper() if values["ticker"] else None
    try:
        await db.update_channel_name(channel_id, values["name"])
        await db.update_channel_keywords(channel_id, values["keywords"])
        await db.update_channel_ticker(channel_id, ticker)
        await db.update_channel_source_tags(channel_id, values["source_tags"])
        await db.update_channel_topics(channel_id, values["topics"])
    except db.aiosqlite.IntegrityError:
        return _channel_form_page(
            user_id, values, action=f"/channels/{channel_id}",
            title="Редактирование ленты",
            error="Лента с таким названием уже существует.",
        )
    raise web.HTTPFound(f"/channels?user_id={user_id}")


async def channel_delete(request: web.Request) -> web.Response:
    data = await request.post()
    try:
        user_id = int(data.get("user_id", "").strip())
    except (TypeError, ValueError):
        return _error_page("Укажите корректный Telegram ID (число).")

    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page("Лента не найдена.")
    await db.delete_channel(channel_id)
    await db.remove_pinned_news_by_channel(channel_id)
    raise web.HTTPFound(f"/channels?user_id={user_id}")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/channels", channels)
    app.router.add_get("/channels/new", channel_new)
    app.router.add_post("/channels", channel_create)
    app.router.add_get("/channels/{channel_id}/edit", channel_edit)
    app.router.add_post("/channels/{channel_id}", channel_update)
    app.router.add_post("/channels/{channel_id}/delete", channel_delete)
    return app


async def main():
    await db.init_db()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEB_HOST, config.WEB_PORT)
    await site.start()
    logger.info(f"Web interface running at http://{config.WEB_HOST}:{config.WEB_PORT}")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
