import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from fastapi.middleware.cors import CORSMiddleware

from app.components.config import Config
from app.utils.logger import logger


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Client: {request.client.host}"
        )

        return response


def init_middleware(app):
    """
    Attach CORS, request logging, and rate limiting middleware to the app.
    """
    logger.info("Initializing middleware stack")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
