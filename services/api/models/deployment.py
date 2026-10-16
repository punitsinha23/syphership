from enum import Enum
from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from datetime import datetime, timezone

class DeploymentStatus(str, Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    # Replaced by a newer deployment of the same project; container removed.
    STOPPED = "STOPPED"

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(SQLEnum(DeploymentStatus), nullable=False)
    commit_sha = Column(String, nullable=False)

    container_id = Column(String, nullable=True)
    host_port = Column(Integer, nullable=True)
    url = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    failure_reason = Column(String)
    build_logs = Column(Text, nullable=True)
