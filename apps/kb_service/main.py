from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.kb_service.api import ingest_router, batch_router, review_router, callback_router, query_router
from apps.kb_service.core.exceptions import register_exceptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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

    return _app