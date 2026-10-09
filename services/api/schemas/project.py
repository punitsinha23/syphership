from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    repo_full_name: str | None = None
    repo_branch: str | None = None


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
