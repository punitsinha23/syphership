import re

import redis
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from github.service import fetch_latest_commit, get_github_token
from models.deployment import Deployment
from models.project import Project
from schemas.deployment import (
    DeploymentCreate,
    DeploymentLogsResponse,
    DeploymentResponse,
)
from services.deployment_services import IN_PROGRESS_STATUSES, queue_deployment
from services.errors import AppLimitReached, DeploymentInProgress, QueueUnavailable
from services.log_stream import end_event, read_events, stream_exists
from services.queue import publish_cleanup
from services.rate_limit import limit_by_user

router = APIRouter(prefix="/deployments")

DEPLOYMENT_IN_PROGRESS = "A deployment of this project is already in progress."


@router.post("/", response_model=DeploymentResponse, dependencies=[Depends(limit_by_user("deploy", 5))])
def create_deployment(
    deployment: DeploymentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == deployment.project_id,
        Project.user_id == user.id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found."
        )

    if not project.repo_full_name or not project.repo_branch:
        raise HTTPException(status_code=400,
        detail="This project has no linked Github repository or branch.")

    in_progress = db.query(Deployment.id).filter(
        Deployment.project_id == project.id,
        Deployment.status.in_(IN_PROGRESS_STATUSES)
    ).first()

    if in_progress is not None:
        raise HTTPException(status_code=409, detail=DEPLOYMENT_IN_PROGRESS)

    token = get_github_token(db, user)
    commit_sha = fetch_latest_commit(token, project.repo_full_name, project.repo_branch)

    try:
        return queue_deployment(db, project, commit_sha)
    except AppLimitReached as e:
        raise HTTPException(status_code=403, detail=str(e)) from None
    except DeploymentInProgress as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except QueueUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from None


@router.get("/", response_model=list[DeploymentResponse])
def get_deployments(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Deployment).join(Project).filter(
        Project.user_id == user.id
    )

    if project_id is not None:
        query = query.filter(Deployment.project_id == project_id)

    return query.order_by(Deployment.created_at.desc(), Deployment.id.desc()).all()


@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deployment_db = db.query(Deployment).join(Project).filter(
        Deployment.id == deployment_id,
        Project.user_id == user.id
    ).first()

    if deployment_db is None:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )

    return deployment_db


@router.get("/{deployment_id}/logs", response_model=DeploymentLogsResponse)
def get_deployment_logs(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deployment_db = db.query(Deployment).join(Project).filter(
        Deployment.id == deployment_id,
        Project.user_id == user.id
    ).first()

    if deployment_db is None:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )

    return deployment_db

# A Redis Stream entry ID, e.g. "1794840605158-0"
STREAM_ID = re.compile(r"\d+-\d+")


@router.get("/{deployment_id}/logs/stream")
def stream_deployment_logs(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    last_event_id: str | None = Header(default=None),
):
    """The build output as Server-Sent Events, live while the build runs.

    Sends the lines printed so far, then each new one as it appears, then an
    "end" event. A client that reconnects sends Last-Event-ID to resume."""
    deployment_db = db.query(Deployment).join(Project).filter(
        Deployment.id == deployment_id,
        Project.user_id == user.id
    ).first()

    if deployment_db is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Finished and nothing live left: the stored log (GET .../logs) has it all.
    finished = deployment_db.status not in IN_PROGRESS_STATUSES
    if finished and not stream_exists(deployment_id):
        events = iter([end_event()])
    else:
        start = last_event_id if last_event_id and STREAM_ID.fullmatch(last_event_id) else "0"
        events = read_events(deployment_id, start)

    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Tell proxies not to hold lines back until the response ends.
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{deployment_id}")
def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deployment_db = db.query(Deployment).join(Project).filter(
        Deployment.id == deployment_id,
        Project.user_id == user.id
    ).first()

    if deployment_db is None:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )

    # The runner is still working on it and would recreate the container.
    if deployment_db.status in IN_PROGRESS_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Wait for this deployment to finish before deleting it."
        )

    # Queue the removal first so a failure never leaves the container running unseen.
    try:
        publish_cleanup(deployment_db.id)
    except redis.exceptions.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Could not queue the container's removal. Try again."
        ) from None

    db.delete(deployment_db)
    db.commit()

    return {"message": "Deployment deleted"}
