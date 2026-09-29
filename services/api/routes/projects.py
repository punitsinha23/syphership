from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.routes import get_current_user
from database import get_db
from models.user import User
from models.project import Project
from schemas.project import ProjectCreate, ProjectResponse


router = APIRouter(prefix='/projects')



@router.post("/", response_model=ProjectResponse)
def create_projects(project: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):


    new_project = Project(
        name = project.name,
        description = project.description,
        user_id = user.id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project

@router.get("/", response_model=list[ProjectResponse])
def get_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.user_id == user.id).all()
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

    db.delete(db_project)
    db.commit()

    return {"message" : "Project deleted"}

    



            
            