"""Feedback HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.feedback.models import FeedbackSentiment
from app.modules.feedback.schemas import FeedbackCreate, FeedbackRead, FeedbackUpdate
from app.modules.feedback.service import (
    create_feedback,
    delete_feedback,
    get_feedback,
    list_feedback,
    update_feedback,
)
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/feedback", tags=["feedback"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[FeedbackRead],
    summary="List feedback",
    description=(
        "List feedback in the current organization. You see feedback you wrote and feedback "
        "about people who report to you; owners and admins see all of it. Nobody sees feedback "
        "written about themselves. Filter with subject_id and sentiment."
    ),
    responses=_AUTH_RESPONSES,
)
def read_feedback_collection(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    subject_id: Annotated[UUID | None, Query()] = None,
    sentiment: Annotated[FeedbackSentiment | None, Query()] = None,
) -> CollectionResponse[FeedbackRead]:
    items, meta = list_feedback(
        session,
        context,
        pagination,
        subject_id=subject_id,
        sentiment=sentiment,
    )
    return CollectionResponse(data=items, meta=meta)


@router.post(
    "",
    response_model=DataResponse[FeedbackRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create feedback",
    description=(
        "Write feedback about another member of the current organization. The subject is not "
        "notified and cannot read it."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Subject not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_feedback_endpoint(
    payload: FeedbackCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[FeedbackRead]:
    feedback = create_feedback(session, context, payload)
    return DataResponse(data=FeedbackRead.model_validate(feedback))


@router.get(
    "/{feedback_id}",
    response_model=DataResponse[FeedbackRead],
    summary="Get feedback",
    description="Return one piece of feedback you are allowed to read.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Feedback not found"},
    },
)
def read_feedback(
    feedback_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[FeedbackRead]:
    feedback = get_feedback(session, context, feedback_id)
    return DataResponse(data=FeedbackRead.model_validate(feedback))


@router.patch(
    "/{feedback_id}",
    response_model=DataResponse[FeedbackRead],
    summary="Update feedback",
    description="Update feedback. Only the author may change it.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Feedback not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_feedback(
    feedback_id: UUID,
    payload: FeedbackUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[FeedbackRead]:
    feedback = update_feedback(session, context, feedback_id, payload)
    return DataResponse(data=FeedbackRead.model_validate(feedback))


@router.delete(
    "/{feedback_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete feedback",
    description="Delete feedback. Only the author may remove it.",
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Feedback not found"},
    },
)
def delete_feedback_endpoint(
    feedback_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> Response:
    delete_feedback(session, context, feedback_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
