"""Finance news handler — subscriptions, monitoring, analysis."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..i18n import t
from ..keyboards import main_menu
from .. import database as db
from ..finance import (
    fetch_finance_news,
    analyze_with_gemini,
    format_finance_alert,
)
from ..database import is_news_sent, mark_news_sent

router = Router()

# ── /finance command ──

@router.message(F.text == "/finance")
async def cmd_finance(message: Message, user_lang: str):
    subs = await db.get_finance_subscriptions(message.from_user.id)
    if subs:
        ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
        text = t(user_lang, "finance_menu", tickers=ticker_list)
    else:
        text = t(user_lang, "finance_empty")
    await message.answer(text, reply_markup=finance_menu(user_lang), parse_mode="HTML")


# ── Finance menu callbacks ──

@router.callback_query(F.data.startswith("fin:"))
async def finance_handler(callback: CallbackQuery, user_lang: str):
    parts = callback.data.split(":")
    action = parts[1]

    if action == "list":
        subs = await db.get_finance_subscriptions(callback.from_user.id)
        if subs:
            ticker_list = "\n".join(f"• <code>{s['ticker']}</code> — {s['name'] or '—'}" for s in subs)
            text = t(user_lang, "finance_list", tickers=ticker_list)
        else:
            text = t(user_lang, "finance_empty")
        await callback.message.edit_text(text, reply_markup=finance_menu(user_lang), parse_mode="HTML")
        await callback.answer()

    elif action == "add":
        await callback.message.edit_text(t(user_lang, "finance_add_ask"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
        await callback.answer()

    elif action == "remove":
        subs = await db.get_finance_subscriptions(callback.from_user.id)
        if subs:
            kb = InlineKeyboardBuilder()
            for s in subs:
                kb.row(InlineKeyboardButton(text=f"❌ {s['ticker']}", callback_data=f"fin:del:{s['ticker']}"))
            kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="fin:list"))
            await callback.message.edit_text(t(user_lang, "finance_remove_ask"), reply_markup=kb.as_markup(), parse_mode="HTML")
        else:
            await callback.message.edit_text(t(user_lang, "finance_empty"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
        await callback.answer()

    elif action == "scan":
        await callback.answer()
        await callback.message.edit_text("🔄 Сканирую новости...", parse_mode="HTML")
        news = await fetch_finance_news()
        if not news:
            await callback.message.edit_text(t(user_lang, "finance_no_news"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
            return
        sent_count = 0
        for item in news[:5]:
            if await is_news_sent(item["title"]):
                continue
            user_tickers = await db.get_user_tickers(callback.from_user.id)
            analysis = await analyze_with_gemini(item["title"], item["summary"], user_tickers)
            alert = format_finance_alert(item["title"], item["summary"], item["source"], analysis, item["link"])
            try:
                await callback.message.answer(alert, disable_web_page_preview=True, parse_mode="HTML")
                await mark_news_sent(item["title"], item["source"])
                sent_count += 1
            except Exception:
                continue
        if sent_count == 0:
            await callback.message.edit_text(t(user_lang, "finance_all_seen"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
        else:
            await callback.message.edit_text(
                t(user_lang, "finance_scan_done", count=sent_count),
                reply_markup=finance_menu(user_lang),
                parse_mode="HTML",
            )

    elif action == "del" and len(parts) >= 3:
        ticker = parts[2]
        await db.remove_finance_subscription(callback.from_user.id, ticker)
        await callback.answer(f"❌ {ticker} удалён", show_alert=True)
        subs = await db.get_finance_subscriptions(callback.from_user.id)
        if subs:
            ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
            text = t(user_lang, "finance_menu", tickers=ticker_list)
        else:
            text = t(user_lang, "finance_empty")
        await callback.message.edit_text(text, reply_markup=finance_menu(user_lang), parse_mode="HTML")


# ── Receive ticker to add ──

@router.message(F.text)
async def finance_receive_ticker(message: Message, user_lang: str):
    text = message.text.strip().upper()

    # Skip commands
    if text.startswith("/"):
        return

    # Skip if it's a known non-ticker text
    if text in ("ДА", "НЕТ", "YES", "NO", "ОК", "OK"):
        return

    # Only process if it looks like a ticker (2-10 uppercase chars, no spaces)
    if len(text) > 10 or " " in text or len(text) < 2:
        await message.answer(
            t(user_lang, "finance_invalid_ticker"),
            reply_markup=finance_menu(user_lang),
            parse_mode="HTML",
        )
        return

    await db.add_finance_subscription(message.from_user.id, text, text)
    await message.answer(
        t(user_lang, "finance_added", ticker=text),
        reply_markup=finance_menu(user_lang),
        parse_mode="HTML",
    )


# ── Keyboard ──

def finance_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(lang, "fin_btn_scan"), callback_data="fin:scan"))
    kb.row(
        InlineKeyboardButton(text=t(lang, "fin_btn_list"), callback_data="fin:list"),
        InlineKeyboardButton(text=t(lang, "fin_btn_add"), callback_data="fin:add"),
    )
    kb.row(InlineKeyboardButton(text=t(lang, "fin_btn_remove"), callback_data="fin:remove"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main"))
    return kb.as_markup()
