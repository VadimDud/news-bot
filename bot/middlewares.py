from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from . import database as db


class LanguageMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Any, Any], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        event_user = event.from_user
        if event_user:
            user_data = await db.get_user(event_user.id)
            if user_data:
                data["user_lang"] = user_data.get("language", "ru")
                until_str = user_data.get("access_until")
                if until_str:
                    import datetime
                    try:
                        data["is_subscriber"] = datetime.datetime.fromisoformat(until_str) > datetime.datetime.now()
                    except (ValueError, TypeError):
                        data["is_subscriber"] = False
                else:
                    data["is_subscriber"] = False
            else:
                data["user_lang"] = "ru"
                data["is_subscriber"] = False
        else:
            data["user_lang"] = "ru"
            data["is_subscriber"] = False
        return await handler(event, data)
