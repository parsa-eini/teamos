"""Dashboard cache keys. Spec section 27: `dashboard:{organization_id}` with an explicit TTL."""

from uuid import UUID

from app.core.redis import RedisClient

DASHBOARD_CACHE_TTL_SECONDS = 60


def dashboard_cache_key(organization_id: UUID) -> str:
    return f"dashboard:{organization_id}"


def invalidate_dashboard(redis: RedisClient, organization_id: UUID) -> None:
    redis.delete(dashboard_cache_key(organization_id))
