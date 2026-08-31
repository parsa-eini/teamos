"""Project CRUD, authorization, and organization-isolation tests."""

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


def test_owner_can_crud_project(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    team_id = _create_team(client, token, "Platform")

    created = client.post(
        "/api/v1/projects",
        headers=_auth(token),
        json={
            "name": "Launch",
            "description": "Ship v1",
            "team_id": team_id,
            "status": "ACTIVE",
            "start_date": "2026-01-01",
            "end_date": "2026-03-01",
        },
    )
    assert created.status_code == 201
    project = created.json()["data"]
    assert project["name"] == "Launch"
    assert project["description"] == "Ship v1"
    assert project["team_id"] == team_id
    assert project["status"] == "ACTIVE"
    assert project["start_date"] == "2026-01-01"
    assert project["end_date"] == "2026-03-01"
    assert project["created_by"] == str(owner["id"])
    project_id = project["id"]

    listed = client.get("/api/v1/projects", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["meta"] == {"page": 1, "page_size": 20, "total": 1}
    assert listed.json()["data"][0]["id"] == project_id

    fetched = client.get(f"/api/v1/projects/{project_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["name"] == "Launch"

    patched = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=_auth(token),
        json={"name": "Launch 2", "status": "COMPLETED", "description": None, "team_id": None},
    )
    assert patched.status_code == 200
    body = patched.json()["data"]
    assert body["name"] == "Launch 2"
    assert body["status"] == "COMPLETED"
    assert body["description"] is None
    assert body["team_id"] is None

    deleted = client.delete(f"/api/v1/projects/{project_id}", headers=_auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}", headers=_auth(token)).status_code == 404


def test_create_project_defaults_status_to_planned(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    project = _create_project(client, token, "Roadmap")
    assert project["status"] == "PLANNED"
    assert project["team_id"] is None


def test_list_projects_is_paginated_and_filterable(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    _create_project(client, token, "One", status="PLANNED")
    _create_project(client, token, "Two", status="ACTIVE")
    _create_project(client, token, "Three", status="ACTIVE")

    page = client.get("/api/v1/projects?page=2&page_size=2", headers=_auth(token))
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1

    filtered = client.get("/api/v1/projects?status=ACTIVE", headers=_auth(token))
    assert filtered.status_code == 200
    assert filtered.json()["meta"]["total"] == 2
    assert {item["name"] for item in filtered.json()["data"]} == {"Two", "Three"}


def test_create_project_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json={"name": "Launch"})
    assert response.status_code == 401


def test_create_project_rejects_blank_name_and_invalid_dates(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    blank = client.post("/api/v1/projects", headers=_auth(token), json={"name": "   "})
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "VALIDATION_ERROR"

    dates = client.post(
        "/api/v1/projects",
        headers=_auth(token),
        json={"name": "Launch", "start_date": "2026-03-01", "end_date": "2026-01-01"},
    )
    assert dates.status_code == 422
    assert dates.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_project_rejects_team_from_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    foreign_team = _create_team(client, token_b, "Globex Team")

    response = client.post(
        "/api/v1/projects",
        headers=_auth(token_a),
        json={"name": "Launch", "team_id": foreign_team},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_member_cannot_create_or_update_project(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    team_id = _create_team(client, owner_token, "Platform")
    project = _create_project(client, owner_token, "Launch", team_id=team_id)

    assert (
        client.post(
            "/api/v1/projects",
            headers=_auth(member_token),
            json={"name": "Nope"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}",
            headers=_auth(member_token),
            json={"name": "Hijacked"},
        ).status_code
        == 403
    )
    listed = client.get("/api/v1/projects", headers=_auth(member_token))
    assert listed.status_code == 200
    assert listed.json()["data"] == []
    assert (
        client.get(f"/api/v1/projects/{project['id']}", headers=_auth(member_token)).status_code
        == 403
    )


def test_member_can_view_project_on_assigned_team(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    team_id = _create_team(client, owner_token, "Platform")
    added = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(owner_token),
        json={"user_id": str(member["id"])},
    )
    assert added.status_code == 201
    project = _create_project(client, owner_token, "Launch", team_id=team_id)
    org_wide = _create_project(client, owner_token, "Org Wide")

    listed = client.get("/api/v1/projects", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == project["id"]
    fetched = client.get(f"/api/v1/projects/{project['id']}", headers=_auth(member_token))
    assert fetched.status_code == 200
    assert (
        client.get(f"/api/v1/projects/{org_wide['id']}", headers=_auth(member_token)).status_code
        == 403
    )


def test_manager_can_manage_assigned_and_unassigned_projects(
    client: TestClient, app: FastAPI
) -> None:
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
    assigned = _create_project(client, owner_token, "Assigned Project", team_id=assigned_team)
    other = _create_project(client, owner_token, "Other Project", team_id=other_team)
    org_wide = _create_project(client, owner_token, "Org Wide")

    created = client.post(
        "/api/v1/projects",
        headers=_auth(manager_token),
        json={"name": "Manager Project", "team_id": assigned_team},
    )
    assert created.status_code == 201

    forbidden_team = client.post(
        "/api/v1/projects",
        headers=_auth(manager_token),
        json={"name": "Nope", "team_id": other_team},
    )
    assert forbidden_team.status_code == 403

    patched = client.patch(
        f"/api/v1/projects/{assigned['id']}",
        headers=_auth(manager_token),
        json={"name": "Assigned Now"},
    )
    assert patched.status_code == 200
    assert (
        client.patch(
            f"/api/v1/projects/{org_wide['id']}",
            headers=_auth(manager_token),
            json={"status": "ACTIVE"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/projects/{other['id']}",
            headers=_auth(manager_token),
            json={"name": "Nope"},
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/projects/{other['id']}", headers=_auth(manager_token)).status_code
        == 403
    )

    listed = client.get("/api/v1/projects", headers=_auth(manager_token))
    names = {item["name"] for item in listed.json()["data"]}
    assert "Assigned Now" in names
    assert "Org Wide" in names
    assert "Manager Project" in names
    assert "Other Project" not in names


def test_cross_organization_project_access_is_not_found(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    project = _create_project(client, token_a, "Launch")

    assert (
        client.get(f"/api/v1/projects/{project['id']}", headers=_auth(token_b)).status_code == 404
    )
    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}",
            headers=_auth(token_b),
            json={"name": "Stolen"},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/projects/{project['id']}", headers=_auth(token_b)).status_code
        == 404
    )
    assert client.get("/api/v1/projects", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/projects/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_project_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/projects"]
    assert "post" in paths["/api/v1/projects"]
    assert "get" in paths["/api/v1/projects/{project_id}"]
    assert "patch" in paths["/api/v1/projects/{project_id}"]
    assert "delete" in paths["/api/v1/projects/{project_id}"]
