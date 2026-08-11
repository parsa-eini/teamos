"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging


class HealthResponse(BaseModel):
    """Liveness result for the application process."""

    status: str = Field(examples=["healthy"])


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Passing settings explicitly keeps tests independent of the env."""
    settings = settings or get_settings()

    configure_logging()

    app = FastAPI(
        title="Team Management API",
        version="0.1.0",
        summary="Backend API for the team management product.",
    )

    app.add_middleware(RequestLoggingMiddleware)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
