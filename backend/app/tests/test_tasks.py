"""Task CRUD, assignment, filtering, and organization-isolation tests."""

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


def _create_project(client: TestClient, token: str, name: str, **fields: object) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=_auth(token),
        json={"name": name, **fields},
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


def test_owner_can_crud_task(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    project_id = _create_project(client, token, "Launch")

    created = client.post(
        "/api/v1/tasks",
        headers=_auth(token),
        json={
            "project_id": project_id,
            "title": "Write spec",
            "description": "Draft the RFC",
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "assignee_id": str(owner["id"]),
            "due_date": "2026-09-15",
        },
    )
    assert created.status_code == 201
    task = created.json()["data"]
    assert task["title"] == "Write spec"
    assert task["description"] == "Draft the RFC"
    assert task["status"] == "IN_PROGRESS"
    assert task["priority"] == "HIGH"
    assert task["assignee_id"] == str(owner["id"])
    assert task["project_id"] == project_id
    assert task["due_date"] == "2026-09-15"
    assert task["created_by"] == str(owner["id"])
    task_id = task["id"]

    listed = client.get("/api/v1/tasks", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["meta"] == {"page": 1, "page_size": 20, "total": 1}
    assert listed.json()["data"][0]["id"] == task_id

    fetched = client.get(f"/api/v1/tasks/{task_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["title"] == "Write spec"

    patched = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=_auth(token),
        json={"title": "Write spec v2", "status": "DONE", "assignee_id": None, "description": None},
    )
    assert patched.status_code == 200
    body = patched.json()["data"]
    assert body["title"] == "Write spec v2"
    assert body["status"] == "DONE"
    assert body["assignee_id"] is None
    assert body["description"] is None

    deleted = client.delete(f"/api/v1/tasks/{task_id}", headers=_auth(token))
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}", headers=_auth(token)).status_code == 404


def test_create_task_defaults_status_and_priority(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    project_id = _create_project(client, token, "Launch")
    task = _create_task(client, token, project_id, "Blank slate")
    assert task["status"] == "TODO"
    assert task["priority"] == "MEDIUM"
    assert task["assignee_id"] is None


def test_list_tasks_is_paginated_and_filterable(client: TestClient) -> None:
    owner = _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    project_a = _create_project(client, token, "Alpha")
    project_b = _create_project(client, token, "Beta")
    owner_id = str(owner["id"])
    _create_task(client, token, project_a, "One", status="TODO", priority="LOW")
    _create_task(
        client,
        token,
        project_a,
        "Two",
        status="IN_PROGRESS",
        priority="HIGH",
        assignee_id=owner_id,
    )
    _create_task(
        client,
        token,
        project_b,
        "Three",
        status="IN_PROGRESS",
        priority="HIGH",
        assignee_id=owner_id,
    )

    page = client.get("/api/v1/tasks?page=2&page_size=2", headers=_auth(token))
    assert page.status_code == 200
    assert page.json()["meta"] == {"page": 2, "page_size": 2, "total": 3}
    assert len(page.json()["data"]) == 1

    by_status = client.get("/api/v1/tasks?status=IN_PROGRESS", headers=_auth(token))
    assert {item["title"] for item in by_status.json()["data"]} == {"Two", "Three"}

    by_priority = client.get("/api/v1/tasks?priority=HIGH", headers=_auth(token))
    assert by_priority.json()["meta"]["total"] == 2

    by_assignee = client.get(f"/api/v1/tasks?assignee_id={owner_id}", headers=_auth(token))
    assert by_assignee.json()["meta"]["total"] == 2

    by_project = client.get(f"/api/v1/tasks?project_id={project_b}", headers=_auth(token))
    assert [item["title"] for item in by_project.json()["data"]] == ["Three"]

    combined = client.get(
        f"/api/v1/tasks?status=IN_PROGRESS&priority=HIGH&assignee_id={owner_id}&project_id={project_a}",
        headers=_auth(token),
    )
    assert combined.json()["meta"]["total"] == 1
    assert combined.json()["data"][0]["title"] == "Two"


def test_create_task_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json={"project_id": str(uuid4()), "title": "Nope"})
    assert response.status_code == 401


def test_create_task_rejects_blank_title_and_missing_project(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    project_id = _create_project(client, token, "Launch")

    blank = client.post(
        "/api/v1/tasks",
        headers=_auth(token),
        json={"project_id": project_id, "title": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "VALIDATION_ERROR"

    missing = client.post(
        "/api/v1/tasks",
        headers=_auth(token),
        json={"project_id": str(uuid4()), "title": "Orphan"},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cannot_assign_user_from_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    outsider = _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    project_id = _create_project(client, token_a, "Launch")

    response = client.post(
        "/api/v1/tasks",
        headers=_auth(token_a),
        json={
            "project_id": project_id,
            "title": "Secret",
            "assignee_id": str(outsider["id"]),
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cannot_create_task_on_project_in_another_organization(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    foreign_project = _create_project(client, token_b, "Globex Launch")

    response = client.post(
        "/api/v1/tasks",
        headers=_auth(token_a),
        json={"project_id": foreign_project, "title": "Steal"},
    )
    assert response.status_code == 404


def test_member_can_update_own_task_only(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    member = _register(client, email="member@example.com", organization_name="Other")
    _move_user_to_owner_org(app, "owner@example.com", "member@example.com", OrganizationRole.MEMBER)
    owner_token = _login(client, "owner@example.com")
    member_token = _login(client, "member@example.com")
    team_id = _create_team(client, owner_token, "Platform")
    client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=_auth(owner_token),
        json={"user_id": str(member["id"])},
    )
    project_id = _create_project(client, owner_token, "Launch", team_id=team_id)
    assigned = _create_task(
        client,
        owner_token,
        project_id,
        "Mine",
        assignee_id=str(member["id"]),
    )
    other = _create_task(client, owner_token, project_id, "Theirs")

    assert (
        client.post(
            "/api/v1/tasks",
            headers=_auth(member_token),
            json={"project_id": project_id, "title": "Nope"},
        ).status_code
        == 403
    )

    listed = client.get("/api/v1/tasks", headers=_auth(member_token))
    assert listed.json()["meta"]["total"] == 1
    assert listed.json()["data"][0]["id"] == assigned["id"]

    own = client.get(f"/api/v1/tasks/{assigned['id']}", headers=_auth(member_token))
    assert own.status_code == 200
    assert (
        client.get(f"/api/v1/tasks/{other['id']}", headers=_auth(member_token)).status_code == 403
    )

    updated = client.patch(
        f"/api/v1/tasks/{assigned['id']}",
        headers=_auth(member_token),
        json={"status": "IN_PROGRESS", "title": "Mine now"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "IN_PROGRESS"

    reassign = client.patch(
        f"/api/v1/tasks/{assigned['id']}",
        headers=_auth(member_token),
        json={"assignee_id": str(uuid4())},
    )
    assert reassign.status_code == 403
    assert (
        client.patch(
            f"/api/v1/tasks/{other['id']}",
            headers=_auth(member_token),
            json={"status": "DONE"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/tasks/{assigned['id']}", headers=_auth(member_token)).status_code
        == 403
    )


def test_manager_can_assign_on_visible_projects_only(client: TestClient, app: FastAPI) -> None:
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
    visible_project = _create_project(client, owner_token, "Visible", team_id=assigned_team)
    hidden_project = _create_project(client, owner_token, "Hidden", team_id=other_team)
    org_wide = _create_project(client, owner_token, "Org Wide")

    created = client.post(
        "/api/v1/tasks",
        headers=_auth(manager_token),
        json={
            "project_id": visible_project,
            "title": "Do it",
            "assignee_id": str(manager["id"]),
        },
    )
    assert created.status_code == 201

    org_task = client.post(
        "/api/v1/tasks",
        headers=_auth(manager_token),
        json={"project_id": org_wide, "title": "Org task"},
    )
    assert org_task.status_code == 201

    hidden = client.post(
        "/api/v1/tasks",
        headers=_auth(manager_token),
        json={"project_id": hidden_project, "title": "Nope"},
    )
    assert hidden.status_code == 403

    hidden_task = _create_task(client, owner_token, hidden_project, "Secret")
    listed = client.get("/api/v1/tasks", headers=_auth(manager_token))
    titles = {item["title"] for item in listed.json()["data"]}
    assert "Do it" in titles
    assert "Org task" in titles
    assert "Secret" not in titles
    assert (
        client.get(f"/api/v1/tasks/{hidden_task['id']}", headers=_auth(manager_token)).status_code
        == 403
    )


def test_cross_organization_task_access_is_not_found(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")
    project_id = _create_project(client, token_a, "Launch")
    task = _create_task(client, token_a, project_id, "Write spec")

    assert client.get(f"/api/v1/tasks/{task['id']}", headers=_auth(token_b)).status_code == 404
    assert (
        client.patch(
            f"/api/v1/tasks/{task['id']}",
            headers=_auth(token_b),
            json={"title": "Stolen"},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=_auth(token_b)).status_code == 404
    assert client.get("/api/v1/tasks", headers=_auth(token_b)).json()["data"] == []
    missing = client.get(f"/api/v1/tasks/{uuid4()}", headers=_auth(token_a))
    assert missing.status_code == 404


def test_task_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/tasks"]
    assert "post" in paths["/api/v1/tasks"]
    assert "get" in paths["/api/v1/tasks/{task_id}"]
    assert "patch" in paths["/api/v1/tasks/{task_id}"]
    assert "delete" in paths["/api/v1/tasks/{task_id}"]
