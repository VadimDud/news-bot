"""Generate keyword-based filtering rules for a ticker via AI."""

import logging

from .ai_client import analyze

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Ты — главный финансовый аналитик. Твоя задача — составить словарь ключевых слов и критериев оценки новостей для заданного финансового актива или компании.

Отвечай СТРОГО в формате JSON без дополнительного текста.

Формат ответа:
{
  "ticker": "ОФИЦИАЛЬНЫЙ_ТИКЕР",
  "company_name": "Название компании на русском",
  "keywords": ["слово1", "слово2", "синоним1", "продукция/дочка"],
  "positive_triggers": ["дивиденды", "байбэк", "рост прибыли", "новое месторождение"],
  "negative_triggers": ["санкции", "допэмиссия", "авария", "падение выручки", "суд"],
  "description": "Краткое описание бизнеса компании (1-2 предложения) для справки пользователю."
}"""

_FALLBACK_POSITIVE = ["дивиденды", "рост", "прибыль", "рекорд", "апгрейд"]
_FALLBACK_NEGATIVE = ["падение", "убыток", "санкции", "расследование", "дефолт"]


async def analyze_ticker(ticker: str) -> dict | None:
    """Analyze a ticker and return keyword/filter rules."""
    result = await analyze(
        ANALYSIS_PROMPT,
        f"Проанализируй финансовый актив: {ticker}",
        temperature=0.2,
        max_tokens=4096,
    )

    if not result:
        logger.info(f"No AI available for {ticker}, using minimal fallback")
        result = {
            "ticker": ticker.upper(),
            "company_name": ticker.upper(),
            "keywords": [ticker.upper(), ticker.lower()],
            "positive_triggers": _FALLBACK_POSITIVE,
            "negative_triggers": _FALLBACK_NEGATIVE,
            "description": f"Финансовый актив {ticker}",
        }

    if not isinstance(result.get("keywords"), list):
        result["keywords"] = [ticker.upper()]
    if not isinstance(result.get("positive_triggers"), list):
        result["positive_triggers"] = _FALLBACK_POSITIVE
    if not isinstance(result.get("negative_triggers"), list):
        result["negative_triggers"] = _FALLBACK_NEGATIVE

    result["ticker"] = result.get("ticker", ticker).upper()
    result["company_name"] = result.get("company_name", ticker)
    result["description"] = result.get("description", "")

    logger.info(
        f"Asset analysis for {result['ticker']}: "
        f"{len(result['keywords'])} keywords, "
        f"{len(result['positive_triggers'])} pos, "
        f"{len(result['negative_triggers'])} neg"
    )
    return result
