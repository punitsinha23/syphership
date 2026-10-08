from urllib.parse import parse_qs, urlparse

import pytest

import github.routes
import google_oauth.routes
from auth.oauth import FRONTEND_URL
from auth.security import create_token, decrypt_secret
from models.user import OAuthAccount
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def oauth_config(monkeypatch):
    for provider in ("GITHUB", "GOOGLE"):
        monkeypatch.setenv(f"{provider}_CLIENT_ID", "client-id")
        monkeypatch.setenv(f"{provider}_CLIENT_SECRET", "client-secret")
        monkeypatch.setenv(f"{provider}_REDIRECT_URI", "http://testserver/callback")


def github_identity(id="101", email="octo@example.com", login="octocat", token="gho_token"):
    return {
        "provider_user_id": id,
        "email": email,
        "username_hint": login,
        "avatar_url": "https://avatars.example/octo.png",
        "access_token": token,
    }


def google_identity(sub="g-202", email="octo@example.com"):
    return {
        "provider_user_id": sub,
        "email": email,
        "username_hint": email.split("@")[0] if email else None,
        "avatar_url": None,
        "access_token": None,
    }


def mock_identity(monkeypatch, provider, identity):
    module, attr = {
        "github": (github.routes, "fetch_github_identity"),
        "google": (google_oauth.routes, "fetch_google_identity"),
    }[provider]
    monkeypatch.setattr(module, attr, lambda code: identity)


def frontend_params(response):
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith(f"{FRONTEND_URL}/auth/callback?")
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


def start_login(client, provider):
    response = client.get(f"/{provider}/login", follow_redirects=False)
    assert response.status_code == 307
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def oauth_sign_in(client, monkeypatch, provider, identity):
    """Run login -> callback -> exchange; returns the token response."""
    mock_identity(monkeypatch, provider, identity)
    state = start_login(client, provider)

    callback = client.get(
        f"/{provider}/callback",
        params={"code": "provider-code", "state": state},
        follow_redirects=False,
    )
    params = frontend_params(callback)
    assert "code" in params, params

    response = client.post("/auth/exchange", json={"code": params["code"]})
    assert response.status_code == 200
    return response.json()


def me(client, tokens):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    return response.json()


def test_password_routes_removed(client):
    assert client.post("/auth/register", json={}).status_code == 404
    assert client.post("/auth/login", json={}).status_code == 404


def test_github_sign_up_creates_user(client, monkeypatch):
    tokens = oauth_sign_in(client, monkeypatch, "github", github_identity())

    assert tokens["token_type"] == "bearer"
    assert "refresh_token" in tokens

    user = me(client, tokens)
    assert user["username"] == "octocat"
    assert user["email"] == "octo@example.com"
    assert user["providers"] == ["github"]
    assert user["github_connected"] is True


def test_github_token_is_stored_encrypted(client, monkeypatch):
    oauth_sign_in(client, monkeypatch, "github", github_identity(token="gho_secret"))

    db = TestingSessionLocal()
    try:
        account = db.query(OAuthAccount).one()
        assert account.access_token != "gho_secret"
        assert decrypt_secret(account.access_token) == "gho_secret"
    finally:
        db.close()


def test_returning_user_signs_into_same_account(client, monkeypatch):
    first = me(client, oauth_sign_in(client, monkeypatch, "github", github_identity()))
    # GitHub username and email changed; the GitHub id is what identifies them
    second = me(client, oauth_sign_in(
        client, monkeypatch, "github", github_identity(email="new@example.com", login="renamed")
    ))

    assert second["id"] == first["id"]


def test_google_sign_in_links_to_same_email(client, monkeypatch):
    github_user = me(client, oauth_sign_in(client, monkeypatch, "github", github_identity()))
    google_user = me(client, oauth_sign_in(client, monkeypatch, "google", google_identity()))

    assert google_user["id"] == github_user["id"]
    assert google_user["providers"] == ["github", "google"]


def test_google_only_user_has_no_github(client, monkeypatch):
    user = me(client, oauth_sign_in(client, monkeypatch, "google", google_identity()))

    assert user["providers"] == ["google"]
    assert user["github_connected"] is False


def test_username_collision_gets_suffix(client, monkeypatch, make_user):
    make_user(email="someone@example.com", username="octocat")

    user = me(client, oauth_sign_in(client, monkeypatch, "github", github_identity()))

    assert user["username"] == "octocat-2"


