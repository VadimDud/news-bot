"""Unified AI client for DeepSeek, Gemini, and DashScope providers.

Each provider implements the same interface. Call analyze() to try
providers in priority order (DeepSeek -> Gemini -> DashScope).
"""

from collections.abc import Callable
import json
import logging
import re

import httpx

from . import config
from .retry_utils import async_retry

logger = logging.getLogger(__name__)


def _parse_json(text: str) -> dict | None:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_deepseek(system_prompt: str, user_message: str,
                         temperature: float = 0.2, max_tokens: int = 4096,
                         timeout: int = 30) -> str | None:
    if not config.DEEPSEEK_API_KEY:
        return None
    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
        resp = await client.post(url, json={
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.warning("DeepSeek API error %d: %s", resp.status_code, resp.text[:200])
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_gemini(system_prompt: str, user_message: str,
                       temperature: float = 0.2, max_tokens: int = 4096,
                       timeout: int = 30) -> str | None:
    if not config.GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "X-goog-api-key": config.GEMINI_API_KEY}
    prompt = f"{system_prompt}\n\n{user_message}"
    proxy = config.HTTP_PROXY or None
    async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
        resp = await client.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }, headers=headers)
        if resp.status_code == 200:
            parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "") if parts else None
        logger.warning("Gemini API error %d: %s", resp.status_code, resp.text[:200])
    return None


@async_retry(max_retries=2, base_delay=1.0)
async def _call_dashscope(system_prompt: str, user_message: str,
                          temperature: float = 0.2, max_tokens: int = 4096,
                          timeout: int = 30) -> str | None:
    if not config.DASHSCOPE_API_KEY:
        return None
    base_url = config.DASHSCOPE_BASE_URL.rstrip("/")
    proxy = config.HTTP_PROXY or None
    async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
        resp = await client.post(
            f"{base_url}/services/aigc/text-generation/generation",
            headers={
                "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.DASHSCOPE_MODEL,
                "input": {"messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]},
                "parameters": {"max_tokens": max_tokens, "temperature": temperature},
            },
        )
        if resp.status_code == 200:
            choices = resp.json().get("output", {}).get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        logger.warning("DashScope API error %d: %s", resp.status_code, resp.text[:200])
    return None


_AVAILABLE_PROVIDERS: dict[str, Callable] = {
    "deepseek": _call_deepseek,
    "gemini": _call_gemini,
    "dashscope": _call_dashscope,
}


def _build_providers() -> list[tuple[str, Callable]]:
    default = config.DEFAULT_AGENT
    ordered = [default] + [p for p in _AVAILABLE_PROVIDERS if p != default]
    return [(name, _AVAILABLE_PROVIDERS[name]) for name in ordered
            if name in _AVAILABLE_PROVIDERS]


_PROVIDERS = _build_providers()


async def analyze(system_prompt: str, user_message: str, *,
                  temperature: float = 0.2, max_tokens: int = 4096,
                  parse_json: bool = True,
                  timeout: int = 30) -> dict | str | None:
    """Try each AI provider, starting with DEFAULT_AGENT.

    Args:
        system_prompt: System-level instructions.
        user_message: User's request.
        temperature: LLM temperature.
        max_tokens: Max output tokens.
        parse_json: If True, parse response as JSON and return dict.
                    If False, return raw text or None.
        timeout: HTTP timeout per provider call in seconds.

    Returns:
        Parsed dict, raw string, or None if all providers failed.
    """
    for name, provider in _PROVIDERS:
        text = await provider(system_prompt, user_message, temperature, max_tokens, timeout=timeout)
        if not text:
            continue
        if parse_json:
            parsed = _parse_json(text)
            if parsed:
                return parsed
            logger.warning(f"{name}: returned invalid JSON, trying next")
        else:
            return text
    return None
