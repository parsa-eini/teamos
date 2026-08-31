"""Shared test fixtures.

Settings are constructed explicitly rather than read from the environment so tests are isolated
and independent of execution order. The in-memory SQLite schema is created per app instance.

Redis is replaced with an in-memory stand-in so dashboard cache tests do not need a live server.
"""

from collections.abc import Iterator
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import Settings
from app.core.database import Base
from app.core.redis import RedisClient
from app.main import create_app
from app.modules.checkins.models import CheckIn as CheckIn  # noqa: F401
from app.modules.goals.models import Goal as Goal  # noqa: F401
from app.modules.organizations.models import Organization as Organization  # noqa: F401
from app.modules.projects.models import Project as Project  # noqa: F401
from app.modules.tasks.models import Task as Task  # noqa: F401
from app.modules.teams.models import Team as Team  # noqa: F401
from app.modules.users.models import User as User  # noqa: F401


class FakeRedis:
    """In-memory stand-in for redis.Redis, covering the commands we actually call."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.closed = False

    def get(self, name: str) -> str | None:
        return self.store.get(name)

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self.store[name] = value
        if ex is None:
            self.ttls.pop(name, None)
        else:
            self.ttls[name] = ex
        return True

    def delete(self, name: str) -> int:
        if name not in self.store:
            return 0
        del self.store[name]
        self.ttls.pop(name, None)
        return 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        secret_key="test-secret-key-that-is-at-least-32b",
        cors_origins="http://localhost:5173,http://localhost:5174",
    )


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def app(settings: Settings, fake_redis: FakeRedis) -> FastAPI:
    application = create_app(settings)
    application.state.redis.close()
    application.state.redis = RedisClient(cast(Redis, fake_redis))
    Base.metadata.create_all(application.state.engine)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
