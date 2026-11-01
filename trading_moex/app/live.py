"""Live-торговля: сигналы на свежих свечах, исполнение через T-Bank Invest API.

По умолчанию dry-run (реальные ордера не выставляются). Состояние сессии
хранится в памяти и доступно веб-дашборду.
"""

import asyncio
import inspect
import logging
from math import isfinite
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd
from .timezones import as_utc_naive_index

from . import config
from . import risk as risk_module
from . import settings as app_settings
from . import signals as sig
from .strategies import STRATEGIES
from .skills.context import TradeContext
from .skills.pretrade import check_pretrade

logger = logging.getLogger("moex_trader.live")

TICKER_LIVE_INTERVALS = {
    "1min": "1_MIN",
    "5min": "5_MIN",
    "15min": "15_MIN",
    "30min": "30_MIN",
    "hour": "HOUR",
    "day": "DAY",
    "week": "WEEK",
    "month": "MONTH",
}

_LIVE_BARS = 200

# Стратегии, пригодные для live-цикла (имеют функцию сигналов в SIGNAL_FUNCS).
# Остальные из STRATEGIES — только бэктест (портфельные/фундаментальные).
LIVE_STRATEGIES = frozenset(sig.SIGNAL_FUNCS)

# Максимальный период запроса свечей по интервалу (лимит T-Bank Invest API,
# превышение даёт ошибку 30014). Дольше — API отклонит запрос.
_MAX_LOOKBACK = {
    "1_MIN": timedelta(days=1),
    "2_MIN": timedelta(days=1),
    "3_MIN": timedelta(days=7),
    "5_MIN": timedelta(days=7),
    "10_MIN": timedelta(days=14),
    "15_MIN": timedelta(days=31),
    "30_MIN": timedelta(days=90),
    "HOUR": timedelta(days=31),
    "DAY": timedelta(days=365),
    "WEEK": timedelta(days=730),
    "MONTH": timedelta(days=3650),
}

# Длительность одного бара в секундах (для расчёта периода под нужное число баров)
_INTERVAL_SECONDS = {
    "1_MIN": 60,
    "2_MIN": 120,
    "3_MIN": 180,
    "5_MIN": 300,
    "10_MIN": 600,
    "15_MIN": 900,
    "30_MIN": 1800,
    "HOUR": 3600,
    "DAY": 86400,
    "WEEK": 7 * 86400,
    "MONTH": 30 * 86400,
}

_ORDER_CONFIRM_ATTEMPTS = 5
_ORDER_CONFIRM_DELAY = 0.2


def _order_status_name(status) -> str:
    """Нормализовать enum/строку статуса заявки без зависимости от SDK enum."""
    name = getattr(status, "name", None)
    if name:
        return str(name).upper()
    return str(status or "").upper().replace(".", "_")


def _order_lots(state, field: str, default: int = 0) -> int:
    try:
        return int(getattr(state, field, default) or default)
    except (TypeError, ValueError):
        return default


def _watchlist() -> list[str]:
    """Тикеры для live: приоритет у watchlist из БД, иначе из .env."""
    from . import storage

    stored = storage.list_watchlist()
    if stored:
        return stored
    return list(config.WATCH_TICKERS)


def _signal_kwargs(func, params: dict) -> dict:
    """Отфильтровать параметры стратегии под сигнатуру pandas-функции.

    В ``strategy_params`` лежат и риск-параметры, которые сигнал-функции
    не принимают — их нужно отсечь, иначе TypeError. Если функция объявляет
    ``**kwargs`` (VAR_KEYWORD, напр. ``fib_pullback_signal``), пропускаем все
    параметры — она принимает их сама.
    """
    sig_par = inspect.signature(func).parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_par.values()):
        return {k: v for k, v in params.items() if k != "df"}
    return {k: v for k, v in params.items() if k in sig_par and k != "df"}


def _money_to_float(value) -> float:
    if value is None:
        return 0.0
    return value.units + value.nano / 1_000_000_000


def _candles_from(candle_name: str, now: datetime) -> datetime:
    """Начало периода для запроса свечей: min(нужно баров, лимит API)."""
    span = _INTERVAL_SECONDS.get(candle_name, 3600) * _LIVE_BARS
    needed = timedelta(seconds=span)
    lookback = _MAX_LOOKBACK.get(candle_name, timedelta(days=31))
    return now - min(needed, lookback)


