# Tech News Bot

Telegram-бот для создания тематических лент новостей с AI-анализом.

## Возможности

- **Тематические ленты** — создавайте каналы по темам (финансы, IT, крипта, энергетика и др.)
- **Умные ключевые слова** — бот ищет новости по вашим ключевым словам
- **AI-расширение** — DeepSeek/Gemini/DashScope предлагают дополнительные ключевые слова
- **Динамические источники** — 9 категорий RSS-лент (финансы, макро, сырьё, IT, крипта, политика, рынки, наука, недвижимость)
- **Автоматический скан** — фоновый скан каждые 30 минут (настраивается)
- **Edit-in-place** — одно сообщение обновляется без спама
- **Анализ тональности** — AI определяет позитивную, негативную или нейтральную тональность
- **Поддержка ru/en** — интернационализация, переключение языка
- **Админ-панель** — статистика, регистрации, рассылка

## Архитектура

```
main.py                    — точка входа, APScheduler, фоновые задачи
web_app.py                 — веб-интерфейс для управления лентами (aiohttp)
web/templates/             — HTML-шаблоны веб-интерфейса
bot/
  config.py                — конфигурация из .env
  database.py              — SQLite (aiosqlite), все запросы
  sources.py               — каталог RSS-источников по категориям
  finance.py               — RSS-парсер с кэшированием
  news_processor.py        — 4-стадийный пайплайн: фильтр → sentiment → dedup → распределение
  topic_analyzer.py        — AI-анализ тем для расширения ключевых слов
  asset_analyzer.py        — AI-анализ тикеров
  rate_limiter.py          — per-user rate limiting
  retry_utils.py           — async retry с exponential backoff
  scheduler.py             — APScheduler integration
  i18n.py                  — интернационализация (ru/en)
  keyboards.py             — inline-клавиатуры
  middlewares.py           — language detection middleware
  translator.py            — перевод текста через OpenAI
  handlers/
    start.py               — /start, главное меню, навигация
    channels.py            — создание/управление лентами, сканирование
    finance.py             — добавление/удаление тикеров (legacy)
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

### Обязательные переменные

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_ID` | Ваш Telegram ID (узнать через @userinfobot) |

### Опциональные переменные

| Переменная | Описание |
|---|---|
| `DEEPSEEK_API_KEY` | API-ключ DeepSeek (AI-анализ, основной) |
| `DEEPSEEK_BASE_URL` | URL API DeepSeek |
| `DEEPSEEK_MODEL` | Модель DeepSeek |
| `GEMINI_API_KEY` | API-ключ Gemini (fallback) |
| `GEMINI_MODEL` | Модель Gemini |
| `DASHSCOPE_API_KEY` | API-ключ DashScope/Qwen (fallback) |
| `DASHSCOPE_BASE_URL` | URL API DashScope |
| `DASHSCOPE_MODEL` | Модель DashScope |
| `HTTP_PROXY` | Прокси для Telegram API |
| `AUTO_SCAN_INTERVAL` | Интервал сканирования в секундах (по умолчанию 1800) |

## Запуск

```bash
python main.py
```

## Веб-интерфейс

Веб-страницы для ввода настроек лент (название, ключевые слова, тикер, категории источников, тематики) вместо переписки в Telegram:

```bash
python web_app.py
```

Открывайте `http://127.0.0.1:8080` и введите ваш Telegram ID. Хост и порт настраиваются через `WEB_HOST` / `WEB_PORT` в `.env` (по умолчанию `127.0.0.1:8080`).

> Примечание: авторизация через Telegram пока не подключена — ID вводится вручную. Для публичного доступа установите `WEB_HOST=0.0.0.0` и заверните за Cloudflare Tunnel / Nginx + HTTPS.

## Docker

```bash
docker compose up -d
```

## Тесты

```bash
pip install pytest-asyncio
pytest tests/ -q
```

## Использование

1. Отправьте `/start` в бот
2. Нажмите «Попробовать бесплатно» (30 дней)
3. Создайте ленту: нажмите «📡 Мои ленты» → «➕ Создать ленту»
4. Введите название (например, «Макроэкономика»)
5. Введите ключевые слова через запятую (например, «инфляция, ключевая ставка, ЦБ»)
6. Введите тикер или пропустите
7. Выберите категории источников (или «Все»)
8. Нажмите «🔍 Сканировать» для ручного обновления

## Технологии

- Python 3.12+
- aiogram 3.30 — Telegram Bot API
- aiohttp — веб-интерфейс
- aiosqlite — асинхронный SQLite
- APScheduler — планировщик задач
- DeepSeek/Gemini/DashScope — AI-анализ
- httpx — асинхронные HTTP-запросы
- feedparser — парсинг RSS
