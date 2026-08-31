"""Task HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.core.redis import RedisClient, get_redis
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context
from app.modules.tasks.models import TaskPriority, TaskStatus
from app.modules.tasks.schemas import TaskCreate, TaskRead, TaskUpdate
from app.modules.tasks.service import create_task, delete_task, get_task, list_tasks, update_task

router = APIRouter(prefix="/tasks", tags=["tasks"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=CollectionResponse[TaskRead],
    summary="List tasks",
    description=(
        "List tasks in the current organization. Members see assigned tasks only. "
        "Filter with status, priority, assignee_id, and project_id."
    ),
    responses=_AUTH_RESPONSES,
)
def read_tasks(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    assignee_id: Annotated[UUID | None, Query()] = None,
    project_id: Annotated[UUID | None, Query()] = None,
) -> CollectionResponse[TaskRead]:
    tasks, meta = list_tasks(
        session,
        context,
        pagination,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        project_id=project_id,
    )
    return CollectionResponse(data=tasks, meta=meta)


@router.post(
    "",
    response_model=DataResponse[TaskRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description=(
        "Create a task on a project in the current organization. The assignee, if set, must "
        "belong to the same organization."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project or user not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_task_endpoint(
    payload: TaskCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[TaskRead]:
    task = create_task(session, context, payload, redis)
    return DataResponse(data=TaskRead.model_validate(task))


@router.get(
    "/{task_id}",
    response_model=DataResponse[TaskRead],
    summary="Get task",
    description="Return a task in the current organization.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Task not found"}},
)
def read_task(
    task_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[TaskRead]:
    task = get_task(session, context, task_id)
    return DataResponse(data=TaskRead.model_validate(task))


@router.patch(
    "/{task_id}",
    response_model=DataResponse[TaskRead],
    summary="Update task",
    description=(
        "Update a task. Members may update their assigned tasks but cannot reassign them "
        "or move them to another project."
    ),
    responses={
        **_AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Task not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_task(
    task_id: UUID,
    payload: TaskUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[TaskRead]:
    task = update_task(session, context, task_id, payload, redis)
    return DataResponse(data=TaskRead.model_validate(task))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Delete a task.",
    responses={**_AUTH_RESPONSES, 404: {"model": ErrorResponse, "description": "Task not found"}},
)
def delete_task_endpoint(
    task_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> Response:
    delete_task(session, context, task_id, redis)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
