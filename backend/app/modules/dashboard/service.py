"""Dashboard use cases. Organization id comes from membership, never from the client."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError
from app.core.redis import RedisClient
from app.modules.dashboard import repository as dashboard_repository
from app.modules.dashboard.cache import (
    DASHBOARD_CACHE_TTL_SECONDS,
    dashboard_cache_key,
)
from app.modules.dashboard.schemas import DashboardRead, GoalSummary
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole

_DASHBOARD_ROLES = {
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MANAGER,
}


def _require_dashboard(context: OrganizationContext) -> None:
    if context.role not in _DASHBOARD_ROLES:
        raise ForbiddenError("You do not have permission to view the dashboard")


def _compute_dashboard(session: Session, organization_id: UUID) -> DashboardRead:
    total_goals, goal_items = dashboard_repository.goal_summary(session, organization_id)
    return DashboardRead(
        member_count=dashboard_repository.count_members(session, organization_id),
        active_projects=dashboard_repository.count_active_projects(session, organization_id),
        open_tasks=dashboard_repository.count_open_tasks(session, organization_id),
        overdue_tasks=dashboard_repository.count_overdue_tasks(
            session,
            organization_id,
            dashboard_repository.utc_today(),
        ),
        goal_summary=GoalSummary(total=total_goals, items=goal_items),
        recent_checkins=dashboard_repository.recent_checkins(session, organization_id),
        recent_activity=dashboard_repository.recent_activity(session, organization_id),
    )


def get_dashboard(
    session: Session,
    context: OrganizationContext,
    redis: RedisClient,
) -> DashboardRead:
    _require_dashboard(context)
    organization_id = context.organization.id
    cache_key = dashboard_cache_key(organization_id)
    cached = redis.get(cache_key)
    if cached is not None:
        return DashboardRead.model_validate_json(cached)

    dashboard = _compute_dashboard(session, organization_id)
    redis.set(cache_key, dashboard.model_dump_json(), ttl_seconds=DASHBOARD_CACHE_TTL_SECONDS)
    return dashboard
