from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    repo_full_name: str | None = None
    repo_branch: str | None = None
    auto_deploy: bool | None = None


class EnvVarsUpdate(BaseModel):
    """Variables to set; a null value deletes that variable."""

    variables: dict[str, str | None]


class EnvVarsResponse(BaseModel):
    """Names only: saved values never leave the server."""

    names: list[str]


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str
    created_at: datetime
    repo_full_name: str | None = None
    repo_branch: str | None = None
    repo_html_url: str | None = None
    repo_private: bool | None = None
    auto_deploy: bool
    webhook_active: bool


class ProjectCreated(ProjectResponse):
    """A new project, and what happened to its first deployment."""

    first_deployment_id: int | None = None
    deployment_warning: str | None = None
