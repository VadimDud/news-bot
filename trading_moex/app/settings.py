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


# ── Live-состояние (стратегия, dry_run, параметры) ───────────────────────────

def save_live_state(strategy: str, dry_run: bool, strategy_params: dict) -> None:
    """Сохранить настройки live-цикла в БД (переживают перезапуск)."""
    import json
    storage.set_setting("live_strategy", strategy)
    storage.set_setting("live_dry_run", "1" if dry_run else "0")
    storage.set_setting("live_strategy_params", json.dumps(strategy_params, ensure_ascii=False))


def load_live_state() -> dict:
    """Загрузить сохранённое live-состояние из БД.

    Возвращает dict с ключами strategy, dry_run, strategy_params.
    Если ничего не сохранено — значения из config.
    """
    import json
    from . import config

    strategy = storage.get_setting("live_strategy") or "donchian"
    dry_run_raw = storage.get_setting("live_dry_run")
    dry_run = (dry_run_raw == "1") if dry_run_raw is not None else config.DRY_RUN
    params_raw = storage.get_setting("live_strategy_params")
    if params_raw:
        try:
            strategy_params = json.loads(params_raw)
        except (ValueError, TypeError):
            strategy_params = {}
    else:
        strategy_params = {}
    return {"strategy": strategy, "dry_run": dry_run, "strategy_params": strategy_params}


# ── Скринер: фильтры ────────────────────────────────────────────────────────

_SCREENER_DEFAULTS = {
    "min_avg_roe": 15.0,
    "min_single_roe": 12.0,
    "pb_entry": 0.8,
    "years": 10,
    "min_market_cap": 10_000_000_000,
    "min_volume_rub": 1_000_000,
}


def save_screener_filters(filters: dict) -> None:
    """Сохранить фильтры скринера в БД (переживают перезапуск)."""
    import json
    storage.set_setting("screener_filters", json.dumps(filters, ensure_ascii=False))


def load_screener_filters() -> dict:
    """Загрузить сохранённые фильтры скринера из БД.

    Возвращает dict с ключами min_avg_roe, min_single_roe, pb_entry, years,
    min_market_cap, min_volume_rub. Если ничего не сохранено — дефолты.
    """
    import json
    raw = storage.get_setting("screener_filters")
    if raw:
        try:
            saved = json.loads(raw)
            if isinstance(saved, dict):
                return {**_SCREENER_DEFAULTS, **saved}
        except (ValueError, TypeError):
            pass
    return dict(_SCREENER_DEFAULTS)
