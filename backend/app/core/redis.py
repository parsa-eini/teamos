"""Redis connection and a thin get/set/delete helper.

This is not a caching framework. Callers choose keys and TTLs explicitly
(`AI_BUILD_SPEC.md` section 27).
"""

from redis import Redis
from starlette.requests import Request


def create_redis(url: str) -> Redis:
    """Return a synchronous Redis client that decodes values as strings."""
    return Redis.from_url(url, decode_responses=True)


class RedisClient:
    """Minimal key/value access used by later caching and rate-limiting code."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    def get(self, key: str) -> str | None:
        value = self._client.get(key)
        if value is None:
            return None
        return str(value)

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is None:
            self._client.set(key, value)
        else:
            self._client.set(key, value, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def close(self) -> None:
        self._client.close()


def get_redis(request: Request) -> RedisClient:
    """FastAPI dependency that returns the process-wide Redis wrapper."""
    return request.app.state.redis
