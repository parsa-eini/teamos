"""Feedback API tests: authoring, visibility through the reporting line, and isolation."""

from fastapi.testclient import TestClient
from httpx import Response

_PASSWORD = "correct-horse"


def _register(client: TestClient, *, email: str, organization_name: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PASSWORD,
            "first_name": email.split("@")[0].title(),
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


def _add_member(client: TestClient, token: str, *, email: str, role: str = "MEMBER") -> str:
    response = client.post(
        "/api/v1/organizations/current/members",
        headers=_auth(token),
        json={
            "email": email,
            "password": _PASSWORD,
            "first_name": email.split("@")[0].title(),
            "last_name": "User",
            "role": role,
        },
    )
    assert response.status_code == 201
    return str(response.json()["data"]["user_id"])


def _set_manager(client: TestClient, token: str, user_id: str, manager_id: str) -> None:
    response = client.patch(
        f"/api/v1/organizations/current/members/{user_id}",
        headers=_auth(token),
        json={"reports_to_user_id": manager_id},
    )
    assert response.status_code == 200


def _write(
    client: TestClient,
    token: str,
    *,
    subject_id: str,
    sentiment: str = "POSITIVE",
    body: str = "Shipped the migration cleanly.",
) -> Response:
    return client.post(
        "/api/v1/feedback",
        headers=_auth(token),
        json={"subject_id": subject_id, "sentiment": sentiment, "body": body},
    )


def _owner_id(client: TestClient, token: str) -> str:
    members = client.get(
        "/api/v1/organizations/current/members",
        headers=_auth(token),
    ).json()["data"]
    return str(next(member["user_id"] for member in members if member["role"] == "OWNER"))


def test_member_can_write_feedback_about_a_colleague(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    author_id = _add_member(client, owner_token, email="author@example.com")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    author_token = _login(client, "author@example.com")

    created = _write(client, author_token, subject_id=subject_id, sentiment="NEGATIVE")
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["subject_id"] == subject_id
    assert body["author_id"] == author_id
    assert body["sentiment"] == "NEGATIVE"

    listed = client.get("/api/v1/feedback", headers=_auth(author_token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [body["id"]]
    assert listed.json()["meta"]["total"] == 1


def test_feedback_rejects_blank_body_and_self_subject(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    author_token = _login(client, "subject@example.com")

    blank = _write(client, author_token, subject_id=_owner_id(client, owner_token), body="   ")
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "VALIDATION_ERROR"

    about_self = _write(client, author_token, subject_id=subject_id)
    assert about_self.status_code == 422
    assert about_self.json()["error"]["message"] == "You cannot write feedback about yourself"


def test_feedback_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/feedback").status_code == 401
    anonymous = client.post(
        "/api/v1/feedback",
        json={
            "subject_id": "11111111-1111-4111-8111-111111111111",
            "sentiment": "POSITIVE",
            "body": "Nice work",
        },
    )
    assert anonymous.status_code == 401


def test_the_subject_never_reads_feedback_about_themselves(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    _add_member(client, owner_token, email="author@example.com")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    author_token = _login(client, "author@example.com")
    subject_token = _login(client, "subject@example.com")

    feedback_id = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]

    listed = client.get("/api/v1/feedback", headers=_auth(subject_token))
    assert listed.json()["data"] == []
    assert listed.json()["meta"]["total"] == 0

    filtered = client.get(
        f"/api/v1/feedback?subject_id={subject_id}",
        headers=_auth(subject_token),
    )
    assert filtered.json()["data"] == []

    single = client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(subject_token))
    assert single.status_code == 404
    assert single.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_the_owner_does_not_see_feedback_written_about_themselves(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    _add_member(client, owner_token, email="author@example.com")
    author_token = _login(client, "author@example.com")

    feedback_id = _write(
        client,
        author_token,
        subject_id=_owner_id(client, owner_token),
        sentiment="NEGATIVE",
    ).json()["data"]["id"]

    listed = client.get("/api/v1/feedback", headers=_auth(owner_token))
    assert listed.json()["data"] == []
    single = client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(owner_token))
    assert single.status_code == 404


def test_managers_read_feedback_about_people_who_report_to_them(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    manager_id = _add_member(client, owner_token, email="manager@example.com", role="MANAGER")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    _add_member(client, owner_token, email="author@example.com")
    _add_member(client, owner_token, email="bystander@example.com")
    _set_manager(client, owner_token, subject_id, manager_id)

    author_token = _login(client, "author@example.com")
    feedback_id = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]

    manager_token = _login(client, "manager@example.com")
    listed = client.get("/api/v1/feedback", headers=_auth(manager_token))
    assert [item["id"] for item in listed.json()["data"]] == [feedback_id]
    single = client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(manager_token))
    assert single.status_code == 200

    # An unrelated member sees nothing, and neither does a manager further along the chain.
    bystander_token = _login(client, "bystander@example.com")
    assert client.get("/api/v1/feedback", headers=_auth(bystander_token)).json()["data"] == []
    assert (
        client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(bystander_token)).status_code
        == 404
    )


def test_visibility_follows_the_whole_reporting_chain(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    director_id = _add_member(client, owner_token, email="director@example.com", role="MANAGER")
    lead_id = _add_member(client, owner_token, email="lead@example.com", role="MANAGER")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    _add_member(client, owner_token, email="author@example.com")
    _set_manager(client, owner_token, lead_id, director_id)
    _set_manager(client, owner_token, subject_id, lead_id)

    author_token = _login(client, "author@example.com")
    feedback_id = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]

    director_token = _login(client, "director@example.com")
    listed = client.get("/api/v1/feedback", headers=_auth(director_token))
    assert [item["id"] for item in listed.json()["data"]] == [feedback_id]


def test_admins_see_all_feedback_and_can_filter(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    _add_member(client, owner_token, email="admin@example.com", role="ADMIN")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    other_id = _add_member(client, owner_token, email="other@example.com")
    _add_member(client, owner_token, email="author@example.com")

    author_token = _login(client, "author@example.com")
    positive = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]
    _write(client, author_token, subject_id=other_id, sentiment="NEGATIVE")

    admin_token = _login(client, "admin@example.com")
    all_items = client.get("/api/v1/feedback", headers=_auth(admin_token))
    assert all_items.json()["meta"]["total"] == 2

    by_subject = client.get(
        f"/api/v1/feedback?subject_id={subject_id}",
        headers=_auth(admin_token),
    )
    assert [item["id"] for item in by_subject.json()["data"]] == [positive]

    by_sentiment = client.get("/api/v1/feedback?sentiment=NEGATIVE", headers=_auth(admin_token))
    assert [item["sentiment"] for item in by_sentiment.json()["data"]] == ["NEGATIVE"]


def test_only_the_author_can_change_or_delete_feedback(client: TestClient) -> None:
    _register(client, email="owner@example.com", organization_name="Acme")
    owner_token = _login(client, "owner@example.com")
    subject_id = _add_member(client, owner_token, email="subject@example.com")
    _add_member(client, owner_token, email="author@example.com")
    author_token = _login(client, "author@example.com")

    feedback_id = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]

    updated = client.patch(
        f"/api/v1/feedback/{feedback_id}",
        headers=_auth(author_token),
        json={"body": "Revised note", "sentiment": "NEGATIVE"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["body"] == "Revised note"
    assert updated.json()["data"]["sentiment"] == "NEGATIVE"

    # An owner may read it but not rewrite someone else's words.
    forbidden = client.patch(
        f"/api/v1/feedback/{feedback_id}",
        headers=_auth(owner_token),
        json={"body": "Rewritten"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    # The subject cannot even tell that it exists.
    subject_token = _login(client, "subject@example.com")
    hidden = client.delete(f"/api/v1/feedback/{feedback_id}", headers=_auth(subject_token))
    assert hidden.status_code == 404

    deleted = client.delete(f"/api/v1/feedback/{feedback_id}", headers=_auth(author_token))
    assert deleted.status_code == 204
    gone = client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(author_token))
    assert gone.status_code == 404


def test_feedback_is_isolated_across_organizations(client: TestClient) -> None:
    _register(client, email="a-owner@example.com", organization_name="Acme")
    _register(client, email="b-owner@example.com", organization_name="Globex")
    token_a = _login(client, "a-owner@example.com")
    token_b = _login(client, "b-owner@example.com")

    subject_id = _add_member(client, token_a, email="a-subject@example.com")
    _add_member(client, token_a, email="a-author@example.com")
    author_token = _login(client, "a-author@example.com")
    feedback_id = _write(client, author_token, subject_id=subject_id).json()["data"]["id"]

    assert client.get("/api/v1/feedback", headers=_auth(token_b)).json()["data"] == []
    assert client.get(f"/api/v1/feedback/{feedback_id}", headers=_auth(token_b)).status_code == 404

    outsider = _write(client, token_b, subject_id=subject_id)
    assert outsider.status_code == 404
    assert outsider.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_feedback_endpoints_are_documented(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/feedback"]
    assert "post" in paths["/api/v1/feedback"]
    assert "get" in paths["/api/v1/feedback/{feedback_id}"]
    assert "patch" in paths["/api/v1/feedback/{feedback_id}"]
    assert "delete" in paths["/api/v1/feedback/{feedback_id}"]
