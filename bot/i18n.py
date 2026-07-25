"""All user-facing strings keyed by language code."""

STRINGS = {
    "ru": {
        # ── Guest menu ──
        "welcome_guest": (
            "📰 <b>Финансовый новостной бот</b>\n\n"
            "Мониторю <i>Коммерсантъ</i>, <i>Интерфакс</i>, <i>ТАСС</i> и <i>Ведомости</i> каждые 30 минут.\n"
            "Фильтрую по тикерам: <code>SBER</code>, <code>GAZP</code>, <code>ОФЗ</code> и др.\n"
            "Анализирую тональность через <b>DeepSeek AI</b>.\n\n"
            "<b>Что умею:</b>\n"
            "• Автоматическая рассылка свежих новостей\n"
            "• Edit-in-place — одно сообщение обновляется без спама\n"
            "• Экспресс-анализ: позитив / негатив / нейтрально\n"
            "• 30 дней бесплатно без ограничений\n\n"
            "Нажмите <b>«Попробовать бесплатно»</b> для начала:"
        ),
        "btn_about": "📊 О боте",
        "btn_buy": "💳 Подписка",
        "btn_trial": "🎁 Попробовать бесплатно",
        "btn_support": "💬 Поддержка",
        "btn_lang": "🌐 Язык",

        "about_text": (
            "📊 <b>О боте</b>\n\n"
            "Источники: <i>Коммерсантъ</i>, <i>Интерфакс</i>, <i>ТАСС</i>, <i>Ведомости</i>.\n"
            "Фильтр по тикерам: <code>SBER</code>, <code>GAZP</code>, <code>LKOH</code>, <code>GMKN</code> и др.\n\n"
            "<b>Как это работает:</b>\n"
            "1. Каждые 30 минут сканирую 4 новостных источника\n"
            "2. Сопоставляю заголовки с вашими тикерами\n"
            "3. DeepSeek AI определяет тональность новости\n"
            "4. Обновляю сообщение в чате (edit-in-place)\n\n"
            "Бесплатный период — 30 дней. Далее — подписка."
        ),
        "trial_activated": (
            "🎉 <b>Пробный период активирован!</b>\n\n"
            "Полный доступ на <b>{days} дней</b> (до {until}).\n\n"
            "Нажмите <b>«🔥 Новости»</b> чтобы получить первый отчёт:"
        ),
        "trial_already_used": (
            "⚠️ Пробный период уже использован.\n\n"
            "Оформите подписку для полного доступа:"
        ),
        "buy_text": (
            "💳 <b>Оформление подписки</b>\n\n"
            "Выберите тариф:\n\n"
            "• 1 месяц — XXX ₽\n"
            "• 3 месяца — XXX ₽\n"
            "• 12 месяцев — XXX ₽\n\n"
            "_(Интеграция с оплатой будет добавлено позже)_"
        ),
        "support_text": (
            "💬 <b>Поддержка</b>\n\n"
            "По вопросам подписки и работы бота:\n"
            "@VP135792"
        ),
        "btn_back": "◀️ Назад",

        # ── Subscriber menu ──
        "welcome_sub": (
            "📰 <b>Финансовый новостной бот</b>\n\n"
            "Подписка активна. Выберите действие:"
        ),
        "sub_btn_news": "🔥 Новости",
        "sub_btn_tickers": "🎯 Тикеры",
        "sub_btn_settings": "⚙️ Настройки",
        "sub_btn_profile": "👤 Профиль",

        "profile_text": (
            "👤 <b>Мой профиль</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "📛 Имя: {username}\n\n"
            "📋 Подписка: {status}\n"
            "📅 До: {until}\n"
            "⏳ Осталось: {days} дней"
        ),
        "profile_no_access": (
            "👤 <b>Мой профиль</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "📛 Имя: {username}\n\n"
            "📋 Подписка: не активна\n\n"
            "Активируйте бесплатный период или оформите подписку."
        ),

        "settings_text": (
            "⚙️ <b>Настройки</b>\n\n"
            "Управление уведомлениями:"
        ),
        "settings_notify": "🔔 Уведомления: ВКЛ",
        "settings_notify_off": "🔕 Уведомления: ВЫКЛ",

        # ── Access denied ──
        "access_expired": (
            "⛔ <b>Доступ истёк</b>\n\n"
            "Подписка закончилась {until}.\n"
            "Продлите для продолжения."
        ),
        "access_denied": (
            "⛔ <b>Нет доступа</b>\n\n"
            "Активируйте бесплатный период или оформите подписку."
        ),
        "btn_extend": "💳 Продлить",

        # ── Expiry reminder ──
        "expiry_reminder": (
            "⏰ <b>Подписка истекает!</b>\n\n"
            "Заканчивается завтра.\n"
            "Продлите, чтобы не пропустить новости!"
        ),

        # ── Finance ──
        "finance_menu": (
            "🎯 <b>Тикеры</b>\n\n"
            "Подписки: {tickers}\n\n"
            "Выберите действие:"
        ),
        "finance_empty": (
            "🎯 <b>Тикеры</b>\n\n"
            "Пока нет подписок.\n"
            "Отправьте тикер (например, <code>SBER</code>) для добавления."
        ),
        "finance_add_ask": (
            "📝 <b>Добавление тикера</b>\n\n"
            "Отправьте <b>название компании</b> или <b>тикер</b>.\n"
            "Бот проанализирует через AI и сохранит правила фильтрации.\n\n"
            "<b>Примеры:</b>\n"
            "• <code>Сбербанк</code> или <code>SBER</code>\n"
            "• <code>Газпром</code> или <code>GAZP</code>\n"
            "• <code>ФосАгро</code> или <code>PhosAgro</code>\n\n"
            "⚠️ <i>Не используйте внутренние коды брокера — бот не найдёт новости.</i>"
        ),
        "finance_added": "✅ <code>{ticker}</code> добавлен!",
        "finance_analyzing": "🔄 Анализирую <code>{ticker}</code> через AI...",
        "finance_analysis_ok": (
            "✅ <b>{ticker}</b> ({name}) — готово!\n\n"
            "📝 {description}\n\n"
            "🔑 Ключевых слов: {kw_count}\n"
            "🟢 Позитивных: {pos_count}\n"
            "🔴 Негативных: {neg_count}\n\n"
            "Новости фильтруются автоматически."
        ),
        "finance_analysis_fallback": (
            "⚠️ <b>{ticker}</b> — AI не смог проанализировать.\n\n"
            "Добавлен с базовой фильтрацией.\n"
            "Отправьте <b>название компании</b> для точного анализа."
        ),
        "finance_invalid_ticker": "⚠️ Формат: 2–10 заглавных букв (например, <code>SBER</code>).",
        "finance_remove_ask": "❌ Выберите бумагу для удаления:",
        "finance_list": (
            "📋 <b>Подписки:</b>\n\n{tickers}\n\n"
            "Отправьте тикер для добавления."
        ),
        "finance_scan_done": "✅ Найдено {count} новых новостей.",
        "finance_no_news": "🔍 Свежих новостей пока нет.",
        "finance_all_seen": "ℹ️ Все новости уже отправлены.",
        "fin_btn_scan": "🔍 Сканировать",
        "fin_btn_list": "📋 Подписки",
        "fin_btn_add": "➕ Добавить",
        "fin_btn_remove": "❌ Удалить",

        # ── Admin ──
        "admin_welcome": (
            "🔧 <b>Админ-панель</b>\n\n"
            "Выберите действие:"
        ),
        "btn_broadcast": "📢 Рассылка",
        "btn_stats": "📊 Статистика",
        "admin_stats": (
            "📊 <b>Статистика</b>\n\n"
            "👥 Всего: {total}\n"
            "🆕 Сегодня: {new_today} | Неделя: {new_week}\n\n"
            "🌐 RU — {lang_ru} | EN — {lang_en}\n\n"
            "💰 Финансы:\n"
            "   Подписчиков: {finance_subs}\n"
            "   Тикеров: {finance_tickers}\n"
            "   Новостей: {news_sent}"
        ),
        "admin_broadcast_ask": (
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте сообщение для рассылки.\n"
            "«◀️ Назад» для отмены."
        ),
        "admin_broadcast_confirm": (
            "📢 Рассылка отправлена {count} пользователям."
        ),
        "admin_not_admin": "⛔ Нет доступа к админ-панели.",
        "btn_registrations": "📋 Регистрации",
        "admin_registrations": (
            "📋 <b>Регистрации</b>\n\n"
            "{table}\n\n"
            "Всего: {total}"
        ),

        "lang_changed": "🌐 Язык: русский.",

        "help": (
            "📖 <b>Справка</b>\n\n"
            "Отслеживаю финансовые новости по вашим тикерам.\n"
            "Источники: Коммерсантъ, Интерфакс, ТАСС, Ведомости.\n"
            "Анализ тональности: DeepSeek AI.\n\n"
            "<b>Команды:</b>\n"
            "/start — Главное меню\n"
            "/help — Эта справка\n\n"
            "<b>Как пользоваться:</b>\n"
            "1. Нажмите «Попробовать бесплатно»\n"
            "2. Добавьте тикеры (SBER, GAZP и др.)\n"
            "3. Нажмите «Новости» для получения отчёта\n"
            "4. Бот будет обновлять сообщение каждые 30 минут"
        ),

        # ── News pagination ──
        "news_header": "📰 <b>Новости</b> ({current}/{total})\n\n",
        "news_nav_prev": "◀️ Пред",
        "news_nav_next": "След ▶️",
        "news_nav_back": "◀️ Меню",
        "news_no_items": "ℹ️ Нет новостей.",
    },

    "en": {
        # ── Guest menu ──
        "welcome_guest": (
            "📰 <b>Financial News Bot</b>\n\n"
            "Scanning <i>Kommersant</i>, <i>Interfax</i>, <i>TASS</i>, and <i>Vedomosti</i> every 30 min.\n"
            "Filtering by tickers: <code>SBER</code>, <code>GAZP</code>, <code>OFZ</code> and more.\n"
            "Sentiment analysis via <b>DeepSeek AI</b>.\n\n"
            "<b>Features:</b>\n"
            "• Auto-delivery of fresh news\n"
            "• Edit-in-place — one message updates, no spam\n"
            "• Express analysis: positive / negative / neutral\n"
            "• 30 days free, no limits\n\n"
            "Tap <b>«Free Trial»</b> to start:"
        ),
        "btn_about": "📊 About",
        "btn_buy": "💳 Subscribe",
        "btn_trial": "🎁 Free Trial",
        "btn_support": "💬 Support",
        "btn_lang": "🌐 Language",

        "about_text": (
            "📊 <b>About the Bot</b>\n\n"
            "Sources: <i>Kommersant</i>, <i>Interfax</i>, <i>TASS</i>, <i>Vedomosti</i>.\n"
            "Tickers: <code>SBER</code>, <code>GAZP</code>, <code>LKOH</code>, <code>GMKN</code> and more.\n\n"
            "<b>How it works:</b>\n"
            "1. Scans 4 news sources every 30 minutes\n"
            "2. Matches headlines to your tickers\n"
            "3. DeepSeek AI determines sentiment\n"
            "4. Updates the message in chat (edit-in-place)\n\n"
            "Free trial — 30 days. Then subscription."
        ),
        "trial_activated": (
            "🎉 <b>Trial activated!</b>\n\n"
            "Full access for <b>{days} days</b> (until {until}).\n\n"
            "Tap <b>«🔥 News»</b> for your first report:"
        ),
        "trial_already_used": (
            "⚠️ Free trial already used.\n\n"
            "Subscribe for full access:"
        ),
        "buy_text": (
            "💳 <b>Subscription Plans</b>\n\n"
            "Choose a plan:\n\n"
            "• 1 month — XXX ₽\n"
            "• 3 months — XXX ₽\n"
            "• 12 months — XXX ₽\n\n"
            "_(Payment integration coming soon)_"
        ),
        "support_text": (
            "💬 <b>Support</b>\n\n"
            "For subscription and bot issues:\n"
            "@VP135792"
        ),
        "btn_back": "◀️ Back",

        # ── Subscriber menu ──
        "welcome_sub": (
            "📰 <b>Financial News Bot</b>\n\n"
            "Subscription active. Choose an action:"
        ),
        "sub_btn_news": "🔥 News",
        "sub_btn_tickers": "🎯 Tickers",
        "sub_btn_settings": "⚙️ Settings",
        "sub_btn_profile": "👤 Profile",

        "profile_text": (
            "👤 <b>My Profile</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "📛 Name: {username}\n\n"
            "📋 Subscription: {status}\n"
            "📅 Until: {until}\n"
            "⏳ Days left: {days}"
        ),
        "profile_no_access": (
            "👤 <b>My Profile</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "📛 Name: {username}\n\n"
            "📋 Subscription: inactive\n\n"
            "Activate free trial or subscribe."
        ),

        "settings_text": (
            "⚙️ <b>Settings</b>\n\n"
            "Manage notifications:"
        ),
        "settings_notify": "🔔 Notifications: ON",
        "settings_notify_off": "🔕 Notifications: OFF",

        # ── Access denied ──
        "access_expired": (
            "⛔ <b>Access expired</b>\n\n"
            "Subscription ended {until}.\n"
            "Renew to continue."
        ),
        "access_denied": (
            "⛔ <b>No access</b>\n\n"
            "Activate free trial or subscribe."
        ),
        "btn_extend": "💳 Renew",

        # ── Expiry reminder ──
        "expiry_reminder": (
            "⏰ <b>Subscription expiring!</b>\n\n"
            "Ends tomorrow.\n"
            "Renew to stay updated!"
        ),

        # ── Finance ──
        "finance_menu": (
            "🎯 <b>Tickers</b>\n\n"
            "Subscriptions: {tickers}\n\n"
            "Choose an action:"
        ),
        "finance_empty": (
            "🎯 <b>Tickers</b>\n\n"
            "No subscriptions yet.\n"
            "Send a ticker (e.g., <code>SBER</code>) to add."
        ),
        "finance_add_ask": (
            "📝 <b>Add Ticker</b>\n\n"
            "Send a <b>company name</b> or <b>ticker</b>.\n"
            "Bot will analyze via AI and save filtering rules.\n\n"
            "<b>Examples:</b>\n"
            "• <code>Sberbank</code> or <code>SBER</code>\n"
            "• <code>Gazprom</code> or <code>GAZP</code>\n"
            "• <code>PhosAgro</code> or <code>PhosAgro</code>\n\n"
            "⚠️ <i>Don't use broker-internal codes — bot won't find news.</i>"
        ),
        "finance_added": "✅ <code>{ticker}</code> added!",
        "finance_analyzing": "🔄 Analyzing <code>{ticker}</code> via AI...",
        "finance_analysis_ok": (
            "✅ <b>{ticker}</b> ({name}) — done!\n\n"
            "📝 {description}\n\n"
            "🔑 Keywords: {kw_count}\n"
            "🟢 Positive: {pos_count}\n"
            "🔴 Negative: {neg_count}\n\n"
            "News filtered automatically."
        ),
        "finance_analysis_fallback": (
            "⚠️ <b>{ticker}</b> — AI couldn't analyze.\n\n"
            "Added with basic filtering.\n"
            "Send <b>company name</b> for accurate analysis."
        ),
        "finance_invalid_ticker": "⚠️ Format: 2–10 uppercase letters (e.g., <code>SBER</code>).",
        "finance_remove_ask": "❌ Choose security to remove:",
        "finance_list": (
            "📋 <b>Subscriptions:</b>\n\n{tickers}\n\n"
            "Send a ticker to add more."
        ),
        "finance_scan_done": "✅ Found {count} new news items.",
        "finance_no_news": "🔍 No news yet.",
        "finance_all_seen": "ℹ️ All news already sent.",
        "fin_btn_scan": "🔍 Scan",
        "fin_btn_list": "📋 Tickers",
        "fin_btn_add": "➕ Add",
        "fin_btn_remove": "❌ Remove",

        # ── Admin ──
        "admin_welcome": (
            "🔧 <b>Admin Panel</b>\n\n"
            "Choose an action:"
        ),
        "btn_broadcast": "📢 Broadcast",
        "btn_stats": "📊 Statistics",
        "admin_stats": (
            "📊 <b>Statistics</b>\n\n"
            "👥 Total: {total}\n"
            "🆕 Today: {new_today} | Week: {new_week}\n\n"
            "🌐 RU — {lang_ru} | EN — {lang_en}\n\n"
            "💰 Finance:\n"
            "   Subscribers: {finance_subs}\n"
            "   Tickers: {finance_tickers}\n"
            "   News sent: {news_sent}"
        ),
        "admin_broadcast_ask": (
            "📢 <b>Broadcast</b>\n\n"
            "Send a message to broadcast.\n"
            "«◀️ Back» to cancel."
        ),
        "admin_broadcast_confirm": "📢 Sent to {count} users.",
        "admin_not_admin": "⛔ No admin access.",
        "btn_registrations": "📋 Registrations",
        "admin_registrations": (
            "📋 <b>Registrations</b>\n\n"
            "{table}\n\n"
            "Total: {total}"
        ),

        "lang_changed": "🌐 Language: English.",

        "help": (
            "📖 <b>Help</b>\n\n"
            "Tracks financial news for your tickers.\n"
            "Sources: Kommersant, Interfax, TASS, Vedomosti.\n"
            "Sentiment: DeepSeek AI.\n\n"
            "<b>Commands:</b>\n"
            "/start — Main menu\n"
            "/help — This help\n\n"
            "<b>How to use:</b>\n"
            "1. Tap «Free Trial»\n"
            "2. Add tickers (SBER, GAZP, etc.)\n"
            "3. Tap «News» for your report\n"
            "4. Bot updates every 30 minutes"
        ),

        # ── News pagination ──
        "news_header": "📰 <b>News</b> ({current}/{total})\n\n",
        "news_nav_prev": "◀️ Prev",
        "news_nav_next": "Next ▶️",
        "news_nav_back": "◀️ Menu",
        "news_no_items": "ℹ️ No news.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["ru"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
