"""Check-in workflow, authorization, and organization-isolation tests."""

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


def _create_checkin(
    client: TestClient, token: str, member_id: str, **fields: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "member_id": member_id,
        "period_start": "2026-08-01",
        "period_end": "2026-08-07",
        **fields,
    }
    response = client.post("/api/v1/checkins", headers=_auth(token), json=payload)
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


def test_checkin_draft_submit_review_workflow(client: TestClient, app: FastAPI) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    created = client.post(
        "/api/v1/checkins",
        headers=_auth(owner_token),
        json={
            "member_id": str(member["id"]),
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
        },
    )
    assert created.status_code == 201
    checkin = created.json()["data"]
    assert checkin["status"] == "DRAFT"
    assert checkin["manager_id"] == str(owner["id"])
    assert checkin["member_id"] == str(member["id"])
    checkin_id = checkin["id"]

    drafted = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(member_token),
        json={"wins": "Shipped the API", "challenges": "Flaky tests", "next_steps": "Add coverage"},
    )
    assert drafted.status_code == 200
    assert drafted.json()["data"]["wins"] == "Shipped the API"

    submitted = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "SUBMITTED"

    reviewed = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED", "manager_notes": "Solid week"},
    )
    assert reviewed.status_code == 200
    body = reviewed.json()["data"]
    assert body["status"] == "REVIEWED"
    assert body["manager_notes"] == "Solid week"

    locked = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(owner_token),
        json={"manager_notes": "Too late"},
    )
    assert locked.status_code == 422
    assert locked.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_status_transitions_are_rejected(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    checkin = _create_checkin(client, owner_token, str(member["id"]))

    skip = client.patch(
        f"/api/v1/checkins/{checkin['id']}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED"},
    )
    assert skip.status_code == 422

    client.patch(
        f"/api/v1/checkins/{checkin['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    reverse = client.patch(
        f"/api/v1/checkins/{checkin['id']}",
        headers=_auth(owner_token),
        json={"status": "DRAFT"},
    )
    assert reverse.status_code == 422


def test_create_checkin_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/checkins",
        json={
            "member_id": str(uuid4()),
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
        },
    )
    assert response.status_code == 401


def test_create_checkin_rejects_invalid_period_and_self_as_member(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    dates = client.post(
        "/api/v1/checkins",
        headers=_auth(token),
        json={
            "member_id": str(owner["id"]),
            "period_start": "2026-08-07",
            "period_end": "2026-08-01",
        },
    )
    assert dates.status_code == 422

    same = client.post(
        "/api/v1/checkins",
        headers=_auth(token),
        json={
            "member_id": str(owner["id"]),
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
        },
    )
    assert same.status_code == 422


def test_member_and_admin_cannot_create_checkins(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _register(client, email="admin@example.com", organization_name="Third")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    _move_user_to_owner_org(app, "owner@example.com", "admin@example.com", OrganizationRole.ADMIN)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    admin_token = _login(client, "admin@example.com")

    payload = {
        "member_id": str(member["id"]),
        "period_start": "2026-08-01",
        "period_end": "2026-08-07",
    }
    assert (
        client.post("/api/v1/checkins", headers=_auth(member_token), json=payload).status_code
        == 403
    )
    assert (
        client.post("/api/v1/checkins", headers=_auth(admin_token), json=payload).status_code == 403
    )

    checkin = _create_checkin(client, owner_token, str(member["id"]))
    listed = client.get("/api/v1/checkins", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == checkin["id"]


def test_member_can_submit_own_checkin_only(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    other = _register(client, email="other@example.com", organization_name="Third")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    _move_user_to_owner_org(app, "owner@example.com", "other@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    checkin = _create_checkin(client, owner_token, str(member["id"]))
    other_checkin = _create_checkin(client, owner_token, str(other["id"]))

    listed = client.get("/api/v1/checkins", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == checkin["id"]
    assert (
        client.get(
            f"/api/v1/checkins/{other_checkin['id']}", headers=_auth(member_token)
        ).status_code
        == 403
    )

    submitted = client.patch(
        f"/api/v1/checkins/{checkin['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "SUBMITTED"

    assert (
        client.patch(
            f"/api/v1/checkins/{other_checkin['id']}",
            headers=_auth(member_token),
            json={"status": "SUBMITTED"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/checkins/{checkin['id']}",
            headers=_auth(member_token),
            json={"status": "REVIEWED"},
        ).status_code
        == 403
    )


def test_manager_can_conduct_checkin_for_assigned_member(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    manager = _register(client, email="manager@example.com", organization_name="Other")
    member = _register(client, email="member@example.com", organization_name="Third")
    _move_user_to_owner_org(
        app, "owner@example.com", "manager@example.com", OrganizationRole.MANAGER
    )
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    manager_token = _login(client, "manager@example.com")
    member_token = _login(client, "member@example.com")

    created = _create_checkin(client, manager_token, str(member["id"]))
    assert created["manager_id"] == str(manager["id"])
    assert created["status"] == "DRAFT"

    submitted = client.patch(
        f"/api/v1/checkins/{created['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED", "wins": "Done"},
    )
    assert submitted.status_code == 200

    reviewed = client.patch(
        f"/api/v1/checkins/{created['id']}",
        headers=_auth(manager_token),
        json={"status": "REVIEWED", "manager_notes": "Nice"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["status"] == "REVIEWED"


def test_cannot_create_checkin_for_user_in_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    outsider = _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")

    response = client.post(
        "/api/v1/checkins",
        headers=_auth(token_a),
        json={
            "member_id": str(outsider["id"]),
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cross_organization_checkin_access_is_not_found(client: TestClient, app: FastAPI) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Acme Member")
    _move_user_to_owner_org(app, "a@example.com", "member@example.com", OrganizationRole.MEMBER)
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    checkin = _create_checkin(client, token_a, str(member["id"]))

    assert (
        client.get(f"/api/v1/checkins/{checkin['id']}", headers=_auth(token_b)).status_code == 404
    )
    assert (
        client.patch(
            f"/api/v1/checkins/{checkin['id']}",
            headers=_auth(token_b),
            json={"status": "SUBMITTED"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/checkins", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/checkins/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_list_checkins_is_paginated(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "owner@example.com")
    for _ in range(3):
        _create_checkin(client, token, str(member["id"]))

    page = client.get("/api/v1/checkins?page=2&page_size=2", headers=_auth(token))
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1


def test_checkin_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/checkins"]
    assert "post" in paths["/api/v1/checkins"]
    assert "get" in paths["/api/v1/checkins/{checkin_id}"]
    assert "patch" in paths["/api/v1/checkins/{checkin_id}"]
    assert "delete" not in paths.get("/api/v1/checkins/{checkin_id}", {})
