from datetime import datetime, timedelta

import pytest
import redis
from sqlalchemy.exc import IntegrityError

import routes.deployments
from auth.security import encrypt_secret
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import OAuthAccount, User
from services.deployment_services import update_deployment_status
from tests.conftest import TestingSessionLocal


FAKE_SHA = "a" * 40


@pytest.fixture(autouse=True)
def fake_latest_commit(monkeypatch):
    """Never call real GitHub: every deployment gets FAKE_SHA.
    Patched in routes.deployments because that module imports the function by name."""
    calls = []

    def fake(token, full_name, branch):
        calls.append({"token": token, "full_name": full_name, "branch": branch})
        return FAKE_SHA

    monkeypatch.setattr(routes.deployments, "fetch_latest_commit", fake)
    return calls


@pytest.fixture(autouse=True)
def fake_publish(monkeypatch):
    """Never publish to the real Redis queue from API tests.
    Records the deployment ids that were published."""
    queued = []
    monkeypatch.setattr(routes.deployments, "publish", queued.append)
    return queued


def create_project(email, name="Deployment Test Project", repo=True, github=True):
    """Insert a project for the user with this email straight into the DB, so the
    GitHub repo check in POST /projects/ is skipped. Returns the project id."""
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()

        if github and not db.query(OAuthAccount).filter_by(user_id=user.id, provider="github").first():
            db.add(OAuthAccount(user_id=user.id, provider="github", provider_user_id=str(user.id),
                                access_token=encrypt_secret("gho_test")))

        repo_fields = {"repo_full_name": "octo/app", "repo_branch": "main"} if repo else {}
        project = Project(user_id=user.id, name=name, description="", **repo_fields)
        db.add(project)
        db.commit()
        return project.id
    finally:
        db.close()


@pytest.fixture
def project_id(auth_headers):
    """A repo-linked project owned by the auth_headers user, who has GitHub connected."""
    return create_project("auth@example.com")


def deploy(client, headers, project_id):
    return client.post("/deployments/", headers=headers, json={"project_id": project_id})


def test_create_deployment(client, auth_headers, project_id):
    response = deploy(client, auth_headers, project_id)

    assert response.status_code == 200

    data = response.json()

    assert data["project_id"] == project_id
    assert data["commit_sha"] == FAKE_SHA
    assert data["status"] == "QUEUED"
    assert "id" in data


def test_deployment_timestamps_include_timezone(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    data = client.get(f"/deployments/{deployment_id}", headers=auth_headers).json()

    # Naive timestamps would be read as local time by the browser.
    for field in ("created_at", "updated_at"):
        assert datetime.fromisoformat(data[field]).utcoffset() == timedelta(0)


def test_deployment_uses_latest_commit_of_project_branch(client, auth_headers, project_id, fake_latest_commit):
    deploy(client, auth_headers, project_id)

    assert fake_latest_commit == [{"token": "gho_test", "full_name": "octo/app", "branch": "main"}]


def test_deployment_ignores_commit_sha_from_client(client, auth_headers, project_id):
    # The SHA always comes from GitHub, never from the browser
    response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={"project_id": project_id, "commit_sha": "abc123"}
    )

    assert response.status_code == 200
    assert response.json()["commit_sha"] == FAKE_SHA


def test_deployment_requires_linked_repo(client, auth_headers, fake_latest_commit):
    no_repo_project = create_project("auth@example.com", repo=False)

    response = deploy(client, auth_headers, no_repo_project)

    assert response.status_code == 400
    assert fake_latest_commit == []          # GitHub was never asked


def test_deployment_requires_github_connected(client, auth_headers):
    project_without_github = create_project("auth@example.com", github=False)

    response = deploy(client, auth_headers, project_without_github)

    assert response.status_code == 403


def test_deployment_status_flow():
    deployment = Deployment(status=DeploymentStatus.QUEUED)

    for status in [DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING, DeploymentStatus.RUNNING, DeploymentStatus.STOPPED]:
        update_deployment_status(deployment, status)
        assert deployment.status == status


def test_invalid_deployment_status_transition():
    deployment = Deployment(status=DeploymentStatus.RUNNING)

    with pytest.raises(ValueError, match="Invalid deployment status transition"):
        update_deployment_status(deployment, DeploymentStatus.BUILDING)


def test_deployment_can_fail():
    deployment = Deployment(status=DeploymentStatus.BUILDING)

    update_deployment_status(deployment, DeploymentStatus.FAILED, "Build failed")

    assert deployment.status == DeploymentStatus.FAILED
    assert deployment.failure_reason == "Build failed"
    assert deployment.failed_stage == DeploymentStatus.BUILDING


def test_status_cannot_be_set_through_api(client, auth_headers, project_id):
    # Only the deployment runner moves a deployment between states.
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "RUNNING"}
    )

    assert response.status_code == 404


def test_other_user_cannot_access_deployment(client, auth_headers, user2_headers, project_id):
    # User 1 creates a deployment
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    # User 2 tries to access User 1's deployment
    response = client.get(
        f"/deployments/{deployment_id}",
        headers=user2_headers
    )

    assert response.status_code == 404


