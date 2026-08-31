"""Goal CRUD, progress validation, authorization, and organization-isolation tests."""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import OrganizationMembership, OrganizationRole
from app.modules.users.models import User

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


def _create_team(client: TestClient, token: str, name: str) -> str:
    response = client.post("/api/v1/teams", headers=_auth(token), json={"name": name})
    assert response.status_code == 201, response.json()
    return str(response.json()["data"]["id"])


def _create_goal(client: TestClient, token: str, title: str, **fields: object) -> dict[str, object]:
    response = client.post(
        "/api/v1/goals",
        headers=_auth(token),
        json={"title": title, **fields},
    )
    assert response.status_code == 201, response.json()
    return dict(response.json()["data"])


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


def test_owner_can_create_and_update_goal(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    team_id = _create_team(client, token, "Platform")

    created = client.post(
        "/api/v1/goals",
        headers=_auth(token),
        json={
            "title": "Ship v1",
            "description": "Launch the MVP",
            "team_id": team_id,
            "user_id": str(owner["id"]),
            "status": "IN_PROGRESS",
            "progress": 40,
            "start_date": "2026-01-01",
            "due_date": "2026-06-01",
        },
    )
    assert created.status_code == 201
    goal = created.json()["data"]
    assert goal["title"] == "Ship v1"
    assert goal["description"] == "Launch the MVP"
    assert goal["team_id"] == team_id
    assert goal["user_id"] == str(owner["id"])
    assert goal["status"] == "IN_PROGRESS"
    assert goal["progress"] == 40
    assert goal["created_by"] == str(owner["id"])
    goal_id = goal["id"]

    listed = client.get("/api/v1/goals", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["meta"] == {"page": 1, "page_size": 20, "total": 1}
    assert listed.json()["data"][0]["id"] == goal_id

    fetched = client.get(f"/api/v1/goals/{goal_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["title"] == "Ship v1"

    patched = client.patch(
        f"/api/v1/goals/{goal_id}",
        headers=_auth(token),
        json={"progress": 100, "status": "COMPLETED", "description": None},
    )
    assert patched.status_code == 200
    body = patched.json()["data"]
    assert body["progress"] == 100
    assert body["status"] == "COMPLETED"
    assert body["description"] is None


def test_create_goal_defaults_status_and_progress(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    goal = _create_goal(client, token, "Improve onboarding")
    assert goal["status"] == "NOT_STARTED"
    assert goal["progress"] == 0
    assert goal["team_id"] is None
    assert goal["user_id"] is None


def test_list_goals_is_paginated(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    _create_goal(client, token, "One")
    _create_goal(client, token, "Two")
    _create_goal(client, token, "Three")

    page = client.get("/api/v1/goals?page=2&page_size=2", headers=_auth(token))
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1


def test_progress_is_rejected_outside_0_to_100(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    too_high = client.post(
        "/api/v1/goals",
        headers=_auth(token),
        json={"title": "Over", "progress": 101},
    )
    assert too_high.status_code == 422
    assert too_high.json()["error"]["code"] == "VALIDATION_ERROR"

    too_low = client.post(
        "/api/v1/goals",
        headers=_auth(token),
        json={"title": "Under", "progress": -1},
    )
    assert too_low.status_code == 422

    goal = _create_goal(client, token, "Valid", progress=0)
    patched = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=_auth(token),
        json={"progress": 101},
    )
    assert patched.status_code == 422
    assert patched.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_goal_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/goals", json={"title": "Nope"})
    assert response.status_code == 401


def test_create_goal_rejects_blank_title(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    response = client.post("/api/v1/goals", headers=_auth(token), json={"title": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_cannot_attach_team_or_user_from_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    outsider = _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    foreign_team = _create_team(client, token_b, "Globex Team")

    by_team = client.post(
        "/api/v1/goals",
        headers=_auth(token_a),
        json={"title": "Steal", "team_id": foreign_team},
    )
    assert by_team.status_code == 404

    by_user = client.post(
        "/api/v1/goals",
        headers=_auth(token_a),
        json={"title": "Steal", "user_id": str(outsider["id"])},
    )
    assert by_user.status_code == 404
    assert by_user.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_member_can_view_own_goal_only(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    own = _create_goal(client, owner_token, "Member goal", user_id=str(member["id"]))
    other = _create_goal(client, owner_token, "Org goal")

    assert (
        client.post(
            "/api/v1/goals",
            headers=_auth(member_token),
            json={"title": "Nope"},
        ).status_code
        == 403
    )

    listed = client.get("/api/v1/goals", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == own["id"]

    assert client.get(f"/api/v1/goals/{own['id']}", headers=_auth(member_token)).status_code == 200
    assert (
        client.get(f"/api/v1/goals/{other['id']}", headers=_auth(member_token)).status_code == 403
    )
    assert (
        client.patch(
            f"/api/v1/goals/{own['id']}",
            headers=_auth(member_token),
            json={"progress": 50},
        ).status_code
        == 403
    )


def test_admin_cannot_create_or_update_goals(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="admin@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "admin@example.com", OrganizationRole.ADMIN)
    owner_token = _login(client, "owner@example.com")
    admin_token = _login(client, "admin@example.com")
    goal = _create_goal(client, owner_token, "Org goal")

    assert (
        client.post(
            "/api/v1/goals",
            headers=_auth(admin_token),
            json={"title": "Nope"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/goals/{goal['id']}",
            headers=_auth(admin_token),
            json={"progress": 10},
        ).status_code
        == 403
    )
    listed = client.get("/api/v1/goals", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1


def test_manager_can_create_and_update_visible_goals(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    manager = _register(client, email="manager@example.com", organization_name="Other")
    _move_user_to_owner_org(
        app,
        "owner@example.com",
        "manager@example.com",
        OrganizationRole.MANAGER,
    )
    owner_token = _login(client, "owner@example.com")
    manager_token = _login(client, "manager@example.com")
    assigned_team = _create_team(client, owner_token, "Assigned")
    other_team = _create_team(client, owner_token, "Other")
    client.post(
        f"/api/v1/teams/{assigned_team}/members",
        headers=_auth(owner_token),
        json={"user_id": str(manager["id"])},
    )

    created = client.post(
        "/api/v1/goals",
        headers=_auth(manager_token),
        json={"title": "Team goal", "team_id": assigned_team, "progress": 10},
    )
    assert created.status_code == 201

    forbidden_team = client.post(
        "/api/v1/goals",
        headers=_auth(manager_token),
        json={"title": "Nope", "team_id": other_team},
    )
    assert forbidden_team.status_code == 403

    org_wide = _create_goal(client, owner_token, "Org wide")
    owner = client.get("/api/v1/users/me", headers=_auth(owner_token)).json()["data"]
    hidden = _create_goal(client, owner_token, "Hidden personal", user_id=str(owner["id"]))

    patched = client.patch(
        f"/api/v1/goals/{created.json()['data']['id']}",
        headers=_auth(manager_token),
        json={"progress": 55},
    )
    assert patched.status_code == 200
    assert (
        client.patch(
            f"/api/v1/goals/{org_wide['id']}",
            headers=_auth(manager_token),
            json={"progress": 20},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/goals/{hidden['id']}",
            headers=_auth(manager_token),
            json={"progress": 1},
        ).status_code
        == 403
    )

    listed = client.get("/api/v1/goals", headers=_auth(manager_token))
    titles = {item["title"] for item in listed.json()["data"]}
    assert "Team goal" in titles
    assert "Org wide" in titles
    assert "Hidden personal" not in titles


def test_cross_organization_goal_access_is_not_found(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    goal = _create_goal(client, token_a, "Ship v1")

    assert client.get(f"/api/v1/goals/{goal['id']}", headers=_auth(token_b)).status_code == 404
    assert (
        client.patch(
            f"/api/v1/goals/{goal['id']}",
            headers=_auth(token_b),
            json={"progress": 50},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/goals", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/goals/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_goal_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/goals"]
    assert "post" in paths["/api/v1/goals"]
    assert "get" in paths["/api/v1/goals/{goal_id}"]
    assert "patch" in paths["/api/v1/goals/{goal_id}"]
    assert "delete" not in paths.get("/api/v1/goals/{goal_id}", {})
