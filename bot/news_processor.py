"""4-stage news processing pipeline (universal channels):

   1. Quick Python filter: keywords from user_channels table (0 tokens)
   2. Sentiment by trigger counting (0 tokens) — hybrid AI for ambiguous cases
   3. Global dedup (MinHash)
   4. Distribution to matched channels
"""

import datetime
import hashlib
import html
import logging
import math
import re
import struct

from . import config
from .ai_client import analyze
from .database import (get_all_tracked_assets, get_all_ticker_subscriber_counts,
                       get_max_ticker_subscriber_count, get_ai_cache, set_ai_cache)
from .topics import count_topics, effective_topics, topic_filter_pass

logger = logging.getLogger(__name__)

# Maximum number of AI calls per scan to prevent blocking (configurable via env)
MAX_AI_CALLS_PER_SCAN = config.MAX_AI_CALLS_PER_SCAN

# News items examined per scan and the target number of matched items after
# which scanning stops early. Items are processed freshest-first, so the
# window contains the most relevant part of the stream instead of whatever
# the first feed happened to return.
MAX_SCAN_ITEMS = 40
MAX_SCAN_MATCHED = 15

# Keywords that are ambiguous outside their domain and should be verified by
# the LLM before delivery (e.g. "золото" → gold medal, «Золотой глобус»,
# «Южуралзолото»). Normalized (lowercase) forms.
AMBIGUOUS_KEYWORDS = frozenset({
    "золото", "золотой", "золотая", "золотом", "золотые", "gold",
    "серебро", "silver", "платина", "платины", "platinum",
    "инфляция", "инфляции", "inflation",
    "нефть", "нефти", "oil",
    "газ", "gas",
    "биткоин", "bitcoin",
    "санкци", "санкций", "sanction", "sanctions",
})

# Importance score weights
IMPORTANCE_WEIGHTS = {
    "sentiment_magnitude": 0.25,
    "ai_confidence": 0.20,
    "source_authority": 0.10,
    "recency": 0.15,
    "match_count": 0.10,
    "subscriber_popularity": 0.20,
}


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


def _parse_published(value) -> datetime.datetime | None:
    """Parse a published timestamp (ISO string) into a naive datetime, or None."""
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    try:
        return datetime.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _relevance_cache_key(content_hash: str, keyword: str) -> str:
    return f"rel:{content_hash}:{_normalize(keyword)}"


def _sentiment_cache_key(content_hash: str, ticker: str | None) -> str:
    return f"sent:{content_hash}:{ticker or 'none'}"


def _polarity_from_provider(value: str) -> str | None:
    """Map an aggregator polarity label to the bot's sentiment vocabulary."""
    v = str(value).strip().lower()
    if v in ("positive", "pos"):
        return "POSITIVE"
    if v in ("negative", "neg"):
        return "NEGATIVE"
    if v in ("neutral", "neu"):
        return "NEUTRAL"
    return None


# Russian morphological endings, longest first so longer endings win over
# their single-letter suffixes (e.g. "ого" over "о").
_STEM_ENDINGS = (
    "ятся", "ются", "ыми", "ими", "ого", "его", "ому", "ему",
    "ать", "ить", "еть", "тся",
    "ая", "яя", "ое", "ее", "ые", "ие", "ую", "юю",
    "ий", "ый", "ой", "ей",
    "ах", "ях", "ам", "ям", "ом", "ем", "ов", "ев",
    "а", "я", "о", "е", "у", "ю", "ы", "и", "ь",
)


def _simple_stem(word: str) -> str:
    word = word.lower()
    for ending in _STEM_ENDINGS:
        if len(word) > len(ending) + 3 and word.endswith(ending):
            return word[:-len(ending)]
    return word


_WORD_RE = re.compile(r"[а-яёa-z0-9-]+")


def _kw_in_text(combined: str, kw: str, words: list[str] | None = None) -> bool:
    """Whole-word keyword matching.

    Multi-word phrases match as substrings of the lowercased text; single
    words must match the START of a whole word after light stemming. This
    prevents false positives like "золото" matching mid-word in
    "Южуралзолото" while still catching inflections ("золотом", "золотой").
    """
    kw = _normalize(kw)
    if len(kw) < 2:
        return False
    if " " in kw:
        return kw in combined
    root = _simple_stem(kw)
    if len(root) < 2:
        return False
    if words is None:
        words = _WORD_RE.findall(combined)
    return any(w.startswith(root) for w in words)


# ── Stage 1: keyword matching against user channels ──

