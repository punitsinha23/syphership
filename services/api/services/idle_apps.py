"""Put apps nobody uses to sleep, so their memory goes to other apps.

Caddy logs every request to an app in that app's own log file (see
services/app_routes.py), so the file's modification time is the app's last
visit. Once a minute the worker:
1. record_activity(): copies those times into Deployment.last_active_at
2. sleep_idle_apps(): stops apps idle for IDLE_SLEEP_HOURS -> SLEEPING

A visit to a sleeping app wakes it again (routes/wake.py, wake_deployment).
Only with APPS_DOMAIN: without Caddy in front, nothing could wake an app."""

import logging
import os
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services import app_routes
from services.docker_services import stop_container

logger = logging.getLogger(__name__)

# 0 turns sleeping off.
IDLE_SLEEP_HOURS = float(os.getenv("IDLE_SLEEP_HOURS", "24"))


def _enabled() -> bool:
    return bool(app_routes.APPS_DOMAIN) and IDLE_SLEEP_HOURS > 0


def _last_visit(project_id: int, project_name: str) -> datetime | None:
    """When the app's log file was last written; None before its first visit."""
    try:
        mtime = app_routes.app_log_file(project_id, project_name).stat().st_mtime
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(mtime, tz=timezone.utc)


def record_activity() -> None:
    """Move RUNNING apps' last_active_at forward to their last visit."""
    if not _enabled():
        return

    db = SessionLocal()
    try:
        running = (
            db.query(Deployment, Project.name)
            .join(Project, Project.id == Deployment.project_id)
            .filter(Deployment.status == DeploymentStatus.RUNNING)
            .all()
        )
        for deployment, project_name in running:
            visit = _last_visit(deployment.project_id, project_name)
            if visit and (deployment.last_active_at is None or visit > deployment.last_active_at):
                deployment.last_active_at = visit
        db.commit()
    finally:
        db.close()


def sleep_idle_apps(now: datetime | None = None) -> None:
    """Stop RUNNING apps that weren't used for IDLE_SLEEP_HOURS."""
    if not _enabled():
        return

    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=IDLE_SLEEP_HOURS)

    db = SessionLocal()
    try:
        idle = (
            db.query(Deployment.id, Deployment.container_id)
            .filter(
                Deployment.status == DeploymentStatus.RUNNING,
                Deployment.container_id.isnot(None),
                # Never-active apps (shouldn't happen) are left alone.
                Deployment.last_active_at < cutoff,
            )
            .all()
        )

        for deployment_id, container_id in idle:
            # Claim it first (only if still RUNNING), so a newer deploy that
            # replaced it in the meantime is never touched.
            claimed = (
                db.query(Deployment)
                .filter(Deployment.id == deployment_id, Deployment.status == DeploymentStatus.RUNNING)
                .update({Deployment.status: DeploymentStatus.SLEEPING})
            )
            db.commit()
            if not claimed:
                continue

            # Visitors now get the wake page instead of a dead container.
            app_routes.sync_app_routes()

            try:
                stop_container(container_id)
                logger.info("Deployment %s was idle; put to sleep.", deployment_id)
            except Exception:
                # Still running: mark it RUNNING again so it's retried next time.
                logger.exception("Could not stop idle deployment %s.", deployment_id)
                db.query(Deployment).filter(
                    Deployment.id == deployment_id,
                    Deployment.status == DeploymentStatus.SLEEPING,
                ).update({Deployment.status: DeploymentStatus.RUNNING})
                db.commit()
                app_routes.sync_app_routes()
    finally:
        db.close()
