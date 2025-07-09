import time

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from fastapi.middleware.cors import CORSMiddleware

from app.components.config import Config
from app.utils.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit_per_minute: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit_per_minute
        self.requests = {}

    async def dispatch(self, request: StarletteRequest, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Clean up old entries
        self.requests = {
            ip: times
            for ip, times in self.requests.items()
            if any(t > current_time - 60 for t in times)
        }

        # Get or create request times for this IP
        request_times = self.requests.get(client_ip, [])

        # Filter to requests in the last minute
        request_times = [t for t in request_times if t > current_time - 60]

        # Check if rate limit exceeded
        if len(request_times) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded. Please try again later."},
            )

        # Add this request
        request_times.append(current_time)
        self.requests[client_ip] = request_times

        # Process the request
        return await call_next(request)


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

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
