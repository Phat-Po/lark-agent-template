import logging
import os

APP_ENV = os.environ.get("APP_ENV", "development")
if APP_ENV not in ("development", "staging", "production"):
    raise ValueError(f"APP_ENV must be development, staging, or production; got '{APP_ENV}'")

_ENV_LOG_LEVELS = {"development": "DEBUG", "staging": "INFO", "production": "WARNING"}
LOG_LEVEL = os.environ.get("LOG_LEVEL", _ENV_LOG_LEVELS[APP_ENV]).upper()
_LOG_LEVEL_MAP = {name: lvl for lvl, name in logging._levelToName.items()}
if LOG_LEVEL not in _LOG_LEVEL_MAP:
    raise ValueError(f"LOG_LEVEL must be a valid logging level; got '{LOG_LEVEL}'")

DEBUG_ENDPOINTS_ENABLED = APP_ENV != "production"

# --- LLM provider (OpenAI-compatible: change env vars to switch provider) ---
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")

# --- Feishu/Lark app credentials ---
LARK_APP_ID = os.environ.get("LARK_APP_ID", "")
LARK_APP_SECRET = os.environ.get("LARK_APP_SECRET", "")

# --- Database ---
DB_PATH = os.environ.get("DB_PATH", "data/agent.db")
MAX_HISTORY_ROUNDS = int(os.environ.get("MAX_HISTORY_ROUNDS", "20"))
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS", "1800"))
MAX_TOKEN_BUDGET = int(os.environ.get("MAX_TOKEN_BUDGET", "3000"))
MESSAGE_DEDUP_SECONDS = int(os.environ.get("MESSAGE_DEDUP_SECONDS", "300"))

# --- Search ---
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")

# --- Bot display ---
BOT_DISPLAY_NAME = os.environ.get("BOT_DISPLAY_NAME", "Lark Agent")

# --- Agent behaviour ---
REQUIRE_WRITE_CONFIRMATION = os.environ.get("REQUIRE_WRITE_CONFIRMATION", "true").lower() in ("1", "true", "yes")
SYSTEM_PROMPT_FILE = os.environ.get("SYSTEM_PROMPT_FILE", "")
