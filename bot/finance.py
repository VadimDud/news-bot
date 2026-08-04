"""Financial news analysis module."""

import asyncio
import html
import logging
import re
import time
from collections.abc import Mapping
import httpx
import feedparser
from datetime import datetime

from . import config
from .aggregators import fetch_aggregated
from .feed_filter import should_keep
from .retry_utils import async_retry
from .sources import get_sources_by_tags

logger = logging.getLogger(__name__)

# Conditional HTTP cache per feed URL: {url: (etag, last_modified, entries, ts)}
# Reused across the 5-min tag cache and different tag combos to avoid
# re-downloading unchanged feeds (If-None-Match / If-Modified-Since → 304).
_http_cache: dict[str, tuple[str | None, str | None, list[dict], float]] = {}

# Legacy RSS feeds (kept for backward compat)
FINANCE_FEEDS = [
    {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/news.xml", "type": "rss"},
    {"name": "Интерфакс", "url": "https://www.interfax.ru/rss.asp", "type": "rss"},
    {"name": "ТАСС", "url": "https://tass.ru/rss/v2.xml", "type": "rss"},
    {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss/news.xml", "type": "rss"},
]




@async_retry(max_retries=2, base_delay=2.0)
async def fetch_finance_news() -> list[dict]:
    """Fetch latest news from Russian sources (no pre-filter — stage1_filter handles relevance).

    Wraps fetch_news(["finance"]) — the finance category catalog is the same set
    of feeds as the legacy FINANCE_FEEDS constant.
    """
    return await fetch_news(source_tags=["finance"])


async def _fetch_sources(feeds: list[dict]) -> list[dict]:
    """Fetch news from a list of feeds using one shared HTTP client, then dedup."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            results = await asyncio.gather(
                *[_fetch_one(client, f) for f in feeds],
                return_exceptions=True,
            )
    except Exception as e:
        logger.warning(f"Failed to create HTTP client: {e}")
        return []
    all_news = [item for r in results if isinstance(r, list) for item in r]
    return _dedup_news(all_news)


async def _fetch_one(client: httpx.AsyncClient, feed_info: dict) -> list[dict]:
    url = feed_info["url"]
    headers = {}
    cached = _http_cache.get(url)
    if cached:
        etag, last_modified, _, _ts = cached
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
    try:
        resp = await client.get(url, follow_redirects=True, headers=headers)
        if resp.status_code == 304:
            if cached:
                logger.debug(f"Feed {feed_info['name']}: 304 Not Modified, using cached entries")
                return cached[2]
            return []
        if resp.status_code != 200:
            return []
        if feed_info["type"] == "rss":
            feed = await asyncio.to_thread(feedparser.parse, resp.text)
            entries = [
                {
                    "title": e.get("title", ""),
                    "summary": _clean_html(e.get("summary", ""))[:300],
                    "link": e.get("link", ""),
                    "source": feed_info["name"],
                    "source_tag": feed_info.get("tag", ""),
                    "published": e.get("published", ""),
                    "published_at": _entry_published_at(e),
                }
                for e in feed.entries[:30]
            ]
        elif feed_info["type"] == "json":
            data = resp.json()
            items = data.get("items", data.get("news", []))
            entries = [
                {
                    "title": it.get("title", ""),
                    "summary": _clean_html(it.get("desc", it.get("description", "")))[:300],
                    "link": it.get("url", it.get("link", "")),
                    "source": feed_info["name"],
                    "source_tag": feed_info.get("tag", ""),
                    "published": it.get("publishDate", ""),
                    "published_at": it.get("publishDate", ""),
                }
                for it in items[:30]
            ]
        else:
            entries = []
        new_etag = None
        new_lm = None
        if isinstance(resp.headers, Mapping):
            new_etag = _header_str(resp.headers.get("ETag"))
            new_lm = _header_str(resp.headers.get("Last-Modified"))
        _http_cache[url] = (new_etag, new_lm, entries, time.time())
        return entries
    except Exception as e:
        logger.warning(f"Failed to fetch {feed_info['name']}: {e}")
        if cached:
            return cached[2]
    return []


def _header_str(value) -> str | None:
    """Return a non-empty header string, or None (also guards mock/None values)."""
    return value if isinstance(value, str) and value else None


def _entry_published_at(entry) -> str:
    parsed = entry.get("published_parsed")
    if not parsed:
        return ""
    try:
        return datetime(*parsed[:6]).isoformat()
    except (TypeError, ValueError):
        return ""


def _dedup_news(all_news: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in all_news:
        key = _dedup_key(item["title"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _dedup_key(title: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", title.lower())


# Cache for fetch_news results: {frozenset(source_tags): (timestamp, news)}
_fetch_cache: dict[frozenset, tuple[float, list[dict]]] = {}
_FETCH_CACHE_TTL = 300  # 5 minutes


@async_retry(max_retries=2, base_delay=2.0)
async def fetch_news(source_tags: list[str] | None = None,
                     keep_keywords: list[str] | None = None) -> list[dict]:
    """Fetch news from sources matching the given tags.

    Args:
        source_tags: List of category tags (e.g. ["finance", "macro"]).
                     None or empty = fetch from all sources.
        keep_keywords: Channel keywords that always protect an item from the
                     stage-0 relevance filter (see bot.feed_filter).

    Returns:
        Deduplicated, relevance-filtered list of news dicts.
    """
    cache_key = frozenset(source_tags or [])
    now = time.time()

    if cache_key in _fetch_cache:
        cached_time, cached_news = _fetch_cache[cache_key]
        if now - cached_time < _FETCH_CACHE_TTL:
            logger.info(f"fetch_news: cache hit for {list(cache_key) or 'all'} ({len(cached_news)} items)")
            return _filter_news(cached_news, source_tags, keep_keywords)

    sources = get_sources_by_tags(source_tags)
    if not sources:
        sources = get_sources_by_tags([])

    # Fetch RSS sources and the API aggregator (APITube) in parallel, then
    # dedup across both. The aggregator returns [] when disabled, so the
    # existing RSS-only behavior is preserved.
    rss_result, agg_result = await asyncio.gather(
        _fetch_sources(sources),
        fetch_aggregated(source_tags),
        return_exceptions=True,
    )
    rss_news = rss_result if isinstance(rss_result, list) else []
    agg_news = agg_result if isinstance(agg_result, list) else []
    unique = _dedup_news(rss_news + agg_news)

    _fetch_cache[cache_key] = (now, unique)
    logger.info(
        f"fetch_news: fetched {len(unique)} unique items "
        f"({len(rss_news)} RSS + {len(agg_news)} aggregated) "
        f"(tags: {list(cache_key) or 'all'})"
    )

    return _filter_news(unique, source_tags, keep_keywords)


def _filter_news(news: list[dict], tags: list[str] | None,
                 keep_keywords: list[str] | None) -> list[dict]:
    """Drop clearly irrelevant items for finance-like categories."""
    filtered = [
        item for item in news
        if should_keep(item.get("title", ""), item.get("summary", ""),
                       tags, keep_keywords)
    ]
    if len(filtered) != len(news):
        logger.info(f"fetch_news: relevance filter dropped {len(news) - len(filtered)} of {len(news)} items")
    return filtered


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(text))
    return html.unescape(text)


async def analyze_with_gemini(title: str, summary: str, tickers: list[str]) -> str:
    """Use Gemini API to generate financial analysis."""
    if not config.GEMINI_API_KEY:
        return _fallback_analysis(title, tickers)

    prompt = f"""Ты — оперативный финансовый аналитик. Проанализируй новость для инвестора.

Новость: {title}
Описание: {summary}
Тикеры в подписке: {', '.join(tickers) if tickers else 'не указаны'}

Сгенерируй КОРОТКИЙ анализ по шаблону:
1. Оценка события (🟢 Позитив / 🔴 Негатив / 🟡 Нейтрально) — одно слово
2. Оптимистичный сценарий — 1 предложение
3. Пессимистичный сценарий — 1 предложение
4. Рекомендация — 1 предложение

Отвечай ТОЛЬКО на русском, кратко, без лишних слов."""

    try:
        async with httpx.AsyncClient(timeout=30, proxy=config.HTTP_PROXY or None) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
    except Exception as e:
        logger.warning(f"Gemini API error: {e}")

    return _fallback_analysis(title, tickers)


def _fallback_analysis(title: str, tickers: list[str]) -> str:
    """Simple rule-based fallback when Gemini is unavailable."""
    title_lower = title.lower()

    if any(w in title_lower for w in ["дефолт", "техдефолт", "просроч", "не платит"]):
        return "🔴 Негативно. Высокий риск потерь. Рассмотреть выход из позиции."
    elif any(w in title_lower for w in ["рейтинг", "повышени", "апгрейд"]):
        return "🟢 Позитивно. Укрепление позиций эмитента. Можно держать."
    elif any(w in title_lower for w in ["снижени рейтинг", "понижени", "даунгрейд"]):
        return "🔴 Негативно. Риск дальнейшего падения. Стоит сократить позицию."
    elif any(w in title_lower for w in ["купон", "дивиденд", "погашен"]):
        return "🟢 Позитивно. Доходность подтверждена. Держать."
    elif any(w in title_lower for w in ["ставк", "ЦБ"]):
        return "🟡 Нейтрально. Следить за решением ЦБ по ключевой ставке."
    else:
        return "🟡 Нейтрально. Событие требует дополнительного анализа."


def _safe_html(text: str) -> str:
    """Unescape then re-escape arbitrary text so it can be embedded in HTML messages."""
    return html.escape(html.unescape(str(text)), quote=False)


def format_finance_alert(title: str, summary: str, source: str, analysis: str, link: str) -> str:
    """Format financial news alert for Telegram."""
    msg = (
        f"🔔 <b>ФИНАНСОВАЯ НОВОСТЬ</b>\n"
        f"📰 {_safe_html(title)}\n"
        f"📡 Источник: {_safe_html(source)}\n\n"
        f"📌 <b>Суть:</b>\n{_safe_html(summary)}\n\n"
        f"⚡ <b>Оценка:</b>\n{_safe_html(analysis)}\n\n"
        f"🔗 <a href=\"{html.escape(str(link), quote=True)}\">Подробнее</a>\n\n"
        f"⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    )
    return msg
