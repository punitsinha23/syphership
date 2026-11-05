import json

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from auth.dependencies import get_current_user
from auth.oauth import complete_oauth, connect_url_response, redirect_to_provider
from github.service import get_github_auth_url, fetch_github_identity, get_github_token, github_get
from github.webhook import handle_push, is_new_delivery, verify_signature
from services.errors import QueueUnavailable
from services.rate_limit import limit_by_ip


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


@router.post("/webhook", dependencies=[Depends(limit_by_ip("webhook", 60))])
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """Called by GitHub, not a user: the signature replaces login."""
    # Raw bytes: GitHub signed exactly these, so don't parse them first.
    body = await request.body()
    if not verify_signature(body=body, signature_header=request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    # Checked after the signature, so unsigned requests can't fill Redis with IDs.
    # Repeats get 200: the delivery was already handled, so it isn't an error.
    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id or not is_new_delivery(delivery_id):
        return {"ok": True, "duplicate": True}

    event = request.headers.get("X-GitHub-Event")
    if event == "ping":
        # Sent once when the webhook is added on GitHub.
        return {"ok": True}

    if event == "push":
        try:
            deployment_ids = handle_push(db, json.loads(body))
        except QueueUnavailable as e:
            # Shows the delivery as failed on GitHub's webhook page. Redelivering it
            # won't help (same delivery ID, so it counts as a repeat): push again or deploy by hand.
            raise HTTPException(status_code=503, detail=str(e)) from None
        return {"ok": True, "deployments": deployment_ids}

    return {"ok": True}
