"""Authentication and current-user API tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User

_REGISTER_PAYLOAD = {
    "email": "Alex@example.com",
    "password": "correct-horse",
    "first_name": "Alex",
    "last_name": "Manager",
    "organization_name": "Alex Team",
}


def _register(client: TestClient, **overrides: object) -> Response:
    payload = {**_REGISTER_PAYLOAD, **overrides}
    return client.post("/api/v1/auth/register", json=payload)


def test_register_creates_user_and_hashes_password(client: TestClient, app: FastAPI) -> None:
    response = _register(client)

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["email"] == "alex@example.com"
    assert body["first_name"] == "Alex"
    assert body["last_name"] == "Manager"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in response.json()["data"]
    assert "password_hash" not in response.text

    session: Session = app.state.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == "alex@example.com"))
        assert user is not None
        assert user.password_hash != _REGISTER_PAYLOAD["password"]
        assert user.password_hash.startswith("$argon2id$")
    finally:
        session.close()


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    assert _register(client).status_code == 201
    response = _register(client, email="alex@example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_ALREADY_EXISTS"


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = _register(client, email="not-an-email")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = _register(client, password="short")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_returns_access_token(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "Alex@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_rejects_invalid_password(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_inactive_user(client: TestClient, app: FastAPI) -> None:
    _register(client)
    session: Session = app.state.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == "alex@example.com"))
        assert user is not None
        user.is_active = False
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_authenticated_user(client: TestClient) -> None:
    created = _register(client).json()["data"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "correct-horse"},
    ).json()["data"]["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["id"] == created["id"]
    assert body["email"] == "alex@example.com"
    assert "password_hash" not in body


def test_me_rejects_inactive_user(client: TestClient, app: FastAPI) -> None:
    _register(client)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "alex@example.com", "password": "correct-horse"},
    ).json()["data"]["access_token"]

    session: Session = app.state.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == "alex@example.com"))
        assert user is not None
        user.is_active = False
        session.commit()
    finally:
        session.close()

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_endpoints_are_documented(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "post" in paths["/api/v1/auth/register"]
    assert "post" in paths["/api/v1/auth/login"]
    assert "get" in paths["/api/v1/users/me"]
    assert "/api/v1/auth/refresh" not in paths
