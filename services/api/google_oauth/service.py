import os
from urllib.parse import urlencode

import httpx

from auth.oauth import OAuthError


SCOPES = "openid email profile"


def _config():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not (client_id and client_secret and redirect_uri):
        raise OAuthError("Google sign-in is not configured.")

    return client_id, client_secret, redirect_uri


def get_google_auth_url(state: str) -> str:
    client_id, _, redirect_uri = _config()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "prompt": "select_account",
    }

    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_code_for_token(code: str) -> dict:
    client_id, client_secret, redirect_uri = _config()

    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )

    if response.status_code == 400:
        # invalid_grant: code expired or already used
        raise OAuthError("Google sign-in failed. Please try again.")
    response.raise_for_status()

    return response.json()


def get_google_user(access_token: str) -> dict:
    response = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def fetch_google_identity(code: str) -> dict:
    token_data = exchange_code_for_token(code)
    userinfo = get_google_user(token_data["access_token"])

    email = userinfo.get("email") if userinfo.get("email_verified") else None

    return {
        "provider_user_id": userinfo["sub"],
        "email": email,
        "username_hint": (userinfo.get("email") or "").split("@")[0],
        "avatar_url": userinfo.get("picture"),
        # Google is only used for identity; nothing to keep
        "access_token": None,
    }
