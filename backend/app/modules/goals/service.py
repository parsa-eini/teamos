"""Goal use cases. Organization id is taken from membership context, never from the client."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.goals import repository as goals_repository
from app.modules.goals.models import Goal
from app.modules.goals.schemas import GoalCreate, GoalRead, GoalUpdate
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole
from app.modules.teams import repository as teams_repository
from app.modules.users import repository as users_repository

_VIEW_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _is_team_member(session: Session, team_id: UUID, user_id: UUID) -> bool:
    return teams_repository.get_membership(session, team_id, user_id) is not None


def _can_view(context: OrganizationContext, session: Session, goal: Goal) -> bool:
    if context.role in _VIEW_ALL_ROLES:
        return True
    if context.role == OrganizationRole.MEMBER:
        return goal.user_id == context.user.id
    if goal.user_id == context.user.id or goal.created_by == context.user.id:
        return True
    if goal.team_id is None and goal.user_id is None:
        return True
    if goal.team_id is not None:
        return _is_team_member(session, goal.team_id, context.user.id)
    return False


def _can_modify(context: OrganizationContext, session: Session, goal: Goal) -> bool:
    if context.role == OrganizationRole.OWNER:
        return True
    if context.role != OrganizationRole.MANAGER:
        return False
    return _can_view(context, session, goal)


def _require_create(context: OrganizationContext) -> None:
    if context.role not in {OrganizationRole.OWNER, OrganizationRole.MANAGER}:
        raise ForbiddenError("You do not have permission to create goals")


def _require_team_assignable(
    context: OrganizationContext,
    session: Session,
    team_id: UUID | None,
) -> None:
    if team_id is None:
        return
    if context.role == OrganizationRole.OWNER:
        return
    if context.role == OrganizationRole.MANAGER and _is_team_member(
        session, team_id, context.user.id
    ):
        return
    raise ForbiddenError("You do not have permission to assign this team")


def _resolve_team(session: Session, organization_id: UUID, team_id: UUID | None) -> None:
    if team_id is None:
        return
    team = teams_repository.get_by_id(session, team_id, organization_id)
    if team is None:
        raise ResourceNotFoundError("Team not found")


def _resolve_user(session: Session, organization_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    user = users_repository.get_by_id(session, user_id)
    membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=organization_id,
        user_id=user_id,
    )
    if user is None or membership is None:
        raise ResourceNotFoundError("User not found in this organization")


def _assert_progress(progress: int) -> None:
    if progress < 0 or progress > 100:
        raise ValidationError("progress must be between 0 and 100")


def _get_goal_or_404(session: Session, goal_id: UUID, organization_id: UUID) -> Goal:
    goal = goals_repository.get_by_id(session, goal_id, organization_id)
    if goal is None:
        raise ResourceNotFoundError("Goal not found")
    return goal


def list_goals(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
) -> tuple[list[GoalRead], PaginationMeta]:
    owner_user_id = context.user.id if context.role == OrganizationRole.MEMBER else None
    manager_user_id = context.user.id if context.role == OrganizationRole.MANAGER else None
    goals, total = goals_repository.list_for_organization(
        session,
        context.organization.id,
        owner_user_id=owner_user_id,
        manager_user_id=manager_user_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [GoalRead.model_validate(goal) for goal in goals], meta


def create_goal(
    session: Session,
    context: OrganizationContext,
    payload: GoalCreate,
    redis: RedisClient,
) -> Goal:
    _require_create(context)
    _resolve_team(session, context.organization.id, payload.team_id)
    _require_team_assignable(context, session, payload.team_id)
    _resolve_user(session, context.organization.id, payload.user_id)
    _assert_progress(payload.progress)

    goal = Goal(
        organization_id=context.organization.id,
        team_id=payload.team_id,
        user_id=payload.user_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        progress=payload.progress,
        start_date=payload.start_date,
        due_date=payload.due_date,
        created_by=context.user.id,
    )
    goals_repository.add(session, goal)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(goal)
    return goal


def get_goal(session: Session, context: OrganizationContext, goal_id: UUID) -> Goal:
    goal = _get_goal_or_404(session, goal_id, context.organization.id)
    if not _can_view(context, session, goal):
        raise ForbiddenError()
    return goal


def update_goal(
    session: Session,
    context: OrganizationContext,
    goal_id: UUID,
    payload: GoalUpdate,
    redis: RedisClient,
) -> Goal:
    goal = _get_goal_or_404(session, goal_id, context.organization.id)
    if not _can_modify(context, session, goal):
        raise ForbiddenError()

    if "team_id" in payload.model_fields_set:
        _resolve_team(session, context.organization.id, payload.team_id)
        _require_team_assignable(context, session, payload.team_id)
        goal.team_id = payload.team_id
    if "user_id" in payload.model_fields_set:
        _resolve_user(session, context.organization.id, payload.user_id)
        goal.user_id = payload.user_id
    if payload.title is not None:
        goal.title = payload.title
    if "description" in payload.model_fields_set:
        goal.description = payload.description
    if payload.status is not None:
        goal.status = payload.status
    if payload.progress is not None:
        _assert_progress(payload.progress)
        goal.progress = payload.progress
    if "start_date" in payload.model_fields_set:
        goal.start_date = payload.start_date
    if "due_date" in payload.model_fields_set:
        goal.due_date = payload.due_date

    session.add(goal)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(goal)
    return goal
