import pytest
from unittest.mock import AsyncMock, patch
from bot.news_processor import (
    match_news_to_channels, stage1_filter, compute_sentiment,
    compute_hash, compute_minhash, is_similar,
    format_channel_news, format_news_batch, format_news_alert,
    split_news_text, _normalize, _simple_stem, refine_sentiment,
)
from bot import database as db


class TestNormalizeAndStem:
    def test_normalize_lowercases(self):
        assert _normalize("  HELLO  ") == "hello"

    def test_simple_stem_removes_endings(self):
        assert _simple_stem("ключевого") == "ключев"
        assert _simple_stem("финансовый") == "финансов"


class TestMatchNewsToChannels:
    def test_keyword_match(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "SBER", "keywords": ["сбербанк", "сбер"]},
        ]
        matches = match_news_to_channels("Сбербанк снизил ставку", "", channels)
        assert len(matches) == 1
        assert matches[0]["channel_id"] == 1
        assert matches[0]["matched_keyword"] in ("сбербанк", "сбер")

    def test_no_match(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None, "keywords": ["сбербанк"]},
        ]
        matches = match_news_to_channels("Погода в Москве", "", channels)
        assert len(matches) == 0

    def test_multiple_channels(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None, "keywords": ["газпром"]},
            {"id": 2, "user_id": 200, "language": "ru", "ticker": None, "keywords": ["газпром"]},
        ]
        matches = match_news_to_channels("Газпром увеличил добычу", "", channels)
        assert len(matches) == 2

    def test_one_match_per_channel(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None, "keywords": ["сбербанк", "сбер"]},
        ]
        matches = match_news_to_channels("Сбербанк — это Сбер", "", channels)
        assert len(matches) == 1

    def test_short_keyword_ignored(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None, "keywords": ["a"]},
        ]
        matches = match_news_to_channels("This is a test", "", channels)
        assert len(matches) == 0

    def test_stem_match(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None, "keywords": ["ключевого"]},
        ]
        matches = match_news_to_channels("Ключевого ставка ЦБ", "", channels)
        assert len(matches) == 1

    def test_mid_word_company_name_not_matched(self):
        # "золото" must not match mid-word in "Южуралзолото"
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "topics": [], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Акции ЮГК выросли на 6%",
            "Акции ПАО «Южуралзолото» (ЮГК) на торгах Мосбиржи подскочили на 6%",
            channels)
        assert len(matches) == 0

    def test_inflections_match_same_root(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "topics": [], "keywords": ["золото"]},
        ]
        assert len(match_news_to_channels("Золотые резервы растут", "", channels)) == 1
        assert len(match_news_to_channels("Цена золотом исчисляется", "", channels)) == 1
        assert len(match_news_to_channels("Золотая монета", "", channels)) == 1

    def test_phrase_keyword_matches(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "keywords": ["ключевая ставка"]},
        ]
        matches = match_news_to_channels("Ключевая ставка осталась на уровне 21%", "", channels)
        assert len(matches) == 1
        assert matches[0]["matched_keyword"] == "ключевая ставка"

    def test_first_matching_keyword_reported(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "keywords": ["погода", "сбербанк"]},
        ]
        matches = match_news_to_channels("Сбербанк улучшил сервис", "", channels)
        assert len(matches) == 1
        assert matches[0]["matched_keyword"] == "сбербанк"

    def test_many_channels_one_match(self):
        channels = [
            {"id": i, "user_id": 1000 + i, "language": "ru", "ticker": None,
             "keywords": [f"kw{i}"]}
            for i in range(50)
        ]
        channels.append({"id": 99, "user_id": 1099, "language": "ru", "ticker": None,
                         "keywords": ["сбербанк"]})
        matches = match_news_to_channels("Сбербанк снизил ставку", "", channels)
        assert len(matches) == 1
        assert matches[0]["channel_id"] == 99


