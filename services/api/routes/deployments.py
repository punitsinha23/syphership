from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import redis

from database import get_db
from models.deployment import Deployment
from models.project import Project
from schemas.deployment import (
    DeploymentCreate,
    DeploymentLogsResponse,
    DeploymentResponse,
)
from auth.dependencies import get_current_user
from services.deployment_services import IN_PROGRESS_STATUSES, queue_deployment
from services.errors import AppLimitReached, DeploymentInProgress, QueueUnavailable
from services.queue import publish_cleanup
from services.rate_limit import limit_by_user
from github.service import get_github_token, fetch_latest_commit



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
