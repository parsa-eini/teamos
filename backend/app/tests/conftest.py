"""Shared test fixtures.

Settings are constructed explicitly rather than read from the environment so tests are isolated
and independent of execution order. The in-memory SQLite schema is created per app instance.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app
from app.modules.organizations.models import Organization as Organization  # noqa: F401
from app.modules.users.models import User as User  # noqa: F401


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        secret_key="test-secret-key-that-is-at-least-32b",
        cors_origins="http://localhost:5173,http://localhost:5174",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
