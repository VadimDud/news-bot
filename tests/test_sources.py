import pytest
from bot.sources import get_all_sources, get_sources_by_tags, get_source_tags_display, SOURCES


class TestGetAllSources:
    def test_returns_nonempty_list(self):
        sources = get_all_sources()
        assert len(sources) > 0

    def test_all_categories_present(self):
        sources = get_all_sources()
        tags = {s["tag"] for s in sources}
        assert tags == set(SOURCES.keys())

    def test_each_source_has_required_fields(self):
        sources = get_all_sources()
        for s in sources:
            assert "name" in s
            assert "url" in s
            assert "type" in s
            assert "tag" in s

    def test_source_count_matches(self):
        sources = get_all_sources()
        total = sum(len(cat["feeds"]) for cat in SOURCES.values())
        assert len(sources) == total

    def test_returns_same_list_on_repeated_calls(self):
        s1 = get_all_sources()
        s2 = get_all_sources()
        assert s1 is s2


class TestGetSourcesByTags:
    def test_empty_tags_returns_all(self):
        all_sources = get_all_sources()
        result = get_sources_by_tags([])
        assert len(result) == len(all_sources)

    def test_single_tag(self):
        result = get_sources_by_tags(["finance"])
        assert len(result) > 0
        assert all(s["tag"] == "finance" for s in result)

    def test_multiple_tags(self):
        result = get_sources_by_tags(["finance", "crypto"])
        assert len(result) > 0
        assert all(s["tag"] in ("finance", "crypto") for s in result)

    def test_invalid_tag(self):
        result = get_sources_by_tags(["nonexistent"])
        assert result == []

    def test_mixed_valid_invalid(self):
        result = get_sources_by_tags(["finance", "nonexistent"])
        assert len(result) > 0
        assert all(s["tag"] == "finance" for s in result)


class TestGetSourceTagsDisplay:
    def test_returns_all_categories(self):
        display = get_source_tags_display("ru")
        assert len(display) == len(SOURCES)

    def test_each_entry_has_fields(self):
        display = get_source_tags_display("ru")
        for item in display:
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "count" in item

    def test_ru_vs_en_names(self):
        ru = get_source_tags_display("ru")
        en = get_source_tags_display("en")
        ru_names = {d["id"]: d["name"] for d in ru}
        en_names = {d["id"]: d["name"] for d in en}
        assert ru_names["finance"] != en_names["finance"]

    def test_count_matches_feeds(self):
        display = get_source_tags_display("ru")
        for item in display:
            cat = SOURCES[item["id"]]
            assert item["count"] == len(cat["feeds"])
