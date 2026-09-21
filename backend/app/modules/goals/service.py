"""Goal use cases. Organization id is taken from membership context, never from the client."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.goals import repository as goals_repository
from app.modules.goals.models import Goal
from app.modules.goals.progress import (
    recalculate_goal_progress,
    task_counts,
    task_counts_for_goals,
)
from app.modules.goals.schemas import GoalCreate, GoalRead, GoalUpdate
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole
from app.modules.tasks import repository as tasks_repository
from app.modules.teams import repository as teams_repository
from app.modules.users import repository as users_repository

_VIEW_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _is_team_member(session: Session, team_id: UUID, user_id: UUID) -> bool:
    return teams_repository.get_membership(session, team_id, user_id) is not None


def _can_view(context: OrganizationContext, session: Session, goal: Goal) -> bool:
    if context.role in _VIEW_ALL_ROLES:
        return True
    owner_ids = goals_repository.owner_ids_for_goal(session, goal.id)
    if context.role == OrganizationRole.MEMBER:
        return context.user.id in owner_ids
    if context.user.id in owner_ids or goal.created_by == context.user.id:
        return True
    team_ids = goals_repository.team_ids_for_goal(session, goal.id)
    if not team_ids and not owner_ids:
        return True
    return any(_is_team_member(session, team_id, context.user.id) for team_id in team_ids)


def _can_modify(context: OrganizationContext, session: Session, goal: Goal) -> bool:
    if context.role == OrganizationRole.OWNER:
        return True
    if context.role != OrganizationRole.MANAGER:
        return False
    return _can_view(context, session, goal)


def _require_create(context: OrganizationContext) -> None:
    if context.role not in {OrganizationRole.OWNER, OrganizationRole.MANAGER}:
        raise ForbiddenError("You do not have permission to create goals")


def _require_teams_assignable(
    context: OrganizationContext,
    session: Session,
    team_ids: Sequence[UUID],
) -> None:
    if context.role == OrganizationRole.OWNER:
        return
    for team_id in team_ids:
        if context.role == OrganizationRole.MANAGER and _is_team_member(
            session, team_id, context.user.id
        ):
            continue
        raise ForbiddenError("You do not have permission to assign this team")


def _require_teams_exist(session: Session, organization_id: UUID, team_ids: Sequence[UUID]) -> None:
    for team_id in team_ids:
        if teams_repository.get_by_id(session, team_id, organization_id) is None:
            raise ResourceNotFoundError("Team not found")


def _require_owners_in_organization(
    session: Session,
    organization_id: UUID,
    user_ids: Sequence[UUID],
) -> None:
    for user_id in user_ids:
        user = users_repository.get_by_id(session, user_id)
        membership = organizations_repository.get_membership_in_organization(
            session,
            organization_id=organization_id,
            user_id=user_id,
        )
        if user is None or membership is None:
            raise ResourceNotFoundError("User not found in this organization")


def _require_tasks_in_organization(
    session: Session,
    organization_id: UUID,
    task_ids: Sequence[UUID],
) -> None:
    for task_id in task_ids:
        if tasks_repository.get_by_id(session, task_id, organization_id) is None:
            raise ResourceNotFoundError("Task not found")


def _assert_progress(progress: int) -> None:
    if progress < 0 or progress > 100:
        raise ValidationError("progress must be between 0 and 100")


def _get_goal_or_404(session: Session, goal_id: UUID, organization_id: UUID) -> Goal:
    goal = goals_repository.get_by_id(session, goal_id, organization_id)
    if goal is None:
        raise ResourceNotFoundError("Goal not found")
    return goal


def _read(
    goal: Goal,
    *,
    team_ids: list[UUID],
    owner_ids: list[UUID],
    task_ids: list[UUID],
    progress_is_derived: bool,
) -> GoalRead:
    return GoalRead(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        team_ids=team_ids,
        owner_ids=owner_ids,
        task_ids=task_ids,
        status=goal.status,
        progress=goal.progress,
        progress_is_derived=progress_is_derived,
        start_date=goal.start_date,
        due_date=goal.due_date,
        created_by=goal.created_by,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _to_read(session: Session, goal: Goal) -> GoalRead:
    return _read(
        goal,
        team_ids=goals_repository.team_ids_for_goal(session, goal.id),
        owner_ids=goals_repository.owner_ids_for_goal(session, goal.id),
        task_ids=goals_repository.task_ids_for_goal(session, goal.id),
        progress_is_derived=_derives_progress(session, goal.id),
    )


def _derives_progress(session: Session, goal_id: UUID) -> bool:
    """A goal derives progress once it has at least one linked task that is not cancelled."""
    _, countable = task_counts(session, goal_id)
    return countable > 0


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
    goal_ids = [goal.id for goal in goals]
    teams, owners, tasks = goals_repository.links_for_goals(session, goal_ids)
    counts = task_counts_for_goals(session, goal_ids)
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    reads = [
        _read(
            goal,
            team_ids=teams.get(goal.id, []),
            owner_ids=owners.get(goal.id, []),
            task_ids=tasks.get(goal.id, []),
            progress_is_derived=counts[goal.id][1] > 0,
        )
        for goal in goals
    ]
    return reads, meta


def create_goal(
    session: Session,
    context: OrganizationContext,
    payload: GoalCreate,
    redis: RedisClient,
) -> GoalRead:
    _require_create(context)
    _require_teams_exist(session, context.organization.id, payload.team_ids)
    _require_teams_assignable(context, session, payload.team_ids)
    _require_owners_in_organization(session, context.organization.id, payload.owner_ids)
    _require_tasks_in_organization(session, context.organization.id, payload.task_ids)
    _assert_progress(payload.progress)
    if payload.task_ids and payload.progress:
        raise ValidationError("progress is derived from linked tasks and cannot be set directly")

    goal = Goal(
        organization_id=context.organization.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        progress=payload.progress,
        start_date=payload.start_date,
        due_date=payload.due_date,
        created_by=context.user.id,
    )
    goals_repository.add(session, goal)
    session.flush()
    goals_repository.set_teams(session, goal.id, payload.team_ids)
    goals_repository.set_owners(session, goal.id, payload.owner_ids)
    goals_repository.set_tasks(session, goal.id, payload.task_ids)
    session.flush()
    # Linked tasks take over from the submitted progress value.
    recalculate_goal_progress(session, goal)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(goal)
    return _to_read(session, goal)


def get_goal(session: Session, context: OrganizationContext, goal_id: UUID) -> GoalRead:
    goal = _get_goal_or_404(session, goal_id, context.organization.id)
    if not _can_view(context, session, goal):
        raise ForbiddenError()
    return _to_read(session, goal)


def update_goal(
    session: Session,
    context: OrganizationContext,
    goal_id: UUID,
    payload: GoalUpdate,
    redis: RedisClient,
) -> GoalRead:
    goal = _get_goal_or_404(session, goal_id, context.organization.id)
    if not _can_modify(context, session, goal):
        raise ForbiddenError()

    fields = payload.model_fields_set

    if "team_ids" in fields:
        if payload.team_ids is None:
            raise ValidationError("team_ids is required")
        _require_teams_exist(session, context.organization.id, payload.team_ids)
        _require_teams_assignable(context, session, payload.team_ids)
        goals_repository.set_teams(session, goal.id, payload.team_ids)
    if "owner_ids" in fields:
        if payload.owner_ids is None:
            raise ValidationError("owner_ids is required")
        _require_owners_in_organization(session, context.organization.id, payload.owner_ids)
        goals_repository.set_owners(session, goal.id, payload.owner_ids)
    if "task_ids" in fields:
        if payload.task_ids is None:
            raise ValidationError("task_ids is required")
        _require_tasks_in_organization(session, context.organization.id, payload.task_ids)
        goals_repository.set_tasks(session, goal.id, payload.task_ids)
        session.flush()
    if payload.title is not None:
        goal.title = payload.title
    if "description" in fields:
        goal.description = payload.description
    if payload.status is not None:
        goal.status = payload.status
    if payload.progress is not None:
        _assert_progress(payload.progress)
        if _derives_progress(session, goal.id):
            raise ValidationError(
                "progress is derived from linked tasks and cannot be set directly"
            )
        goal.progress = payload.progress
    if "start_date" in fields:
        goal.start_date = payload.start_date
    if "due_date" in fields:
        goal.due_date = payload.due_date

    session.add(goal)
    recalculate_goal_progress(session, goal)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(goal)
    return _to_read(session, goal)
