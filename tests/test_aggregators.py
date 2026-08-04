import time

import pytest
from unittest.mock import AsyncMock, patch

import bot.aggregators as agg_mod
from bot import aggregators as agg


@pytest.fixture
def apitube_article():
    """Minimal APITube /v1/news/everything article with enrichment fields."""
    return {
        "id": 1,
        "title": "ЦБ сохранил ключевую ставку на уровне 21%",
        "description": "Решение было ожидаемым для рынка...[Upgrade subscription plan]",
        "href": "https://example.com/rates",
        "published_at": "2026-08-04T09:15:00.000Z",
        "language": "ru",
        "source": {"domain": "example.com", "rankings": {"opr": 8}},
        "categories": [
            {"name": "Economy", "taxonomy": "iptc_mediatopics",
             "links": {"self": "https://api.apitube.io/v1/news/category/iptc_mediatopics/medtop:04000000"}}
        ],
        "sentiment": {"overall": {"polarity": "positive", "score": 0.8}},
        "is_breaking": False,
        "shares": {"total": 120},
    }


def _article(categories_self, **overrides):
    art = {
        "id": 2,
        "title": "Some headline",
        "description": "Some description",
        "href": "https://example.com/x",
        "published_at": "2026-08-04T10:00:00.000Z",
        "language": "ru",
        "source": {"domain": "example.com", "rankings": {"opr": 7}},
        "categories": [
            {"name": "C", "taxonomy": "iptc_mediatopics",
             "links": {"self": categories_self}}
        ],
        "sentiment": {"overall": {"polarity": "neutral", "score": 0.1}},
        "is_breaking": False,
        "shares": {"total": 5},
    }
    art.update(overrides)
    return art


class TestEnabled:
    def test_disabled_without_key(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        assert agg._enabled() is False

    def test_disabled_by_switch(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", False)
        assert agg._enabled() is False

    def test_enabled_with_key(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        assert agg._enabled() is True


class TestNormalize:
    def test_maps_schema(self, apitube_article):
        item = agg._normalize_article(apitube_article, "finance")
        assert item["title"] == apitube_article["title"]
        assert item["link"] == "https://example.com/rates"
        assert item["source"] == "example.com"
        assert item["source_tag"] == "finance"
        assert item["published_at"] == "2026-08-04T09:15:00.000Z"
        assert item["published"] == item["published_at"]

    def test_strips_preview_marker(self, apitube_article):
        item = agg._normalize_article(apitube_article, "finance")
        assert "[Upgrade subscription plan]" not in item["summary"]
        assert "Решение было ожидаемым" in item["summary"]

    def test_enrichment_fields(self, apitube_article):
        item = agg._normalize_article(apitube_article, "finance")
        assert item["opr"] == 8
        assert item["agg_sentiment"] == "positive"
        assert item["agg_sentiment_score"] == 0.8
        assert item["shares"] == 120
        assert "is_breaking" not in item

    def test_breaking_flag(self, apitube_article):
        apitube_article["is_breaking"] = True
        item = agg._normalize_article(apitube_article, "finance")
        assert item["is_breaking"] is True


class TestFetchAggregated:
    @pytest.fixture(autouse=True)
    def _clean_agg_cache(self):
        agg._AGG_CACHE.clear()
        yield
        agg._AGG_CACHE.clear()

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "")
        assert await agg.fetch_aggregated(["finance"]) == []

    @pytest.mark.asyncio
    async def test_keyword_tagging(self, monkeypatch, apitube_article):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[apitube_article])) as mock_req:
            news = await agg.fetch_aggregated(["crypto"])
        assert news
        assert all(i["source_tag"] == "crypto" for i in news)
        params = mock_req.call_args.args[0]
        assert "language.code" not in params
        assert "title" in params

    @pytest.mark.asyncio
    async def test_category_batch_single_request(self, monkeypatch, apitube_article):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[apitube_article])) as mock_req:
            await agg.fetch_aggregated(["finance", "macro"])
        assert mock_req.await_count == 1
        params = mock_req.call_args.args[0]
        assert "category.id" in params
        assert "language.code" in params

    @pytest.mark.asyncio
    async def test_macro_tag_inference(self, monkeypatch, apitube_article):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[apitube_article])):
            news = await agg.fetch_aggregated(["finance", "macro"])
        assert news[0]["source_tag"] == "macro"

    @pytest.mark.asyncio
    async def test_politics_tag_inference(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        article = _article("https://api.apitube.io/v1/news/category/iptc_mediatopics/medtop:11000000")
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[article])):
            news = await agg.fetch_aggregated(["politics"])
        assert news[0]["source_tag"] == "politics"

    @pytest.mark.asyncio
    async def test_en_business_tags_global_finance(self, monkeypatch):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        article = _article(
            "https://api.apitube.io/v1/news/category/iptc_mediatopics/medtop:04000000",
            language="en")
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[article])):
            news = await agg.fetch_aggregated(["global_finance"])
        assert news[0]["source_tag"] == "global_finance"

    @pytest.mark.asyncio
    async def test_all_tags_five_requests(self, monkeypatch, apitube_article):
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[apitube_article])) as mock_req:
            await agg.fetch_aggregated()
        # 2 category batches (ru + en) + 3 keyword queries
        assert mock_req.await_count == 5

    @pytest.mark.asyncio
    async def test_cache_reused(self, monkeypatch, apitube_article):
        agg._AGG_CACHE.clear()
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(return_value=[apitube_article])) as mock_req:
            await agg.fetch_aggregated(["finance"])
            await agg.fetch_aggregated(["finance"])
        assert mock_req.await_count == 1
        agg._AGG_CACHE.clear()

    @pytest.mark.asyncio
    async def test_request_failure_returns_empty(self, monkeypatch):
        agg._AGG_CACHE.clear()
        monkeypatch.setattr(agg.config, "APITUBE_API_KEY", "key")
        monkeypatch.setattr(agg.config, "NEWS_AGG_ENABLED", True)
        with patch.object(agg_mod, "_apitube_request",
                          new=AsyncMock(side_effect=agg.RateLimitError("429"))):
            news = await agg.fetch_aggregated(["finance"])
        assert news == []
        agg._AGG_CACHE.clear()


