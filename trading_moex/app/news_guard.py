"""News Guard: AI-powered news severity scoring + user overrides.

Проверяет, есть ли свежие негативные новости по тикеру, перед входом
в позицию. Три уровня защиты:

1. **User overrides** — ручные решения на веб-странице /news
2. **AI severity** — нейросеть оценивает новость от -1.0 до +1.0
3. **Bot sentiment** — sentiment из bot.db (POSITIVE/NEGATIVE/NEUTRAL)

Блокировка срабатывает если:
- Пользователь пометил новость как "block", ИЛИ
- Средний severity < -0.5 И количество NEGATIVE >= порога
"""

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from . import config
from . import storage

logger = logging.getLogger("moex_trader.news_guard")

# ── AI severity scoring ──────────────────────────────────────────────────────

_SEVERITY_PROMPT = (
    "Ты — финансовый аналитик. Оцени влияние новости на акцию {ticker} (Мосбиржа).\n\n"
    "Новость: {title}\n"
    "Суть: {summary}\n\n"
    "Оцени:\n"
    "1. severity: число от -1.0 (катастрофа — дефолт, банкротство, санкции, "
    "обвал прибыли) до +1.0 (суперпозитив — рекордная прибыль, мажорный "
    "апгрейд, дивиденды выше ожиданий). 0.0 = нейтрально/не влияет на цену.\n"
    "2. reason: краткое объяснение (1 предложение на русском).\n\n"
    "Ответь ТОЛЬКО JSON: {{\"severity\": 0.0, \"reason\": \"...\"}}"
)


def _hash_title(title: str) -> str:
    """Content hash для дедупликации (совместим с bot.db news.content_hash)."""
    normalized = title.lower().strip()
    sig = [0] * 4
    seeds = [b'\x01', b'\x02', b'\x03', b'\x04']
    for i in range(len(normalized) - 2):
        shingle = normalized[i:i + 3]
        for j, seed in enumerate(seeds):
            h = hashlib.sha256(seed + shingle.encode()).digest()[:8]
            val = int.from_bytes(h, 'big')
            if val < sig[j] or sig[j] == 0:
                sig[j] = val
    return ''.join(f'{s:016x}' for s in sig)


async def ai_severity(title: str, summary: str, ticker: str) -> dict:
    """Нейросеть оценивает новость.

    Возвращает: {"severity": float (-1..+1), "reason": str}
    Falls back to rule-based severity если AI недоступен.
    """
    if not config.NEWS_AI_ENABLED or not config.DEEPSEEK_API_KEY:
        return _rule_based_severity(title, summary)

    prompt = _SEVERITY_PROMPT.format(
        ticker=ticker, title=title, summary=(summary or title)[:500],
    )

    try:
        result = await _call_deepseek_severity(prompt)
        if result and "severity" in result:
            severity = float(result["severity"])
            severity = max(-1.0, min(1.0, severity))
            reason = str(result.get("reason", ""))[:500]
            return {"severity": severity, "reason": reason}
    except Exception as e:
        logger.warning("AI severity failed for %s: %s", ticker, e)

    return _rule_based_severity(title, summary)


async def _call_deepseek_severity(prompt: str) -> dict | None:
    """Direct DeepSeek call for severity scoring (bot.ai_client is async)."""
    import httpx

    url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30, proxy=None) as client:
        resp = await client.post(url, json={
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "Ты финансовый аналитик. Отвечай ТОЛЬКО JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 200,
        }, headers=headers)
        if resp.status_code != 200:
            logger.warning("DeepSeek severity API error %d: %s", resp.status_code, resp.text[:200])
            return None
        text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        # Parse JSON (strip markdown fences if present)
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        return json.loads(text.strip())


def _rule_based_severity(title: str, summary: str) -> dict:
    """Rule-based severity fallback без AI."""
    combined = (title + " " + (summary or "")).lower()

    # Катастрофические негативные
    catastrophic = ["дефолт", "банкротств", "санкци", "эმбарго", "конфискаци",
                    "расследовани", "мошенничеств", "уголовн", "отстранен",
                    "приостановк", "отзыв лицензи"]
    severe_neg = ["убыток", "падение", "снижение прибыли", "отток клиентов",
                  "суд", "штраф", "рекурсия", "снижение выручки"]
    mild_neg = ["негатив", "риск", "тревог", "сомнени"]
    mild_pos = ["рост", "прибыль", "дивиденды", "апгрейд", "рекорд"]
    strong_pos = ["рекордная прибыль", "мажорн", "супер", "прорыв"]

    neg_score = 0
    pos_score = 0

    for kw in catastrophic:
        if kw in combined:
            neg_score += 3
    for kw in severe_neg:
        if kw in combined:
            neg_score += 2
    for kw in mild_neg:
        if kw in combined:
            neg_score += 1
    for kw in strong_pos:
        if kw in combined:
            pos_score += 3
    for kw in mild_pos:
        if kw in combined:
            pos_score += 1

    if neg_score > pos_score:
        severity = max(-1.0, -0.3 * neg_score)
        reason = f"Найдены негативные триггеры (score={neg_score})"
    elif pos_score > neg_score:
        severity = min(1.0, 0.3 * pos_score)
        reason = f"Найдены позитивные триггеры (score={pos_score})"
    else:
        severity = 0.0
        reason = "Нейтральная новость"

    return {"severity": severity, "reason": reason}


