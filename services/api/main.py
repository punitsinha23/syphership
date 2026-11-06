from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from database import get_db
from models.user import User
from models.project import Project
from models.deployment import Deployment
from auth.routes import router as auth_router
from routes.projects import router as project_router
from routes.deployments import router as deployment_router
from github.routes import router as github_router
from google_oauth.routes import router as google_router
from auth.oauth import FRONTEND_URL

load_dotenv()

app = FastAPI(title="Syphership API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Browsers ignore this over plain HTTP, so it's safe in development.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

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