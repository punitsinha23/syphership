import hmac
import logging
import os
import re
import time

import redis
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.oauth import FRONTEND_URL
from auth.routes import router as auth_router
from database import get_db
from github.routes import router as github_router
from google_oauth.routes import router as google_router
from routes.deployments import router as deployment_router
from routes.projects import router as project_router
from routes.wake import router as wake_router
from services.logging_setup import new_request_id, request_id_var, setup_logging
from services.metrics import HTTP_LATENCY, HTTP_REQUESTS
from services.queue import redis_client

load_dotenv()
setup_logging()

logger = logging.getLogger("syphership.api")

# Set in production; Prometheus sends it as "Authorization: Bearer <token>".
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

# A request ID from outside is only reused if it looks like one.
REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")

app = FastAPI(title="Syphership API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    """Give each request an ID, time it, count it for /metrics, log one line."""
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if REQUEST_ID.fullmatch(incoming) else new_request_id()
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    status = 500

    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration = time.perf_counter() - started
        # The route template (/deployments/{deployment_id}), not the real path:
        # one series per endpoint instead of one per ID.
        route = request.scope.get("route")
        route_path = route.path if route is not None else "unmatched"

        HTTP_REQUESTS.labels(request.method, route_path, str(status)).inc()
        HTTP_LATENCY.labels(request.method, route_path).observe(duration)
        if route_path not in ("/health", "/ready", "/metrics"):
            logger.info(
                "%s %s %s",
                request.method,
                route_path,
                status,
                extra={
                    "method": request.method,
                    "route": route_path,
                    "status": status,
                    "duration_ms": round(duration * 1000, 1),
                },
            )
        request_id_var.reset(token)


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
app.include_router(wake_router)
app.include_router(github_router)
app.include_router(google_router)



@app.get("/health")
def health():
    """The process is up. Says nothing about the database or Redis."""
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)):
    """Can this instance serve requests? 503 if a dependency is down."""
    checks = {"database": True, "redis": True}

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        checks["database"] = False

    try:
        redis_client.ping()
    except redis.exceptions.RedisError:
        checks["redis"] = False

    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = 503

    return {"status": "ready" if is_ready else "not ready", **checks}


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request):
    """Prometheus metrics. With METRICS_TOKEN set, only for that bearer token."""
    if METRICS_TOKEN:
        given = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(given.encode(), METRICS_TOKEN.encode()):
            raise HTTPException(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/')
def root(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {
        "message": "Syphership API is running",
        "database": result.scalar(),
    }
