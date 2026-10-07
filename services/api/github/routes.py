from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from urllib.parse import urlencode

from database import get_db
from models.user import User
from auth.security import create_token
from auth.dependencies import get_user_by_email

from github.service import (
    get_github_auth_url,
    exchange_code_for_token,
    get_github_user,
    get_github_emails,
)


router = APIRouter(prefix="/github", tags=["GitHub"])


@router.get("/login")
def github_login():
    authorization_url = get_github_auth_url()

    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def github_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    # Exchange GitHub authorization code for access token
    token_data = await exchange_code_for_token(code)

    if "access_token" not in token_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to obtain access token from GitHub",
        )

    github_token = token_data["access_token"]

    # Get GitHub user information
    github_user = await get_github_user(github_token)

    if not github_user:
        raise HTTPException(
            status_code=400,
            detail="Failed to fetch GitHub user info",
        )

    username = github_user.get("login")

    # GitHub may return email=None from /user,
    # so fetch the user's emails separately.
    emails = await get_github_emails(github_token)

    primary_email = next(
        (
            email_data["email"]
            for email_data in emails
            if email_data.get("primary")
            and email_data.get("verified")
        ),
        None,
    )

    if not username or not primary_email:
        raise HTTPException(
            status_code=400,
            detail="GitHub account missing required info",
        )

    email = primary_email

    # Check if Syphership user already exists
    user = get_user_by_email(email, db)

    # Create user if they don't exist
    if not user:
        user = User(
            email=email,
            username=username,
            password_hash="github_oauth",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # Create Syphership JWT tokens
    access_token = create_token(
        {"sub": user.email},
        expire_delta=timedelta(hours=1),
        token_type="access",
    )

    refresh_token = create_token(
        {"sub": user.email},
        expire_delta=timedelta(days=7),
        token_type="refresh",
    )

    # Redirect back to frontend
    params = urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
    })

    return RedirectResponse(
        url=f"http://localhost:5173/auth/github/callback?{params}"
    )