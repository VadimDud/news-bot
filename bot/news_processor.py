"""4-stage news processing pipeline (universal channels):

   1. Quick Python filter: keywords from user_channels table (0 tokens)
   2. Sentiment by trigger counting (0 tokens) — hybrid AI for ambiguous cases
   3. Global dedup (MinHash)
   4. Distribution to matched channels
"""

import hashlib
import logging
import re
import struct

from . import config
from .ai_client import analyze
from .database import get_tracked_asset

logger = logging.getLogger(__name__)


# ── MinHash / dedup ──

def _shingle(text: str, n: int = 3):
    for i in range(len(text) - n + 1):
        yield text[i:i+n]


def compute_minhash(text: str) -> list:
    text = text.lower().strip()
    seeds = [b'\x01', b'\x02', b'\x03', b'\x04']
    max_hash = (1 << 64) - 1
    min_hashes = [max_hash] * 4
    for shingle in _shingle(text):
        for i, seed in enumerate(seeds):
            h = hashlib.sha256(seed + shingle.encode()).digest()[:8]
            val = struct.unpack('>Q', h)[0]
            if val < min_hashes[i]:
                min_hashes[i] = val
    if min_hashes[0] == max_hash:
        return [0] * 4
    return min_hashes


def compute_hash(text: str) -> str:
    sig = compute_minhash(text)
    return ''.join(f'{i:016x}' for i in sig)


def is_similar(hash1: str, hash2: str, threshold: float = 0.75) -> bool:
    sig1 = [int(hash1[i:i+16], 16) for i in range(0, 64, 16)]
    sig2 = [int(hash2[i:i+16], 16) for i in range(0, 64, 16)]
    equal = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return (equal / 4.0) >= threshold


# ── Text helpers ──

def _normalize(text: str) -> str:
    return text.lower().strip()


def _simple_stem(word: str) -> str:
    word = word.lower()
    for ending in ("ого", "ему", "ать", "ить", "еть", "ятся", "ются", "тся",
                    "ий", "ый", "ой", "ая", "яя", "ое", "ее", "ов", "ев",
                    "ам", "ям", "ах", "ях", "ов", "ев", "ах", "ях"):
        if len(word) > len(ending) + 3 and word.endswith(ending):
            return word[:-len(ending)]
    return word


# ── Stage 1: keyword matching against user channels ──

def match_news_to_channels(
    title: str,
    summary: str,
    all_channels: list[dict],
) -> list[dict]:
    """Check a single news item against all user channels.

    Returns list of matches: [{channel_id, user_id, language, ticker, matched_keyword}]
    """
    combined = _normalize(title + " " + summary)
    combined_stems = {_simple_stem(combined)}
    matches = []

    for ch in all_channels:
        keywords = ch.get("keywords", [])
        for kw in keywords:
            kw_lower = _normalize(kw)
            if len(kw_lower) < 2:
                continue
            if kw_lower in combined or _simple_stem(kw_lower) in combined_stems:
                matches.append({
                    "channel_id": ch["id"],
                    "user_id": ch["user_id"],
                    "language": ch.get("language", "ru"),
                    "ticker": ch.get("ticker"),
                    "matched_keyword": kw,
                })
                break  # one match per channel is enough

    return matches


def stage1_filter(title: str, summary: str, tracked_assets: list[dict]) -> tuple[bool, str | None, dict | None]:
    """Legacy filter against tracked_assets (kept for backward compat).

    Returns (is_relevant, matched_ticker_or_None, matched_asset_or_None).
    """
    combined = _normalize(title + " " + summary)
    combined_stems = {_simple_stem(combined)}

    for asset in tracked_assets:
        keywords = asset.get("keywords", [])
        ticker = asset["ticker"]
        for kw in keywords:
            kw_lower = _normalize(kw)
            if len(kw_lower) < 2:
                continue
            if kw_lower in combined or _simple_stem(kw_lower) in combined_stems:
                return True, ticker, asset

    return False, None, None


# ── Stage 2: sentiment analysis ──

