import pytest
from bot.feed_filter import (
    should_keep, _has_finance_marker, _has_irrelevance,
    FINANCE_STEMS, IRRELEVANT_STEMS, FILTER_TAGS,
)


class TestShouldKeep:
    def test_normal_finance_news_kept(self):
        assert should_keep(
            "Рынок акций вырос на 2%",
            "Индекс МосБиржи обновил максимум", ["finance"]) is True

    def test_war_news_dropped_for_finance(self):
        assert should_keep(
            "Минобороны: сбито 320 БПЛА за ночь",
            "Силы ПВО отразили атаку", ["finance"]) is False

    def test_war_news_with_finance_marker_kept(self):
        assert should_keep(
            "Санкции против банка после атаки БПЛА",
            "ЦБ оценил последствия", ["finance"]) is True

    def test_sport_news_dropped(self):
        assert should_keep(
            "Сборная выиграла матч и завоевала кубок чемпионата",
            "Финал турнира прошёл в Москве", ["finance"]) is False

    def test_sports_gold_kept_by_stage0(self):
        # "золото" is a finance marker, so stage-0 keeps it; the topic
        # filter / AI verification drop it downstream.
        assert should_keep(
            "Сборная завоевала золото на чемпионате мира по футболу",
            "", ["finance"]) is True

    def test_non_finance_tags_untouched(self):
        # Filtering applies only to finance-like categories.
        assert should_keep(
            "Сборная выиграла матч",
            "Чемпионат мира по футболу", ["sport"]) is True

    def test_all_tags_applies_filter(self):
        assert should_keep(
            "Пожар уничтожил склад",
            "Происшествие на складе", None) is False

    def test_no_junk_always_kept(self):
        assert should_keep("Обычная новость", "Никаких маркеров", ["finance"]) is True

    def test_channel_keyword_protects_item(self):
        assert should_keep(
            "После атаки БПЛА приостановлена добыча золота",
            "Прииск не работает", ["finance"], keep_keywords=["золото"]) is True

    def test_short_keywords_ignored(self):
        assert should_keep(
            "Атака БПЛА на склад",
            "", ["finance"], keep_keywords=["а"]) is False

    def test_empty_tags_list_is_all(self):
        assert should_keep(
            "Пожар в торговом центре",
            "Есть пострадавшие", []) is False


class TestStemMatching:
    def test_irrelevant_stems_match_junk(self):
        for text in ["БПЛА атаковали регион", "Обошлось без жертв",
                     "Спортивный матч завершился", "Уголовное дело возбуждено"]:
            assert _has_irrelevance(text), text

    def test_finance_stems_match_markers(self):
        for text in ["курс рубля вырос", "ЦБ повысил ставку", "нефть дорожает",
                     "облигации подешевели", "gold prices rise"]:
            assert _has_finance_marker(text), text

    def test_inflections_covered(self):
        assert _has_irrelevance("Атаковали позиции")
        assert _has_finance_marker("Банковская система стабильна")


class TestFilterTags:
    def test_expected_categories(self):
        assert FILTER_TAGS == {"finance", "macro", "commodities", "global_finance"}

    def test_stem_lists_nonempty(self):
        assert len(IRRELEVANT_STEMS) > 0
        assert len(FINANCE_STEMS) > 0
