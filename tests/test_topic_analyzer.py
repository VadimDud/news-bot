import json
import pytest
from unittest.mock import AsyncMock, patch

from bot.ai_client import _parse_json
from bot.topic_analyzer import analyze_topic
import bot.topic_analyzer as ta_mod


class TestParseJson:
    def test_valid_json(self):
        text = '{"keywords": ["a", "b"]}'
        result = _parse_json(text)
        assert result["keywords"] == ["a", "b"]

    def test_json_in_code_block(self):
        text = '```json\n{"keywords": ["a"]}\n```'
        result = _parse_json(text)
        assert result is not None
        assert result["keywords"] == ["a"]

    def test_invalid_json(self):
        result = _parse_json("not json at all")
        assert result is None

    def test_empty_string(self):
        result = _parse_json("")
        assert result is None


class TestAnalyzeTopic:
    async def test_deepseek_success(self):
        mock_result = {
            "topic": "Газпром",
            "keywords": ["газпром", "gazp", "газ"],
            "positive_triggers": ["рост", "дивиденды"],
            "negative_triggers": ["санкции"],
            "related_tickers": ["GAZP"],
            "source_tags": ["finance", "commodities"],
            "description": "Газпром"
        }
        with patch("bot.topic_analyzer.analyze", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_topic("Газпром", ["газпром"])
            assert result["topic"] == "Газпром"
            assert len(result["keywords"]) == 3
            assert result["source_tags"] == ["finance", "commodities"]

    async def test_all_fail_returns_none(self):
        with patch("bot.topic_analyzer.analyze", new_callable=AsyncMock, return_value=None):
            result = await analyze_topic("topic", ["kw"])
            assert result is None

    async def test_invalid_source_tags_filtered(self):
        mock_result = {
            "keywords": ["k"],
            "positive_triggers": [],
            "negative_triggers": [],
            "source_tags": ["finance", "invalid_tag", "crypto"],
        }
        with patch("bot.topic_analyzer.analyze", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_topic("t", ["k"])
            assert result["source_tags"] == ["finance", "crypto"]

    async def test_missing_fields_default(self):
        mock_result = {"keywords": ["k"]}
        with patch("bot.topic_analyzer.analyze", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_topic("my_topic", ["k"])
            assert result["positive_triggers"] == []
            assert result["negative_triggers"] == []
            assert result["related_tickers"] == []
            assert result["source_tags"] == []
            assert result["topic"] == "my_topic"
            assert result["description"] == ""

    async def test_non_list_source_tags(self):
        mock_result = {
            "keywords": ["k"],
            "source_tags": "not_a_list",
        }
        with patch("bot.topic_analyzer.analyze", new_callable=AsyncMock, return_value=mock_result):
            result = await analyze_topic("t", ["k"])
            assert result["source_tags"] == []
