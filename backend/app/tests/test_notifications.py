"""Notification list, mark-read, generation, authorization, and isolation tests."""

from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notifications.models import NotificationType
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


def _create_project(client: TestClient, token: str, name: str) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=_auth(token),
        json={"name": name, "status": "ACTIVE"},
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["data"]["id"])


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


def _list_notifications(client: TestClient, token: str, **query: object) -> dict[str, Any]:
    response = client.get("/api/v1/notifications", headers=_auth(token), params=query)
    assert response.status_code == 200, response.json()
    return dict(response.json())


def test_new_user_has_an_empty_notification_list(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    response = client.get("/api/v1/notifications", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"] == {"page": 1, "page_size": 20, "total": 0}


def test_assigning_a_task_notifies_the_assignee_not_the_actor(
    client: TestClient, app: FastAPI
) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    project_id = _create_project(client, owner_token, "Launch")

    _create_task(
        client,
        owner_token,
        project_id,
        "Write spec",
        assignee_id=str(member["id"]),
    )
    _create_task(
        client,
        owner_token,
        project_id,
        "Self task",
        assignee_id=str(owner["id"]),
    )

    member_list = _list_notifications(client, member_token)
    assert member_list["meta"]["total"] == 1
    item = member_list["data"][0]
    assert item["type"] == NotificationType.TASK_ASSIGNED
    assert item["title"] == "Task assigned"
    assert item["message"] == 'You were assigned "Write spec"'
    assert item["is_read"] is False
    assert item["user_id"] == str(member["id"])

    owner_list = _list_notifications(client, owner_token)
    assert owner_list["data"] == []


def test_reassigning_a_task_notifies_the_new_assignee(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    project_id = _create_project(client, owner_token, "Launch")
    task = _create_task(client, owner_token, project_id, "Write spec")

    patched = client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=_auth(owner_token),
        json={"assignee_id": str(member["id"])},
    )
    assert patched.status_code == 200

    member_list = _list_notifications(client, member_token)
    assert member_list["meta"]["total"] == 1
    assert member_list["data"][0]["message"] == 'You were assigned "Write spec"'


def test_checkin_workflow_notifies_the_other_participant(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
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
    checkin_id = created.json()["data"]["id"]

    after_create = _list_notifications(client, member_token)
    assert after_create["meta"]["total"] == 1
    assert after_create["data"][0]["type"] == NotificationType.CHECKIN_CREATED
    assert _list_notifications(client, owner_token)["data"] == []

    submitted = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(member_token),
        json={"status": "SUBMITTED"},
    )
    assert submitted.status_code == 200
    owner_after_submit = _list_notifications(client, owner_token)
    assert owner_after_submit["meta"]["total"] == 1
    assert owner_after_submit["data"][0]["type"] == NotificationType.CHECKIN_SUBMITTED

    reviewed = client.patch(
        f"/api/v1/checkins/{checkin_id}",
        headers=_auth(owner_token),
        json={"status": "REVIEWED"},
    )
    assert reviewed.status_code == 200
    member_after_review = _list_notifications(client, member_token)
    types = {item["type"] for item in member_after_review["data"]}
    assert types == {
        NotificationType.CHECKIN_REVIEWED,
        NotificationType.CHECKIN_CREATED,
    }
    assert member_after_review["meta"]["total"] == 2


def test_member_can_mark_own_notification_read(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    project_id = _create_project(client, owner_token, "Launch")
    _create_task(client, owner_token, project_id, "Write spec", assignee_id=str(member["id"]))

    listed = _list_notifications(client, member_token)
    notification_id = listed["data"][0]["id"]

    marked = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(member_token),
    )
    assert marked.status_code == 200
    assert marked.json()["data"]["is_read"] is True
    assert marked.json()["data"]["id"] == notification_id

    again = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(member_token),
    )
    assert again.status_code == 200
    assert again.json()["data"]["is_read"] is True

    relisted = _list_notifications(client, member_token)
    assert relisted["data"][0]["is_read"] is True


def test_notifications_require_authentication(client: TestClient) -> None:
    listed = client.get("/api/v1/notifications")
    assert listed.status_code == 401

    marked = client.patch(f"/api/v1/notifications/{uuid4()}/read")
    assert marked.status_code == 401


def test_cannot_mark_another_users_notification_read(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    _register(client, email="outsider@example.com", organization_name="Beta")
    outsider_token = _login(client, "outsider@example.com")
    project_id = _create_project(client, owner_token, "Launch")
    _create_task(client, owner_token, project_id, "Write spec", assignee_id=str(member["id"]))
    notification_id = _list_notifications(client, member_token)["data"][0]["id"]

    owner_mark = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(owner_token),
    )
    outsider_mark = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(outsider_token),
    )
    missing = client.patch(
        f"/api/v1/notifications/{uuid4()}/read",
        headers=_auth(member_token),
    )
    assert owner_mark.status_code == 404
    assert owner_mark.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert outsider_mark.status_code == 404
    assert missing.status_code == 404
    assert _list_notifications(client, member_token)["data"][0]["is_read"] is False


def test_mark_read_rejects_invalid_notification_id(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    response = client.patch(
        "/api/v1/notifications/not-a-uuid/read",
        headers=_auth(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_notification_list_is_paginated(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    project_id = _create_project(client, owner_token, "Launch")
    for index in range(3):
        _create_task(
            client,
            owner_token,
            project_id,
            f"Task {index}",
            assignee_id=str(member["id"]),
        )

    page = client.get(
        "/api/v1/notifications?page=2&page_size=2",
        headers=_auth(member_token),
    )
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1


def test_notification_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/notifications"]
    assert "patch" in paths["/api/v1/notifications/{notification_id}/read"]
    assert "post" not in paths.get("/api/v1/notifications", {})
    assert "delete" not in paths.get("/api/v1/notifications/{notification_id}", {})
