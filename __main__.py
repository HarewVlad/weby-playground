import uvicorn
from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.project_name import router as project_router
from app.api.v1.prompt_enhance import router as prompt_router
from app.api.v1.weby import router as weby_router

from app.api.v1.studio import router as studio_router

from app.components.config import Config
from app.utils.app.exceptions import register_exception_handlers
from app.utils.logger import logger
from app.utils.app.middleware import init_middleware

app = FastAPI(
    title="Weby API",
    description="Production-ready API for Weby code generation service",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Weby Support",
        "email": "support@weby.example.com",
    },
)

init_middleware(app=app)
register_exception_handlers(app)

app.include_router(prompt_router)
app.include_router(chat_router)
app.include_router(weby_router)
app.include_router(project_router)
app.include_router(health_router)
app.include_router(studio_router)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting Weby API Server")
    logger.info("Version: 1.0.0")
    logger.info(f"Environment: {'Production' if not Config.DEBUG else 'Development'}")
    logger.info("=" * 50)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG,
        log_level="info",
    )
