"""CORS middleware tests."""

from fastapi.testclient import TestClient


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_rejects_unlisted_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_headers_are_present_on_simple_requests(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5174"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
