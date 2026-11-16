import pytest
import redis

import routes.wake as wake_route
import services.deployment_runner as runner
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from tests.conftest import TestingSessionLocal


def add_deployment(make_user, status, container_id="container123", name="Blog"):
    db = TestingSessionLocal()
    try:
        project = Project(user_id=make_user(), name=name, description="")
        db.add(project)
        db.flush()
        deployment = Deployment(
            project_id=project.id,
            commit_sha="a" * 40,
            status=status,
            container_id=container_id,
            host_port=32768,
        )
        db.add(deployment)
        db.commit()
        return project.id, deployment.id
    finally:
        db.close()


def get(deployment_id):
    db = TestingSessionLocal()
    try:
        return db.get(Deployment, deployment_id)
    finally:
        db.close()


# ---------- the wake page (API) ----------

@pytest.fixture
def published(monkeypatch):
    calls = []
    monkeypatch.setattr(wake_route, "publish_wake", calls.append)
    return calls


def test_first_visit_to_a_sleeping_app_queues_one_wake_job(client, make_user, published):
    project_id, deployment_id = add_deployment(make_user, DeploymentStatus.SLEEPING)

    first = client.get(f"/apps/{project_id}/wake")
    second = client.get(f"/apps/{project_id}/wake")

    assert first.status_code == second.status_code == 503
    assert "Waking up Blog" in first.text
    assert 'http-equiv="refresh"' in first.text
    assert first.headers["Retry-After"]
    assert published == [deployment_id]
    assert get(deployment_id).status == DeploymentStatus.WAKING


def test_wake_page_answers_any_method(client, make_user, published):
    project_id, _ = add_deployment(make_user, DeploymentStatus.SLEEPING)

    assert client.post(f"/apps/{project_id}/wake").status_code == 503


def test_project_name_is_escaped(client, make_user, published):
    project_id, _ = add_deployment(make_user, DeploymentStatus.SLEEPING, name="<script>x</script>")

    response = client.get(f"/apps/{project_id}/wake")

    assert "<script>x" not in response.text
    assert "&lt;script&gt;" in response.text


def test_app_that_is_gone_gets_a_404_without_refresh(client, make_user, published):
    project_id, _ = add_deployment(make_user, DeploymentStatus.FAILED)

    response = client.get(f"/apps/{project_id}/wake")

    assert response.status_code == 404
    assert "refresh" not in response.text
    assert published == []


def test_queue_down_puts_the_app_back_to_sleep(client, make_user, monkeypatch):
    def down(deployment_id):
        raise redis.exceptions.ConnectionError("down")
    monkeypatch.setattr(wake_route, "publish_wake", down)
    project_id, deployment_id = add_deployment(make_user, DeploymentStatus.SLEEPING)

    response = client.get(f"/apps/{project_id}/wake")

    assert response.status_code == 503
    assert get(deployment_id).status == DeploymentStatus.SLEEPING


# ---------- the wake job (worker) ----------

@pytest.fixture
def docker(monkeypatch):
    """Fake Docker: start works, the app comes back on a new port."""
    state = {"started": [], "removed": [], "syncs": 0, "status": "running"}
    monkeypatch.setattr(runner, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(runner, "start_container", state["started"].append)
    monkeypatch.setattr(runner, "get_container_status", lambda container_id: state["status"])
    monkeypatch.setattr(runner, "get_exposed_port", lambda image_tag: 80)
    monkeypatch.setattr(runner, "get_host_port", lambda container_id, port: 40000)
    monkeypatch.setattr(runner, "wait_for_healthy", lambda url: None)
    monkeypatch.setattr(runner, "remove_deployment_resources", state["removed"].append)
    monkeypatch.setattr(runner, "sync_app_routes", lambda: state.__setitem__("syncs", state["syncs"] + 1))
    return state


def test_wake_starts_the_container_and_saves_the_new_port(make_user, docker):
    _, deployment_id = add_deployment(make_user, DeploymentStatus.WAKING)

    runner.wake_deployment(deployment_id)

    deployment = get(deployment_id)
    assert deployment.status == DeploymentStatus.RUNNING
    assert deployment.host_port == 40000
    assert deployment.last_active_at is not None
    assert docker["started"] == ["container123"]
    assert docker["syncs"] == 1


@pytest.mark.parametrize("status", [DeploymentStatus.RUNNING, DeploymentStatus.SLEEPING, DeploymentStatus.STOPPED])
def test_wake_skips_deployments_that_are_not_waking(make_user, docker, status):
    _, deployment_id = add_deployment(make_user, status)

    runner.wake_deployment(deployment_id)

    assert get(deployment_id).status == status
    assert docker["started"] == []


def test_app_that_exits_on_wake_is_failed_and_cleaned_up(make_user, docker):
    _, deployment_id = add_deployment(make_user, DeploymentStatus.WAKING)
    docker["status"] = "exited"

    runner.wake_deployment(deployment_id)

    deployment = get(deployment_id)
    assert deployment.status == DeploymentStatus.FAILED
    assert "exited right after waking up" in deployment.failure_reason
    assert docker["removed"] == [deployment_id]


def test_new_deploy_retires_the_old_sleeping_one(make_user, monkeypatch):
    project_id, old_id = add_deployment(make_user, DeploymentStatus.SLEEPING)
    removed = []
    monkeypatch.setattr(runner, "remove_deployment_resources", removed.append)

    db = TestingSessionLocal()
    try:
        new = Deployment(project_id=project_id, commit_sha="b" * 40, status=DeploymentStatus.RUNNING)
        db.add(new)
        db.commit()
        runner._stop_previous_deployments(db, new)
    finally:
        db.close()

    assert get(old_id).status == DeploymentStatus.STOPPED
    assert removed == [old_id]


def test_every_status_has_an_entry_in_the_transitions_table():
    from services.deployment_services import ALLOWED_TRANSITIONS

    assert set(ALLOWED_TRANSITIONS) == set(DeploymentStatus)