class TestFinanceIntegration:
    @pytest.fixture
    def mock_feeds(self):
        return """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>RSS News</title><summary>summary</summary><link>https://example.com/rss</link></item>
</channel></rss>"""

    @pytest.mark.asyncio
    async def test_fetch_news_merges_rss_and_aggregated(self, mock_feeds):
        from bot import finance as fm
        fm._fetch_cache.clear()
        fm._http_cache.clear()

        agg_item = {
            "title": "API НОВОСТЬ", "summary": "", "link": "https://example.com/api",
            "source": "apitube", "source_tag": "finance", "published": "",
            "published_at": "",
        }
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance
            with patch("bot.finance.fetch_aggregated",
                       new=AsyncMock(return_value=[agg_item])):
                news = await fm.fetch_news(source_tags=["finance"])

        assert any(n["title"] == "RSS News" for n in news)
        assert any(n["title"] == "API НОВОСТЬ" for n in news)

    @pytest.mark.asyncio
    async def test_fetch_news_dedups_across_sources(self, mock_feeds):
        from bot import finance as fm
        fm._fetch_cache.clear()
        fm._http_cache.clear()

        dup_item = {
            "title": "RSS News", "summary": "api copy", "link": "https://example.com/api",
            "source": "apitube", "source_tag": "finance", "published": "",
            "published_at": "",
        }
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance
            with patch("bot.finance.fetch_aggregated",
                       new=AsyncMock(return_value=[dup_item])):
                news = await fm.fetch_news(source_tags=["finance"])

        assert sum(1 for n in news if n["title"] == "RSS News") == 1


class TestPhase3Enrichment:
    @pytest.mark.asyncio
    async def test_refine_sentiment_uses_agg(self, monkeypatch):
        from bot import news_processor as np
        monkeypatch.setattr(np.config, "NEWS_AGG_USE_SENTIMENT", True)
        monkeypatch.setattr(np.config, "NEWS_AGG_SENTIMENT_THRESHOLD", 0.5)
        with patch.object(np, "stage2_hybrid", new=AsyncMock()) as mock_ai:
            impact, used = await np.refine_sentiment(
                "h1", "title", "summary", None, "NEUTRAL", "low", 0,
                agg_sentiment="positive", agg_sentiment_score=0.8)
        assert impact == "POSITIVE"
        assert used == 0
        mock_ai.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refine_sentiment_ignores_weak_agg(self, monkeypatch):
        from bot import news_processor as np
        monkeypatch.setattr(np.config, "NEWS_AGG_USE_SENTIMENT", True)
        monkeypatch.setattr(np.config, "NEWS_AGG_SENTIMENT_THRESHOLD", 0.5)
        with patch.object(np, "stage2_hybrid",
                          new=AsyncMock(return_value="POSITIVE")) as mock_ai:
            impact, used = await np.refine_sentiment(
                "h1", "title", "summary", None, "NEUTRAL", "low", 0,
                agg_sentiment="negative", agg_sentiment_score=0.2)
        assert impact == "POSITIVE"
        assert used == 1
        mock_ai.assert_awaited()

    def test_compute_importance_opr_raises_authority(self, monkeypatch):
        from bot import news_processor as np
        monkeypatch.setattr(np.config, "NEWS_AGG_USE_OPR", True)
        with_opr = np.compute_importance_score("t", "s", "POSITIVE", "high", opr=10)
        no_opr = np.compute_importance_score("t", "s", "POSITIVE", "high", opr=None)
        assert with_opr > no_opr

    def test_compute_importance_breaking_bonus(self):
        from bot import news_processor as np
        base = np.compute_importance_score("t", "s", "POSITIVE", "high")
        with_breaking = np.compute_importance_score("t", "s", "POSITIVE", "high",
                                                    is_breaking=True)
        assert with_breaking > base

    def test_polarity_from_provider(self):
        from bot import news_processor as np
        assert np._polarity_from_provider("positive") == "POSITIVE"
        assert np._polarity_from_provider("NEGATIVE") == "NEGATIVE"
        assert np._polarity_from_provider("neutral") == "NEUTRAL"
        assert np._polarity_from_provider("nonsense") is None
