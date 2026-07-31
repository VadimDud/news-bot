"""Topic classification and per-channel topic filtering.

Channels can be bound to one or more topics (e.g. "finance", "politics").
During keyword matching a news item whose text is clearly dominated by a
topic NOT present in the channel's topic list is rejected. This prevents
ambiguous financial keywords (e.g. "золото") from matching sports news
(gold medals) or political news.

Matching rules for indicator words:
  * short words (<= 4 chars) are matched as whole words (word boundaries);
  * longer words are matched as word prefixes, so a single pseudo-stem
    (e.g. "ставк") covers all inflections ("ставка", "ставки", "ставку").
  * multi-word phrases are matched as substrings of the lowercased text.
"""

import re

# Minimum number of topic-keyword hits required to treat a topic as
# "clearly present". Below this threshold no topic filtering happens, so
# news that only mentions a topic word in passing still passes through.
MIN_TOPIC_SIGNAL = 2

# Each topic: {name, name_en, keywords, parents}.
# `parents` receive the same hit count as their child topic (used for
# topic expansion, e.g. macro/commodities news is inherently financial).
TOPICS: dict[str, dict] = {
    "finance": {
        "name": "Финансы",
        "name_en": "Finance",
        "keywords": [
            "банк", "банке", "банки", "банка", "банков", "банковск",
            "биржа", "биржи", "бирже",
            "инвестици", "инвестор", "котировк",
            "прибыл", "выручк", "дивиденд", "облигаци",
            "капитал", "рынок", "рынке", "рынка",
            "рубль", "рубля", "рубли", "рублей",
            "доллар", "доллара", "доллары", "долларов", "евро",
            "валюта", "валютн", "фондов",
            "депозит", "кредит", "финансов", "финансист",
            "ликвидност", "доходност", "эмитент", "активы",
            "убыток", "ставк", "выплат", "доход",
            "ipo", "m&a", "market", "markets", "stock", "stocks",
            "investor", "investors", "profit",
            "revenue", "trading", "equity", "bonds", "bond",
        ],
    },
    "macro": {
        "name": "Макроэкономика",
        "name_en": "Macroeconomics",
        "parents": ["finance"],
        "keywords": [
            "инфляци", "ввп", "госдолг", "бюджет", "бюджетн",
            "минфин", "безработиц", "экономик", "рецесси",
            "профицит", "дефицит", "цб", "центробанк",
            "ключевая ставка", "ключевой ставки", "процентная ставка",
            "макроэкономи", "gdp", "inflation", "recession", "economy",
            "key rate",
        ],
    },
    "commodities": {
        "name": "Сырьё и энергия",
        "name_en": "Commodities & Energy",
        "parents": ["finance"],
        "keywords": [
            "нефть", "нефти", "нефтян", "нефте",
            "газ", "газа", "газу", "газом", "газов", "газовый",
            "уголь", "угля", "угле", "углем", "зерно", "зерна", "пшениц",
            "металл", "сырьё", "сырье", "опек", "opec",
            "баррель", "алюмини", "никель", "уран", "энергоносител",
            "oil", "gas", "energy", "commodit", "barrel", "wheat",
        ],
    },
    "crypto": {
        "name": "Криптовалюты",
        "name_en": "Cryptocurrency",
        "keywords": [
            "биткоин", "крипто", "блокчейн", "эфириум",
            "bitcoin", "blockchain", "ethereum", "btc", "eth",
            "токен", "token", "coin", "coins", "defi",
            "майнинг", "mining", "stablecoin", "альткоин", "altcoin",
        ],
    },
    "tech": {
        "name": "Технологии и IT",
        "name_en": "Tech & IT",
        "keywords": [
            "технолог", "программн", "разработчик", "стартап", "гаджет",
            "смартфон", "процессор", "робот", "чип", "чипы", "чипов",
            "интернет", "облачн", "кибер", "цифров", "ии",
            "искусственный интеллект", "нейросет", "машинное обучение",
            "software", "startup", "processor", "chip", "chips",
            "smartphone", "robot", "digital", "ai", "tech",
            "technology", "data", "cyber", "app", "apps",
        ],
    },
    "politics": {
        "name": "Политика",
        "name_en": "Politics",
        "keywords": [
            "политик", "президент", "правительств", "выбор",
            "парламент", "депутат", "госдума", "кремль", "минобороны",
            "министр", "губернатор", "партия", "государств", "переговор",
            "саммит", "голосовани", "избирательн", "указ", "послание",
            "закон", "реформа", "председатель", "спикер", "протест",
            "кабинет министров", "президент россии",
            "president", "government", "parliament", "election",
            "elections", "senate", "congress", "minister", "summit",
            "vote", "votes", "voting", "legislation", "reform",
        ],
    },
    "sanctions": {
        "name": "Санкции",
        "name_en": "Sanctions",
        "parents": ["politics"],
        "keywords": [
            "санкци", "санкционн", "эмбарго",
            "ценовой потолок", "заморозка активов", "черный список",
            "чёрный список", "ofac", "экспортные ограничения",
            "запрет поставок", "санкционные риски",
            "sanction", "sanctions", "sanctioned", "embargo",
            "blacklist", "export ban", "export control",
        ],
    },
    "sport": {
        "name": "Спорт",
        "name_en": "Sport",
        "keywords": [
            "спорт", "спортивн", "футбол", "хокке", "чемпионат",
            "чемпион", "матч", "матча", "матче", "матчей", "матчи",
            "олимпиад", "медал", "турнир", "сборн", "тренер",
            "стадион", "теннис", "баскетбол", "волейбол", "биатлон",
            "финал", "лига", "лиги", "лиге", "гол", "гола", "голы", "голу",
            "мяч", "мяча", "голкипер", "футболист", "спортсмен",
            "вратарь", "болельщик", "забил", "олимпийск",
            "sport", "sports", "football", "soccer", "hockey",
            "championship", "champion", "tournament",
            "olympic", "olympics", "olympiad", "medal", "medals",
            "tennis", "basketball", "volleyball", "league",
            "stadium", "soccer",
        ],
    },
    "science": {
        "name": "Наука",
        "name_en": "Science",
        "keywords": [
            "наук", "учён", "учен", "исследовани", "физик", "биолог",
            "химик", "лаборатори", "открыти", "телескоп", "геном",
            "квант", "космос", "космическ", "днк", "эксперимент",
            "астроном", "микробиолог",
            "science", "scientist", "research", "study", "experiment",
            "telescope", "genome", "quantum", "space", "dna",
            "astronom", "physics", "biology",
        ],
    },
    "realty": {
        "name": "Недвижимость",
        "name_en": "Real Estate",
        "keywords": [
            "недвижимост", "ипотек", "ипотечн", "жилищн",
            "строительств", "квартир", "новостройк", "застройщик",
            "аренд", "девелопер", "квадратный метр", "real estate",
            "realty", "mortgage", "housing", "apartment", "property",
            "construction", "rent",
        ],
    },
}


