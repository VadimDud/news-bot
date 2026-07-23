import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

from bot import config
from bot.database import init_db
from bot.middlewares import LanguageMiddleware
from bot.handlers import start, language, finance, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Check your .env file.")
        sys.exit(1)

    logger.info("Initializing database...")
    await init_db()

    logger.info("Starting bot...")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    if config.TELEGRAM_API_SERVER:
        logger.info(f"Using Telegram API mirror: {config.TELEGRAM_API_SERVER}")
        bot.session.api = TelegramAPIServer.from_base(config.TELEGRAM_API_SERVER)
    dp = Dispatcher()

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_routers(
        start.router,
        language.router,
        finance.router,
        admin.router,
    )

    logger.info("Bot is now polling. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
