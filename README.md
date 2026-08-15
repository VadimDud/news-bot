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
| `AUTO_SCAN_INTERVAL` | Интервал сканирования в секундах (по умолчанию 3600 = 60 минут) |
| `BOT_USERNAME` | Имя бота без `@` — включает Telegram Login Widget в веб-интерфейсе |
| `WEB_HOST` | Хост веб-интерфейса (по умолчанию `127.0.0.1`) |
| `WEB_PORT` | Порт веб-интерфейса (по умолчанию `8080`) |
| `WEB_COOKIE_SECRET` | Отдельный секрет для сессионных кук (по умолчанию — хэш `BOT_TOKEN`) |
| `WEB_COOKIE_SECURE` | `true`, если веб-интерфейс отдаётся по HTTPS |

## Запуск

```bash
python main.py
```

## Веб-интерфейс

Веб-страницы для ввода настроек лент (название, ключевые слова, тикер, категории источников, тематики) вместо переписки в Telegram. Стек: aiohttp + Jinja2 + HTMX + Alpine.js.

```bash
python web_app.py
```

Открывайте `http://127.0.0.1:8080`. Хост и порт настраиваются через `WEB_HOST` / `WEB_PORT` в `.env` (по умолчанию `127.0.0.1:8080`).

### Авторизация

1. **Telegram Login Widget** — основной способ. Укажите `BOT_USERNAME` в `.env`; кнопка входа появится на главной странице. Виджет работает только по HTTPS (или на localhost), поэтому для публичного доступа заверните веб-интерфейс за Cloudflare Tunnel / Nginx с HTTPS и установите `WEB_COOKIE_SECURE=true`.
2. **Ручной вход по Telegram ID** — запасной вариант (кнопка «Войти по Telegram ID вручную» на главной). Работает и без HTTPS.

В обоих случаях пользователь должен сначала запустить бота (`/start`) и иметь активный доступ.

## Docker

```bash
docker compose up -d
```

## MOEX-торговый робот (контейнер `moex-trader`)

Отдельный контейнер в `trading_moex/` для бэктеста стратегий на истории Московской
биржи (AlgoPack / `moexalgo`, движок Backtrader) и live-торговли через
T-Bank Invest API (`tinkoff-invest`).

- **Бэктест**: `GET/POST` в веб-дашборде — тикер (SBER, LKOH, ...), таймфрейм,
  период, стратегия (SMA Cross / RSI / Donchian), капитал и комиссия. Результат:
  доходность, max просадка, Sharpe, список сделок, кривая капитала (Chart.js).
- **Live**: цикл опроса котировок T-Bank, сигнал по выбранной стратегии, ордера
  через `OrdersService`. По умолчанию **dry-run** (`TRADER_DRY_RUN=true`) — реальные
  ордера выставляются только при явном отключении.
- **Список тикеров**: раздел «Тикеры» в дашборде — выбирайте инструменты из
  каталога популярных акций MOEX (`trading_moex/app/catalog.py`) или вводите код
  вручную. Список хранится в SQLite и применяется live-циклом без перезапуска;
  пока список пуст, используется `TRADER_WATCH_TICKERS` из `.env`.
- **Веб-дашборд**: `http://<host>:8081` (порт настраивается `TRADER_WEB_PORT`),
  вход по паролю `TRADER_WEB_PASSWORD`.

Переменные окружения — блок `MOEX trading bot` в `.env` / `.env.example`:
`TINKOFF_API_TOKEN`, `TRADER_DRY_RUN`, `TRADER_POLL_INTERVAL`,
`TRADER_WATCH_TICKERS`, `TRADER_QUANTITY`, `TRADER_LIVE_INTERVAL`,
`TRADER_WEB_HOST/PORT/PASSWORD`, `MOEX_LOGIN/MOEX_PASSWORD` (только для
Super Candles, обычные свечи доступны без авторизации).

### Как создать свою стратегию

Каждая стратегия состоит из **двух частей**, зарегистрированных под одним ключом:

1. **pandas-функция сигнала** в `trading_moex/app/signals.py` — используется
   live-циклом и покрыта юнит-тестами. Принимает DataFrame с колонками
   `open/high/low/close/volume`, возвращает `pd.Series` позиции `0/1`
   (0 — вне рынка, 1 — в позиции). Регистрируется в `SIGNAL_FUNCS`.
2. **Backtrader-класс** в `trading_moex/app/strategies.py` — для бэктеста.
   Наследуется от `TradeRecordingStrategy`, реализует `__init__` (индикаторы)
   и `next` (покупка/закрытие по сигналу). Регистрируется в `STRATEGIES`
   вместе с описанием параметров для веб-формы.

Ключ в `SIGNAL_FUNCS` и ключ в `STRATEGIES` должны совпадать — по нему веб
связывает live-сигнал и бэктест. Шаблон новой стратегии:

```python
# ── signals.py ──────────────────────────────────────────────────────────
def my_strategy_position(df, period: int = 20) -> pd.Series:
    close = df["close"]
    base = close.rolling(period).mean()
    return (close > base).astype(int)

# ...и в SIGNAL_FUNCS внизу файла:
SIGNAL_FUNCS = {
    "sma_cross": sma_cross_position,
    "rsi": rsi_position,
    "donchian": donchian_position,
    "my_strategy": my_strategy_position,
}

# ── strategies.py ───────────────────────────────────────────────────────
class MyStrategy(TradeRecordingStrategy):
    params = (("period", 20),)

    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        elif self.data.close[0] < self.sma[0]:
            self.close()

# ...и в STRATEGIES внизу файла:
STRATEGIES["my_strategy"] = {
    "name": "Моя стратегия",
    "cls": MyStrategy,
    "params": [
        {"key": "period", "label": "Период SMA", "type": "int", "default": 20},
    ],
}
```

После этого стратегия появится в формах бэктеста и live без изменений в
`app.py`: параметры подтянутся из `params` реестра, а сигналы — из `SIGNAL_FUNCS`.
Добавьте юнит-тест сигнала в `tests/test_trading_moex.py` по образцу существующих.

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
