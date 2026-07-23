from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..i18n import t
from ..keyboards import main_menu
from .. import database as db

router = Router()


@router.callback_query(F.data == "lang:toggle")
async def toggle_language(callback: CallbackQuery, user_lang: str):
    new_lang = "en" if user_lang == "ru" else "ru"
    await db.set_language(callback.from_user.id, new_lang)
    await callback.message.edit_text(
        t(new_lang, "welcome"),
        reply_markup=main_menu(new_lang),
    )
    await callback.answer(t(new_lang, "lang_changed"))
