from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from apps.rbac.api import rbac_router
from apps.rbac.core.exceptions import SettingNotFound, register_exceptions
from apps.rbac.core.init_app import init_data
from apps.rbac.core.middlewares import make_middlewares

try:
    from config.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()
    yield
    await Tortoise.close_connections()


def create_rbac_app() -> FastAPI:
    _app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(_app)
    _app.include_router(rbac_router, prefix="/api/v1")
    return _app


app = create_rbac_app()
