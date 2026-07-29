import pytest
from unittest.mock import AsyncMock, patch

from bot.asset_analyzer import _parse_json_response, analyze_ticker
import bot.asset_analyzer as aa_mod


class TestParseJsonResponse:
    def test_valid_json(self):
        text = '{"ticker": "SBER", "keywords": ["а"]}'
        result = _parse_json_response(text)
        assert result["ticker"] == "SBER"

    def test_json_in_code_block(self):
        text = '```json\n{"ticker": "SBER"}\n```'
        result = _parse_json_response(text)
        assert result is not None

    def test_invalid_json(self):
        result = _parse_json_response("not json")
        assert result is None

    def test_empty(self):
        result = _parse_json_response("")
        assert result is None


class TestAnalyzeTicker:
    async def test_deepseek_success(self):
        mock_result = {
            "ticker": "SBER",
            "company_name": "Сбербанк",
            "keywords": ["сбербанк", "SBER", "сбер"],
            "positive_triggers": ["рост", "дивиденды"],
            "negative_triggers": ["санкции"],
            "description": "Банк"
        }
        with patch.object(aa_mod, "_call_deepseek", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_ticker("SBER")
            assert result["ticker"] == "SBER"
            assert result["company_name"] == "Сбербанк"

    async def test_fallback_when_all_fail(self):
        with patch.object(aa_mod, "_call_deepseek", new_callable=AsyncMock, return_value=None):
            with patch.object(aa_mod, "_call_gemini", new_callable=AsyncMock, return_value=None):
                with patch.object(aa_mod, "_call_dashscope", new_callable=AsyncMock, return_value=None):
                    result = await analyze_ticker("TEST")
                    assert result is not None
                    assert result["ticker"] == "TEST"
                    assert "TEST" in result["keywords"]
                    assert len(result["positive_triggers"]) == 5
                    assert len(result["negative_triggers"]) == 5

    async def test_missing_fields_default(self):
        mock_result = {"ticker": "SBER"}
        with patch.object(aa_mod, "_call_deepseek", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_ticker("SBER")
            assert result["positive_triggers"] == ["дивиденды", "рост"]
            assert result["negative_triggers"] == ["падение", "убыток"]
            assert result["description"] == ""

    async def test_ticker_uppercased(self):
        mock_result = {"ticker": "sber", "keywords": ["k"], "positive_triggers": ["p"], "negative_triggers": ["n"]}
        with patch.object(aa_mod, "_call_deepseek", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_ticker("sber")
            assert result["ticker"] == "SBER"

    async def test_deepseek_fails_gemini_fallback(self):
        mock_result = {
            "ticker": "GAZP",
            "company_name": "Газпром",
            "keywords": ["газпром"],
            "positive_triggers": ["p"],
            "negative_triggers": ["n"],
        }
        with patch.object(aa_mod, "_call_deepseek", new_callable=AsyncMock, return_value=None):
            with patch.object(aa_mod, "_call_gemini", new_callable=AsyncMock, return_value=mock_result):
                result = await analyze_ticker("GAZP")
                assert result["ticker"] == "GAZP"
