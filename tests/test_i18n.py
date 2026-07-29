import pytest
from bot.i18n import t, STRINGS


REQUIRED_KEYS = [
    "welcome_guest", "welcome_sub", "finance_menu", "finance_empty",
    "finance_add_ask", "finance_added", "finance_invalid_ticker",
    "finance_remove_ask", "finance_list", "finance_scan_done",
    "finance_no_news", "finance_all_seen", "admin_welcome",
    "admin_not_admin", "help", "lang_changed",
    "channels_menu", "channels_empty", "btn_create_channel",
    "channel_ask_name", "channel_ask_keywords", "channel_ask_ticker",
    "channel_created", "channel_created_with_ticker", "channel_created_no_ticker",
    "channel_already_exists", "channel_list_item", "channel_delete_confirm",
    "channel_deleted", "channel_scan_start", "channel_scan_done",
    "channel_no_news", "channel_edit_keywords", "channel_keywords_updated",
    "channel_scan_all", "channel_scan_all_done",
    "channel_ai_expanding", "channel_ai_expanded", "channel_ai_use_expanded",
    "channel_ai_use_original", "channel_ai_no_expansion",
    "btn_back", "btn_edit_keywords", "btn_ai_expand", "btn_delete",
    "about_text", "trial_activated", "trial_already_used", "buy_text",
    "support_text", "feedback_ask", "feedback_sent", "feedback_cancelled",
    "profile_text", "profile_no_access", "settings_text",
    "settings_notify", "settings_notify_off",
    "access_expired", "access_denied", "btn_extend", "expiry_reminder",
    "fin_btn_scan", "fin_btn_list", "fin_btn_add", "fin_btn_remove",
    "btn_broadcast", "btn_stats", "admin_broadcast_ask", "admin_broadcast_confirm",
    "btn_registrations", "admin_registrations",
    "news_header", "news_nav_prev", "news_nav_next", "news_nav_back", "news_no_items",
    "sub_btn_news", "sub_btn_tickers", "sub_btn_settings", "sub_btn_profile", "sub_btn_feedback",
    "finance_analyzing", "finance_analysis_ok", "finance_analysis_fallback",
    "channel_keywords_hint", "btn_about", "btn_buy", "btn_trial", "btn_support", "btn_lang",
]


class TestI18nKeys:
    def test_all_required_keys_in_ru(self):
        missing = [k for k in REQUIRED_KEYS if k not in STRINGS["ru"]]
        assert missing == [], f"Missing RU keys: {missing}"

    def test_all_required_keys_in_en(self):
        missing = [k for k in REQUIRED_KEYS if k not in STRINGS["en"]]
        assert missing == [], f"Missing EN keys: {missing}"

    def test_all_ru_keys_in_en(self):
        extra = set(STRINGS["ru"]) - set(STRINGS["en"])
        assert not extra, f"RU-only keys not in EN: {extra}"

    def test_all_en_keys_in_ru(self):
        extra = set(STRINGS["en"]) - set(STRINGS["ru"])
        assert not extra, f"EN-only keys not in RU: {extra}"


class TestTFunction:
    def test_simple_key(self):
        result = t("ru", "lang_changed")
        assert "русский" in result

    def test_with_kwargs(self):
        result = t("ru", "finance_added", ticker="SBER")
        assert "SBER" in result
        assert "добавлен" in result

    def test_missing_key_returns_key(self):
        result = t("ru", "nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_fallback_to_ru(self):
        result = t("xx", "finance_added", ticker="TEST")
        assert "TEST" in result

    def test_en_string(self):
        result = t("en", "finance_added", ticker="GAZP")
        assert "GAZP" in result
        assert "added" in result.lower()

    def test_channel_created_with_kwargs(self):
        result = t("ru", "channel_created", name="Ch", keywords="k1, k2", ticker_line="🏷 SBER")
        assert "Ch" in result
        assert "k1, k2" in result
        assert "SBER" in result

    def test_admin_stats_kwargs(self):
        result = t("ru", "admin_stats", total=10, new_today=2, new_week=5, lang_ru=7, lang_en=3, finance_subs=4, finance_tickers=8, news_sent=100)
        assert "10" in result
        assert "2" in result
        assert "100" in result
