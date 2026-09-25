from __future__ import annotations

import asyncio

from app import adaptive_collector


def test_configured_tickers_defaults_to_t(monkeypatch) -> None:
    monkeypatch.delenv("TRADER_ADAPTIVE_TICKERS", raising=False)

    assert adaptive_collector.configured_tickers() == ("T",)


def test_configured_interval_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("TRADER_ADAPTIVE_INTERVAL", "1")

    assert adaptive_collector.configured_interval() == 15


def test_collect_once_updates_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(adaptive_collector._status, "tickers", ("T",))
    monkeypatch.setattr(adaptive_collector.storage, "get_candles", lambda ticker, period: None)

    result = asyncio.run(adaptive_collector.collect_once(tmp_path / "collector.db"))
    current = adaptive_collector.status()

    assert result["processed"] == 0
    assert current["last_run_at"] is not None
    assert current["errors"] == {"T": "no 15min candles"}
    assert current["mode"] == "statistics_only"