class TestRefineSentiment:
    async def test_high_confidence_skips_ai(self):
        impact, used = await refine_sentiment(
            "h1", "title", "summary", None, "POSITIVE", "high", 0)
        assert impact == "POSITIVE"
        assert used == 0

    async def test_cache_hit_returns_cached(self):
        await db.set_ai_cache("sent:h1:none", "NEGATIVE")
        impact, used = await refine_sentiment(
            "h1", "title", "summary", None, "POSITIVE", "low", 0)
        assert impact == "NEGATIVE"
        assert used == 0

    async def test_budget_exhausted_no_ai(self):
        impact, used = await refine_sentiment(
            "h1", "title", "summary", None, "POSITIVE", "low", 999)
        assert impact == "POSITIVE"
        assert used == 0

    async def test_ai_refines_sentiment(self):
        with patch("bot.news_processor.stage2_hybrid",
                   new_callable=AsyncMock, return_value="NEGATIVE"):
            impact, used = await refine_sentiment(
                "h1", "title", "summary", None, "POSITIVE", "low", 0)
        assert impact == "NEGATIVE"
        assert used == 1

    async def test_ai_none_keeps_impact(self):
        with patch("bot.news_processor.stage2_hybrid",
                   new_callable=AsyncMock, return_value=None):
            impact, used = await refine_sentiment(
                "h1", "title", "summary", None, "POSITIVE", "low", 0)
        assert impact == "POSITIVE"
        assert used == 1


class TestTopicFilter:
    """Topic-based filtering: ambiguous keywords (e.g. "золото") must not
    match news that is clearly about another topic (e.g. sport)."""

    def test_sports_gold_rejected_for_finance_channel(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "GOLD",
             "topics": ["finance"], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Сборная России завоевала золото на чемпионате мира по футболу",
            "", channels)
        assert len(matches) == 0

    def test_finance_gold_accepted(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "GOLD",
             "topics": ["finance"], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Цена на золото достигла рекорда",
            "Инвесторы покупают золото, растёт доходность", channels)
        assert len(matches) == 1

    def test_weak_signal_passes(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "GOLD",
             "topics": ["finance"], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels("Золото подорожало", "", channels)
        assert len(matches) == 1

    def test_no_topics_means_no_filtering(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "topics": [], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Сборная России завоевала золото на чемпионате мира по футболу",
            "", channels)
        assert len(matches) == 1

    def test_topics_inferred_from_ticker(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "GOLD",
             "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Сборная России завоевала золото на чемпионате мира по футболу",
            "", channels)
        assert len(matches) == 0

    def test_sanctions_rejected_for_finance_accepted_for_politics(self):
        news = "США ввели новые санкции и эмбарго против российских банков"
        fin = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": "SBER",
             "topics": ["finance"], "keywords": ["банк"]},
        ]
        pol = [
            {"id": 2, "user_id": 200, "language": "ru", "ticker": None,
             "topics": ["politics"], "keywords": ["санкции"]},
        ]
        assert len(match_news_to_channels(news, "", fin)) == 0
        assert len(match_news_to_channels(news, "", pol)) == 1

    def test_sport_channel_accepts_sports_news(self):
        channels = [
            {"id": 1, "user_id": 100, "language": "ru", "ticker": None,
             "topics": ["sport"], "keywords": ["золото"]},
        ]
        matches = match_news_to_channels(
            "Сборная России завоевала золото на чемпионате мира по футболу",
            "", channels)
        assert len(matches) == 1


class TestStage1Filter:
    def test_relevant(self):
        assets = [{"ticker": "SBER", "keywords": ["Сбербанк", "SBER"]}]
        relevant, ticker, _ = stage1_filter("Сбербанк снизил ставку", "Банк", assets)
        assert relevant is True
        assert ticker == "SBER"

    def test_irrelevant(self):
        assets = [{"ticker": "SBER", "keywords": ["Сбербанк"]}]
        relevant, ticker, _ = stage1_filter("Погода в Москве", "", assets)
        assert relevant is False

    def test_macro(self):
        assets = [{"ticker": "MACRO", "keywords": ["ЦБ", "ключевая ставка"]}]
        relevant, ticker, _ = stage1_filter("ЦБ повысил ключевую ставку", "", assets)
        assert relevant is True
        assert ticker == "MACRO"

    def test_no_assets(self):
        relevant, ticker, _ = stage1_filter("title", "summary", [])
        assert relevant is False


