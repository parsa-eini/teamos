"""Persistence helpers for tasks. Every query is scoped to an organization."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from app.modules.projects.models import Project
from app.modules.tasks.models import Task, TaskAssignee, TaskPriority, TaskStatus
from app.modules.teams.models import TeamMembership


def get_by_id(session: Session, task_id: UUID, organization_id: UUID) -> Task | None:
    return session.scalar(
        select(Task).where(Task.id == task_id, Task.organization_id == organization_id)
    )


def _tasks_assigned_to(user_id: UUID) -> Select[Any]:
    return select(TaskAssignee.task_id).where(TaskAssignee.user_id == user_id)


def assignee_ids_for_task(session: Session, task_id: UUID) -> list[UUID]:
    """Assignees of one task.

    Assignees are a set, so they are ordered by user id to keep responses stable across
    requests. Insertion order is not usable here because rows written in the same transaction
    share a `created_at`.
    """
    return list(
        session.scalars(
            select(TaskAssignee.user_id)
            .where(TaskAssignee.task_id == task_id)
            .order_by(TaskAssignee.user_id)
        ).all()
    )


def assignee_ids_for_tasks(session: Session, task_ids: Sequence[UUID]) -> dict[UUID, list[UUID]]:
    """Load assignees for many tasks at once so list endpoints avoid a query per row."""
    if not task_ids:
        return {}
    rows = session.execute(
        select(TaskAssignee.task_id, TaskAssignee.user_id)
        .where(TaskAssignee.task_id.in_(task_ids))
        .order_by(TaskAssignee.user_id)
    ).all()
    grouped: dict[UUID, list[UUID]] = {task_id: [] for task_id in task_ids}
    for task_id, user_id in rows:
        grouped[task_id].append(user_id)
    return grouped


def set_assignees(session: Session, task_id: UUID, user_ids: Sequence[UUID]) -> None:
    """Replace the assignee set, leaving already-assigned rows untouched."""
    current = set(assignee_ids_for_task(session, task_id))
    wanted = list(dict.fromkeys(user_ids))
    removed = current - set(wanted)
    if removed:
        session.execute(
            sql_delete(TaskAssignee).where(
                TaskAssignee.task_id == task_id,
                TaskAssignee.user_id.in_(removed),
            )
        )
    for user_id in wanted:
        if user_id not in current:
            session.add(TaskAssignee(task_id=task_id, user_id=user_id))


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
        filters.append(Task.id.in_(_tasks_assigned_to(assigned_to_user_id)))
    if status is not None:
        filters.append(Task.status == status)
    if priority is not None:
        filters.append(Task.priority == priority)
    if assignee_id is not None:
        filters.append(Task.id.in_(_tasks_assigned_to(assignee_id)))
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
