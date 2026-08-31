"""Team CRUD, membership, and organization-isolation tests."""

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


def _create_team(client: TestClient, token: str, name: str, **fields: object) -> str:
    response = client.post(
        "/api/v1/teams",
        headers=_auth(token),
        json={"name": name, **fields},
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["data"]["id"])


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


def test_owner_can_crud_team(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    created = client.post(
        "/api/v1/teams",
        headers=_auth(token),
        json={"name": "Platform", "description": "Core services"},
    )
    assert created.status_code == 201
    team = created.json()["data"]
    assert team["name"] == "Platform"
    assert team["description"] == "Core services"
    team_id = team["id"]

    listed = client.get("/api/v1/teams", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["meta"] == {"page": 1, "page_size": 20, "total": 1}
    assert listed.json()["data"][0]["id"] == team_id

    fetched = client.get(f"/api/v1/teams/{team_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["name"] == "Platform"

    patched = client.patch(
        f"/api/v1/teams/{team_id}",
        headers=_auth(token),
        json={"name": "Platform Eng", "description": None},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "Platform Eng"
    assert patched.json()["data"]["description"] is None

    deleted = client.delete(f"/api/v1/teams/{team_id}", headers=_auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/teams/{team_id}", headers=_auth(token)).status_code == 404


def test_list_teams_is_paginated(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    for index in range(3):
        client.post(
            "/api/v1/teams",
            headers=_auth(token),
            json={"name": f"Team {index}"},
        )

    response = client.get("/api/v1/teams?page=2&page_size=2", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(body["data"]) == 1


def test_create_team_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/teams", json={"name": "Platform"})
    assert response.status_code == 401


def test_create_team_rejects_blank_name(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    response = client.post(
        "/api/v1/teams",
        headers=_auth(_login(client, "owner@example.com")),
        json={"name": "   "},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_member_cannot_create_or_update_team(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    team_id = client.post(
        "/api/v1/teams",
        headers=_auth(owner_token),
        json={"name": "Platform"},
    ).json()["data"]["id"]

    assert (
        client.post("/api/v1/teams", headers=_auth(member_token), json={"name": "Nope"}).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/teams/{team_id}",
            headers=_auth(member_token),
            json={"name": "Hijacked"},
        ).status_code
        == 403
    )
    listed = client.get("/api/v1/teams", headers=_auth(member_token))
    assert listed.status_code == 200
    assert listed.json()["data"] == []
    assert client.get(f"/api/v1/teams/{team_id}", headers=_auth(member_token)).status_code == 403
    assert (
        client.post(
            f"/api/v1/teams/{team_id}/members",
            headers=_auth(member_token),
            json={"user_id": str(uuid4())},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/teams/{team_id}/members/{uuid4()}",
            headers=_auth(member_token),
        ).status_code
        == 403
    )


def test_member_can_view_assigned_team(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    member_id = str(member["id"])

    team_id = client.post(
        "/api/v1/teams",
        headers=_auth(owner_token),
        json={"name": "Platform"},
    ).json()["data"]["id"]
    added = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(owner_token),
        json={"user_id": member_id},
    )
    assert added.status_code == 201

    listed = client.get("/api/v1/teams", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == team_id
    fetched = client.get(f"/api/v1/teams/{team_id}", headers=_auth(member_token))
    assert fetched.status_code == 200


def test_manager_can_manage_assigned_team_only(client: TestClient, app: FastAPI) -> None:
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

    assert (
        client.post(
            "/api/v1/teams",
            headers=_auth(manager_token),
            json={"name": "Created by manager"},
        ).status_code
        == 403
    )

    assigned_id = client.post(
        "/api/v1/teams",
        headers=_auth(owner_token),
        json={"name": "Assigned"},
    ).json()["data"]["id"]
    other_id = client.post(
        "/api/v1/teams",
        headers=_auth(owner_token),
        json={"name": "Unassigned"},
    ).json()["data"]["id"]
    client.post(
        f"/api/v1/teams/{assigned_id}/members",
        headers=_auth(owner_token),
        json={"user_id": str(manager["id"])},
    )

    patched = client.patch(
        f"/api/v1/teams/{assigned_id}",
        headers=_auth(manager_token),
        json={"name": "Assigned Now"},
    )
    assert patched.status_code == 200
    assert (
        client.patch(
            f"/api/v1/teams/{other_id}",
            headers=_auth(manager_token),
            json={"name": "Nope"},
        ).status_code
        == 403
    )
    assert client.get(f"/api/v1/teams/{other_id}", headers=_auth(manager_token)).status_code == 403
    listed = client.get("/api/v1/teams", headers=_auth(manager_token))
    assert [team["name"] for team in listed.json()["data"]] == ["Assigned Now"]


def test_add_and_remove_team_member(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "owner@example.com")
    team_id = client.post(
        "/api/v1/teams",
        headers=_auth(token),
        json={"name": "Platform"},
    ).json()["data"]["id"]

    added = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(token),
        json={"user_id": str(member["id"])},
    )
    assert added.status_code == 201
    assert added.json()["data"]["email"] == "member@example.com"

    listed = client.get(f"/api/v1/teams/{team_id}/members", headers=_auth(token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["user_id"] == str(member["id"])

    duplicate = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(token),
        json={"user_id": str(member["id"])},
    )
    assert duplicate.status_code == 409

    unknown = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(token),
        json={"user_id": str(uuid4())},
    )
    assert unknown.status_code == 404

    removed = client.delete(
        f"/api/v1/teams/{team_id}/members/{member['id']}",
        headers=_auth(token),
    )
    assert removed.status_code == 204
    assert (
        client.get(f"/api/v1/teams/{team_id}/members", headers=_auth(token)).json()["meta"]["total"]
        == 0
    )


def test_cannot_add_user_from_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    outsider = _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    team_id = client.post(
        "/api/v1/teams",
        headers=_auth(token_a),
        json={"name": "Platform"},
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(token_a),
        json={"user_id": str(outsider["id"])},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cross_organization_team_access_is_not_found(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    team_id = client.post(
        "/api/v1/teams",
        headers=_auth(token_a),
        json={"name": "Platform"},
    ).json()["data"]["id"]

    assert client.get(f"/api/v1/teams/{team_id}", headers=_auth(token_b)).status_code == 404
    assert (
        client.patch(
            f"/api/v1/teams/{team_id}",
            headers=_auth(token_b),
            json={"name": "Stolen"},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/teams/{team_id}", headers=_auth(token_b)).status_code == 404
    assert (
        client.post(
            f"/api/v1/teams/{team_id}/members",
            headers=_auth(token_b),
            json={"user_id": str(uuid4())},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/teams/{team_id}/members/{uuid4()}",
            headers=_auth(token_b),
        ).status_code
        == 404
    )
    assert client.get("/api/v1/teams", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/teams/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_team_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/teams"]
    assert "post" in paths["/api/v1/teams"]
    assert "get" in paths["/api/v1/teams/{team_id}"]
    assert "patch" in paths["/api/v1/teams/{team_id}"]
    assert "delete" in paths["/api/v1/teams/{team_id}"]
    assert "get" in paths["/api/v1/teams/{team_id}/members"]
    assert "post" in paths["/api/v1/teams/{team_id}/members"]
    assert "delete" in paths["/api/v1/teams/{team_id}/members/{user_id}"]
