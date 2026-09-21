"""Authentication dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.common.exceptions import UnauthorizedError
from app.core.database import get_db_session
from app.core.security import decode_access_token
from app.modules.users import repository as users_repository
from app.modules.users.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()

    user_id = decode_access_token(credentials.credentials, request.app.state.settings)
    user = users_repository.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()

    return user
