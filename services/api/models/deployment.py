from enum import Enum
from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from datetime import datetime, timezone

class DeploymentStatus(str, Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(DeploymentStatus), nullable=False)
    commit_sha = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    failure_reason = Column(String)

