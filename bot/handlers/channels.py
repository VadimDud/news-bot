"""Channel management handler — create, list, edit, delete, scan topic channels."""

import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..finance import fetch_news
from ..i18n import t
from ..keyboards import subscriber_menu
from .. import database as db
from .. import config
from ..news_processor import global_scan, format_channel_news
from ..sources import get_source_tags_display
from ..topic_analyzer import analyze_topic
from .start import _store_msg, _get_text_buttons

router = Router()

logger = logging.getLogger(__name__)

# Channel creation state machine: {user_id: {"step": ..., "name": ..., "keywords": ..., "ai_keywords": ..., "ticker": ..., "source_tags": [...]}}
_channel_state: dict[int, dict] = {}

# Channel edit state: {user_id: channel_id}
_channel_edit_state: dict[int, int] = {}


class _ChannelStateFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in _channel_state


class _ChannelEditFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in _channel_edit_state


def _channel_list_text(channels: list[dict], lang: str) -> str:
    if not channels:
        return t(lang, "channels_empty")

    lines = []
    for ch in channels:
        kw = ", ".join(ch["keywords"][:5])
        if len(ch["keywords"]) > 5:
            kw += f" (+{len(ch['keywords']) - 5})"
        ticker_line = f"🏷 <code>{ch['ticker']}</code>" if ch.get("ticker") else ""
        lines.append(t(lang, "channel_list_item", name=ch["name"], keywords=kw, ticker_line=ticker_line))

    return t(lang, "channels_menu", channels_list="\n\n".join(lines))


def _channels_menu_kb(lang: str, channels: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        ch_id = ch["id"]
        ticker_tag = f" 🏷{ch['ticker']}" if ch.get("ticker") else ""
        kb.row(InlineKeyboardButton(
            text=f"📡 {ch['name']}{ticker_tag}",
            callback_data=f"ch:view:{ch_id}",
        ))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_create_channel"), callback_data="ch:create"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main"))
    return kb.as_markup()


def _channel_detail_kb(lang: str, channel_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"🔍 {t(lang, 'fin_btn_scan')}", callback_data=f"ch:scan:{channel_id}"))
    kb.row(
        InlineKeyboardButton(text=f"✏️ {t(lang, 'btn_edit_keywords', default='Ключевые слова')}", callback_data=f"ch:edit_kw:{channel_id}"),
        InlineKeyboardButton(text=f"🤖 {t(lang, 'btn_ai_expand', default='AI расширить')}", callback_data=f"ch:ai_expand:{channel_id}"),
    )
    kb.row(InlineKeyboardButton(text=f"❌ {t(lang, 'btn_delete', default='Удалить')}", callback_data=f"ch:del:{channel_id}"))
    kb.row(InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="ch:list"))
    return kb.as_markup()


# ── /channels command ──

@router.message(F.text == "/channels")
async def cmd_channels(message: Message, user_lang: str):
    user_id = message.from_user.id
    if not await db.has_access(user_id):
        await message.answer(t(user_lang, "access_denied"), reply_markup=subscriber_menu(user_lang))
        return
    channels = await db.get_user_channels(user_id)
    text = _channel_list_text(channels, user_lang)
    kb = _channels_menu_kb(user_lang, channels)
    msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    _store_msg(user_id, msg.message_id)


# ── Channel list callback ──

@router.callback_query(F.data == "ch:list")
async def channel_list(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id)
    text = _channel_list_text(channels, user_lang)
    kb = _channels_menu_kb(user_lang, channels)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── Create channel flow ──

