from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import check_database_connection, close_database_connections
from app.routers import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)

    await check_database_connection()
    await app.state.redis.ping()

    try:
        yield
    finally:
        await app.state.redis.aclose()
        await close_database_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doxa CRM API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health() -> JSONResponse:
        checks: dict[str, Any] = {"api": "ok", "database": "ok", "redis": "ok"}
        http_status = status.HTTP_200_OK

        try:
            await check_database_connection()
        except Exception as exc:
            checks["database"] = {"status": "error", "detail": exc.__class__.__name__}
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        try:
            await app.state.redis.ping()
        except Exception as exc:
            checks["redis"] = {"status": "error", "detail": exc.__class__.__name__}
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=http_status,
            content={
                "status": "ok" if http_status == status.HTTP_200_OK else "degraded",
                "environment": settings.environment,
                "checks": checks,
            },
        )

    return app


app = create_app()
