"""Persistence helpers for tasks. Every query is scoped to an organization."""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.projects.models import Project
from app.modules.tasks.models import Task, TaskPriority, TaskStatus
from app.modules.teams.models import TeamMembership


def get_by_id(session: Session, task_id: UUID, organization_id: UUID) -> Task | None:
    return session.scalar(
        select(Task).where(Task.id == task_id, Task.organization_id == organization_id)
    )


def _apply_project_visibility(
    stmt: Select[Any],
    *,
    manager_user_id: UUID,
    include_unassigned_projects: bool,
) -> Select[Any]:
    assigned_teams = select(TeamMembership.team_id).where(TeamMembership.user_id == manager_user_id)
    if include_unassigned_projects:
        visibility = or_(Project.team_id.is_(None), Project.team_id.in_(assigned_teams))
    else:
        visibility = Project.team_id.in_(assigned_teams)
    return stmt.join(Project, Project.id == Task.project_id).where(visibility)


def list_for_organization(
    session: Session,
    organization_id: UUID,
    *,
    assigned_to_user_id: UUID | None,
    manager_user_id: UUID | None,
    include_unassigned_projects: bool,
    status: TaskStatus | None,
    priority: TaskPriority | None,
    assignee_id: UUID | None,
    project_id: UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[Task], int]:
    filters = [Task.organization_id == organization_id]
    if assigned_to_user_id is not None:
        filters.append(Task.assignee_id == assigned_to_user_id)
    if status is not None:
        filters.append(Task.status == status)
    if priority is not None:
        filters.append(Task.priority == priority)
    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)
    if project_id is not None:
        filters.append(Task.project_id == project_id)

    stmt = select(Task).where(*filters)
    count_stmt = select(func.count()).select_from(Task).where(*filters)

    if manager_user_id is not None:
        stmt = _apply_project_visibility(
            stmt,
            manager_user_id=manager_user_id,
            include_unassigned_projects=include_unassigned_projects,
        )
        count_stmt = _apply_project_visibility(
            count_stmt,
            manager_user_id=manager_user_id,
            include_unassigned_projects=include_unassigned_projects,
        )

    total = session.scalar(count_stmt) or 0
    tasks = list(
        session.scalars(
            stmt.order_by(Task.created_at.desc(), Task.id.desc()).offset(offset).limit(limit)
        ).all()
    )
    return tasks, total


def add(session: Session, task: Task) -> Task:
    session.add(task)
    return task


def delete(session: Session, task: Task) -> None:
    session.delete(task)
