"""Finance news handler — subscriptions, monitoring, analysis."""

import asyncio
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..asset_analyzer import analyze_ticker
from ..i18n import t
from ..keyboards import guest_menu, subscriber_menu
from .. import database as db
from .. import config
from ..finance import fetch_finance_news
from ..news_processor import (
    stage1_filter,
    compute_sentiment,
    stage2_hybrid,
    format_news_batch,
    compute_hash,
    _sentiment_cache_key,
    MAX_AI_CALLS_PER_SCAN,
)
from .start import _store_msg, _store_news_msg, _delete_old_news_msg, _get_msg_id, _feedback_state, _get_text_buttons

router = Router()

logger = logging.getLogger(__name__)


# ── /finance command ──

@router.message(F.text == "/finance")
async def cmd_finance(message: Message, user_lang: str):
    subs = await db.get_finance_subscriptions(message.from_user.id)
    if subs:
        ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
        text = t(user_lang, "finance_menu", tickers=ticker_list)
    else:
        text = t(user_lang, "finance_empty")
    msg = await message.answer(text, reply_markup=finance_menu(user_lang), parse_mode="HTML")
    _store_msg(message.from_user.id, msg.message_id)


# ── Finance menu callbacks ──

@router.callback_query(F.data.startswith("fin:"))
async def finance_handler(callback: CallbackQuery, user_lang: str):
    parts = callback.data.split(":")
    action = parts[1]

    # Skip inline add/del handlers (handled by start.py)
    if action in ("add", "del") and len(parts) >= 3:
        return

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
        user_id = callback.from_user.id

        async def _do_finance_scan():
            await callback.message.edit_text(t(user_lang, "scan_progress_rss"), parse_mode="HTML")

            tracked_assets = await db.get_all_tracked_assets()
            if not tracked_assets:
                await callback.message.edit_text(t(user_lang, "finance_empty"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
                return

            news = await fetch_finance_news()
            if not news:
                await callback.message.edit_text(t(user_lang, "finance_no_news"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
                return

            await callback.message.edit_text(
                t(user_lang, "scan_progress_analyze", count=min(len(news), 20)),
                parse_mode="HTML",
            )

            batch_items = []
            ai_calls_count = 0

            for item in news[:20]:
                title = item["title"]
                content_hash = compute_hash(title)

                if await db.is_news_seen(content_hash, user_id):
                    continue

                is_relevant, matched_ticker, matched_asset = stage1_filter(
                    title, item["summary"], tracked_assets
                )
                if not is_relevant:
                    continue

                impact, confidence = compute_sentiment(title, item["summary"], matched_asset)

                if (confidence == "low" or impact == "NEUTRAL"):
                    sent_cache_key = _sentiment_cache_key(
                        content_hash, matched_asset.get("ticker") if matched_asset else None
                    )
                    cached_sent = await db.get_ai_cache(sent_cache_key)
                    if cached_sent is not None and cached_sent in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                        impact = cached_sent
                    elif ai_calls_count < MAX_AI_CALLS_PER_SCAN:
                        ai_impact = await stage2_hybrid(
                            title, item["summary"], matched_asset, confidence,
                            content_hash=content_hash,
                        )
                        if ai_impact:
                            impact = ai_impact
                        ai_calls_count += 1

                summary = item["summary"][:200] if item["summary"] else title[:200]

                await db.save_news(
                    content_hash, user_id, item["source"], title, item.get("link", ""),
                    matched_ticker, summary, impact,
                )

                batch_items.append({
                    "title": title,
                    "source": item["source"],
                    "ticker": matched_ticker,
                    "summary": summary,
                    "impact": impact,
                    "link": item.get("link", ""),
                })

            if not batch_items:
                await callback.message.edit_text(t(user_lang, "finance_all_seen"), reply_markup=finance_menu(user_lang), parse_mode="HTML")
                return

            await _delete_old_news_msg(user_id, callback.message.chat.id, callback.bot)

            messages = format_news_batch(batch_items, user_lang)
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))

            last_msg = None
            for i, msg_text in enumerate(messages):
                rm = kb.as_markup() if i == len(messages) - 1 else None
                last_msg = await callback.message.answer(msg_text, reply_markup=rm, disable_web_page_preview=True)
                if i < len(messages) - 1:
                    await asyncio.sleep(0.3)
            if last_msg:
                _store_news_msg(user_id, last_msg.message_id)

        try:
            await asyncio.wait_for(_do_finance_scan(), timeout=config.SCAN_TIMEOUT)
        except asyncio.TimeoutError:
            await callback.message.edit_text(
                t(user_lang, "scan_timeout"),
                reply_markup=finance_menu(user_lang),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Finance scan failed for user {user_id}: {e}")
            try:
                await callback.message.edit_text(
                    t(user_lang, "scan_timeout"),
                    reply_markup=finance_menu(user_lang),
                    parse_mode="HTML",
                )
            except Exception:
                pass


# ── Receive ticker/company name to add (text input) ──

@router.message(F.text)
async def finance_receive_ticker(message: Message, user_lang: str):
    raw = message.text.strip()
    text = raw.upper()

    if text.startswith("/"):
        return

    if text in ("ДА", "НЕТ", "YES", "NO", "ОК", "OK"):
        return

    # Skip if user is in feedback mode
    if message.from_user.id in _feedback_state:
        return

    # Skip if text matches a menu button
    if raw in _get_text_buttons(user_lang) or raw in _get_text_buttons("ru") or raw in _get_text_buttons("en"):
        return

    # Accept both short tickers (2-10 chars) and longer company names (up to 50 chars)
    if len(raw) < 2 or len(raw) > 50:
        return

    # Use raw text for AI analysis (preserves case for company names like "ФосАгро")
    ticker_for_ai = raw if len(raw) > 10 else text

    # Check if already tracked globally
    already_tracked = await db.has_tracked_asset(text)

    await db.add_finance_subscription(message.from_user.id, text, raw)

    if not already_tracked:
        # Show analyzing message
        analyzing_msg = await message.answer(t(user_lang, "finance_analyzing", ticker=raw), parse_mode="HTML")

        analysis = await analyze_ticker(raw)

        if analysis:
            kw = analysis.get("keywords", [])
            meaningful_kw = [k for k in kw if k.upper() != text and len(k) > 2]

            await db.save_tracked_asset(
                ticker=text,
                name=analysis.get("company_name", raw),
                keywords=kw,
                positive_triggers=analysis.get("positive_triggers", []),
                negative_triggers=analysis.get("negative_triggers", []),
                description=analysis.get("description", ""),
            )

            if len(meaningful_kw) >= 3:
                result_text = t(user_lang, "finance_analysis_ok",
                    ticker=text, name=analysis.get("company_name", raw),
                    description=analysis.get("description", ""),
                    kw_count=len(kw), pos_count=len(analysis.get("positive_triggers", [])),
                    neg_count=len(analysis.get("negative_triggers", [])))
            else:
                result_text = t(user_lang, "finance_analysis_fallback", ticker=text)
        else:
            result_text = t(user_lang, "finance_analysis_fallback", ticker=text)

        # Update the analyzing message with result
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="sub:tickers"))
        try:
            await analyzing_msg.edit_text(result_text, reply_markup=kb.as_markup(), parse_mode="HTML")
        except Exception:
            pass
    else:
        old_id = _get_msg_id(message.from_user.id)
        result_text = t(user_lang, "finance_added", ticker=text)
        if old_id:
            try:
                await message.bot.edit_message_text(
                    result_text, chat_id=message.chat.id, message_id=old_id,
                    reply_markup=finance_menu(user_lang), parse_mode="HTML",
                )
                return
            except Exception:
                pass
        msg = await message.answer(result_text, reply_markup=finance_menu(user_lang), parse_mode="HTML")
        _store_msg(message.from_user.id, msg.message_id)


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
