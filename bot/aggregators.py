"""News API aggregator layer (APITube primary).

Fetches news from external JSON APIs in parallel with the RSS pipeline and
normalizes them into the same news-dict schema used by ``bot.finance``:

    {title, summary, link, source, source_tag, published, published_at}

plus optional enrichment keys consumed by ``bot.news_processor``:

    agg_sentiment, agg_sentiment_score, opr, is_breaking, shares, entities

Primary provider: APITube (https://apitube.io). Without an API key the module
is inert — the bot keeps running on RSS sources only.

Category coverage:
  * global_finance / finance / macro -> IPTC "Economy, Business & Finance"
  * politics                          -> IPTC "Politics"
  * tech / science                    -> IPTC "Science & Technology"
  * commodities / crypto / realty     -> keyword queries (no dedicated code)

APITube does not index Russian-language news (``language.code=ru`` is
rejected with ER0237), so category queries run in English
(``APITUBE_LANGUAGE``). Articles fetched under the finance code therefore map
to ``global_finance``; the Russian-facing ``finance``/``macro`` channels stay
RSS-only.

IPTC category codes are configurable (``APITUBE_CATEGORY_*``) and must be
validated with ``/v1/suggest/categories`` — an unknown code fails the whole
request with ER0206.
"""

import asyncio
import html
import logging
import re
import time

import httpx

from . import config
from .retry_utils import async_retry

logger = logging.getLogger(__name__)

# Selected response fields (dot notation for nested objects, per APITube docs).
_FIELDS = (
    "id,title,description,href,published_at,language,"
    "source.domain,source.rankings.opr,categories,"
    "sentiment.overall,is_breaking,shares.total"
)

# Preview-content truncation markers appended by APITube on free/test plans.
_PREVIEW_MARKER_RE = re.compile(
    r"\.\.\.\[(?:Upgrade subscription plan|Test mode[^\]]*)\]"
)

# Junk-signal phrases for low-quality sources that dominate the APITube free
# tier (casino/gambling spam, deal farms, clickbait). Bare words like "deal",
# "free" or "bet" are intentionally NOT matched — they are common in legit
# business headlines ("merger deal", "free trade"). Applied to aggregated
# items only; RSS sources are trusted and unaffected.
_JUNK_RE = re.compile(
    r"casino|gambl|slot\b|slot game|slots|poker|betting|bookmaker|bingo|"
    r"lottery|sweepstake|wagering|jackpot|free spins|no deposit|"
    r"sign[ -]?up bonus|promo code|promotional code|discount code|"
    r"best deal|great deal|deals? now|deals? right now|biggest discount|"
    r"clearance sale|shop now|buy now|limited offer|grab your|"
    r"don'?t miss out|click here|coupon code|код бонус|бонус казино",
    re.IGNORECASE,
)

# Bot source tag -> APITube query.
#   category: grouped by IPTC code (max 3 codes per request, OR logic)
#   keywords: free-text query against titles (AND/OR/NOT supported)
CATEGORY_QUERIES: dict[str, dict] = {
    "finance": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_FINANCE],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "macro": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_FINANCE],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "global_finance": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_FINANCE],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "politics": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_POLITICS],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "tech": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_SCIENCE_TECH],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "science": {
        "kind": "category",
        "categories": [config.APITUBE_CATEGORY_SCIENCE_TECH],
        "languages": [config.APITUBE_LANGUAGE],
    },
    "commodities": {
        "kind": "keywords",
        "keywords": ("нефть OR газ OR уголь OR золото OR металлы OR "
                     "энергоносители OR oil OR gas OR gold OR energy"),
    },
    "crypto": {
        "kind": "keywords",
        "keywords": ("bitcoin OR ethereum OR крипто OR криптовалют OR "
                     "блокчейн OR blockchain OR defi"),
    },
    "realty": {
        "kind": "keywords",
        "keywords": "недвижимость OR ипотека OR жильё OR real estate OR property",
    },
}

# Article tags -> disambiguation hints for articles fetched via category batches.
_SCIENCE_HINTS = (
    "наук", "исследован", "учё", "учен", "астроном", "физик", "химик",
    "биолог", "ген", "космос", "открыти", "science", "scientist",
    "physics", "biology", "astronomy", "research", "discovery",
)

# Simple response cache: {key: (timestamp, items)} to stay within API limits.
_AGG_CACHE: dict[str, tuple[float, list[dict]]] = {}


class AggregatorError(Exception):
    """Base error for the aggregator layer."""


class RateLimitError(AggregatorError):
    """Raised on HTTP 429 so the retry decorator can back off and retry."""


