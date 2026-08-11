"""Shared test fixtures.

Settings are constructed explicitly rather than read from the environment so tests are isolated
and independent of execution order.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        secret_key="test-secret-key",
        cors_origins="http://localhost:5173,http://localhost:5174",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
