import hashlib
import hmac
import json
import uuid

import pytest
import redis

import services.deployment_services
from github import webhook
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import User
from services.queue import redis_client
from tests.conftest import TestingSessionLocal

SECRET = "test-secret"
BODY = b'{"ref": "refs/heads/main"}'


def sign(body: bytes, secret: str = SECRET) -> str:
    """The header GitHub would send for this body."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    """Every test starts with a known secret, whatever is in .env."""
    monkeypatch.setattr(webhook, "WEBHOOK_SECRET", SECRET)


def test_valid_signature_passes():
    assert webhook.verify_signature(BODY, sign(BODY)) is True


def test_changed_body_fails():
    tampered = b'{"ref": "refs/heads/evil"}'

    assert webhook.verify_signature(tampered, sign(BODY)) is False


def test_wrong_secret_fails():
    assert webhook.verify_signature(BODY, sign(BODY, secret="guessed")) is False


def test_missing_header_fails():
    assert webhook.verify_signature(BODY, None) is False
    assert webhook.verify_signature(BODY, "") is False


def test_header_without_prefix_fails():
    bare_hex = sign(BODY).removeprefix("sha256=")

    assert webhook.verify_signature(BODY, bare_hex) is False


def test_empty_secret_fails(monkeypatch):
    # With no secret set, HMAC("", body) is something anyone can compute.
    monkeypatch.setattr(webhook, "WEBHOOK_SECRET", "")

    assert webhook.verify_signature(BODY, sign(BODY, secret="")) is False


@pytest.fixture
def delivery_ids():
    """Fresh delivery IDs; their Redis keys are deleted after the test."""
    ids = []

    def new_id() -> str:
        ids.append(f"test-{uuid.uuid4()}")
        return ids[-1]

    yield new_id
    for delivery_id in ids:
        redis_client.delete(f"github:delivery:{delivery_id}")


def webhook_headers(signature: str | None, delivery_id: str | None, event: str = "ping") -> dict:
    headers = {"X-GitHub-Event": event, "Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    if delivery_id is not None:
        headers["X-GitHub-Delivery"] = delivery_id
    return headers


def test_is_new_delivery_only_once(delivery_ids):
    delivery_id = delivery_ids()

    assert webhook.is_new_delivery(delivery_id) is True
    assert webhook.is_new_delivery(delivery_id) is False


def test_endpoint_rejects_bad_signature(client, delivery_ids):
    headers = webhook_headers(sign(BODY, secret="guessed"), delivery_ids())
    response = client.post("/github/webhook", content=BODY, headers=headers)

    assert response.status_code == 401


def test_endpoint_rejects_missing_signature(client, delivery_ids):
    response = client.post("/github/webhook", content=BODY, headers=webhook_headers(None, delivery_ids()))

    assert response.status_code == 401


def test_endpoint_accepts_signed_ping(client, delivery_ids):
    # content=, not json=: the exact bytes we signed must be the ones sent.
    response = client.post("/github/webhook", content=BODY, headers=webhook_headers(sign(BODY), delivery_ids()))

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_endpoint_ignores_repeated_delivery(client, delivery_ids):
    # A recorded request sent again still has a valid signature.
    headers = webhook_headers(sign(BODY), delivery_ids())

    first = client.post("/github/webhook", content=BODY, headers=headers)
    second = client.post("/github/webhook", content=BODY, headers=headers)

    assert first.json() == {"ok": True}
    assert second.status_code == 200
    assert second.json() == {"ok": True, "duplicate": True}


def test_endpoint_ignores_missing_delivery_id(client):
    response = client.post("/github/webhook", content=BODY, headers=webhook_headers(sign(BODY), None))

    assert response.json() == {"ok": True, "duplicate": True}


def test_rejected_request_does_not_use_up_delivery_id(client, delivery_ids):
    # Otherwise an attacker could block a real delivery by sending its ID first.
    delivery_id = delivery_ids()
    client.post("/github/webhook", content=BODY, headers=webhook_headers(sign(BODY, secret="guessed"), delivery_id))

    response = client.post("/github/webhook", content=BODY, headers=webhook_headers(sign(BODY), delivery_id))

    assert response.json() == {"ok": True}


REPO_ID = 812345678
SHA = "a" * 40


@pytest.fixture
def published(monkeypatch):
    """Deployment IDs sent to the queue, without touching the real stream."""
    queued = []
    monkeypatch.setattr(services.deployment_services, "publish", queued.append)
    return queued


def make_project(repo_id=REPO_ID, branch="main", email="push@example.com") -> int:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, username=email)
            db.add(user)
            db.flush()
        project = Project(user_id=user.id, name="app", description="", repo_id=repo_id, repo_branch=branch)
        db.add(project)
        db.commit()
        return project.id
    finally:
        db.close()


def push_payload(ref="refs/heads/main", repo_id=REPO_ID, **extra) -> bytes:
    return json.dumps({"ref": ref, "after": SHA, "repository": {"id": repo_id}, **extra}).encode()


def send_push(client, delivery_id: str, body: bytes):
    headers = webhook_headers(sign(body), delivery_id, event="push")
    return client.post("/github/webhook", content=body, headers=headers)


def deployments_of(project_id: int) -> list[Deployment]:
    db = TestingSessionLocal()
    try:
        return db.query(Deployment).filter(Deployment.project_id == project_id).all()
    finally:
        db.close()


def test_push_queues_the_pushed_commit(client, delivery_ids, published):
    project_id = make_project()

    response = send_push(client, delivery_ids(), push_payload())

    assert response.status_code == 200
    [deployment] = deployments_of(project_id)
    assert deployment.commit_sha == SHA
    assert deployment.status == DeploymentStatus.QUEUED
    assert response.json() == {"ok": True, "deployments": [deployment.id]}
    assert published == [deployment.id]


def test_push_to_another_branch_deploys_nothing(client, delivery_ids, published):
    project_id = make_project(branch="main")

    response = send_push(client, delivery_ids(), push_payload(ref="refs/heads/dev"))

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_push_to_another_repo_deploys_nothing(client, delivery_ids, published):
    project_id = make_project()

    response = send_push(client, delivery_ids(), push_payload(repo_id=999))

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_tag_push_deploys_nothing(client, delivery_ids, published):
    project_id = make_project()

    response = send_push(client, delivery_ids(), push_payload(ref="refs/tags/main"))

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_deleted_branch_deploys_nothing(client, delivery_ids, published):
    project_id = make_project()

    response = send_push(client, delivery_ids(), push_payload(deleted=True))

    assert response.json()["deployments"] == []
    assert deployments_of(project_id) == []


def test_push_deploys_every_project_tracking_the_branch(client, delivery_ids, published):
    first, second = make_project(), make_project()

    response = send_push(client, delivery_ids(), push_payload())

    assert len(response.json()["deployments"]) == 2
    assert len(deployments_of(first)) == 1
    assert len(deployments_of(second)) == 1


def test_busy_project_is_skipped_and_the_others_still_deploy(client, delivery_ids, published):
    busy, free = make_project(), make_project()
    send_push(client, delivery_ids(), push_payload(repo_id=REPO_ID))
    db = TestingSessionLocal()
    try:
        db.query(Deployment).filter(Deployment.project_id == free).update({"status": DeploymentStatus.FAILED})
        db.commit()
    finally:
        db.close()

    response = send_push(client, delivery_ids(), push_payload())

    assert response.status_code == 200
    assert len(response.json()["deployments"]) == 1
    assert len(deployments_of(busy)) == 1
    assert len(deployments_of(free)) == 2


def test_repeated_push_deploys_once(client, delivery_ids, published):
    project_id = make_project()
    delivery_id = delivery_ids()

    send_push(client, delivery_id, push_payload())
    send_push(client, delivery_id, push_payload())

    assert len(deployments_of(project_id)) == 1


def test_push_returns_503_when_queue_is_down(client, delivery_ids, monkeypatch):
    def queue_down(deployment_id):
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(services.deployment_services, "publish", queue_down)
    project_id = make_project()

    response = send_push(client, delivery_ids(), push_payload())

    assert response.status_code == 503
    [deployment] = deployments_of(project_id)
    assert deployment.status == DeploymentStatus.FAILED
