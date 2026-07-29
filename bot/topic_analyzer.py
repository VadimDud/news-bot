"""AI-powered topic analysis for channel keywords.

Called when user creates a channel or requests keyword expansion.
Suggests additional keywords, positive/negative triggers based on the topic.
"""

import json
import logging
import re

import httpx

from . import config
from .retry_utils import async_retry

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
}

Инструкция к полям:
1. keywords: расширь список ключевых слов. Включи синонимы, аббревиатуры, смежные понятия. Минимум 10 слов.
2. positive_triggers: события, которые позитивно влияют на данную тему. Минимум 5.
3. negative_triggers: события, которые негативно влияют. Минимум 5.
4. related_tickers: тикеры компаний, наиболее связанных с темой (макс 5).
5. source_tags: какие категории источников сканировать для этой темы (1-4 категории).
6. description: краткое описание темы (1 предложение)."""


def _parse_json_response(text: str) -> dict | None:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from topic analyzer: {text[:300]}")
        return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_deepseek(topic: str, keywords: list[str]) -> dict | None:
    if not config.DEEPSEEK_API_KEY:
        return None

    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    user_msg = (
        f"Тема: {topic}\n"
        f"Ключевые слова пользователя: {', '.join(keywords)}\n\n"
        f"Расширь набор ключевых слов и предложи триггеры для мониторинга новостей по этой теме."
    )
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={
                "model": config.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": TOPIC_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
                "max_tokens": 2048,
            }, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return _parse_json_response(text)
            else:
                logger.warning(f"DeepSeek HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"DeepSeek error: {e}")
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_gemini(topic: str, keywords: list[str]) -> dict | None:
    if not config.GEMINI_API_KEY:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    user_msg = (
        f"Тема: {topic}\n"
        f"Ключевые слова пользователя: {', '.join(keywords)}\n\n"
        f"Расширь набор ключевых слов и предложи триггеры для мониторинга новостей по этой теме.\n\n"
        f"{TOPIC_PROMPT}"
    )
    headers = {"Content-Type": "application/json", "X-goog-api-key": config.GEMINI_API_KEY}

    try:
        proxy = config.HTTP_PROXY or None
        async with httpx.AsyncClient(timeout=30, proxy=proxy) as client:
            resp = await client.post(url, json={
                "contents": [{"parts": [{"text": user_msg}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
            }, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return _parse_json_response(text)
    except Exception as e:
        logger.warning(f"Gemini error: {e}")
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_dashscope(topic: str, keywords: list[str]) -> dict | None:
    if not config.DASHSCOPE_API_KEY:
        return None

    base_url = config.DASHSCOPE_BASE_URL.rstrip("/")
    user_msg = (
        f"Тема: {topic}\n"
        f"Ключевые слова пользователя: {', '.join(keywords)}\n\n"
        f"Расширь набор ключевых слов и предложи триггеры для мониторинга новостей по этой теме."
    )

    try:
        proxy = config.HTTP_PROXY or None
        async with httpx.AsyncClient(timeout=30, proxy=proxy) as client:
            resp = await client.post(
                f"{base_url}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.DASHSCOPE_MODEL,
                    "input": {"messages": [
                        {"role": "system", "content": TOPIC_PROMPT},
                        {"role": "user", "content": user_msg},
                    ]},
                    "parameters": {"max_tokens": 2048, "temperature": 0.2},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("output", {}).get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    return _parse_json_response(text)
    except Exception as e:
        logger.warning(f"DashScope error: {e}")
    return None


async def analyze_topic(topic: str, keywords: list[str]) -> dict | None:
    """Analyze a topic and suggest expanded keywords, triggers, and related tickers.

    Returns dict with: topic, keywords, positive_triggers, negative_triggers,
    related_tickers, source_tags, description. Or None on failure.
    """
    result = await _call_deepseek(topic, keywords)
    if not result:
        result = await _call_gemini(topic, keywords)
    if not result:
        result = await _call_dashscope(topic, keywords)

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

    # Validate source_tags against known categories
    valid_tags = {"finance", "macro", "commodities", "tech", "crypto", "politics", "global_finance", "science", "realty"}
    raw_tags = result.get("source_tags", [])
    if isinstance(raw_tags, list):
        result["source_tags"] = [t for t in raw_tags if t in valid_tags]
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
