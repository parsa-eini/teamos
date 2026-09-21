"""Notification HTTP API. Recipients are the authenticated user, never a client-supplied id."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.schemas import NotificationRead
from app.modules.notifications.service import list_notifications, mark_notification_read
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
}


@router.get(
    "",
    response_model=CollectionResponse[NotificationRead],
    summary="List notifications",
    description="List notifications for the authenticated user, newest first.",
    responses=_AUTH_RESPONSES,
)
def read_notifications(
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[NotificationRead]:
    notifications, meta = list_notifications(session, user, pagination)
    return CollectionResponse(data=notifications, meta=meta)


@router.patch(
    "/{notification_id}/read",
    response_model=DataResponse[NotificationRead],
    summary="Mark notification read",
    description="Mark one of the authenticated user's notifications as read.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Notification not found"},
    },
)
def patch_notification_read(
    notification_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> DataResponse[NotificationRead]:
    notification = mark_notification_read(session, user, notification_id)
    return DataResponse(data=NotificationRead.model_validate(notification))
