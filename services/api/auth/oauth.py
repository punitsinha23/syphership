import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlencode

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.security import create_token, verify_token, encrypt_secret
from models.user import User, OAuthAccount, LoginCode


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

STATE_COOKIE = "oauth_state"
STATE_TTL = timedelta(minutes=10)
LOGIN_CODE_TTL = timedelta(seconds=60)

PROVIDER_NAMES = {"github": "GitHub", "google": "Google"}


class OAuthError(Exception):
    """A sign-in failure whose message is safe to show to the user."""


# ---------- state (CSRF protection) ----------

def _new_state(provider: str, link_user_id: int | None) -> tuple[str, str]:
    """Return (state, nonce). The state is a signed JWT carrying the nonce that
    is also stored in a cookie, so a callback is only accepted in the browser
    that started the flow."""
    nonce = secrets.token_urlsafe(32)
    claims = {"nonce": nonce, "provider": provider}
    if link_user_id is not None:
        claims["link_user_id"] = link_user_id
    return create_token(claims, STATE_TTL, "oauth_state"), nonce


def _set_state_cookie(response, nonce: str):
    response.set_cookie(
        STATE_COOKIE,
        nonce,
        max_age=int(STATE_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=FRONTEND_URL.startswith("https://"),
    )


def _check_state(request: Request, state: str | None, provider: str) -> dict:
    payload = verify_token(state, "oauth_state") if state else None
    cookie_nonce = request.cookies.get(STATE_COOKIE)

    if (
        payload is None
        or payload.get("provider") != provider
        or not cookie_nonce
        or not secrets.compare_digest(cookie_nonce, payload.get("nonce", ""))
    ):
        raise OAuthError("Sign-in request expired or is invalid. Please try again.")

    return payload


# ---------- responses ----------

def frontend_redirect(**params) -> RedirectResponse:
    response = RedirectResponse(f"{FRONTEND_URL}/auth/callback?{urlencode(params)}")
    response.delete_cookie(STATE_COOKIE)
    return response


def redirect_to_provider(provider: str, build_auth_url: Callable[[str], str]):
    """Start a sign-in flow from a top-level browser navigation."""
    try:
        state, nonce = _new_state(provider, None)
        response = RedirectResponse(build_auth_url(state))
    except OAuthError as e:
        return frontend_redirect(error=str(e))

    _set_state_cookie(response, nonce)
    return response


def connect_url_response(provider: str, build_auth_url: Callable[[str], str], user: User):
    """Start a flow that links the provider to an already signed-in user.
    Called with fetch(credentials: "include") so the state cookie is set."""
    try:
        state, nonce = _new_state(provider, user.id)
        response = JSONResponse({"url": build_auth_url(state)})
    except OAuthError as e:
        return JSONResponse({"detail": str(e)}, status_code=503)

    _set_state_cookie(response, nonce)
    return response


def complete_oauth(
    request: Request,
    db: Session,
    provider: str,
    code: str | None,
    state: str | None,
    error: str | None,
    fetch_identity: Callable[[str], dict],
) -> RedirectResponse:
    """Shared callback handler. fetch_identity(code) exchanges the code with the
    provider and returns provider_user_id, email, username_hint, avatar_url and
    access_token (None if it shouldn't be stored)."""
    name = PROVIDER_NAMES[provider]

    try:
        if error:
            raise OAuthError(f"{name} sign-in was cancelled.")

        payload = _check_state(request, state, provider)

        if not code:
            raise OAuthError(f"{name} did not return an authorization code.")

        try:
            identity = fetch_identity(code)
        except httpx.HTTPError:
            raise OAuthError(f"Could not reach {name}. Please try again.")

        link_user_id = payload.get("link_user_id")
        user = sign_in_with_provider(db, provider=provider, link_user_id=link_user_id, **identity)
    except OAuthError as e:
        return frontend_redirect(error=str(e))

    if link_user_id is not None:
        return frontend_redirect(connected=provider)

    return frontend_redirect(code=issue_login_code(db, user))


# ---------- users & accounts ----------

def unique_username(db: Session, hint: str | None) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]", "", hint or "")[:30] or "user"
    candidate = base
    n = 2
    while db.query(User.id).filter(User.username == candidate).first():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def sign_in_with_provider(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str | None,
    username_hint: str | None,
    avatar_url: str | None,
    access_token: str | None,
    link_user_id: int | None = None,
) -> User:
    name = PROVIDER_NAMES[provider]
    provider_user_id = str(provider_user_id)
    email = email.lower() if email else None

    account = db.query(OAuthAccount).filter(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    ).first()

    if link_user_id is not None:
        # "Connect <provider>" from a signed-in session
        user = db.get(User, link_user_id)
        if user is None:
            raise OAuthError("Your session has expired. Please sign in again.")
        if account is not None and account.user_id != user.id:
            raise OAuthError(f"This {name} account is already linked to another Syphership account.")

    elif account is not None:
        # Returning user
        user = db.get(User, account.user_id)

    else:
        # First sign-in with this provider account. Both providers only give us
        # verified emails, so an existing user with the same email is the same person.
        if not email:
            raise OAuthError(f"Your {name} account has no verified email address.")

        user = db.query(User).filter(User.email == email).first()

        if user is None:
            user = User(
                email=email,
                username=unique_username(db, username_hint),
                avatar_url=avatar_url,
            )
            db.add(user)
            db.flush()

    if account is None:
        already_linked = db.query(OAuthAccount.id).filter(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == provider,
        ).first()
        if already_linked:
            raise OAuthError(f"This Syphership account is already connected to a different {name} account.")

        account = OAuthAccount(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
        db.add(account)

    if access_token is not None:
        account.access_token = encrypt_secret(access_token)

    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url

    try:
        db.commit()
    except IntegrityError:
        # Concurrent sign-in created the same user/account first
        db.rollback()
        raise OAuthError("Sign-in conflicted with another request. Please try again.")

    db.refresh(user)
    return user


# ---------- one-time login codes ----------

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def issue_login_code(db: Session, user: User) -> str:
    now = datetime.now(timezone.utc)
    code = secrets.token_urlsafe(32)

    db.execute(delete(LoginCode).where(LoginCode.expires_at < now))
    db.add(LoginCode(code_hash=_hash_code(code), user_id=user.id, expires_at=now + LOGIN_CODE_TTL))
    db.commit()

    return code


def redeem_login_code(db: Session, code: str) -> int | None:
    """Consume a login code atomically; returns the user id, or None if invalid/expired."""
    row = db.execute(
        delete(LoginCode)
        .where(LoginCode.code_hash == _hash_code(code))
        .returning(LoginCode.user_id, LoginCode.expires_at)
    ).first()
    db.commit()

    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None

    return row.user_id
