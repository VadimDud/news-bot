"""3-stage news processing pipeline (updated):

   1. Quick Python filter: keywords from tracked_assets table (0 tokens)
   2. Sentiment by trigger counting (0 tokens) — hybrid AI for ambiguous cases
   3. SQLite storage (news table)
"""

import hashlib
import json
import logging
import re
import struct

import httpx

from . import config
from .retry_utils import async_retry

logger = logging.getLogger(__name__)


def _shingle(text: str, n: int = 3):
    """Yield n-character shingles from text."""
    for i in range(len(text) - n + 1):
        yield text[i:i+n]


def compute_minhash(text: str) -> list:
    """Compute MinHash signature (4 ints) using 3-char shingles and 4 seeds."""
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
    """Return a hex string representation of the MinHash signature."""
    sig = compute_minhash(text)
    return ''.join(f'{i:016x}' for i in sig)


def is_similar(hash1: str, hash2: str, threshold: float = 0.75) -> bool:
    """Compare two MinHash hex signatures and return True if Jaccard similarity >= threshold."""
    sig1 = [int(hash1[i:i+16], 16) for i in range(0, 64, 16)]
    sig2 = [int(hash2[i:i+16], 16) for i in range(0, 64, 16)]
    equal = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return (equal / 4.0) >= threshold


def _normalize(text: str) -> str:
    """Lowercase and strip for matching."""
    return text.lower().strip()


def _simple_stem(word: str) -> str:
    """Very basic Russian stemming — strip common endings for matching."""
    word = word.lower()
    for ending in ("ого", "ему", "ать", "ить", "еть", "ятся", "ются", "тся",
                    "ий", "ый", "ой", "ая", "яя", "ое", "ее", "ов", "ев",
                    "ам", "ям", "ах", "ях", "ов", "ев", "ах", "ях"):
        if len(word) > len(ending) + 3 and word.endswith(ending):
            return word[:-len(ending)]
    return word


def stage1_filter(title: str, summary: str, tracked_assets: list[dict]) -> tuple[bool, str | None, dict | None]:
    """Filter news against tracked_assets keywords.

    Returns (is_relevant, matched_ticker_or_None, matched_asset_or_None).
    """
    combined = _normalize(title + " " + summary)
    combined_stems = _simple_stem(combined)

    for asset in tracked_assets:
        keywords = asset.get("keywords", [])
        ticker = asset["ticker"]

        for kw in keywords:
            kw_lower = _normalize(kw)
            if len(kw_lower) < 2:
                continue
            # Check exact or stemmed match
            if kw_lower in combined or _simple_stem(kw_lower) in combined_stems:
                logger.info(f"Stage1 MATCH: {title[:50]} -> {ticker} (keyword: {kw})")
                return True, ticker, asset

    # No keyword match — skip
    logger.debug(f"Stage1 SKIP: {title[:60]}")
    return False, None, None


def compute_sentiment(title: str, summary: str, asset: dict) -> tuple[str, str]:
    """Compute sentiment by counting positive/negative triggers in text.

    Returns (sentiment, confidence) where confidence is 'high' or 'low'.
    High confidence: >=3 triggers, all same polarity.
    Low confidence: all other cases.
    """
    combined = _normalize(title + " " + summary)
    pos_count = 0
    neg_count = 0

    for trigger in asset.get("positive_triggers", []):
        if _normalize(trigger) in combined:
            pos_count += 1

    for trigger in asset.get("negative_triggers", []):
        if _normalize(trigger) in combined:
            neg_count += 1

    total = pos_count + neg_count
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