class TestComputeHash:
    def test_deterministic(self):
        h1 = compute_hash("Тестовая новость")
        h2 = compute_hash("Тестовая новость")
        assert h1 == h2

    def test_different_texts(self):
        h1 = compute_hash("Новость 1")
        h2 = compute_hash("Новость 2")
        assert h1 != h2

    def test_length(self):
        h = compute_hash("test")
        assert len(h) == 64


class TestIsSimilar:
    def test_same_hash(self):
        h = compute_hash("Тестовая новость")
        assert is_similar(h, h) is True

    def test_different_hashes(self):
        h1 = compute_hash("Тестовая новость 1")
        h2 = compute_hash("Совершенно другая новость о чем-то")
        assert is_similar(h1, h2) is False

    def test_threshold(self):
        h = compute_hash("test text")
        assert is_similar(h, h, threshold=0.99) is True


class TestComputeSentiment:
    def test_positive(self):
        asset = {
            "ticker": "SBER",
            "positive_triggers": ["рост", "дивиденды", "прибыль"],
            "negative_triggers": ["дефолт", "падение"],
        }
        sentiment, confidence = compute_sentiment("Дивиденды выросли", "", asset)
        assert sentiment == "POSITIVE"

    def test_negative(self):
        asset = {
            "ticker": "SBER",
            "positive_triggers": ["рост", "дивиденды"],
            "negative_triggers": ["дефолт", "падение"],
        }
        sentiment, confidence = compute_sentiment("Дефолт компании", "", asset)
        assert sentiment == "NEGATIVE"

    def test_neutral(self):
        asset = {
            "ticker": "SBER",
            "positive_triggers": ["рост"],
            "negative_triggers": ["падение"],
        }
        sentiment, confidence = compute_sentiment("Новость без триггеров", "", asset)
        assert sentiment == "NEUTRAL"

    def test_high_confidence(self):
        asset = {
            "ticker": "X",
            "positive_triggers": ["а", "б", "в"],
            "negative_triggers": [],
        }
        sentiment, confidence = compute_sentiment("а б в", "", asset)
        assert sentiment == "POSITIVE"
        assert confidence == "high"

    def test_no_asset_uses_params(self):
        pos = ["рост"]
        neg = ["падение"]
        sentiment, _ = compute_sentiment("Рост показателей", "", positive_triggers=pos, negative_triggers=neg)
        assert sentiment == "POSITIVE"


class TestFormatChannelNews:
    def test_basic(self):
        items = [{"title": "T", "source": "S", "impact": "POSITIVE", "summary": "Sum", "matched_keyword": "k", "ticker_hint": "SBER"}]
        result = format_channel_news("Ch", items, "ru")
        assert len(result) == 1
        assert "Ch" in result[0]
        assert "T" in result[0]
        assert "🟢" in result[0]

    def test_empty(self):
        assert format_channel_news("Ch", [], "ru") == []

    def test_negative_emoji(self):
        items = [{"title": "T", "source": "S", "impact": "NEGATIVE", "summary": "S"}]
        result = format_channel_news("Ch", items, "ru")
        assert "🔴" in result[0]

    def test_en_language(self):
        items = [{"title": "T", "source": "S", "impact": "POSITIVE", "summary": "S"}]
        result = format_channel_news("Ch", items, "en")
        assert "Read more" in result[0] or "Подробнее" not in result[0]


class TestFormatNewsBatch:
    def test_basic(self):
        items = [{"title": "T", "source": "S", "ticker": "SBER", "impact": "POSITIVE", "summary": "S", "link": "http://x"}]
        result = format_news_batch(items, "ru")
        assert len(result) >= 1
        assert "SBER" in result[0]

    def test_empty(self):
        assert format_news_batch([], "ru") == []