def compute_sentiment(title: str, summary: str, asset: dict | None = None,
                      positive_triggers: list[str] | None = None,
                      negative_triggers: list[str] | None = None) -> tuple[str, str]:
    """Compute sentiment by counting positive/negative triggers in text.

    Returns (sentiment, confidence) where confidence is 'high' or 'low'.
    """
    combined = _normalize(title + " " + summary)

    pos_triggers = positive_triggers or (asset.get("positive_triggers", []) if asset else [])
    neg_triggers = negative_triggers or (asset.get("negative_triggers", []) if asset else [])

    pos_count = sum(1 for t in pos_triggers if _normalize(t) in combined)
    neg_count = sum(1 for t in neg_triggers if _normalize(t) in combined)

    if pos_count > neg_count:
        sentiment = "POSITIVE"
        confidence = "high" if pos_count >= 3 and neg_count == 0 else "low"
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
        confidence = "high" if neg_count >= 3 and pos_count == 0 else "low"
    else:
        sentiment = "NEUTRAL"
        confidence = "low"

    return sentiment, confidence


async def stage2_hybrid(title: str, summary: str, asset: dict | None = None,
                        positive_triggers: list[str] | None = None,
                        negative_triggers: list[str] | None = None,
                        trigger_confidence: str = "low",
                        ai_timeout: int = 10) -> str | None:
    combined = _normalize(title + " " + summary)
    pos_triggers = positive_triggers or (asset.get("positive_triggers", []) if asset else [])
    neg_triggers = negative_triggers or (asset.get("negative_triggers", []) if asset else [])

    pos_count = sum(1 for t in pos_triggers if _normalize(t) in combined)
    neg_count = sum(1 for t in neg_triggers if _normalize(t) in combined)

    should_call_ai = (
        (pos_count > 0 and neg_count > 0)
        or trigger_confidence == "low"
        or (pos_count == 0 and neg_count == 0)
    )

    if not should_call_ai:
        return None

    label = asset.get("name", asset["ticker"]) if asset else "тема"
    system_prompt = "Ты финансовый аналитик. Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. Ответь одним словом."
    user_message = (
        f"Новость: {title}\nСуть: {summary[:200]}\n\n"
        f"Актив/тема: {label}\n\n"
        f"Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. "
        f"Ответь одним словом."
    )
    result = await analyze(system_prompt, user_message, parse_json=False,
                           temperature=0.1, max_tokens=10, timeout=ai_timeout)
    if result:
        text = result.strip().upper()
        if text in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            return text
    return None


# ── Global scan: process all news against all channels ──

async def global_scan(
    news_items: list[dict],
    all_channels: list[dict],
) -> dict[int, list[dict]]:
    """Process all news against all user channels.

    Returns {channel_id: [matched_news_item_with_sentiment]}.
    Each matched item: {title, source, link, summary, impact, matched_keyword, ticker_hint}
    """
    if not all_channels:
        return {}

    results: dict[int, list[dict]] = {}

    for item in news_items[:20]:
        title = item["title"]
        summary = item.get("summary", "")
        content_hash = compute_hash(title)

        matches = match_news_to_channels(title, summary, all_channels)
        if not matches:
            continue

        # Compute sentiment once per news item (use first match's triggers as hint)
        first_channel = next(
            (ch for ch in all_channels if ch["id"] == matches[0]["channel_id"]),
            None,
        )
        pos_triggers = []
        neg_triggers = []
        asset = None
        if first_channel and first_channel.get("ticker"):
            asset = await get_tracked_asset(first_channel["ticker"])
            if asset:
                pos_triggers = asset.get("positive_triggers", [])
                neg_triggers = asset.get("negative_triggers", [])

        sentiment, confidence = compute_sentiment(title, summary, asset, pos_triggers, neg_triggers)
        if confidence == "low" or sentiment == "NEUTRAL":
            ai_sentiment = await stage2_hybrid(
                title, summary, asset, pos_triggers, neg_triggers, confidence
            )
            if ai_sentiment:
                sentiment = ai_sentiment

        impact = sentiment

        for match in matches:
            ch_id = match["channel_id"]
            if ch_id not in results:
                results[ch_id] = []
            results[ch_id].append({
                "title": title,
                "source": item.get("source", ""),
                "link": item.get("link", ""),
                "summary": (summary or title)[:200],
                "impact": impact,
                "matched_keyword": match["matched_keyword"],
                "ticker_hint": match.get("ticker") or "",
                "content_hash": content_hash,
            })

    return results


