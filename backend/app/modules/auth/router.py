"""Auth HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.common.responses import DataResponse, ErrorResponse
from app.core.database import get_db_session
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.auth.service import login_user, register_user
from app.modules.users.schemas import RegisterRequest, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=DataResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Register",
    description=(
        "Create a user account and the user's initial organization. "
        "The password is stored as an Argon2id hash. The caller becomes the organization owner."
    ),
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def register(
    payload: RegisterRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> DataResponse[UserRead]:
    user = register_user(session, payload)
    return DataResponse(data=UserRead.model_validate(user))


@router.post(
    "/login",
    response_model=DataResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with email and password and return a bearer access token.",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
) -> DataResponse[TokenResponse]:
    access_token = login_user(
        session,
        str(payload.email),
        payload.password,
        request.app.state.settings,
    )
    return DataResponse(data=TokenResponse(access_token=access_token))
