import pytest

import services.app_routes as routes
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from tests.conftest import TestingSessionLocal


DOMAIN = "apps.example.com"


@pytest.fixture
def caddy(monkeypatch, tmp_path):
    """APPS_DOMAIN set, the routes file in a temp folder, and a fake Caddy reload."""
    monkeypatch.setattr(routes, "APPS_DOMAIN", DOMAIN)
    monkeypatch.setattr(routes, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(routes, "CADDY_ROUTES_FILE", tmp_path / "apps.caddy")

    state = {"reloads": 0, "fail": False}

    def fake_reload():
        if state["fail"]:
            raise RuntimeError("Caddy is down")
        state["reloads"] += 1

    monkeypatch.setattr(routes, "_reload_caddy", fake_reload)
    state["file"] = tmp_path / "apps.caddy"
    return state


def add_project(make_user, name="My App", deployments=()):
    """A project with deployments given as (status, host_port) pairs."""
    db = TestingSessionLocal()
    try:
        project = Project(user_id=make_user(), name=name, description="")
        db.add(project)
        db.flush()
        for status, host_port in deployments:
            db.add(Deployment(project_id=project.id, commit_sha="a" * 40, status=status, host_port=host_port))
        db.commit()
        return project.id
    finally:
        db.close()


@pytest.mark.parametrize(
    "name, expected",
    [
        ("My Cool App", "my-cool-app-7"),
        ("  API!!  ", "api-7"),
        ("émoji 🚀 site", "moji-site-7"),
        ("!!!", "app-7"),
        ("x" * 80, "x" * 40 + "-7"),
    ],
)
def test_hostname_is_a_safe_slug_plus_project_id(monkeypatch, name, expected):
    monkeypatch.setattr(routes, "APPS_DOMAIN", DOMAIN)
    assert routes.app_hostname(7, name) == f"{expected}.{DOMAIN}"


def test_no_public_url_without_apps_domain(monkeypatch):
    monkeypatch.setattr(routes, "APPS_DOMAIN", "")
    assert routes.public_url(7, "My App") is None


def test_render_routes_proxies_each_app_to_its_local_port(monkeypatch):
    monkeypatch.setattr(routes, "APPS_DOMAIN", DOMAIN)

    content = routes.render_routes([(2, "Blog", 32769), (1, "Shop", 32768)])

    assert content.startswith(routes.ROUTES_HEADER)
    assert f"shop-1.{DOMAIN} {{\n    reverse_proxy 127.0.0.1:32768\n}}" in content
    assert f"blog-2.{DOMAIN} {{\n    reverse_proxy 127.0.0.1:32769\n}}" in content


def test_sync_does_nothing_without_apps_domain(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "APPS_DOMAIN", "")
    monkeypatch.setattr(routes, "CADDY_ROUTES_FILE", tmp_path / "apps.caddy")

    routes.sync_app_routes()

    assert not (tmp_path / "apps.caddy").exists()


def test_sync_routes_only_the_newest_running_deployment(make_user, caddy):
    project_id = add_project(
        make_user,
        deployments=[
            (DeploymentStatus.STOPPED, 30001),
            (DeploymentStatus.RUNNING, 30002),  # old one, still running mid-redeploy
            (DeploymentStatus.RUNNING, 30003),  # new one
            (DeploymentStatus.FAILED, 30004),
        ],
    )

    routes.sync_app_routes()

    content = caddy["file"].read_text()
    assert f"my-app-{project_id}.{DOMAIN}" in content
    assert "127.0.0.1:30003" in content
    assert content.count("reverse_proxy") == 1
    assert caddy["reloads"] == 1


def test_sync_reloads_caddy_only_when_routes_change(make_user, caddy):
    add_project(make_user, deployments=[(DeploymentStatus.RUNNING, 30001)])

    routes.sync_app_routes()
    routes.sync_app_routes()

    assert caddy["reloads"] == 1


def test_sync_removes_routes_of_apps_that_stopped(make_user, caddy):
    caddy["file"].write_text(routes.ROUTES_HEADER + "old-1.apps.example.com {\n}\n")

    routes.sync_app_routes()

    assert "old-1" not in caddy["file"].read_text()
    assert caddy["reloads"] == 1


def test_failed_reload_restores_the_old_file_so_the_next_sync_retries(make_user, caddy):
    previous = routes.ROUTES_HEADER
    caddy["file"].write_text(previous)
    add_project(make_user, deployments=[(DeploymentStatus.RUNNING, 30001)])
    caddy["fail"] = True

    routes.sync_app_routes()  # must not raise

    assert caddy["file"].read_text() == previous

    caddy["fail"] = False
    routes.sync_app_routes()

    assert "127.0.0.1:30001" in caddy["file"].read_text()
    assert caddy["reloads"] == 1
