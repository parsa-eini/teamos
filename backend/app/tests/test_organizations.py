"""Organization API and isolation tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Organization, OrganizationMembership, OrganizationRole
from app.modules.users.models import User

_PASSWORD = "correct-horse"


def _register(
    client: TestClient,
    *,
    email: str,
    organization_name: str,
    first_name: str = "Alex",
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PASSWORD,
            "first_name": first_name,
            "last_name": "User",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201


def _login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["data"]["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_organization_and_owner_membership_atomically(
    client: TestClient,
    app: FastAPI,
) -> None:
    _register(client, email="owner@example.com", organization_name="Acme Engineering")
    token = _login(client, "owner@example.com")

    session: Session = app.state.session_factory()
    try:
        user = session.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        organization = session.scalar(
            select(Organization).where(Organization.slug == "acme-engineering")
        )
        assert organization is not None
        assert organization.name == "Acme Engineering"
        membership = session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization.id,
            )
        )
        assert membership is not None
        assert membership.role == OrganizationRole.OWNER
    finally:
        session.close()

    response = client.get("/api/v1/organizations/current", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Acme Engineering"
    assert body["slug"] == "acme-engineering"


def test_register_requires_organization_name(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": _PASSWORD,
            "first_name": "Alex",
            "last_name": "User",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_organization_names_get_distinct_slugs(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Acme")

    first = client.get(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "a@example.com")),
    ).json()["data"]
    second = client.get(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "b@example.com")),
    ).json()["data"]

    assert first["name"] == "Acme"
    assert second["name"] == "Acme"
    assert first["slug"] == "acme"
    assert second["slug"].startswith("acme-")
    assert first["slug"] != second["slug"]
    assert first["id"] != second["id"]


def test_current_organization_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/organizations/current")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

    members = client.get("/api/v1/organizations/current/members")
    assert members.status_code == 401
    assert members.json()["error"]["code"] == "UNAUTHORIZED"


def test_current_organization_requires_membership(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    session: Session = app.state.session_factory()
    try:
        session.execute(delete(OrganizationMembership))
        session.commit()
    finally:
        session.close()

    response = client.get(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "owner@example.com")),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


def test_owner_can_update_current_organization(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    response = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(token),
        json={"name": "Acme Labs", "slug": "acme-labs"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Acme Labs"
    assert body["slug"] == "acme-labs"

    reread = client.get("/api/v1/organizations/current", headers=_auth(token))
    assert reread.json()["data"]["name"] == "Acme Labs"


def test_member_cannot_update_current_organization(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="member@example.com", organization_name="Other Co")

    session: Session = app.state.session_factory()
    try:
        owner = session.scalar(select(User).where(User.email == "owner@example.com"))
        member = session.scalar(select(User).where(User.email == "member@example.com"))
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
        member_membership.role = OrganizationRole.MEMBER
        session.commit()
    finally:
        session.close()

    response = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "member@example.com")),
        json={"name": "Hijacked"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_update_rejects_invalid_slug(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    response = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "owner@example.com")),
        json={"slug": "Not Valid"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_rejects_duplicate_slug(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")

    response = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(_login(client, "b@example.com")),
        json={"slug": "acme"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_ALREADY_EXISTS"


def test_cross_organization_isolation(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")

    org_a = client.get("/api/v1/organizations/current", headers=_auth(token_a)).json()["data"]
    org_b = client.get("/api/v1/organizations/current", headers=_auth(token_b)).json()["data"]

    assert org_a["id"] != org_b["id"]
    assert org_a["slug"] == "acme"
    assert org_b["slug"] == "globex"

    patched = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(token_a),
        json={"name": "Acme Updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["id"] == org_a["id"]

    still_b = client.get("/api/v1/organizations/current", headers=_auth(token_b)).json()["data"]
    assert still_b["id"] == org_b["id"]
    assert still_b["name"] == "Globex"

    members_a = client.get("/api/v1/organizations/current/members", headers=_auth(token_a))
    members_b = client.get("/api/v1/organizations/current/members", headers=_auth(token_b))
    assert members_a.status_code == 200
    assert members_b.status_code == 200
    emails_a = {member["email"] for member in members_a.json()["data"]}
    emails_b = {member["email"] for member in members_b.json()["data"]}
    assert emails_a == {"a@example.com"}
    assert emails_b == {"b@example.com"}

    # Client-supplied organization ids are ignored; context comes from membership only.
    ignored = client.patch(
        "/api/v1/organizations/current",
        headers=_auth(token_b),
        json={"name": "Globex Updated", "id": org_a["id"]},
    )
    assert ignored.status_code == 200
    assert ignored.json()["data"]["id"] == org_b["id"]
    assert ignored.json()["data"]["name"] == "Globex Updated"

    unchanged_a = client.get("/api/v1/organizations/current", headers=_auth(token_a)).json()["data"]
    assert unchanged_a["id"] == org_a["id"]
    assert unchanged_a["name"] == "Acme Updated"


def test_organization_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/organizations/current"]
    assert "patch" in paths["/api/v1/organizations/current"]
    assert "get" in paths["/api/v1/organizations/current/members"]
    assert "post" in paths["/api/v1/organizations/current/members"]


def test_owner_can_list_and_create_members(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")

    created = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(token),
        json={
            "email": "sara@example.com",
            "password": "member-pass",
            "first_name": "Sara",
            "last_name": "Nouri",
            "role": "MEMBER",
        },
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["email"] == "sara@example.com"
    assert body["first_name"] == "Sara"
    assert body["role"] == "MEMBER"
    assert "password" not in body
    assert "password_hash" not in body

    listed = client.get("/api/v1/organizations/current/members", headers=_auth(token))
    assert listed.status_code == 200
    emails = {member["email"] for member in listed.json()["data"]}
    assert emails == {"owner@example.com", "sara@example.com"}
    assert listed.json()["meta"]["total"] == 2

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "sara@example.com", "password": "member-pass"},
    )
    assert login.status_code == 200
    sara_org = client.get(
        "/api/v1/organizations/current",
        headers=_auth(login.json()["data"]["access_token"]),
    )
    owner_org = client.get("/api/v1/organizations/current", headers=_auth(token))
    assert sara_org.json()["data"]["id"] == owner_org.json()["data"]["id"]


def test_create_member_rejects_duplicate_email(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    token = _login(client, "owner@example.com")
    client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(token),
        json={
            "email": "sara@example.com",
            "password": "member-pass",
            "first_name": "Sara",
            "last_name": "Nouri",
        },
    )
    duplicate = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(token),
        json={
            "email": "Sara@example.com",
            "password": "member-pass",
            "first_name": "Sara",
            "last_name": "Nouri",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RESOURCE_ALREADY_EXISTS"


def test_create_member_rejects_owner_role(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    response = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(_login(client, "owner@example.com")),
        json={
            "email": "other@example.com",
            "password": "member-pass",
            "first_name": "Other",
            "last_name": "User",
            "role": "OWNER",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_member_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/organizations/current/members",
        json={
            "email": "sara@example.com",
            "password": "member-pass",
            "first_name": "Sara",
            "last_name": "Nouri",
        },
    )
    assert response.status_code == 401


def test_member_cannot_create_organization_members(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(owner_token),
        json={
            "email": "member@example.com",
            "password": _PASSWORD,
            "first_name": "Mem",
            "last_name": "Ber",
            "role": "MEMBER",
        },
    )
    response = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(_login(client, "member@example.com")),
        json={
            "email": "another@example.com",
            "password": "member-pass",
            "first_name": "A",
            "last_name": "Nother",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_create_member_is_isolated_across_organizations(client: TestClient) -> None:
    _register(client, email="a@example.com", organization_name="Acme")
    _register(client, email="b@example.com", organization_name="Globex")
    token_a = _login(client, "a@example.com")
    token_b = _login(client, "b@example.com")

    client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(token_a),
        json={
            "email": "acme-member@example.com",
            "password": "member-pass",
            "first_name": "Acme",
            "last_name": "Member",
        },
    )

    listed_b = client.get("/api/v1/organizations/current/members", headers=_auth(token_b))
    emails_b = {member["email"] for member in listed_b.json()["data"]}
    assert "acme-member@example.com" not in emails_b
    assert emails_b == {"b@example.com"}


def test_admin_can_create_organization_members(client: TestClient, app: FastAPI) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    _register(client, email="admin@example.com", organization_name="Other Co")
    session: Session = app.state.session_factory()
    try:
        owner = session.scalar(select(User).where(User.email == "owner@example.com"))
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert owner is not None
        assert admin is not None
        owner_membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == owner.id)
        )
        admin_membership = session.scalar(
            select(OrganizationMembership).where(OrganizationMembership.user_id == admin.id)
        )
        assert owner_membership is not None
        assert admin_membership is not None
        admin_membership.organization_id = owner_membership.organization_id
        admin_membership.role = OrganizationRole.ADMIN
        session.commit()
    finally:
        session.close()

    created = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(_login(client, "admin@example.com")),
        json={
            "email": "new-member@example.com",
            "password": "member-pass",
            "first_name": "New",
            "last_name": "Member",
            "role": "MEMBER",
        },
    )
    assert created.status_code == 201
    listed = client.get(
        "/api/v1/organizations/current/members",
        headers=_auth(_login(client, "admin@example.com")),
    )
    emails = {member["email"] for member in listed.json()["data"]}
    assert "new-member@example.com" in emails
