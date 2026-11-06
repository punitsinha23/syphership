import hashlib
import hmac
import json
import uuid

import httpx
import pytest
import redis
from fastapi import HTTPException

import github.service
import github.webhook
import services.deployment_services
from auth.security import encrypt_secret
from github import webhook
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import OAuthAccount, User
from services.queue import redis_client
from tests.conftest import TestingSessionLocal

SECRET = "test-secret"
BODY = b'{"ref": "refs/heads/main"}'
REPO_ID = 812345678
SHA = "a" * 40


def sign(body: bytes, secret: str = SECRET) -> str:
    """The header GitHub would send for this body."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_passes():
    assert webhook.verify_signature(SECRET, BODY, sign(BODY)) is True


def test_changed_body_fails():
    tampered = b'{"ref": "refs/heads/evil"}'

    assert webhook.verify_signature(SECRET, tampered, sign(BODY)) is False


def test_wrong_secret_fails():
    assert webhook.verify_signature(SECRET, BODY, sign(BODY, secret="guessed")) is False


def test_missing_header_fails():
    assert webhook.verify_signature(SECRET, BODY, None) is False
    assert webhook.verify_signature(SECRET, BODY, "") is False


def test_header_without_prefix_fails():
    bare_hex = sign(BODY).removeprefix("sha256=")

    assert webhook.verify_signature(SECRET, BODY, bare_hex) is False


@pytest.mark.parametrize("secret", ["", None])
def test_missing_secret_fails(secret):
    # With no secret, HMAC("", body) is something anyone can compute.
    assert webhook.verify_signature(secret, BODY, sign(BODY, secret="")) is False


@pytest.fixture
def delivery_ids():
    """Fresh delivery IDs; their Redis keys are deleted after the test."""
    ids = []

    def new_id() -> str:
        ids.append(f"test-{uuid.uuid4()}")
        return ids[-1]

    yield new_id
    for delivery_id in ids:
        for key in redis_client.scan_iter(f"github:delivery:*:{delivery_id}"):
            redis_client.delete(key)


@pytest.fixture
def published(monkeypatch):
    """Deployment IDs sent to the queue, without touching the real stream."""
    queued = []
    monkeypatch.setattr(services.deployment_services, "publish", queued.append)
    return queued


def make_project(repo_id=REPO_ID, branch="main", email="push@example.com", secret=SECRET, **fields) -> int:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, username=email)
            db.add(user)
            db.flush()
        project = Project(
            user_id=user.id,
            name="app",
            description="",
            repo_id=repo_id,
            repo_branch=branch,
            webhook_id=1,
            webhook_secret=encrypt_secret(secret) if secret else None,
            **fields,
        )
        db.add(project)
        db.commit()
        return project.id
    finally:
        db.close()


def webhook_headers(signature: str | None, delivery_id: str | None, event: str = "ping") -> dict:
    headers = {"X-GitHub-Event": event, "Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    if delivery_id is not None:
        headers["X-GitHub-Delivery"] = delivery_id
    return headers


def send(client, project_id, body, signature, delivery_id, event="ping"):
    return client.post(
        f"/github/webhook/{project_id}",
        content=body,
        headers=webhook_headers(signature, delivery_id, event),
    )


def test_is_new_delivery_only_once(delivery_ids):
    delivery_id = delivery_ids()

    assert webhook.is_new_delivery(1, delivery_id) is True
    assert webhook.is_new_delivery(1, delivery_id) is False


def test_same_delivery_id_is_new_for_another_project(delivery_ids):
    delivery_id = delivery_ids()

    assert webhook.is_new_delivery(1, delivery_id) is True
    assert webhook.is_new_delivery(2, delivery_id) is True


def test_endpoint_rejects_bad_signature(client, delivery_ids):
    project_id = make_project()

    assert send(client, project_id, BODY, sign(BODY, secret="guessed"), delivery_ids()).status_code == 401


def test_endpoint_rejects_missing_signature(client, delivery_ids):
    project_id = make_project()

    assert send(client, project_id, BODY, None, delivery_ids()).status_code == 401


def test_unknown_project_looks_like_a_bad_signature(client, delivery_ids):
    assert send(client, 999999, BODY, sign(BODY), delivery_ids()).status_code == 401


def test_project_without_webhook_rejects_everything(client, delivery_ids):
    project_id = make_project(secret=None)

    assert send(client, project_id, BODY, sign(BODY, secret=""), delivery_ids()).status_code == 401


def test_one_projects_secret_cannot_sign_for_another(client, delivery_ids, published):
    victim = make_project(secret="victim-secret")
    make_project(secret="attacker-secret")
    body = push_payload()

    response = send(client, victim, body, sign(body, secret="attacker-secret"), delivery_ids(), "push")

    assert response.status_code == 401
    assert deployments_of(victim) == []


def test_endpoint_accepts_signed_ping(client, delivery_ids):
    project_id = make_project()

    # content=, not json=: the exact bytes we signed must be the ones sent.
    response = send(client, project_id, BODY, sign(BODY), delivery_ids())

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_endpoint_ignores_repeated_delivery(client, delivery_ids):
    # A recorded request sent again still has a valid signature.
    project_id = make_project()
    delivery_id = delivery_ids()

    first = send(client, project_id, BODY, sign(BODY), delivery_id)
    second = send(client, project_id, BODY, sign(BODY), delivery_id)

    assert first.json() == {"ok": True}
    assert second.status_code == 200
    assert second.json() == {"ok": True, "duplicate": True}


def test_endpoint_ignores_missing_delivery_id(client):
    project_id = make_project()

    response = send(client, project_id, BODY, sign(BODY), None)

    assert response.json() == {"ok": True, "duplicate": True}


def test_rejected_request_does_not_use_up_delivery_id(client, delivery_ids):
    # Otherwise an attacker could block a real delivery by sending its ID first.
    project_id = make_project()
    delivery_id = delivery_ids()
    send(client, project_id, BODY, sign(BODY, secret="guessed"), delivery_id)

    response = send(client, project_id, BODY, sign(BODY), delivery_id)

    assert response.json() == {"ok": True}


def push_payload(ref="refs/heads/main", repo_id=REPO_ID, after=SHA, **extra) -> bytes:
    return json.dumps({"ref": ref, "after": after, "repository": {"id": repo_id}, **extra}).encode()


def send_push(client, project_id, delivery_id: str, body: bytes):
    return send(client, project_id, body, sign(body), delivery_id, "push")


def deployments_of(project_id: int) -> list[Deployment]:
    db = TestingSessionLocal()
    try:
        return db.query(Deployment).filter(Deployment.project_id == project_id).all()
    finally:
        db.close()


def test_push_queues_the_pushed_commit(client, delivery_ids, published):
    project_id = make_project()

    response = send_push(client, project_id, delivery_ids(), push_payload())

    assert response.status_code == 200
    [deployment] = deployments_of(project_id)
    assert deployment.commit_sha == SHA
    assert deployment.status == DeploymentStatus.QUEUED
    assert response.json() == {"ok": True, "deployments": [deployment.id]}
    assert published == [deployment.id]


@pytest.mark.parametrize(
    "body",
    [
        push_payload(ref="refs/heads/dev"),
        push_payload(repo_id=999),
        push_payload(ref="refs/tags/main"),
        push_payload(deleted=True),
        push_payload(after="-" * 40),
    ],
    ids=["other-branch", "other-repo", "tag", "deleted-branch", "invalid-sha"],
)
def test_push_that_does_not_apply_deploys_nothing(client, delivery_ids, published, body):
    project_id = make_project()

    response = send_push(client, project_id, delivery_ids(), body)

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_auto_deploy_off_deploys_nothing(client, delivery_ids, published):
    project_id = make_project(auto_deploy=False)

    response = send_push(client, project_id, delivery_ids(), push_payload())

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_push_while_building_is_skipped(client, delivery_ids, published):
    project_id = make_project()
    send_push(client, project_id, delivery_ids(), push_payload())

    response = send_push(client, project_id, delivery_ids(), push_payload())

    assert response.status_code == 200
    assert response.json()["deployments"] == []
    assert len(deployments_of(project_id)) == 1


def test_repeated_push_deploys_once(client, delivery_ids, published):
    project_id = make_project()
    delivery_id = delivery_ids()

    send_push(client, project_id, delivery_id, push_payload())
    send_push(client, project_id, delivery_id, push_payload())

    assert len(deployments_of(project_id)) == 1


def test_push_returns_503_when_queue_is_down(client, delivery_ids, monkeypatch):
    def queue_down(deployment_id):
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(services.deployment_services, "publish", queue_down)
    project_id = make_project()

    response = send_push(client, project_id, delivery_ids(), push_payload())

    assert response.status_code == 503
    [deployment] = deployments_of(project_id)
    assert deployment.status == DeploymentStatus.FAILED


# --- Creating webhooks on GitHub ---


@pytest.fixture
def fake_github(monkeypatch):
    """Records webhook calls and answers like GitHub."""
    calls = {"post": [], "delete": []}

    def fake_post(path, token, body):
        calls["post"].append((path, token, body))
        return {"id": 555}

    monkeypatch.setattr(github.webhook, "PUBLIC_API_URL", "https://api.example.com")
    monkeypatch.setattr(github.webhook, "github_post", fake_post)
    monkeypatch.setattr(github.webhook, "github_delete", lambda path, token: calls["delete"].append(path))
    monkeypatch.setattr(
        github.service,
        "github_get",
        # No commits, so these tests aren't affected by the first deployment.
        lambda path, token, params=None: [] if path.endswith("/commits") else {
            "id": 42 if "other" not in path else 43,
            "full_name": path.removeprefix("/repos/").split("/branches")[0],
            "default_branch": "main",
            "clone_url": "https://github.com/octo/app.git",
            "html_url": "https://github.com/octo/app",
            "private": False,
        },
    )
    return calls


@pytest.fixture
def github_user(auth_headers):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        db.add(OAuthAccount(user_id=user.id, provider="github", provider_user_id="1", access_token=encrypt_secret("gho_test")))
        db.commit()
    finally:
        db.close()
    return auth_headers


def new_project(client, headers, repo="octo/app"):
    return client.post("/projects/", headers=headers, json={"name": "App", "repo_full_name": repo})


def stored_project(project_id) -> Project:
    db = TestingSessionLocal()
    try:
        return db.query(Project).filter(Project.id == project_id).one()
    finally:
        db.close()


def test_linking_a_repo_creates_a_signed_webhook(client, github_user, fake_github):
    response = new_project(client, github_user)

    project_id = response.json()["id"]
    assert response.json()["webhook_active"] is True
    [(path, token, body)] = fake_github["post"]
    assert path == "/repos/octo/app/hooks"
    assert token == "gho_test"
    assert body["events"] == ["push"]
    assert body["config"]["url"] == f"https://api.example.com/github/webhook/{project_id}"
    assert body["config"]["content_type"] == "json"

    # The secret GitHub got is the one we can check signatures with, stored encrypted.
    project = stored_project(project_id)
    assert project.webhook_id == 555
    assert webhook.project_secret(project) == body["config"]["secret"]
    assert project.webhook_secret != body["config"]["secret"]


def test_every_project_gets_its_own_secret(client, github_user, fake_github):
    new_project(client, github_user)
    new_project(client, github_user)

    first, second = (call[2]["config"]["secret"] for call in fake_github["post"])
    assert first != second


def test_secret_is_not_in_the_api_response(client, github_user, fake_github):
    response = new_project(client, github_user)

    assert "webhook_secret" not in response.json()
    assert fake_github["post"][0][2]["config"]["secret"] not in response.text


@pytest.mark.parametrize(
    "error",
    [HTTPException(status_code=404, detail="no access"), httpx.ConnectError("GitHub is down")],
    ids=["no-admin-access", "github-down"],
)
def test_project_is_kept_when_webhook_fails(client, github_user, fake_github, monkeypatch, error):
    def refuse(path, token, body):
        raise error

    monkeypatch.setattr(github.webhook, "github_post", refuse)

    response = new_project(client, github_user)

    assert response.status_code == 200
    assert response.json()["webhook_active"] is False


def test_no_public_url_means_no_webhook(client, github_user, fake_github, monkeypatch):
    monkeypatch.setattr(github.webhook, "PUBLIC_API_URL", "")

    response = new_project(client, github_user)

    assert response.json()["webhook_active"] is False
    assert fake_github["post"] == []


def test_deleting_a_project_removes_its_webhook(client, github_user, fake_github):
    project_id = new_project(client, github_user).json()["id"]

    assert client.delete(f"/projects/{project_id}", headers=github_user).status_code == 200

    assert fake_github["delete"] == ["/repos/octo/app/hooks/555"]


def test_moving_to_another_repo_replaces_the_webhook(client, github_user, fake_github):
    project_id = new_project(client, github_user).json()["id"]

    response = client.put(
        f"/projects/{project_id}",
        headers=github_user,
        json={"name": "App", "repo_full_name": "octo/other"},
    )

    assert response.json()["webhook_active"] is True
    assert fake_github["delete"] == ["/repos/octo/app/hooks/555"]
    assert [call[0] for call in fake_github["post"]] == ["/repos/octo/app/hooks", "/repos/octo/other/hooks"]


def test_changing_branch_keeps_the_webhook(client, github_user, fake_github):
    project_id = new_project(client, github_user).json()["id"]

    client.put(f"/projects/{project_id}", headers=github_user, json={"name": "App", "repo_branch": "dev"})

    assert fake_github["delete"] == []
    assert len(fake_github["post"]) == 1


def test_existing_project_can_enable_webhook(client, github_user, fake_github, monkeypatch):
    monkeypatch.setattr(github.webhook, "PUBLIC_API_URL", "")
    project_id = new_project(client, github_user).json()["id"]
    monkeypatch.setattr(github.webhook, "PUBLIC_API_URL", "https://api.example.com")

    response = client.post(f"/projects/{project_id}/webhook", headers=github_user)

    assert response.status_code == 200
    assert response.json()["webhook_active"] is True


def test_enable_webhook_reports_failure(client, github_user, fake_github, monkeypatch):
    project_id = client.post("/projects/", headers=github_user, json={"name": "No repo"}).json()["id"]

    assert client.post(f"/projects/{project_id}/webhook", headers=github_user).status_code == 400


def test_cannot_enable_webhook_on_another_users_project(client, github_user, user2_headers, fake_github):
    project_id = new_project(client, github_user).json()["id"]

    assert client.post(f"/projects/{project_id}/webhook", headers=user2_headers).status_code == 404


def test_auto_deploy_can_be_turned_off(client, github_user, fake_github):
    project_id = new_project(client, github_user).json()["id"]

    response = client.put(f"/projects/{project_id}", headers=github_user, json={"name": "App", "auto_deploy": False})

    assert response.json()["auto_deploy"] is False


def test_saving_a_project_keeps_auto_deploy_setting(client, github_user, fake_github):
    project_id = new_project(client, github_user).json()["id"]
    client.put(f"/projects/{project_id}", headers=github_user, json={"name": "App", "auto_deploy": False})

    response = client.put(f"/projects/{project_id}", headers=github_user, json={"name": "Renamed"})

    assert response.json()["auto_deploy"] is False
