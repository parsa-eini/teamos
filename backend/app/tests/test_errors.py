"""Tests for application exceptions and the section-24 error envelope."""

from fastapi import Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, model_validator

from app.common.exceptions import (
    ForbiddenError,
    InvalidCredentialsError,
    OrganizationAccessDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.config import Settings
from app.main import create_app


def test_unknown_path_uses_the_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Not Found",
        }
    }


def test_app_error_is_mapped_to_the_error_envelope(
    settings: Settings,
) -> None:
    app = create_app(settings)

    @app.get("/_missing")
    def missing() -> None:
        raise ResourceNotFoundError("Project not found")

    with TestClient(app) as test_client:
        response = test_client.get("/_missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Project not found",
        }
    }


def test_request_validation_error_uses_stable_code(settings: Settings) -> None:
    app = create_app(settings)

    @app.get("/_validate")
    def validate(count: int = Query()) -> dict[str, int]:
        return {"count": count}

    with TestClient(app) as test_client:
        response = test_client.get("/_validate")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "count: Field required",
        }
    }


def test_request_validation_error_reports_the_model_validator_reason(settings: Settings) -> None:
    """Model-level failures must reach the client as readable text, not a generic message."""
    app = create_app(settings)

    class Period(BaseModel):
        start: int
        end: int

        @model_validator(mode="after")
        def ordered(self) -> "Period":
            if self.end < self.start:
                raise ValueError("end must not be before start")
            return self

    @app.post("/_period")
    def period(payload: Period) -> dict[str, int]:
        return {"start": payload.start, "end": payload.end}

    with TestClient(app) as test_client:
        response = test_client.post("/_period", json={"start": 7, "end": 1})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "end must not be before start",
        }
    }


def test_request_validation_error_names_nested_fields_and_omits_input(
    settings: Settings,
) -> None:
    app = create_app(settings)

    class Inner(BaseModel):
        amount: int

    class Outer(BaseModel):
        inner: Inner

    @app.post("/_nested")
    def nested(payload: Outer) -> dict[str, int]:
        return {"amount": payload.inner.amount}

    with TestClient(app) as test_client:
        response = test_client.post("/_nested", json={"inner": {"amount": "not-a-number"}})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"].startswith("inner.amount: ")
    assert "not-a-number" not in response.text
    assert "int_parsing" not in response.text


def test_request_validation_error_caps_the_number_of_reported_problems(
    settings: Settings,
) -> None:
    app = create_app(settings)

    class Wide(BaseModel):
        a: int
        b: int
        c: int
        d: int

    @app.post("/_wide")
    def wide(payload: Wide) -> int:
        return payload.a

    with TestClient(app) as test_client:
        response = test_client.post("/_wide", json={})

    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert message.count(";") == 2
    assert "d:" not in message


def test_unhandled_error_does_not_expose_internals(settings: Settings) -> None:
    app = create_app(settings)

    @app.get("/_boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/_boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }
    }
    assert "secret internals" not in response.text
    assert "Traceback" not in response.text


def test_exception_classes_use_specified_codes() -> None:
    assert InvalidCredentialsError().code == "INVALID_CREDENTIALS"
    assert InvalidCredentialsError().status_code == 401
    assert UnauthorizedError().code == "UNAUTHORIZED"
    assert UnauthorizedError().status_code == 401
    assert ForbiddenError().code == "FORBIDDEN"
    assert ForbiddenError().status_code == 403
    assert ResourceAlreadyExistsError().code == "RESOURCE_ALREADY_EXISTS"
    assert ResourceAlreadyExistsError().status_code == 409
    assert OrganizationAccessDeniedError().code == "ORGANIZATION_ACCESS_DENIED"
    assert OrganizationAccessDeniedError().status_code == 403
    assert ValidationError().code == "VALIDATION_ERROR"
    assert ValidationError().status_code == 422
