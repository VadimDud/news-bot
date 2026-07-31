import pytest

from bot.topics import (
    MIN_TOPIC_SIGNAL,
    count_topics,
    dominant_topics,
    effective_topics,
    get_topics_display,
    infer_channel_topics,
    topic_filter_pass,
)


class TestCountTopics:
    def test_sport_detected(self):
        counts = count_topics(
            "Сборная России завоевала золото на чемпионате мира по футболу"
        )
        assert counts.get("sport", 0) >= MIN_TOPIC_SIGNAL

    def test_sanctions_expands_to_politics(self):
        counts = count_topics("США ввели новые санкции и эмбарго против России")
        assert counts.get("sanctions", 0) >= MIN_TOPIC_SIGNAL
        assert counts["politics"] >= counts["sanctions"]

    def test_macro_expands_to_finance(self):
        counts = count_topics("Инфляция в стране растёт, ЦБ повышает ставку")
        assert counts.get("macro", 0) >= 1
        assert counts.get("finance", 0) >= counts["macro"]

    def test_gold_alone_has_no_topic(self):
        assert count_topics("Золото подорожало") == {}

    def test_short_word_not_inside_longer_word(self):
        # "газ" must not match "газета"
        counts = count_topics("В газете пишут о важных делах")
        assert "commodities" not in counts

    def test_english_sport_detected(self):
        counts = count_topics("Team won gold at the olympic championship")
        assert counts.get("sport", 0) >= MIN_TOPIC_SIGNAL


class TestDominantTopics:
    def test_weak_signal(self):
        assert dominant_topics({"finance": 1}) == set()

    def test_empty(self):
        assert dominant_topics({}) == set()

    def test_strong_signal(self):
        assert dominant_topics({"sport": 3}) == {"sport"}

    def test_tie(self):
        assert dominant_topics({"sport": 2, "politics": 2}) == {"sport", "politics"}


class TestTopicFilterPass:
    def test_no_channel_topics(self):
        assert topic_filter_pass({"sport": 3}, []) is True
        assert topic_filter_pass({"sport": 3}, None) is True

    def test_pass_on_matching_topic(self):
        assert topic_filter_pass({"sport": 3}, ["sport"]) is True

    def test_reject_off_topic(self):
        assert topic_filter_pass({"sport": 3}, ["finance"]) is False

    def test_weak_signal_never_rejected(self):
        assert topic_filter_pass({"finance": 1}, ["sport"]) is True


class TestInference:
    def test_from_ticker(self):
        assert infer_channel_topics({"ticker": "GOLD"}) == ["finance"]

    def test_from_source_tags(self):
        topics = infer_channel_topics({"source_tags": ["finance", "macro"]})
        assert "finance" in topics
        assert "macro" in topics

    def test_politics_tag(self):
        assert infer_channel_topics({"source_tags": ["politics"]}) == ["politics"]

    def test_global_finance_maps_to_finance(self):
        assert infer_channel_topics({"source_tags": ["global_finance"]}) == ["finance"]

    def test_nothing(self):
        assert infer_channel_topics({}) == []

    def test_explicit_topics_override_inference(self):
        ch = {"ticker": "GOLD", "topics": ["sport"]}
        assert effective_topics(ch) == ["sport"]

    def test_empty_explicit_falls_back_to_inference(self):
        ch = {"ticker": "GOLD", "topics": []}
        assert effective_topics(ch) == ["finance"]


class TestDisplay:
    def test_has_expected_topics(self):
        ids = {t["id"] for t in get_topics_display("ru")}
        assert {"finance", "politics", "sanctions", "sport"} <= ids

    def test_localized_names(self):
        ru = {t["id"]: t["name"] for t in get_topics_display("ru")}
        en = {t["id"]: t["name"] for t in get_topics_display("en")}
        assert ru["finance"] != en["finance"]
