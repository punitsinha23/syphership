from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from schemas.deployment import (
    DeploymentCreate,
    DeploymentLogsResponse,
    DeploymentResponse,
)
from auth.dependencies import get_current_user
from services.deployment_services import IN_PROGRESS_STATUSES
from services.deployment_runner import run_deployment
from services.docker_services import remove_deployment_resources
from github.service import get_github_token, fetch_latest_commit



router = APIRouter(prefix="/deployments")


@router.post("/", response_model=DeploymentResponse)
def create_deployment(
    background_tasks : BackgroundTasks,
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

    token = get_github_token(db, user)
    commit_sha = fetch_latest_commit(token, project.repo_full_name, project.repo_branch)
    
    new_deployment = Deployment(
        project_id=project.id,
        commit_sha=commit_sha,
        status=DeploymentStatus.QUEUED
    )

    db.add(new_deployment)
    db.commit()
    db.refresh(new_deployment)
    background_tasks.add_task(run_deployment, new_deployment.id)
    return new_deployment


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

    # Remove the container first so a failure never leaves it running unseen.
    try:
        remove_deployment_resources(deployment_db.id)
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Could not remove the deployment's container. Try again."
        ) from None

    db.delete(deployment_db)
    db.commit()

    return {"message": "Deployment deleted"}
