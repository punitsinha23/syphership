from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    name: str
    description: str
    created_at: datetime