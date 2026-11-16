import os
from datetime import UTC, datetime, timedelta

import pytest

import services.app_routes as routes
import services.idle_apps as idle
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from tests.conftest import TestingSessionLocal

DOMAIN = "apps.example.com"
NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    """Sleeping enabled, logs in a temp folder, and fake docker stop / route sync."""
    monkeypatch.setattr(routes, "APPS_DOMAIN", DOMAIN)
    monkeypatch.setattr(routes, "APP_LOG_DIR", tmp_path)
    monkeypatch.setattr(idle, "IDLE_SLEEP_HOURS", 24)
    monkeypatch.setattr(idle, "SessionLocal", TestingSessionLocal)

    state = {"stopped": [], "syncs": 0, "stop_fails": False}

    def fake_stop(container_id):
        if state["stop_fails"]:
            raise RuntimeError("docker stop failed")
        state["stopped"].append(container_id)

    def fake_sync():
        state["syncs"] += 1

    monkeypatch.setattr(idle, "stop_container", fake_stop)
    monkeypatch.setattr(routes, "sync_app_routes", fake_sync)
    return state


def add_running(make_user, last_active_at, name="My App", status=DeploymentStatus.RUNNING):
    db = TestingSessionLocal()
    try:
        project = Project(user_id=make_user(), name=name, description="")
        db.add(project)
        db.flush()
        deployment = Deployment(
            project_id=project.id,
            commit_sha="a" * 40,
            status=status,
            container_id="container123",
            host_port=32768,
            last_active_at=last_active_at,
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


def touch_log(project_id, when, name="My App"):
    path = routes.app_log_file(project_id, name)
    path.write_text("request\n")
    os.utime(path, (when.timestamp(), when.timestamp()))


# ---------- record_activity ----------

def test_visit_in_the_log_moves_last_active_forward(make_user, setup):
    project_id, deployment_id = add_running(make_user, NOW - timedelta(hours=30))
    touch_log(project_id, NOW - timedelta(minutes=5))

    idle.record_activity()

    assert get(deployment_id).last_active_at == NOW - timedelta(minutes=5)


def test_older_log_never_moves_last_active_back(make_user, setup):
    project_id, deployment_id = add_running(make_user, NOW)
    touch_log(project_id, NOW - timedelta(days=3))

    idle.record_activity()

    assert get(deployment_id).last_active_at == NOW


def test_app_without_log_file_keeps_its_time(make_user, setup):
    _, deployment_id = add_running(make_user, NOW - timedelta(hours=2))

    idle.record_activity()

    assert get(deployment_id).last_active_at == NOW - timedelta(hours=2)


# ---------- sleep_idle_apps ----------

def test_app_idle_for_a_day_is_stopped_and_sleeping(make_user, setup):
    _, deployment_id = add_running(make_user, NOW - timedelta(hours=25))

    idle.sleep_idle_apps(now=NOW)

    assert get(deployment_id).status == DeploymentStatus.SLEEPING
    assert setup["stopped"] == ["container123"]
    assert setup["syncs"] == 1


def test_recently_used_app_keeps_running(make_user, setup):
    _, deployment_id = add_running(make_user, NOW - timedelta(hours=23))

    idle.sleep_idle_apps(now=NOW)

    assert get(deployment_id).status == DeploymentStatus.RUNNING
    assert setup["stopped"] == []


def test_failed_stop_puts_the_app_back_to_running(make_user, setup):
    _, deployment_id = add_running(make_user, NOW - timedelta(hours=25))
    setup["stop_fails"] = True

    idle.sleep_idle_apps(now=NOW)  # must not raise

    assert get(deployment_id).status == DeploymentStatus.RUNNING


@pytest.mark.parametrize("domain, hours", [("", 24), (DOMAIN, 0)])
def test_sleeping_is_off_without_apps_domain_or_with_zero_hours(make_user, setup, monkeypatch, domain, hours):
    monkeypatch.setattr(routes, "APPS_DOMAIN", domain)
    monkeypatch.setattr(idle, "IDLE_SLEEP_HOURS", hours)
    _, deployment_id = add_running(make_user, NOW - timedelta(days=10))

    idle.sleep_idle_apps(now=NOW)

    assert get(deployment_id).status == DeploymentStatus.RUNNING
    assert setup["stopped"] == []
