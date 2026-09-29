from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentStatusUpdate
from auth.dependencies import get_current_user
from services.deployment_services import update_deployment_status


router = APIRouter(prefix="/deployments")


@router.post("/", response_model=DeploymentResponse)
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

    new_deployment = Deployment(
        project_id=project.id,
        commit_sha=deployment.commit_sha,
        status=DeploymentStatus.QUEUED
    )

    db.add(new_deployment)
    db.commit()
    db.refresh(new_deployment)

    return new_deployment


@router.get("/", response_model=list[DeploymentResponse])
def get_deployments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deployments = db.query(Deployment).join(Project).filter(
        Project.user_id == user.id
    ).all()

    return deployments


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
    ).first()

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