def test_unverified_google_email_rejected(client, monkeypatch):
    mock_identity(monkeypatch, "google", google_identity(email=None))
    state = start_login(client, "google")

    response = client.get("/google/callback", params={"code": "c", "state": state}, follow_redirects=False)

    assert "verified email" in frontend_params(response)["error"]


def test_callback_without_state_cookie_rejected(client, monkeypatch):
    mock_identity(monkeypatch, "github", github_identity())
    state = start_login(client, "github")
    client.cookies.clear()

    response = client.get("/github/callback", params={"code": "c", "state": state}, follow_redirects=False)

    assert "error" in frontend_params(response)


def test_callback_with_forged_state_rejected(client, monkeypatch):
    mock_identity(monkeypatch, "github", github_identity())
    start_login(client, "github")
    forged = create_token({"nonce": "attacker", "provider": "github"}, __import__("datetime").timedelta(minutes=5), "oauth_state")

    response = client.get("/github/callback", params={"code": "c", "state": forged}, follow_redirects=False)

    assert "error" in frontend_params(response)


def test_state_from_other_provider_rejected(client, monkeypatch):
    mock_identity(monkeypatch, "github", github_identity())
    state = start_login(client, "google")

    response = client.get("/github/callback", params={"code": "c", "state": state}, follow_redirects=False)

    assert "error" in frontend_params(response)


def test_user_cancelled_at_provider(client):
    state = start_login(client, "github")

    response = client.get("/github/callback", params={"error": "access_denied", "state": state}, follow_redirects=False)

    assert "cancelled" in frontend_params(response)["error"]


def test_login_code_is_single_use(client, monkeypatch):
    mock_identity(monkeypatch, "github", github_identity())
    state = start_login(client, "github")
    callback = client.get("/github/callback", params={"code": "c", "state": state}, follow_redirects=False)
    code = frontend_params(callback)["code"]

    assert client.post("/auth/exchange", json={"code": code}).status_code == 200
    assert client.post("/auth/exchange", json={"code": code}).status_code == 400


def test_invalid_login_code(client):
    assert client.post("/auth/exchange", json={"code": "nope"}).status_code == 400


def test_unconfigured_provider_redirects_with_error(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID")

    response = client.get("/google/login", follow_redirects=False)

    assert "not configured" in frontend_params(response)["error"]


def test_connect_github_to_google_account(client, monkeypatch):
    tokens = oauth_sign_in(client, monkeypatch, "google", google_identity(email="g@example.com"))
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    connect = client.post("/github/connect", headers=headers)
    assert connect.status_code == 200
    state = parse_qs(urlparse(connect.json()["url"]).query)["state"][0]

    # Different email on GitHub: linking is explicit, so it still attaches to this user
    mock_identity(monkeypatch, "github", github_identity(email="other@example.com"))
    callback = client.get("/github/callback", params={"code": "c", "state": state}, follow_redirects=False)

    assert frontend_params(callback) == {"connected": "github"}
    user = me(client, tokens)
    assert user["github_connected"] is True
    assert user["email"] == "g@example.com"


def test_connect_github_already_linked_elsewhere(client, monkeypatch):
    oauth_sign_in(client, monkeypatch, "github", github_identity())
    tokens = oauth_sign_in(client, monkeypatch, "google", google_identity(email="someone-else@example.com"))

    connect = client.post("/github/connect", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    state = parse_qs(urlparse(connect.json()["url"]).query)["state"][0]
    mock_identity(monkeypatch, "github", github_identity())
    callback = client.get("/github/callback", params={"code": "c", "state": state}, follow_redirects=False)

    assert "already linked" in frontend_params(callback)["error"]
    assert me(client, tokens)["github_connected"] is False


def test_connect_requires_auth(client):
    assert client.post("/github/connect").status_code == 401


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_refresh_token(client, monkeypatch):
    tokens = oauth_sign_in(client, monkeypatch, "github", github_identity())

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert me(client, response.json())["username"] == "octocat"


def test_access_token_rejected_as_refresh(client, monkeypatch):
    tokens = oauth_sign_in(client, monkeypatch, "github", github_identity())

    response = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})

    assert response.status_code == 401
