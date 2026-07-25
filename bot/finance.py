"""Financial news analysis module."""

import logging
import httpx
import feedparser
from datetime import datetime

from . import config
from .retry_utils import async_retry

logger = logging.getLogger(__name__)

# RSS feeds for Russian financial news
FINANCE_FEEDS = [
    {
        "name": "Коммерсантъ",
        "url": "https://www.kommersant.ru/RSS/news.xml",
        "type": "rss",
    },
    {
        "name": "Интерфакс",
        "url": "https://www.interfax.ru/rss.asp",
        "type": "rss",
    },
    {
        "name": "ТАСС",
        "url": "https://tass.ru/rss/v2.xml",
        "type": "rss",
    },
    {
        "name": "Ведомости",
        "url": "https://www.vedomosti.ru/rss/news.xml",
        "type": "rss",
    },
]

# Keywords that indicate financial/market news
FINANCE_KEYWORDS = [
    "ставк", "инфляц", "дефолт", "рейтинг", "купон", "облигац",
    "ОФЗ", "евробонд", "акци", "дивиденд", "выручк", "прибыл",
    "ЦБ", "Росстат", "Мосбирж", "Сбербанк", "Газпром", "ЛУКОЙЛ",
    "Роснефть", "Норникель", "Яндекс", "Т-Банк", "ВТБ", "Россельхоз",
    "санкц", "эмитент", "погашен", "размещ", "аукцион", "репо",
    "ключев", "долг", "бюджет", "ВВП", "нефт", "газ", "металл",
]


@async_retry(max_retries=3, base_delay=2.0)
async def fetch_finance_news() -> list[dict]:
    """Fetch latest news from Russian sources (no pre-filter — stage1_filter handles relevance)."""
    all_news = []

    for feed_info in FINANCE_FEEDS:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(feed_info["url"], follow_redirects=True)
                if resp.status_code != 200:
                    continue

                if feed_info["type"] == "rss":
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:30]:
                        title = entry.get("title", "")
                        summary = entry.get("summary", "")
                        link = entry.get("link", "")
                        all_news.append({
                            "title": title,
                            "summary": _clean_html(summary)[:300],
                            "link": link,
                            "source": feed_info["name"],
                            "published": entry.get("published", ""),
                        })
                elif feed_info["type"] == "json":
                    data = resp.json()
                    items = data.get("items", data.get("news", []))
                    for item in items[:30]:
                        title = item.get("title", "")
                        desc = item.get("desc", item.get("description", ""))
                        link = item.get("url", item.get("link", ""))
                        all_news.append({
                            "title": title,
                            "summary": _clean_html(desc)[:300],
                            "link": link,
                            "source": feed_info["name"],
                            "published": item.get("publishDate", ""),
                        })
        except Exception as e:
            logger.warning(f"Failed to fetch {feed_info['name']}: {e}")
            continue

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_news:
        key = item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def _is_finance_relevant(title: str, text: str) -> bool:
    """Check if news is relevant to finance/investments."""
    combined = (title + " " + text).lower()
    return any(kw.lower() in combined for kw in FINANCE_KEYWORDS)


def _clean_html(text: str) -> str:
    """Remove HTML tags."""
    import re
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
