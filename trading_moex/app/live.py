"""Live-торговля: сигналы на свежих свечах, исполнение через T-Bank Invest API.

По умолчанию dry-run (реальные ордера не выставляются). Состояние сессии
хранится в памяти и доступно веб-дашборду.
"""

import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd

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
    df.index = pd.to_datetime(df.index)
    return df[["open", "high", "low", "close", "volume"]]


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
        self.entries: dict[str, dict] = {}
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
        }

    def _restore_state(self) -> None:
        """Восстановить сохранённые настройки (стратегия, dry_run, params) из БД."""
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

    # ── Управление ───────────────────────────────────────────────────────────

    def set_strategy(self, key: str) -> None:
        if key not in STRATEGIES:
            raise ValueError(f"Неизвестная стратегия {key!r}")
        if key not in LIVE_STRATEGIES:
            raise ValueError(
                f"Стратегия {key!r} доступна только для бэктеста, live-цикл её не поддерживает"
            )
        self.strategy = key
        self.strategy_params = {p["key"]: p["default"] for p in STRATEGIES[key]["params"]}
        self.entries.clear()
        app_settings.save_live_state(self.strategy, self.dry_run, self.strategy_params)

    def set_dry_run(self, dry_run: bool) -> None:
        self.dry_run = bool(dry_run)
        app_settings.save_live_state(self.strategy, self.dry_run, self.strategy_params)

    async def start(self) -> None:
        async with self._lock:
            if self.running:
                return
            if not app_settings.tinkoff_token():
                raise RuntimeError("TINKOFF_API_TOKEN не задан — live-торговля недоступна")
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

            figis = await self._resolve_figis(client)
            prices = await self._last_prices(client, figis)
            positions = self._positions_from_portfolio(portfolio)
            signals = await self._compute_signals(client, figis)
            await self._act(client, account_id, figis, signals, positions, prices)

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
            qty = _money_to_float(pos.quantity)
            if qty <= 0:
                continue
            out.append(
                {
                    "figi": pos.figi,
                    "quantity": round(qty, 4),
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
        return _candles_to_df(resp.candles)

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
                    if bool(position.iloc[-1]):
                        # позиция удерживается — считаем уровни SL/TP, чтобы
                        # отслеживать их на каждом цикле (а не только на входе)
                        last = df.iloc[-1]
                        atr_val = float(risk_module.atr(df, atr_period).iloc[-1])
                        if atr_val != atr_val or atr_val <= 0:  # NaN / вырожденные данные
                            atr_val = 0.0
                        stop_dist = max(atr_val * atr_mult, float(last["close"]) * 0.005)
                        entry["stop"] = round(float(last["close"]) - stop_dist, 4)
                        entry["target"] = round(float(last["close"]) + stop_dist * rr_ratio, 4)
            out[ticker] = entry
        return out

    def _risk_size(self, price: float, stop: float | None) -> int:
        risk_pct = float(self.strategy_params.get("risk_pct", 1.0) or 1.0) / 100.0
        stop_dist = max((price - stop), price * 0.005) if stop else 0.0
        return max(
            risk_module.position_size(self._equity, risk_pct, stop_dist, price), 1
        )

    def _run_pretrade_gate(self, ticker: str, price: float, stop: float | None,
                           target: float | None, figi: str):
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
            direction="long",
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
                   signals: dict[str, dict], positions: list[dict], prices: list[dict]) -> None:
        held_figis = {p["figi"] for p in positions}
        held_qty = {p["figi"]: p["quantity"] for p in positions}
        price_map = {p["ticker"]: p["price"] for p in prices}

        for ticker, figi in figis.items():
            info = signals.get(ticker, {}) or {}
            action = info.get("action", "hold")
            price = price_map.get(ticker, 0.0)

            # 1) Выход по стоп-лоссу / тейк-профиту
            if info.get("stop") is not None and price > 0 and figi in held_figis:
                if price <= info["stop"]:
                    await self._submit(client, account_id, figi, "sell",
                                       held_qty.get(figi, self.quantity), f"SL {ticker} по {price}")
                    self.entries.pop(ticker, None)
                    continue
                if info.get("target") is not None and price >= info["target"]:
                    await self._submit(client, account_id, figi, "sell",
                                       held_qty.get(figi, self.quantity), f"TP {ticker} по {price}")
                    self.entries.pop(ticker, None)
                    continue

            if action == "hold":
                continue
            if action == "buy":
                if figi in held_figis:
                    continue
                # Pre-trade gate: проверка перед входом
                if config.TRADER_SKILLS_ENABLED:
                    gate_report = self._run_pretrade_gate(
                        ticker, price, info.get("stop"), info.get("target"), figi
                    )
                    if gate_report.verdict == "BLOCKED":
                        self._log(
                            f"[gate] {ticker}: BLOCKED — {gate_report.first_blocker}"
                        )
                        continue
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
                await self._submit(client, account_id, figi, "buy", size, f"BUY {ticker} x{size}")
                self.entries[ticker] = {
                    "entry_price": price,
                    "stop": info.get("stop"),
                    "target": info.get("target"),
                    "size": size,
                }
            else:  # sell
                if figi not in held_figis:
                    continue
                await self._submit(client, account_id, figi, "sell",
                                   held_qty.get(figi, self.quantity), f"SELL {ticker}")
                self.entries.pop(ticker, None)

    async def _submit(self, client, account_id: str, figi: str, action: str,
                      size: int | float, label: str) -> None:
        if self.dry_run:
            self._log(f"[dry-run] {label} ({figi})")
            return
        try:
            await self._post_market_order(client, account_id, figi, int(size), action)
            self._log(f"[live] {label} ({figi})")
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
