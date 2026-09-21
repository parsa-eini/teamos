"""Meeting HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.core.redis import RedisClient, get_redis
from app.modules.meetings.models import MeetingType
from app.modules.meetings.schemas import MeetingCreate, MeetingRead, MeetingUpdate
from app.modules.meetings.service import (
    create_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
)
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/meetings", tags=["meetings"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[MeetingRead],
    summary="List meetings",
    description=(
        "List meetings in the current organization. Members see meetings they take part in; "
        "owners and admins see all. Filter with type."
    ),
    responses=_AUTH_RESPONSES,
)
def read_meetings(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    meeting_type: Annotated[MeetingType | None, Query(alias="type")] = None,
) -> CollectionResponse[MeetingRead]:
    meetings, meta = list_meetings(session, context, pagination, meeting_type=meeting_type)
    return CollectionResponse(data=meetings, meta=meta)


@router.post(
    "",
    response_model=DataResponse[MeetingRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create meeting",
    description=(
        "Create a draft meeting: a check-in, a one-on-one, or a performance review. Owners and "
        "managers may create meetings. The member must belong to the same organization. Status "
        "starts as DRAFT."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_meeting_endpoint(
    payload: MeetingCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[MeetingRead]:
    meeting = create_meeting(session, context, payload, redis)
    return DataResponse(data=MeetingRead.model_validate(meeting))


@router.get(
    "/{meeting_id}",
    response_model=DataResponse[MeetingRead],
    summary="Get meeting",
    description="Return a meeting in the current organization.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Meeting not found"},
    },
)
def read_meeting(
    meeting_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[MeetingRead]:
    meeting = get_meeting(session, context, meeting_id)
    return DataResponse(data=MeetingRead.model_validate(meeting))


@router.patch(
    "/{meeting_id}",
    response_model=DataResponse[MeetingRead],
    summary="Update meeting",
    description=(
        "Update a meeting. Members submit by setting status to SUBMITTED. Managers review by "
        "setting status to REVIEWED. Transitions cannot skip or reverse."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Meeting not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_meeting(
    meeting_id: UUID,
    payload: MeetingUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[MeetingRead]:
    meeting = update_meeting(session, context, meeting_id, payload, redis)
    return DataResponse(data=MeetingRead.model_validate(meeting))
