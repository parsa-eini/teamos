"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.common.error_handlers import register_exception_handlers
from app.core.config import Settings, get_settings
from app.core.database import create_engine_from_settings, create_session_factory
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.redis import RedisClient, create_redis


class HealthResponse(BaseModel):
    """Liveness result for the application process."""

    status: str = Field(examples=["healthy"])


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Passing settings explicitly keeps tests independent of the env."""
    settings = settings or get_settings()

    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.redis.close()
        app.state.engine.dispose()

    app = FastAPI(
        title="Team Management API",
        version="0.1.0",
        summary="Backend API for the team management product.",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.engine = create_engine_from_settings(settings)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.redis = RedisClient(create_redis(settings.redis_url))

    app.add_middleware(RequestLoggingMiddleware)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    @app.get(
        "/health",
        response_model=HealthResponse,
        status_code=200,
        summary="Health check",
        description="Reports that the application process is running and able to serve requests.",
        tags=["operations"],
    )
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    return app
