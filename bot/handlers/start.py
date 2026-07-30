import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..i18n import t, STRINGS
from ..keyboards import (
    guest_menu, subscriber_menu, guest_reply_keyboard, subscriber_reply_keyboard,
    settings_menu,
)
from .. import database as db
from ..asset_analyzer import analyze_ticker
from .. import config
from ..config import ADMIN_ID
from ..finance import fetch_finance_news
from ..news_processor import (
    stage1_filter, compute_sentiment, stage2_hybrid,
    format_news_batch, compute_hash, compute_importance_score,
    _normalize, MAX_AI_CALLS_PER_SCAN,
)

router = Router()

logger = logging.getLogger(__name__)

TRIAL_DAYS = 30

# Per-user tracking: {user_id: message_id} for single-window mode
_user_messages: dict[int, int] = {}
# Per-user news message tracking: {user_id: message_id} — separate for news deletion
_user_news_messages: dict[int, int] = {}

# Users currently in feedback input mode: {user_id: user_lang}
_feedback_state: dict[int, str] = {}


class _FeedbackModeFilter(BaseFilter):
    """Only match messages from users in feedback mode."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in _feedback_state


def _store_msg(user_id: int, msg_id: int):
    _user_messages[user_id] = msg_id


def _get_msg_id(user_id: int) -> int | None:
    return _user_messages.get(user_id)


def _store_news_msg(user_id: int, msg_id: int):
    _user_news_messages[user_id] = msg_id


def _get_news_msg_id(user_id: int) -> int | None:
    return _user_news_messages.get(user_id)


async def _delete_old_news_msg(user_id: int, chat_id: int, bot):
    """Delete previous news message if exists."""
    old_id = _get_news_msg_id(user_id)
    if old_id:
        try:
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass
        _user_news_messages.pop(user_id, None)


async def _show_home(target, user_lang: str):
    """Show the appropriate menu based on user access."""
    if isinstance(target, Message):
        user_id = target.from_user.id
    else:
        user_id = target.from_user.id

    if await db.has_access(user_id):
        text = t(user_lang, "welcome_sub")
        reply_markup = subscriber_menu(user_lang)
    else:
        text = t(user_lang, "welcome_guest")
        reply_markup = guest_menu(user_lang)

    await _send_or_edit(target, user_id, text, reply_markup=reply_markup)


async def _send_or_edit(target, user_id: int, text: str, reply_markup=None, **kwargs) -> Message:
    """Send new message or edit existing one for single-window mode."""
    old_id = _get_msg_id(user_id)
    if old_id and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=reply_markup, **kwargs)
            return target.message
        except Exception:
            pass
    if isinstance(target, Message):
        msg = await target.answer(text, reply_markup=reply_markup, **kwargs)
    else:
        msg = await target.message.answer(text, reply_markup=reply_markup, **kwargs)
    _store_msg(user_id, msg.message_id)
    return msg


@router.message(F.text == "/start")
async def cmd_start(message: Message, user_lang: str):
    user = message.from_user
    await db.set_user(user.id, user.username, user.full_name, user_lang)

    if not await db.has_access(user.id):
        granted = await db.grant_trial(user.id, days=TRIAL_DAYS)
        if granted:
            info = await db.get_access_info(user.id)
            msg = await message.answer(
                t(user_lang, "trial_activated", days=info["days_left"], until=info["until"]),
                reply_markup=subscriber_menu(user_lang),
            )
            _store_msg(user.id, msg.message_id)
            return

    await _show_home(message, user_lang)


@router.message(F.text == "/help")
async def cmd_help(message: Message, user_lang: str):
    if await db.has_access(message.from_user.id):
        msg = await message.answer(t(user_lang, "help"), reply_markup=subscriber_menu(user_lang))
    else:
        msg = await message.answer(t(user_lang, "help"), reply_markup=guest_menu(user_lang))
    _store_msg(message.from_user.id, msg.message_id)


# ── Guest callbacks ──

@router.callback_query(F.data == "menu:about")
async def menu_about(callback: CallbackQuery, user_lang: str):
    await callback.message.edit_text(t(user_lang, "about_text"), reply_markup=guest_menu(user_lang))
    await callback.answer()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery, user_lang: str):
    await callback.message.edit_text(t(user_lang, "buy_text"), reply_markup=guest_menu(user_lang))
    await callback.answer()


@router.callback_query(F.data == "menu:trial")
async def menu_trial(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    granted = await db.grant_trial(user_id, days=TRIAL_DAYS)
    if granted:
        info = await db.get_access_info(user_id)
        await callback.message.edit_text(
            t(user_lang, "trial_activated", days=info["days_left"], until=info["until"]),
            reply_markup=subscriber_menu(user_lang),
        )
    else:
        await callback.message.edit_text(
            t(user_lang, "trial_already_used"),
            reply_markup=guest_menu(user_lang),
        )
    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery, user_lang: str):
    await callback.message.edit_text(t(user_lang, "support_text"), reply_markup=guest_menu(user_lang))
    await callback.answer()


# ── Subscriber callbacks ──

@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, user_lang: str):
    if await db.has_access(callback.from_user.id):
        await callback.message.edit_text(t(user_lang, "welcome_sub"), reply_markup=subscriber_menu(user_lang))
    else:
        await callback.message.edit_text(t(user_lang, "welcome_guest"), reply_markup=guest_menu(user_lang))
    await callback.answer()


@router.callback_query(F.data == "back:main")
async def back_main(callback: CallbackQuery, user_lang: str):
    _feedback_state.pop(callback.from_user.id, None)
    if await db.has_access(callback.from_user.id):
        await callback.message.edit_text(t(user_lang, "welcome_sub"), reply_markup=subscriber_menu(user_lang))
    else:
        await callback.message.edit_text(t(user_lang, "welcome_guest"), reply_markup=guest_menu(user_lang))
    await callback.answer()


# ── News scanning (keyword-based, batch in one message) ──

async def _scan_and_show_news(target, user_id: int, user_lang: str):
    """Core news scan logic: filter by tracked_assets keywords, show batch in one message."""

    tracked_assets = await db.get_all_tracked_assets()
    if not tracked_assets:
        text = t(user_lang, "finance_empty") if user_lang == "ru" else "💰 <b>Financial Analysis</b>\n\nAdd a ticker first to track news."
        await _send_or_edit(target, user_id, text, reply_markup=subscriber_menu(user_lang))
        return

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(t(user_lang, "scan_progress_rss"), parse_mode="HTML")
    else:
        pass

    news = await fetch_finance_news()
    if not news:
        await _send_or_edit(target, user_id, t(user_lang, "finance_no_news"), reply_markup=subscriber_menu(user_lang))
        return

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(
            t(user_lang, "scan_progress_analyze", count=min(len(news), 20)),
            parse_mode="HTML",
        )

    # Get news summary from buffer
    summary_info = await db.get_news_summary(user_id)
    buffer_hashes = await db.get_all_news_buffer_hashes()

    batch_items = []
    ai_calls_count = 0
    max_sub_count = 1
    try:
        max_sub_count = await db.get_max_ticker_subscriber_count()
    except Exception:
        pass

    for item in news[:20]:
        title = item["title"]
        content_hash = compute_hash(title)

        if content_hash in buffer_hashes:
            continue

        if await db.is_news_seen(content_hash, user_id):
            continue

        is_relevant, matched_ticker, matched_asset = stage1_filter(
            title, item["summary"], tracked_assets
        )
        if not is_relevant:
            continue

        impact, confidence = compute_sentiment(title, item["summary"], matched_asset)

        pos_triggers = matched_asset.get("positive_triggers", []) if matched_asset else []
        neg_triggers = matched_asset.get("negative_triggers", []) if matched_asset else []
        combined = _normalize(title + " " + item.get("summary", ""))
        pos_count = sum(1 for t in pos_triggers if _normalize(t) in combined) if pos_triggers else 0
        neg_count = sum(1 for t in neg_triggers if _normalize(t) in combined) if neg_triggers else 0

        if (confidence == "low" or impact == "NEUTRAL") and ai_calls_count < MAX_AI_CALLS_PER_SCAN:
            ai_impact = await stage2_hybrid(title, item["summary"], matched_asset, confidence)
            if ai_impact:
                impact = ai_impact
            ai_calls_count += 1

        summary = item["summary"][:200] if item["summary"] else title[:200]

        sub_count = 0
        if matched_ticker:
            try:
                sub_count = await db.get_subscriber_count_for_ticker(matched_ticker)
            except Exception:
                pass

        importance_score = compute_importance_score(
            title=title,
            summary=summary,
            sentiment=impact,
            confidence=confidence,
            pos_count=pos_count,
            neg_count=neg_count,
            match_count=1,
            subscriber_count=sub_count,
            max_subscriber_count=max_sub_count,
        )

        await db.save_news(
            content_hash, item["source"], title, item.get("link", ""),
            matched_ticker, summary, impact,
        )

        await db.upsert_news_buffer(
            content_hash=content_hash,
            source=item.get("source", ""),
            title=title,
            url=item.get("link", ""),
            summary=summary,
            importance_score=importance_score,
            match_count=1,
            is_used=1,
        )

        await db.upsert_user_news_priority(
            user_id=user_id,
            content_hash=content_hash,
            ticker=matched_ticker,
            importance_score=importance_score,
        )

        if matched_ticker:
            sc = await db.get_subscriber_count_for_ticker(matched_ticker)
            await db.upsert_news_ticker_popularity(
                content_hash=content_hash,
                ticker=matched_ticker,
                subscriber_count=sc,
            )

        batch_items.append({
            "title": title,
            "source": item["source"],
            "ticker": matched_ticker,
            "summary": summary,
            "impact": impact,
            "link": item.get("link", ""),
            "importance_score": importance_score,
        })

    chat_id = target.message.chat.id if isinstance(target, CallbackQuery) else target.chat.id
    bot_instance = target.message.bot if isinstance(target, CallbackQuery) else target.bot
    try:
        await _delete_old_news_msg(user_id, chat_id, bot_instance)
    except Exception:
        pass

    # Refresh summary after new additions
    summary_info = await db.get_news_summary(user_id)

    if not batch_items and summary_info.get("total", 0) == 0:
        await _send_or_edit(target, user_id, t(user_lang, "finance_all_seen"), reply_markup=subscriber_menu(user_lang))
        return

    if batch_items:
        messages = format_news_batch(batch_items, user_lang)
    else:
        messages = []

    if not messages and summary_info.get("total", 0) > 0:
        cached = await db.get_news_for_user(user_id, limit=10, min_score=0.0)
        if cached:
            messages = format_news_batch([
                {
                    "title": c["title"],
                    "source": c["source"],
                    "ticker": c.get("ticker", ""),
                    "summary": c["summary"][:200],
                    "impact": "POSITIVE" if c.get("importance_score", 0.5) >= 0.5 else "NEUTRAL",
                    "link": c.get("url", ""),
                    "importance_score": c.get("importance_score", 0.5),
                }
                for c in cached
            ], user_lang)

    summary_line = ""

    kb = InlineKeyboardBuilder()
    news_count = summary_info.get("total", 0)
    unread_count = summary_info.get("unread", 0)
    if news_count > 0:
        summary_line = (
            f"📊 <b>Всего новостей:</b> {news_count}"
            f"{f'  ({unread_count} новых)' if unread_count > 0 else ''}\n\n"
        )
        kb.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="sub:news"),
        )
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
    reply_markup = kb.as_markup()

    last_msg = None
    for i, msg_text in enumerate(messages):
        rm = reply_markup if i == len(messages) - 1 else None
        final_text = summary_line + msg_text if i == 0 else msg_text
        if isinstance(target, CallbackQuery):
            last_msg = await target.message.answer(final_text, reply_markup=rm, disable_web_page_preview=True)
        else:
            last_msg = await target.answer(final_text, reply_markup=rm, disable_web_page_preview=True)
        if i < len(messages) - 1:
            await asyncio.sleep(0.3)
    if last_msg:
        _store_news_msg(user_id, last_msg.message_id)


@router.callback_query(F.data == "sub:news")
async def sub_news(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
        await callback.answer()
        return
    await callback.answer()
    await callback.message.edit_text("🔄 Сканирую новости...", parse_mode="HTML")
    try:
        await asyncio.wait_for(_scan_and_show_news(callback, user_id, user_lang), timeout=config.SCAN_TIMEOUT)
    except asyncio.TimeoutError:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
        await callback.message.edit_text(t(user_lang, "scan_timeout"), reply_markup=kb.as_markup())
    except Exception as e:
        logger.warning(f"News scan failed for user {user_id}: {e}")
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
        try:
            await callback.message.edit_text(t(user_lang, "scan_timeout"), reply_markup=kb.as_markup())
        except Exception:
            pass


# ── Subscriber menu callbacks ──

@router.callback_query(F.data == "sub:tickers")
async def sub_tickers(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
        await callback.answer()
        return
    subs = await db.get_finance_subscriptions(user_id)
    if subs:
        ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
        text = t(user_lang, "finance_menu", tickers=ticker_list)
    else:
        text = t(user_lang, "finance_empty")
    await callback.message.edit_text(text, reply_markup=_ticker_management_kb(user_lang, subs), parse_mode="HTML")
    await callback.answer()


def _ticker_management_kb(lang: str, subs: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    subscribed_tickers = {s["ticker"] for s in subs}
    common_tickers = ["SBER", "GAZP", "LKOH", "ROSN", "YDEX", "VTB", "TCS", "GMKN", "NLMK", "ALRS"]
    for ticker in common_tickers:
        is_sub = ticker in subscribed_tickers
        prefix = "✅" if is_sub else "➕"
        action = f"fin:del:{ticker}" if is_sub else f"fin:add:{ticker}"
        kb.row(InlineKeyboardButton(text=f"{prefix} {ticker}", callback_data=action))
    custom_subs = [s for s in subs if s["ticker"] not in common_tickers]
    if custom_subs:
        for s in custom_subs:
            kb.row(InlineKeyboardButton(text=f"❌ {s['ticker']}", callback_data=f"fin:del:{s['ticker']}"))
    add_text = "✏️ Добавить свой" if lang == "ru" else "✏️ Add custom"
    kb.row(InlineKeyboardButton(text=add_text, callback_data="fin:add"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main"))
    return kb.as_markup()


async def _do_analyze_and_add(callback: CallbackQuery, user_lang: str, ticker: str, user_id: int):
    """Core logic: analyze ticker via Gemini, save, show feedback with retry option."""
    already_tracked = await db.has_tracked_asset(ticker)

    if not already_tracked:
        await callback.answer()
        await callback.message.edit_text(t(user_lang, "finance_analyzing", ticker=ticker), parse_mode="HTML")

        analysis = await analyze_ticker(ticker)

        if analysis:
            # Check if keywords are meaningful (more than just the ticker itself)
            kw = analysis.get("keywords", [])
            meaningful_kw = [k for k in kw if k.upper() != ticker.upper() and len(k) > 2]

            await db.save_tracked_asset(
                ticker=ticker,
                name=analysis.get("company_name", ticker),
                keywords=kw,
                positive_triggers=analysis.get("positive_triggers", []),
                negative_triggers=analysis.get("negative_triggers", []),
                description=analysis.get("description", ""),
            )

            if len(meaningful_kw) >= 3:
                # Good analysis
                info_text = t(user_lang, "finance_analysis_ok",
                    ticker=ticker, name=analysis.get("company_name", ticker),
                    description=analysis.get("description", ""),
                    kw_count=len(kw), pos_count=len(analysis.get("positive_triggers", [])),
                    neg_count=len(analysis.get("negative_triggers", [])))
            else:
                # AI responded but keywords are too generic
                info_text = t(user_lang, "finance_analysis_fallback", ticker=ticker)
        else:
            # AI failed completely
            info_text = t(user_lang, "finance_analysis_fallback", ticker=ticker)
    else:
        info_text = t(user_lang, "finance_added", ticker=ticker)
        await callback.answer(f"✅ {ticker}", show_alert=False)

    # Show feedback, then menu after short delay
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="sub:tickers"))
    await callback.message.edit_text(info_text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "fin:add")
async def ticker_add_prompt(callback: CallbackQuery, user_lang: str):
    """Show instruction when user clicks 'Add' button without a specific ticker."""
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
        await callback.answer()
        return
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="sub:tickers"))
    await callback.message.edit_text(t(user_lang, "finance_add_ask"), reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("fin:add:"))
async def ticker_add(callback: CallbackQuery, user_lang: str):
    """Add ticker via inline button — calls Gemini once for keyword analysis."""
    ticker = callback.data.split(":")[2]
    user_id = callback.from_user.id

    await db.add_finance_subscription(user_id, ticker, ticker)
    await _do_analyze_and_add(callback, user_lang, ticker, user_id)


@router.callback_query(F.data.startswith("fin:del:"))
async def ticker_del(callback: CallbackQuery, user_lang: str):
    ticker = callback.data.split(":")[2]
    await db.remove_finance_subscription(callback.from_user.id, ticker)
    await callback.answer(f"❌ {ticker} удалён", show_alert=False)
    subs = await db.get_finance_subscriptions(callback.from_user.id)
    if subs:
        ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
        text = t(user_lang, "finance_menu", tickers=ticker_list)
    else:
        text = t(user_lang, "finance_empty")
    await callback.message.edit_text(text, reply_markup=_ticker_management_kb(user_lang, subs), parse_mode="HTML")


@router.callback_query(F.data == "sub:settings")
async def sub_settings(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
        await callback.answer()
        return
    await callback.message.edit_text(t(user_lang, "settings_text"), reply_markup=settings_menu(user_lang))
    await callback.answer()


@router.callback_query(F.data == "sub:profile")
async def sub_profile(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    username = callback.from_user.full_name or callback.from_user.username or "—"
    info = await db.get_access_info(user_id)
    if info["has_access"]:
        text = t(user_lang, "profile_text",
                 user_id=user_id, username=username,
                 status="✅ Активна" if user_lang == "ru" else "✅ Active",
                 until=info["until"], days=info["days_left"])
    else:
        text = t(user_lang, "profile_no_access", user_id=user_id, username=username)
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


# ── Feedback ──

@router.callback_query(F.data == "sub:feedback")
async def sub_feedback(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
        await callback.answer()
        return
    _feedback_state[user_id] = user_lang
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
    await callback.message.edit_text(t(user_lang, "feedback_ask"), reply_markup=kb.as_markup())
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), _FeedbackModeFilter())
async def feedback_capture(message: Message, user_lang: str):
    """Capture feedback text from users in feedback mode."""
    user_id = message.from_user.id
    lang = _feedback_state.pop(user_id)
    fb_lang = lang

    user = message.from_user
    username = user.full_name or user.username or "—"
    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'

    admin_text = (
        "💬 <b>Новая обратная связь</b>\n\n"
        f"👤 Пользователь: {user_link}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🌐 Язык: {fb_lang}\n\n"
        f"📝 <b>Сообщение:</b>\n{message.text}"
    )

    try:
        await message.bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception:
        pass

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(fb_lang, "btn_back"), callback_data="back:main"))
    await message.answer(t(fb_lang, "feedback_sent"), reply_markup=kb.as_markup())


# ── Reply keyboard text handlers (общие обработчики текстовых кнопок) ──

def _get_text_buttons(lang: str) -> dict[str, str]:
    """Map button text to its corresponding callback data action."""
    s = STRINGS.get(lang, STRINGS.get("ru", {}))
    return {
        s["sub_btn_news"]: "sub:news",
        s["btn_my_channels"]: "ch:list",
        s["sub_btn_tickers"]: "sub:tickers",
        s["sub_btn_settings"]: "sub:settings",
        s["sub_btn_profile"]: "sub:profile",
        s["sub_btn_feedback"]: "sub:feedback",
        s["btn_about"]: "menu:about",
        s["btn_buy"]: "menu:buy",
        s["btn_trial"]: "menu:trial",
        s["btn_support"]: "menu:support",
        s["btn_lang"]: "lang:toggle",
        s["btn_back"]: "back:main",
    }


@router.message(F.text.in_(set(_get_text_buttons("ru").keys()) | set(_get_text_buttons("en").keys())))
async def text_button_handler(message: Message, user_lang: str):
    buttons = _get_text_buttons(user_lang)
    action = buttons.get(message.text)
    if not action:
        action = _get_text_buttons("ru").get(message.text)
    if not action:
        action = _get_text_buttons("en").get(message.text)
    if not action:
        return

    user_id = message.from_user.id

    # Route to appropriate handler
    if action == "sub:news":
        if not await db.has_access(user_id):
            await message.answer(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
            return
        await message.answer(t(user_lang, "scan_progress_rss"), parse_mode="HTML")
        try:
            await asyncio.wait_for(_scan_and_show_news(message, user_id, user_lang), timeout=config.SCAN_TIMEOUT)
        except asyncio.TimeoutError:
            await message.answer(t(user_lang, "scan_timeout"))
        except Exception as e:
            logger.warning(f"News scan failed for user {user_id}: {e}")
            try:
                await message.answer(t(user_lang, "scan_timeout"))
            except Exception:
                pass

    elif action == "ch:list":
        if not await db.has_access(user_id):
            await message.answer(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
            return
        channels = await db.get_user_channels(user_id)
        from .channels import _channel_list_text, _channels_menu_kb
        text = _channel_list_text(channels, user_lang)
        kb = _channels_menu_kb(user_lang, channels)
        msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        _store_msg(user_id, msg.message_id)

    elif action == "sub:tickers":
        if not await db.has_access(user_id):
            await message.answer(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
            return
        subs = await db.get_finance_subscriptions(user_id)
        if subs:
            ticker_list = ", ".join(f"<code>{s['ticker']}</code>" for s in subs)
            text = t(user_lang, "finance_menu", tickers=ticker_list)
        else:
            text = t(user_lang, "finance_empty")
        msg = await message.answer(text, reply_markup=_ticker_management_kb(user_lang, subs), parse_mode="HTML")
        _store_msg(user_id, msg.message_id)

    elif action == "sub:settings":
        if not await db.has_access(user_id):
            await message.answer(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
            return
        msg = await message.answer(t(user_lang, "settings_text"), reply_markup=settings_menu(user_lang))
        _store_msg(user_id, msg.message_id)

    elif action == "sub:profile":
        username = message.from_user.full_name or message.from_user.username or "—"
        info = await db.get_access_info(user_id)
        if info["has_access"]:
            text = t(user_lang, "profile_text",
                     user_id=user_id, username=username,
                     status="✅ Активна" if user_lang == "ru" else "✅ Active",
                     until=info["until"], days=info["days_left"])
        else:
            text = t(user_lang, "profile_no_access", user_id=user_id, username=username)
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
        msg = await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        _store_msg(user_id, msg.message_id)

    elif action == "sub:feedback":
        if not await db.has_access(user_id):
            await message.answer(t(user_lang, "access_denied"), reply_markup=guest_menu(user_lang))
            return
        _feedback_state[user_id] = user_lang
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="back:main"))
        msg = await message.answer(t(user_lang, "feedback_ask"), reply_markup=kb.as_markup())
        _store_msg(user_id, msg.message_id)

    elif action == "menu:about":
        msg = await message.answer(t(user_lang, "about_text"), reply_markup=guest_menu(user_lang))
        _store_msg(user_id, msg.message_id)

    elif action == "menu:buy":
        msg = await message.answer(t(user_lang, "buy_text"), reply_markup=guest_menu(user_lang))
        _store_msg(user_id, msg.message_id)

    elif action == "menu:trial":
        granted = await db.grant_trial(user_id, days=TRIAL_DAYS)
        if granted:
            info = await db.get_access_info(user_id)
            msg = await message.answer(
                t(user_lang, "trial_activated", days=info["days_left"], until=info["until"]),
                reply_markup=subscriber_menu(user_lang),
            )
        else:
            msg = await message.answer(
                t(user_lang, "trial_already_used"),
                reply_markup=guest_menu(user_lang),
            )
        _store_msg(user_id, msg.message_id)

    elif action == "menu:support":
        msg = await message.answer(t(user_lang, "support_text"), reply_markup=guest_menu(user_lang))
        _store_msg(user_id, msg.message_id)

    elif action == "lang:toggle":
        new_lang = "en" if user_lang == "ru" else "ru"
        await db.set_language(user_id, new_lang)
        await _show_home(message, new_lang)

    elif action == "back:main":
        _feedback_state.pop(user_id, None)
        await _show_home(message, user_lang)
