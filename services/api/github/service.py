import os
from urllib.parse import urlencode

import httpx

from auth.oauth import OAuthError


# Sign-in only needs identity + email. Add repo access (ideally via a GitHub App)
# when deployments start pulling code.
SCOPES = "read:user user:email"


def _config():
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI")

    if not (client_id and client_secret and redirect_uri):
        raise OAuthError("GitHub sign-in is not configured.")

    return client_id, client_secret, redirect_uri


def get_github_auth_url(state: str) -> str:
    client_id, _, redirect_uri = _config()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }

    return "https://github.com/login/oauth/authorize?" + urlencode(params)


def exchange_code_for_token(code: str) -> dict:
    client_id, client_secret, redirect_uri = _config()

    response = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def _get(path: str, access_token: str):
    response = httpx.get(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def fetch_github_identity(code: str) -> dict:
    token_data = exchange_code_for_token(code)

    # GitHub reports a bad/expired code as 200 with an "error" field
    access_token = token_data.get("access_token")
    if not access_token:
        raise OAuthError("GitHub sign-in failed. Please try again.")

    github_user = _get("/user", access_token)

    # /user can return email=None, so read the verified primary email separately
    emails = _get("/user/emails", access_token)
    primary_email = next(
        (e["email"] for e in emails if e.get("primary") and e.get("verified")),
        None,
    )

    return {
        "provider_user_id": str(github_user["id"]),
        "email": primary_email,
        "username_hint": github_user.get("login"),
        "avatar_url": github_user.get("avatar_url"),
        "access_token": access_token,
    }