def match_news_to_channels(
    title: str,
    summary: str,
    all_channels: list[dict],
) -> list[dict]:
    """Check a single news item against all user channels.

    Returns list of matches: [{channel_id, user_id, language, ticker, matched_keyword}]

    Builds an inverted index keyword root → channels once, so channels whose
    keywords don't appear in the text are never iterated in the per-keyword match.
    """
    combined = _normalize(title + " " + summary)
    words = _WORD_RE.findall(combined)
    topic_counts = count_topics(combined)

    # ── Inverted index: keyword root → channels ──
    # Multi-word keywords match as a substring of the combined text; single
    # words match the START of a text word after light stemming.
    phrase_index: dict[str, list[dict]] = {}
    root_index: dict[str, list[dict]] = {}
    for ch in all_channels:
        if not topic_filter_pass(topic_counts, effective_topics(ch)):
            continue
        for kw in ch.get("keywords", []):
            nk = _normalize(kw)
            if " " in nk:
                phrase_index.setdefault(nk, []).append(ch)
            else:
                root = _simple_stem(nk)
                if len(root) >= 2:
                    root_index.setdefault(root, []).append(ch)

    matched_channels: set[int] = set()
    for phrase, chs in phrase_index.items():
        if phrase in combined:
            matched_channels.update(id(c) for c in chs)
    for w in words:
        for root, chs in root_index.items():
            if w.startswith(root):
                matched_channels.update(id(c) for c in chs)

    if not matched_channels:
        return []

    matches = []
    for ch in all_channels:
        if id(ch) not in matched_channels:
            continue
        for kw in ch.get("keywords", []):
            if not _kw_in_text(combined, kw, words):
                continue
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
    words = _WORD_RE.findall(combined)

    for asset in tracked_assets:
        keywords = asset.get("keywords", [])
        ticker = asset["ticker"]
        for kw in keywords:
            if _kw_in_text(combined, kw, words):
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
                        ai_timeout: int = 10,
                        content_hash: str | None = None) -> str | None:
    combined = _normalize(title + " " + summary)
    pos_triggers = positive_triggers or (asset.get("positive_triggers", []) if asset else [])
    neg_triggers = negative_triggers or (asset.get("negative_triggers", []) if asset else [])

    cache_key = (
        _sentiment_cache_key(content_hash, asset.get("ticker") if asset else None)
        if content_hash else None
    )
    if cache_key:
        cached = await get_ai_cache(cache_key)
        if cached in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            return cached

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
            if cache_key:
                await set_ai_cache(cache_key, text)
            return text
    return None


async def refine_sentiment(
    content_hash: str,
    title: str,
    summary: str,
    asset: dict | None,
    impact: str,
    confidence: str,
    ai_calls_count: int,
    positive_triggers: list[str] | None = None,
    negative_triggers: list[str] | None = None,
    agg_sentiment: str | None = None,
    agg_sentiment_score: float | None = None,
) -> tuple[str, int]:
    """Refine rule-based sentiment via AI cache or LLM when confidence is low.

    Shared by global_scan and the legacy manual scans. Applies the per-scan AI
    budget: cache hits and low-confidence-but-high-signal results don't cost a
    call. When the aggregator provided a confident sentiment (NEWS_AGG_USE_
    SENTIMENT) it is trusted without an LLM call. Returns (impact, ai_calls_used).
    """
    if confidence != "low" and impact != "NEUTRAL":
        return impact, 0

    if config.NEWS_AGG_USE_SENTIMENT and agg_sentiment:
        polarity = _polarity_from_provider(agg_sentiment)
        if polarity and abs(float(agg_sentiment_score or 0.0)) >= config.NEWS_AGG_SENTIMENT_THRESHOLD:
            return polarity, 0

    sent_cache_key = _sentiment_cache_key(
        content_hash, asset.get("ticker") if asset else None
    )
    cached = await get_ai_cache(sent_cache_key)
    if cached is not None and cached in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
        return cached, 0

    if ai_calls_count >= MAX_AI_CALLS_PER_SCAN:
        return impact, 0

    ai_impact = await stage2_hybrid(
        title, summary, asset, positive_triggers, negative_triggers, confidence,
        content_hash=content_hash,
    )
    if ai_impact:
        impact = ai_impact
    return impact, 1


async def _verify_relevance(title: str, summary: str, keyword: str,
                            ai_timeout: int = 8,
                            content_hash: str | None = None) -> bool | None:
    """Ask the LLM whether the news is really about `keyword`.

    Returns True/False, or None when the AI is unavailable or gave an
    unparseable answer (in which case the match is kept).
    """
    cache_key = _relevance_cache_key(content_hash, keyword) if content_hash else None
    if cache_key:
        cached = await get_ai_cache(cache_key)
        if cached == "yes":
            return True
        if cached == "no":
            return False

    system_prompt = (
        "Ты — новостной редактор. Определи, действительно ли новость посвящена "
        "указанной теме. Отвечай ТОЛЬКО одним словом: да или нет."
    )
    user_message = (
        f"Тема: {keyword}\n\n"
        f"Заголовок: {title}\n"
        f"Краткое содержание: {summary[:300]}\n\n"
        f"Новость действительно об этой теме? Ответь одним словом: да или нет."
    )
    result = await analyze(system_prompt, user_message, parse_json=False,
                           temperature=0.0, max_tokens=5, timeout=ai_timeout)
    if result:
        text = result.strip().lower()
        if text.startswith("да"):
            if cache_key:
                await set_ai_cache(cache_key, "yes")
            return True
        if text.startswith("нет"):
            if cache_key:
                await set_ai_cache(cache_key, "no")
            return False
    return None


