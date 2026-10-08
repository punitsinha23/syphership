from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from auth.dependencies import get_current_user
from auth.oauth import complete_oauth, connect_url_response, redirect_to_provider
from github.service import get_github_auth_url, fetch_github_identity


router = APIRouter(prefix="/github", tags=["GitHub"])


@router.get("/login")
def github_login():
    return redirect_to_provider("github", get_github_auth_url)


@router.post("/connect")
def github_connect(user: User = Depends(get_current_user)):
    return connect_url_response("github", get_github_auth_url, user)


@router.get("/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    return complete_oauth(request, db, "github", code, state, error, fetch_github_identity)
