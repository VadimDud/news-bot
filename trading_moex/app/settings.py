"""Настройки и токены, управляемые через веб-интерфейс.

Приоритет: значение из SQLite (задано в дашборде) → переменная окружения
(из ``config``). Изменение через веб не перезапускает процесс, поэтому
live-цикл и загрузка данных читают эффективное значение в рантайме.
"""

from . import config, storage

_ENV_FALLBACK = {
    "TINKOFF_API_TOKEN": lambda: config.TINKOFF_API_TOKEN,
    "MOEX_LOGIN": lambda: config.MOEX_LOGIN,
    "MOEX_PASSWORD": lambda: config.MOEX_PASSWORD,
    "TRADER_WEB_PASSWORD": lambda: config.WEB_PASSWORD,
}

# Секретные настройки (маскируются в форме)
SECRET_KEYS = ("TINKOFF_API_TOKEN", "MOEX_PASSWORD", "TRADER_WEB_PASSWORD")

# Все настройки, редактируемые через дашборд: key -> описание для формы
EDITABLE = {
    "TINKOFF_API_TOKEN": {
        "label": "T-Bank Invest API-токен",
        "hint": "Токен из https://www.tinkoff.ru/invest/settings/ (Invest API). Нужен для live-торговли.",
    },
    "TRADER_WEB_PASSWORD": {
        "label": "Пароль входа в дашборд",
        "hint": "Задайте при первом входе, если TRADER_WEB_PASSWORD не указан в .env.",
    },
    "MOEX_LOGIN": {
        "label": "Логин moex.com",
        "hint": "Только для Super Candles; обычные свечи работают без авторизации.",
    },
    "MOEX_PASSWORD": {
        "label": "Пароль moex.com",
        "hint": "Пароль от учётной записи на moex.com.",
    },
}


def get(key: str) -> str:
    """Эффективное значение настройки: SQLite → env."""
    value = storage.get_setting(key)
    if value:
        return value
    fallback = _ENV_FALLBACK.get(key)
    return fallback() if fallback else ""


def set(key: str, value: str) -> None:
    storage.set_setting(key, (value or "").strip())


def tinkoff_token() -> str:
    return get("TINKOFF_API_TOKEN")


def moex_login() -> str:
    return get("MOEX_LOGIN")


def moex_password() -> str:
    return get("MOEX_PASSWORD")


def mask(value: str) -> str:
    """Маскировать секрет для отображения: первые 4 символа + «•••»."""
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * 4
    return f"{value[:4]}•••"
