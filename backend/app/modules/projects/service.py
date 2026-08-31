"""Project use cases. Organization id is taken from membership context, never from the client."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenError, ResourceNotFoundError, ValidationError
from app.common.pagination import PaginationMeta, PaginationParams
from app.core.redis import RedisClient
from app.modules.dashboard.cache import invalidate_dashboard
from app.modules.organizations.dependencies import OrganizationContext
from app.modules.organizations.models import OrganizationRole
from app.modules.projects import repository as projects_repository
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.teams import repository as teams_repository

_MANAGE_ALL_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def _is_team_member(session: Session, team_id: UUID, user_id: UUID) -> bool:
    return teams_repository.get_membership(session, team_id, user_id) is not None


def _can_view(context: OrganizationContext, session: Session, project: Project) -> bool:
    if context.role in _MANAGE_ALL_ROLES:
        return True
    if project.team_id is None:
        return context.role == OrganizationRole.MANAGER
    return _is_team_member(session, project.team_id, context.user.id)


def _can_manage(context: OrganizationContext, session: Session, project: Project) -> bool:
    if context.role in _MANAGE_ALL_ROLES:
        return True
    if context.role != OrganizationRole.MANAGER:
        return False
    if project.team_id is None:
        return True
    return _is_team_member(session, project.team_id, context.user.id)


def can_view_project(context: OrganizationContext, session: Session, project: Project) -> bool:
    return _can_view(context, session, project)


def can_manage_project(context: OrganizationContext, session: Session, project: Project) -> bool:
    return _can_manage(context, session, project)


def _require_view(context: OrganizationContext, session: Session, project: Project) -> None:
    if not _can_view(context, session, project):
        raise ForbiddenError()


def _require_manage(context: OrganizationContext, session: Session, project: Project) -> None:
    if not _can_manage(context, session, project):
        raise ForbiddenError()


def _require_create(context: OrganizationContext) -> None:
    if context.role not in _MANAGE_ALL_ROLES and context.role != OrganizationRole.MANAGER:
        raise ForbiddenError("You do not have permission to create projects")


def _require_team_assignable(
    context: OrganizationContext,
    session: Session,
    team_id: UUID | None,
) -> None:
    if team_id is None:
        return
    if context.role in _MANAGE_ALL_ROLES:
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


def _assert_dates_ordered(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValidationError("end_date must not be before start_date")


def _get_project_or_404(session: Session, project_id: UUID, organization_id: UUID) -> Project:
    project = projects_repository.get_by_id(session, project_id, organization_id)
    if project is None:
        raise ResourceNotFoundError("Project not found")
    return project


def list_projects(
    session: Session,
    context: OrganizationContext,
    pagination: PaginationParams,
    status: ProjectStatus | None = None,
) -> tuple[list[ProjectRead], PaginationMeta]:
    member_user_id = None if context.role in _MANAGE_ALL_ROLES else context.user.id
    include_unassigned = context.role != OrganizationRole.MEMBER
    projects, total = projects_repository.list_for_organization(
        session,
        context.organization.id,
        member_user_id=member_user_id,
        include_unassigned=include_unassigned,
        status=status,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total=total)
    return [ProjectRead.model_validate(project) for project in projects], meta


def create_project(
    session: Session,
    context: OrganizationContext,
    payload: ProjectCreate,
    redis: RedisClient,
) -> Project:
    _require_create(context)
    _resolve_team(session, context.organization.id, payload.team_id)
    _require_team_assignable(context, session, payload.team_id)

    project = Project(
        organization_id=context.organization.id,
        team_id=payload.team_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by=context.user.id,
    )
    projects_repository.add(session, project)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(project)
    return project


def get_project(session: Session, context: OrganizationContext, project_id: UUID) -> Project:
    project = _get_project_or_404(session, project_id, context.organization.id)
    _require_view(context, session, project)
    return project


def update_project(
    session: Session,
    context: OrganizationContext,
    project_id: UUID,
    payload: ProjectUpdate,
    redis: RedisClient,
) -> Project:
    project = _get_project_or_404(session, project_id, context.organization.id)
    _require_manage(context, session, project)

    if "team_id" in payload.model_fields_set:
        _resolve_team(session, context.organization.id, payload.team_id)
        _require_team_assignable(context, session, payload.team_id)
        project.team_id = payload.team_id
    if payload.name is not None:
        project.name = payload.name
    if "description" in payload.model_fields_set:
        project.description = payload.description
    if payload.status is not None:
        project.status = payload.status
    if "start_date" in payload.model_fields_set:
        project.start_date = payload.start_date
    if "end_date" in payload.model_fields_set:
        project.end_date = payload.end_date

    _assert_dates_ordered(project.start_date, project.end_date)
    session.add(project)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
    session.refresh(project)
    return project


def delete_project(
    session: Session,
    context: OrganizationContext,
    project_id: UUID,
    redis: RedisClient,
) -> None:
    project = _get_project_or_404(session, project_id, context.organization.id)
    _require_manage(context, session, project)
    projects_repository.delete(session, project)
    session.commit()
    invalidate_dashboard(redis, context.organization.id)
