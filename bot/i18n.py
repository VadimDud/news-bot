"""All user-facing strings keyed by language code."""

STRINGS = {
    "ru": {
        "welcome": (
            "👋 <b>Привет! Я Finance Bot 💰</b>\n\n"
            "Я отслеживаю финансовые новости по вашим бумагам\n"
            "и присылаю экспресс-анализ с Gemini AI.\n\n"
            "<b>Команды:</b>\n"
            "/start — Перезапустить бота\n"
            "/help — Подробная справка\n"
            "/finance — Меню анализа\n"
            "/admin — Панель управления\n\n"
            "Выбери действие:"
        ),
        "btn_finance": "💰 Финансовый анализ",
        "btn_lang": "🌐 Язык: RU",
        "btn_admin": "🔧 Админ-панель",
        "btn_back": "◀️ Назад",

        # Finance
        "finance_menu": (
            "💰 <b>Финансовый анализ</b>\n\n"
            "Твои подписки: {tickers}\n\n"
            "Выбери действие:"
        ),
        "finance_empty": (
            "💰 <b>Финансовый анализ</b>\n\n"
            "У тебя пока нет подписок на бумаги.\n"
            "Отправь тикер (например, <code>SBER</code>), чтобы добавить."
        ),
        "finance_add_ask": (
            "📝 <b>Добавление бумаги</b>\n\n"
            "Отправь мне тикер бумаги (например, <code>SBER</code>, <code>GAZP</code>, <code>RUBI</code>)."
        ),
        "finance_added": "✅ Бумага <code>{ticker}</code> добавлена в подписки!",
        "finance_invalid_ticker": "⚠️ Неверный формат тикера. Отправь 2–10 заглавных букв без пробелов (например, <code>SBER</code>).",
        "finance_remove_ask": "❌ Выбери бумагу для удаления:",
        "finance_list": (
            "📋 <b>Твои подписки:</b>\n\n{tickers}\n\n"
            "Отправь тикер, чтобы добавить ещё."
        ),
        "finance_scan_done": "✅ Найдено и отправлено {count} новых новостей.",
        "finance_no_news": "🔍 Свежих финансовых новостей пока нет.",
        "finance_all_seen": "ℹ️ Все найденные новости уже были отправлены ранее.",
        "fin_btn_scan": "🔍 Сканировать новости",
        "fin_btn_list": "📋 Мои подписки",
        "fin_btn_add": "➕ Добавить",
        "fin_btn_remove": "❌ Удалить",

        # Admin
        "admin_welcome": (
            "🔧 <b>Админ-панель</b>\n\n"
            "Привет, админ! Выбери действие:"
        ),
        "btn_broadcast": "📢 Рассылка",
        "btn_stats": "📊 Статистика",
        "admin_stats": "📊 <b>Статистика</b>\n\nЗарегистрировано пользователей: {count}",
        "admin_broadcast_ask": (
            "📢 <b>Рассылка</b>\n\n"
            "Отправь сообщение для рассылки всем пользователям.\n"
            "Или нажми «◀️ Назад» для отмены."
        ),
        "admin_broadcast_confirm": (
            "📢 Рассылка отправлена {count} пользователям."
        ),
        "admin_not_admin": "⛔ У тебя нет доступа к админ-панели.",

        "lang_changed": "🌐 Язык изменён на русский.",

        "help": (
            "📖 <b>Что умеет этот бот</b>\n\n"
            "Я отслеживаю финансовые новости по бумагам из твоей подписки\n"
            "и присылаю экспресс-анализ с помощью Gemini AI.\n\n"
            "<b>Команды:</b>\n"
            "/start — Перезапустить бота\n"
            "/help — Показать эту справку\n"
            "/finance — Меню анализа\n\n"
            "<b>Как пользоваться:</b>\n"
            "1. Добавь тикеры бумаг в подписки\n"
            "2. Нажми «Сканировать новости»\n"
            "3. Получи экспресс-оценку с Gemini\n\n"
            "<b>Для админа:</b>\n"
            "/admin — панель управления"
        ),
    },

    "en": {
        "welcome": (
            "👋 <b>Hello! I'm Finance Bot 💰</b>\n\n"
            "I track financial news for your securities\n"
            "and send express analysis powered by Gemini AI.\n\n"
            "<b>Commands:</b>\n"
            "/start — Restart the bot\n"
            "/help — Detailed help\n"
            "/finance — Analysis menu\n"
            "/admin — Admin panel\n\n"
            "Choose an action:"
        ),
        "btn_finance": "💰 Financial Analysis",
        "btn_lang": "🌐 Language: EN",
        "btn_admin": "🔧 Admin Panel",
        "btn_back": "◀️ Back",

        "finance_menu": (
            "💰 <b>Financial Analysis</b>\n\n"
            "Your subscriptions: {tickers}\n\n"
            "Choose an action:"
        ),
        "finance_empty": (
            "💰 <b>Financial Analysis</b>\n\n"
            "You have no security subscriptions yet.\n"
            "Send a ticker (e.g., <code>SBER</code>) to add one."
        ),
        "finance_add_ask": (
            "📝 <b>Add Security</b>\n\n"
            "Send me a ticker (e.g., <code>SBER</code>, <code>GAZP</code>, <code>RUBI</code>)."
        ),
        "finance_added": "✅ Security <code>{ticker}</code> added to subscriptions!",
        "finance_invalid_ticker": "⚠️ Invalid ticker format. Send 2–10 uppercase letters without spaces (e.g., <code>SBER</code>).",
        "finance_remove_ask": "❌ Choose a security to remove:",
        "finance_list": (
            "📋 <b>Your subscriptions:</b>\n\n{tickers}\n\n"
            "Send a ticker to add more."
        ),
        "finance_scan_done": "✅ Found and sent {count} new news items.",
        "finance_no_news": "🔍 No financial news available yet.",
        "finance_all_seen": "ℹ️ All found news was already sent earlier.",
        "fin_btn_scan": "🔍 Scan News",
        "fin_btn_list": "📋 My Subscriptions",
        "fin_btn_add": "➕ Add",
        "fin_btn_remove": "❌ Remove",

        "admin_welcome": (
            "🔧 <b>Admin Panel</b>\n\n"
            "Hey, admin! Choose an action:"
        ),
        "btn_broadcast": "📢 Broadcast",
        "btn_stats": "📊 Statistics",
        "admin_stats": "📊 <b>Statistics</b>\n\nRegistered users: {count}",
        "admin_broadcast_ask": (
            "📢 <b>Broadcast</b>\n\n"
            "Send a message to broadcast to all users.\n"
            "Or press «◀️ Back» to cancel."
        ),
        "admin_broadcast_confirm": "📢 Broadcast sent to {count} users.",
        "admin_not_admin": "⛔ You don't have access to the admin panel.",

        "lang_changed": "🌐 Language changed to English.",

        "help": (
            "📖 <b>What this bot does</b>\n\n"
            "I track financial news for your subscribed securities\n"
            "and send express analysis powered by Gemini AI.\n\n"
            "<b>Commands:</b>\n"
            "/start — Restart the bot\n"
            "/help — Show this help\n"
            "/finance — Analysis menu\n\n"
            "<b>How to use:</b>\n"
            "1. Add security tickers to your subscriptions\n"
            "2. Tap «Scan News»\n"
            "3. Get express analysis from Gemini\n\n"
            "<b>For admin:</b>\n"
            "/admin — admin panel"
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = STRINGS.get(lang, STRINGS["ru"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
