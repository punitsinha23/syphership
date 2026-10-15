from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from models.deployment import Deployment
from models.project import Project
from schemas.project import ProjectCreate, ProjectResponse
from github.service import fetch_repo_config, get_github_token
from services.deployment_services import IN_PROGRESS_STATUSES
from services.docker_services import remove_deployment_resources


router = APIRouter(prefix='/projects')



@router.post("/", response_model=ProjectResponse)
def create_projects(project: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo_fields = {}

    if project.repo_full_name:
        token = get_github_token(db, user)
        repo_fields = fetch_repo_config(token, project.repo_full_name, project.repo_branch)
    elif project.repo_branch:
        raise HTTPException(status_code=422, detail="repo_branch requires repo_full_name")

    new_project = Project(
        name = project.name,
        description = project.description,
        user_id = user.id,
        **repo_fields
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project

@router.get("/", response_model=list[ProjectResponse])
def get_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc(), Project.id.desc()).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):

    db_project = db.query(Project).filter(
    Project.id == project_id,
    Project.user_id == user.id
    ).first()

    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_project.name = project.name
    db_project.description = project.description

    # Omitted repo fields keep the current repo; a branch alone switches branch on it
    if project.repo_full_name or project.repo_branch:
        full_name = project.repo_full_name or db_project.repo_full_name
        if not full_name:
            raise HTTPException(status_code=422, detail="repo_branch requires repo_full_name")

        token = get_github_token(db, user)
        for field, value in fetch_repo_config(token, full_name, project.repo_branch).items():
            setattr(db_project, field, value)

    db.commit()
    db.refresh(db_project)

    return db_project

@router.delete("/{project_id}")  
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id
    ).first()

    if not db_project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    deployments = db.query(Deployment).filter(
        Deployment.project_id == db_project.id
    ).all()

    # A running build would keep going after its project is gone.
    if any(deployment.status in IN_PROGRESS_STATUSES for deployment in deployments):
        raise HTTPException(
            status_code=409,
            detail="Wait for the current deployment to finish before deleting this project."
        )

    # Remove every container and image before the rows that point to them.
    try:
        for deployment in deployments:
            remove_deployment_resources(deployment.id)
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Could not remove the project's containers. Try again."
        ) from None

    # Deployments are removed by the database (ON DELETE CASCADE).
    db.delete(db_project)
    db.commit()

    return {"message" : "Project deleted"}

    



            
            