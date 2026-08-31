"""Check-in HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.checkins.schemas import CheckInCreate, CheckInRead, CheckInUpdate
from app.modules.checkins.service import create_checkin, get_checkin, list_checkins, update_checkin
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/checkins", tags=["checkins"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[CheckInRead],
    summary="List check-ins",
    description=(
        "List check-ins in the current organization. Members see check-ins they belong to; "
        "owners and admins see all."
    ),
    responses=_AUTH_RESPONSES,
)
def read_checkins(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[CheckInRead]:
    checkins, meta = list_checkins(session, context, pagination)
    return CollectionResponse(data=checkins, meta=meta)


@router.post(
    "",
    response_model=DataResponse[CheckInRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create check-in",
    description=(
        "Create a draft check-in. Owners and managers may create check-ins. The member must "
        "belong to the same organization. Status starts as DRAFT."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_checkin_endpoint(
    payload: CheckInCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[CheckInRead]:
    checkin = create_checkin(session, context, payload)
    return DataResponse(data=CheckInRead.model_validate(checkin))


@router.get(
    "/{checkin_id}",
    response_model=DataResponse[CheckInRead],
    summary="Get check-in",
    description="Return a check-in in the current organization.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Check-in not found"},
    },
)
def read_checkin(
    checkin_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[CheckInRead]:
    checkin = get_checkin(session, context, checkin_id)
    return DataResponse(data=CheckInRead.model_validate(checkin))


@router.patch(
    "/{checkin_id}",
    response_model=DataResponse[CheckInRead],
    summary="Update check-in",
    description=(
        "Update a check-in. Members submit by setting status to SUBMITTED. Managers review by "
        "setting status to REVIEWED. Transitions cannot skip or reverse."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Check-in not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_checkin(
    checkin_id: UUID,
    payload: CheckInUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[CheckInRead]:
    checkin = update_checkin(session, context, checkin_id, payload)
    return DataResponse(data=CheckInRead.model_validate(checkin))
