from database import Base
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, DateTime, ForeignKey



class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Linked GitHub repository (all null for projects without one)
    repo_id = Column(BigInteger)          # GitHub's repo id (can exceed 32-bit int)
    repo_full_name = Column(String)       # "owner/name"
    repo_branch = Column(String)
    repo_clone_url = Column(String)
    repo_html_url = Column(String)
    repo_private = Column(Boolean)