def _candles_to_df(candles):
    rows = []
    for c in candles:
        rows.append(
            {
                "begin": c.time,
                "open": _money_to_float(c.open),
                "high": _money_to_float(c.high),
                "low": _money_to_float(c.low),
                "close": _money_to_float(c.close),
                "volume": float(c.volume or 0),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("begin").sort_index()
    df.index = as_utc_naive_index(df.index)
    return df[["open", "high", "low", "close", "volume"]]


def _closed_candles(df: pd.DataFrame, candle_name: str, now: datetime | None = None) -> pd.DataFrame:
    """Оставить только свечи, чей интервал уже завершился."""
    if df.empty:
        return df
    now_ts = pd.Timestamp(now or datetime.now(timezone.utc))
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize("UTC")
    else:
        now_ts = now_ts.tz_convert("UTC")
    last_ts = pd.Timestamp(df.index[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    else:
        last_ts = last_ts.tz_convert("UTC")
    seconds = _INTERVAL_SECONDS.get(candle_name)
    if seconds and last_ts + pd.Timedelta(seconds=seconds) > now_ts:
        return df.iloc[:-1]
    return df


class LiveTrader:
    """Один live-цикл на T-Bank; управляется из веб-дашборда."""

    def __init__(self) -> None:
        self.running = False
        self.dry_run = config.DRY_RUN
        self.tickers = list(config.WATCH_TICKERS)
        self.poll_interval = config.POLL_INTERVAL
        self.strategy = "donchian"
        self.strategy_params: dict = {}
        self.quantity = int(getattr(config, "TRADER_QUANTITY", "1") or 1)
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._equity = 100_000.0
        self._available_cash = self._equity
        self.entries: dict[str, dict] = {}
        self._last_reconciliation_issue: tuple[str, ...] = ()
        self._circuit = {
            "day": None,
            "day_start_equity": None,
            "peak_equity": None,
            "tripped": False,
            "reason": None,
            "alert_sent": False,
            "alert_key": None,
        }
        self._restore_state()
        self.status: dict = {
            "running": False,
            "dry_run": self.dry_run,
            "strategy": self.strategy,
            "last_update": None,
            "prices": [],
            "portfolio": [],
            "signals": {},
            "log": [],
            "last_error": None,
            "reconciliation": {"ok": True, "issues": []},
            "circuit_breaker": dict(self._circuit),
            "risk": self._risk_snapshot(),
        }

    def _restore_state(self) -> None:
        """Восстановить настройки и открытые позиции из БД."""
        try:
            saved = app_settings.load_live_state()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось загрузить live-состояние: %s", exc)
            return
        strategy = saved.get("strategy") or self.strategy
        if strategy in STRATEGIES and strategy in LIVE_STRATEGIES:
            self.strategy = strategy
            defaults = {p["key"]: p["default"] for p in STRATEGIES[strategy]["params"]}
            for key, value in (saved.get("strategy_params") or {}).items():
                if key in defaults:
                    spec = next(p for p in STRATEGIES[strategy]["params"] if p["key"] == key)
                    try:
                        value = int(value) if spec["type"] == "int" else float(value)
                    except (TypeError, ValueError):
                        value = defaults[key]
                    defaults[key] = value
            self.strategy_params = defaults
        dry_run = saved.get("dry_run")
        if isinstance(dry_run, bool):
            self.dry_run = dry_run
        try:
            entries = app_settings.load_live_entries()
            self.entries = {
                ticker: entry for ticker, entry in entries.items()
                if isinstance(ticker, str) and isinstance(entry, dict)
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось загрузить открытые live-позиции: %s", exc)
        try:
            saved_circuit = app_settings.load_circuit_state()
            if isinstance(saved_circuit, dict):
                self._circuit.update({key: saved_circuit[key] for key in self._circuit if key in saved_circuit})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось загрузить circuit breaker: %s", exc)

    def _save_entries(self) -> None:
        """Сохранить локальный снимок позиций после подтверждённого действия."""
        app_settings.save_live_entries(self.entries)

    # ── Управление ───────────────────────────────────────────────────────────

    def set_strategy(self, key: str) -> None:
        if self.running:
            raise RuntimeError("Сначала остановите live-цикл перед сменой стратегии")
        if key not in STRATEGIES:
            raise ValueError(f"Неизвестная стратегия {key!r}")
        if key not in LIVE_STRATEGIES:
            raise ValueError(
                f"Стратегия {key!r} доступна только для бэктеста, live-цикл её не поддерживает"
            )
        self.strategy = key
        self.strategy_params = {p["key"]: p["default"] for p in STRATEGIES[key]["params"]}
        self.entries.clear()
        self._save_entries()
        app_settings.save_live_state(self.strategy, self.dry_run, self.strategy_params)
        self.status["strategy"] = self.strategy
        self.status["entries"] = {}

    def set_dry_run(self, dry_run: bool) -> None:
        if self.running and bool(dry_run) != self.dry_run:
            raise RuntimeError("Сначала остановите live-цикл перед сменой режима")
        self.dry_run = bool(dry_run)
        app_settings.save_live_state(self.strategy, self.dry_run, self.strategy_params)
        self.status["dry_run"] = self.dry_run

    def reset_circuit_breaker(self) -> None:
        """Сбросить circuit breaker только до следующего цикла измерений."""
        if self.running:
            raise RuntimeError("Сначала остановите live-цикл")
        self._circuit.update({
            "day": None,
            "day_start_equity": None,
            "peak_equity": None,
            "tripped": False,
            "reason": None,
            "alert_sent": False,
            "alert_key": None,
        })
        app_settings.save_circuit_state(self._circuit)
        self.status["circuit_breaker"] = dict(self._circuit)
        self.status["risk"] = self._risk_snapshot()
        self._log("Circuit breaker сброшен вручную; baseline будет установлен при запуске")

    async def start(self) -> None:
        async with self._lock:
            if self.running:
                return
            if not app_settings.tinkoff_token():
                raise RuntimeError("TINKOFF_API_TOKEN не задан — live-торговля недоступна")
            errors, warnings = config.live_config_issues(
                dry_run=self.dry_run,
                web_password_configured=bool(app_settings.get("TRADER_WEB_PASSWORD")),
                token_configured=bool(app_settings.tinkoff_token()),
            )
            for warning in warnings:
                logger.warning("Live config: %s", warning)
            if errors:
                raise RuntimeError("Некорректная конфигурация live: " + "; ".join(errors))
            self.running = True
            self.status["running"] = True
            self.status["last_error"] = None
            self._log(f"Live-цикл запущен (dry_run={self.dry_run}, стратегия={self.strategy})")
        self._task = asyncio.get_running_loop().create_task(self._worker())
        logger.info("LiveTrader started")

    async def stop(self) -> None:
        async with self._lock:
            if not self.running:
                return
            self.running = False
            self.status["running"] = False
            self._log("Live-цикл остановлен")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def snapshot(self) -> dict:
        return dict(self.status)

    # ── Рабочий цикл ─────────────────────────────────────────────────────────

    async def _worker(self) -> None:
        while True:
            async with self._lock:
                running = self.running
            if not running:
                break
            try:
                await self._cycle()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ошибка live-цикла: %s", exc)
                self.status["last_error"] = str(exc)
                self._log(f"Ошибка: {exc}")
            await asyncio.sleep(self.poll_interval)

    async def _cycle(self) -> None:
        from tinkoff.invest import AsyncClient

        from . import tinkoff_ssl

        tinkoff_ssl.install_ru_ca()

        self.tickers = _watchlist()
        async with AsyncClient(token=app_settings.tinkoff_token(), app_name="moex-trader") as client:
            accounts = await client.users.get_accounts()
            if not accounts.accounts:
                raise RuntimeError("Нет доступных счетов в T-Bank")
            account_id = accounts.accounts[0].id

            portfolio = await client.operations.get_portfolio(account_id=account_id)
            self._equity = self._portfolio_value(portfolio)
            self._available_cash = await self._available_cash_from_broker(
                client, account_id, portfolio
            )
            self._update_circuit(self._equity)
            self.status["circuit_breaker"] = dict(self._circuit)
            self.status["risk"] = self._risk_snapshot()

            figis = await self._resolve_figis(client)
            prices = await self._last_prices(client, figis)
            positions = self._positions_from_portfolio(portfolio)
            reconciliation = self._reconcile_positions(figis, positions)
            self.status["reconciliation"] = reconciliation
            if not self.dry_run and not reconciliation["ok"]:
                issues = tuple(reconciliation["issues"])
                if issues != self._last_reconciliation_issue:
                    self._log("Reconciliation BLOCKED: " + "; ".join(issues))
                    self._last_reconciliation_issue = issues
                self.status["last_error"] = "Расхождение локальных и биржевых позиций"
                self.status["prices"] = prices
                self.status["portfolio"] = positions
                self.status["signals"] = {}
                self.status["entries"] = {t: e for t, e in self.entries.items()}
                self.status["last_update"] = datetime.now(timezone.utc).isoformat()
                return
            self._last_reconciliation_issue = ()
            signals = await self._compute_signals(client, figis)
            await self._act(
                client, account_id, figis, signals, positions, prices,
                allow_entries=not self._circuit["tripped"],
            )

            self.status["prices"] = prices
            self.status["portfolio"] = positions
            self.status["signals"] = signals
            self.status["entries"] = {t: e for t, e in self.entries.items()}
            self.status["last_update"] = datetime.now(timezone.utc).isoformat()
            self.status["last_error"] = None

    async def _resolve_figis(self, client) -> dict[str, str]:
        """FIGI по тикеру. Предпочитаем основную площадку MOEX.

        ``find_instrument`` возвращает много дублей с разными class_code
        (SPEQ, 37M, BEB, RDL и т.п.) — свечи есть только у TQBR/SMAL
        (реальные площадки), остальные дают пустой список. Берём первый
        инструмент с самым приоритетным классом.
        """
        priority = {"TQBR": 0, "SMAL": 1}
        figis: dict[str, str] = {}
        for ticker in self.tickers:
            try:
                resp = await client.instruments.find_instrument(query=ticker)
                matches = [
                    item for item in resp.instruments
                    if item.ticker.upper() == ticker.upper() and item.figi
                ]
                matches.sort(
                    key=lambda item: (
                        priority.get(getattr(item, "class_code", ""), 9),
                        item.instrument_type != "share",
                    )
                )
                if matches:
                    figis[ticker] = matches[0].figi
                elif resp.instruments:
                    figis[ticker] = resp.instruments[0].figi
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось найти FIGI для %s: %s", ticker, exc)
        return figis

    async def _last_prices(self, client, figis: dict[str, str]) -> list[dict]:
        if not figis:
            return []
        resp = await client.market_data.get_last_prices(figi=list(figis.values()))
        price_map = {item.figi: _money_to_float(item.price) for item in resp.last_prices}
        out = []
        for ticker, figi in figis.items():
            out.append(
                {
                    "ticker": ticker,
                    "figi": figi,
                    "price": round(price_map.get(figi, 0.0), 4),
                }
            )
        return out

    def _positions_from_portfolio(self, portfolio) -> list[dict]:
        out = []
        for pos in portfolio.positions:
            raw_qty = _money_to_float(pos.quantity)
            if raw_qty == 0:
                continue
            out.append(
                {
                    "figi": pos.figi,
                    # T-Bank represents a short position with a negative quantity,
                    # while order close quantity must be a positive integer.
                    "quantity": round(abs(raw_qty), 4),
                    "direction": "short" if raw_qty < 0 else "long",
                    "price": round(_money_to_float(pos.current_price), 4),
                    "pnl": round(_money_to_float(pos.expected_yield), 2),
                }
            )
        return out

    def _portfolio_value(self, portfolio) -> float:
        """Стоимость портфеля (акции + валюта + пр.) для расчёта размера позиции."""
        total = 0.0
        for name in (
            "total_amount_shares",
            "total_amount_bonds",
            "total_amount_futures",
            "total_amount_currencies",
        ):
            total += _money_to_float(getattr(portfolio, name, None))
        return total if total > 0 else float(getattr(config, "TRADER_EQUITY", 100_000) or 100_000)

    def _portfolio_cash(self, portfolio) -> float:
        """Fallback для старых SDK: денежная часть стоимости портфеля."""
        cash = _money_to_float(getattr(portfolio, "total_amount_currencies", None))
        return max(cash, 0.0)

    async def _available_cash_from_broker(self, client, account_id: str, portfolio) -> float:
        """Получить свободные RUB из positions, не включая заблокированные деньги."""
        try:
            positions = await client.operations.get_positions(account_id=account_id)
            total = 0.0
            found_rub = False
            for money in getattr(positions, "money", ()):
                currency = str(getattr(money, "currency", "")).lower()
                if currency not in ("rub", "rur", "₽"):
                    continue
                found_rub = True
                available = getattr(money, "available", None)
                if available is not None:
                    total += max(_money_to_float(available), 0.0)
                    continue
                balance = _money_to_float(money)
                blocked = _money_to_float(getattr(money, "blocked", None))
                total += max(balance - blocked, 0.0)
            if found_rub:
                return total
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось получить свободные средства: %s", exc)
        return self._portfolio_cash(portfolio)

    def _cap_position_size(self, size: int, price: float, direction: str) -> int:
        """Ограничить заявку equity-лимитом и доступными деньгами."""
        if size <= 0 or price <= 0:
            return 0
        max_pct = min(max(float(getattr(config, "TRADER_MAX_POSITION_PCT", 50.0)), 0.0), 100.0)
        max_value = self._equity * max_pct / 100.0
        if direction == "long":
            max_value = min(max_value, self._available_cash)
        capped = min(size, int(max_value / price))
        return max(capped, 0)

    def _update_circuit(self, equity: float, now: datetime | None = None) -> None:
        """Обновить дневной baseline/peak и защёлкнуть лимит убытка."""
        now = now or datetime.now(timezone.utc)
        day = now.date().isoformat()
        if self._circuit.get("day") != day or not self._circuit.get("day_start_equity"):
            previous_peak = float(self._circuit.get("peak_equity") or 0.0)
            previous_alert_key = self._circuit.get("alert_key")
            previous_alert_sent = bool(self._circuit.get("alert_sent"))
            self._circuit.update({
                "day": day,
                "day_start_equity": equity,
                "peak_equity": max(previous_peak, equity),
                "tripped": False,
                "reason": None,
                # A drawdown is not reset at UTC midnight. Keep its alert
                # state so a persistent drawdown does not produce duplicates.
                "alert_sent": previous_alert_sent if previous_alert_key == "drawdown" else False,
                "alert_key": previous_alert_key if previous_alert_key == "drawdown" else None,
            })
        else:
            self._circuit["peak_equity"] = max(float(self._circuit.get("peak_equity") or equity), equity)

        daily_loss_pct = (
            (float(self._circuit["day_start_equity"]) - equity)
            / float(self._circuit["day_start_equity"])
            * 100
        )
        peak = float(self._circuit.get("peak_equity") or equity)
        drawdown_pct = (peak - equity) / peak * 100 if peak > 0 else 0.0
        max_daily = max(float(getattr(config, "TRADER_MAX_DAILY_LOSS_PCT", 0.0)), 0.0)
        max_drawdown = max(float(getattr(config, "TRADER_MAX_DRAWDOWN_PCT", 0.0)), 0.0)
        reason = None
        reason_key = None
        # Drawdown is portfolio-wide and survives a UTC-day rollover, so it
        # takes precedence when both limits are exceeded.
        if max_drawdown and drawdown_pct >= max_drawdown:
            reason = f"просадка {drawdown_pct:.2f}% >= {max_drawdown:.2f}%"
            reason_key = "drawdown"
        elif max_daily and daily_loss_pct >= max_daily:
            reason = f"дневной убыток {daily_loss_pct:.2f}% >= {max_daily:.2f}%"
            reason_key = "daily_loss"
        if reason and not self._circuit.get("tripped"):
            self._log(f"[circuit-breaker] {reason}; новые входы заблокированы")
            if self._circuit.get("alert_key") != reason_key:
                self._circuit["alert_sent"] = False
            self._schedule_circuit_alert(reason, reason_key)
        if reason:
            self._circuit.update({"tripped": True, "reason": reason, "alert_key": reason_key})
        app_settings.save_circuit_state(self._circuit)

    def _risk_snapshot(self) -> dict:
        """Текущие risk-метрики для дашборда без секретов."""
        start = float(self._circuit.get("day_start_equity") or self._equity)
        peak = float(self._circuit.get("peak_equity") or self._equity)
        daily_loss = (start - self._equity) / start * 100 if start > 0 else 0.0
        drawdown = (peak - self._equity) / peak * 100 if peak > 0 else 0.0
        return {
            "equity": round(self._equity, 2),
            "available_cash": round(self._available_cash, 2),
            "day_start_equity": round(start, 2),
            "peak_equity": round(peak, 2),
            "daily_loss_pct": round(max(daily_loss, 0.0), 2),
            "drawdown_pct": round(max(drawdown, 0.0), 2),
            "max_daily_loss_pct": float(getattr(config, "TRADER_MAX_DAILY_LOSS_PCT", 0.0)),
            "max_drawdown_pct": float(getattr(config, "TRADER_MAX_DRAWDOWN_PCT", 0.0)),
        }

    def _schedule_circuit_alert(self, reason: str, alert_key: str | None = None) -> None:
        """Запланировать одно уведомление о переходе circuit breaker в tripped."""
        if self._circuit.get("alert_sent") and self._circuit.get("alert_key") == alert_key:
            return
        self._circuit["alert_sent"] = True
        self._circuit["alert_key"] = alert_key
        app_settings.save_circuit_state(self._circuit)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("Нет event loop для Telegram-алерта circuit breaker")
            return
        loop.create_task(self._send_circuit_alert(reason))

    async def _send_circuit_alert(self, reason: str) -> None:
        from .signal_notifier import send_telegram_message

        text = (
            "⚠️ CIRCUIT BREAKER MOEX\n"
            f"Новые входы заблокированы: {reason}\n"
            f"Equity: {self._equity:.2f}"
        )
        try:
            sent = await send_telegram_message(text)
            if not sent:
                logger.warning("Circuit breaker: Telegram-алерт не отправлен")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Circuit breaker: ошибка Telegram-алерта: %s", exc)

    def _reconcile_positions(self, figis: dict[str, str], positions: list[dict]) -> dict:
        """Сверить локальные записи с фактическими позициями брокера.

        В live-режиме любое отличие блокирует новые заявки: это безопаснее, чем
        пытаться угадать, был ли предыдущий ордер исполнен частично или вручную.
        В dry-run проверка не используется, поскольку виртуальные entries не
        обязаны присутствовать в брокерском портфеле.
        """
        expected: dict[str, tuple[float, str]] = {}
        issues: list[str] = []
        for ticker, entry in self.entries.items():
            figi = entry.get("figi") or figis.get(ticker)
            if not figi:
                issues.append(f"{ticker}: FIGI локальной позиции не найден")
                continue
            try:
                quantity = float(entry.get("size", 0))
            except (TypeError, ValueError):
                quantity = 0.0
            expected[figi] = (quantity, entry.get("direction", "long"))

        watched_figis = set(figis.values())
        actual = {
            position["figi"]: (float(position["quantity"]), position.get("direction", "long"))
            for position in positions
            if position.get("figi") in watched_figis
        }
        for figi in sorted(set(expected) | set(actual)):
            if figi not in expected:
                issues.append(f"{figi}: биржевая позиция отсутствует локально")
                continue
            if figi not in actual:
                issues.append(f"{figi}: локальная позиция отсутствует на бирже")
                continue
            expected_qty, expected_direction = expected[figi]
            actual_qty, actual_direction = actual[figi]
            if expected_direction != actual_direction:
                issues.append(
                    f"{figi}: направление local={expected_direction}, broker={actual_direction}"
                )
            if abs(expected_qty - actual_qty) > 1e-9:
                issues.append(f"{figi}: количество local={expected_qty:g}, broker={actual_qty:g}")
        return {"ok": not issues, "issues": issues}

    async def _candles_df(self, client, figi: str) -> pd.DataFrame:
        now = datetime.now(timezone.utc)
        interval = getattr(config, "TRADER_LIVE_INTERVAL", "hour")
        from tinkoff.invest import CandleInterval

        candle_name = TICKER_LIVE_INTERVALS.get(interval, "HOUR")
        candle_interval = getattr(CandleInterval, f"CANDLE_INTERVAL_{candle_name}")
        from_ = _candles_from(candle_name, now)
        try:
            resp = await client.market_data.get_candles(
                instrument_id=figi, from_=from_, to=now, interval=candle_interval
            )
        except TypeError:
            resp = await client.market_data.get_candles(
                figi=figi, from_=from_, to=now, interval=candle_interval
            )
        return _closed_candles(_candles_to_df(resp.candles), candle_name, now)

    async def _compute_signals(self, client, figis: dict[str, str]) -> dict[str, dict]:
        """Сигнал по каждому тикеру + уровни стоп-лосса и тейк-профита.

        Возвращает ``{ticker: {action, stop, target}}``. Уровни считаются от ATR
        и R:R, применяются трендовый фильтр EMA и риск-параметры стратегии.
        """
        func = sig.SIGNAL_FUNCS.get(self.strategy)
        if func is None:
            raise RuntimeError(
                f"Стратегия {self.strategy!r} не поддерживается live-циклом "
                f"(выберите одну из: {', '.join(sorted(LIVE_STRATEGIES))})"
            )
        trend_period = int(self.strategy_params.get("trend_period", 0) or 0)
        atr_period = int(self.strategy_params.get("atr_period", 14) or 14)
        atr_mult = float(self.strategy_params.get("atr_stop_mult", 1.5) or 1.5)
        rr_ratio = float(self.strategy_params.get("rr_ratio", 2.0) or 2.0)

        out: dict[str, dict] = {}
        for ticker, figi in figis.items():
            entry: dict = {"action": "hold", "stop": None, "target": None}
            df = await self._candles_df(client, figi)
            if not df.empty and len(df) >= 2:
                kwargs = _signal_kwargs(func, self.strategy_params)
                # Per-ticker overrides (TICKER_OVERRIDES) применяются поверх
                # глобальных параметров стратегии (например, direction/шорт).
                from .strategies import TICKER_OVERRIDES as _TO

                ticker_over = _TO.get((self.strategy, ticker.upper()), {})
                if ticker_over:
                    kwargs = {**kwargs, **ticker_over}
                if self.strategy == "roe_portfolio":
                    from . import storage

                    kwargs["fundamentals"] = storage.load_fundamentals(ticker)
                elif self.strategy == "fib_pullback" and int(
                    self.strategy_params.get("use_htf", 0)
                ):
                    # Глобальный тренд (принцип 5): LTF-вход только в направлении
                    # тренда старшего таймфрейма (дневные свечи из БД).
                    try:
                        from . import storage
                        from . import fib_pullback as fib_module

                        htf_raw = storage.get_candles(ticker, "1day")
                        if not htf_raw.empty:
                            kwargs["htf_df"] = fib_module.prepare_ohlc(htf_raw)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Не удалось получить дневные свечи для %s: %s", ticker, exc)
                position = func(df, **kwargs)
                if position.empty:
                    entry["action"] = "hold"
                else:
                    if trend_period:
                        position = sig.apply_trend_filter(position, df["close"], trend_period)
                    entry["action"] = sig.signal_from_position(position)
                    last_pos = bool(position.iloc[-1])
                    if last_pos:
                        # позиция удерживается — считаем уровни SL/TP, чтобы
                        # отслеживать их на каждом цикле (а не только на входе)
                        last = df.iloc[-1]
                        atr_val = float(risk_module.atr(df, atr_period).iloc[-1])
                        if atr_val != atr_val or atr_val <= 0:  # NaN / вырожденные данные
                            atr_val = 0.0
                        stop_dist = max(atr_val * atr_mult, float(last["close"]) * 0.005)
                        if int(position.iloc[-1]) < 0:
                            # шорт: стоп выше входа, цель ниже
                            entry["stop"] = round(float(last["close"]) + stop_dist, 4)
                            entry["target"] = round(float(last["close"]) - stop_dist * rr_ratio, 4)
                        else:
                            entry["stop"] = round(float(last["close"]) - stop_dist, 4)
                            entry["target"] = round(float(last["close"]) + stop_dist * rr_ratio, 4)
            out[ticker] = entry
        return out

    def _risk_size(self, price: float, stop: float | None) -> int:
        risk_pct = float(self.strategy_params.get("risk_pct", 1.0) or 1.0) / 100.0
        stop_dist = max(abs(price - stop), price * 0.005) if stop else 0.0
        return max(
            risk_module.position_size(self._equity, risk_pct, stop_dist, price), 1
        )

    def _run_pretrade_gate(self, ticker: str, price: float, stop: float | None,
                           target: float | None, figi: str, direction: str = "long"):
        """Запустить pre-trade проверку для тикера."""
        from .news_guard import NewsGuard

        risk_pct = float(self.strategy_params.get("risk_pct", 1.0) or 1.0)
        atr_period = int(self.strategy_params.get("atr_period", 14) or 14)

        # Проверка новостей
        guard = NewsGuard()
        news_blocked, news_reason = guard.is_blocked(ticker)

        # Контекст сделки
        ctx = TradeContext(
            ticker=ticker,
            direction=direction,
            entry=price,
            stop=stop,
            target=target,
            equity=self._equity,
            risk_pct=risk_pct,
            atr_period=atr_period,
        )

        # Regime из локальных свечей (если есть в кэше)
        regime_df = None
        try:
            from . import storage
            candles = storage.get_candles(ticker, "1day")
            if candles is not None and not candles.empty and len(candles) >= 50:
                regime_df = candles
        except Exception:  # noqa: BLE001
            pass

        return check_pretrade(
            ctx,
            regime_df=regime_df,
            min_rr=config.TRADER_SKILLS_MIN_RR,
            max_position_pct=config.TRADER_SKILLS_MAX_POSITION_PCT,
            commission_pct=config.TRADER_SKILLS_COMMISSION_PCT,
            news_blocked=news_blocked,
            news_reason=news_reason,
        )

    async def _act(self, client, account_id: str, figis: dict[str, str],
                   signals: dict[str, dict], positions: list[dict], prices: list[dict],
                   allow_entries: bool = True) -> None:
        held_figis = {p["figi"] for p in positions}
        held_qty = {p["figi"]: p["quantity"] for p in positions}
        held_directions = {p["figi"]: p.get("direction", "long") for p in positions}
        price_map = {p["ticker"]: p["price"] for p in prices}

        for ticker, figi in figis.items():
            try:
                await self._act_for(
                    client, account_id, figi, ticker, signals, prices,
                    held_figis, held_qty, held_directions, price_map, allow_entries,
                )
            except Exception as exc:  # noqa: BLE001
                # Один сбойный инструмент не должен лишать остальные позиции
                # проверки стопа; цикл продолжается на следующем тикере.
                self._log(f"[order] {ticker}: действие не выполнено: {exc}")
                self._save_entries()


    async def _act_for(self, client, account_id: str, figi: str, ticker: str,
                        signals: dict[str, dict], prices: list[dict],
                        held_figis: set, held_qty: dict, held_directions: dict,
                        price_map: dict, allow_entries: bool) -> None:
        info = signals.get(ticker, {}) or {}
        action = info.get("action", "hold")
        price = price_map.get(ticker, 0.0)
        held = self.entries.get(ticker, {})
        cur_dir = held.get("direction") or held_directions.get(figi, "long")

        if not isfinite(price) or price <= 0:
            if action != "hold" or figi in held_figis or "stop" in held:
                self._log(f"[market-data] {ticker}: действие пропущено, цена недоступна")
            return

        # 1) Выход по стоп-лоссу / тейк-профиту
        if info.get("stop") is not None and price > 0 and (figi in held_figis or "stop" in held):
            if cur_dir == "short":
                hit_stop = price >= info["stop"]
                hit_target = info.get("target") is not None and price <= info["target"]
                close_action, close_label = "buy", "COVER"
            else:
                hit_stop = price <= info["stop"]
                hit_target = info.get("target") is not None and price >= info["target"]
                close_action, close_label = "sell", "CLOSE"
            if hit_stop:
                await self._submit(client, account_id, figi, close_action,
                                   held_qty.get(figi, self.quantity), f"SL {ticker} по {price}")
                self.entries.pop(ticker, None)
                self._save_entries()
                return
            if hit_target:
                await self._submit(client, account_id, figi, close_action,
                                   held_qty.get(figi, self.quantity), f"TP {ticker} по {price}")
                self.entries.pop(ticker, None)
                self._save_entries()
                return

        if action == "hold":
            return
        if action in ("buy", "short"):
            if not allow_entries:
                self._log(f"[circuit-breaker] {ticker}: вход заблокирован")
                return
            if figi in held_figis or "stop" in held:
                return
            direction = "long" if action == "buy" else "short"
            # Pre-trade gate: проверка перед входом
            if config.TRADER_SKILLS_ENABLED:
                gate_report = self._run_pretrade_gate(
                    ticker, price, info.get("stop"), info.get("target"), figi, direction
                )
                if gate_report.verdict == "BLOCKED":
                    self._log(
                        f"[gate] {ticker}: BLOCKED — {gate_report.first_blocker}"
                    )
                    return
                if gate_report.verdict == "RESIZE" and config.TRADER_SKILLS_MODE == "enforce":
                    original_size = self._risk_size(price, info.get("stop"))
                    gate_size = gate_report.checks.get("sizing", {}).get("size", original_size)
                    size = min(original_size, gate_size)
                    self._log(f"[gate] {ticker}: RESIZE → size={size}")
                else:
                    size = self._risk_size(price, info.get("stop"))
                # В shadow-режиме логируем вердикт, но не блокируем
                if config.TRADER_SKILLS_MODE == "shadow":
                    self._log(
                        f"[gate:shadow] {ticker}: {gate_report.verdict}"
                        + (f" — {gate_report.first_blocker}" if gate_report.first_blocker else "")
                    )
            else:
                size = self._risk_size(price, info.get("stop"))
            size = self._cap_position_size(size, price, direction)
            if size <= 0:
                self._log(
                    f"[risk] {ticker}: заявка отклонена, недостаточно доступных средств "
                    "или превышен лимит позиции"
                )
                return
            order_id = await self._submit(
                client, account_id, figi, "sell" if action == "short" else "buy",
                size, f"{'SHORT' if action == 'short' else 'BUY'} {ticker} x{size}"
            )
            self.entries[ticker] = {
                "figi": figi,
                "entry_price": price,
                "stop": info.get("stop"),
                "target": info.get("target"),
                "size": size,
                "direction": direction,
                "order_id": order_id,
            }
            self._save_entries()
        else:  # sell / cover
            if figi not in held_figis and "stop" not in held:
                return
            close_action = "buy" if action == "cover" else "sell"
            await self._submit(client, account_id, figi, close_action,
                               held_qty.get(figi, self.quantity),
                               f"{action.upper()} {ticker}")
            self.entries.pop(ticker, None)

    async def _submit(self, client, account_id: str, figi: str, action: str,
                       size: int | float, label: str) -> str | None:
        if self.dry_run:
            self._log(f"[dry-run] {label} ({figi})")
            return None
        try:
            response = await self._post_market_order(client, account_id, figi, int(size), action)
            order_id = getattr(response, "order_id", None)
            if not order_id:
                raise RuntimeError("Биржа не вернула order_id")
            requested = int(size)
            status = ""
            executed = 0
            for attempt in range(_ORDER_CONFIRM_ATTEMPTS):
                state = await client.orders.get_order_state(
                    account_id=account_id,
                    order_id=order_id,
                )
                status = _order_status_name(getattr(state, "execution_report_status", None))
                executed = _order_lots(state, "lots_executed")
                if "EXECUTION_COMPLETE" in status and executed == requested:
                    break
                if any(marker in status for marker in ("REJECTED", "CANCELLED", "NOT_ENOUGH")):
                    break
                if attempt + 1 < _ORDER_CONFIRM_ATTEMPTS:
                    await asyncio.sleep(_ORDER_CONFIRM_DELAY)
            if "EXECUTION_COMPLETE" not in status or executed != requested:
                raise RuntimeError(
                    f"Заявка {order_id} не исполнена полностью: "
                    f"status={status or 'UNKNOWN'}, lots={executed}/{requested}"
                )
            self._log(f"[live] {label} ({figi})")
            return order_id
        except Exception as exc:  # noqa: BLE001
            self._log(f"Ошибка ордера {label}: {exc}")
            raise

    async def _post_market_order(self, client, account_id: str, figi: str, quantity: int, action: str) -> None:
        from tinkoff.invest import MoneyValue, OrderDirection, OrderType

        direction = (
            OrderDirection.ORDER_DIRECTION_BUY if action == "buy"
            else OrderDirection.ORDER_DIRECTION_SELL
        )
        kwargs = dict(
            quantity=quantity,
            price=MoneyValue(units=0, nano=0),
            direction=direction,
            account_id=account_id,
            order_type=OrderType.ORDER_TYPE_MARKET,
            order_id=uuid.uuid4().hex,
        )
        try:
            return await client.orders.post_order(**kwargs, instrument_id=figi)
        except TypeError:
            return await client.orders.post_order(**kwargs, figi=figi)

    def _log(self, message: str) -> None:
        entry = {"time": datetime.now(timezone.utc).isoformat(), "message": message}
        log = self.status["log"]
        log.append(entry)
        del log[:-40]
        logger.info("live: %s", message)


live_trader = LiveTrader()
