"""The page visitors of a sleeping app see while it starts again.

Caddy sends every request for a SLEEPING/WAKING app here (see
services/app_routes.py). The first visit queues a wake job; the page then
reloads itself until Caddy routes the address to the running app again.
Public on purpose: visitors aren't signed in. The worst anyone can do with it
is wake an app, which a normal visit would do anyway."""

import html

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services.queue import publish_wake


router = APIRouter(prefix="/apps")

ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
RETRY_SECONDS = 3


def _page(title: str, message: str, status_code: int, refresh: bool) -> HTMLResponse:
    refresh_tag = f'<meta http-equiv="refresh" content="{RETRY_SECONDS}">' if refresh else ""
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
{refresh_tag}
<title>{html.escape(title)}</title>
<style>
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
         background: #0b1020; color: #e2e8f0; font: 16px/1.5 system-ui, sans-serif; }}
  main {{ max-width: 28rem; padding: 2rem; text-align: center; }}
  .spinner {{ width: 2.5rem; height: 2.5rem; margin: 0 auto 1.5rem; border-radius: 50%;
             border: 3px solid #334155; border-top-color: #38bdf8; animation: spin 1s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .5rem; }}
  p {{ color: #94a3b8; margin: 0; }}
  small {{ display: block; margin-top: 2rem; color: #475569; }}
</style>
</head>
<body>
<main>
  {'<div class="spinner" aria-hidden="true"></div>' if refresh else ''}
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(message)}</p>
  <small>Hosted on Syphership</small>
</main>
</body>
</html>"""
    headers = {"Retry-After": str(RETRY_SECONDS), "Cache-Control": "no-store"} if refresh else {"Cache-Control": "no-store"}
    return HTMLResponse(body, status_code=status_code, headers=headers)


@router.api_route("/{project_id}/wake", methods=ALL_METHODS, include_in_schema=False)
def wake_app(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    deployment = (
        db.query(Deployment)
        .filter(
            Deployment.project_id == project_id,
            Deployment.status.in_((
                DeploymentStatus.RUNNING,
                DeploymentStatus.SLEEPING,
                DeploymentStatus.WAKING,
            )),
        )
        .order_by(Deployment.id.desc())
        .first()
    )

    if project is None or deployment is None:
        return _page("This app isn't running", "Its owner can deploy it again from Syphership.", 404, refresh=False)

    name = project.name

    if deployment.status == DeploymentStatus.SLEEPING:
        # Only one visitor's request moves it to WAKING and queues the job.
        claimed = (
            db.query(Deployment)
            .filter(Deployment.id == deployment.id, Deployment.status == DeploymentStatus.SLEEPING)
            .update({Deployment.status: DeploymentStatus.WAKING})
        )
        db.commit()

        if claimed:
            try:
                publish_wake(deployment.id)
            except redis.exceptions.RedisError:
                # Put it back, so the next visit tries again.
                db.query(Deployment).filter(
                    Deployment.id == deployment.id,
                    Deployment.status == DeploymentStatus.WAKING,
                ).update({Deployment.status: DeploymentStatus.SLEEPING})
                db.commit()
                return _page(f"{name} is asleep", "It couldn't be woken up right now. Try again in a minute.", 503, refresh=False)

    # SLEEPING (just queued), WAKING, or RUNNING while Caddy's route catches up.
    return _page(
        f"Waking up {name}…",
        "This app was asleep because nobody used it for a while. It'll be back in a few seconds.",
        503,
        refresh=True,
    )
