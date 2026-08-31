"""Users HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.common.responses import DataResponse, ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=DataResponse[UserRead],
    status_code=status.HTTP_200_OK,
    summary="Current user",
    description="Return the authenticated user. Requires a bearer access token.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> DataResponse[UserRead]:
    return DataResponse(data=UserRead.model_validate(current_user))
