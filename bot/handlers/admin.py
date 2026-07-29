import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from .. import database as db
from ..i18n import t
from ..keyboards import admin_menu
from .. import config

router = Router()
log = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


@router.message(F.text.in_({"/vadman", "/vadmin"}))
async def cmd_admin(message: Message, user_lang: str):
    log.info(f"[ADMIN] /vadman called by user_id={message.from_user.id}, expected={config.ADMIN_ID}, is_admin={_is_admin(message.from_user.id)}")
    if not _is_admin(message.from_user.id):
        await message.answer(t(user_lang, "admin_not_admin"))
        return
    try:
        await message.answer(t(user_lang, "admin_welcome"), reply_markup=admin_menu(user_lang))
        log.info("[ADMIN] admin_welcome sent successfully")
    except Exception as e:
        log.error(f"[ADMIN] Failed to send admin panel: {e}")


@router.callback_query(F.data.startswith("admin:"))
async def admin_handler(callback: CallbackQuery, user_lang: str):
    if not _is_admin(callback.from_user.id):
        await callback.answer(t(user_lang, "admin_not_admin"), show_alert=True)
        return

    action = callback.data.split(":")[1]

    if action == "stats":
        stats = await db.get_full_stats()
        await callback.message.edit_text(
            t(user_lang, "admin_stats",
               total=stats["total"],
               new_today=stats["new_today"],
               new_week=stats["new_week"],
               lang_ru=stats["lang_ru"],
               lang_en=stats["lang_en"],
               finance_subs=stats["finance_subs"],
               finance_tickers=stats["finance_tickers"],
               news_sent=stats["news_sent"],
            ),
            reply_markup=admin_menu(user_lang),
        )
        await callback.answer()

    elif action == "registrations":
        users = await db.get_all_users()
        if not users:
            table = "_(нет пользователей)_"
        else:
            lines = []
            for i, u in enumerate(users, 1):
                uname = f"@{u['username']}" if u["username"] else u["full_name"]
                until = (u.get("access_until") or "—")[:10]
                lines.append(f"<code>{i:2}</code>. <b>{u['user_id']}</b>  {uname}  [{u['language']}]  до {until}")
            table = "\n".join(lines)
        await callback.message.edit_text(
            t(user_lang, "admin_registrations", table=table, total=len(users)),
            reply_markup=admin_menu(user_lang),
            parse_mode="HTML",
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
