"""Thesis Validation — LLM-валидация тезиса сделки.

По мотивам marian2js/trading-skills/thesis-validation.

Работает ТОЛЬКО в ручном режиме (дашборд /api/pretrade):
- Промпт строится по контексту сделки;
- DeepSeek оценивает чёткость тезиса, наличие доказательств, инвалидационные условия;
- Возвращает JSON-вердикт + список недостающих фактов.

В автоматическом гейте НЕ участвует (чтобы не добавлять задержку и
зависимость от API на каждый вход).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from .. import config
from .context import TradeContext

logger = logging.getLogger("moex_trader.skills.thesis")

_THESIS_PROMPT = (
    "Ты — финансовый аналитик. Оцени тезис для сделки по акции {ticker}.\n\n"
    "Тезис: {thesis}\n"
    "Направление: {direction}\n"
    "Таймфрейм: {timeframe}\n"
    "Цена входа: {entry}\n"
    "Стоп-лосс: {stop}\n"
    "Тейк-профит: {target}\n"
    "Рыночный контекст: {regime}\n\n"
    "Оцени:\n"
    "1. verdict: 'ready' (тезис чёткий, доказательства есть, инвалидация ясна), "
    "'unclear' (тезис есть, но доказательства/инвалидация неясны), "
    "'not_ready' (тезис слабый или не подтверждён фактами).\n"
    "2. claim_clarity: float 0.0-1.0 — насколько чётко сформулирован тезис.\n"
    "3. evidence_quality: float 0.0-1.0 — качество доступных доказательств.\n"
    "4. invalidation_clear: bool — известно ли условие инвалидации (где тезис ломается).\n"
    "5. missing: list[str] — какие факты/данные нужны для усиления тезиса.\n"
    "6. risk: str — основной риск сделки.\n\n"
    "Ответь ТОЛЬКО JSON: {{\"verdict\": \"...\", \"claim_clarity\": 0.0, "
    "\"evidence_quality\": 0.0, \"invalidation_clear\": false, "
    "\"missing\": [\"...\"], \"risk\": \"...\"}}"
)


@dataclass
class ThesisResult:
    """Результат LLM-валидации тезиса."""

    verdict: str  # "ready" | "unclear" | "not_ready"
    claim_clarity: float  # 0.0 - 1.0
    evidence_quality: float  # 0.0 - 1.0
    invalidation_clear: bool
    missing: list[str] = field(default_factory=list)
    risk: str = ""
    raw_response: str = ""
    error: str = ""


async def validate_thesis(
    ctx: TradeContext,
    thesis_text: str = "",
) -> ThesisResult:
    """Валидировать тезис сделки через LLM (DeepSeek).

    Вызывается только в ручном режиме из дашборда.
    Если API недоступен — возвращает 'unclear' с ошибкой.
    """
    if not config.DEEPSEEK_API_KEY:
        return ThesisResult(
            verdict="unclear",
            claim_clarity=0,
            evidence_quality=0,
            invalidation_clear=False,
            error="DEEPSEEK_API_KEY не задан",
        )

    if not thesis_text:
        return ThesisResult(
            verdict="unclear",
            claim_clarity=0,
            evidence_quality=0,
            invalidation_clear=False,
            error="Тезис не задан",
        )

    prompt = _THESIS_PROMPT.format(
        ticker=ctx.ticker,
        thesis=thesis_text,
        direction=ctx.direction or "long",
        timeframe=ctx.timeframe or "swing",
        entry=ctx.entry,
        stop=ctx.stop or "не задан",
        target=ctx.target or "не задан",
        regime=ctx.regime or "не определён",
    )

    try:
        result = await _call_deepseek_thesis(prompt)
        if result and "verdict" in result:
            verdict = result["verdict"]
            if verdict not in ("ready", "unclear", "not_ready"):
                verdict = "unclear"
            return ThesisResult(
                verdict=verdict,
                claim_clarity=float(result.get("claim_clarity", 0)),
                evidence_quality=float(result.get("evidence_quality", 0)),
                invalidation_clear=bool(result.get("invalidation_clear", False)),
                missing=result.get("missing", []),
                risk=result.get("risk", ""),
                raw_response=json.dumps(result, ensure_ascii=False),
            )
    except Exception as e:
        logger.warning("Thesis validation failed for %s: %s", ctx.ticker, e)
        return ThesisResult(
            verdict="unclear",
            claim_clarity=0,
            evidence_quality=0,
            invalidation_clear=False,
            error=str(e),
        )

    return ThesisResult(
        verdict="unclear",
        claim_clarity=0,
        evidence_quality=0,
        invalidation_clear=False,
        error="Пустой ответ от LLM",
    )


async def _call_deepseek_thesis(prompt: str) -> dict | None:
    """Вызов DeepSeek для валидации тезиса."""
    import httpx

    from ..secrets_guard import sanitize_prompt

    safe_prompt = sanitize_prompt(prompt)

    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30, proxy=None) as client:
        resp = await client.post(
            url,
            json={
                "model": config.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты финансовый аналитик. Отвечай ТОЛЬКО JSON."},
                    {"role": "user", "content": safe_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 400,
            },
            headers=headers,
        )
        if resp.status_code != 200:
            logger.warning("DeepSeek thesis API error %d: %s", resp.status_code, resp.text[:200])
            return None
        text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        # Parse JSON (strip markdown fences if present)
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        return json.loads(text.strip())
