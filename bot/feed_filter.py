"""Stage-0 feed relevance filter.

Drops clearly irrelevant news (war/attacks, accidents, crime, sport,
weather, showbiz, human-interest) right after fetching, so the news pool
fed into the matching pipeline contains mostly finance-relevant items.

The filter is deliberately conservative: an item is dropped ONLY when it
contains an irrelevance signal AND carries no financial marker word AND
(optionally) no keyword of the active channels. Everything ambiguous is kept
(ambiguous keyword matches are handled downstream by the topic filter and
AI relevance verification).
"""

import re

# Finance-like categories whose streams are cleaned by this filter.
FILTER_TAGS = frozenset({"finance", "macro", "commodities", "global_finance"})

_WORD_RE = re.compile(r"[а-яёa-z0-9]+")

# Stem prefixes (Russian/English) of clearly irrelevant topics. A text word
# matching the START of any stem counts as an irrelevance signal, so
# inflections ("матч"/"матчи", "атака"/"атаковал") are covered.
IRRELEVANT_STEMS = (
    "бпла", "дрон", "атак", "всу", "вкл", "минобороны",
    "обстрел", "сбил", "погиб", "жертв", "убит", "ранен",
    "пожар", "взрыв", "дтп", "авари", "крушен", "катастроф",
    "теракт", "диверс", "саботаж",
    "чемпионат", "чемпион", "матч", "турнир", "олимпиад", "медал",
    "футбол", "хокке", "спортсмен", "погод", "мороз", "жара", "циклон",
    "ураган", "наводнен", "землетрясен", "звезд", "звёзд", "актрис",
    "певиц", "телеведущ", "светск", "уголовн", "преступлен", "криминал",
    "задержан", "приговор", "осужден", "курьез", "любопытн",
)

# Financial vocabulary stems that override the irrelevance signal.
FINANCE_STEMS = (
    "банк", "акци", "котировк", "бирж", "курс", "валют", "рубл",
    "доллар", "евро", "юан",
    "нефт", "газ", "стал", "угл", "золот", "металл", "сырь", "баррель",
    "ставк", "инфляци", "дефляци", "ввп", "бюджет", "минфин", "цб", "центробанк",
    "инвестор", "эмитент", "облигаци", "дивиденд", "депозит", "кредит",
    "прибыл", "выручк", "доход", "убыт", "ликвидност", "рентабельн",
    "санкци", "эмбарго", "госдолг", "безработиц", "экономик",
    "рынок", "рынка", "ipo", "bond", "stock", "investor", "market",
    "equit", "revenue", "trading", "inflation", "oil", "gas", "gold",
    "energ", "commodit", "bitcoin", "ethereum", "crypto",
)


def _has_stem(text: str, stems: tuple[str, ...]) -> bool:
    """True when any whitespace-separated word starts with one of the stems."""
    for word in _WORD_RE.findall(text.lower()):
        for stem in stems:
            if word.startswith(stem):
                return True
    return False


def _has_irrelevance(text: str) -> bool:
    return _has_stem(text, IRRELEVANT_STEMS)


def _has_finance_marker(text: str) -> bool:
    return _has_stem(text, FINANCE_STEMS)


def should_keep(
    title: str,
    summary: str,
    tags: list[str] | None = None,
    keep_keywords: list[str] | None = None,
) -> bool:
    """Return True to keep the news item, False to drop it as irrelevant.

    tags: the source tags being fetched (None/empty = all categories).
          Filtering only applies when a finance-like category is involved.
    keep_keywords: optional channel keywords that always protect an item
          (e.g. an asset name appearing in a war headline).
    """
    if tags and FILTER_TAGS.isdisjoint(tags):
        return True

    combined = f"{title} {summary}".lower()
    if not _has_irrelevance(combined):
        return True
    if _has_finance_marker(combined):
        return True
    if keep_keywords:
        for kw in keep_keywords:
            kw = kw.lower().strip()
            if len(kw) >= 2 and kw in combined:
                return True
    return False
