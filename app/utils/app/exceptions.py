import time
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.utils.logger import logger
from app.schemas.types import ErrorResponse


def register_exception_handlers(app):

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                details=exc.detail,
                status_code=exc.status_code,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                details=f"An unexpected error occurred: {str(exc)}",
                status_code=500,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            ).model_dump(),
        )
