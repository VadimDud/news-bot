"""Generate keyword-based filtering rules for a ticker via Gemini/DashScope.

Called ONCE when user adds a ticker. Result is stored in tracked_assets table.
"""

import json
import logging
import re

import httpx

from . import config

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
}

Инструкция к полям:
1. keywords: включи тикер, название компании на русском и английском, наименования ключевой продукции, дочерних компаний и ключевых топ-менеджеров. Минимум 8 слов.
2. positive_triggers: специфичные для этой отрасли/компании позитивные события. Минимум 5 триггеров.
3. negative_triggers: специфичные негативные события. Минимум 5 триггеров.
4. description: краткое описание для пользователя."""


def _parse_json_response(text: str) -> dict | None:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from asset analyzer: {text[:300]}")
        return None


async def _call_deepseek(ticker: str) -> dict | None:
    """Call DeepSeek API (OpenAI-compatible) to analyze a ticker."""
    if not config.DEEPSEEK_API_KEY:
        return None

    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    messages = [
        {"role": "system", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": f"Проанализируй финансовый актив: {ticker}"},
    ]
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={
                "model": config.DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 4096,
            }, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return _parse_json_response(text)
            else:
                logger.warning(f"DeepSeek HTTP {resp.status_code}: {resp.text[:200]}")
                return None
    except Exception as e:
        logger.warning(f"DeepSeek error: {e}")
        return None


async def _call_gemini(ticker: str) -> dict | None:
    """Call Gemini API to analyze a ticker."""
    if not config.GEMINI_API_KEY:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": f"Проанализируй финансовый актив: {ticker}\n\n{ANALYSIS_PROMPT}"}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
    }
    headers = {"Content-Type": "application/json", "X-goog-api-key": config.GEMINI_API_KEY}

    try:
        proxy = config.HTTP_PROXY or None
        async with httpx.AsyncClient(timeout=30, proxy=proxy) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return _parse_json_response(text)
            else:
                logger.warning(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
                return None
    except Exception as e:
        logger.warning(f"Gemini error: {e}")
        return None


async def _call_dashscope(ticker: str) -> dict | None:
    """Call DashScope (Qwen) as fallback."""
    if not config.DASHSCOPE_API_KEY:
        return None

    base_url = config.DASHSCOPE_BASE_URL.rstrip("/")
    messages = [
        {"role": "system", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": f"Проанализируй финансовый актив: {ticker}"},
    ]

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
                    "input": {"messages": messages},
                    "parameters": {"max_tokens": 1024, "temperature": 0.2},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("output", {}).get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    return _parse_json_response(text)
            return None
    except Exception as e:
        logger.warning(f"DashScope error for asset analysis: {e}")
        return None


async def analyze_ticker(ticker: str) -> dict | None:
    """Analyze a ticker and return keyword/filter rules.

    Returns dict with keys: ticker, company_name, keywords, positive_triggers,
    negative_triggers, description. Or None on failure.
    """
    result = await _call_deepseek(ticker)
    if not result:
        result = await _call_gemini(ticker)
    if not result:
        result = await _call_dashscope(ticker)

    if not result:
        # Fallback: generate minimal rules from ticker name
        logger.info(f"No AI available for {ticker}, using minimal fallback")
        result = {
            "ticker": ticker.upper(),
            "company_name": ticker.upper(),
            "keywords": [ticker.upper(), ticker.lower()],
            "positive_triggers": ["дивиденды", "рост", "прибыль", "рекорд", "апгрейд"],
            "negative_triggers": ["падение", "убыток", "санкции", "расследование", "дефолт"],
            "description": f"Финансовый актив {ticker}",
        }

    # Validate and normalize
    if not isinstance(result.get("keywords"), list):
        result["keywords"] = [ticker.upper()]
    if not isinstance(result.get("positive_triggers"), list):
        result["positive_triggers"] = ["дивиденды", "рост"]
    if not isinstance(result.get("negative_triggers"), list):
        result["negative_triggers"] = ["падение", "убыток"]

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
