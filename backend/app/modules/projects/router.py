"""Project HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context
from app.modules.projects.models import ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.projects.service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[ProjectRead],
    summary="List projects",
    description=(
        "List projects in the current organization. Members see projects on assigned teams; "
        "managers also see organization-wide projects."
    ),
    responses=_AUTH_RESPONSES,
)
def read_projects(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[ProjectStatus | None, Query(alias="status")] = None,
) -> CollectionResponse[ProjectRead]:
    projects, meta = list_projects(session, context, pagination, status_filter)
    return CollectionResponse(data=projects, meta=meta)


@router.post(
    "",
    response_model=DataResponse[ProjectRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description=(
        "Create a project in the current organization. Owners, admins, and managers may create "
        "projects. A team_id must belong to the same organization."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Team not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_project_endpoint(
    payload: ProjectCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[ProjectRead]:
    project = create_project(session, context, payload)
    return DataResponse(data=ProjectRead.model_validate(project))


@router.get(
    "/{project_id}",
    response_model=DataResponse[ProjectRead],
    summary="Get project",
    description="Return a project in the current organization.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def read_project(
    project_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[ProjectRead]:
    project = get_project(session, context, project_id)
    return DataResponse(data=ProjectRead.model_validate(project))


@router.patch(
    "/{project_id}",
    response_model=DataResponse[ProjectRead],
    summary="Update project",
    description=(
        "Update a project. Owners and admins may update any project; managers may update "
        "organization-wide projects and projects on assigned teams."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[ProjectRead]:
    project = update_project(session, context, project_id, payload)
    return DataResponse(data=ProjectRead.model_validate(project))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
def delete_project_endpoint(
    project_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> Response:
    delete_project(session, context, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
