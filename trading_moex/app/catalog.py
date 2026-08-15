"""Каталог ликвидных тикеров MOEX для выбора в веб-дашборде.

Практический список акций (TQBR) с названиями эмитентов. Вручную можно
добавить любой инструмент — каталог лишь упрощает выбор.
"""

AVAILABLE_TICKERS: list[dict[str, str]] = [
    {"ticker": "SBER", "name": "Сбер"},
    {"ticker": "SBERP", "name": "Сбер (прив.)"},
    {"ticker": "LKOH", "name": "Лукойл"},
    {"ticker": "GAZP", "name": "Газпром"},
    {"ticker": "ROSN", "name": "Роснефть"},
    {"ticker": "TATN", "name": "Татнефть"},
    {"ticker": "TATNP", "name": "Татнефть (прив.)"},
    {"ticker": "GMKN", "name": "Норникель"},
    {"ticker": "NLMK", "name": "НЛМК"},
    {"ticker": "SNGS", "name": "Сургутнефтегаз"},
    {"ticker": "SNGSP", "name": "Сургутнефтегаз (прив.)"},
    {"ticker": "CHMF", "name": "Северсталь"},
    {"ticker": "PLZL", "name": "Полюс"},
    {"ticker": "MGNT", "name": "Магнит"},
    {"ticker": "MAGN", "name": "ММК"},
    {"ticker": "MTSS", "name": "МТС"},
    {"ticker": "NVTK", "name": "Новатэк"},
    {"ticker": "VTBR", "name": "ВТБ"},
    {"ticker": "AFKS", "name": "АФК Система"},
    {"ticker": "ALRS", "name": "Алроса"},
    {"ticker": "ASTR", "name": "Астра"},
    {"ticker": "CBOM", "name": "МКБ"},
    {"ticker": "ENPG", "name": "Эн+ Групп"},
    {"ticker": "FIVE", "name": "X5 Group"},
    {"ticker": "GLTR", "name": "Globaltrans"},
    {"ticker": "HYDR", "name": "РусГидро"},
    {"ticker": "IRAO", "name": "Интер РАО"},
    {"ticker": "MOEX", "name": "Московская биржа"},
    {"ticker": "OZON", "name": "Ozon"},
    {"ticker": "PHOR", "name": "Фосагро"},
    {"ticker": "PIKK", "name": "ПИК"},
    {"ticker": "RUAL", "name": "РУСАЛ"},
    {"ticker": "SGZH", "name": "Селигдар"},
    {"ticker": "SMLT", "name": "Самолёт"},
    {"ticker": "TCSG", "name": "Т-Технологии"},
    {"ticker": "TRMK", "name": "ТМК"},
    {"ticker": "VKCO", "name": "VK"},
    {"ticker": "YDEX", "name": "Яндекс (МКПАО)"},
    {"ticker": "AFLT", "name": "Аэрофлот"},
    {"ticker": "BANE", "name": "Башнефть"},
    {"ticker": "BANEP", "name": "Башнефть (прив.)"},
    {"ticker": "RTKM", "name": "Ростелеком"},
    {"ticker": "RTKMP", "name": "Ростелеком (прив.)"},
    {"ticker": "FEES", "name": "ФСК Россети"},
    {"ticker": "LENT", "name": "Лента"},
    {"ticker": "POSS", "name": "Positive Technologies"},
    {"ticker": "SLEN", "name": "Сегежа"},
    {"ticker": "TTLK", "name": "Транснефть"},
    {"ticker": "VSMO", "name": "ВСМПО-Ависма"},
    {"ticker": "MTLR", "name": "Мечел"},
    {"ticker": "MTLRP", "name": "Мечел (прив.)"},
    {"ticker": "RENI", "name": "Ренессанс Страхование"},
    {"ticker": "CIAN", "name": "Циан"},
    {"ticker": "MVID", "name": "М.Видео"},
    {"ticker": "AKRN", "name": "Акрон"},
    {"ticker": "SFTL", "name": "Softline"},
    {"ticker": "FLOT", "name": "Совкомфлот"},
    {"ticker": "MDMG", "name": "МД Медикал Групп"},
    {"ticker": "EUTR", "name": "Euromed"},
]

AVAILABLE_TICKER_KEYS: set[str] = {t["ticker"] for t in AVAILABLE_TICKERS}


def find(ticker: str) -> dict[str, str] | None:
    """Найти инструмент в каталоге по коду."""
    for item in AVAILABLE_TICKERS:
        if item["ticker"] == ticker.upper():
            return item
    return None
