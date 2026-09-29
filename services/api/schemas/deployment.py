from pydantic import BaseModel, model_validator
from models.deployment import DeploymentStatus
from datetime import datetime

class DeploymentCreate(BaseModel):
    project_id: int
    commit_sha: str

class DeploymentResponse(BaseModel):
    id: int
    project_id: int
    status: DeploymentStatus
    commit_sha: str
    created_at: datetime
    updated_at: datetime
    failure_reason: str | None

class DeploymentStatusUpdate(BaseModel):
    status: DeploymentStatus
    failure_reason: str | None = None

    @model_validator(mode="after")
    def check_failure_reason(self):
        if self.status == DeploymentStatus.FAILED and not self.failure_reason:
            raise ValueError("failure_reason is required when status is FAILED")
        if self.status != DeploymentStatus.FAILED and self.failure_reason:
            raise ValueError("failure_reason is only allowed when status is FAILED")
        return self
