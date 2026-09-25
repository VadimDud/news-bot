"""Continuous closed-candle collector for adaptive scenario statistics.

The collector reads the local candle cache and writes only derived pattern
outcomes. It has no broker client and cannot submit or modify orders.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from . import storage
from .adaptive_scenarios import extract_pattern_records, store_pattern_records

logger = logging.getLogger(__name__)


def configured_tickers() -> tuple[str, ...]:
    raw = os.environ.get("TRADER_ADAPTIVE_TICKERS", "T")
    tickers = tuple(dict.fromkeys(item.strip().upper() for item in raw.split(",") if item.strip()))
    return tickers or ("T",)


def configured_interval() -> int:
    raw = os.environ.get("TRADER_ADAPTIVE_INTERVAL", "60")
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        interval = 60
    return max(15, interval)


def configured_enabled() -> bool:
    return os.environ.get("TRADER_ADAPTIVE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


@dataclass
class CollectorStatus:
    enabled: bool = True
    running: bool = False
    interval_seconds: int = 60
    tickers: tuple[str, ...] = ("T",)
    last_run_at: str | None = None
    last_candle_at: dict[str, str] = field(default_factory=dict)
    processed_records: int = 0
    errors: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "interval_seconds": self.interval_seconds,
            "tickers": list(self.tickers),
            "last_run_at": self.last_run_at,
            "last_candle_at": dict(self.last_candle_at),
            "processed_records": self.processed_records,
            "errors": dict(self.errors),
            "mode": "statistics_only",
        }


_status = CollectorStatus(
    enabled=configured_enabled(),
    interval_seconds=configured_interval(),
    tickers=configured_tickers(),
)
_status_lock = Lock()


def status() -> dict[str, object]:
    with _status_lock:
        return _status.as_dict()


def _set_status(**updates: object) -> None:
    with _status_lock:
        for key, value in updates.items():
            setattr(_status, key, value)


def _collect_sync(db_path: str | Path, tickers: tuple[str, ...]) -> dict[str, object]:
    processed = 0
    last_candle: dict[str, str] = {}
    errors: dict[str, str] = {}
    for ticker in tickers:
        try:
            frame = storage.get_candles(ticker, "15min")
            if frame is None or frame.empty:
                errors[ticker] = "no 15min candles"
                continue
            frame = frame.rename(columns={"begin": "timestamp"})
            records = extract_pattern_records(frame, ticker=ticker)
            processed += store_pattern_records(db_path, records)
            last_candle[ticker] = str(frame["timestamp"].iloc[-1])
        except Exception as exc:  # noqa: BLE001
            errors[ticker] = str(exc)
            logger.exception("Adaptive collector failed for %s", ticker)
    return {"processed": processed, "last_candle": last_candle, "errors": errors}


async def collect_once(db_path: str | Path) -> dict[str, object]:
    """Process currently available closed candles once."""
    result = await asyncio.to_thread(_collect_sync, db_path, _status.tickers)
    _set_status(
        last_run_at=datetime.now(timezone.utc).isoformat(),
        last_candle_at=result["last_candle"],
        processed_records=int(result["processed"]),
        errors=result["errors"],
    )
    return result


async def collector_loop(db_path: str | Path) -> None:
    """Run until cancelled; cancellation is the normal shutdown path."""
    if not _status.enabled:
        logger.info("Adaptive collector disabled by TRADER_ADAPTIVE_ENABLED")
        return
    _set_status(running=True)
    try:
        while True:
            await collect_once(db_path)
            await asyncio.sleep(_status.interval_seconds)
    finally:
        _set_status(running=False)
