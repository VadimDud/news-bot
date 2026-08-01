"""Web interface for the Tech News Bot.

aiohttp + Jinja2 (autoescaping) + HTMX + Alpine.js.

Auth:
  * Primary: Telegram Login Widget. The widget posts user data to
    ``/auth/telegram``, the server verifies the payload hash against the bot
    token and stores a signed session cookie.
  * Fallback: manual Telegram ID entry (``/auth/manual``) for non-HTTPS
    deployments where the widget cannot render.
  * The Telegram Login Widget only renders on HTTPS or localhost. Set
    ``BOT_USERNAME`` in ``.env`` to enable it.

Run:
    python web_app.py
"""

import asyncio
import hashlib
import hmac
import json
import logging
import sys
import time
from pathlib import Path

import aiohttp_jinja2
import jinja2
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

_USER_KEY = web.RequestKey("user_id", int)

# ── Session cookies ───────────────────────────────────────────────────────────

COOKIE_NAME = "tnb_uid"
COOKIE_MAX_AGE = 30 * 24 * 3600
TELEGRAM_AUTH_MAX_AGE = 86400  # allow Telegram auth payloads up to 24h old


def _cookie_secret() -> bytes:
    secret = config.WEB_COOKIE_SECRET or config.BOT_TOKEN
    if not secret:
        raise RuntimeError("BOT_TOKEN (or WEB_COOKIE_SECRET) is required for web auth")
    return secret.encode()


def _sign_user(user_id: int) -> str:
    payload = str(user_id)
    sig = hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_user(value: str) -> int | None:
    try:
        payload, sig = value.rsplit(".", 1)
        expected = hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return int(payload)
    except (ValueError, TypeError):
        return None


def _current_user(request: web.Request) -> int | None:
    value = request.cookies.get(COOKIE_NAME)
    return _verify_user(value) if value else None


def _set_user_cookie(request: web.Request, resp: web.StreamResponse, user_id: int) -> None:
    resp.set_cookie(
        COOKIE_NAME,
        _sign_user(user_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=config.WEB_COOKIE_SECURE or request.secure,
    )


# ── Telegram Login Widget verification ────────────────────────────────────────

def _verify_telegram_auth(data: dict) -> int | None:
    """Verify the Telegram Login Widget payload and return the user_id."""
    received_hash = data.pop("hash", "")
    auth_date = data.get("auth_date", "")
    if not received_hash or not auth_date:
        return None
    try:
        auth_date_int = int(auth_date)
    except (TypeError, ValueError):
        return None
    if abs(time.time() - auth_date_int) > TELEGRAM_AUTH_MAX_AGE:
        return None
    # Telegram docs: sort all fields except hash as key=value, join with \n
    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret = hashlib.sha256(_cookie_secret()).digest()
    digest = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, received_hash):
        return None
    try:
        return int(data["id"])
    except (KeyError, TypeError, ValueError):
        return None


async def _check_registration(user_id: int) -> str | None:
    """Return an error message if the user cannot use the web interface."""
    user = await db.get_user(user_id)
    if user is None:
        return "Вы не зарегистрированы в боте. Отправьте /start боту в Telegram и повторите попытку."
    if not await db.has_access(user_id):
        return "Доступ ещё не активирован. Нажмите «Попробовать бесплатно» в боте."
    return None


# ── Auth helpers ──────────────────────────────────────────────────────────────

class _AuthError(Exception):
    def __init__(self, message: str):
        self.message = message


async def _require_user(request: web.Request) -> int:
    user_id = _current_user(request)
    if user_id is None:
        raise web.HTTPFound("/")
    error = await _check_registration(user_id)
    if error:
        raise _AuthError(error)
    return user_id


_PUBLIC_PATHS = {"/", "/auth/telegram", "/auth/manual", "/logout"}


@web.middleware
async def _auth_middleware(request: web.Request, handler) -> web.StreamResponse:
    if request.path in _PUBLIC_PATHS:
        return await handler(request)
    try:
        request[_USER_KEY] = await _require_user(request)
    except _AuthError as exc:
        return _error_page(request, exc.message)
    return await handler(request)


# ── Template helpers ──────────────────────────────────────────────────────────

def _source_names(ids, sep: str = ", ") -> str:
    names = [t["name"] for t in get_source_tags_display() if t["id"] in ids]
    return sep.join(names) or sep.join(str(i) for i in ids)


def _topic_names(ids, sep: str = ", ") -> str:
    names = [t["name"] for t in get_topics_display() if t["id"] in ids]
    return sep.join(names) or sep.join(str(i) for i in ids)


def _error_page(request: web.Request, error: str) -> web.Response:
    return aiohttp_jinja2.render_template(
        "error.html", request, {"error": error}
    )


# ── Form parsing / validation ─────────────────────────────────────────────────

def _empty_form() -> dict:
    return {
        "name": "",
        "keywords": [],
        "ticker": "",
        "source_tags": [],
        "topics": [],
    }


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


