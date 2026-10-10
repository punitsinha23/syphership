import pytest
from fastapi import HTTPException

import github.routes
import github.service
from auth.security import encrypt_secret
from models.user import OAuthAccount, User
from tests.conftest import TestingSessionLocal


@pytest.fixture
def github_headers(auth_headers):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        db.add(OAuthAccount(
            user_id=user.id,
            provider="github",
            provider_user_id="1",
            access_token=encrypt_secret("gho_test"),
        ))
        db.commit()
    finally:
        db.close()

    return auth_headers


def test_list_repos_returns_trimmed_fields(client, github_headers, monkeypatch):
    # Arrange: a fake GitHub that returns one repo with an extra field
    def fake_github_get(path, token, params=None):
        return [{
            "id": 1,
            "full_name": "octo/app",
            "name": "app",
            "private": False,
            "default_branch": "main",
            "stargazers_count": 5,          # extra field: should NOT reach the frontend
        }]

    # Pass the function itself, not the string "fake_github_get"
    monkeypatch.setattr(github.routes, "github_get", fake_github_get)

    # Act
    response = client.get("/github/repos", headers=github_headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == [{
        "id": 1,
        "full_name": "octo/app",
        "name": "app",
        "private": False,
        "default_branch": "main",
    }]


def test_list_repos_requires_github(client, auth_headers):
    # No OAuthAccount row, so get_github_token() stops with 403
    # before github_get is ever called: no fake needed
    response = client.get("/github/repos", headers=auth_headers)

    assert response.status_code == 403


def test_list_repos_passes_page(client, github_headers, monkeypatch):
    calls = {}

    def fake_github_get(path, token, params=None):
        # Record how the route called GitHub so the test can check it afterwards
        calls["path"] = path
        calls["token"] = token
        calls["params"] = params
        return []

    monkeypatch.setattr(github.routes, "github_get", fake_github_get)

    response = client.get("/github/repos?page=3", headers=github_headers)

    assert response.status_code == 200
    assert response.json() == []
    assert calls["path"] == "/user/repos"
    assert calls["token"] == "gho_test"      # the stored token was decrypted correctly
    assert calls["params"] == {"per_page": 100, "page": 3, "sort": "updated"}


def test_list_branches_returns_names(client, github_headers, monkeypatch):
    calls = {}

    def fake_github_get(path, token, params=None):
        calls["path"] = path
        return [{"name": "main", "commit": {"sha": "abc"}}, {"name": "dev", "commit": {"sha": "def"}}]

    monkeypatch.setattr(github.routes, "github_get", fake_github_get)

    response = client.get("/github/repos/octo/app/branches", headers=github_headers)

    assert response.status_code == 200
    assert response.json() == ["main", "dev"]
    assert calls["path"] == "/repos/octo/app/branches"


def test_revoked_token_returns_403(client, github_headers, monkeypatch):
    # This is what the real github_get raises when GitHub answers 401
    def fake_github_get(path, token, params=None):
        raise HTTPException(status_code=403, detail="GitHub access was revoked. Reconnect GitHub.")

    monkeypatch.setattr(github.routes, "github_get", fake_github_get)

    response = client.get("/github/repos", headers=github_headers)

    # Must be 403, not 401: client.js treats any 401 as "session expired" and logs the user out
    assert response.status_code == 403
    assert "revoked" in response.json()["detail"]


def test_list_repos_requires_login(client):
    response = client.get("/github/repos")

    assert response.status_code == 401


# ---------- fetch_latest_commit (used by POST /deployments/) ----------


def test_fetch_latest_commit_returns_newest_sha(monkeypatch):
    calls = {}

    def fake_github_get(path, token, params=None):
        calls["path"] = path
        calls["params"] = params
        return [{"sha": "newest"}, {"sha": "older"}]

    # fetch_latest_commit lives in github.service and looks github_get up there
    monkeypatch.setattr(github.service, "github_get", fake_github_get)

    assert github.service.fetch_latest_commit("gho_test", "octo/app", "dev") == "newest"
    assert calls["path"] == "/repos/octo/app/commits"
    assert calls["params"] == {"sha": "dev", "per_page": 1}


def test_fetch_latest_commit_empty_branch(monkeypatch):
    monkeypatch.setattr(github.service, "github_get", lambda path, token, params=None: [])

    with pytest.raises(HTTPException) as error:
        github.service.fetch_latest_commit("gho_test", "octo/app", "empty")

    assert error.value.status_code == 404

def test_github_get_repository_not_found(monkeypatch):
    class FakeResponse:
        status_code = 404

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(github.service.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as error:
        github.service.github_get(
            "/repos/octo/missing",
            "gho_test",
        )

    assert error.value.status_code == 404
    assert "not found" in error.value.detail.lower()

