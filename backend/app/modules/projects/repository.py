"""Persistence helpers for projects. Every query is scoped to an organization."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.projects.models import Project, ProjectStatus
from app.modules.teams.models import TeamMembership


def get_by_id(session: Session, project_id: UUID, organization_id: UUID) -> Project | None:
    return session.scalar(
        select(Project).where(Project.id == project_id, Project.organization_id == organization_id)
    )


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    member_user_id: UUID | None,
    include_unassigned: bool,
    status: ProjectStatus | None,
    offset: int,
    limit: int,
) -> tuple[list[Project], int]:
    filters = [Project.organization_id == organization_id]
    if status is not None:
        filters.append(Project.status == status)

    stmt = select(Project).where(*filters)
    count_stmt = select(func.count()).select_from(Project).where(*filters)

    if member_user_id is not None:
        assigned_teams = select(TeamMembership.team_id).where(
            TeamMembership.user_id == member_user_id
        )
        if include_unassigned:
            visibility = or_(Project.team_id.is_(None), Project.team_id.in_(assigned_teams))
        else:
            visibility = Project.team_id.in_(assigned_teams)
        stmt = stmt.where(visibility)
        count_stmt = count_stmt.where(visibility)

    total = session.scalar(count_stmt) or 0
    projects = list(
        session.scalars(
            stmt.order_by(Project.created_at.desc(), Project.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return projects, total


def add(session: Session, project: Project) -> Project:
    session.add(project)
    return project


def delete(session: Session, project: Project) -> None:
    session.delete(project)
