# Finance News Bot

Telegram-бот для отслеживания финансовых новостей с AI-анализом тональности.

## Возможности

- Мониторинг 4 новостных источников: Коммерсантъ, Интерфакс, ТАСС, Ведомости
- Автоматический скан каждые 30 минут (настраивается)
- Фильтрация по тикерам: SBER, GAZP, LKOH, GMKN и др.
- Анализ тональности через DeepSeek AI (позитив / негатив / нейтрально)
- Edit-in-place — одно сообщение обновляется без спама
- 30-дневный бесплатный период
- Поддержка русского и английского языков

## Архитектура

```
main.py                    — точка входа, APScheduler, фоновые задачи
bot/
  config.py                — конфигурация из .env
  database.py              — SQLite (aiosqlite), все запросы
  finance.py               — RSS-парсер, источники новостей
  news_processor.py        — 3-стадийный пайплайн: фильтр → sentiment → AI
  asset_analyzer.py        — AI-анализ тикеров (DeepSeek/Gemini)
  retry_utils.py           — async retry с exponential backoff
  rate_limiter.py          — per-user rate limiting
  scheduler.py             — APScheduler integration
  i18n.py                  — интернационализация (ru/en)
  keyboards.py             — inline-клавиатуры
  middlewares.py           — language detection middleware
  handlers/
    start.py               — /start, главное меню, навигация
    finance.py             — добавление/удаление тикеров
    admin.py               — админ-панель
    language.py            — переключение языка
```

## Установка

```bash
git clone <repo-url>
cd tech_news_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Обязательные переменные:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_ID` — ваш Telegram ID (узнать через @userinfobot)

Опциональные:
- `DEEPSEEK_API_KEY` — API-ключ DeepSeek (для AI-анализа)
- `GEMINI_API_KEY` — API-ключ Gemini (фолбэк)
- `HTTP_PROXY` — прокси для Telegram API
- `AUTO_SCAN_INTERVAL` — интервал скана в секундах (по умолчанию 1800)

## Запуск

```bash
python main.py
```

## Docker

```bash
docker-compose up -d
```

## Использование

1. Отправьте `/start` в бот
2. Нажмите «Попробовать бесплатно» (30 дней)
3. Добавьте тикеры: отправьте `SBER`, `GAZP` и др.
4. Нажмите «Новости» для получения отчёта
5. Бот обновляет сообщение каждые 30 минут

## Технологии

- Python 3.11+
- aiogram 3.30 — Telegram Bot API
- aiosqlite — асинхронный SQLite
- APScheduler — планировщик задач
- DeepSeek AI — анализ тональности
- httpx — асинхронные HTTP-запросы
- feedparser — парсинг RSS
