"""Persistence helpers for teams. Every query is scoped to an organization."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.teams.models import Team, TeamMembership
from app.modules.users.models import User


def get_by_id(session: Session, team_id: UUID, organization_id: UUID) -> Team | None:
    return session.scalar(
        select(Team).where(Team.id == team_id, Team.organization_id == organization_id)
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    member_user_id: UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[Team], int]:
    filters = [Team.organization_id == organization_id]
    stmt = select(Team).where(*filters)
    count_stmt = select(func.count()).select_from(Team).where(*filters)

    if member_user_id is not None:
        member_filter = TeamMembership.user_id == member_user_id
        stmt = stmt.join(TeamMembership, TeamMembership.team_id == Team.id).where(member_filter)
        count_stmt = (
            select(func.count())
            .select_from(Team)
            .join(TeamMembership, TeamMembership.team_id == Team.id)
            .where(*filters, member_filter)
        )

    total = session.scalar(count_stmt) or 0
    teams = list(
        session.scalars(
            stmt.order_by(Team.created_at.desc(), Team.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return teams, total


def add(session: Session, team: Team) -> Team:
    session.add(team)
    return team


def delete(session: Session, team: Team) -> None:
    session.delete(team)


def get_membership(session: Session, team_id: UUID, user_id: UUID) -> TeamMembership | None:
    return session.scalar(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id,
        )
    )


def list_members(
    session: Session,
    team_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[TeamMembership, User]], int]:
    stmt = (
        select(TeamMembership, User)
        .join(User, User.id == TeamMembership.user_id)
        .where(TeamMembership.team_id == team_id)
    )
    total = (
        session.scalar(
            select(func.count())
            .select_from(TeamMembership)
            .where(TeamMembership.team_id == team_id)
        )
        or 0
    )
    rows = list(
        session.execute(
            stmt.order_by(TeamMembership.created_at.asc(), TeamMembership.id.asc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [(row[0], row[1]) for row in rows], total


def add_membership(session: Session, membership: TeamMembership) -> TeamMembership:
    session.add(membership)
    return membership


def delete_membership(session: Session, membership: TeamMembership) -> None:
    session.delete(membership)
