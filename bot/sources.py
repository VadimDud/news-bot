"""Source catalog — RSS/API news sources grouped by topic category."""

SOURCES = {
    "finance": {
        "name": "Финансы",
        "name_en": "Finance",
        "description": "Основные финансовые и деловые СМИ",
        "feeds": [
            {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/news.xml", "type": "rss", "lang": "ru"},
            {"name": "Интерфакс", "url": "https://www.interfax.ru/rss.asp", "type": "rss", "lang": "ru"},
            {"name": "ТАСС", "url": "https://tass.ru/rss/v2.xml", "type": "rss", "lang": "ru"},
            {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss/news.xml", "type": "rss", "lang": "ru"},
        ],
    },
    "macro": {
        "name": "Макроэкономика",
        "name_en": "Macroeconomics",
        "description": "ЦБ, инфляция, ВВП, госдолг, бюджет",
        "feeds": [
            {"name": "ЦБ РФ", "url": "https://www.cbr.ru/rss/eventrss", "type": "rss", "lang": "ru"},
            {"name": "Росстат", "url": "https://rosstat.gov.ru/rss/news", "type": "rss", "lang": "ru"},
            {"name": "Минфин РФ", "url": "https://minfin.gov.ru/rss/news/", "type": "rss", "lang": "ru"},
        ],
    },
    "commodities": {
        "name": "Сырьё и энергия",
        "name_en": "Commodities & Energy",
        "description": "Нефть, газ, металлы, энергоносители",
        "feeds": [
            {"name": "OilPrice", "url": "https://oilprice.com/rss/main", "type": "rss", "lang": "en"},
            {"name": "Reuters Energy", "url": "https://www.reutersagency.com/feed/?taxonomy=category&post_type=best&best-sections=energy", "type": "rss", "lang": "en"},
        ],
    },
    "tech": {
        "name": "Технологии и IT",
        "name_en": "Tech & IT",
        "description": "IT, стартапы, цифровая экономика, гаджеты",
        "feeds": [
            {"name": "Habr", "url": "https://habr.com/ru/rss/all/all/", "type": "rss", "lang": "ru"},
            {"name": "VC.ru", "url": "https://vc.ru/rss/all", "type": "rss", "lang": "ru"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "type": "rss", "lang": "en"},
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "type": "rss", "lang": "en"},
        ],
    },
    "crypto": {
        "name": "Криптовалюты",
        "name_en": "Cryptocurrency",
        "description": "Биткоин, блокчейн, DeFi, крипторынок",
        "feeds": [
            {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "type": "rss", "lang": "en"},
            {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "type": "rss", "lang": "en"},
            {"name": "Bits.media", "url": "https://bits.media/rss/", "type": "rss", "lang": "ru"},
        ],
    },
    "politics": {
        "name": "Политика",
        "name_en": "Politics",
        "description": "Внутренняя и внешняя политика, санкции, регуляторика",
        "feeds": [
            {"name": "РИА Новости", "url": "https://ria.ru/export/rss2/archive/index.xml", "type": "rss", "lang": "ru"},
            {"name": "ТАСС Политика", "url": "https://tass.ru/rss/v2/politics.xml", "type": "rss", "lang": "ru"},
            {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "type": "rss", "lang": "en"},
        ],
    },
    "global_finance": {
        "name": "Мировые финансы",
        "name_en": "Global Finance",
        "description": "Глобальные рынки, M&A, отчёты, макро США/ЕС",
        "feeds": [
            {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?taxonomy=category&post_type=best&best-sections=business", "type": "rss", "lang": "en"},
            {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "type": "rss", "lang": "en"},
        ],
    },
    "science": {
        "name": "Наука и открытия",
        "name_en": "Science",
        "description": "Научные открытия, исследования, инновации",
        "feeds": [
            {"name": "N+1", "url": "https://nplus1.ru/rss", "type": "rss", "lang": "ru"},
            {"name": "Scientific American", "url": "https://www.scientificamerican.com/feed/rss/", "type": "rss", "lang": "en"},
        ],
    },
    "realty": {
        "name": "Недвижимость",
        "name_en": "Real Estate",
        "description": "Рынок недвижимости, ипотека, строительство",
        "feeds": [
            {"name": "IRN.ru", "url": "https://www.irn.ru/news/rss/", "type": "rss", "lang": "ru"},
            {"name": "Домклик", "url": "https://blog.domclick.ru/rss", "type": "rss", "lang": "ru"},
        ],
    },
}

_ALL_SOURCES_CACHE: list[dict] | None = None


def get_all_sources() -> list[dict]:
    """Return flat list of all source dicts with tag attached."""
    global _ALL_SOURCES_CACHE
    if _ALL_SOURCES_CACHE is None:
        _ALL_SOURCES_CACHE = []
        for tag, cat in SOURCES.items():
            for feed in cat["feeds"]:
                feed["tag"] = tag
                _ALL_SOURCES_CACHE.append(feed)
    return _ALL_SOURCES_CACHE


def get_sources_by_tags(tags: list[str]) -> list[dict]:
    """Return sources matching the given tags. Empty tags = all sources."""
    if not tags:
        return get_all_sources()
    all_sources = get_all_sources()
    return [s for s in all_sources if s["tag"] in tags]


def get_source_tags_display(lang: str = "ru") -> list[dict]:
    """Return list of {id, name, description} for each source category."""
    result = []
    for tag, cat in SOURCES.items():
        name = cat["name"] if lang == "ru" else cat.get("name_en", cat["name"])
        result.append({
            "id": tag,
            "name": name,
            "description": cat["description"],
            "count": len(cat["feeds"]),
        })
    return result