def _channel_from_db(ch: dict) -> dict:
    return {
        "name": ch["name"],
        "keywords": ch["keywords"],
        "ticker": ch.get("ticker") or "",
        "source_tags": ch.get("source_tags") or [],
        "topics": ch.get("topics") or [],
    }


def _channel_form_page(request: web.Request, user_id: int, values: dict,
                       action: str, title: str,
                       error: str | None = None) -> web.Response:
    ctx = {
        "user_id": user_id,
        "form": values,
        "form_action": action,
        "form_title": title,
        "notice": error or "",
        "source_tags": get_source_tags_display(),
        "topics": get_topics_display(),
    }
    return aiohttp_jinja2.render_template("channel_form.html", request, ctx)


# ── Routes ────────────────────────────────────────────────────────────────────

async def index(request: web.Request) -> web.Response:
    if _current_user(request) is not None:
        raise web.HTTPFound("/channels")
    return aiohttp_jinja2.render_template(
        "index.html", request, {"bot_username": config.BOT_USERNAME}
    )


async def auth_telegram(request: web.Request) -> web.Response:
    try:
        data = dict(await request.json())
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "Неверный запрос"}, status=400)
    user_id = _verify_telegram_auth(data)
    if user_id is None:
        return web.json_response(
            {"ok": False, "error": "Не удалось проверить вход Telegram"}, status=400
        )
    error = await _check_registration(user_id)
    if error:
        return web.json_response({"ok": False, "error": error}, status=403)
    resp = web.json_response({"ok": True})
    _set_user_cookie(request, resp, user_id)
    return resp


async def auth_manual(request: web.Request) -> web.Response:
    data = await request.post()
    try:
        user_id = int(data.get("user_id", "").strip())
    except (TypeError, ValueError):
        return _error_page(request, "Укажите корректный Telegram ID (число).")
    error = await _check_registration(user_id)
    if error:
        return _error_page(request, error)
    resp = web.HTTPFound("/channels")
    _set_user_cookie(request, resp, user_id)
    raise resp


async def logout(request: web.Request) -> web.Response:
    resp = web.HTTPFound("/")
    resp.del_cookie(COOKIE_NAME)
    raise resp


async def channels(request: web.Request) -> web.Response:
    user_id = request[_USER_KEY]
    chans = await db.get_user_channels(user_id)
    return aiohttp_jinja2.render_template(
        "channels.html", request, {"user_id": user_id, "channels": chans}
    )


async def channel_new(request: web.Request) -> web.Response:
    return _channel_form_page(
        request, request[_USER_KEY], _empty_form(), action="/channels", title="Создание ленты"
    )


async def channel_create(request: web.Request) -> web.Response:
    user_id = request[_USER_KEY]
    data = await request.post()
    values = _parse_channel_form(data)
    errors = _validate_channel_form(values)
    if errors:
        return _channel_form_page(
            request, user_id, values, action="/channels",
            title="Создание ленты", error=" ".join(errors),
        )
    ticker = values["ticker"].upper() if values["ticker"] else None
    channel_id = await db.create_channel(
        user_id, values["name"], values["keywords"],
        ticker, values["source_tags"], values["topics"],
    )
    if channel_id is None:
        return _channel_form_page(
            request, user_id, values, action="/channels",
            title="Создание ленты", error="Лента с таким названием уже существует.",
        )
    raise web.HTTPFound("/channels")


async def channel_edit(request: web.Request) -> web.Response:
    user_id = request[_USER_KEY]
    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page(request, "Лента не найдена.")
    return _channel_form_page(
        request, user_id, _channel_from_db(ch), action=f"/channels/{channel_id}",
        title="Редактирование ленты",
    )


async def channel_update(request: web.Request) -> web.Response:
    user_id = request[_USER_KEY]
    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page(request, "Лента не найдена.")

    data = await request.post()
    values = _parse_channel_form(data)
    errors = _validate_channel_form(values)
    if errors:
        return _channel_form_page(
            request, user_id, values, action=f"/channels/{channel_id}",
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
            request, user_id, values, action=f"/channels/{channel_id}",
            title="Редактирование ленты",
            error="Лента с таким названием уже существует.",
        )
    raise web.HTTPFound("/channels")


async def channel_delete(request: web.Request) -> web.Response:
    user_id = request[_USER_KEY]
    channel_id = int(request.match_info["channel_id"])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return _error_page(request, "Лента не найдена.")
    await db.delete_channel(channel_id)
    await db.remove_pinned_news_by_channel(channel_id)
    if request.headers.get("HX-Request"):
        return web.Response(headers={"HX-Redirect": "/channels"})
    raise web.HTTPFound("/channels")


def create_app() -> web.Application:
    app = web.Application(middlewares=[_auth_middleware])
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
        filters={"source_names": _source_names, "topic_names": _topic_names},
    )
    app.router.add_get("/", index)
    app.router.add_post("/auth/telegram", auth_telegram)
    app.router.add_post("/auth/manual", auth_manual)
    app.router.add_post("/logout", logout)
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
