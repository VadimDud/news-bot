from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..i18n import t
from ..keyboards import guest_menu, subscriber_menu
from .. import database as db

router = Router()


@router.callback_query(F.data == "lang:toggle")
async def toggle_language(callback: CallbackQuery, user_lang: str):
    new_lang = "en" if user_lang == "ru" else "ru"
    await db.set_language(callback.from_user.id, new_lang)
    if await db.has_access(callback.from_user.id):
        text = t(new_lang, "welcome_sub")
        reply_markup = subscriber_menu(new_lang)
    else:
        text = t(new_lang, "welcome_guest")
        reply_markup = guest_menu(new_lang)
    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer(t(new_lang, "lang_changed"))
