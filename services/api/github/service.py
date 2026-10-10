import os
import re
from urllib.parse import quote, urlencode
from auth.security import decrypt_secret
from models.user import OAuthAccount
from fastapi import HTTPException
import httpx

from auth.oauth import OAuthError


SCOPES = "read:user user:email repo"


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

def get_github_token(db, user) -> str:
    account = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "github",
    ).first()

    token = decrypt_secret(account.access_token) if account and account.access_token else None
    if not token:
        raise HTTPException(status_code=403, detail="Connect your Github account first.")
    return token


def github_get(path: str, token: str, params: dict | None = None):
    response = httpx.get(
        f"https://api.github.com{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    if response.status_code == 401:
        raise HTTPException(status_code=403, detail="Github access was revoked. Reconnect Github.")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Respository or branch not found, or no access.")
    response.raise_for_status()
    return response.json()


REPO_FULL_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fetch_repo_config(token: str, full_name: str, branch: str | None = None) -> dict:
    if not REPO_FULL_NAME.match(full_name) or any(part in (".", "..") for part in full_name.split("/")):
        raise HTTPException(status_code=422, detail="Repository must look like 'owner/name'.")

    repo = github_get(f"/repos/{full_name}", token)
    branch = branch or repo["default_branch"]
    # Branch names may contain "/", so encode it as one path segment
    github_get(f"/repos/{repo['full_name']}/branches/{quote(branch, safe='')}", token)

    return {
        "repo_id": repo["id"],
        "repo_full_name": repo["full_name"],
        "repo_branch": branch,
        "repo_clone_url": repo["clone_url"],
        "repo_html_url": repo["html_url"],
        "repo_private": repo["private"],
    }


def fetch_latest_commit(token, full_name, branch):
    commits = github_get(
        f"/repos/{full_name}/commits",
        token,
        params={'sha': branch, "per_page": 1}
    )

    if not commits:
        raise HTTPException(
            status_code=404,
            detail="No commits found for this branch."
        )

    latest_commit = commits[0]["sha"]
    return latest_commit
    
