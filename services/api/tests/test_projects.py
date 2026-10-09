def test_projects_requires_auth(client):
    response = client.get("/projects/")

    assert response.status_code == 401

def test_projects_authenticated(client, auth_headers):
    response = client.get(
        "/projects/",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_project(client, auth_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Test Project",
            "description": "Project for testing"
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "Project for testing"
    assert "id" in data

def test_get_projects(client, auth_headers):
    client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Project One",
            "description": "First project"
        }
    )

    response = client.get(
        "/projects/",
        headers=auth_headers
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Project One"

def test_get_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Specific Project",
            "description": "Testing get by ID"
        }
    )

    project_id = create_response.json()["id"]

    response = client.get(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == project_id

def test_update_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Old Name",
            "description": "Old description"
        }
    )

    project_id = create_response.json()["id"]

    response = client.put(
        f"/projects/{project_id}",
        headers=auth_headers,
        json={
            "name": "New Name",
            "description": "New description"
        }
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "New description"

def test_delete_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Delete Me",
            "description": "Testing deletion"
        }
    )

    project_id = create_response.json()["id"]

    response = client.delete(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert response.status_code == 200

    get_response = client.get(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert get_response.status_code == 404

def test_user_cannot_access_other_users_project(client, auth_headers, user2_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]


    response = client.get(
        f"/projects/{project_id}",
        headers=user2_headers
    )

    assert response.status_code == 404


def test_user_cannot_update_other_users_project(client, auth_headers, user2_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]


    response = client.put(
        f"/projects/{project_id}",
        headers=user2_headers,
        json={
            "name": "Hacked Project",
            "description": "Changes"
        }
    )

    assert response.status_code == 404


def test_user_cannot_delete_other_users_project(client, auth_headers, user2_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]

    response = client.delete(
        f"/projects/{project_id}",
        headers=user2_headers,
    )

    assert response.status_code == 404


# ---------- linked GitHub repository ----------

import pytest
from fastapi import HTTPException

import github.service
from auth.security import encrypt_secret
from models.user import OAuthAccount, User
from tests.conftest import TestingSessionLocal

FAKE_REPO = {
    "id": 9_000_000_001,
    "full_name": "octo/app",
    "default_branch": "main",
    "clone_url": "https://github.com/octo/app.git",
    "html_url": "https://github.com/octo/app",
    "private": True,
}
FAKE_BRANCHES = {"main", "dev", "feature/x"}


def fake_github_get(path, token, params=None):
    assert token == "gho_test"
    if path == "/repos/octo/app":
        return FAKE_REPO
    prefix = "/repos/octo/app/branches/"
    if path.startswith(prefix) and path[len(prefix):].replace("%2F", "/") in FAKE_BRANCHES:
        return {"name": path[len(prefix):]}
    raise HTTPException(status_code=404, detail="Repository or branch not found, or no access.")


@pytest.fixture
def github_connected(auth_headers, monkeypatch):
    """Give the auth_headers user a GitHub account and fake the GitHub API."""
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        db.add(OAuthAccount(user_id=user.id, provider="github", provider_user_id="1",
                            access_token=encrypt_secret("gho_test")))
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(github.service, "github_get", fake_github_get)
    return auth_headers


def create(client, headers, **repo):
    return client.post("/projects/", headers=headers,
                       json={"name": "App", "description": "", **repo})


def test_create_project_with_repo_uses_default_branch(client, github_connected):
    response = create(client, github_connected, repo_full_name="octo/app")

    assert response.status_code == 200
    data = response.json()
    assert data["repo_full_name"] == "octo/app"
    assert data["repo_branch"] == "main"
    assert data["repo_html_url"] == "https://github.com/octo/app"
    assert data["repo_private"] is True


def test_create_project_with_repo_and_branch(client, github_connected):
    response = create(client, github_connected, repo_full_name="octo/app", repo_branch="feature/x")

    assert response.status_code == 200
    assert response.json()["repo_branch"] == "feature/x"


def test_create_project_repo_not_accessible(client, github_connected):
    response = create(client, github_connected, repo_full_name="octo/secret")

    assert response.status_code == 404


def test_create_project_unknown_branch(client, github_connected):
    response = create(client, github_connected, repo_full_name="octo/app", repo_branch="nope")

    assert response.status_code == 404


def test_create_project_invalid_repo_name(client, github_connected):
    response = create(client, github_connected, repo_full_name="../octo")

    assert response.status_code == 422


def test_create_project_branch_without_repo(client, github_connected):
    response = create(client, github_connected, repo_branch="main")

    assert response.status_code == 422


def test_create_project_with_repo_requires_github(client, auth_headers):
    response = create(client, auth_headers, repo_full_name="octo/app")

    assert response.status_code == 403


def test_update_project_branch_keeps_repo(client, github_connected):
    project_id = create(client, github_connected, repo_full_name="octo/app").json()["id"]

    response = client.put(f"/projects/{project_id}", headers=github_connected,
                          json={"name": "App", "description": "", "repo_branch": "dev"})

    assert response.status_code == 200
    assert response.json()["repo_full_name"] == "octo/app"
    assert response.json()["repo_branch"] == "dev"


def test_update_project_without_repo_fields_keeps_repo(client, github_connected):
    project_id = create(client, github_connected, repo_full_name="octo/app").json()["id"]

    response = client.put(f"/projects/{project_id}", headers=github_connected,
                          json={"name": "Renamed", "description": "new"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["repo_full_name"] == "octo/app"
    assert response.json()["repo_branch"] == "main"


def test_update_project_branch_without_repo(client, auth_headers):
    project_id = create(client, auth_headers).json()["id"]

    response = client.put(f"/projects/{project_id}", headers=auth_headers,
                          json={"name": "App", "description": "", "repo_branch": "dev"})

    assert response.status_code == 422
