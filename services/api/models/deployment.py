from enum import Enum
from database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Index, text
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
    __table_args__ = (
        # At most one queued/building/deploying deployment per project.
        Index(
            "uq_deployments_one_in_progress_per_project",
            "project_id",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'BUILDING', 'DEPLOYING')"),
        ),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(SQLEnum(DeploymentStatus), nullable=False, index=True)
    commit_sha = Column(String, nullable=False)

    container_id = Column(String, nullable=True)
    host_port = Column(Integer, nullable=True)
    url = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    failure_reason = Column(String)
    # Status the deployment was in when it failed, so the UI can show the failed stage.
    failed_stage = Column(SQLEnum(DeploymentStatus), nullable=True)
    build_logs = Column(Text, nullable=True)
