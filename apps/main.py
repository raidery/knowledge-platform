from pathlib import Path
from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from tortoise import Tortoise

from apps.rbac.api import rbac_router
from apps.rbac.core.exceptions import SettingNotFound, register_exceptions
from apps.rbac.core.init_app import init_data
# TODO: 恢复 make_middlewares 以启用 audit log 等中间件功能
# from apps.rbac.core.middlewares import make_middlewares

try:
    from config.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")

from apps.kb_service.main import create_kb_app as create_kb_service_app

# 配置loguru
logger.remove()
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)
logger.add(
    "logs/error.log",
    rotation="500 MB",
    retention="30 days",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)
logger.info("Starting application initialization")

root = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application data")
    await init_data()
    logger.info("Application data initialization completed")
    yield
    logger.info("Closing database connections")
    await Tortoise.close_connections()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.VERSION,
    openapi_url="/openapi.json",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# 最大跨域权限
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Registering exception handlers")
register_exceptions(app)

logger.info("Including RBAC router")
app.include_router(rbac_router, prefix="/api/v1")

logger.info("Creating and mounting KB service app")
kb_app = create_kb_service_app()
app.mount("/api/v1/kb", kb_app)

# Mount static files for Swagger UI
static_dir = root / "static"
logger.info(f"Mounting static files from {static_dir}")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    logger.info("Swagger UI documentation accessed")
    openapi_url = app.openapi_url or "/openapi.json"
    oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url or "/docs/oauth2-redirect"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=oauth2_redirect_url,
        swagger_js_url='/static/swagger-ui-bundle.js',
        swagger_css_url="/static/swagger-ui.css"
    )


@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect():
    logger.info("Swagger UI OAuth2 redirect accessed")
    return get_swagger_ui_oauth2_redirect_html()


logger.info("Application initialization completed")
