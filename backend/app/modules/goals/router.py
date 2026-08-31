"""Goal HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.core.redis import RedisClient, get_redis
from app.modules.goals.schemas import GoalCreate, GoalRead, GoalUpdate
from app.modules.goals.service import create_goal, get_goal, list_goals, update_goal
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/goals", tags=["goals"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[GoalRead],
    summary="List goals",
    description=(
        "List goals in the current organization. Members see their own goals; managers see "
        "organization-wide goals, assigned-team goals, and goals they created or own."
    ),
    responses=_AUTH_RESPONSES,
)
def read_goals(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[GoalRead]:
    goals, meta = list_goals(session, context, pagination)
    return CollectionResponse(data=goals, meta=meta)


@router.post(
    "",
    response_model=DataResponse[GoalRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create goal",
    description=(
        "Create a goal in the current organization. Owners and managers may create goals. "
        "Progress must be between 0 and 100."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Team or user not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_goal_endpoint(
    payload: GoalCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[GoalRead]:
    goal = create_goal(session, context, payload, redis)
    return DataResponse(data=GoalRead.model_validate(goal))


@router.get(
    "/{goal_id}",
    response_model=DataResponse[GoalRead],
    summary="Get goal",
    description="Return a goal in the current organization.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Goal not found"}},
)
def read_goal(
    goal_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[GoalRead]:
    goal = get_goal(session, context, goal_id)
    return DataResponse(data=GoalRead.model_validate(goal))


@router.patch(
    "/{goal_id}",
    response_model=DataResponse[GoalRead],
    summary="Update goal",
    description=(
        "Update a goal, including progress (0-100). Owners may update any goal; managers may "
        "update goals they can view."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Goal not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[GoalRead]:
    goal = update_goal(session, context, goal_id, payload, redis)
    return DataResponse(data=GoalRead.model_validate(goal))
