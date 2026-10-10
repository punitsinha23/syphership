import pytest

import routes.deployments
from auth.security import encrypt_secret
from models.project import Project
from models.user import OAuthAccount, User
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


def test_deployment_status_flow(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    for status in ["BUILDING", "DEPLOYING", "RUNNING"]:
        response = client.patch(
            f"/deployments/{deployment_id}/status",
            headers=auth_headers,
            json={"status": status}
        )

        assert response.status_code == 200
        assert response.json()["status"] == status


def test_invalid_deployment_status_transition(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    # Move deployment to RUNNING
    for status in ["BUILDING", "DEPLOYING", "RUNNING"]:
        client.patch(
            f"/deployments/{deployment_id}/status",
            headers=auth_headers,
            json={"status": status}
        )

    # RUNNING → BUILDING should fail
    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "BUILDING"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid deployment status transition"


def test_deployment_can_fail(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "FAILED", "failure_reason": "Build failed"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["failure_reason"] == "Build failed"


def test_failed_status_requires_failure_reason(client, auth_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "FAILED"}
    )

    assert response.status_code == 422


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


def test_other_user_cannot_update_deployment(client, auth_headers, user2_headers, project_id):
    deployment_id = deploy(client, auth_headers, project_id).json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=user2_headers,
        json={"status": "BUILDING"}
    )

    assert response.status_code == 404


def test_deployment_not_found(client, auth_headers):
    response = client.get(
        "/deployments/99999",
        headers=auth_headers
    )

    assert response.status_code == 404
