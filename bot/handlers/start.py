from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from ..i18n import t
from ..keyboards import main_menu
from .. import database as db

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, user_lang: str):
    user = message.from_user
    await db.set_user(user.id, user.username, user.full_name, user_lang)
    await message.answer(t(user_lang, "welcome"), reply_markup=main_menu(user_lang))


@router.message(F.text == "/help")
async def cmd_help(message: Message, user_lang: str):
    await message.answer(t(user_lang, "help"), reply_markup=main_menu(user_lang))


@router.callback_query(F.data == "back:main")
async def back_main(callback: CallbackQuery, user_lang: str):
    await callback.message.edit_text(t(user_lang, "welcome"), reply_markup=main_menu(user_lang))
    await callback.answer()
