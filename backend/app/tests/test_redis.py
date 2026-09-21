"""Tests for the Redis get/set/delete wrapper and FastAPI dependency."""

from typing import Annotated, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import Settings
from app.core.redis import RedisClient, get_redis
from app.main import create_app
from app.tests.conftest import FakeRedis


def test_get_set_and_delete_round_trip() -> None:
    client = RedisClient(cast(Redis, FakeRedis()))

    assert client.get("missing") is None
    client.set("dashboard:org-1", "summary")
    assert client.get("dashboard:org-1") == "summary"
    client.delete("dashboard:org-1")
    assert client.get("dashboard:org-1") is None


def test_set_stores_explicit_ttl() -> None:
    fake = FakeRedis()
    client = RedisClient(cast(Redis, fake))

    client.set("dashboard:org-1", "summary", ttl_seconds=30)

    assert fake.ttls["dashboard:org-1"] == 30


def test_get_redis_dependency_returns_the_app_client(settings: Settings) -> None:
    app = create_app(settings)
    fake = FakeRedis()
    app.state.redis = RedisClient(cast(Redis, fake))

    @app.get("/_cache")
    def read_cache(
        redis_client: Annotated[RedisClient, Depends(get_redis)],
    ) -> dict[str, str | None]:
        redis_client.set("k", "v")
        return {"value": redis_client.get("k")}

    with TestClient(app) as client:
        response = client.get("/_cache")

    assert response.status_code == 200
    assert response.json() == {"value": "v"}
    assert fake.store["k"] == "v"
