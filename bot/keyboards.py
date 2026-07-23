from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .i18n import t


def main_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "btn_finance"), callback_data="fin:list"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_lang"), callback_data="lang:toggle"))
    return kb.as_markup()


def admin_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "btn_stats"), callback_data="admin:stats"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_broadcast"), callback_data="admin:broadcast"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main"))
    return kb.as_markup()
