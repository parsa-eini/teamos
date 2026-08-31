"""Dashboard HTTP API. Organization scope comes from membership, never from the client."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.responses import DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.core.redis import RedisClient, get_redis
from app.modules.dashboard.schemas import DashboardRead
from app.modules.dashboard.service import get_dashboard
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
}


@router.get(
    "",
    response_model=DataResponse[DashboardRead],
    summary="Get dashboard",
    description=(
        "Return organization dashboard aggregates. Owners, admins, and managers may view it. "
        "The summary is cached in Redis."
    ),
    responses=_AUTH_RESPONSES,
)
def read_dashboard(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[DashboardRead]:
    return DataResponse(data=get_dashboard(session, context, redis))
