"""Tests for bot.macro_monitor — CBR data parsing, linker risk logic, DB state."""
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from bot.database import (
    save_macro_indicator, get_macro_history,
    get_macro_state, set_macro_state,
)
from bot.macro_monitor import (
    parse_usd_rub,
    parse_inflation_page,
    evaluate_linker_risk,
    format_linker_alert,
    build_linker_alert,
)
import bot.macro_monitor as macro_mod


def _snap(offset_days: int, usd_rub: float, inflation_yy: float, key_rate: float = 15.0) -> dict:
    observed_on = (date.today() - timedelta(days=offset_days)).isoformat()
    return {
        "observed_on": observed_on,
        "usd_rub": usd_rub,
        "inflation_yy": inflation_yy,
        "key_rate": key_rate,
    }


# ── Parsing ──

class TestParseUsdRub:
    def test_parses_usd_rate(self):
        xml = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="11.08.2026" name="Foreign Currency Market">
<Valute ID="R01010"><CharCode>AUD</CharCode><Nominal>1</Nominal><Value>58,3942</Value></Valute>
<Valute ID="R01235"><CharCode>USD</CharCode><Nominal>1</Nominal><Value>92,1533</Value></Valute>
</ValCurs>"""
        assert parse_usd_rub(xml.encode("utf-8")) == 92.1533

    def test_invalid_xml(self):
        assert parse_usd_rub(b"not xml at all") is None

    def test_missing_usd(self):
        xml = "<ValCurs><Valute><CharCode>EUR</CharCode><Value>100,0</Value></Valute></ValCurs>"
        assert parse_usd_rub(xml.encode()) is None


class TestParseInflationPage:
    HTML = """<table>
