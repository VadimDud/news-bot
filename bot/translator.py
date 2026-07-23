import httpx
from . import config


async def translate_to_russian(text: str) -> str:
    """Translate English text to Russian using OpenAI API with a tech-savvy tone."""

    if config.OPENAI_API_KEY:
        return await _translate_openai(text)

    # Fallback: just return original text with a note
    return f"[Перевод недоступен — настройте OPENAI_API_KEY]\n\n{text}"


async def _translate_openai(text: str) -> str:
    prompt = (
        "Переведи следующий техно-новостной текст на русский язык.\n"
        "Стиль: живой, современный, с техническим сленгом.\n"
        "Не теряй факты и цифры. Сохраняй эмодзи.\n"
        "Пиши кратко и по делу, как в хорошем техно-блоге.\n\n"
        f"Текст:\n{text}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты техно-журналист. Переводишь новости на русский язык с живым, современным стилем."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
