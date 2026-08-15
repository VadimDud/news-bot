"""Веб-дашборд MOEX-торгового робота (aiohttp + Jinja2 + HTMX + Chart.js).

Авторизация по паролю ``TRADER_WEB_PASSWORD`` (HMAC-кука).
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web

from .. import config, data, settings, storage
from ..backtest import run_backtest
from ..catalog import AVAILABLE_TICKERS
from ..live import live_trader
from ..strategies import STRATEGIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("moex_trader.web")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_PUBLIC_PATHS = {"/login", "/static"}

# ── Фоновые задачи скачивания (прогресс в UI) ────────────────────────────────

_DL_TTL_SECONDS = 15 * 60
_DL_JOBS: dict[str, dict] = {}


def _prune_dl_jobs() -> None:
    now = time.monotonic()
    for jid in [j for j, job in _DL_JOBS.items() if now - job["created"] > _DL_TTL_SECONDS]:
        _DL_JOBS.pop(jid, None)


def _effective_password() -> str:
    return settings.get("TRADER_WEB_PASSWORD")


def _cookie_secret() -> bytes:
    password = _effective_password()
    if not password:
        raise RuntimeError("TRADER_WEB_PASSWORD не задан")
    return password.encode()


def _sign() -> str:
    payload = "ok"
    return f"{payload}.{hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()}"


def _verify(value: str) -> bool:
    try:
        payload, sig = value.rsplit(".", 1)
        expected = hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()
        return payload == "ok" and hmac.compare_digest(sig, expected)
    except (ValueError, TypeError):
        return False


def _current_user(request: web.Request) -> bool:
    value = request.cookies.get(config.COOKIE_NAME)
    return bool(value and _verify(value))


@web.middleware
async def _auth_middleware(request: web.Request, handler) -> web.StreamResponse:
    if any(request.path.startswith(p) for p in _PUBLIC_PATHS):
        return await handler(request)
    if request.path == "/settings":
        # Без установленного пароля /settings открыт для начальной настройки;
        # иначе страница настроек требует авторизации как и остальные.
        if not _effective_password():
            return await handler(request)
    if not _effective_password():
        raise web.HTTPFound("/settings")
    if not _current_user(request):
        raise web.HTTPFound("/login")
    return await handler(request)


@web.middleware
async def _no_cache_middleware(request: web.Request, handler) -> web.StreamResponse:
    """HTML-страницы не кэшируются браузером — иначе не видны свежие правки шаблонов."""
    resp = await handler(request)
    if not request.path.startswith("/static") and resp.content_type == "text/html":
        resp.headers.setdefault("Cache-Control", "no-cache, no-store, must-revalidate")
    return resp


def _error_page(request: web.Request, message: str) -> web.Response:
    return aiohttp_jinja2.render_template("error.html", request, {"error": message})


# ── Стратегия / параметры ────────────────────────────────────────────────────

def _default_params(strategy_key: str) -> dict:
    return {p["key"]: p["default"] for p in STRATEGIES[strategy_key]["params"]}


def _parse_params(strategy_key: str, form: dict) -> dict:
    params = {}
    for spec in STRATEGIES[strategy_key]["params"]:
        raw = form.get(spec["key"], str(spec["default"]))
        try:
            params[spec["key"]] = int(raw) if spec["type"] == "int" else float(raw)
        except (TypeError, ValueError):
            params[spec["key"]] = spec["default"]
    return params


def _parse_date(raw: str, fallback: date) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def _ticker_suggestions() -> list[str]:
    """Тикеры для подсказок в поле ввода: сначала добавленные в watchlist, потом каталог."""
    current = storage.list_watchlist()
    suggestions = list(current)
    for item in AVAILABLE_TICKERS:
        if item["ticker"] not in suggestions:
            suggestions.append(item["ticker"])
    return suggestions


# ── Маршруты ─────────────────────────────────────────────────────────────────

async def login_page(request: web.Request) -> web.Response:
    if _current_user(request):
        raise web.HTTPFound("/")
    return aiohttp_jinja2.render_template("login.html", request, {})


async def login_post(request: web.Request) -> web.Response:
    form = await request.post()
    password = form.get("password", "")
    effective = _effective_password()
    if not effective:
        return aiohttp_jinja2.render_template(
            "login.html", request, {"error": "Пароль не задан. Установите его на странице настроек."}
        )
    if not hmac.compare_digest(password, effective):
        return aiohttp_jinja2.render_template(
            "login.html", request, {"error": "Неверный пароль"}
        )
    resp = web.HTTPFound("/")
    resp.set_cookie(
        config.COOKIE_NAME, _sign(), max_age=config.COOKIE_MAX_AGE,
        httponly=True, samesite="Lax",
    )
    raise resp


async def logout(request: web.Request) -> web.Response:
    resp = web.HTTPFound("/login")
    resp.del_cookie(config.COOKIE_NAME)
    raise resp


async def watchlist_page(request: web.Request) -> web.Response:
    current = storage.list_watchlist()
    current_set = set(current)
    return aiohttp_jinja2.render_template(
        "watchlist.html",
        request,
        {
            "available": [t for t in AVAILABLE_TICKERS if t["ticker"] not in current_set],
            "current": current,
            "env_defaults": [t for t in config.WATCH_TICKERS if t not in current_set],
            "periods": data.PERIODS,
            "today": date.today().isoformat(),
            "year_ago": (date.today() - timedelta(days=365)).isoformat(),
            "ticker_suggestions": _ticker_suggestions(),
        },
    )


async def watchlist_add(request: web.Request) -> web.Response:
    form = await request.post()
    ticker = (form.get("manual", "") or form.get("ticker", "")).strip().upper()
    if ticker:
        storage.add_watchlist(ticker)
    raise web.HTTPFound("/watchlist")


async def watchlist_remove(request: web.Request) -> web.Response:
    form = await request.post()
    ticker = form.get("ticker", "").strip().upper()
    if ticker:
        storage.remove_watchlist(ticker)
    raise web.HTTPFound("/watchlist")


async def settings_page(request: web.Request) -> web.Response:
    values = {}
    for key, meta in settings.EDITABLE.items():
        current = settings.get(key)
        values[key] = {
            "label": meta["label"],
            "hint": meta["hint"],
            "masked": settings.mask(current) if current else "",
            "configured": bool(current),
            "secret": key in settings.SECRET_KEYS,
        }
    return aiohttp_jinja2.render_template(
        "settings.html",
        request,
        {
            "values": values,
            "bootstrap": not _effective_password(),
            "notice": "",
        },
    )


async def settings_save(request: web.Request) -> web.Response:
    form = await request.post()
    password_changed = False
    for key in settings.EDITABLE:
        value = form.get(key, "").strip()
        if value:
            settings.set(key, value)
            if key == "TRADER_WEB_PASSWORD":
                password_changed = True

    values = {}
    for key, meta in settings.EDITABLE.items():
        current = settings.get(key)
        values[key] = {
            "label": meta["label"],
            "hint": meta["hint"],
            "masked": settings.mask(current) if current else "",
            "configured": bool(current),
            "secret": key in settings.SECRET_KEYS,
        }

    resp = aiohttp_jinja2.render_template(
        "settings.html",
        request,
        {
            "values": values,
            "bootstrap": not _effective_password(),
            "notice": "Настройки сохранены.",
        },
    )
    if password_changed and _current_user(request):
        # Переиздать куку новым секретом, чтобы сессия не слетела после смены пароля
        resp.set_cookie(
            config.COOKIE_NAME, _sign(), max_age=config.COOKIE_MAX_AGE,
            httponly=True, samesite="Lax",
        )
    return resp


async def index(request: web.Request) -> web.Response:
    runs = storage.list_runs(20)
    ctx = {
        "periods": data.PERIODS,
        "strategies": STRATEGIES,
        "runs": runs,
        "today": date.today().isoformat(),
        "year_ago": (date.today() - timedelta(days=365)).isoformat(),
        "ticker_suggestions": _ticker_suggestions(),
    }
    return aiohttp_jinja2.render_template("index.html", request, ctx)


async def data_download(request: web.Request) -> web.Response:
    """Скачать свечи тикера с MOEX в CSV (общая база данных свечей с бэктестом)."""
    form = await request.post()
    ticker = form.get("ticker", "").strip().upper()
    period = form.get("period", "1min")
    start = _parse_date(form.get("start", ""), date.today() - timedelta(days=365))
    end = _parse_date(form.get("end", ""), date.today())

    errors = []
    if not ticker:
        errors.append("Укажите тикер (например SBER).")
    if period not in data.PERIODS:
        errors.append("Неизвестный таймфрейм.")
    if start >= end:
        errors.append("Дата начала должна быть раньше даты окончания.")
    if errors:
        return _error_page(request, " ".join(errors))

    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(None, data.fetch_history, ticker, period, start, end, True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Скачивание %s %s не удалось: %s", ticker, period, exc)
        return _error_page(request, f"Ошибка загрузки данных: {exc}")

    filename = f"{ticker}_{period}_{start.isoformat()}_{end.isoformat()}.csv"
    return web.Response(
        body=data.to_csv(df),
        content_type="text/csv",
        charset="utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def data_status(request: web.Request) -> web.Response:
    """Статус базы данных свечей для тикера/таймфрейма."""
    ticker = request.query.get("ticker", "").strip().upper()
    period = request.query.get("period", "1day")
    if not ticker or period not in data.PERIODS:
        return web.json_response({"ticker": ticker, "period": period, "last": None, "count": 0})
    return web.json_response(
        {
            "ticker": ticker,
            "period": period,
            "last": storage.last_candle_time(ticker, period),
            "count": storage.candle_count(ticker, period),
        }
    )


async def data_download_start(request: web.Request) -> web.Response:
    """Запустить фоновое скачивание свечей; вернуть job_id для опроса прогресса."""
    form = await request.post()
    ticker = form.get("ticker", "").strip().upper()
    period = form.get("period", "1min")
    start = _parse_date(form.get("start", ""), date.today() - timedelta(days=365))
    end = _parse_date(form.get("end", ""), date.today())

    errors = []
    if not ticker:
        errors.append("Укажите тикер (например SBER).")
    if period not in data.PERIODS:
        errors.append("Неизвестный таймфрейм.")
    if start >= end:
        errors.append("Дата начала должна быть раньше даты окончания.")
    if errors:
        return web.json_response({"error": " ".join(errors)}, status=400)

    _prune_dl_jobs()
    job_id = secrets.token_hex(8)
    _DL_JOBS[job_id] = {
        "state": "running",
        "percent": 0,
        "error": None,
        "csv": None,
        "filename": None,
        "created": time.monotonic(),
    }
    asyncio.get_running_loop().create_task(_run_download_job(job_id, ticker, period, start, end))
    return web.json_response({"job_id": job_id})


async def _run_download_job(job_id: str, ticker: str, period: str, start: date, end: date) -> None:
    job = _DL_JOBS[job_id]
    loop = asyncio.get_running_loop()

    def set_progress(pct: int) -> None:
        job["percent"] = pct

    try:
        df = await loop.run_in_executor(
            None, data.fetch_history, ticker, period, start, end, True, set_progress
        )
        job["csv"] = data.to_csv(df)
        job["filename"] = f"{ticker}_{period}_{start.isoformat()}_{end.isoformat()}.csv"
        job["percent"] = 100
        job["state"] = "done"
    except Exception as exc:  # noqa: BLE001
        job["state"] = "error"
        job["error"] = str(exc)
        logger.warning("Скачивание %s %s не удалось: %s", ticker, period, exc)


async def data_download_status(request: web.Request) -> web.Response:
    """Прогресс фонового скачивания."""
    job = _DL_JOBS.get(request.query.get("job_id", ""))
    if job is None:
        return web.json_response({"state": "not_found"}, status=404)
    return web.json_response({"state": job["state"], "percent": job["percent"], "error": job["error"]})


async def data_download_result(request: web.Request) -> web.Response:
    """Отдать готовый CSV (однократно) или ошибку/промежуточный статус."""
    job_id = request.query.get("job_id", "")
    job = _DL_JOBS.get(job_id)
    if job is None:
        return web.json_response({"error": "Задача не найдена"}, status=404)
    if job["state"] == "running":
        return web.json_response({"error": "Скачивание ещё выполняется"}, status=425)
    if job["state"] == "error":
        return _error_page(request, f"Ошибка загрузки данных: {job['error']}")
    csv_data = job.pop("csv")
    filename = job.pop("filename")
    _DL_JOBS.pop(job_id, None)
    return web.Response(
        body=csv_data,
        content_type="text/csv",
        charset="utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def backtest_run(request: web.Request) -> web.Response:
    form = await request.post()
    ticker = form.get("ticker", "").strip().upper()
    period = form.get("period", "1day")
    strategy_key = form.get("strategy", "")
    start_raw = form.get("start", "")
    end_raw = form.get("end", "")
    try:
        cash = float(form.get("cash", "100000"))
        commission = float(form.get("commission", "0.0005"))
    except (TypeError, ValueError):
        return _error_page(request, "Некорректный капитал или комиссия")

    errors = []
    if not ticker:
        errors.append("Укажите тикер (например SBER, LKOH).")
    if period not in data.PERIODS:
        errors.append("Неизвестный таймфрейм.")
    if strategy_key not in STRATEGIES:
        errors.append("Неизвестная стратегия.")
    if cash <= 0:
        errors.append("Стартовый капитал должен быть больше нуля.")
    if errors:
        return _error_page(request, " ".join(errors))

    start = _parse_date(start_raw, date.today() - timedelta(days=365))
    end = _parse_date(end_raw, date.today())
    if start >= end:
        return _error_page(request, "Дата начала должна быть раньше даты окончания.")

    params = _parse_params(strategy_key, form)
    run_id = storage.create_run(ticker, period, strategy_key, params, start.isoformat(), end.isoformat())

    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(None, data.fetch_history, ticker, period, start, end, True)
        result = await loop.run_in_executor(
            None, run_backtest, df, STRATEGIES[strategy_key]["cls"], params, cash, commission
        )
        storage.finish_run(run_id, result)
        return web.HTTPFound(f"/backtest/{run_id}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backtest %s (%s %s) failed: %s", run_id, ticker, period, exc)
        storage.finish_run(run_id, None, str(exc))
        return _error_page(request, f"Ошибка бэктеста: {exc}")


async def backtest_detail(request: web.Request) -> web.Response:
    run = storage.get_run(int(request.match_info["run_id"]))
    if run is None:
        return _error_page(request, "Бэктест не найден.")
    result = run["result"] or {}
    return aiohttp_jinja2.render_template(
        "result.html",
        request,
        {
            "run": run,
            "result": result,
            "equity_json": json.dumps(result.get("equity_curve", [])),
        },
    )


async def live_page(request: web.Request) -> web.Response:
    return aiohttp_jinja2.render_template(
        "live.html",
        request,
        {
            "status": live_trader.snapshot(),
            "strategies": STRATEGIES,
            "has_token": bool(settings.tinkoff_token()),
            "live_intervals": TICKER_INTERVAL_LABELS,
        },
    )


async def live_data(request: web.Request) -> web.Response:
    ctx = {
        "status": live_trader.snapshot(),
        "has_token": bool(settings.tinkoff_token()),
    }
    return aiohttp_jinja2.render_template("_live_status.html", request, ctx)


async def live_start(request: web.Request) -> web.Response:
    try:
        await live_trader.start()
        msg = "Live-цикл запущен"
    except RuntimeError as exc:
        msg = str(exc)
    return web.Response(text=f"<span class='chip'>{msg}</span>", content_type="text/html")


async def live_stop(request: web.Request) -> web.Response:
    await live_trader.stop()
    return web.Response(text="<span class='chip'>Live-цикл остановлен</span>", content_type="text/html")


async def live_strategy(request: web.Request) -> web.Response:
    form = await request.post()
    key = form.get("strategy", "")
    try:
        live_trader.set_strategy(key)
        msg = f"Стратегия: {STRATEGIES[key]['name']}"
    except (ValueError, KeyError):
        msg = "Неизвестная стратегия"
    return web.Response(text=f"<span class='chip'>{msg}</span>", content_type="text/html")


async def live_dryrun(request: web.Request) -> web.Response:
    form = await request.post()
    dry_run = form.get("dry_run", "true").lower() == "true"
    live_trader.set_dry_run(dry_run)
    mode = "dry-run" if dry_run else "LIVE"
    return web.Response(text=f"<span class='chip'>Режим: {mode}</span>", content_type="text/html")


TICKER_INTERVAL_LABELS = {
    "1min": "1 минута",
    "5min": "5 минут",
    "15min": "15 минут",
    "hour": "1 час",
    "day": "1 день",
    "week": "1 неделя",
    "month": "1 месяц",
}


def create_app() -> web.Application:
    app = web.Application(middlewares=[_auth_middleware, _no_cache_middleware])
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
        context_processors=[aiohttp_jinja2.request_processor],
    )
    app.router.add_get("/login", login_page)
    app.router.add_post("/login", login_post)
    app.router.add_post("/logout", logout)
    app.router.add_get("/watchlist", watchlist_page)
    app.router.add_post("/watchlist/add", watchlist_add)
    app.router.add_post("/watchlist/remove", watchlist_remove)
    app.router.add_get("/settings", settings_page)
    app.router.add_post("/settings", settings_save)
    app.router.add_get("/", index)
    app.router.add_post("/backtest/run", backtest_run)
    app.router.add_get("/backtest/{run_id}", backtest_detail)
    app.router.add_post("/data/download", data_download)
    app.router.add_get("/data/status", data_status)
    app.router.add_post("/data/download/start", data_download_start)
    app.router.add_get("/data/download/status", data_download_status)
    app.router.add_get("/data/download/result", data_download_result)
    app.router.add_get("/live", live_page)
    app.router.add_get("/live/data", live_data)
    app.router.add_post("/live/start", live_start)
    app.router.add_post("/live/stop", live_stop)
    app.router.add_post("/live/strategy", live_strategy)
    app.router.add_post("/live/dryrun", live_dryrun)
    app.router.add_static("/static", Path(__file__).resolve().parent / "static")
    return app
