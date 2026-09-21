"""Tests for the health endpoint and the request logging middleware."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.core.logging import REQUEST_ID_HEADER, JsonFormatter


class _RecordCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def collect_request_logs() -> Iterator[_RecordCollector]:
    """Capture records from the request logger.

    The handler is attached to the request logger rather than to the root logger, because
    `configure_logging` owns the root handlers.
    """
    collector = _RecordCollector()
    logger = logging.getLogger("app.request")
    logger.addHandler(collector)
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        yield collector
    finally:
        logger.setLevel(previous_level)
        logger.removeHandler(collector)


def test_health_returns_healthy_status(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers[REQUEST_ID_HEADER]


def test_incoming_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "given-request-id"})

    assert response.headers[REQUEST_ID_HEADER] == "given-request-id"


def test_each_request_gets_a_distinct_request_id(client: TestClient) -> None:
    first = client.get("/health").headers[REQUEST_ID_HEADER]
    second = client.get("/health").headers[REQUEST_ID_HEADER]

    assert first != second


def test_unknown_path_returns_not_found(client: TestClient) -> None:
    assert client.get("/does-not-exist").status_code == 404


def test_health_is_documented_in_the_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/health"]["get"]
    assert operation["summary"] == "Health check"
    assert "200" in operation["responses"]


def test_request_is_logged_with_the_required_fields(client: TestClient) -> None:
    with collect_request_logs() as collector:
        response = client.get("/health")

    assert len(collector.records) == 1
    logged = collector.records[0].__dict__
    assert logged["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert logged["method"] == "GET"
    assert logged["path"] == "/health"
    assert logged["status_code"] == 200
    assert isinstance(logged["duration_ms"], float)


def test_request_log_does_not_include_credentials(client: TestClient) -> None:
    with collect_request_logs() as collector:
        client.post(
            "/api/v1/auth/login",
            json={"email": "alex@example.com", "password": "super-secret-password"},
            headers={"Authorization": "Bearer leaked-access-token"},
        )

    assert collector.records
    payload = json.loads(JsonFormatter().format(collector.records[0]))
    serialized = json.dumps(payload)
    assert "super-secret-password" not in serialized
    assert "leaked-access-token" not in serialized
    assert "password" not in serialized
    assert "authorization" not in serialized.lower()
    assert payload["path"] == "/api/v1/auth/login"


def test_request_log_records_are_serialisable_json(client: TestClient) -> None:
    with collect_request_logs() as collector:
        client.get("/health")

    payload = json.loads(JsonFormatter().format(collector.records[0]))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.request"
    assert payload["status_code"] == 200
