from fastapi import HTTPException
import redis
from sqlalchemy.orm import Session

from github.service import get_github_token
from github.webhook import delete_webhook
from models.deployment import Deployment
from models.project import Project
from models.user import User
from services.deployment_services import IN_PROGRESS_STATUSES
from services.queue import publish_cleanup


def delete_account(db: Session, user: User) -> None:
    """Remove a user, their projects, and everything those projects own.

    Raises HTTPException, leaving the account in place, if it can't be done yet."""
    projects = db.query(Project).filter(Project.user_id == user.id).all()
    project_ids = [project.id for project in projects]
    deployments = db.query(Deployment).filter(Deployment.project_id.in_(project_ids)).all()

    if any(deployment.status in IN_PROGRESS_STATUSES for deployment in deployments):
        raise HTTPException(status_code=409, detail="Wait for your running builds to finish first.")

    # Queue every removal before deleting the rows that point to the containers.
    try:
        for deployment in deployments:
            publish_cleanup(deployment.id)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Could not queue the containers' removal. Try again.") from None

    try:
        token = get_github_token(db, user)
    except HTTPException:
        token = None  # GitHub isn't connected, so there's nothing to clean up there.

    if token:
        for project in projects:
            delete_webhook(project.repo_full_name, project.webhook_id, token)

    # Deployments, OAuth accounts and sessions go with these (ON DELETE CASCADE).
    db.query(Project).filter(Project.user_id == user.id).delete()
    db.delete(user)
    db.commit()
