from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from auth.oauth import complete_oauth, redirect_to_provider
from google_oauth.service import get_google_auth_url, fetch_google_identity


router = APIRouter(prefix="/google", tags=["Google"])


@router.get("/login")
def google_login():
    return redirect_to_provider("google", get_google_auth_url)


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    return complete_oauth(request, db, "google", code, state, error, fetch_google_identity)
