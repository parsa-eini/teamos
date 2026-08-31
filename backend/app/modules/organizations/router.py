"""Organization HTTP API. Organization id is never accepted from the client."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.responses import DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context
from app.modules.organizations.schemas import OrganizationRead, OrganizationUpdate
from app.modules.organizations.service import update_organization

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get(
    "/current",
    response_model=DataResponse[OrganizationRead],
    status_code=status.HTTP_200_OK,
    summary="Current organization",
    description="Return the organization of the authenticated user, derived from membership.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "No organization membership"},
    },
)
def read_current_organization(
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[OrganizationRead]:
    return DataResponse(data=OrganizationRead.model_validate(context.organization))


@router.patch(
    "/current",
    response_model=DataResponse[OrganizationRead],
    status_code=status.HTTP_200_OK,
    summary="Update current organization",
    description="Update the current organization. Only the owner may change it.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Not the organization owner"},
        409: {"model": ErrorResponse, "description": "Slug already in use"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_current_organization(
    payload: OrganizationUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DataResponse[OrganizationRead]:
    organization = update_organization(
        session,
        context.organization,
        payload,
        role=context.role,
    )
    return DataResponse(data=OrganizationRead.model_validate(organization))
