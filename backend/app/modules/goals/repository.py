"""Persistence helpers for goals. Every query is scoped to an organization."""

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.goals.models import Goal
from app.modules.teams.models import TeamMembership


def get_by_id(session: Session, goal_id: UUID, organization_id: UUID) -> Goal | None:
    return session.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.organization_id == organization_id)
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
        filters.append(Goal.user_id == owner_user_id)

    stmt = select(Goal).where(*filters)
    count_stmt = select(func.count()).select_from(Goal).where(*filters)

    if manager_user_id is not None:
        assigned_teams = select(TeamMembership.team_id).where(
            TeamMembership.user_id == manager_user_id
        )
        visibility = or_(
            and_(Goal.team_id.is_(None), Goal.user_id.is_(None)),
            Goal.team_id.in_(assigned_teams),
            Goal.user_id == manager_user_id,
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
