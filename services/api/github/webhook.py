import hashlib
import hmac
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
import httpx
from sqlalchemy.orm import Session

from auth.security import decrypt_secret, encrypt_secret
from github.service import github_delete, github_post
from models.project import Project
from services.deployment_services import queue_deployment
from services.errors import AppLimitReached, DeploymentInProgress
from services.queue import redis_client
from services.validation import is_valid_sha

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


logger = logging.getLogger(__name__)

# Where GitHub can reach this API. Without it, webhooks can't be created.
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "").rstrip("/")


def verify_signature(secret: str | None, body: bytes, signature_header: str | None) -> bool:
    """True if the request was signed by GitHub with this project's secret."""
    if not secret or not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def project_secret(project: Project | None) -> str | None:
    """The project's webhook secret; None if it has no webhook."""
    if project is None or not project.webhook_secret:
        return None
    return decrypt_secret(project.webhook_secret)


def is_new_delivery(project_id: int, delivery_id: str) -> bool:
    """True the first time this project sees this delivery ID."""
    key = f"github:delivery:{project_id}:{delivery_id}"
    return bool(redis_client.set(key, "1", nx=True, ex=24 * 60 * 60))


def handle_push(db: Session, project: Project, payload: dict) -> list[int]:
    """Queue a deployment if this push is for the project's branch. Returns the new IDs."""
    project_id = project.id

    if not project.auto_deploy or payload.get("deleted"):
        return []

    ref = payload["ref"]

    # Tags arrive as refs/tags/...; only branches are deployed.
    if not ref.startswith("refs/heads/"):
        return []

    if not is_valid_sha(payload["after"]):
        logger.warning("Ignored push with an invalid commit SHA.")
        return []

    branch = ref.removeprefix("refs/heads/")

    if payload["repository"]["id"] != project.repo_id or branch != project.repo_branch:
        return []

    try:
        deployment = queue_deployment(db, project, payload["after"])
    except (DeploymentInProgress, AppLimitReached) as error:
        logger.info("Skipped push for project %s: %s", project_id, error)
        return []

    return [deployment.id]


def create_webhook(db: Session, project: Project, token: str) -> bool:
    """Create the repo's push webhook with the user's token. False if it failed.

    A failure never blocks the project: manual deploys still work. GitHub
    refuses when the user isn't an admin of the repo."""
    if not PUBLIC_API_URL or not project.repo_full_name or project.webhook_id:
        return False

    secret = secrets.token_hex(32)

    try:
        hook = github_post(
            f"/repos/{project.repo_full_name}/hooks",
            token,
            {
                "name": "web",
                "active": True,
                "events": ["push"],
                "config": {
                    "url": f"{PUBLIC_API_URL}/github/webhook/{project.id}",
                    "content_type": "json",
                    "secret": secret,
                    "insecure_ssl": "0",
                },
            },
        )
    except (HTTPException, httpx.HTTPError) as error:
        logger.warning("Could not create a webhook for project %s: %s", project.id, error)
        return False

    project.webhook_id = hook["id"]
    project.webhook_secret = encrypt_secret(secret)
    db.commit()
    return True


def delete_webhook(repo_full_name: str | None, webhook_id: int | None, token: str) -> None:
    """Remove a webhook from GitHub. Failure only leaves a hook that gets 401s."""
    if not repo_full_name or not webhook_id:
        return

    try:
        github_delete(f"/repos/{repo_full_name}/hooks/{webhook_id}", token)
    except (HTTPException, httpx.HTTPError) as error:
        logger.warning("Could not delete webhook %s on %s: %s", webhook_id, repo_full_name, error)
