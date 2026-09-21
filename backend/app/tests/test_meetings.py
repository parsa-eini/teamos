"""Meeting workflow, type filtering, authorization, and organization-isolation tests."""

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


def _create_meeting(
    client: TestClient, token: str, member_id: str, **fields: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "member_id": member_id,
        "scheduled_on": "2026-08-07",
        **fields,
    }
    response = client.post("/api/v1/meetings", headers=_auth(token), json=payload)
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


def test_meeting_draft_submit_review_workflow(client: TestClient, app: FastAPI) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    created = client.post(
        "/api/v1/meetings",
        headers=_auth(owner_token),
        json={
            "member_id": str(member["id"]),
            "scheduled_on": "2026-08-07",
        },
    )
    assert created.status_code == 201
    meeting = created.json()["data"]
    assert meeting["status"] == "DRAFT"
    assert meeting["type"] == "CHECK_IN"
    assert meeting["scheduled_on"] == "2026-08-07"
    assert meeting["manager_id"] == str(owner["id"])
    assert meeting["member_id"] == str(member["id"])
    meeting_id = meeting["id"]

    drafted = client.patch(
        f"/api/v1/meetings/{meeting_id}",
        headers=_auth(member_token),
        json={"wins": "Shipped the API", "challenges": "Flaky tests", "next_steps": "Add coverage"},
    )
    assert drafted.status_code == 200
    assert drafted.json()["data"]["wins"] == "Shipped the API"

    submitted = client.patch(
        f"/api/v1/meetings/{meeting_id}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "SUBMITTED"

    reviewed = client.patch(
        f"/api/v1/meetings/{meeting_id}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED", "manager_notes": "Solid week"},
    )
    assert reviewed.status_code == 200
    body = reviewed.json()["data"]
    assert body["status"] == "REVIEWED"
    assert body["manager_notes"] == "Solid week"

    locked = client.patch(
        f"/api/v1/meetings/{meeting_id}",
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
    meeting = _create_meeting(client, owner_token, str(member["id"]))

    skip = client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED"},
    )
    assert skip.status_code == 422

    client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    reverse = client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(owner_token),
        json={"status": "DRAFT"},
    )
    assert reverse.status_code == 422


def test_create_meeting_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/meetings",
        json={
            "member_id": str(uuid4()),
            "scheduled_on": "2026-08-07",
        },
    )
    assert response.status_code == 401


