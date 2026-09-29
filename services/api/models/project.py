from database import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey



class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    