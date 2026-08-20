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
# Отключить проверку SSL-сертификатов при подключении к T-Bank API
# (актуально при DPI провайдера / корпоративном прокси с самоподписанным сертификатом)
TINKOFF_SSL_NO_VERIFY = os.environ.get("TINKOFF_SSL_NO_VERIFY", "false").lower() == "true"

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
