import pytest
from fastapi import HTTPException

import services.deployment_runner as runner
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services.errors import BuildError, DeploymentError
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
    monkeypatch.setattr(
        runner,
        "build_docker_image",
        record("build", ("syphership-deployment-1:latest", "#1 DONE\n")),
    )
    monkeypatch.setattr(runner, "get_exposed_port", record("exposed_port", 80))
    monkeypatch.setattr(runner, "run_docker_container", record("run", "abc123container"))
    monkeypatch.setattr(runner, "get_container_status", record("status", "running"))
    monkeypatch.setattr(runner, "get_host_port", record("host_port", 49153))
    monkeypatch.setattr(runner, "wait_for_healthy", record("health"))

    removed = []
    monkeypatch.setattr(runner, "remove_deployment_resources", removed.append)
    monkeypatch.setattr(runner, "DEPLOYMENT_HOST", "localhost")

    return {"calls": calls, "repository_path": repository_path, "removed": removed}


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
    assert deployment.build_logs == "#1 DONE\n"

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


def test_failed_build_stores_build_logs(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "build_docker_image",
        fail_with(BuildError(
            "Docker build failed. See the build logs for details.",
            "#6 RUN npm run build\nnpm ERR! missing script: build\n",
        )),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert deployment.failure_reason == "Docker build failed. See the build logs for details."
    assert "npm ERR! missing script: build" in deployment.build_logs
    assert "run" not in pipeline["calls"]


def test_logs_from_successful_build_survive_later_failure(make_user, pipeline, monkeypatch):
    # Build succeeded (logs saved), then the health check failed.
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "wait_for_healthy",
        fail_with(DeploymentError("The app did not respond.")),
    )

    runner.run_deployment(deployment_id)

    deployment = get_deployment(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert deployment.build_logs == "#1 DONE\n"


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


def add_deployment(project_id, status):
    """Add another deployment to an existing project."""
    db = TestingSessionLocal()
    try:
        deployment = Deployment(project_id=project_id, commit_sha=FAKE_SHA, status=status)
        db.add(deployment)
        db.commit()
        return deployment.id
    finally:
        db.close()


def test_leftover_resources_are_removed_before_build(make_user, pipeline):
    deployment_id = create_queued_deployment(make_user)

    runner.run_deployment(deployment_id)

    # Removed once up front; nothing else, because the deployment succeeded.
    assert pipeline["removed"] == [deployment_id]


def test_failed_deployment_resources_are_removed(make_user, pipeline, monkeypatch):
    deployment_id = create_queued_deployment(make_user)
    monkeypatch.setattr(
        runner,
        "wait_for_healthy",
        fail_with(DeploymentError("The app did not respond.")),
    )

    runner.run_deployment(deployment_id)

    # Up front, then again after the failure (container was started).
    assert pipeline["removed"] == [deployment_id, deployment_id]


def test_new_deployment_stops_previous_running_one(make_user, pipeline):
    old_id = create_queued_deployment(make_user, status=DeploymentStatus.RUNNING)
    project_id = get_deployment(old_id).project_id
    new_id = add_deployment(project_id, DeploymentStatus.QUEUED)

    runner.run_deployment(new_id)

    assert get_deployment(new_id).status == DeploymentStatus.RUNNING
    assert get_deployment(old_id).status == DeploymentStatus.STOPPED
    assert old_id in pipeline["removed"]


def test_failed_deployment_keeps_previous_one_running(make_user, pipeline, monkeypatch):
    old_id = create_queued_deployment(make_user, status=DeploymentStatus.RUNNING)
    project_id = get_deployment(old_id).project_id
    new_id = add_deployment(project_id, DeploymentStatus.QUEUED)
    monkeypatch.setattr(
        runner,
        "build_docker_image",
        fail_with(DeploymentError("No Dockerfile found at the repository root.")),
    )

    runner.run_deployment(new_id)

    assert get_deployment(new_id).status == DeploymentStatus.FAILED
    assert get_deployment(old_id).status == DeploymentStatus.RUNNING
    assert old_id not in pipeline["removed"]


def test_newer_running_deployment_is_not_stopped(make_user, pipeline):
    # A slow, older build finishing late must not stop the newer version.
    old_id = create_queued_deployment(make_user)
    project_id = get_deployment(old_id).project_id
    newer_id = add_deployment(project_id, DeploymentStatus.RUNNING)

    runner.run_deployment(old_id)

    assert get_deployment(newer_id).status == DeploymentStatus.RUNNING
    assert newer_id not in pipeline["removed"]


def test_previous_deployment_stays_running_if_cleanup_fails(make_user, pipeline, monkeypatch):
    old_id = create_queued_deployment(make_user, status=DeploymentStatus.RUNNING)
    project_id = get_deployment(old_id).project_id
    new_id = add_deployment(project_id, DeploymentStatus.QUEUED)

    def remove(deployment_id):
        if deployment_id == old_id:
            raise RuntimeError("Docker cleanup timed out.")

    monkeypatch.setattr(runner, "remove_deployment_resources", remove)

    runner.run_deployment(new_id)

    assert get_deployment(new_id).status == DeploymentStatus.RUNNING
    assert get_deployment(old_id).status == DeploymentStatus.RUNNING


def test_other_projects_are_not_stopped(make_user, pipeline):
    other_id = create_queued_deployment(make_user, status=DeploymentStatus.RUNNING)
    new_id = create_queued_deployment(
        lambda: make_user(email="other@example.com", username="other")
    )

    runner.run_deployment(new_id)

    assert get_deployment(other_id).status == DeploymentStatus.RUNNING
