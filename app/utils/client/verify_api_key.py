from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.components.config import Config
from app.utils.logger import logger

# API Key Authorization
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# Dependency for API key validation
async def verify_api_key(api_key: str = Depends(api_key_header)):
    if Config.API_KEYS:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is missing",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if not Config.API_KEYS or api_key not in Config.API_KEYS:
            logger.warning(f"Invalid API key attempt: {api_key[:5]}...")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return api_key
