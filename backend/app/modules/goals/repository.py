"""Persistence helpers for goals. Every query is scoped to an organization."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, not_, or_, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from app.modules.goals.models import Goal, GoalOwner, GoalTask, GoalTeam
from app.modules.teams.models import TeamMembership


def get_by_id(session: Session, goal_id: UUID, organization_id: UUID) -> Goal | None:
    return session.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.organization_id == organization_id)
    )


def _goals_owned_by(user_id: UUID) -> Select[Any]:
    return select(GoalOwner.goal_id).where(GoalOwner.user_id == user_id)


def _goals_for_teams_of(user_id: UUID) -> Select[Any]:
    assigned_teams = select(TeamMembership.team_id).where(TeamMembership.user_id == user_id)
    return select(GoalTeam.goal_id).where(GoalTeam.team_id.in_(assigned_teams))


def _organization_wide_goals() -> Any:
    """Goals with neither a team nor an owner are visible to everyone who can see goals."""
    return and_(
        not_(Goal.id.in_(select(GoalTeam.goal_id))),
        not_(Goal.id.in_(select(GoalOwner.goal_id))),
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    owner_user_id: UUID | None,
    manager_user_id: UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[Goal], int]:
    filters = [Goal.organization_id == organization_id]
    if owner_user_id is not None:
        filters.append(Goal.id.in_(_goals_owned_by(owner_user_id)))

    stmt = select(Goal).where(*filters)
    count_stmt = select(func.count()).select_from(Goal).where(*filters)

    if manager_user_id is not None:
        visibility = or_(
            _organization_wide_goals(),
            Goal.id.in_(_goals_for_teams_of(manager_user_id)),
            Goal.id.in_(_goals_owned_by(manager_user_id)),
            Goal.created_by == manager_user_id,
        )
        stmt = stmt.where(visibility)
        count_stmt = count_stmt.where(visibility)

    total = session.scalar(count_stmt) or 0
    goals = list(
        session.scalars(
            stmt.order_by(Goal.created_at.desc(), Goal.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return goals, total


def add(session: Session, goal: Goal) -> Goal:
    session.add(goal)
    return goal


def team_ids_for_goal(session: Session, goal_id: UUID) -> list[UUID]:
    return _linked_ids(session, GoalTeam, GoalTeam.team_id, goal_id)


def owner_ids_for_goal(session: Session, goal_id: UUID) -> list[UUID]:
    return _linked_ids(session, GoalOwner, GoalOwner.user_id, goal_id)


def task_ids_for_goal(session: Session, goal_id: UUID) -> list[UUID]:
    return _linked_ids(session, GoalTask, GoalTask.task_id, goal_id)


def _linked_ids(session: Session, model: Any, column: Any, goal_id: UUID) -> list[UUID]:
    """Linked ids for one goal, ordered by id so responses are stable across requests."""
    return list(
        session.scalars(select(column).where(model.goal_id == goal_id).order_by(column)).all()
    )


def links_for_goals(
    session: Session,
    goal_ids: Sequence[UUID],
) -> tuple[dict[UUID, list[UUID]], dict[UUID, list[UUID]], dict[UUID, list[UUID]]]:
    """Load teams, owners, and tasks for many goals so list endpoints avoid a query per row."""
    if not goal_ids:
        return {}, {}, {}
    return (
        _grouped_links(session, GoalTeam, GoalTeam.team_id, goal_ids),
        _grouped_links(session, GoalOwner, GoalOwner.user_id, goal_ids),
        _grouped_links(session, GoalTask, GoalTask.task_id, goal_ids),
    )


def _grouped_links(
    session: Session,
    model: Any,
    column: Any,
    goal_ids: Sequence[UUID],
) -> dict[UUID, list[UUID]]:
    rows = session.execute(
        select(model.goal_id, column).where(model.goal_id.in_(goal_ids)).order_by(column)
    ).all()
    grouped: dict[UUID, list[UUID]] = {goal_id: [] for goal_id in goal_ids}
    for goal_id, target_id in rows:
        grouped[goal_id].append(target_id)
    return grouped


def set_teams(session: Session, goal_id: UUID, team_ids: Sequence[UUID]) -> None:
    _replace_links(session, GoalTeam, GoalTeam.team_id, goal_id, team_ids, "team_id")


def set_owners(session: Session, goal_id: UUID, user_ids: Sequence[UUID]) -> None:
    _replace_links(session, GoalOwner, GoalOwner.user_id, goal_id, user_ids, "user_id")


def set_tasks(session: Session, goal_id: UUID, task_ids: Sequence[UUID]) -> None:
    _replace_links(session, GoalTask, GoalTask.task_id, goal_id, task_ids, "task_id")


def _replace_links(
    session: Session,
    model: Any,
    column: Any,
    goal_id: UUID,
    target_ids: Sequence[UUID],
    field: str,
) -> None:
    """Replace a link set, leaving existing rows in place."""
    current = set(_linked_ids(session, model, column, goal_id))
    wanted = list(dict.fromkeys(target_ids))
    removed = current - set(wanted)
    if removed:
        session.execute(sql_delete(model).where(model.goal_id == goal_id, column.in_(removed)))
    for target_id in wanted:
        if target_id not in current:
            session.add(model(goal_id=goal_id, **{field: target_id}))


def goal_ids_linked_to_task(session: Session, task_id: UUID) -> list[UUID]:
    return list(session.scalars(select(GoalTask.goal_id).where(GoalTask.task_id == task_id)).all())
