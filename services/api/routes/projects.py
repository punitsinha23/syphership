from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session
import redis
from auth.dependencies import get_current_user
from database import get_db
from models.user import User
from models.deployment import Deployment
from models.project import Project
from schemas.project import EnvVarsResponse, EnvVarsUpdate, ProjectCreate, ProjectCreated, ProjectResponse
from github.service import fetch_latest_commit, fetch_repo_config, get_github_token
from github.webhook import create_webhook, delete_webhook
from services.deployment_services import IN_PROGRESS_STATUSES, queue_deployment
from services.env_vars import MAX_ENV_VARS, read_env_vars, save_env_vars, validate_env_var
from services.errors import DeploymentError
from services.queue import publish_cleanup
from services.rate_limit import limit_by_user


router = APIRouter(prefix='/projects')



def _start_first_deployment(db: Session, project: Project, token: str) -> tuple[int | None, str | None]:
    """Deploy a new project's latest commit. Returns (deployment ID, warning).

    The project is already saved, so a failure here only becomes a warning:
    the user can fix the cause and press Deploy."""
    try:
        commit_sha = fetch_latest_commit(token, project.repo_full_name, project.repo_branch)
        return queue_deployment(db, project, commit_sha).id, None
    except DeploymentError as e:
        reason = str(e)
    except HTTPException as e:
        reason = e.detail
    except httpx.HTTPError:
        reason = "GitHub could not be reached."

    return None, f"Project created, but the first deployment didn't start. {reason}"


@router.post("/", response_model=ProjectCreated)
def create_projects(project: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo_fields = {}
    token = None

    if project.repo_full_name:
        token = get_github_token(db, user)
        repo_fields = fetch_repo_config(token, project.repo_full_name, project.repo_branch)
    elif project.repo_branch:
        raise HTTPException(status_code=422, detail="repo_branch requires repo_full_name")

    new_project = Project(
        name = project.name,
        description = project.description,
        user_id = user.id,
        auto_deploy = project.auto_deploy is not False,
        **repo_fields
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    first_deployment_id = None
    deployment_warning = None

    if token:
        create_webhook(db, new_project, token)
        if new_project.auto_deploy:
            first_deployment_id, deployment_warning = _start_first_deployment(db, new_project, token)
            db.refresh(new_project)

    return ProjectCreated(
        **ProjectResponse.model_validate(new_project).model_dump(),
        first_deployment_id=first_deployment_id,
        deployment_warning=deployment_warning,
    )

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
    if project.auto_deploy is not None:
        db_project.auto_deploy = project.auto_deploy

    old_repo_id = db_project.repo_id
    old_repo_name = db_project.repo_full_name
    old_webhook_id = db_project.webhook_id
    token = None

    # Omitted repo fields keep the current repo; a branch alone switches branch on it
    if project.repo_full_name or project.repo_branch:
        full_name = project.repo_full_name or db_project.repo_full_name
        if not full_name:
            raise HTTPException(status_code=422, detail="repo_branch requires repo_full_name")

        token = get_github_token(db, user)
        for field, value in fetch_repo_config(token, full_name, project.repo_branch).items():
            setattr(db_project, field, value)

        # A hook belongs to one repo, so moving to another repo needs a new one.
        if db_project.repo_id != old_repo_id:
            db_project.webhook_id = None
            db_project.webhook_secret = None

    db.commit()
    db.refresh(db_project)

    if token and db_project.repo_id != old_repo_id:
        delete_webhook(old_repo_name, old_webhook_id, token)
        create_webhook(db, db_project, token)

    return db_project


@router.post("/{project_id}/webhook", response_model=ProjectResponse, dependencies=[Depends(limit_by_user("webhook-setup", 10))])
def enable_webhook(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Create the push webhook for a project that doesn't have one yet."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.repo_full_name:
        raise HTTPException(status_code=400, detail="This project has no linked Github repository.")

    if project.webhook_id:
        return project

    if not create_webhook(db, project, get_github_token(db, user)):
        raise HTTPException(
            status_code=502,
            detail="Could not create the webhook. You need admin access to the repository.",
        )

    db.refresh(project)
    return project

def _owned_project(db: Session, project_id: int, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _env_vars_or_error(project: Project) -> dict[str, str]:
    try:
        return read_env_vars(project)
    except DeploymentError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/{project_id}/env", response_model=EnvVarsResponse)
def get_env_vars(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned_project(db, project_id, user)
    return {"names": sorted(_env_vars_or_error(project))}


@router.put("/{project_id}/env", response_model=EnvVarsResponse)
def update_env_vars(
    project_id: int,
    update: EnvVarsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set or delete variables. They apply from the next deployment."""
    project = _owned_project(db, project_id, user)
    env_vars = _env_vars_or_error(project)

    for name, value in update.variables.items():
        if value is None:
            env_vars.pop(name, None)
            continue

        problem = validate_env_var(name, value)
        if problem:
            raise HTTPException(status_code=422, detail=problem)
        env_vars[name] = value

    if len(env_vars) > MAX_ENV_VARS:
        raise HTTPException(status_code=422, detail=f"A project can have {MAX_ENV_VARS} variables.")

    save_env_vars(project, env_vars)
    db.commit()
    return {"names": sorted(env_vars)}


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

    # Queue every removal before deleting the rows that point to the containers.
    try:
        for deployment in deployments:
            publish_cleanup(deployment.id)
    except redis.exceptions.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Could not queue the containers' removal. Try again."
        ) from None

    if db_project.webhook_id:
        try:
            delete_webhook(db_project.repo_full_name, db_project.webhook_id, get_github_token(db, user))
        except HTTPException:
            # GitHub is disconnected. The leftover hook only gets 401s from now on.
            pass

    # Deployments are removed by the database (ON DELETE CASCADE).
    db.delete(db_project)
    db.commit()

    return {"message" : "Project deleted"}

    



            
            