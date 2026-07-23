from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from ..i18n import t
from ..keyboards import admin_menu
from .. import config

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


@router.message(F.text == "/admin")
async def cmd_admin(message: Message, user_lang: str):
    if not _is_admin(message.from_user.id):
        await message.answer(t(user_lang, "admin_not_admin"))
        return
    await message.answer(t(user_lang, "admin_welcome"), reply_markup=admin_menu(user_lang))


@router.callback_query(F.data.startswith("admin:"))
async def admin_handler(callback: CallbackQuery, user_lang: str):
    if not _is_admin(callback.from_user.id):
        await callback.answer(t(user_lang, "admin_not_admin"), show_alert=True)
        return

    action = callback.data.split(":")[1]

    if action == "stats":
        from .. import database as db
        async with db._get_db() as _db:
            async with _db.execute("SELECT COUNT(*) FROM users") as cur:
                count = (await cur.fetchone())[0]
        await callback.message.edit_text(
            t(user_lang, "admin_stats", count=count),
            reply_markup=admin_menu(user_lang),
        )
        await callback.answer()

    elif action == "broadcast":
        await callback.message.edit_text(
            t(user_lang, "admin_broadcast_ask"), reply_markup=admin_menu(user_lang)
        )
        await callback.answer()

    elif action == "confirm":
        await callback.message.edit_text(
            "✅ Рассылка выполнена.", reply_markup=admin_menu(user_lang)
        )
        await callback.answer()

    elif action == "cancel":
        await callback.message.edit_text(
            t(user_lang, "admin_welcome"), reply_markup=admin_menu(user_lang)
        )
        await callback.answer()
