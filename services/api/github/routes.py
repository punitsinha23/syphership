from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from auth.dependencies import get_current_user
from auth.oauth import complete_oauth, connect_url_response, redirect_to_provider
from github.service import get_github_auth_url, fetch_github_identity, get_github_token, github_get


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


@router.get("/repos")
def list_repos(page: int = 1, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_github_token(db, user)
    repos = github_get("/user/repos", token, {'per_page': 100, 'page': page, 'sort': 'updated'})
    return[
        {
            "id": r["id"],
            "full_name": r["full_name"],
            "name": r["name"],
            "private": r["private"],
            "default_branch": r["default_branch"],
        }
        for r in repos
    ]


@router.get("/repos/{owner}/{repo}/branches")
def list_branches(owner: str, repo: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = get_github_token(db, user)
    branches = github_get(f"/repos/{owner}/{repo}/branches", token, {"per_page": 100})
    return [b["name"] for b in branches]
