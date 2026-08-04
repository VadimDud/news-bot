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
HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
TELEGRAM_API_SERVER: str = os.getenv("TELEGRAM_API_SERVER", "")

# DeepSeek API for financial analysis (primary)
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Gemini API for financial analysis (fallback)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Alibaba DashScope (Qwen) API for financial analysis (fallback)
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-turbo")

# Default AI agent for analysis (primary provider in the priority chain)
DEFAULT_AGENT: str = os.getenv("DEFAULT_AGENT", "deepseek")

# Max time in seconds for a user-triggered scan before timing out
SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "120"))

# Max number of AI calls per scan (relevance/sentiment verification)
MAX_AI_CALLS_PER_SCAN: int = int(os.getenv("MAX_AI_CALLS_PER_SCAN", "8"))

# Auto-scan news interval (in seconds, default 3600 = 60 minutes)
AUTO_SCAN_INTERVAL: int = int(os.getenv("AUTO_SCAN_INTERVAL", "3600"))

# Web interface (web_app.py)
WEB_HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))
# Telegram Login Widget requires the bot username (without @), e.g. "my_news_bot"
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
# Optional secret for web session cookies. If empty, derived from BOT_TOKEN.
WEB_COOKIE_SECRET: str = os.getenv("WEB_COOKIE_SECRET", "")
# Set "true" when the web UI is served over HTTPS (behind Nginx/Cloudflare Tunnel)
WEB_COOKIE_SECURE: bool = os.getenv("WEB_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
