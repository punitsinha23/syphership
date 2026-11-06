import pytest
import redis

import services.account
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import User
from tests.conftest import TestingSessionLocal


@pytest.fixture
def cleaned(monkeypatch):
    """Deployment IDs queued for cleanup, without touching the real queue."""
    removed = []
    monkeypatch.setattr(services.account, "publish_cleanup", removed.append)
    return removed


def add_project(status=None) -> tuple[int, int | None]:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        project = Project(user_id=user.id, name="App", description="")
        db.add(project)
        db.flush()
        deployment = None
        if status:
            deployment = Deployment(project_id=project.id, commit_sha="a" * 40, status=status)
            db.add(deployment)
        db.commit()
        return project.id, deployment.id if deployment else None
    finally:
        db.close()


def delete_me(client, headers, username="authuser"):
    return client.request("DELETE", "/auth/me", headers=headers, json={"confirm_username": username})


def row_count(model) -> int:
    db = TestingSessionLocal()
    try:
        return db.query(model).count()
    finally:
        db.close()


def test_delete_account_removes_everything(client, auth_headers, cleaned):
    _, deployment_id = add_project(DeploymentStatus.RUNNING)

    response = delete_me(client, auth_headers)

    assert response.status_code == 200
    assert cleaned == [deployment_id]
    assert row_count(User) == 0
    assert row_count(Project) == 0
    assert row_count(Deployment) == 0


def test_old_token_stops_working_after_delete(client, auth_headers, cleaned):
    delete_me(client, auth_headers)

    assert client.get("/auth/me", headers=auth_headers).status_code == 401


def test_delete_needs_the_right_username(client, auth_headers, cleaned):
    assert delete_me(client, auth_headers, username="wrong").status_code == 422
    assert row_count(User) == 1


def test_delete_needs_a_login(client):
    assert client.request("DELETE", "/auth/me", json={"confirm_username": "x"}).status_code == 401


def test_cannot_delete_during_a_build(client, auth_headers, cleaned):
    add_project(DeploymentStatus.BUILDING)

    assert delete_me(client, auth_headers).status_code == 409
    assert row_count(User) == 1
    assert cleaned == []


def test_account_is_kept_when_cleanup_cannot_be_queued(client, auth_headers, monkeypatch):
    def fail(deployment_id):
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(services.account, "publish_cleanup", fail)
    add_project(DeploymentStatus.RUNNING)

    assert delete_me(client, auth_headers).status_code == 503
    assert row_count(User) == 1


def test_only_your_own_data_is_deleted(client, auth_headers, user2_headers, cleaned):
    add_project(DeploymentStatus.RUNNING)

    delete_me(client, user2_headers, username="user2")

    assert row_count(User) == 1
    assert row_count(Project) == 1
    assert cleaned == []
