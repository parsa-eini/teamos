"""Dashboard aggregates, cache, authorization, and organization-isolation tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.dashboard.cache import DASHBOARD_CACHE_TTL_SECONDS, dashboard_cache_key
from app.modules.organizations.models import OrganizationMembership, OrganizationRole
from app.modules.users.models import User
from app.tests.conftest import FakeRedis

_PASSWORD = "correct-horse"


def _register(client: TestClient, *, email: str, organization_name: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PASSWORD,
            "first_name": "Alex",
            "last_name": "User",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201
    return dict(response.json()["data"])


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["data"]["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _organization_id(app: FastAPI, email: str) -> UUID:
    session: Session = app.state.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
        assert membership is not None
        return membership.organization_id
    finally:
        session.close()


def _move_user_to_owner_org(
    app: FastAPI,
    owner_email: str,
    member_email: str,
    role: OrganizationRole,
) -> None:
    session: Session = app.state.session_factory()
    try:
        owner = session.scalar(select(User).where(User.email == owner_email))
        member = session.scalar(select(User).where(User.email == member_email))
        assert owner is not None
        assert member is not None
        owner_membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == owner.id)
        )
        member_membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == member.id)
        )
        assert owner_membership is not None
        assert member_membership is not None
        member_membership.organization_id = owner_membership.organization_id
        member_membership.role = role
        session.commit()
    finally:
        session.close()


def _create_project(
    client: TestClient, token: str, name: str, **fields: object
) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        headers=_auth(token),
        json={"name": name, **fields},
    )
    assert response.status_code == 201, response.json()
    return dict(response.json()["data"])


def _create_task(
    client: TestClient, token: str, project_id: str, title: str, **fields: object
) -> dict[str, object]:
    response = client.post(
        "/api/v1/tasks",
        headers=_auth(token),
        json={"project_id": project_id, "title": title, **fields},
    )
    assert response.status_code == 201, response.json()
    return dict(response.json()["data"])


def test_empty_dashboard_for_new_organization(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    response = client.get("/api/v1/dashboard", headers=_auth(token))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["member_count"] == 1
    assert data["active_projects"] == 0
    assert data["open_tasks"] == 0
    assert data["overdue_tasks"] == 0
    assert data["goal_summary"] == {"total": 0, "items": []}
    assert data["recent_checkins"] == []
    assert data["recent_activity"] == []


def test_dashboard_aggregates_scoped_to_the_current_organization(
    client: TestClient, app: FastAPI
) -> None:
    member = _register(client, email="member@example.com", organization_name="Other")
    _register(client, email="owner@example.com", organization_name="Acme")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    _register(client, email="outsider@example.com", organization_name="Beta")
    outsider_token = _login(client, "outsider@example.com")
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    today = datetime.now(UTC).date().isoformat()

    _create_project(client, outsider_token, "Foreign", status="ACTIVE")
    created = client.post(
        "/api/v1/goals",
        headers=_auth(outsider_token),
        json={"title": "Foreign goal", "progress": 90},
    )
    assert created.status_code == 201

    active = _create_project(client, owner_token, "Launch", status="ACTIVE")
    _create_project(client, owner_token, "Backlog", status="PLANNED")
    project_id = str(active["id"])

    _create_task(
        client,
        owner_token,
        project_id,
        "Overdue open",
        status="TODO",
        due_date="2020-01-01",
    )
    _create_task(
        client,
        owner_token,
        project_id,
        "Open current",
        status="IN_PROGRESS",
        due_date="2099-12-01",
    )
    _create_task(
        client,
        owner_token,
        project_id,
        "API redesign",
        status="DONE",
        due_date="2020-01-01",
    )
    _create_task(client, owner_token, project_id, "Due today", status="TODO", due_date=today)

    live = client.post(
        "/api/v1/goals",
        headers=_auth(owner_token),
        json={"title": "Ship v1", "status": "IN_PROGRESS", "progress": 70},
    )
    assert live.status_code == 201
    cancelled = client.post(
        "/api/v1/goals",
        headers=_auth(owner_token),
        json={"title": "Dropped", "status": "CANCELLED", "progress": 10},
    )
    assert cancelled.status_code == 201

    checkin = client.post(
        "/api/v1/checkins",
        headers=_auth(owner_token),
        json={
            "member_id": str(member["id"]),
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
        },
    )
    assert checkin.status_code == 201
    checkin_id = checkin.json()["data"]["id"]
    submitted = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200

    response = client.get("/api/v1/dashboard", headers=_auth(owner_token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["member_count"] == 2
    assert data["active_projects"] == 1
    assert data["open_tasks"] == 3
    assert data["overdue_tasks"] == 1
    assert data["goal_summary"]["total"] == 2
    assert [item["title"] for item in data["goal_summary"]["items"]] == ["Ship v1"]
    assert data["goal_summary"]["items"][0]["progress"] == 70
    assert data["goal_summary"]["items"][0]["status"] == "IN_PROGRESS"
    assert len(data["recent_checkins"]) == 1
    assert data["recent_checkins"][0]["id"] == checkin_id
    assert data["recent_checkins"][0]["status"] == "SUBMITTED"
    assert data["recent_checkins"][0]["member_id"] == str(member["id"])

    messages = [item["message"] for item in data["recent_activity"]]
    assert 'Alex User completed "API redesign"' in messages
    assert "Alex User submitted weekly check-in" in messages
    assert "Alex User created a new project" in messages
    assert all("Foreign" not in message for message in messages)


def test_dashboard_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_member_cannot_view_dashboard(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "member@example.com")

    response = client.get("/api/v1/dashboard", headers=_auth(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_manager_and_admin_can_view_dashboard(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="manager@example.com", organization_name="MgrCo")
    _register(client, email="admin@example.com", organization_name="AdmCo")
    _move_user_to_owner_org(
        app, "owner@example.com", "manager@example.com", OrganizationRole.MANAGER
    )
    _move_user_to_owner_org(app, "owner@example.com", "admin@example.com", OrganizationRole.ADMIN)

    manager_response = client.get(
        "/api/v1/dashboard", headers=_auth(_login(client, "manager@example.com"))
    )
    admin_response = client.get(
        "/api/v1/dashboard", headers=_auth(_login(client, "admin@example.com"))
    )
    assert manager_response.status_code == 200
    assert admin_response.status_code == 200
    assert manager_response.json()["data"]["member_count"] == 3
    assert admin_response.json()["data"]["member_count"] == 3


def test_dashboard_does_not_leak_another_organization(
    client: TestClient,
) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Beta")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    _create_project(client, token_a, "Acme Launch", status="ACTIVE")
    _create_project(client, token_b, "Beta Launch", status="ACTIVE")

    dash_a = client.get("/api/v1/dashboard", headers=_auth(token_a))
    dash_b = client.get("/api/v1/dashboard", headers=_auth(token_b))
    assert dash_a.status_code == 200
    assert dash_b.status_code == 200
    assert dash_a.json()["data"]["active_projects"] == 1
    assert dash_b.json()["data"]["active_projects"] == 1
    assert dash_a.json()["data"]["member_count"] == 1
    assert dash_b.json()["data"]["member_count"] == 1


def test_dashboard_is_cached_and_invalidated_after_writes(
    client: TestClient, app: FastAPI, fake_redis: FakeRedis
) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    organization_id = _organization_id(app, "owner@example.com")
    cache_key = dashboard_cache_key(organization_id)

    first = client.get("/api/v1/dashboard", headers=_auth(token))
    assert first.status_code == 200
    assert first.json()["data"]["active_projects"] == 0
    assert cache_key in fake_redis.store
    assert fake_redis.ttls[cache_key] == DASHBOARD_CACHE_TTL_SECONDS

    _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)

    cached = client.get("/api/v1/dashboard", headers=_auth(token))
    assert cached.status_code == 200
    assert cached.json()["data"]["member_count"] == 1
    assert cached.json()["data"]["active_projects"] == 0

    _create_project(client, token, "Launch", status="ACTIVE")
    assert cache_key not in fake_redis.store

    refreshed = client.get("/api/v1/dashboard", headers=_auth(token))
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["member_count"] == 2
    assert refreshed.json()["data"]["active_projects"] == 1
    assert cache_key in fake_redis.store

    cached_again = client.get("/api/v1/dashboard", headers=_auth(token))
    assert cached_again.status_code == 200
    assert cached_again.json() == refreshed.json()


def test_dashboard_endpoint_is_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/dashboard"]
    assert "post" not in paths.get("/api/v1/dashboard", {})


def test_dashboard_cache_key_includes_organization_id() -> None:
    organization_id = uuid4()
    assert dashboard_cache_key(organization_id) == f"dashboard:{organization_id}"