def test_create_meeting_rejects_missing_date_and_self_as_member(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    undated = client.post(
        "/api/v1/meetings",
        headers=_auth(token),
        json={"member_id": str(owner["id"])},
    )
    assert undated.status_code == 422
    assert undated.json()["error"]["message"] == "scheduled_on: Field required"

    same = client.post(
        "/api/v1/meetings",
        headers=_auth(token),
        json={
            "member_id": str(owner["id"]),
            "scheduled_on": "2026-08-07",
        },
    )
    assert same.status_code == 422
    assert same.json()["error"]["message"] == "manager_id and member_id must be different"


def test_member_and_admin_cannot_create_meetings(client: TestClient, app: FastAPI) -> None:
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
        "scheduled_on": "2026-08-07",
    }
    assert (
        client.post("/api/v1/meetings", headers=_auth(member_token), json=payload).status_code
        == 403
    )
    assert (
        client.post("/api/v1/meetings", headers=_auth(admin_token), json=payload).status_code == 403
    )

    meeting = _create_meeting(client, owner_token, str(member["id"]))
    listed = client.get("/api/v1/meetings", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == meeting["id"]


def test_member_can_submit_own_meeting_only(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    other = _register(client, email="other@example.com", organization_name="Third")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    _move_user_to_owner_org(app, "owner@example.com", "other@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")

    meeting = _create_meeting(client, owner_token, str(member["id"]))
    other_meeting = _create_meeting(client, owner_token, str(other["id"]))

    listed = client.get("/api/v1/meetings", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == meeting["id"]
    assert (
        client.get(
            f"/api/v1/meetings/{other_meeting['id']}", headers=_auth(member_token)
        ).status_code
        == 403
    )

    submitted = client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "SUBMITTED"

    assert (
        client.patch(
            f"/api/v1/meetings/{other_meeting['id']}",
            headers=_auth(member_token),
            json={"status": "SUBMITTED"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=_auth(member_token),
            json={"status": "REVIEWED"},
        ).status_code
        == 403
    )


def test_manager_can_conduct_meeting_for_assigned_member(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    manager = _register(client, email="manager@example.com", organization_name="Other")
    member = _register(client, email="member@example.com", organization_name="Third")
    _move_user_to_owner_org(
        app, "owner@example.com", "manager@example.com", OrganizationRole.MANAGER
    )
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    manager_token = _login(client, "manager@example.com")
    member_token = _login(client, "member@example.com")

    created = _create_meeting(client, manager_token, str(member["id"]))
    assert created["manager_id"] == str(manager["id"])
    assert created["status"] == "DRAFT"

    submitted = client.patch(
        f"/api/v1/meetings/{created['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED", "wins": "Done"},
    )
    assert submitted.status_code == 200

    reviewed = client.patch(
        f"/api/v1/meetings/{created['id']}",
        headers=_auth(manager_token),
        json={"status": "REVIEWED", "manager_notes": "Nice"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["status"] == "REVIEWED"


def test_cannot_create_meeting_for_user_in_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    outsider = _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")

    response = client.post(
        "/api/v1/meetings",
        headers=_auth(token_a),
        json={
            "member_id": str(outsider["id"]),
            "scheduled_on": "2026-08-07",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cross_organization_meeting_access_is_not_found(client: TestClient, app: FastAPI) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Acme Member")
    _move_user_to_owner_org(app, "a@example.com", "member@example.com", OrganizationRole.MEMBER)
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    meeting = _create_meeting(client, token_a, str(member["id"]))

    assert (
        client.get(f"/api/v1/meetings/{meeting['id']}", headers=_auth(token_b)).status_code == 404
    )
    assert (
        client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=_auth(token_b),
            json={"status": "SUBMITTED"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/meetings", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/meetings/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_list_meetings_is_paginated(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "owner@example.com")
    for _ in range(3):
        _create_meeting(client, token, str(member["id"]))

    page = client.get("/api/v1/meetings?page=2&page_size=2", headers=_auth(token))
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1


def test_meeting_types_can_be_created_and_filtered(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "owner@example.com")
    member_id = str(member["id"])

    check_in = _create_meeting(client, token, member_id)
    one_on_one = _create_meeting(client, token, member_id, type="ONE_ON_ONE")
    review = _create_meeting(client, token, member_id, type="PERFORMANCE_REVIEW")
    assert check_in["type"] == "CHECK_IN"
    assert one_on_one["type"] == "ONE_ON_ONE"
    assert review["type"] == "PERFORMANCE_REVIEW"

    expected = {
        "CHECK_IN": check_in["id"],
        "ONE_ON_ONE": one_on_one["id"],
        "PERFORMANCE_REVIEW": review["id"],
    }
    for meeting_type, meeting_id in expected.items():
        listed = client.get(f"/api/v1/meetings?type={meeting_type}", headers=_auth(token))
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["data"]] == [meeting_id]

    assert client.get("/api/v1/meetings", headers=_auth(token)).json()["meta"]["total"] == 3


def test_unknown_meeting_type_is_rejected(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    token = _login(client, "owner@example.com")

    created = client.post(
        "/api/v1/meetings",
        headers=_auth(token),
        json={
            "member_id": str(member["id"]),
            "scheduled_on": "2026-08-07",
            "type": "STANDUP",
        },
    )
    assert created.status_code == 422
    assert created.json()["error"]["code"] == "VALIDATION_ERROR"

    filtered = client.get("/api/v1/meetings?type=STANDUP", headers=_auth(token))
    assert filtered.status_code == 422


def test_manager_can_reschedule_and_retype_a_draft(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    meeting = _create_meeting(client, owner_token, str(member["id"]))

    moved = client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(owner_token),
        json={"scheduled_on": "2026-09-01", "type": "PERFORMANCE_REVIEW"},
    )
    assert moved.status_code == 200
    assert moved.json()["data"]["scheduled_on"] == "2026-09-01"
    assert moved.json()["data"]["type"] == "PERFORMANCE_REVIEW"

    # The member records content but does not control scheduling.
    assert (
        client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=_auth(member_token),
            json={"scheduled_on": "2026-10-01"},
        ).status_code
        == 403
    )

    client.patch(
        f"/api/v1/meetings/{meeting['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert (
        client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=_auth(owner_token),
            json={"scheduled_on": "2026-11-01"},
        ).status_code
        == 403
    )


def test_performance_review_follows_the_same_workflow(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    review = _create_meeting(
        client,
        owner_token,
        str(member["id"]),
        type="PERFORMANCE_REVIEW",
    )

    submitted = client.patch(
        f"/api/v1/meetings/{review['id']}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED", "wins": "Grew the team"},
    )
    assert submitted.status_code == 200

    reviewed = client.patch(
        f"/api/v1/meetings/{review['id']}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED", "manager_notes": "Promote"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["status"] == "REVIEWED"


def test_meeting_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/meetings"]
    assert "post" in paths["/api/v1/meetings"]
    assert "get" in paths["/api/v1/meetings/{meeting_id}"]
    assert "patch" in paths["/api/v1/meetings/{meeting_id}"]
    assert "delete" not in paths.get("/api/v1/meetings/{meeting_id}", {})