@router.callback_query(F.data == "ch:create")
async def channel_create_start(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    if not await db.has_access(user_id):
        await callback.message.edit_text(t(user_lang, "access_denied"), reply_markup=subscriber_menu(user_lang))
        await callback.answer()
        return
    _channel_state[user_id] = {"step": "name"}
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
    await callback.message.edit_text(t(user_lang, "channel_ask_name"), reply_markup=kb.as_markup())
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), _ChannelStateFilter())
async def channel_state_handler(message: Message, user_lang: str):
    user_id = message.from_user.id
    state = _channel_state.get(user_id)
    if not state:
        return

    if message.text in _get_text_buttons(user_lang) or message.text in _get_text_buttons("ru") or message.text in _get_text_buttons("en"):
        return

    step = state["step"]

    if step == "name":
        name = message.text.strip()
        if len(name) < 1 or len(name) > 50:
            return

        existing = await db.get_channel_by_name(user_id, name)
        if existing:
            await message.answer(t(user_lang, "channel_already_exists"))
            return

        state["name"] = name
        state["step"] = "keywords"
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
        await message.answer(t(user_lang, "channel_ask_keywords", name=name), reply_markup=kb.as_markup())

    elif step == "keywords":
        raw = message.text.strip()
        keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
        if len(keywords) < 1:
            return

        state["user_keywords"] = keywords
        state["step"] = "confirm_keywords"

        # Try AI expansion
        analysis = await analyze_topic(state["name"], keywords)

        if analysis and analysis.get("keywords"):
            ai_keywords = analysis["keywords"]
            related = analysis.get("related_tickers", [])
            related_str = ", ".join(f"<code>{t}</code>" for t in related[:5]) if related else "—"

            state["ai_keywords"] = ai_keywords
            state["ai_related_tickers"] = related

            text = t(user_lang, "channel_ai_expanded",
                     user_keywords=", ".join(keywords),
                     ai_keywords=", ".join(ai_keywords),
                     related_tickers=related_str)
            kb = InlineKeyboardBuilder()
            kb.row(
                InlineKeyboardButton(text=t(user_lang, "channel_ai_use_expanded"), callback_data="ch:use_ai"),
                InlineKeyboardButton(text=t(user_lang, "channel_ai_use_original"), callback_data="ch:use_original"),
            )
            kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
            await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        else:
            # No AI available, skip to ticker
            state["keywords"] = keywords
            state["step"] = "ticker"
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
            await message.answer(t(user_lang, "channel_ask_ticker", name=state["name"]), reply_markup=kb.as_markup())

    elif step == "ticker":
        raw = message.text.strip()
        ticker = None if raw in ("—", "-", "нет", "no", "skip") else raw.upper()
        state["ticker"] = ticker

        # Move to source_tags selection
        state["step"] = "source_tags"
        tags_display = get_source_tags_display(user_lang)
        tag_lines = []
        for tag_info in tags_display:
            tag_lines.append(f"• <b>{tag_info['name']}</b> ({tag_info['count']} источников) — <code>{tag_info['id']}</code>")
        text = (
            f"📡 <b>{state['name']}</b>\n\n"
            f"Выберите <b>категории источников</b> для сканирования.\n"
            f"Введите ID через запятую или <b>все</b> для всех источников:\n\n"
            + "\n".join(tag_lines)
        )
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🌐 Все источники", callback_data="ch:src_all"))
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

    elif step == "source_tags":
        raw = message.text.strip().lower()
        if raw in ("все", "all", "*"):
            source_tags = []
        else:
            valid_ids = {tag["id"] for tag in get_source_tags_display(user_lang)}
            source_tags = [t.strip() for t in raw.split(",") if t.strip() in valid_ids]
            if not source_tags:
                return

        name = state["name"]
        keywords = state["keywords"]
        ticker = state.get("ticker")

        channel_id = await db.create_channel(user_id, name, keywords, ticker, source_tags)
        if channel_id is None:
            await message.answer(t(user_lang, "channel_already_exists"))
            _channel_state.pop(user_id, None)
            return

        ticker_line = t(user_lang, "channel_created_with_ticker", ticker=ticker) if ticker else t(user_lang, "channel_created_no_ticker")
        src_text = ", ".join(source_tags) if source_tags else "все"
        text = (
            t(user_lang, "channel_created", name=name, keywords=", ".join(keywords), ticker_line=ticker_line)
            + f"\n\n📡 Источники: {src_text}"
        )

        _channel_state.pop(user_id, None)

        kb = _channel_detail_kb(user_lang, channel_id)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Source tags callbacks ──

