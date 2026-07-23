import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db")

# Translation provider config
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEEPL_API_KEY: str = os.getenv("DEEPL_API_KEY", "")
SOCKS5_PROXY: str = os.getenv("SOCKS5_PROXY", "")
TELEGRAM_API_SERVER: str = os.getenv("TELEGRAM_API_SERVER", "")

# Gemini API for financial analysis
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
