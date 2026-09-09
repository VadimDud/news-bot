"""Tests for main.py startup report and watchdog helpers (no runtime side effects)."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402  (module imports are side-effect-free; __main__ guard)


async def test_dead_tasks_detects_crash_and_ignores_none():
    async def crash():
        raise RuntimeError("boom")

    async def ok():
        return 42

    good = asyncio.create_task(ok())
    bad = asyncio.create_task(crash())
    tasks = {"good": good, "bad": bad, "none": None}

    await asyncio.gather(good, bad, return_exceptions=True)

    dead = main._dead_tasks(tasks)
    assert dead == ["bad"]


async def test_dead_tasks_empty_when_all_running():
    async def ok():
        return 42

    t = asyncio.create_task(ok())
    tasks = {"ok": t, "none": None}
    # НЕ ждём завершения — задача ещё выполняется → не краш
    assert main._dead_tasks(tasks) == []
    await t


def test_report_startup_state_logs_without_secrets(caplog):
    class FakeLive:
        strategy = "donchian"

    with caplog.at_level("INFO"), patch.object(main, "config") as mc:
        mc.TELEGRAM_BOT_TOKEN = "SECRET_REAL_TOKEN"
        mc.TELEGRAM_CHAT_ID = "12345"
        mc.TRADER_TG_PROXY = ""
        mc.TRADER_SIGNALS_ENABLED = True
        mc.TRADER_SIGNALS_RUN_ON_STARTUP = True
        mc.TRADER_ELLIOTT_ENABLED = False
        mc.TRADER_ELLIOTT_RUN_ON_STARTUP = False
        mc.TRADER_FIB_ENABLED = True
        mc.TRADER_FIB_RUN_ON_STARTUP = True
        mc.TRADER_MTF_ENABLED = True
        mc.TRADER_MTF_RUN_ON_STARTUP = False
        mc.DRY_RUN = True
        mc.TINKOFF_API_TOKEN = ""
        mc.TRADER_SKILLS_ENABLED = True
        mc.TRADER_SKILLS_MODE = "shadow"
        mc.WATCH_TICKERS = ["SBER", "LKOH"]

        main.report_startup_state(FakeLive())

    text = caplog.text
    # секрет не должен попасть в лог
    assert "SECRET_REAL_TOKEN" not in text
    assert "токен задан" in text


async def test_notify_dead_sends_alert_once_and_dedups():
    async def crash():
        raise RuntimeError("kaboom")

    task = asyncio.ensure_future(crash())
    await asyncio.gather(task, return_exceptions=True)

    tasks = {"ROE": task}
    with patch("app.signal_notifier.send_telegram_message", new_callable=AsyncMock) as msend:
        logged = set()
        await main._notify_dead(tasks, logged)
        msend.assert_awaited_once()
        assert logged == {"ROE"}

        # повторный проход с тем же logged — алерта больше нет
        await main._notify_dead(tasks, logged)
        msend.assert_awaited_once()
