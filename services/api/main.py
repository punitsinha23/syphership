from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models.user import User
from models.project import Project
from models.deployment import Deployment
from auth.routes import router as auth_router
from routes.projects import router as project_router
from routes.deployments import router as deployment_router

app = FastAPI(title="Syphership API")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(deployment_router)

print(Base.metadata.tables.keys())
Base.metadata.create_all(bind=engine)


@app.get('/')
def root(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {
        "message": "Syphership API is running",
        "database": result.scalar(),
    }