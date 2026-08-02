import pytest
from unittest.mock import AsyncMock, patch
from bot.news_processor import (
    match_news_to_channels, stage1_filter, compute_sentiment,
    compute_hash, compute_minhash, is_similar,
    format_channel_news, format_news_batch, format_news_alert,
    split_news_text, _normalize, _simple_stem,
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
