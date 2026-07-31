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
        "btn_edit_keywords": "✏️ Ключевые слова",
        "btn_ai_expand": "🤖 AI расширить",
        "btn_delete": "❌ Удалить",

        # ── Subscriber menu ──
        "welcome_sub": (
            "📰 <b>Финансовый новостной бот</b>\n\n"
            "Подписка активна. Выберите действие:"
        ),
        "sub_btn_news": "🔥 Новости",
        "sub_btn_tickers": "🎯 Тикеры",
        "sub_btn_settings": "⚙️ Настройки",
        "sub_btn_profile": "👤 Профиль",
        "sub_btn_feedback": "💬 Обратная связь",

        "feedback_ask": (
            "💬 <b>Обратная связь</b>\n\n"
            "Напишите ваше замечание, предложение или отзыв.\n"
            "Сообщение будет передано администратору.\n\n"
            "«◀️ Назад» — отмена."
        ),
        "feedback_sent": (
            "✅ <b>Спасибо!</b>\n\n"
            "Ваше сообщение отправлено администратору.\n"
            "Мы постараемся ответить в ближайшее время."
        ),
        "feedback_cancelled": "↩️ Отправка отменена.",

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
        "scan_no_new_match": "ℹ️ Новых подходящих новостей нет. Попробуйте позже.",
        "fin_btn_scan": "🔍 Сканировать",
        "fin_btn_list": "📋 Подписки",
        "fin_btn_add": "➕ Добавить",
        "fin_btn_remove": "❌ Удалить",

        # ── Channels (universal topics) ──
        "channels_menu": (
            "📡 <b>Мои ленты</b>\n\n"
            "Создавайте ленты по темам. Бот находит новости по ключевым словам.\n\n"
            "{channels_list}"
        ),
        "channels_empty": (
            "📡 <b>Мои ленты</b>\n\n"
            "Пока нет ни одной ленты.\n"
            "Нажмите «➕ Создать ленту» чтобы начать."
        ),
        "btn_create_channel": "➕ Создать ленту",
        "btn_my_channels": "📡 Мои ленты",
        "channel_ask_name": (
            "📝 <b>Новая лента</b>\n\n"
            "Введите <b>название</b> для ленты.\n"
            "Например: <i>Макроэкономика</i>, <i>Газпром</i>, <i>Криптовалюта</i>\n\n"
            "«◀️ Назад» — отмена."
        ),
        "channel_ask_keywords": (
            "🔑 <b>{name}</b>\n\n"
            "Введите <b>ключевые слова</b> через запятую.\n"
            "Бот будет искать новости, где встречаются эти слова.\n\n"
            "<b>Примеры:</b>\n"
            "• <i>инфляция, ключевая ставка, курс рубля</i>\n"
            "• <i>добыча, экспорт, санкции</i>\n"
            "• <i>Газпром, газ, трубопровод</i>\n\n"
            "«◀️ Назад» — отмена."
        ),
        "channel_ask_ticker": (
            "🏷 <b>{name}</b>\n\n"
            "Введите <b>тикер</b> для привязки к бумаге (или <b>—</b> чтобы пропустить).\n\n"
            "<b>Примеры:</b> <code>SBER</code>, <code>GAZP</code>, <code>LKOH</code>\n\n"
            "«◀️ Назад» — отмена."
        ),
        "channel_created": (
            "✅ <b>Лента создана!</b>\n\n"
            "📡 {name}\n"
            "🔑 Ключевые слова: {keywords}\n"
            "{ticker_line}"
        ),
        "channel_created_with_ticker": "🏷 Тикер: <code>{ticker}</code>",
        "channel_created_no_ticker": "🏷 Тикер: не привязана",
        "channel_already_exists": "⚠️ Лента с таким именем уже существует.",
        "channel_list_item": (
            "📡 <b>{name}</b>\n"
            "   🔑 {keywords}\n"
            "{ticker_line}"
        ),
        "channel_delete_confirm": (
            "❌ Удалить ленту <b>{name}</b>?\n\n"
            "Это действие необратимо."
        ),
        "channel_deleted": "✅ Лента «{name}» удалена.",
        "channel_scan_start": "🔄 Сканирую ленту <b>{name}</b>...",
        "channel_scan_done": "✅ Найдено {count} новых новостей.",
        "channel_no_news": "ℹ️ Свежих новостей в ленте нет.",
        "scan_progress_rss": "📥 Загружаю новости из RSS...",
        "scan_progress_analyze": "🧠 Анализирую новости ({count} шт.)...",
        "scan_progress_done": "✅ Готово! Найдено {count} новых новостей.",
        "scan_timeout": "⏰ Сканирование заняло слишком много времени. Попробуйте позже.",
        "channel_keywords_hint": (
            "💡 <b>Совет:</b> Используйте cụ体ные слова для точного поиска.\n"
            "Чем точнее ключевые слова, тем лучше результат."
        ),
        "channel_edit_keywords": (
            "🔑 Редактирование ключевых слов ленты <b>{name}</b>\n\n"
            "Текущие: {keywords}\n\n"
            "Введите новые ключевые слова через запятую:"
        ),
        "channel_keywords_updated": "✅ Ключевые слова обновлены для ленты «{name}».",
        "channel_scan_all": "🔍 Сканирую все ленты...",
        "channel_scan_all_done": "✅ Сканирование завершено. Найдено {count} новых новостей.",
        "channel_ai_expanding": "🤖 AI расширяет ключевые слова для темы «{name}»...",
        "channel_ai_expanded": (
            "🤖 <b>AI предложил расширение:</b>\n\n"
            "🔑 Ваши ключевые слова: {user_keywords}\n\n"
            "🤖 Расширенный набор: {ai_keywords}\n\n"
            "Связанные тикеры: {related_tickers}\n\n"
            "Использовать расширенный набор?"
        ),
        "channel_ai_use_expanded": "✅ Использовать расширенный набор",
        "channel_ai_use_original": "📝 Оставить мои ключевые слова",
        "channel_ai_no_expansion": "ℹ️ AI не смог предложить расширение. Используем ваши ключевые слова.",
        "btn_edit_topics": "📚 Тематики",
        "channel_ask_topics_hint": (
            "Выберите <b>тематики</b> для фильтрации новостей.\n"
            "Новости, явно относящиеся к другим тематикам, будут отсекаться.\n"
            "Введите ID через запятую:"
        ),
        "channel_ask_topics_skip": "«—» — пропустить (тематики определятся автоматически).",
        "channel_edit_topics": (
            "📚 Редактирование тематик ленты <b>{name}</b>\n\n"
            "{topics_list}\n\n"
            "Введите ID через запятую или «—» чтобы сбросить:"
        ),
        "channel_topics_updated": "✅ Тематики обновлены для ленты «{name}».",

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
        "btn_edit_keywords": "✏️ Keywords",
        "btn_ai_expand": "🤖 AI Expand",
        "btn_delete": "❌ Delete",

        # ── Subscriber menu ──
        "welcome_sub": (
            "📰 <b>Financial News Bot</b>\n\n"
            "Subscription active. Choose an action:"
        ),
        "sub_btn_news": "🔥 News",
        "sub_btn_tickers": "🎯 Tickers",
        "sub_btn_settings": "⚙️ Settings",
        "sub_btn_profile": "👤 Profile",
        "sub_btn_feedback": "💬 Feedback",

        "feedback_ask": (
            "💬 <b>Feedback</b>\n\n"
            "Write your remark, suggestion or review.\n"
            "The message will be forwarded to the administrator.\n\n"
            "«◀️ Back» — cancel."
        ),
        "feedback_sent": (
            "✅ <b>Thank you!</b>\n\n"
            "Your message has been sent to the administrator.\n"
            "We'll try to respond as soon as possible."
        ),
        "feedback_cancelled": "↩️ Sending cancelled.",

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
        "scan_no_new_match": "ℹ️ No new matching news. Try again later.",
        "fin_btn_scan": "🔍 Scan",
        "fin_btn_list": "📋 Tickers",
        "fin_btn_add": "➕ Add",
        "fin_btn_remove": "❌ Remove",

        # ── Channels (universal topics) ──
        "channels_menu": (
            "📡 <b>My Channels</b>\n\n"
            "Create topic channels. Bot finds news by keywords.\n\n"
            "{channels_list}"
        ),
        "channels_empty": (
            "📡 <b>My Channels</b>\n\n"
            "No channels yet.\n"
            "Tap «➕ Create Channel» to start."
        ),
        "btn_create_channel": "➕ Create Channel",
        "btn_my_channels": "📡 My Channels",
        "channel_ask_name": (
            "📝 <b>New Channel</b>\n\n"
            "Enter a <b>name</b> for the channel.\n"
            "e.g.: <i>Macroeconomics</i>, <i>Gazprom</i>, <i>Crypto</i>\n\n"
            "«◀️ Back» — cancel."
        ),
        "channel_ask_keywords": (
            "🔑 <b>{name}</b>\n\n"
            "Enter <b>keywords</b> separated by commas.\n"
            "Bot will find news containing these words.\n\n"
            "<b>Examples:</b>\n"
            "• <i>inflation, key rate, ruble exchange rate</i>\n"
            "• <i>production, export, sanctions</i>\n"
            "• <i>Gazprom, gas, pipeline</i>\n\n"
            "«◀️ Back» — cancel."
        ),
        "channel_ask_ticker": (
            "🏷 <b>{name}</b>\n\n"
            "Enter a <b>ticker</b> to link to a stock (or <b>—</b> to skip).\n\n"
            "<b>Examples:</b> <code>SBER</code>, <code>GAZP</code>, <code>LKOH</code>\n\n"
            "«◀️ Back» — cancel."
        ),
        "channel_created": (
            "✅ <b>Channel created!</b>\n\n"
            "📡 {name}\n"
            "🔑 Keywords: {keywords}\n"
            "{ticker_line}"
        ),
        "channel_created_with_ticker": "🏷 Ticker: <code>{ticker}</code>",
        "channel_created_no_ticker": "🏷 Ticker: not linked",
        "channel_already_exists": "⚠️ Channel with this name already exists.",
        "channel_list_item": (
            "📡 <b>{name}</b>\n"
            "   🔑 {keywords}\n"
            "{ticker_line}"
        ),
        "channel_delete_confirm": (
            "❌ Delete channel <b>{name}</b>?\n\n"
            "This action is irreversible."
        ),
        "channel_deleted": "✅ Channel «{name}» deleted.",
        "channel_scan_start": "🔄 Scanning channel <b>{name}</b>...",
        "channel_scan_done": "✅ Found {count} new news items.",
        "channel_no_news": "ℹ️ No new news in this channel.",
        "scan_progress_rss": "📥 Fetching news from RSS...",
        "scan_progress_analyze": "🧠 Analyzing news ({count} items)...",
        "scan_progress_done": "✅ Done! Found {count} new news items.",
        "scan_timeout": "⏰ Scan took too long. Please try again later.",
        "channel_keywords_hint": (
            "💡 <b>Tip:</b> Use specific words for better search.\n"
            "The more precise the keywords, the better the results."
        ),
        "channel_edit_keywords": (
            "🔑 Editing keywords for channel <b>{name}</b>\n\n"
            "Current: {keywords}\n\n"
            "Enter new keywords separated by commas:"
        ),
        "channel_keywords_updated": "✅ Keywords updated for channel «{name}».",
        "channel_scan_all": "🔍 Scanning all channels...",
        "channel_scan_all_done": "✅ Scan complete. Found {count} new news items.",
        "channel_ai_expanding": "🤖 AI expanding keywords for topic «{name}»...",
        "channel_ai_expanded": (
            "🤖 <b>AI suggested expansion:</b>\n\n"
            "🔑 Your keywords: {user_keywords}\n\n"
            "🤖 Expanded set: {ai_keywords}\n\n"
            "Related tickers: {related_tickers}\n\n"
            "Use expanded set?"
        ),
        "channel_ai_use_expanded": "✅ Use expanded set",
        "channel_ai_use_original": "📝 Keep my keywords",
        "channel_ai_no_expansion": "ℹ️ AI couldn't suggest expansion. Using your keywords.",
        "btn_edit_topics": "📚 Topics",
        "channel_ask_topics_hint": (
            "Choose the <b>topics</b> for news filtering.\n"
            "News clearly belonging to other topics will be rejected.\n"
            "Enter IDs separated by commas:"
        ),
        "channel_ask_topics_skip": "«—» — skip (topics will be inferred automatically).",
        "channel_edit_topics": (
            "📚 Editing topics for channel <b>{name}</b>\n\n"
            "{topics_list}\n\n"
            "Enter IDs separated by commas, or «—» to clear:"
        ),
        "channel_topics_updated": "✅ Topics updated for channel «{name}».",

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
