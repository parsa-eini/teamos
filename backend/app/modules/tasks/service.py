"""Task use cases. Organization id is taken from membership context, never from the client."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.organizations import repository as organizations_repository
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole
from app.modules.projects import repository as projects_repository
from app.modules.projects.models import Project
from app.modules.projects.service import can_manage_project, can_view_project
from app.modules.tasks import repository as tasks_repository
from app.modules.tasks.models import Task, TaskPriority, TaskStatus
from app.modules.tasks.schemas import TaskCreate, TaskRead, TaskUpdate
from app.modules.users import repository as users_repository

_MANAGE_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _get_project_or_404(session: Session, project_id: UUID, organization_id: UUID) -> Project:
    project = projects_repository.get_by_id(session, project_id, organization_id)
    if project is None:
        raise ResourceNotFoundError("Project not found")
    return project


def _get_task_or_404(session: Session, task_id: UUID, organization_id: UUID) -> Task:
    task = tasks_repository.get_by_id(session, task_id, organization_id)
    if task is None:
        raise ResourceNotFoundError("Task not found")
    return task


def _resolve_assignee(session: Session, organization_id: UUID, assignee_id: UUID | None) -> None:
    if assignee_id is None:
        return
    user = users_repository.get_by_id(session, assignee_id)
    membership = organizations_repository.get_membership_in_organization(
        session,
        organization_id=organization_id,
        user_id=assignee_id,
    )
    if user is None or membership is None:
        raise ResourceNotFoundError("User not found in this organization")


def _require_manage_project(
    context: OrganizationContext, session: Session, project: Project
) -> None:
    if not can_manage_project(context, session, project):
        raise ForbiddenError()


def _can_view_task(context: OrganizationContext, session: Session, task: Task) -> bool:
    if context.role == OrganizationRole.MEMBER:
        return task.assignee_id == context.user.id
    project = _get_project_or_404(session, task.project_id, context.organization.id)
    return can_view_project(context, session, project)


def _can_manage_task(context: OrganizationContext, session: Session, task: Task) -> bool:
    if context.role == OrganizationRole.MEMBER:
        return False
    project = _get_project_or_404(session, task.project_id, context.organization.id)
    return can_manage_project(context, session, project)


def _is_own_task(context: OrganizationContext, task: Task) -> bool:
    return task.assignee_id == context.user.id


def _member_update_forbidden(payload: TaskUpdate) -> bool:
    return "project_id" in payload.model_fields_set or "assignee_id" in payload.model_fields_set


def list_tasks(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
    *,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: UUID | None = None,
    project_id: UUID | None = None,
) -> tuple[list[TaskRead], PaginationMeta]:
    assigned_to_user_id = context.user.id if context.role == OrganizationRole.MEMBER else None
    manager_user_id = context.user.id if context.role == OrganizationRole.MANAGER else None
    tasks, total = tasks_repository.list_for_organization(
        session,
        context.organization.id,
        assigned_to_user_id=assigned_to_user_id,
        manager_user_id=manager_user_id,
        include_unassigned_projects=True,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        project_id=project_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [TaskRead.model_validate(task) for task in tasks], meta


def create_task(
    session: Session,
    context: OrganizationContext,
    payload: TaskCreate,
    redis: RedisClient,
) -> Task:
    if context.role not in _MANAGE_ALL_ROLES and context.role != OrganizationRole.MANAGER:
        raise ForbiddenError("You do not have permission to create tasks")

    project = _get_project_or_404(session, payload.project_id, context.organization.id)
    _require_manage_project(context, session, project)
    _resolve_assignee(session, context.organization.id, payload.assignee_id)

    task = Task(
        organization_id=context.organization.id,
        project_id=project.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        created_by=context.user.id,
        due_date=payload.due_date,
    )
    tasks_repository.add(session, task)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(task)
    return task


def get_task(session: Session, context: OrganizationContext, task_id: UUID) -> Task:
    task = _get_task_or_404(session, task_id, context.organization.id)
    if not _can_view_task(context, session, task):
        raise ForbiddenError()
    return task


def update_task(
    session: Session,
    context: OrganizationContext,
    task_id: UUID,
    payload: TaskUpdate,
    redis: RedisClient,
) -> Task:
    task = _get_task_or_404(session, task_id, context.organization.id)

    if context.role == OrganizationRole.MEMBER:
        if not _is_own_task(context, task) or _member_update_forbidden(payload):
            raise ForbiddenError()
    elif not _can_manage_task(context, session, task):
        raise ForbiddenError()

    if "project_id" in payload.model_fields_set:
        if payload.project_id is None:
            raise ValidationError("project_id is required")
        project = _get_project_or_404(session, payload.project_id, context.organization.id)
        _require_manage_project(context, session, project)
        task.project_id = project.id
    if payload.title is not None:
        task.title = payload.title
    if "description" in payload.model_fields_set:
        task.description = payload.description
    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if "assignee_id" in payload.model_fields_set:
        _resolve_assignee(session, context.organization.id, payload.assignee_id)
        task.assignee_id = payload.assignee_id
    if "due_date" in payload.model_fields_set:
        task.due_date = payload.due_date

    session.add(task)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(task)
    return task


def delete_task(
    session: Session, context: OrganizationContext, task_id: UUID, redis: RedisClient
) -> None:
    task = _get_task_or_404(session, task_id, context.organization.id)
    if not _can_manage_task(context, session, task):
        raise ForbiddenError()
    tasks_repository.delete(session, task)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
