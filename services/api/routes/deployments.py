from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentStatusUpdate
from auth.dependencies import get_current_user
from services.deployment_services import update_deployment_status
from services.deployment_runner import run_deployment
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

@router.patch( "/{deployment_id}/status", response_model=DeploymentResponse)
def update_status(
    deployment_id: int,
    status_update: DeploymentStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deployment_db = db.query(Deployment).join(Project).filter(
        Deployment.id == deployment_id,
        Project.user_id == user.id
    ).with_for_update(of=Deployment).first()

    if deployment_db is None:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )

    try:
        update_deployment_status(
            deployment_db,
            status_update.status,
            status_update.failure_reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    db.commit()
    db.refresh(deployment_db)

    return deployment_db