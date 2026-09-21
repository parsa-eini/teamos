"""Password hashing and access-token helpers.

Passwords are hashed with Argon2id. Access tokens are JWTs with a `type=access` claim so a
refresh-token flow can be added later without changing the verification shape.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.common.exceptions import UnauthorizedError
from app.core.config import Settings

_password_hasher = PasswordHasher()
_ACCESS_TOKEN_TYPE = "access"
_JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": _ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_JWT_ALGORITHM],
            leeway=timedelta(seconds=30),
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc

    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid or expired access token")

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise UnauthorizedError("Invalid or expired access token")

    try:
        return UUID(subject)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