async def stage2_hybrid(title: str, summary: str, asset: dict, trigger_confidence: str = "low") -> str | None:
    """Hybrid AI fallback: called for ambiguous or low-confidence cases.

    Returns sentiment string or None if AI unavailable.
    """
    pos_count = sum(1 for t in asset.get("positive_triggers", []) if _normalize(t) in _normalize(title + " " + summary))
    neg_count = sum(1 for t in asset.get("negative_triggers", []) if _normalize(t) in _normalize(title + " " + summary))

    # Call AI when:
    # 1. Both positive and negative triggers found (ambiguous)
    # 2. Low confidence (few triggers or mixed polarity)
    # 3. Zero triggers (no signal from triggers at all)
    should_call_ai = (
        (pos_count > 0 and neg_count > 0)  # ambiguous
        or trigger_confidence == "low"       # low confidence
        or (pos_count == 0 and neg_count == 0)  # no trigger signal
    )

    if not should_call_ai:
        return None

    if config.DEEPSEEK_API_KEY:
        return await _call_deepseek_sentiment(title, summary, asset)
    elif config.GEMINI_API_KEY:
        return await _call_gemini_sentiment(title, summary, asset)
    elif config.DASHSCOPE_API_KEY:
        return await _call_dashscope_sentiment(title, summary, asset)
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_deepseek_sentiment(title: str, summary: str, asset: dict) -> str | None:
    """Quick DeepSeek call for ambiguous sentiment."""
    if not config.DEEPSEEK_API_KEY:
        return None
    prompt = (
        f"Новость: {title}\nСуть: {summary[:200]}\n\n"
        f"Актив: {asset.get('company_name', asset['ticker'])}\n\n"
        f"Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. "
        f"Ответь одним словом."
    )
    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={
                "model": config.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты финансовый аналитик. Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. Ответь одним словом."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 150,
            }, headers=headers)
            if resp.status_code == 200:
                text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()
                if text in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                    return text
    except Exception:
        pass
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_gemini_sentiment(title: str, summary: str, asset: dict) -> str | None:
    """Quick Gemini call for ambiguous sentiment."""
    if not config.GEMINI_API_KEY:
        return None
    prompt = (
        f"Новость: {title}\nСуть: {summary[:200]}\n\n"
        f"Актив: {asset.get('company_name', asset['ticker'])}\n\n"
        f"Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. "
        f"Ответь одним словом."
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    headers = {"Content-Type": "application/json", "X-goog-api-key": config.GEMINI_API_KEY}
    try:
        proxy = config.HTTP_PROXY or None
        async with httpx.AsyncClient(timeout=15, proxy=proxy) as client:
            resp = await client.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 10},
            }, headers=headers)
            if resp.status_code == 200:
                text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().upper()
                if text in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                    return text
    except Exception:
        pass
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_dashscope_sentiment(title: str, summary: str, asset: dict) -> str | None:
    """Quick DashScope call for ambiguous sentiment."""
    if not config.DASHSCOPE_API_KEY:
        return None
    base_url = config.DASHSCOPE_BASE_URL.rstrip("/")
    prompt = (
        f"Новость: {title}\nСуть: {summary[:200]}\n\n"
        f"Актив: {asset.get('company_name', asset['ticker'])}\n\n"
        f"Определи общий тон новости: POSITIVE, NEGATIVE или NEUTRAL. "
        f"Ответь одним словом."
    )
    try:
        proxy = config.HTTP_PROXY or None
        async with httpx.AsyncClient(timeout=15, proxy=proxy) as client:
            resp = await client.post(
                f"{base_url}/services/aigc/text-generation/generation",
                headers={"Authorization": f"Bearer {config.DASHSCOPE_API_KEY}", "Content-Type": "application/json"},
                json={"model": config.DASHSCOPE_MODEL, "input": {"messages": [
                    {"role": "system", "content": "Отвечай одним словом: POSITIVE, NEGATIVE или NEUTRAL."},
                    {"role": "user", "content": prompt},
                ]}, "parameters": {"max_tokens": 10, "temperature": 0.1}},
            )
            if resp.status_code == 200:
                choices = resp.json().get("output", {}).get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "").strip().upper()
                    if text in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                        return text
    except Exception:
        pass
    return None


def split_news_text(text: str, max_len: int = 4000) -> list[str]:
    """Split text into chunks for Telegram (4096 char limit).

    Splits at numbered item boundaries (1. 2. etc), never mid-item.
    """
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


def format_news_batch(items: list[dict], lang: str = "ru") -> list[str]:
    """Format multiple news items into Telegram messages (split if >4096 chars).

    Each item: {title, source, ticker, summary, impact, link}
    Returns list of message strings.
    """
    if not items:
        return []

    import datetime
    now = datetime.datetime.now().strftime("%H:%M")
    emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}
    disclaimer = "\n\n⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    parts = []

    for i, item in enumerate(items, 1):
        impact_emoji = emoji.get(item["impact"], "🟡")
        block = (
            f"<b>{i}. {item['title']}</b>\n"
            f"📡 {item['source']}  |  🏷 <code>{item['ticker']}</code>\n"
            f"📌 {item['summary']}\n"
            f"{impact_emoji} {item['impact']}"
        )
        if item.get("link"):
            block += f'\n🔗 <a href="{item["link"]}">Подробнее</a>'
        parts.append(block)

    if lang == "ru":
        header = f"📰 <b>Новости</b> ({len(items)} шт.) — обновлено {now}\n{'─' * 20}\n\n"
    else:
        header = f"📰 <b>News</b> ({len(items)} items) — updated {now}\n{'─' * 20}\n\n"

    full_text = header + "\n\n".join(parts) + disclaimer
    chunks = split_news_text(full_text, max_len=4000)

    # Add disclaimer only to last chunk if multiple
    if len(chunks) > 1:
        chunks[-1] += disclaimer
        # Remove disclaimer from full_text for first chunks
        chunks = [c.replace(disclaimer, "") for c in chunks[:-1]] + [chunks[-1]]

    return chunks if chunks else [full_text]


def format_news_alert(title: str, source: str, analysis: dict, link: str) -> str:
    """Format analyzed news for Telegram (single item)."""
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
