from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from apps.kb_service.api import ingest_router, batch_router, review_router, callback_router, query_router, monitor_router, datasets_router
from apps.kb_service.core.exceptions import register_exceptions
from apps.kb_service.core.queue import QueueManager


# 初始化队列管理器
queue_manager = QueueManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的初始化逻辑
    yield
    # 应用关闭时的清理逻辑


def create_kb_app() -> FastAPI:
    _app = FastAPI(
        title="kb_service",
        description="RAG Knowledge Base Ingest Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exceptions(_app)

    _app.include_router(ingest_router, tags=["ingest"])
    _app.include_router(batch_router, tags=["batch"])
    _app.include_router(review_router, tags=["review"])
    _app.include_router(callback_router, tags=["callback"])
    _app.include_router(query_router, tags=["query"])
    _app.include_router(datasets_router, tags=["datasets"])
    _app.include_router(monitor_router, tags=["monitor"], prefix="/monitor")

    @_app.get("/health", tags=["health"])
    async def health():
        return JSONResponse({"status": "healthy"})

    return _app