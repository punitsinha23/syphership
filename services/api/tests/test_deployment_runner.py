import pytest
from fastapi import HTTPException

import services.deployment_runner as runner
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services.errors import DeploymentError
from tests.conftest import TestingSessionLocal


FAKE_SHA = "a" * 40


def create_queued_deployment(make_user, status=DeploymentStatus.QUEUED):
    """Create a user, a project with a linked repo, and a deployment."""
    user_id = make_user()

    db = TestingSessionLocal()
    try:
        project = Project(
            user_id=user_id,
            name="Runner Test Project",
            description="",
            repo_full_name="octo/app",
            repo_branch="main",
            repo_clone_url="https://github.com/octo/app.git",
        )
        db.add(project)
        db.flush()

        deployment = Deployment(
            project_id=project.id,
            commit_sha=FAKE_SHA,
            status=status,
        )
        db.add(deployment)
        db.commit()

        return deployment.id
    finally:
        db.close()


def get_deployment(deployment_id):
    db = TestingSessionLocal()
    try:
        return db.query(Deployment).filter(Deployment.id == deployment_id).first()
    finally:
        db.close()


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    """Replace every external step (GitHub, git, Docker, HTTP) with a fake
    that succeeds. Tests override single steps to simulate failures."""
    calls = []
    repository_path = tmp_path / "repo"
    repository_path.mkdir()

    def record(name, result=None):
        def fake(*args, **kwargs):
            calls.append(name)
            return result
        return fake

    monkeypatch.setattr(runner, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(runner, "get_github_token", record("token", "gho_test"))
    monkeypatch.setattr(runner, "clone_repository", record("clone", repository_path))
    monkeypatch.setattr(runner, "build_docker_image", record("build", "syphership-deployment-1:latest"))
    monkeypatch.setattr(runner, "get_exposed_port", record("exposed_port", 80))
    monkeypatch.setattr(runner, "run_docker_container", record("run", "abc123container"))
    monkeypatch.setattr(runner, "get_container_status", record("status", "running"))
    monkeypatch.setattr(runner, "get_host_port", record("host_port", 49153))
    monkeypatch.setattr(runner, "wait_for_healthy", record("health"))
    monkeypatch.setattr(runner, "DEPLOYMENT_HOST", "localhost")

    return {"calls": calls, "repository_path": repository_path}


def fail_with(error):
    def fake(*args, **kwargs):
        raise error
    return fake


def test_successful_deployment_is_running_with_url(make_user, pipeline):
    deployment_id = create_queued_deployment(make_user)

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.RUNNING
    assert deployment.container_id == "abc123container"
    assert deployment.host_port == 49153
    assert deployment.url == "http://localhost:49153"
    assert deployment.failure_reason is None

    assert pipeline["calls"] == [
        "token",
        "clone",
        "build",
        "exposed_port",
        "run",
        "status",
        "host_port",
        "health",
    ]


def test_cloned_repository_is_removed_afterwards(make_user, pipeline):
    deployment_id = create_queued_deployment(make_user)

    runner.run_deployment(deployment_id)

    assert not pipeline["repository_path"].exists()


def test_user_facing_error_is_stored_as_failure_reason(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "build_docker_image",
        fail_with(DeploymentError("No Dockerfile found at the repository root.")),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert deployment.failure_reason == "No Dockerfile found at the repository root."
    assert deployment.url is None


def test_unexpected_error_hides_details(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "build_docker_image",
        fail_with(RuntimeError("Docker is not installed or is not available in PATH.")),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert deployment.failure_reason == "Deployment failed due to an internal error."


def test_failed_health_check_does_not_store_url(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "wait_for_healthy",
        fail_with(DeploymentError("The app did not respond at http://localhost:49153 within 60 seconds.")),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert "did not respond" in deployment.failure_reason
    assert deployment.url is None
    assert deployment.host_port is None
    # The container was started, so its id is kept for later cleanup.
    assert deployment.container_id == "abc123container"


def test_exited_container_fails(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(runner, "get_container_status", lambda container_id: "exited")

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert "exited right after starting" in deployment.failure_reason


def test_missing_github_connection_fails(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "get_github_token",
        fail_with(HTTPException(status_code=403, detail="Connect your Github account first.")),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert "GitHub account is not connected" in deployment.failure_reason
    assert "clone" not in pipeline["calls"]


def test_deployment_that_is_not_queued_is_skipped(make_user, pipeline):
    deployment_id = create_queued_deployment(make_user, status=DeploymentStatus.RUNNING)

    runner.run_deployment(deployment_id)

    assert get_deployment(deployment_id).status == DeploymentStatus.RUNNING
    assert pipeline["calls"] == []


def test_missing_deployment_does_nothing(pipeline):
    runner.run_deployment(999999)

    assert pipeline["calls"] == []
