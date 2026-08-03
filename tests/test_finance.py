import time

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from bot.finance import (
    _clean_html, _fallback_analysis,
    format_finance_alert, fetch_news,
)
import bot.finance as finance_mod


@pytest.fixture
def mock_feeds():
    """Minimal RSS feed for testing."""
    return """<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item>
    <title>Test News Title</title>
    <summary>Test summary text</summary>
    <link>https://example.com/news/1</link>
</item>
<item>
    <title>Another News</title>
    <summary>Another summary</summary>
    <link>https://example.com/news/2</link>
</item>
</channel>
</rss>"""


class TestCleanHtml:
    def test_removes_tags(self):
        assert _clean_html("<b>hello</b>") == "hello"

    def test_nested_tags(self):
        assert _clean_html("<p><b>text</b></p>") == "text"

    def test_no_tags(self):
        assert _clean_html("plain text") == "plain text"

    def test_empty(self):
        assert _clean_html("") == ""


class TestFallbackAnalysis:
    def test_defolt(self):
        result = _fallback_analysis("Технический дефолт компании", [])
        assert "Негативно" in result

    def test_reyting_upgrade(self):
        result = _fallback_analysis("Повышение рейтинга SBER", [])
        assert "Позитивно" in result

    def test_downgrade(self):
        result = _fallback_analysis("Даунгрейд GAZP", [])
        assert "Негативно" in result

    def test_dividends(self):
        result = _fallback_analysis("Дивиденды Газпрома", [])
        assert "Позитивно" in result

    def test_stavka(self):
        result = _fallback_analysis("Ключевая ставка ЦБ", [])
        assert "Нейтрально" in result

    def test_unknown(self):
        result = _fallback_analysis("Обычная новость", [])
        assert "Нейтрально" in result


class TestFormatFinanceAlert:
    def test_basic(self):
        alert = format_finance_alert("Title", "Summary", "РБК", "🟢 Позитивно", "https://x")
        assert "Title" in alert
        assert "Summary" in alert
        assert "РБК" in alert
        assert "🟢" in alert
        assert "Подробнее" in alert


class TestFetchNews:
    async def test_fetch_all_sources(self, mock_feeds):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            finance_mod._fetch_cache.clear()
            news = await fetch_news(source_tags=None)
            assert len(news) == 2
            assert news[0]["title"] == "Test News Title"
            assert news[0]["source_tag"] == "finance"

    async def test_fetch_specific_tags(self, mock_feeds):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            finance_mod._fetch_cache.clear()
            news = await fetch_news(source_tags=["finance"])
            assert len(news) == 2

    async def test_cache_hit(self, mock_feeds):
        finance_mod._fetch_cache.clear()
        import time
        finance_mod._fetch_cache[frozenset()] = (time.time(), [{"title": "cached", "source_tag": ""}])
        news = await fetch_news(source_tags=None)
        assert news[0]["title"] == "cached"

    async def test_empty_response(self):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<rss><channel></channel></rss>"

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            finance_mod._fetch_cache.clear()
            news = await fetch_news(source_tags=[])
            assert news == []

    async def test_dedup(self, mock_feeds):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            finance_mod._fetch_cache.clear()
            news1 = await fetch_news(source_tags=[])
            finance_mod._fetch_cache.clear()
            news2 = await fetch_news(source_tags=[])
            assert len(news1) == len(news2)


class TestFetchFinanceNews:
    async def test_wraps_fetch_news(self, mock_feeds):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            finance_mod._fetch_cache.clear()
            finance_mod._http_cache.clear()
            news = await finance_mod.fetch_finance_news()
            assert len(news) == 2
            assert all(i["source_tag"] == "finance" for i in news)


class TestHttpConditionalCache:
    def _feed(self, url):
        return {"name": "Test", "url": url, "type": "rss"}

    async def test_200_stores_etag_and_last_modified(self, mock_feeds):
        finance_mod._http_cache.clear()
        url = "https://test.example/feed.xml"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_feeds
        mock_response.headers = {
            "ETag": '"abc123"',
            "Last-Modified": "Wed, 21 Oct 2026 07:28:00 GMT",
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            entries = await finance_mod._fetch_one(instance, self._feed(url))
            assert len(entries) == 2
            etag, last_modified, cached, _ts = finance_mod._http_cache[url]
            assert etag == '"abc123"'
            assert last_modified == "Wed, 21 Oct 2026 07:28:00 GMT"
            assert cached == entries

    async def test_304_returns_cached_entries(self):
        finance_mod._http_cache.clear()
        url = "https://test.example/feed.xml"
        cached_entries = [{"title": "cached", "summary": "", "link": "",
                           "source": "X", "source_tag": "", "published": "",
                           "published_at": ""}]
        finance_mod._http_cache[url] = ("etag-1", None, cached_entries, time.time())

        mock_response = AsyncMock()
        mock_response.status_code = 304

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            entries = await finance_mod._fetch_one(instance, self._feed(url))
            assert entries == cached_entries
            headers = instance.get.call_args.kwargs.get("headers", {})
            assert headers.get("If-None-Match") == "etag-1"

    async def test_exception_falls_back_to_cached(self):
        finance_mod._http_cache.clear()
        url = "https://test.example/feed.xml"
        cached_entries = [{"title": "cached", "summary": "", "link": "",
                           "source": "X", "source_tag": "", "published": "",
                           "published_at": ""}]
        finance_mod._http_cache[url] = (None, None, cached_entries, time.time())

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            entries = await finance_mod._fetch_one(instance, self._feed(url))
            assert entries == cached_entries

    async def test_fetch_failure_without_cache_returns_empty(self):
        finance_mod._http_cache.clear()
        url = "https://test.example/feed.xml"

        with patch("httpx.AsyncClient") as mock_client:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = instance

            entries = await finance_mod._fetch_one(instance, self._feed(url))
            assert entries == []