class TestFormatNewsAlert:
    def test_basic(self):
        analysis = {"ticker": "SBER", "summary": "Суть", "impact": "POSITIVE"}
        alert = format_news_alert("Title", "РБК", analysis, "https://example.com")
        assert "SBER" in alert
        assert "🟢" in alert
        assert "Подробнее" in alert


class TestSplitNewsText:
    def test_empty(self):
        assert split_news_text("") == []

    def test_short_text(self):
        result = split_news_text("Short text")
        assert len(result) == 1

    def test_long_text_splits(self):
        text = "\n".join([f"{i}. Item {i} " + "x" * 100 for i in range(50)])
        result = split_news_text(text, max_len=4000)
        assert len(result) >= 2

    def test_html_tags_stay_balanced(self):
        text = (
            "📰 <b>Новости</b> (2 шт.)\n\n"
            "<b>1. Газпром: итоги 2024. Рост выручки на 30%</b>\n"
            "📡 Коммерсантъ\n"
            "🟡 NEUTRAL\n\n"
            "<b>2. Сбер и ВТБ подвели итоги полугодия</b>\n"
            "📡 Интерфакс\n"
            "🟢 POSITIVE"
        )
        chunks = split_news_text(text, max_len=100)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.count("<b>") == chunk.count("</b>")
        title_chunk = next(c for c in chunks if "Газпром" in c)
        assert "Рост выручки на 30%</b>" in title_chunk



class TestGlobalScanRelevanceVerification:
    """AI verification must drop ambiguous matches the LLM deems irrelevant."""

    async def _setup_channel(self):
        await db.set_user(100, "test", "Test User", "ru")
        await db.grant_access(100, 30)
        await db.create_channel(100, "Золото", ["золото"], ticker="ЗОЛОТО")
        return await db.get_all_user_channels()

    async def test_irrelevant_gold_dropped(self):
        from bot import news_processor as np
        channels = await self._setup_channel()
        news = [{
            "title": "Экс-владельцы «Золотого глобуса» заявили о рейдерском захвате премии",
            "summary": "Премия «Золотой глобус» оказалась в центре скандала",
            "source": "Коммерсантъ",
            "link": "http://example.com",
        }]
        with patch.object(np, "analyze", new=AsyncMock(return_value="нет")):
            results, buffer_updates = await np.global_scan(news, channels)
        assert all(len(v) == 0 for v in results.values())
        assert buffer_updates == []

    async def test_relevant_gold_kept(self):
        from bot import news_processor as np
        channels = await self._setup_channel()
        news = [{
            "title": "Золото опустилось ниже $4 тыс. за унцию",
            "summary": "Стоимость августовского фьючерса на золото составила $3,993 тыс.",
            "source": "Коммерсантъ",
            "link": "http://example.com",
        }]
        with patch.object(np, "analyze", new=AsyncMock(return_value="да")):
            results, buffer_updates = await np.global_scan(news, channels)
        assert any(len(v) > 0 for v in results.values())

    async def test_unavailable_ai_keeps_match(self):
        from bot import news_processor as np
        channels = await self._setup_channel()
        news = [{
            "title": "Золото опустилось ниже $4 тыс. за унцию",
            "summary": "Стоимость фьючерса на золото снизилась",
            "source": "Коммерсантъ",
            "link": "http://example.com",
        }]
        with patch.object(np, "analyze", new=AsyncMock(return_value=None)):
            results, _ = await np.global_scan(news, channels)
        assert any(len(v) > 0 for v in results.values())