# ── Enabled check ──

def _enabled() -> bool:
    return bool(config.NEWS_AGG_ENABLED and config.APITUBE_API_KEY)


# ── HTTP client ──

@async_retry(max_retries=2, base_delay=1.0)
async def _apitube_request(params: dict) -> list[dict]:
    """Fetch articles from APITube /v1/news/everything. Returns the results array."""
    url = f"{config.APITUBE_BASE_URL.rstrip('/')}/v1/news/everything"
    headers = {"X-API-Key": config.APITUBE_API_KEY, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15, proxy=config.HTTP_PROXY or None) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 429:
            raise RateLimitError("APITube rate limited (429)")
        if resp.status_code == 402:
            logger.warning("APITube: account out of points (402)")
            return []
        if resp.status_code in (401, 403):
            logger.warning(f"APITube: auth error ({resp.status_code})")
            return []
        if resp.status_code != 200:
            logger.warning(f"APITube HTTP {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
        if isinstance(data, dict) and data.get("status") == "ok":
            return data.get("results") or []
        logger.warning(f"APITube: unexpected payload: {str(data)[:200]}")
        return []


def _category_params(codes: tuple[str, ...], lang: str) -> dict:
    params = {
        "category.id": ",".join(codes),
        "language.code": lang,
        "sort.by": "published_at",
        "sort.order": "desc",
        "per_page": "100",
        "fl": _FIELDS,
    }
    if config.NEWS_AGG_OPR_MIN > 0:
        params["source.rank.opr.min"] = str(config.NEWS_AGG_OPR_MIN)
    return params


def _keyword_params(keywords: str) -> dict:
    params = {
        "title": keywords,
        "sort.by": "published_at",
        "sort.order": "desc",
        "per_page": "100",
        "fl": _FIELDS,
    }
    if config.NEWS_AGG_OPR_MIN > 0:
        params["source.rank.opr.min"] = str(config.NEWS_AGG_OPR_MIN)
    return params


# ── Normalization ──

def _clean_summary(text: str) -> str:
    text = str(text or "")
    text = _PREVIEW_MARKER_RE.sub("", text)
    return html.unescape(text).strip()


def _clean_title(title: str) -> str:
    title = str(title or "")
    title = _PREVIEW_MARKER_RE.sub("", title)
    return html.unescape(title).strip()


def _is_junk(art: dict) -> bool:
    """True when an aggregated article looks like spam/deal-farm content."""
    if not config.NEWS_AGG_JUNK_FILTER:
        return False
    text = f"{art.get('title', '')} {art.get('description', '')}"
    return bool(_JUNK_RE.search(text))


def _normalize_article(art: dict, tag: str) -> dict:
    """Map an APITube article to the bot's news-dict schema (+ enrichment)."""
    title = _clean_title(art.get("title", ""))
    source = art.get("source", {})
    source_domain = source.get("domain") if isinstance(source, dict) else None
    published_at = art.get("published_at", "")

    item: dict = {
        "title": title,
        "summary": _clean_summary(art.get("description", ""))[:300],
        "link": art.get("href", ""),
        "source": source_domain or "APITube",
        "source_tag": tag,
        "published": published_at,
        "published_at": published_at,
    }

    sentiment = art.get("sentiment") or {}
    overall = sentiment.get("overall") if isinstance(sentiment, dict) else None
    if isinstance(overall, dict) and overall.get("polarity"):
        item["agg_sentiment"] = overall.get("polarity")
        item["agg_sentiment_score"] = overall.get("score")

    if isinstance(source, dict):
        opr = (source.get("rankings") or {}).get("opr")
        if isinstance(opr, (int, float)):
            item["opr"] = int(opr)

    if art.get("is_breaking"):
        item["is_breaking"] = True

    shares = art.get("shares")
    if isinstance(shares, dict) and isinstance(shares.get("total"), int):
        item["shares"] = shares["total"]

    entities = art.get("entities") or []
    normalized_entities = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        sent = e.get("sentiment") or {}
        normalized_entities.append({
            "name": e.get("name", ""),
            "polarity": sent.get("polarity") if isinstance(sent, dict) else None,
            "score": sent.get("score") if isinstance(sent, dict) else None,
        })
    if normalized_entities:
        item["entities"] = normalized_entities

    return item


# ── Category batching & tag inference ──

def _category_batches(tags: list[str]) -> list[tuple[str, tuple[str, ...]]]:
    """Return (language, iptc_code) requests needed for the given tags.

    APITube articles carry only their most specific `medtop:` subcategory
    codes (e.g. medtop:20000287 for personal finance) — never the parent
    group code used in the query — so grouping must follow the *requested*
    category, one request per distinct (language, category code). Tags that
    share a category code (finance/macro/global_finance) are fetched once.
    """
    needed: dict[tuple[str, str], None] = {}
    for tag in tags:
        q = CATEGORY_QUERIES.get(tag)
        if not q or q["kind"] != "category":
            continue
        for lang in q.get("languages", ("en",)):
            for code in q["categories"]:
                needed.setdefault((lang, code), None)
    return [(lang, (code,)) for (lang, code) in sorted(needed)]


def _science_or_tech(art: dict) -> str:
    text = f"{art.get('title', '')} {art.get('description', '')}".lower()
    if any(hint in text for hint in _SCIENCE_HINTS):
        return "science"
    return "tech"


def _infer_tag(art: dict, lang: str, codes: tuple[str, ...]) -> str:
    """Assign a bot source tag to an article from a category batch.

    The batch is fetched under a single requested category, so the article's
    group follows the requested code; headline hints only disambiguate within
    the group (tech vs science). Russian-language news is not indexed by
    APITube, hence all finance-group results map to ``global_finance``.
    """
    if config.APITUBE_CATEGORY_FINANCE in codes:
        return "global_finance"
    if config.APITUBE_CATEGORY_POLITICS in codes:
        return "politics"
    if config.APITUBE_CATEGORY_SCIENCE_TECH in codes:
        return _science_or_tech(art)
    return "global_finance"


# ── Caching ──

def _cache_key(kind: str, lang: str, params) -> str:
    return f"{kind}:{lang}:{params}"


def _get_cache(key: str) -> list[dict] | None:
    cached = _AGG_CACHE.get(key)
    if cached and time.time() - cached[0] < config.NEWS_AGG_CACHE_TTL:
        return cached[1]
    return None


def _set_cache(key: str, items: list[dict]) -> None:
    _AGG_CACHE[key] = (time.time(), items)


async def _get_or_fetch(key: str, fetcher) -> list[dict]:
    cached = _get_cache(key)
    if cached is not None:
        return cached
    try:
        items = await fetcher()
    except Exception as e:
        logger.warning(f"aggregated fetch ({key}) failed: {e}")
        if cached is not None:
            return cached
        return []
    _set_cache(key, items)
    return items


# ── Dedup (mirrors bot.finance._dedup_news) ──

def _dedup_key(title: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", title.lower())


def _dedup_news(all_news: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in all_news:
        key = _dedup_key(item.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ── Public API ──

async def fetch_aggregated(source_tags: list[str] | None = None) -> list[dict]:
    """Fetch news from the aggregator provider for the given bot source tags.

    Args:
        source_tags: List of category tags (e.g. ["finance", "macro"]).
                     None or empty = fetch from all aggregator-mapped tags.

    Returns:
        Deduplicated, normalized news dicts. Empty when APITube is disabled,
        fails, or returns nothing — RSS fetching continues regardless.
    """
    if not _enabled():
        return []

    tags = [t for t in (source_tags or list(CATEGORY_QUERIES)) if t in CATEGORY_QUERIES]
    news: list[dict] = []

    # Category batches (shared across tags, ≤3 IPTC codes per request).
    for lang, codes in _category_batches(tags):
        key = _cache_key("cat", lang, codes)
        batch = await _get_or_fetch(
            key, lambda lang=lang, codes=codes: _fetch_category_batch(lang, codes),
        )
        news.extend(batch)

    # Niche keyword queries (one request per tag).
    for tag in tags:
        q = CATEGORY_QUERIES[tag]
        if q["kind"] != "keywords":
            continue
        key = _cache_key("kw", tag, "")
        items = await _get_or_fetch(
            key, lambda tag=tag, q=q: _fetch_keyword_batch(tag, q["keywords"]),
        )
        news.extend(items)

    return _dedup_news(news)


async def _fetch_category_batch(lang: str, codes: tuple[str, ...]) -> list[dict]:
    articles = await _apitube_request(_category_params(codes, lang))
    items = []
    for art in articles:
        if not isinstance(art, dict) or not art.get("title") or _is_junk(art):
            continue
        tag = _infer_tag(art, lang, codes)
        if tag is None:
            continue
        items.append(_normalize_article(art, tag))
    return items


async def _fetch_keyword_batch(tag: str, keywords: str) -> list[dict]:
    articles = await _apitube_request(_keyword_params(keywords))
    items = []
    for art in articles:
        if not isinstance(art, dict) or not art.get("title") or _is_junk(art):
            continue
        items.append(_normalize_article(art, tag))
    return items
