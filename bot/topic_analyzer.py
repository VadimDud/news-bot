"""AI-powered topic analysis for channel keywords."""

import logging

from .ai_client import analyze

logger = logging.getLogger(__name__)

TOPIC_PROMPT = """Ты — финансовый аналитик и эксперт по новостным мониторингам. Твоя задача — помочь составить набор ключевых слов для отслеживания новостей по заданной теме.

Отвечай СТРОГО в формате JSON без дополнительного текста.

Доступные категории источников: finance (финансовые СМИ), macro (ЦБ, инфляция, ВВП), commodities (нефть, газ, металлы), tech (IT, стартапы), crypto (криптовалюты), politics (политика, санкции), global_finance (мировые рынки), science (наука), realty (недвижимость).

Формат ответа:
{
  "topic": "Название темы",
  "keywords": ["слово1", "слово2", ...],
  "positive_triggers": ["событие1", "событие2", ...],
  "negative_triggers": ["событие1", "событие2", ...],
  "related_tickers": ["TICKER1", "TICKER2", ...],
  "source_tags": ["tag1", "tag2", ...],
  "description": "Краткое описание темы для справки"
}"""

VALID_TAGS = {"finance", "macro", "commodities", "tech", "crypto", "politics", "global_finance", "science", "realty"}


async def analyze_topic(topic: str, keywords: list[str]) -> dict | None:
    """Analyze a topic and suggest expanded keywords, triggers, and related tickers."""
    user_message = (
        f"Тема: {topic}\n"
        f"Ключевые слова пользователя: {', '.join(keywords)}\n\n"
        f"Расширь набор ключевых слов и предложи триггеры для мониторинга новостей по этой теме."
    )
    result = await analyze(TOPIC_PROMPT, user_message, temperature=0.2, max_tokens=2048)

    if not result:
        logger.info(f"No AI available for topic analysis: {topic}")
        return None

    # Validate and normalize
    if not isinstance(result.get("keywords"), list):
        result["keywords"] = keywords
    if not isinstance(result.get("positive_triggers"), list):
        result["positive_triggers"] = []
    if not isinstance(result.get("negative_triggers"), list):
        result["negative_triggers"] = []
    if not isinstance(result.get("related_tickers"), list):
        result["related_tickers"] = []

    raw_tags = result.get("source_tags", [])
    if isinstance(raw_tags, list):
        result["source_tags"] = [t for t in raw_tags if t in VALID_TAGS]
    else:
        result["source_tags"] = []

    result["topic"] = result.get("topic", topic)
    result["description"] = result.get("description", "")

    logger.info(
        f"Topic analysis for '{topic}': "
        f"{len(result['keywords'])} keywords, "
        f"{len(result['positive_triggers'])} pos, "
        f"{len(result['negative_triggers'])} neg, "
        f"{len(result['related_tickers'])} tickers, "
        f"source_tags={result['source_tags']}"
    )
    return result