def compute_importance_score(
    title: str,
    summary: str,
    sentiment: str,
    confidence: str,
    pos_count: int = 0,
    neg_count: int = 0,
    match_count: int = 0,
    subscriber_count: int = 0,
    max_subscriber_count: int = 1,
    created_at: datetime.datetime | None = None,
    opr: int | None = None,
    is_breaking: bool = False,
) -> float:
    now = datetime.datetime.now()

    magnitude = abs(pos_count - neg_count) / max(pos_count + neg_count, 1)
    if sentiment == "POSITIVE":
        sentiment_magnitude = magnitude
    elif sentiment == "NEGATIVE":
        sentiment_magnitude = magnitude
    else:
        sentiment_magnitude = magnitude * 0.5

    ai_confidence_factor = 1.0 if confidence == "high" else 0.5

    if config.NEWS_AGG_USE_OPR and opr is not None:
        source_authority = min(max(float(opr), 0.0) / 10.0, 1.0)
    else:
        source_authority = 0.7

    if created_at:
        hours_old = (now - created_at).total_seconds() / 3600
        recency = math.exp(-hours_old / 24)
    else:
        recency = 1.0

    match_factor = min(match_count / 20, 1.0)

    sub_norm = math.log(subscriber_count + 1) / math.log(max_subscriber_count + 1)
    subscriber_factor = min(sub_norm, 1.0)

    score = (
        IMPORTANCE_WEIGHTS["sentiment_magnitude"] * sentiment_magnitude +
        IMPORTANCE_WEIGHTS["ai_confidence"] * ai_confidence_factor +
        IMPORTANCE_WEIGHTS["source_authority"] * source_authority +
        IMPORTANCE_WEIGHTS["recency"] * recency +
        IMPORTANCE_WEIGHTS["match_count"] * match_factor +
        IMPORTANCE_WEIGHTS["subscriber_popularity"] * subscriber_factor
    )

    if is_breaking:
        score += 0.05

    return round(min(max(score, 0.0), 1.0), 4)


# ── Global scan: process all news against all channels ──

