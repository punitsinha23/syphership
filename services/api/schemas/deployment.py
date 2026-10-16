from pydantic import BaseModel
from models.deployment import DeploymentStatus
from datetime import datetime

class DeploymentCreate(BaseModel):
    project_id: int
    

class DeploymentResponse(BaseModel):
    id: int
    project_id: int
    status: DeploymentStatus
    commit_sha: str
    url: str | None
    created_at: datetime
    updated_at: datetime
    failure_reason: str | None

class DeploymentLogsResponse(BaseModel):
    id: int
    status: DeploymentStatus
    build_logs: str | None
