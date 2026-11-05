import hashlib
import hmac
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models.project import Project
from services.deployment_services import queue_deployment
from services.errors import DeploymentInProgress
from services.queue import redis_client

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    """True if the request was signed by GitHub with our webhook secret."""
    if not WEBHOOK_SECRET or not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def is_new_delivery(delivery_id: str) -> bool:
    """True the first time we see this delivery ID."""
    return bool(redis_client.set(f"github:delivery:{delivery_id}", "1", nx=True, ex=24 * 60 * 60))


def handle_push(db: Session, payload: dict) -> list[int]:
    """Queue a deployment for every project tracking the pushed branch. Returns their IDs."""
    if payload.get("deleted"):
        return []

    ref = payload["ref"]

    # Tags arrive as refs/tags/...; only branches are deployed.
    if not ref.startswith("refs/heads/"):
        return []

    branch = ref.removeprefix("refs/heads/")

    projects = db.query(Project).filter(
        Project.repo_id == payload["repository"]["id"],
        Project.repo_branch == branch,
    ).all()

    deployment_ids = []
    for project in projects:
        project_id = project.id
        try:
            deployment = queue_deployment(db, project, payload["after"])
        except DeploymentInProgress:
            logger.info("Skipped push for project %s: a deployment is in progress.", project_id)
            continue
        deployment_ids.append(deployment.id)

    return deployment_ids
