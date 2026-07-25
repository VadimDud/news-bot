from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from . import database as db


class LanguageMiddleware(BaseMiddleware):
    """Attach user's language preference and subscription status to every event."""

    async def __call__(
        self,
        handler: Callable[[Any, Any], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user:
            lang = await db.get_language(user.id)
            data["user_lang"] = lang
            data["is_subscriber"] = await db.has_access(user.id)
        else:
            data["user_lang"] = "ru"
            data["is_subscriber"] = False
        return await handler(event, data)