def test_get_deployments(client, auth_headers, project_id):
    deploy(client, auth_headers, project_id)

    response = client.get(
        "/deployments/",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["commit_sha"] == FAKE_SHA


def test_other_user_cannot_create_deployment_for_project(client, user2_headers, project_id):
    # project_id belongs to user 1
    response = deploy(client, user2_headers, project_id)

    assert response.status_code == 404


def set_status(deployment_id, status):
    db = TestingSessionLocal()
    try:
        db.query(Deployment).filter(Deployment.id == deployment_id).update({"status": status})
        db.commit()
    finally:
        db.close()


def test_cannot_deploy_while_deployment_in_progress(client, auth_headers, project_id, fake_publish):
    first_id = deploy(client, auth_headers, project_id).json()["id"]

    response = deploy(client, auth_headers, project_id)

    assert response.status_code == 409
    assert fake_publish == [first_id]


def test_can_deploy_after_previous_deployment_finished(client, auth_headers, project_id):
    first_id = deploy(client, auth_headers, project_id).json()["id"]
    set_status(first_id, DeploymentStatus.RUNNING)

    response = deploy(client, auth_headers, project_id)

    assert response.status_code == 200


def test_database_rejects_second_in_progress_deployment(project_id):
    # Covers two requests racing past the API check at the same time.
    db = TestingSessionLocal()
    try:
        db.add(Deployment(project_id=project_id, commit_sha=FAKE_SHA, status=DeploymentStatus.QUEUED))
        db.commit()
        db.add(Deployment(project_id=project_id, commit_sha=FAKE_SHA, status=DeploymentStatus.BUILDING))

        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_deployment_not_found(client, auth_headers):
    response = client.get(
        "/deployments/99999",
        headers=auth_headers
    )

    assert response.status_code == 404


def set_build_logs(deployment_id, logs):
    """Simulate the runner having saved build output."""
    db = TestingSessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        deployment.build_logs = logs
        db.commit()
    finally:
        db.close()


def test_get_deployment_logs(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_build_logs(deployment_id, "#6 RUN npm run build\nnpm ERR! missing script: build\n")

    response = client.get(f"/deployments/{deployment_id}/logs", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == deployment_id
    assert data["status"] == "QUEUED"
    assert "npm ERR! missing script: build" in data["build_logs"]


def test_deployment_logs_are_empty_before_build(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.get(f"/deployments/{deployment_id}/logs", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["build_logs"] is None


def test_other_user_cannot_read_deployment_logs(client, auth_headers, user2_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_build_logs(deployment_id, "secret build output")

    response = client.get(f"/deployments/{deployment_id}/logs", headers=user2_headers)

    assert response.status_code == 404
    assert "secret build output" not in response.text


def test_deployment_list_does_not_include_build_logs(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_build_logs(deployment_id, "x" * 10_000)

    response = client.get("/deployments/", headers=auth_headers)

    assert "build_logs" not in response.json()[0]


@pytest.fixture(autouse=True)
def fake_remove_resources(monkeypatch):
    """Never call real Docker from API tests; records removed deployment ids."""
    removed = []
    monkeypatch.setattr(routes.deployments, "remove_deployment_resources", removed.append)
    return removed


def set_status(deployment_id, status):
    db = TestingSessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        deployment.status = status
        db.commit()
    finally:
        db.close()


def test_delete_finished_deployment(client, auth_headers, project_id, fake_remove_resources):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_status(deployment_id, DeploymentStatus.RUNNING)

    response = client.delete(f"/deployments/{deployment_id}", headers=auth_headers)

    assert response.status_code == 200
    assert fake_remove_resources == [deployment_id]
    assert client.get(f"/deployments/{deployment_id}", headers=auth_headers).status_code == 404


def test_cannot_delete_deployment_in_progress(client, auth_headers, project_id, fake_remove_resources):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.delete(f"/deployments/{deployment_id}", headers=auth_headers)

    assert response.status_code == 409
    assert fake_remove_resources == []
    assert client.get(f"/deployments/{deployment_id}", headers=auth_headers).status_code == 200


def test_other_user_cannot_delete_deployment(client, auth_headers, user2_headers, project_id, fake_remove_resources):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_status(deployment_id, DeploymentStatus.FAILED)

    response = client.delete(f"/deployments/{deployment_id}", headers=user2_headers)

    assert response.status_code == 404
    assert fake_remove_resources == []


def test_deployment_kept_when_container_removal_fails(client, auth_headers, project_id, monkeypatch):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]
    set_status(deployment_id, DeploymentStatus.RUNNING)

    def fail(deployment_id):
        raise RuntimeError("Docker cleanup timed out.")

    monkeypatch.setattr(routes.deployments, "remove_deployment_resources", fail)

    response = client.delete(f"/deployments/{deployment_id}", headers=auth_headers)

    assert response.status_code == 502
    assert client.get(f"/deployments/{deployment_id}", headers=auth_headers).status_code == 200


def test_deploy_fails_when_queue_is_down(client, auth_headers, project_id, monkeypatch, fake_publish):
    def queue_down(deployment_id):
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(routes.deployments, "publish", queue_down)

    response = deploy(client, auth_headers, project_id)
    assert response.status_code == 503

    deployments = client.get(f"/deployments/?project_id={project_id}", headers=auth_headers).json()
    assert len(deployments) == 1
    assert deployments[0]["status"] == "FAILED"
    assert "Deploy again" in deployments[0]["failure_reason"]


    monkeypatch.setattr(routes.deployments, "publish", fake_publish.append)

    response = deploy(client, auth_headers, project_id)
    assert response.status_code == 200
    assert fake_publish == [response.json()["id"]]
