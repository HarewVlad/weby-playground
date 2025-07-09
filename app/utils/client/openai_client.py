from functools import lru_cache
from openai import AsyncOpenAI

from app.components.config import Config


@lru_cache(maxsize=1)
def get_openai_client():
    return AsyncOpenAI(
        base_url=Config.OPENAI_API_BASE,
        api_key=Config.OPENAI_API_KEY,
        timeout=Config.TIMEOUT,
    )


async def get_client():
    return get_openai_client()