# ── News Guard: main check ───────────────────────────────────────────────────

class NewsGuard:
    """Проверяет, нужно ли блокировать вход из-за негативных новостей."""

    def __init__(self, lookback_hours: int = 48, max_negative: int = 2,
                 severity_threshold: float = -0.5):
        self._lookback = lookback_hours
        self._max_neg = max_negative
        self._severity_threshold = severity_threshold

    def is_blocked(self, ticker: str, dt: datetime | None = None) -> tuple[bool, str]:
        """Проверяет, нужно ли блокировать вход.

        Returns: (blocked: bool, reason: str)
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        # 1) User overrides — приоритет
        override = storage.get_user_overrides(ticker)
        ignored_hashes = set()
        for o in override:
            if o["action"] == "block":
                return True, f"Пользователь заблокировал: {o.get('reason', '')}"
            if o["action"] == "ignore":
                ignored_hashes.add(o["content_hash"])

        # 2) Загружаем sentiment из кэша
        since = (dt - timedelta(hours=self._lookback)).isoformat()
        cached = storage.get_cached_sentiments(ticker, since_iso=since)

        if not cached:
            return False, ""

        # 3) Считаем негативные (исключая news с user override "ignore")
        negative_count = 0
        severity_sum = 0.0
        severity_count = 0
        reasons = []

        for item in cached:
            ch = item.get("content_hash", "")
            if ch in ignored_hashes:
                continue  # пользователь игнорирует эту новость

            impact = (item.get("impact") or "").upper()
            severity = item.get("severity")

            if impact == "NEGATIVE" or (severity is not None and severity < -0.3):
                negative_count += 1
                if severity is not None:
                    severity_sum += severity
                    severity_count += 1
                    if item.get("reason"):
                        reasons.append(item["reason"])

        # 4) Проверка порогов
        if negative_count >= self._max_neg:
            avg_severity = (severity_sum / severity_count) if severity_count > 0 else -1.0
            if avg_severity < self._severity_threshold or severity_count == 0:
                reason_str = "; ".join(reasons[:3]) if reasons else f"{negative_count} негативных новостей"
                return True, reason_str

        return False, ""

    def analyze_and_cache(self, ticker: str, dt: datetime | None = None) -> list[dict]:
        """Синхронная загрузка новостей из bot.db + AI-оценка.

        Возвращает список новостей с severity.
        """
        if not config.BOT_DB_PATH:
            return []

        if dt is None:
            dt = datetime.now(timezone.utc)

        since = (dt - timedelta(hours=self._lookback)).isoformat()
        news_items = self._load_news_from_botdb(ticker, since)

        results = []
        for item in news_items:
            ch = item["content_hash"]
            # Проверяем кэш
            cached = storage.get_cached_sentiments(ticker, since_iso=since)
            existing = next((c for c in cached if c["content_hash"] == ch), None)

            if existing and existing.get("severity") is not None:
                results.append(existing)
                continue

            # AI оценка
            severity_data = asyncio.get_event_loop().run_until_complete(
                ai_severity(item["title"], item.get("summary", ""), ticker)
            ) if asyncio.get_event_loop().is_running() is False else {"severity": 0.0, "reason": "sync fallback"}

            storage.cache_news_sentiment(
                content_hash=ch,
                ticker=ticker,
                title=item["title"],
                summary=item.get("summary", ""),
                impact=item.get("impact", "NEUTRAL"),
                severity=severity_data["severity"],
                reason=severity_data["reason"],
                source=item.get("source"),
                created_at=item.get("created_at"),
            )
            results.append({
                "content_hash": ch,
                "ticker": ticker,
                "title": item["title"],
                "summary": item.get("summary", ""),
                "impact": item.get("impact", "NEUTRAL"),
                "severity": severity_data["severity"],
                "reason": severity_data["reason"],
                "source": item.get("source"),
                "created_at": item.get("created_at"),
            })

        return results

    def _load_news_from_botdb(self, ticker: str, since_iso: str) -> list[dict]:
        """Читает news из bot.db для тикера."""
        bot_db = config.BOT_DB_PATH
        if not bot_db:
            return []

        try:
            conn = sqlite3.connect(f"file:{bot_db}?mode=ro", uri=True, timeout=5)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT content_hash, title, summary, impact, source, created_at"
                " FROM news WHERE ticker = ? AND created_at >= ?"
                " ORDER BY created_at DESC LIMIT 20",
                (ticker, since_iso),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("Cannot read bot.db for %s: %s", ticker, e)
            return []