@router.callback_query(F.data == "ch:src_all")
async def channel_select_all_sources(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    state = _channel_state.get(user_id)
    if not state or state.get("step") != "source_tags":
        await callback.answer("State expired", show_alert=True)
        return

    source_tags = []  # empty = all sources
    name = state["name"]
    keywords = state["keywords"]
    ticker = state.get("ticker")

    channel_id = await db.create_channel(user_id, name, keywords, ticker, source_tags)
    if channel_id is None:
        await callback.answer(t(user_lang, "channel_already_exists"), show_alert=True)
        _channel_state.pop(user_id, None)
        return

    _channel_state.pop(user_id, None)

    ticker_line = t(user_lang, "channel_created_with_ticker", ticker=ticker) if ticker else t(user_lang, "channel_created_no_ticker")
    text = (
        t(user_lang, "channel_created", name=name, keywords=", ".join(keywords), ticker_line=ticker_line)
        + "\n\n📡 Источники: все"
    )
    kb = _channel_detail_kb(user_lang, channel_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── View channel detail ──

@router.callback_query(F.data == "ch:use_ai")
async def channel_use_ai_keywords(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    state = _channel_state.get(user_id)
    if not state or state.get("step") != "confirm_keywords":
        await callback.answer("State expired", show_alert=True)
        return

    state["keywords"] = state["ai_keywords"]
    state["step"] = "ticker"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
    await callback.message.edit_text(
        t(user_lang, "channel_ask_ticker", name=state["name"]),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "ch:use_original")
async def channel_use_original_keywords(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    state = _channel_state.get(user_id)
    if not state or state.get("step") != "confirm_keywords":
        await callback.answer("State expired", show_alert=True)
        return

    state["keywords"] = state["user_keywords"]
    state["step"] = "ticker"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data="ch:list"))
    await callback.message.edit_text(
        t(user_lang, "channel_ask_ticker", name=state["name"]),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch:view:"))
async def channel_view(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    kw = ", ".join(ch["keywords"])
    ticker_line = f"\n🏷 Тикер: <code>{ch['ticker']}</code>" if ch.get("ticker") else ""

    source_tags = ch.get("source_tags", [])
    if source_tags:
        tags_display = get_source_tags_display(user_lang)
        tag_names = [t["name"] for t in tags_display if t["id"] in source_tags]
        src_line = f"\n📡 Источники: {', '.join(tag_names) if tag_names else ', '.join(source_tags)}"
    else:
        src_line = "\n📡 Источники: все"

    # Count news delivered
    recent_news = await db.get_channel_news_log(channel_id, limit=100)
    news_count = len(recent_news)

    text = (
        f"📡 <b>{ch['name']}</b>\n\n"
        f"🔑 Ключевые слова: {kw}"
        f"{ticker_line}"
        f"{src_line}\n\n"
        f"📊 Доставлено новостей: {news_count}"
    )
    kb = _channel_detail_kb(user_lang, channel_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── Delete channel ──

@router.callback_query(F.data.startswith("ch:del:"))
async def channel_delete_confirm(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    text = t(user_lang, "channel_delete_confirm", name=ch["name"])
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="❌ Да, удалить", callback_data=f"ch:del_yes:{channel_id}"),
        InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"),
    )
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("ch:del_yes:"))
async def channel_delete_yes(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    name = ch["name"]
    await db.delete_channel(channel_id)
    await db.remove_pinned_news_by_channel(channel_id)

    channels = await db.get_user_channels(callback.from_user.id)
    text = t(user_lang, "channel_deleted", name=name) + "\n\n" + _channel_list_text(channels, user_lang)
    kb = _channels_menu_kb(user_lang, channels)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── AI expand keywords for existing channel ──

@router.callback_query(F.data.startswith("ch:ai_expand:"))
async def channel_ai_expand(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(t(user_lang, "channel_ai_expanding", name=ch["name"]))

    analysis = await analyze_topic(ch["name"], ch["keywords"])

    if not analysis or not analysis.get("keywords"):
        kb = _channel_detail_kb(user_lang, channel_id)
        await callback.message.edit_text(
            t(user_lang, "channel_ai_no_expansion"),
            reply_markup=kb,
        )
        return

    ai_keywords = analysis["keywords"]
    related = analysis.get("related_tickers", [])
    related_str = ", ".join(f"<code>{t}</code>" for t in related[:5]) if related else "—"

    # Show suggestion with option to apply
    text = (
        f"🤖 <b>AI-предложение для «{ch['name']}»</b>\n\n"
        f"🔑 Текущие: {', '.join(ch['keywords'])}\n\n"
        f"🤖 Предложенные: {', '.join(ai_keywords)}\n\n"
        f"📊 Связанные тикеры: {related_str}"
    )
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=f"✅ Применить ({len(ai_keywords)} слов)", callback_data=f"ch:ai_apply:{channel_id}"),
    )
    kb.row(
        InlineKeyboardButton(text="📝 Добавить к текущим", callback_data=f"ch:ai_merge:{channel_id}"),
    )
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"))

    # Store AI suggestion in a temp dict
    if not hasattr(channel_ai_expand, '_ai_suggestions'):
        channel_ai_expand._ai_suggestions = {}
    channel_ai_expand._ai_suggestions[channel_id] = ai_keywords

    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("ch:ai_apply:"))
async def channel_ai_apply(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    suggestions = getattr(channel_ai_expand, '_ai_suggestions', {}).get(channel_id, [])
    if not suggestions:
        await callback.answer("Suggestion expired", show_alert=True)
        return

    await db.update_channel_keywords(channel_id, suggestions)
    getattr(channel_ai_expand, '_ai_suggestions', {}).pop(channel_id, None)

    kb = _channel_detail_kb(user_lang, channel_id)
    await callback.message.edit_text(
        f"✅ Ключевые слова обновлены для «{ch['name']}»\n\n"
        f"🔑 Новый набор: {', '.join(suggestions)}",
        reply_markup=kb, parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch:ai_merge:"))
async def channel_ai_merge(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    suggestions = getattr(channel_ai_expand, '_ai_suggestions', {}).get(channel_id, [])
    if not suggestions:
        await callback.answer("Suggestion expired", show_alert=True)
        return

    merged = list(dict.fromkeys(ch["keywords"] + suggestions))  # dedupe, preserve order
    await db.update_channel_keywords(channel_id, merged)
    getattr(channel_ai_expand, '_ai_suggestions', {}).pop(channel_id, None)

    kb = _channel_detail_kb(user_lang, channel_id)
    await callback.message.edit_text(
        f"✅ Ключевые слова объединены для «{ch['name']}»\n\n"
        f"🔑 Итого: {len(merged)} слов\n{', '.join(merged)}",
        reply_markup=kb, parse_mode="HTML",
    )
    await callback.answer()


# ── Edit keywords ──

@router.callback_query(F.data.startswith("ch:edit_kw:"))
async def channel_edit_keywords_start(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    _channel_edit_state[callback.from_user.id] = channel_id
    kw = ", ".join(ch["keywords"])
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"))
    await callback.message.edit_text(
        t(user_lang, "channel_edit_keywords", name=ch["name"], keywords=kw),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), _ChannelEditFilter())
async def channel_edit_keywords_save(message: Message, user_lang: str):
    user_id = message.from_user.id
    channel_id = _channel_edit_state.pop(user_id)
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != user_id:
        return

    raw = message.text.strip()
    keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
    if len(keywords) < 1:
        return

    await db.update_channel_keywords(channel_id, keywords)
    await message.answer(t(user_lang, "channel_keywords_updated", name=ch["name"]))

    kb = _channel_detail_kb(user_lang, channel_id)
    await message.answer(
        f"📡 <b>{ch['name']}</b>\n\n🔑 Новые ключевые слова: {', '.join(keywords)}",
        reply_markup=kb, parse_mode="HTML",
    )


# ── Scan single channel ──

@router.callback_query(F.data.startswith("ch:scan:"))
async def channel_scan(callback: CallbackQuery, user_lang: str):
    channel_id = int(callback.data.split(":")[2])
    ch = await db.get_channel(channel_id)
    if not ch or ch["user_id"] != callback.from_user.id:
        await callback.answer("Not found", show_alert=True)
        return

    await callback.answer()
    source_tags = ch.get("source_tags", [])
    await callback.message.edit_text(t(user_lang, "channel_scan_start", name=ch["name"]))

    async def _do_scan():
        news = await fetch_news(source_tags if source_tags else None)
        if not news:
            await callback.message.edit_text(
                t(user_lang, "channel_no_news"),
                reply_markup=_channel_detail_kb(user_lang, channel_id),
            )
            return

        results = await global_scan(news, [ch], skip_ai=True)
        matched = results.get(channel_id, [])

        new_items = []
        for item in matched:
            if not await db.is_channel_news_seen(channel_id, item["content_hash"]):
                new_items.append(item)

        if not new_items:
            await callback.message.edit_text(
                t(user_lang, "channel_no_news"),
                reply_markup=_channel_detail_kb(user_lang, channel_id),
            )
            return

        cn_items = []
        n_items = []
        dl_items = []
        for item in new_items:
            cn_items.append({
                "channel_id": channel_id,
                "content_hash": item["content_hash"],
                "matched_keyword": item.get("matched_keyword", ""),
                "ticker_hint": item.get("ticker_hint", ""),
                "impact": item["impact"],
            })
            n_items.append({
                "content_hash": item["content_hash"],
                "user_id": callback.from_user.id,
                "source": item["source"],
                "title": item["title"],
                "link": item.get("link", ""),
                "ticker_hint": item.get("ticker_hint", ""),
                "summary": item["summary"],
                "impact": item["impact"],
            })
            dl_items.append({
                "user_id": callback.from_user.id,
                "ticker_hint": item.get("ticker_hint", ""),
                "title": item["title"],
                "source": item["source"],
                "impact": item["impact"],
            })
        await db.save_channel_news_batch(cn_items)
        await db.save_news_batch(n_items)
        await db.log_news_delivery_batch(dl_items)

        messages = format_channel_news(ch["name"], new_items, user_lang)

        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"))

        for i, msg_text in enumerate(messages):
            rm = kb.as_markup() if i == len(messages) - 1 else None
            msg = await callback.message.answer(msg_text, reply_markup=rm, disable_web_page_preview=True)
            if i == 0:
                await db.save_pinned_news(callback.from_user.id, callback.message.chat.id, msg.message_id, channel_id)
            if i < len(messages) - 1:
                await asyncio.sleep(0.3)

    try:
        await asyncio.wait_for(_do_scan(), timeout=config.SCAN_TIMEOUT)
    except asyncio.TimeoutError:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"))
        await callback.message.edit_text(
            t(user_lang, "scan_timeout"),
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        logger.warning(f"Channel scan failed for channel {channel_id}: {e}")
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=t(user_lang, "btn_back"), callback_data=f"ch:view:{channel_id}"))
        try:
            await callback.message.edit_text(
                t(user_lang, "scan_timeout"),
                reply_markup=kb.as_markup(),
            )
        except Exception:
            pass


# ── Scan all channels ──

@router.callback_query(F.data == "ch:scan_all")
async def channel_scan_all(callback: CallbackQuery, user_lang: str):
    user_id = callback.from_user.id
    channels = await db.get_user_channels(user_id)
    if not channels:
        await callback.answer(t(user_lang, "channels_empty"), show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(t(user_lang, "channel_scan_all"))

    async def _do_scan_all():
        all_tags = set()
        for ch in channels:
            for tag in ch.get("source_tags", []):
                all_tags.add(tag)

        await callback.message.edit_text(t(user_lang, "scan_progress_rss"))
        news = await fetch_news(list(all_tags) if all_tags else None)
        if not news:
            await callback.message.edit_text(
                t(user_lang, "finance_no_news"),
                reply_markup=_channels_menu_kb(user_lang, channels),
            )
            return

        await callback.message.edit_text(
            t(user_lang, "scan_progress_analyze", count=len(news))
        )
        all_channels = await db.get_all_user_channels()
        results = await global_scan(news, all_channels)

        cn_items = []
        n_items = []
        dl_items = []
        for ch in channels:
            matched = results.get(ch["id"], [])
            for item in matched:
                if not await db.is_channel_news_seen(ch["id"], item["content_hash"]):
                    cn_items.append({
                        "channel_id": ch["id"],
                        "content_hash": item["content_hash"],
                        "matched_keyword": item.get("matched_keyword", ""),
                        "ticker_hint": item.get("ticker_hint", ""),
                        "impact": item["impact"],
                    })
                    n_items.append({
                        "content_hash": item["content_hash"],
                        "user_id": user_id,
                        "source": item["source"],
                        "title": item["title"],
                        "link": item.get("link", ""),
                        "ticker_hint": item.get("ticker_hint", ""),
                        "summary": item["summary"],
                        "impact": item["impact"],
                    })
                    dl_items.append({
                        "user_id": user_id,
                        "ticker_hint": item.get("ticker_hint", ""),
                        "title": item["title"],
                        "source": item["source"],
                        "impact": item["impact"],
                    })
        total_new = len(cn_items)
        if cn_items:
            await db.save_channel_news_batch(cn_items)
            await db.save_news_batch(n_items)
            await db.log_news_delivery_batch(dl_items)

        text = t(user_lang, "scan_progress_done", count=total_new)
        kb = _channels_menu_kb(user_lang, channels)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    try:
        await asyncio.wait_for(_do_scan_all(), timeout=config.SCAN_TIMEOUT)
    except asyncio.TimeoutError:
        kb = _channels_menu_kb(user_lang, channels)
        await callback.message.edit_text(
            t(user_lang, "scan_timeout"),
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"Channel scan all failed for user {user_id}: {e}")
        kb = _channels_menu_kb(user_lang, channels)
        try:
            await callback.message.edit_text(
                t(user_lang, "scan_timeout"),
                reply_markup=kb,
            )
        except Exception:
            pass