async def global_scan(
    news_items: list[dict],
    all_channels: list[dict],
    skip_ai: bool = False,
) -> dict[int, list[dict]]:
    """Process all news against all user channels.

    Returns {channel_id: [matched_news_item_with_sentiment]}.
    Each matched item: {title, source, link, summary, impact, matched_keyword, ticker_hint}
    """
    if not all_channels:
        return {}, []

    results: dict[int, list[dict]] = {}
    ai_calls_count = 0
    max_sub_count = await get_max_ticker_subscriber_count()
    ticker_counts = await get_all_ticker_subscriber_counts()
    tracked_by_ticker = {a["ticker"].upper(): a for a in await get_all_tracked_assets()}
    buffer_updates: list[dict] = []
    matched_so_far = 0

    # Freshest items first, so the window isn't dominated by the first feed.
    items = sorted(
        news_items[:MAX_SCAN_ITEMS],
        key=lambda it: _parse_published(it.get("published_at") or it.get("published"))
                       or datetime.datetime.min,
        reverse=True,
    )

    for item in items:
        title = item["title"]
        summary = item.get("summary", "")
        content_hash = compute_hash(title)
        created_at = _parse_published(item.get("published_at") or item.get("published"))

        matches = match_news_to_channels(title, summary, all_channels)
        if not matches:
            continue
        matched_so_far += 1

        # ── AI relevance verification: drop ambiguous / summary-only matches ──
        if not skip_ai:
            title_norm = _normalize(title)
            verdicts: dict[str, bool | None] = {}
            for m in matches:
                kw = m["matched_keyword"]
                if kw in verdicts:
                    continue
                needs_check = (
                    _normalize(kw) in AMBIGUOUS_KEYWORDS
                    or not _kw_in_text(title_norm, kw)
                )
                if not needs_check:
                    continue
                cache_key = _relevance_cache_key(content_hash, kw)
                cached = await get_ai_cache(cache_key)
                if cached is not None:
                    verdicts[kw] = (cached == "yes")
                    continue
                if ai_calls_count >= MAX_AI_CALLS_PER_SCAN:
                    continue
                verdict = await _verify_relevance(title, summary, kw,
                                                  content_hash=content_hash)
                ai_calls_count += 1
                verdicts[kw] = verdict
            if any(v is False for v in verdicts.values()):
                matches = [
                    m for m in matches
                    if verdicts.get(m["matched_keyword"]) is not False
                ]
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
            asset = tracked_by_ticker.get(first_channel["ticker"].upper())
            if asset:
                pos_triggers = asset.get("positive_triggers", [])
                neg_triggers = asset.get("negative_triggers", [])

        # Compute trigger counts for importance
        combined = _normalize(title + " " + summary)
        pos_count = sum(1 for t in pos_triggers if _normalize(t) in combined) if pos_triggers else 0
        neg_count = sum(1 for t in neg_triggers if _normalize(t) in combined) if neg_triggers else 0

        sentiment, confidence = compute_sentiment(title, summary, asset, pos_triggers, neg_triggers)
        if not skip_ai:
            sentiment, used = await refine_sentiment(
                content_hash, title, summary, asset, sentiment, confidence,
                ai_calls_count, pos_triggers, neg_triggers,
                agg_sentiment=item.get("agg_sentiment"),
                agg_sentiment_score=item.get("agg_sentiment_score"),
            )
            ai_calls_count += used

        impact = sentiment
        match_count = len(matches)

        # Collect tickers from matched channels for subscriber lookup
        matched_tickers = set()
        for m in matches:
            t = m.get("ticker")
            if t:
                matched_tickers.add(t.upper())

        # Use the ticker with highest subscriber count for importance
        max_sub_for_item = 0
        primary_ticker = ""
        for ticker in matched_tickers:
            sc = ticker_counts.get(ticker, 0)
            if sc > max_sub_for_item:
                max_sub_for_item = sc
                primary_ticker = ticker

        importance_score = compute_importance_score(
            title=title,
            summary=summary,
            sentiment=sentiment,
            confidence=confidence,
            pos_count=pos_count,
            neg_count=neg_count,
            match_count=match_count,
            subscriber_count=max_sub_for_item,
            max_subscriber_count=max_sub_count,
            created_at=created_at,
            opr=item.get("opr"),
            is_breaking=bool(item.get("is_breaking")),
        )

        buffer_updates.append({
            "content_hash": content_hash,
            "source": item.get("source", ""),
            "title": title,
            "url": item.get("link", ""),
            "summary": (summary or title)[:200],
            "importance_score": importance_score,
            "match_count": match_count,
            "is_used": 1 if match_count > 0 else 0,
            "ticker_hints": list(matched_tickers),
            "subscriber_counts": {t: ticker_counts.get(t, 0) for t in matched_tickers},
        })

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
                "importance_score": importance_score,
            })

        if matched_so_far >= MAX_SCAN_MATCHED:
            logger.info(f"global_scan: reached {MAX_SCAN_MATCHED} matched items, stopping early")
            break

    return results, buffer_updates


# ── Formatting ──

def _safe_html(text: str) -> str:
    """Unescape then re-escape arbitrary text so it can be embedded in HTML messages."""
    return html.escape(html.unescape(str(text)), quote=False)


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
                extra += f"  🔑 {_safe_html(val)}"
        ticker_val = item.get(ticker_key)
        ticker_info = f"  🏷 <code>{_safe_html(ticker_val)}</code>" if ticker_val else ""
        score = item.get("importance_score")
        score_str = ""
        if score is not None and score > 0:
            if score >= 0.7:
                score_str = " ★"
            elif score >= 0.5:
                score_str = " ☆"
            score_str += f" <code>{score:.2f}</code>"
        block = (
            f"<b>{i}. {_safe_html(item['title'])}</b>{score_str}\n"
            f"📡 {_safe_html(item['source'])}{ticker_info}{extra}\n"
            f"📌 {_safe_html(item['summary'])}\n"
            f"{impact_emoji} {_safe_html(item['impact'])}"
        )
        if item.get("link"):
            link_text = "Подробнее" if lang == "ru" else "Read more"
            block += f'\n🔗 <a href="{html.escape(str(item["link"]), quote=True)}">{link_text}</a>'
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
        f"📰 {_safe_html(title)}\n"
        f"📡 Источник: {_safe_html(source)}\n"
        f"🏷 Тикер: <code>{_safe_html(analysis['ticker'])}</code>\n\n"
        f"📌 <b>Суть:</b>\n{_safe_html(analysis['summary'])}\n\n"
        f"{impact_emoji} <b>Влияние:</b> {_safe_html(analysis['impact'])}\n\n"
        f"🔗 <a href=\"{html.escape(str(link), quote=True)}\">Подробнее</a>\n\n"
        f"⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    )
    return msg
