from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from .i18n import t


# ── Guest menu (inline) ──

def guest_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "btn_about"), callback_data="menu:about"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_buy"), callback_data="menu:buy"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_trial"), callback_data="menu:trial"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_support"), callback_data="menu:support"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_lang"), callback_data="lang:toggle"))
    return kb.as_markup()


# ── Subscriber menu (inline) ──

def subscriber_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "sub_btn_news"), callback_data="sub:news"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_my_channels"), callback_data="ch:list"))
    kb.row(InlineKeyboardButton(text=t(lang, "sub_btn_tickers"), callback_data="sub:tickers"))
    kb.row(
        InlineKeyboardButton(text=t(lang, "sub_btn_settings"), callback_data="sub:settings"),
        InlineKeyboardButton(text=t(lang, "sub_btn_profile"), callback_data="sub:profile"),
    )
    kb.row(InlineKeyboardButton(text=t(lang, "sub_btn_feedback"), callback_data="sub:feedback"))
    return kb.as_markup()


# ── Subscriber inline helpers ──

def ticker_filter_menu(lang: str, tickers: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ticker in tickers:
        kb.row(InlineKeyboardButton(text=f"📌 {ticker}", callback_data=f"filter:{ticker}"))
    kb.row(InlineKeyboardButton(text=t(lang, "sub_btn_news"), callback_data="filter:all"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:home"))
    return kb.as_markup()


def settings_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "settings_notify"), callback_data="settings:notify"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:home"))
    return kb.as_markup()


# ── Admin menu ──

def admin_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "btn_stats"), callback_data="admin:stats"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_registrations"), callback_data="admin:registrations"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_broadcast"), callback_data="admin:broadcast"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main"))
    return kb.as_markup()


# ── Reply keyboards (persistent keyboard at the bottom) ──

def guest_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=t(lang, "btn_about")))
    kb.row(KeyboardButton(text=t(lang, "btn_buy")))
    kb.row(KeyboardButton(text=t(lang, "btn_trial")))
    kb.row(KeyboardButton(text=t(lang, "btn_support")))
    kb.row(KeyboardButton(text=t(lang, "btn_lang")))
    return kb.as_markup(resize_keyboard=True)


def subscriber_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=t(lang, "sub_btn_news")))
    kb.row(KeyboardButton(text=t(lang, "sub_btn_tickers")))
    kb.row(
        KeyboardButton(text=t(lang, "sub_btn_settings")),
        KeyboardButton(text=t(lang, "sub_btn_profile")),
    )
    kb.row(KeyboardButton(text=t(lang, "sub_btn_feedback")))
    return kb.as_markup(resize_keyboard=True)


def remove_reply_keyboard() -> ReplyKeyboardMarkup:
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()
