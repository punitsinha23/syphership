from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, get_db
from models.user import User
from models.project import Project
from models.deployment import Deployment
from auth.routes import router as auth_router
from routes.projects import router as project_router
from routes.deployments import router as deployment_router
from github.routes import router as github_router
from google_oauth.routes import router as google_router
from auth.oauth import FRONTEND_URL
from services.deployment_runner import fail_interrupted_deployments

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A restart kills in-process builds; don't leave their rows stuck in progress.
    db = SessionLocal()
    try:
        fail_interrupted_deployments(db)
    except Exception:
        logger.exception("Could not clean up interrupted deployments.")
    finally:
        db.close()

    yield


app = FastAPI(title="Syphership API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(deployment_router)
app.include_router(github_router)
app.include_router(google_router)



@app.get('/')
def root(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {
        "message": "Syphership API is running",
        "database": result.scalar(),
    }