class TestAICacheInGlobalScan:
    """AI results must be cached by content_hash so repeat scans avoid LLM calls."""

    async def _make_channel(self):
        await db.set_user(100, "test", "Test User", "ru")
        await db.grant_access(100, 30)
        await db.create_channel(100, "Золото", ["золото"], ticker="ЗОЛОТО")
        return await db.get_all_user_channels()

    async def test_second_scan_uses_cache(self):
        from bot import news_processor as np
        channels = await self._make_channel()
        news = [{
            "title": "Золото опустилось ниже $4 тыс. за унцию",
            "summary": "Стоимость фьючерса на золото снизилась",
            "source": "Коммерсантъ",
            "link": "http://example.com",
        }]

        async def fake_analyze(system_prompt, user_message, **kwargs):
            if "финансовый аналитик" in system_prompt:
                return "NEUTRAL"
            return "да"

        with patch.object(np, "analyze", new=AsyncMock(side_effect=fake_analyze)) as mock_analyze:
            results, _ = await np.global_scan(news, channels)
            first_calls = mock_analyze.await_count
        assert first_calls >= 1
        assert any(len(v) > 0 for v in results.values())

        with patch.object(np, "analyze", new=AsyncMock(side_effect=fake_analyze)) as mock_analyze:
            results, _ = await np.global_scan(news, channels)
            second_calls = mock_analyze.await_count
        assert second_calls == 0
        assert any(len(v) > 0 for v in results.values())


class TestGlobalScanWindow:
    """global_scan must examine the freshest items first and stop early."""

    async def _make_channel(self, keyword="сбербанк"):
        await db.set_user(100, "test", "Test User", "ru")
        await db.grant_access(100, 30)
        await db.create_channel(100, "SBER", [keyword], ticker="SBER")
        return await db.get_all_user_channels()

    async def test_freshest_item_beyond_old_20_limit_is_processed(self):
        from bot import news_processor as np
        channels = await self._make_channel()
        news = [
            {
                "title": f"Обычная новость номер {i}",
                "summary": "Без совпадений",
                "source": "Тест",
                "link": f"http://x/{i}",
                "published_at": f"2026-08-04T00:{i:02d}:00",
            }
            for i in range(30)
        ]
        news.append({
            "title": "Сбербанк объявил о новых тарифах",
            "summary": "Банк обновил условия",
            "source": "Тест",
            "link": "http://x/sber",
            "published_at": "2026-08-04T12:00:00",
        })
        with patch.object(np, "analyze", new=AsyncMock(return_value="NEUTRAL")):
            results, _ = await np.global_scan(news, channels)
        titles = [r["title"] for v in results.values() for r in v]
        assert any("Сбербанк" in t for t in titles)

    async def test_early_stop_after_max_matched(self):
        from bot import news_processor as np
        channels = await self._make_channel()
        news = [
            {
                "title": f"Сбербанк новость {i}",
                "summary": "Банк",
                "source": "Тест",
                "link": f"http://x/{i}",
                "published_at": f"2026-08-04T12:{i:02d}:00",
            }
            for i in range(30)
        ]
        calls = {"n": 0}
        orig = np.match_news_to_channels

        def spy(title, summary, chs):
            calls["n"] += 1
            return orig(title, summary, chs)

        with patch.object(np, "match_news_to_channels", new=spy), \
             patch.object(np, "analyze", new=AsyncMock(return_value="NEUTRAL")):
            results, _ = await np.global_scan(news, channels)
        assert calls["n"] == np.MAX_SCAN_MATCHED
        total = sum(len(v) for v in results.values())
        assert 1 <= total <= np.MAX_SCAN_MATCHED

    async def test_oldest_news_still_processed_within_window(self):
        from bot import news_processor as np
        channels = await self._make_channel()
        news = [
            {
                "title": "Сбербанк отчитался о прибыли",
                "summary": "Банк опубликовал результаты",
                "source": "Тест",
                "link": "http://x/old",
                "published_at": "2026-08-04T00:00:00",
            },
            {
                "title": "Обычная новость 1",
                "summary": "Без совпадений",
                "source": "Тест",
                "link": "http://x/1",
                "published_at": "2026-08-04T01:00:00",
            },
            {
                "title": "Обычная новость 2",
                "summary": "Без совпадений",
                "source": "Тест",
                "link": "http://x/2",
                "published_at": "2026-08-04T02:00:00",
            },
        ]
        with patch.object(np, "analyze", new=AsyncMock(return_value="NEUTRAL")):
            results, _ = await np.global_scan(news, channels)
        titles = [r["title"] for v in results.values() for r in v]
        assert any("Сбербанк отчитался" in t for t in titles)
