"""Live-торговля: сигналы на свежих свечах, исполнение через T-Bank Invest API.

По умолчанию dry-run (реальные ордера не выставляются). Состояние сессии
хранится в памяти и доступно веб-дашборду.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import config
from . import settings as app_settings
from . import signals as sig
from .strategies import STRATEGIES

logger = logging.getLogger("moex_trader.live")

TICKER_LIVE_INTERVALS = {
    "1min": "1_MIN",
    "5min": "5_MIN",
    "15min": "15_MIN",
    "hour": "HOUR",
    "day": "DAY",
    "week": "WEEK",
    "month": "MONTH",
}

_LIVE_BARS = 200


def _watchlist() -> list[str]:
    """Тикеры для live: приоритет у watchlist из БД, иначе из .env."""
    from . import storage

    stored = storage.list_watchlist()
    if stored:
        return stored
    return list(config.WATCH_TICKERS)


def _money_to_float(value) -> float:
    if value is None:
        return 0.0
    return value.units + value.nano / 1_000_000_000


def _candles_to_df(candles) -> pd.DataFrame:
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
        self.strategy = "sma_cross"
        self.strategy_params: dict = {}
        self.quantity = int(getattr(config, "TRADER_QUANTITY", "1") or 1)
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
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

    # ── Управление ───────────────────────────────────────────────────────────

    def set_strategy(self, key: str) -> None:
        if key not in STRATEGIES:
            raise ValueError(f"Неизвестная стратегия {key!r}")
        self.strategy = key
        self.strategy_params = {p["key"]: p["default"] for p in STRATEGIES[key]["params"]}

    def set_dry_run(self, dry_run: bool) -> None:
        self.dry_run = bool(dry_run)

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

        self.tickers = _watchlist()
        async with AsyncClient(token=app_settings.tinkoff_token(), app_name="moex-trader") as client:
            accounts = await client.users.get_accounts()
            if not accounts.accounts:
                raise RuntimeError("Нет доступных счетов в T-Bank")
            account_id = accounts.accounts[0].id

            figis = await self._resolve_figis(client)
            prices = await self._last_prices(client, figis)
            positions = await self._positions(client, account_id)
            signals = await self._compute_signals(client, figis)
            await self._act(client, account_id, figis, signals, positions)

            self.status["prices"] = prices
            self.status["portfolio"] = positions
            self.status["signals"] = signals
            self.status["last_update"] = datetime.now(timezone.utc).isoformat()
            self.status["last_error"] = None

    async def _resolve_figis(self, client) -> dict[str, str]:
        figis: dict[str, str] = {}
        for ticker in self.tickers:
            try:
                resp = await client.instruments.find_instrument(query=ticker)
                for item in resp.instruments:
                    if item.ticker.upper() == ticker.upper() and item.figi:
                        figis[ticker] = item.figi
                        break
                else:
                    if resp.instruments:
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

    async def _positions(self, client, account_id: str) -> list[dict]:
        portfolio = await client.operations.get_portfolio(account_id=account_id)
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

    async def _candles_df(self, client, figi: str) -> pd.DataFrame:
        now = datetime.now(timezone.utc)
        interval = getattr(config, "TRADER_LIVE_INTERVAL", "hour")
        from tinkoff.invest import CandleInterval

        candle_name = TICKER_LIVE_INTERVALS.get(interval, "HOUR")
        candle_interval = getattr(CandleInterval, f"CANDLE_INTERVAL_{candle_name}")
        from_ = now - timedelta(days=_LIVE_BARS)
        try:
            resp = await client.market_data.get_candles(
                instrument_id=figi, from_=from_, to=now, interval=candle_interval
            )
        except TypeError:
            resp = await client.market_data.get_candles(
                figi=figi, from_=from_, to=now, interval=candle_interval
            )
        return _candles_to_df(resp.candles)

    async def _compute_signals(self, client, figis: dict[str, str]) -> dict[str, str]:
        func = sig.SIGNAL_FUNCS.get(self.strategy)
        if func is None:
            return {}
        out: dict[str, str] = {}
        for ticker, figi in figis.items():
            df = await self._candles_df(client, figi)
            if df.empty or len(df) < 2:
                out[ticker] = "hold"
                continue
            position = func(df, **self.strategy_params)
            out[ticker] = sig.signal_from_position(position)
        return out

    async def _act(self, client, account_id: str, figis: dict[str, str],
                   signals: dict[str, str], positions: list[dict]) -> None:
        held_figis = {p["figi"] for p in positions}
        for ticker, figi in figis.items():
            action = signals.get(ticker, "hold")
            if action == "hold":
                continue
            if action == "buy" and figi in held_figis:
                continue
            if action == "sell" and figi not in held_figis:
                continue
            direction_name = "BUY" if action == "buy" else "SELL"
            if self.dry_run:
                self._log(f"[dry-run] {direction_name} {ticker} ({figi}) x{self.quantity}")
                continue
            try:
                await self._post_market_order(client, account_id, figi, self.quantity, action)
                self._log(f"[live] {direction_name} {ticker} ({figi}) x{self.quantity}")
            except Exception as exc:  # noqa: BLE001
                self._log(f"Ошибка ордера {ticker}: {exc}")
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
