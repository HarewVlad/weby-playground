import time
from typing import Dict, Union

from fastapi import status, APIRouter

from app.utils.client.openai_client import get_openai_client
from app.utils.logger import logger

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API is running and connected to required services",
    response_model=Dict[str, Union[str, Dict[str, str]]],
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """Enhanced health check that verifies connectivity to external services."""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "services": {},
    }

    # Check OpenAI connectivity
    try:
        client = get_openai_client()
        # Just make a simple request to check connectivity
        await client.models.list()
        health_status["services"]["openai"] = "connected"
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {str(e)}")
        health_status["services"]["openai"] = f"error: {str(e)[:100]}"

    return health_status
