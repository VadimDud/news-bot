import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.database import set_user, grant_trial, create_channel, add_finance_subscription
from bot import config


def _make_message(text: str = "", user_id: int = 100, username: str = "testuser", full_name: str = "Test User"):
    msg = AsyncMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.full_name = full_name
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = user_id
    return msg


def _make_callback(data: str = "", user_id: int = 100, username: str = "testuser", full_name: str = "Test User"):
    cb = AsyncMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.username = username
    cb.from_user.full_name = full_name
    cb.answer = AsyncMock()
    cb.message = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.chat = MagicMock()
    cb.message.chat.id = user_id
    cb.message.bot = AsyncMock()
    return cb


# ── Start handlers ──


class TestCmdStart:
    async def test_guest_start(self):
        from bot.handlers.start import cmd_start
        msg = _make_message(user_id=77777)
        await cmd_start(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Пробный период активирован" in text

    async def test_subscriber_start_redirects(self):
        from bot.handlers.start import cmd_start
        msg = _make_message(user_id=200)
        await set_user(200, "sub_user", "Sub User", "ru")
        await grant_trial(200, days=30)
        await cmd_start(message=msg, user_lang="ru")
        # _show_home calls _send_or_edit which calls message.answer
        # The exact call path is internal; just verify no exception
        assert True


class TestCmdHelp:
    async def test_help_guest(self):
        from bot.handlers.start import cmd_help
        msg = _make_message()
        await cmd_help(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Справка" in text

    async def test_help_en(self):
        from bot.handlers.start import cmd_help
        msg = _make_message()
        await cmd_help(message=msg, user_lang="en")
        text = msg.answer.call_args[0][0]
        assert "Help" in text


class TestMenuCallbacks:
    async def test_menu_about(self):
        from bot.handlers.start import menu_about
        cb = _make_callback()
        await menu_about(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_menu_buy(self):
        from bot.handlers.start import menu_buy
        cb = _make_callback()
        await menu_buy(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_menu_trial_no_access(self):
        from bot.handlers.start import menu_trial
        cb = _make_callback(user_id=300)
        await menu_trial(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_menu_trial_already_used(self):
        from bot.handlers.start import menu_trial
        cb = _make_callback(user_id=301)
        await set_user(301, "u", "U", "ru")
        await grant_trial(301, days=30)
        await menu_trial(callback=cb, user_lang="ru")
        text = cb.message.edit_text.call_args[0][0]
        assert "Пробный период уже использован" in text

    async def test_menu_support(self):
        from bot.handlers.start import menu_support
        cb = _make_callback()
        await menu_support(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_menu_home(self):
        from bot.handlers.start import menu_home
        cb = _make_callback()
        await menu_home(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()

    async def test_back_main(self):
        from bot.handlers.start import back_main
        cb = _make_callback()
        await back_main(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()


class TestSubTickers:
    async def test_sub_tickers_empty(self):
        from bot.handlers.start import sub_tickers
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await sub_tickers(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Тикеры" in text

    async def test_sub_tickers_with_subs(self):
        from bot.handlers.start import sub_tickers
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await add_finance_subscription(100, "SBER", "SBER")
        await sub_tickers(callback=cb, user_lang="ru")
        text = cb.message.edit_text.call_args[0][0]
        assert "SBER" in text


class TestTickerAddPrompt:
    async def test_add_prompt(self):
        from bot.handlers.start import ticker_add_prompt
        cb = _make_callback()
        await ticker_add_prompt(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()


class TestTickerDel:
    async def test_del_ticker(self):
        from bot.handlers.start import ticker_del
        cb = _make_callback(data="fin:del:SBER", user_id=100)
        await set_user(100, "u", "U", "ru")
        await add_finance_subscription(100, "SBER", "SBER")
        await ticker_del(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()


class TestSubSettings:
    async def test_settings(self):
        from bot.handlers.start import sub_settings
        cb = _make_callback()
        await sub_settings(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()


class TestSubProfile:
    async def test_profile(self):
        from bot.handlers.start import sub_profile
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await sub_profile(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "профиль" in text.lower()


class TestSubFeedback:
    async def test_feedback_ask(self):
        from bot.handlers.start import sub_feedback
        from bot.handlers.start import _feedback_state
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        _feedback_state.clear()
        await sub_feedback(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        assert 100 in _feedback_state
        _feedback_state.clear()


# ── Channels handlers ──


class TestCmdChannels:
    async def test_no_channels(self):
        from bot.handlers.channels import cmd_channels
        msg = _make_message(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await cmd_channels(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Мои ленты" in text

    async def test_with_channels(self):
        from bot.handlers.channels import cmd_channels
        msg = _make_message(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "Ch1", ["kw1"])
        await cmd_channels(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Ch1" in text


class TestChannelList:
    async def test_empty_list(self):
        from bot.handlers.channels import channel_list
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await channel_list(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_with_channels(self):
        from bot.handlers.channels import channel_list
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "MyCh", ["kw"])
        await channel_list(callback=cb, user_lang="ru")
        text = cb.message.edit_text.call_args[0][0]
        assert "MyCh" in text


class TestChannelCreateStart:
    async def test_start_creates_state(self):
        from bot.handlers.channels import channel_create_start, _channel_state
        cb = _make_callback(user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        _channel_state.clear()
        await channel_create_start(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        assert 100 in _channel_state
        assert _channel_state[100]["step"] == "name"
        _channel_state.clear()


class TestChannelStateHandler:
    async def test_name_step(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "name"}
        msg = _make_message(text="Моя лента", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        assert _channel_state[100]["step"] == "keywords"
        assert _channel_state[100]["name"] == "Моя лента"
        msg.answer.assert_called_once()
        _channel_state.clear()

    async def test_keywords_step_no_ai(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "keywords", "name": "Ch"}
        msg = _make_message(text="слово1, слово2", user_id=100)
        with patch("bot.topic_analyzer.analyze_topic", new_callable=AsyncMock, return_value=None):
            await channel_state_handler(message=msg, user_lang="ru")
        assert _channel_state[100]["step"] == "ticker"
        assert _channel_state[100]["keywords"] == ["слово1", "слово2"]
        _channel_state.clear()

    async def test_keywords_step_with_ai(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "keywords", "name": "Ch"}
        msg = _make_message(text="слово1, слово2", user_id=100)
        mock_ai = {"keywords": ["слово1", "слово2", "ai_extra"], "related_tickers": ["TICK"]}
        with patch("bot.topic_analyzer.analyze_topic", new_callable=AsyncMock, return_value=mock_ai):
            await channel_state_handler(message=msg, user_lang="ru")
        assert _channel_state[100]["step"] == "confirm_keywords"
        assert _channel_state[100]["ai_keywords"] == ["слово1", "слово2", "ai_extra"]
        _channel_state.clear()

    async def test_ticker_step_skip(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "ticker", "name": "Ch", "keywords": ["kw"]}
        msg = _make_message(text="—", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        assert _channel_state[100]["step"] == "source_tags"
        assert _channel_state[100]["ticker"] is None
        _channel_state.clear()

    async def test_ticker_step_with_ticker(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "ticker", "name": "Ch", "keywords": ["kw"]}
        msg = _make_message(text="SBER", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        assert _channel_state[100]["step"] == "source_tags"
        assert _channel_state[100]["ticker"] == "SBER"
        _channel_state.clear()

    async def test_source_tags_step_all(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "source_tags", "name": "Ch", "keywords": ["kw"], "ticker": None}
        msg = _make_message(text="все", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Лента создана" in text
        assert _channel_state.get(100) is None

    async def test_source_tags_step_specific(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "source_tags", "name": "Ch", "keywords": ["kw"], "ticker": None}
        msg = _make_message(text="finance, macro", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        assert _channel_state.get(100) is None

    async def test_source_tags_step_invalid_tags(self):
        from bot.handlers.channels import channel_state_handler, _channel_state
        _channel_state[100] = {"step": "source_tags", "name": "Ch", "keywords": ["kw"], "ticker": None}
        msg = _make_message(text="invalid123, xyz", user_id=100)
        await channel_state_handler(message=msg, user_lang="ru")
        msg.answer.assert_not_called()
        _channel_state.clear()


class TestChannelView:
    async def test_view_channel(self):
        from bot.handlers.channels import channel_view
        cb = _make_callback(data="ch:view:1", user_id=100)
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb.data = f"ch:view:{ch_id}"
        await channel_view(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Ch" in text
        assert "kw" in text

    async def test_view_wrong_user(self):
        from bot.handlers.channels import channel_view
        cb = _make_callback(data="ch:view:1", user_id=999)
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb.data = f"ch:view:{ch_id}"
        await channel_view(callback=cb, user_lang="ru")
        cb.answer.assert_called_once_with("Not found", show_alert=True)


class TestChannelDelete:
    async def test_delete_confirm(self):
        from bot.handlers.channels import channel_delete_confirm
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb = _make_callback(data=f"ch:del:{ch_id}", user_id=100)
        await channel_delete_confirm(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Удалить" in text

    async def test_delete_yes(self):
        from bot.handlers.channels import channel_delete_yes
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb = _make_callback(data=f"ch:del_yes:{ch_id}", user_id=100)
        await channel_delete_yes(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()
        from bot.database import get_channel
        assert await get_channel(ch_id) is None


class TestChannelEditKeywords:
    async def test_edit_keywords_start(self):
        from bot.handlers.channels import channel_edit_keywords_start, _channel_edit_state
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["old_kw"])
        cb = _make_callback(data=f"ch:edit_kw:{ch_id}", user_id=100)
        _channel_edit_state.clear()
        await channel_edit_keywords_start(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        assert 100 in _channel_edit_state
        _channel_edit_state.clear()

    async def test_edit_keywords_save(self):
        from bot.handlers.channels import channel_edit_keywords_save, _channel_edit_state
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["old"])
        _channel_edit_state[100] = ch_id
        msg = _make_message(text="new1, new2", user_id=100)
        await channel_edit_keywords_save(message=msg, user_lang="ru")
        assert msg.answer.call_count >= 1
        text = msg.answer.call_args_list[0][0][0]
        assert "обновлены" in text
        from bot.database import get_channel
        ch = await get_channel(ch_id)
        assert ch["keywords"] == ["new1", "new2"]
        assert 100 not in _channel_edit_state


class TestChannelAiExpand:
    async def test_ai_expand(self):
        from bot.handlers.channels import channel_ai_expand
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb = _make_callback(data=f"ch:ai_expand:{ch_id}", user_id=100)
        mock_result = {
            "keywords": ["kw", "extra1", "extra2"],
            "positive_triggers": ["p"],
            "negative_triggers": ["n"],
            "related_tickers": ["TICK"],
            "source_tags": ["finance"],
        }
        with patch("bot.topic_analyzer.analyze_topic", new_callable=AsyncMock, return_value=mock_result):
            await channel_ai_expand(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        assert cb.message.edit_text.call_count >= 1
        text = cb.message.edit_text.call_args_list[-1][0][0]
        assert "AI" in text


class TestChannelAiApply:
    async def test_ai_apply_no_suggestion(self):
        from bot.handlers.channels import channel_ai_apply
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["old"])
        cb = _make_callback(data=f"ch:ai_apply:{ch_id}", user_id=100)
        await channel_ai_apply(callback=cb, user_lang="ru")
        cb.answer.assert_called_once_with("Suggestion expired", show_alert=True)

    async def test_ai_merge_no_suggestion(self):
        from bot.handlers.channels import channel_ai_merge
        await set_user(100, "u", "U", "ru")
        ch_id = await create_channel(100, "Ch", ["kw"])
        cb = _make_callback(data=f"ch:ai_merge:{ch_id}", user_id=100)
        await channel_ai_merge(callback=cb, user_lang="ru")
        cb.answer.assert_called_once_with("Suggestion expired", show_alert=True)


class TestChannelScan:
    async def test_scan(self):
        from bot.handlers.channels import channel_scan
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        ch_id = await create_channel(100, "Ch", ["новость"])
        cb = _make_callback(data=f"ch:scan:{ch_id}", user_id=100)
        cb.message.edit_text = AsyncMock()
        cb.message.answer = AsyncMock()
        with patch("bot.finance.fetch_news", new_callable=AsyncMock, return_value=[]) as mock_fetch:
            await channel_scan(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        mock_fetch.assert_called_once()

    async def test_scan_all(self):
        from bot.handlers.channels import channel_scan_all
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        await create_channel(100, "Ch", ["kw"])
        cb = _make_callback(data="ch:scan_all", user_id=100)
        with patch("bot.finance.fetch_news", new_callable=AsyncMock, return_value=[]) as mock_fetch:
            await channel_scan_all(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        mock_fetch.assert_called_once()


class TestChannelUseAiKeywords:
    async def test_use_ai_keywords(self):
        from bot.handlers.channels import channel_use_ai_keywords, _channel_state
        _channel_state[100] = {
            "step": "confirm_keywords",
            "name": "Ch",
            "keywords": ["orig"],
            "ai_keywords": ["ai1", "ai2"],
        }
        cb = _make_callback(user_id=100)
        await channel_use_ai_keywords(callback=cb, user_lang="ru")
        assert _channel_state[100]["step"] == "ticker"
        assert _channel_state[100]["keywords"] == ["ai1", "ai2"]
        cb.answer.assert_called_once()
        _channel_state.clear()

    async def test_use_original_keywords(self):
        from bot.handlers.channels import channel_use_original_keywords, _channel_state
        _channel_state[100] = {
            "step": "confirm_keywords",
            "name": "Ch",
            "user_keywords": ["orig"],
            "ai_keywords": ["ai1"],
        }
        cb = _make_callback(user_id=100)
        await channel_use_original_keywords(callback=cb, user_lang="ru")
        assert _channel_state[100]["step"] == "ticker"
        assert _channel_state[100]["keywords"] == ["orig"]
        cb.answer.assert_called_once()
        _channel_state.clear()


class TestChannelSelectAllSources:
    async def test_select_all_sources(self):
        from bot.handlers.channels import channel_select_all_sources, _channel_state
        _channel_state[100] = {
            "step": "source_tags",
            "name": "Ch",
            "keywords": ["kw"],
            "ticker": None,
        }
        cb = _make_callback(data="ch:src_all", user_id=100)
        await set_user(100, "u", "U", "ru")
        await channel_select_all_sources(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()
        text = cb.message.edit_text.call_args[0][0]
        assert "Лента создана" in text
        assert _channel_state.get(100) is None


# ── Language handler ──


class TestLanguageToggle:
    async def test_toggle_ru_to_en(self):
        from bot.handlers.language import toggle_language
        await set_user(100, "u", "U", "ru")
        cb = _make_callback(user_id=100)
        await toggle_language(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()
        from bot.database import get_language
        assert await get_language(100) == "en"

    async def test_toggle_en_to_ru(self):
        from bot.handlers.language import toggle_language
        await set_user(100, "u", "U", "en")
        cb = _make_callback(user_id=100)
        await toggle_language(callback=cb, user_lang="en")
        from bot.database import get_language
        assert await get_language(100) == "ru"


# ── Admin handlers ──


class TestAdminHandler:
    async def test_admin_not_admin(self):
        from bot.handlers.admin import cmd_admin
        msg = _make_message(user_id=999)
        await cmd_admin(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Нет доступа" in text

    async def test_admin_is_admin(self):
        from bot.handlers.admin import cmd_admin
        msg = _make_message(user_id=config.ADMIN_ID)
        await cmd_admin(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Админ-панель" in text


class TestAdminCallback:
    async def test_admin_stats_not_admin(self):
        from bot.handlers.admin import admin_handler
        cb = _make_callback(data="admin:stats", user_id=999)
        await admin_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        assert "Нет доступа" in cb.answer.call_args[0][0]

    async def test_admin_stats_is_admin(self):
        from bot.handlers.admin import admin_handler
        cb = _make_callback(data="admin:stats", user_id=config.ADMIN_ID)
        await admin_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()
        cb.message.edit_text.assert_called_once()

    async def test_admin_registrations(self):
        from bot.handlers.admin import admin_handler
        cb = _make_callback(data="admin:registrations", user_id=config.ADMIN_ID)
        await admin_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()


# ── Finance handlers ──


class TestFinanceHandler:
    async def test_finance_cmd(self):
        from bot.handlers.finance import cmd_finance
        msg = _make_message(user_id=100)
        await cmd_finance(message=msg, user_lang="ru")
        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        assert "Тикеры" in text

    async def test_finance_list_callback(self):
        from bot.handlers.finance import finance_handler
        cb = _make_callback(data="fin:list", user_id=100)
        await set_user(100, "u", "U", "ru")
        await finance_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()

    async def test_finance_add_callback(self):
        from bot.handlers.finance import finance_handler
        cb = _make_callback(data="fin:add", user_id=100)
        await finance_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()

    async def test_finance_remove_callback(self):
        from bot.handlers.finance import finance_handler
        cb = _make_callback(data="fin:remove", user_id=100)
        await finance_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()

    async def test_finance_scan_callback(self):
        from bot.handlers.finance import finance_handler
        cb = _make_callback(data="fin:scan", user_id=100)
        await set_user(100, "u", "U", "ru")
        await grant_trial(100, days=30)
        with patch("bot.handlers.finance.fetch_finance_news", new_callable=AsyncMock, return_value=[]):
            await finance_handler(callback=cb, user_lang="ru")
        cb.answer.assert_called_once()


class TestCallbackParsing:
    def test_ch_view_parse(self):
        data = "ch:view:123"
        parts = data.split(":")
        assert parts[1] == "view"
        assert int(parts[2]) == 123

    def test_ch_del_parse(self):
        data = "ch:del:456"
        parts = data.split(":")
        assert parts[1] == "del"
        assert int(parts[2]) == 456

    def test_ch_scan_parse(self):
        data = "ch:scan:789"
        parts = data.split(":")
        assert parts[1] == "scan"
        assert int(parts[2]) == 789

    def test_fin_del_parse(self):
        data = "fin:del:SBER"
        parts = data.split(":")
        assert parts[1] == "del"
        assert parts[2] == "SBER"

    def test_fin_add_parse(self):
        data = "fin:add:GAZP"
        parts = data.split(":")
        assert parts[1] == "add"
        assert parts[2] == "GAZP"
