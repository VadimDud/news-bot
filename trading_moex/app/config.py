"""Конфигурация MOEX-торгового робота.

Читает окружение (docker-compose передаёт .env). Модуль-константы, как и в bot/config.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("TRADER_DATA_DIR", BASE_DIR / "data"))
CANDLE_CACHE_DIR = DATA_DIR / "candles"
DB_PATH = DATA_DIR / "trader.db"

# Данные MOEX (логин нужен только для Super Candles; обычные свечи доступны без него)
MOEX_LOGIN = os.environ.get("MOEX_LOGIN", "")
MOEX_PASSWORD = os.environ.get("MOEX_PASSWORD", "")

# T-Bank Invest API (live-торговля)
TINKOFF_API_TOKEN = os.environ.get("TINKOFF_API_TOKEN", "")
# Доверять российским корневым CA (сертификаты Минцифры, вкл. по умолчанию).
# Выключите, если T-Bank недоступен через стандартную проверку сертификатов.
TINKOFF_SSL_RU_CA = os.environ.get("TINKOFF_SSL_RU_CA", "true").lower() in ("1", "true")

# Live-режим
DRY_RUN = os.environ.get("TRADER_DRY_RUN", "true").lower() == "true"
POLL_INTERVAL = int(os.environ.get("TRADER_POLL_INTERVAL", "60"))
WATCH_TICKERS = [t.strip() for t in os.environ.get("TRADER_WATCH_TICKERS", "SBER,LKOH").split(",") if t.strip()]
TRADER_QUANTITY = os.environ.get("TRADER_QUANTITY", "1")
TRADER_LIVE_INTERVAL = os.environ.get("TRADER_LIVE_INTERVAL", "hour")

# Веб-дашборд
WEB_HOST = os.environ.get("TRADER_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("TRADER_WEB_PORT", "8081"))
WEB_PASSWORD = os.environ.get("TRADER_WEB_PASSWORD", "")
COOKIE_NAME = "moex_trader"
COOKIE_MAX_AGE = 30 * 24 * 3600

# News Guard: AI-powered news severity scoring + user overrides
# Path to bot.db (Telegram bot's database with news/sentiment data).
# Empty = feature disabled (no bot.db access from this container).
BOT_DB_PATH: str = os.environ.get("BOT_DB_PATH", "")
NEWS_AI_ENABLED: bool = os.environ.get("NEWS_AI_ENABLED", "true").lower() in ("1", "true")
# DeepSeek API for news severity scoring (same keys as bot)
DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# ── ROE-signal notifier configuration ─────────────────────────────────────
# Time of day (UTC) to run the daily ROE signal scan, after MOEX opening (07:00 UTC).
# Default 08:30 UTC gives ~30 min for candles to appear in the local DB.
TRADER_SIGNALS_SCAN_HOUR: int = int(os.environ.get("TRADER_SIGNALS_SCAN_HOUR", "8"))
TRADER_SIGNALS_SCAN_MINUTE: int = int(os.environ.get("TRADER_SIGNALS_SCAN_MINUTE", "30"))

# Enable/disable the notifier (when running inside the trader container).
TRADER_SIGNALS_ENABLED: bool = os.environ.get("TRADER_SIGNALS_ENABLED", "true").lower() in ("1", "true")

# Прогнать скан один раз сразу при старте контейнера (догоняем пропущенные дни;
# дубликаты исключены — первое наблюдение фиксируется как baseline без отправки).
TRADER_SIGNALS_RUN_ON_STARTUP: bool = os.environ.get("TRADER_SIGNALS_RUN_ON_STARTUP", "true").lower() in ("1", "true")

# Перед сканом докачивать хвост дневных свечей с MOEX (moexalgo) автоматически.
TRADER_SIGNALS_AUTO_UPDATE: bool = os.environ.get("TRADER_SIGNALS_AUTO_UPDATE", "true").lower() in ("1", "true")
# Свечи старше этого числа календарных дней считаются протухшими (выходные+праздники).
# Протухание/ошибка обновления → Telegram-алерт раз в сутки.
TRADER_SIGNALS_MAX_STALE_DAYS: int = int(os.environ.get("TRADER_SIGNALS_MAX_STALE_DAYS", "5"))
# Отчётность старше этого возраста (дней) помечается предупреждением в алерте
# (годовая отчётность выходит раз в год, поэтому порог щадящий).
TRADER_SIGNALS_FUND_MAX_AGE_DAYS: int = int(os.environ.get("TRADER_SIGNALS_FUND_MAX_AGE_DAYS", "400"))
# Интервал повтора алертов о данных (дней): 0 = алерты отключены, 1 = раз в сутки, N = раз в N дней.
TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS: int = int(os.environ.get("TRADER_SIGNALS_DATA_ALERT_INTERVAL_DAYS", "1"))

# Telegram для сигналов: тот же бот, что и новостной (общий .env).
TELEGRAM_BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.environ.get("ADMIN_ID", "")
# Локальный прокси для api.telegram.org (в host-сети контейнера); пусто = напрямую.
TRADER_TG_PROXY: str = os.environ.get("TRADER_TG_PROXY", "")

# ROE-signal parameters — tuned by backtests (CAGR 24.6%, DD 16% on 2021‑2024, 7 tickers).
# Скоринг-режим (scoring=1) дал +21.2% trading part против +6.1% у AND-логики при rebalance=21д.
# Для ежедневного скана оставляем дефолтные веса из _ROE_PORTFOLIO_PARAMS_TUPLE.
TRADER_ROE_MIN_AVG_ROE: float = float(os.environ.get("TRADER_ROE_MIN_AVG_ROE", "15.0"))  # мин. avg ROE за 10 лет, %
TRADER_ROE_MIN_SINGLE_ROE: float = float(os.environ.get("TRADER_ROE_MIN_SINGLE_ROE", "12.0"))  # мин. годовой ROE, %
TRADER_ROE_PB_ENTRY: float = float(os.environ.get("TRADER_ROE_PB_ENTRY", "0.8"))  # вход: цена ≤ pb_entry × BVPS
TRADER_ROE_PB_EXIT: float = float(os.environ.get("TRADER_ROE_PB_EXIT", "1.5"))  # выход: цена ≥ pb_exit × BVPS
TRADER_ROE_ROE_EXIT: float = float(os.environ.get("TRADER_ROE_ROE_EXIT", "12.0"))  # выход: ROE < roe_exit
TRADER_ROE_MIN_SCORE: float = float(os.environ.get("TRADER_ROE_MIN_SCORE", "0.5"))  # мин. composite score при scoring=1 (0.5 — прибыльный вариант бэктеста SBER 2020–2026)
TRADER_ROE_SCORING: int = int(os.environ.get("TRADER_ROE_SCORING", "1"))  # 1 = мульти-factor, 0 = AND-логика

# Веса факторов при scoring=1 (сумма весов не обязана быть 1, используются как коэффициенты):
TRADER_ROE_W_ROE: float = float(os.environ.get("TRADER_ROE_W_ROE", "1.0"))  # качество ROE (avg_roe)
TRADER_ROE_W_PB: float = float(os.environ.get("TRADER_ROE_W_PB", "1.0"))  # дешевизна (price / BVPS)
TRADER_ROE_W_MOMENTUM: float = float(os.environ.get("TRADER_ROE_W_MOMENTUM", "0.5"))  # моментум (возврат 6 мес)
TRADER_ROE_W_DIVIDEND: float = float(os.environ.get("TRADER_ROE_W_DIVIDEND", "0.5"))  # дивидендная доходность
TRADER_ROE_W_STABILITY: float = float(os.environ.get("TRADER_ROE_W_STABILITY", "0.5"))  # стабильность ROE (min_roe / avg_roe)

# ── Partial exit for portfolio (unused in per-ticker scanner, но оставлено для совместимости) ──

TRADER_ROE_PB_EXIT_PARTIAL: float = float(os.environ.get("TRADER_ROE_PB_EXIT_PARTIAL", "1.2"))  # при P/B ≥ этого продаём часть позиции
TRADER_ROE_PARTIAL_FRAC: float = float(os.environ.get("TRADER_ROE_PARTIAL_FRAC", "0.5"))  # доля позиции при частной продаже
TRADER_ROE_MAX_POSITIONS: int = int(os.environ.get("TRADER_ROE_MAX_POSITIONS", "4"))  # каждая сделка ≈ 100% / max_positions депозита
TRADER_ROE_CASH_YIELD: float = float(os.environ.get("TRADER_ROE_CASH_YIELD", "8.0"))  # годовая доходность денежной подушки (TMON), %
TRADER_ROE_STOP_LOSS_PCT: float = float(os.environ.get("TRADER_ROE_STOP_LOSS_PCT", "0"))  # стоп-лосс: 0=выключен, 10=10% от цены входа
TRADER_ROE_REBALANCE_DAYS: int = int(os.environ.get("TRADER_ROE_REBALANCE_DAYS", "126"))  # ребаланс: 126=5.5мес (grid-оптимизация)

# Автозагрузка дивидендов с T-Bank Invest API при скане (0=выкл, 1=вкл).
TRADER_SIGNALS_AUTO_DIVIDENDS: bool = os.environ.get("TRADER_SIGNALS_AUTO_DIVIDENDS", "true").lower() in ("1", "true")

# ── Trading Skills: pre-trade gate ───────────────────────────────────────────
# Включить pre-trade проверки перед выставлением ордеров (0=выкл, 1=вкл).
TRADER_SKILLS_ENABLED: bool = os.environ.get("TRADER_SKILLS_ENABLED", "true").lower() in ("1", "true")
# Режим гейта: shadow = только лог/дашборд, enforce = блокировка/резайз.
TRADER_SKILLS_MODE: str = os.environ.get("TRADER_SKILLS_MODE", "shadow")
# Минимальное R:R для входа (ниже — BLOCKED).
TRADER_SKILLS_MIN_RR: float = float(os.environ.get("TRADER_SKILLS_MIN_RR", "1.5"))
# Макс. % equity на одну позицию.
TRADER_SKILLS_MAX_POSITION_PCT: float = float(os.environ.get("TRADER_SKILLS_MAX_POSITION_PCT", "50.0"))
# Комиссия (одна сторона, %). 0.04% — типичный тариф MOEX.
TRADER_SKILLS_COMMISSION_PCT: float = float(os.environ.get("TRADER_SKILLS_COMMISSION_PCT", "0.04"))

# ── Elliott micro-wave signal notifier ──────────────────────────────────────
TRADER_ELLIOTT_ENABLED: bool = os.environ.get("TRADER_ELLIOTT_ENABLED", "true").lower() in ("1", "true")
TRADER_ELLIOTT_SCAN_HOUR: int = int(os.environ.get("TRADER_ELLIOTT_SCAN_HOUR", "16"))   # UTC ≈ 19:00 MSK
TRADER_ELLIOTT_SCAN_MINUTE: int = int(os.environ.get("TRADER_ELLIOTT_SCAN_MINUTE", "10"))
TRADER_ELLIOTT_RUN_ON_STARTUP: bool = os.environ.get("TRADER_ELLIOTT_RUN_ON_STARTUP", "true").lower() in ("1", "true")
TRADER_ELLIOTT_WAVE_MIN: int = int(os.environ.get("TRADER_ELLIOTT_WAVE_MIN", "3"))
TRADER_ELLIOTT_WAVE_MAX: int = int(os.environ.get("TRADER_ELLIOTT_WAVE_MAX", "5"))
TRADER_ELLIOTT_BODY_RATIO_MIN: float = float(os.environ.get("TRADER_ELLIOTT_BODY_RATIO_MIN", "0.6"))
TRADER_ELLIOTT_ATR_K: float = float(os.environ.get("TRADER_ELLIOTT_ATR_K", "0.5"))
# Мин. качество волны (0..1) для отправки сигнала; волны ниже порога считаются шумом.
TRADER_ELLIOTT_MIN_QUALITY: float = float(os.environ.get("TRADER_ELLIOTT_MIN_QUALITY", "0.4"))
