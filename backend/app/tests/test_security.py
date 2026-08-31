"""Unit tests for password hashing and access tokens."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.common.exceptions import UnauthorizedError
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_hashed_with_argon2id() -> None:
    hashed = hash_password("correct-horse")

    assert hashed != "correct-horse"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct-horse", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_round_trips_user_id(settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, settings)

    assert decode_access_token(token, settings) == user_id


def test_access_token_carries_access_type_claim(settings: Settings) -> None:
    token = create_access_token(uuid4(), settings)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

    assert payload["type"] == "access"


def test_expired_access_token_is_rejected(settings: Settings) -> None:
    user_id = uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        decode_access_token(token, settings)


def test_refresh_type_token_is_rejected(settings: Settings) -> None:
    payload = {
        "sub": str(uuid4()),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        decode_access_token(token, settings)
