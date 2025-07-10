import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    WEBY_API = os.getenv("WEBY_URL", "http://127.0.0.1:9999")
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", 256))
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
    API_KEYS = os.getenv("API_KEYS", "")
    MAX_CHAT_HISTORY_SIZE = 16
    TIMEOUT = int(os.getenv("TIMEOUT", 1200))
    DEBUG = os.getenv("DEBUG", False)
    CODE_GENERATION_MODEL = os.getenv("MODEL", "deepseek/deepseek-r1-0528")
    HTML_GENERATION_MODEL = "thudm/glm-4-9b:free"
