"""Organization HTTP API. Organization id is never accepted from the client."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.pagination import PaginationParams, get_pagination
from app.common.responses import CollectionResponse, DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.core.redis import RedisClient, get_redis
from app.modules.organizations.dependencies import OrganizationContext, get_organization_context
from app.modules.organizations.schemas import (
    OrganizationMemberCreate,
    OrganizationMemberRead,
    OrganizationRead,
    OrganizationUpdate,
)
from app.modules.organizations.service import create_member, list_members, update_organization

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


@router.get(
    "/current/members",
    response_model=CollectionResponse[OrganizationMemberRead],
    summary="List organization members",
    description="List members of the current organization. Scope comes from membership.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "No organization membership"},
    },
)
def read_organization_members(
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
) -> CollectionResponse[OrganizationMemberRead]:
    members, meta = list_members(session, context, pagination)
    return CollectionResponse(data=members, meta=meta)


@router.post(
    "/current/members",
    response_model=DataResponse[OrganizationMemberRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create organization member",
    description=(
        "Create a user in the current organization. Owners and admins may add members. "
        "The new user signs in with the provided email and password."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Not allowed to manage members"},
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_organization_member(
    payload: OrganizationMemberCreate,
    session: Annotated[Session, Depends(get_db_session)],
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    redis: Annotated[RedisClient, Depends(get_redis)],
) -> DataResponse[OrganizationMemberRead]:
    member = create_member(session, context, payload, redis)
    return DataResponse(data=member)
