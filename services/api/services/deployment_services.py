import os

import redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services.errors import AppLimitReached, DeploymentInProgress, QueueUnavailable
from services.queue import publish

ALLOWED_TRANSITIONS = {
    DeploymentStatus.QUEUED: [
        DeploymentStatus.BUILDING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.BUILDING: [
        DeploymentStatus.DEPLOYING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.DEPLOYING: [
        DeploymentStatus.RUNNING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.RUNNING: [
        DeploymentStatus.STOPPED,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.FAILED: [],
    DeploymentStatus.STOPPED: []
}

IN_PROGRESS_STATUSES = (
    DeploymentStatus.QUEUED,
    DeploymentStatus.BUILDING,
    DeploymentStatus.DEPLOYING,
)


# How many different projects one user can have live or building at once.
MAX_APPS_PER_USER = int(os.getenv("MAX_APPS_PER_USER", "3"))


def update_deployment_status(deployment, new_status: DeploymentStatus, failure_reason: str | None = None):
    if new_status not in ALLOWED_TRANSITIONS[deployment.status]:
        raise ValueError('Invalid deployment status transition')

    if new_status == DeploymentStatus.FAILED:
        deployment.failed_stage = deployment.status
        deployment.failure_reason = failure_reason

    deployment.status = new_status


def save_container_id(deployment, container_id:str) -> None:
    if not isinstance(container_id, str) or not container_id.strip():
        raise ValueError("Invalid container ID.")


    deployment.container_id = container_id.strip()


def _other_active_apps(db: Session, project: Project) -> int:
    """The owner's other projects that are live or building.

    This project isn't counted: a new deployment replaces its old one."""

    return (
        db.query(Deployment.project_id)
        .join(Project)
        .filter(
            Project.user_id == project.user_id,
            Deployment.project_id != project.id,
            Deployment.status.in_((*IN_PROGRESS_STATUSES, DeploymentStatus.RUNNING)),
        )
        .distinct()
        .count()
    )


def queue_deployment(db: Session, project: Project, commit_sha: str) -> Deployment:
    """Create a QUEUED deployment and publish it to the build queue.

    Raises AppLimitReached, DeploymentInProgress or QueueUnavailable."""

    if _other_active_apps(db, project) >= MAX_APPS_PER_USER:
        raise AppLimitReached(f"You can have {MAX_APPS_PER_USER} apps running. Delete one to deploy another.")

    deployment = Deployment(
        project_id=project.id,
        commit_sha=commit_sha,
        status=DeploymentStatus.QUEUED,
    )
    db.add(deployment)

    try:
        db.commit()
    except IntegrityError:
        # The unique index allows one in-progress deployment per project.
        db.rollback()
        raise DeploymentInProgress("A deployment of this project is already in progress.") from None

    db.refresh(deployment)

    try:
        publish(deployment.id)
    except redis.exceptions.RedisError:
        update_deployment_status(
            deployment,
            DeploymentStatus.FAILED,
            "Build queue was unavailable. Deploy again.",
        )
        db.commit()
        raise QueueUnavailable("Build queue is unavailable. Try again.") from None

    return deployment