<tr><th>Дата</th><th>Ключевая ставка, % годовых</th><th>Инфляция, % г/г</th><th>Цель по инфляции, %</th></tr>
<tr><td>06.2026</td><td>14,25</td><td>6,02</td><td>4,00</td></tr>
<tr><td>05.2026</td><td>14,50</td><td>5,31</td><td>4,00</td></tr>
</table>"""

    def test_parses_latest_row(self):
        result = parse_inflation_page(self.HTML)
        assert result == {
            "month": "06.2026",
            "key_rate": 14.25,
            "inflation_yy": 6.02,
            "target": 4.0,
        }

    def test_empty_page(self):
        assert parse_inflation_page("<html><body>nothing</body></html>") == {}


# ── Risk logic ──

class TestEvaluateLinkerRisk:
    def test_both_falling(self):
        history = [
            _snap(30, usd_rub=100.0, inflation_yy=10.0),
            _snap(15, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=90.0, inflation_yy=9.3),
        ]
        risk = evaluate_linker_risk(history)
        assert risk["risk"] is True
        assert risk["fx_strengthening"] is True
        assert risk["inflation_falling"] is True
        assert risk["fx_change_pct"] == -10.0
        assert risk["inflation_change_pp"] == -0.7

    def test_only_fx_strengthening(self):
        history = [
            _snap(30, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=90.0, inflation_yy=10.5),
        ]
        risk = evaluate_linker_risk(history)
        assert risk["fx_strengthening"] is True
        assert risk["inflation_falling"] is False
        assert risk["risk"] is False

    def test_only_inflation_falling(self):
        history = [
            _snap(30, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=101.0, inflation_yy=9.0),
        ]
        risk = evaluate_linker_risk(history)
        assert risk["fx_strengthening"] is False
        assert risk["inflation_falling"] is True
        assert risk["risk"] is False

    def test_insufficient_history(self):
        history = [
            _snap(5, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=80.0, inflation_yy=8.0),
        ]
        risk = evaluate_linker_risk(history)
        assert risk["enough_history"] is False
        assert risk["risk"] is False

    def test_single_record(self):
        risk = evaluate_linker_risk([_snap(0, usd_rub=100.0, inflation_yy=10.0)])
        assert risk["risk"] is False

    def test_custom_thresholds(self):
        history = [
            _snap(30, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=98.0, inflation_yy=9.9),
        ]
        risk = evaluate_linker_risk(history, window_days=14, fx_threshold_pct=3.0, inflation_drop_pp=0.3)
        assert risk["risk"] is False
        risk_loose = evaluate_linker_risk(history, window_days=14, fx_threshold_pct=1.0, inflation_drop_pp=0.05)
        assert risk_loose["risk"] is True


# ── Formatting ──

class TestFormatLinkerAlert:
    def test_contains_key_facts(self):
        history = [
            _snap(30, usd_rub=100.0, inflation_yy=10.0),
            _snap(0, usd_rub=90.0, inflation_yy=9.3),
        ]
        risk = evaluate_linker_risk(history)
        msg = format_linker_alert(risk)
        assert "ОФЗ-ИН" in msg
        assert "52002" in msg and "52003" in msg
        assert "90.00" in msg and "100.00" in msg
        assert "9.30" in msg and "10.00" in msg
        assert "Не является индивидуальной инвестиционной рекомендацией" in msg


# ── DB helpers ──

class TestMacroDb:
    async def test_save_and_read_history(self, setup_db):
        await save_macro_indicator("2026-07-01", 100.0, 10.0, 15.0)
        await save_macro_indicator("2026-07-02", 99.0, 9.5, 15.0)
        history = await get_macro_history()
        assert [h["observed_on"] for h in history] == ["2026-07-01", "2026-07-02"]
        assert history[-1]["usd_rub"] == 99.0
        assert history[-1]["inflation_yy"] == 9.5

    async def test_upsert_same_day(self, setup_db):
        await save_macro_indicator("2026-07-01", 100.0, 10.0, 15.0)
        await save_macro_indicator("2026-07-01", 95.0, 9.0, 14.5)
        history = await get_macro_history()
        assert len(history) == 1
        assert history[0]["usd_rub"] == 95.0

    async def test_state_roundtrip(self, setup_db):
        assert await get_macro_state("linker_alert_active") is None
        await set_macro_state("linker_alert_active", "1")
        assert await get_macro_state("linker_alert_active") == "1"
        await set_macro_state("linker_alert_active", "0")
        assert await get_macro_state("linker_alert_active") == "0"


# ── End-to-end alert transition ──

class TestBuildLinkerAlert:
    async def test_alerts_once_then_resets(self, setup_db):
        # Seed history so the trend window is satisfied
        await save_macro_indicator((date.today() - timedelta(days=30)).isoformat(), 100.0, 10.0, 15.0)
        await save_macro_indicator((date.today() - timedelta(days=15)).isoformat(), 100.0, 10.0, 15.0)

        risky = {"usd_rub": 90.0, "inflation_yy": 9.3, "key_rate": 14.5, "month": "07.2026"}
        cleared = {"usd_rub": 100.0, "inflation_yy": 10.0, "key_rate": 15.0, "month": "07.2026"}

        with patch.object(macro_mod, "fetch_macro_snapshot", new=AsyncMock(return_value=risky)):
            msg1 = await build_linker_alert()
            assert msg1 is not None
            assert "ОФЗ-ИН" in msg1

        # Second run while conditions persist -> no repeat alert
        with patch.object(macro_mod, "fetch_macro_snapshot", new=AsyncMock(return_value=risky)):
            msg2 = await build_linker_alert()
            assert msg2 is None

        # Conditions cleared -> no alert, state reset
        with patch.object(macro_mod, "fetch_macro_snapshot", new=AsyncMock(return_value=cleared)):
            msg3 = await build_linker_alert()
            assert msg3 is None
            assert await get_macro_state("linker_alert_active") == "0"

        # Risk returns -> alert fires again
        with patch.object(macro_mod, "fetch_macro_snapshot", new=AsyncMock(return_value=risky)):
            msg4 = await build_linker_alert()
            assert msg4 is not None

    async def test_no_data_returns_none(self, setup_db):
        empty = {"usd_rub": None, "inflation_yy": None, "key_rate": None, "month": ""}
        with patch.object(macro_mod, "fetch_macro_snapshot", new=AsyncMock(return_value=empty)):
            assert await build_linker_alert() is None