def _match(text: str, keyword: str) -> bool:
    """Check whether an indicator keyword is present in the lowercased text."""
    keyword = keyword.lower()
    if " " in keyword:
        return keyword in text
    escaped = re.escape(keyword)
    if len(keyword) <= 4:
        return re.search(rf"(?<!\w){escaped}(?!\w)", text) is not None
    return re.search(rf"(?<!\w){escaped}", text) is not None


def count_topics(text: str) -> dict[str, int]:
    """Count topic-keyword hits in text.

    Returns {topic_id: hits} including parent expansion (parents receive
    the same hit count as their child topics).
    """
    text = text.lower()
    counts: dict[str, int] = {}
    for topic_id, info in TOPICS.items():
        hits = sum(1 for kw in info["keywords"] if _match(text, kw))
        if hits:
            counts[topic_id] = counts.get(topic_id, 0) + hits
            for parent in info.get("parents", []):
                counts[parent] = counts.get(parent, 0) + hits
    return counts


def dominant_topics(counts: dict[str, int]) -> set[str]:
    """Return topics with the highest hit count, if the signal is strong.

    Returns an empty set when the text has no clear topic dominance.
    """
    if not counts:
        return set()
    max_hits = max(counts.values())
    if max_hits < MIN_TOPIC_SIGNAL:
        return set()
    return {tid for tid, hits in counts.items() if hits == max_hits}


def topic_filter_pass(counts: dict[str, int], channel_topics: list[str] | None) -> bool:
    """Decide whether news passes the topic filter of a channel.

    News is rejected only when a clearly dominant topic is entirely outside
    the channel's topic list. Weak/absent signals always pass through.
    """
    if not channel_topics:
        return True
    dom = dominant_topics(counts)
    if not dom:
        return True
    return bool(dom & set(channel_topics))


SOURCE_TAG_TOPICS = {
    "finance": "finance",
    "global_finance": "finance",
    "macro": "macro",
    "commodities": "commodities",
    "tech": "tech",
    "crypto": "crypto",
    "politics": "politics",
    "science": "science",
    "realty": "realty",
}


def infer_channel_topics(channel: dict) -> list[str]:
    """Derive topics for a channel from its source tags and ticker."""
    topics: set[str] = set()
    for tag in channel.get("source_tags") or []:
        if tag in SOURCE_TAG_TOPICS:
            topics.add(SOURCE_TAG_TOPICS[tag])
    if channel.get("ticker"):
        topics.add("finance")
    return sorted(topics)


def effective_topics(channel: dict) -> list[str]:
    """Return explicit channel topics, or infer them when unset."""
    explicit = channel.get("topics") or []
    if explicit:
        return [tid for tid in explicit if tid in TOPICS]
    return infer_channel_topics(channel)


def get_topics_display(lang: str = "ru") -> list[dict]:
    """Return [{id, name}] for all topics, localized."""
    result = []
    for topic_id, info in TOPICS.items():
        name = info["name_en"] if lang == "en" else info["name"]
        result.append({"id": topic_id, "name": name})
    return result