# ── Formatting ──

def split_news_text(text: str, max_len: int = 4000) -> list[str]:
    if not text:
        return []
    items = re.split(r'(?=\d+\.\s)', text)
    items = [item for item in items if item]
    chunks = []
    current = ""
    for item in items:
        if not current:
            current = item
        elif len(current) + len(item) <= max_len:
            current += item
        else:
            chunks.append(current)
            current = item
    if current:
        chunks.append(current)
    return chunks


import datetime


def _format_items(items: list[dict], lang: str, header_prefix: str,
                  ticker_key: str = "ticker",
                  extra_keys: tuple = ()) -> list[str]:
    if not items:
        return []

    now = datetime.datetime.now().strftime("%H:%M")
    emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}
    disclaimer_ru = "\n\n⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    disclaimer_en = "\n\n⚠️ <i>Not an individual investment recommendation.</i>"
    disclaimer = disclaimer_ru if lang == "ru" else disclaimer_en
    parts = []

    for i, item in enumerate(items, 1):
        impact_emoji = emoji.get(item["impact"], "🟡")
        extra = ""
        for key in extra_keys:
            val = item.get(key)
            if val:
                extra += f"  🔑 {val}"
        ticker_val = item.get(ticker_key)
        ticker_info = f"  🏷 <code>{ticker_val}</code>" if ticker_val else ""
        block = (
            f"<b>{i}. {item['title']}</b>\n"
            f"📡 {item['source']}{ticker_info}{extra}\n"
            f"📌 {item['summary']}\n"
            f"{impact_emoji} {item['impact']}"
        )
        if item.get("link"):
            link_text = "Подробнее" if lang == "ru" else "Read more"
            block += f'\n🔗 <a href="{item["link"]}">{link_text}</a>'
        parts.append(block)

    if lang == "ru":
        header = f"📰 <b>{header_prefix}</b> ({len(items)} шт.)"
        header += " — обновлено " if "Новости" in header_prefix else " — "
        header += f"{now}\n{'─' * 20}\n\n"
    else:
        header = f"📰 <b>{header_prefix}</b> ({len(items)} items)"
        header += " — updated " if "News" in header_prefix else " — "
        header += f"{now}\n{'─' * 20}\n\n"

    full_text = header + "\n\n".join(parts) + disclaimer
    chunks = split_news_text(full_text, max_len=4000)

    if len(chunks) > 1:
        chunks[-1] += disclaimer
        chunks = [c.replace(disclaimer, "") for c in chunks[:-1]] + [chunks[-1]]

    return chunks if chunks else [full_text]


def format_news_batch(items: list[dict], lang: str = "ru") -> list[str]:
    return _format_items(items, lang, "Новости" if lang == "ru" else "News",
                         ticker_key="ticker")


def format_channel_news(channel_name: str, items: list[dict], lang: str = "ru") -> list[str]:
    return _format_items(items, lang, channel_name,
                         ticker_key="ticker_hint",
                         extra_keys=("matched_keyword",))


def format_news_alert(title: str, source: str, analysis: dict, link: str) -> str:
    emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}
    impact_emoji = emoji.get(analysis["impact"], "🟡")
    msg = (
        f"🔔 <b>ФИНАНСОВАЯ НОВОСТЬ</b>\n"
        f"📰 {title}\n"
        f"📡 Источник: {source}\n"
        f"🏷 Тикер: <code>{analysis['ticker']}</code>\n\n"
        f"📌 <b>Суть:</b>\n{analysis['summary']}\n\n"
        f"{impact_emoji} <b>Влияние:</b> {analysis['impact']}\n\n"
        f"🔗 <a href=\"{link}\">Подробнее</a>\n\n"
        f"⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    )
    return msg
