"""Team HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context
from app.modules.teams.schemas import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberRead,
    TeamRead,
    TeamUpdate,
)
from app.modules.teams.service import (
    add_member,
    create_team,
    delete_team,
    get_team,
    list_members,
    list_teams,
    remove_member,
    update_team,
)

router = APIRouter(prefix="/teams", tags=["teams"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[TeamRead],
    summary="List teams",
    description=(
        "List teams in the current organization. Members and managers see only assigned teams."
    ),
    responses=_AUTH_RESPONSES,
)
def read_teams(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[TeamRead]:
    teams, meta = list_teams(session, context, pagination)
    return CollectionResponse(data=teams, meta=meta)


@router.post(
    "",
    response_model=DataResponse[TeamRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create team",
    description="Create a team in the current organization. Owners and admins may create teams.",
    responses={**_AUTH_RESPONSES, 422: {"model": ErrorResponse, "description": "Validation error"}},
)
def create_team_endpoint(
    payload: TeamCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[TeamRead]:
    team = create_team(session, context, payload)
    return DataResponse(data=TeamRead.model_validate(team))


@router.get(
    "/{team_id}",
    response_model=DataResponse[TeamRead],
    summary="Get team",
    description="Return a team in the current organization.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Team not found"}},
)
def read_team(
    team_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[TeamRead]:
    team = get_team(session, context, team_id)
    return DataResponse(data=TeamRead.model_validate(team))


@router.patch(
    "/{team_id}",
    response_model=DataResponse[TeamRead],
    summary="Update team",
    description=(
        "Update a team. Owners and admins may update any team; managers may update assigned teams."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Team not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_team(
    team_id: UUID,
    payload: TeamUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[TeamRead]:
    team = update_team(session, context, team_id, payload)
    return DataResponse(data=TeamRead.model_validate(team))


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete team",
    description="Delete a team and its memberships.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Team not found"}},
)
def delete_team_endpoint(
    team_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> Response:
    delete_team(session, context, team_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{team_id}/members",
    response_model=CollectionResponse[TeamMemberRead],
    summary="List team members",
    description="List members of a team in the current organization.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Team not found"}},
)
def read_team_members(
    team_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[TeamMemberRead]:
    members, meta = list_members(session, context, team_id, pagination)
    return CollectionResponse(data=members, meta=meta)


@router.post(
    "/{team_id}/members",
    response_model=DataResponse[TeamMemberRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description=(
        "Add an organization member to a team. The user must belong to the same organization."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Team or user not found"},
        409: {"model": ErrorResponse, "description": "User already on the team"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def add_team_member(
    team_id: UUID,
    payload: TeamMemberAdd,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[TeamMemberRead]:
    member = add_member(session, context, team_id, payload.user_id)
    return DataResponse(data=member)


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team member",
    description="Remove a member from a team.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Team member not found"},
    },
)
def delete_team_member(
    team_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> Response:
    remove_member(session, context, team_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
