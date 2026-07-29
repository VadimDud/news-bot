"""Financial news analysis module."""

import asyncio
import logging
import re
import httpx
import feedparser
from datetime import datetime

from . import config
from .retry_utils import async_retry
from .sources import get_sources_by_tags

logger = logging.getLogger(__name__)

# Legacy RSS feeds (kept for backward compat)
FINANCE_FEEDS = [
    {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/news.xml", "type": "rss"},
    {"name": "Интерфакс", "url": "https://www.interfax.ru/rss.asp", "type": "rss"},
    {"name": "ТАСС", "url": "https://tass.ru/rss/v2.xml", "type": "rss"},
    {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss/news.xml", "type": "rss"},
]




@async_retry(max_retries=2, base_delay=2.0)
async def fetch_finance_news() -> list[dict]:
    """Fetch latest news from Russian sources (no pre-filter — stage1_filter handles relevance)."""

    async def _fetch_one(feed_info: dict) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(feed_info["url"], follow_redirects=True)
                if resp.status_code != 200:
                    return []
                if feed_info["type"] == "rss":
                    feed = feedparser.parse(resp.text)
                    return [
                        {
                            "title": e.get("title", ""),
                            "summary": _clean_html(e.get("summary", ""))[:300],
                            "link": e.get("link", ""),
                            "source": feed_info["name"],
                            "published": e.get("published", ""),
                        }
                        for e in feed.entries[:30]
                    ]
                elif feed_info["type"] == "json":
                    data = resp.json()
                    items = data.get("items", data.get("news", []))
                    return [
                        {
                            "title": it.get("title", ""),
                            "summary": _clean_html(it.get("desc", it.get("description", "")))[:300],
                            "link": it.get("url", it.get("link", "")),
                            "source": feed_info["name"],
                            "published": it.get("publishDate", ""),
                        }
                        for it in items[:30]
                    ]
        except Exception as e:
            logger.warning(f"Failed to fetch {feed_info['name']}: {e}")
        return []

    results = await asyncio.gather(*[_fetch_one(f) for f in FINANCE_FEEDS])
    all_news = [item for batch in results for item in batch]

    seen = set()
    unique = []
    for item in all_news:
        key = item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


# Cache for fetch_news results: {frozenset(source_tags): (timestamp, news)}
_fetch_cache: dict[frozenset, tuple[float, list[dict]]] = {}
_FETCH_CACHE_TTL = 300  # 5 minutes


@async_retry(max_retries=2, base_delay=2.0)
async def fetch_news(source_tags: list[str] | None = None) -> list[dict]:
    """Fetch news from sources matching the given tags.

    Args:
        source_tags: List of category tags (e.g. ["finance", "macro"]).
                     None or empty = fetch from all sources.

    Returns:
        Deduplicated list of news dicts.
    """
    import time
    cache_key = frozenset(source_tags or [])
    now = time.time()

    if cache_key in _fetch_cache:
        cached_time, cached_news = _fetch_cache[cache_key]
        if now - cached_time < _FETCH_CACHE_TTL:
            logger.info(f"fetch_news: cache hit for {list(cache_key) or 'all'} ({len(cached_news)} items)")
            return cached_news

    sources = get_sources_by_tags(source_tags)
    if not sources:
        sources = get_sources_by_tags([])

    async def _fetch_one(feed_info: dict) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(feed_info["url"], follow_redirects=True)
                if resp.status_code != 200:
                    return []
                if feed_info["type"] == "rss":
                    feed = feedparser.parse(resp.text)
                    return [
                        {
                            "title": e.get("title", ""),
                            "summary": _clean_html(e.get("summary", ""))[:300],
                            "link": e.get("link", ""),
                            "source": feed_info["name"],
                            "source_tag": feed_info.get("tag", ""),
                            "published": e.get("published", ""),
                        }
                        for e in feed.entries[:30]
                    ]
                elif feed_info["type"] == "json":
                    data = resp.json()
                    items = data.get("items", data.get("news", []))
                    return [
                        {
                            "title": it.get("title", ""),
                            "summary": _clean_html(it.get("desc", it.get("description", "")))[:300],
                            "link": it.get("url", it.get("link", "")),
                            "source": feed_info["name"],
                            "source_tag": feed_info.get("tag", ""),
                            "published": it.get("publishDate", ""),
                        }
                        for it in items[:30]
                    ]
        except Exception as e:
            logger.warning(f"Failed to fetch {feed_info['name']}: {e}")
        return []

    results = await asyncio.gather(*[_fetch_one(f) for f in sources])
    all_news = [item for batch in results for item in batch]

    seen = set()
    unique = []
    for item in all_news:
        key = item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    _fetch_cache[cache_key] = (now, unique)
    logger.info(f"fetch_news: fetched {len(unique)} unique items from {len(sources)} sources (tags: {list(cache_key) or 'all'})")

    return unique


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


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


def format_finance_alert(title: str, summary: str, source: str, analysis: str, link: str) -> str:
    """Format financial news alert for Telegram."""
    msg = (
        f"🔔 <b>ФИНАНСОВАЯ НОВОСТЬ</b>\n"
        f"📰 {title}\n"
        f"📡 Источник: {source}\n\n"
        f"📌 <b>Суть:</b>\n{summary}\n\n"
        f"⚡ <b>Оценка:</b>\n{analysis}\n\n"
        f"🔗 <a href=\"{link}\">Подробнее</a>\n\n"
        f"⚠️ <i>Не является индивидуальной инвестиционной рекомендацией.</i>"
    )
    return msg
