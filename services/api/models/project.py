from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text

from database import Base


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Linked GitHub repository (all null for projects without one)
    repo_id = Column(BigInteger)          # GitHub's repo id (can exceed 32-bit int)
    repo_full_name = Column(String)       # "owner/name"
    repo_branch = Column(String)
    repo_clone_url = Column(String)
    repo_html_url = Column(String)
    repo_private = Column(Boolean)

    # The push webhook Syphership created on the repo (null if there is none)
    webhook_id = Column(BigInteger)
    webhook_secret = Column(String)       # Encrypted; unique to this project
    auto_deploy = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Encrypted JSON object of the app's environment variables
    env_vars = Column(Text)

    @property
    def webhook_active(self) -> bool:
        return self.webhook_id is not None
