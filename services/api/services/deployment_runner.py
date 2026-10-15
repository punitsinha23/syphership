
from pathlib import Path
import logging
import os
import shutil

from fastapi import HTTPException

from database import SessionLocal
from github.service import get_github_token
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import User
from services.deployment_services import (
    update_deployment_status,
    save_container_id,
)
from services.repository_service import clone_repository
from services.docker_services import (
    build_docker_image,
    run_docker_container,
    get_container_status,
    get_exposed_port,
    get_host_port,
    remove_deployment_resources,
)
from services.errors import DeploymentError
from services.health_service import wait_for_healthy

logger = logging.getLogger(__name__)

# Hostname used to build deployment URLs (Phase 4: containers run locally).
DEPLOYMENT_HOST = os.getenv("DEPLOYMENT_HOST", "localhost")


def _remove_resources(deployment_id: int) -> bool:
    """Best-effort Docker cleanup; never raises. Returns True on success."""

    try:
        remove_deployment_resources(deployment_id)
        return True
    except Exception:
        logger.exception(
            "Could not remove Docker resources for deployment %s.",
            deployment_id,
        )
        return False


def _stop_previous_deployments(db, deployment) -> None:
    """Stop older running deployments of the same project; never raises."""

    try:
        previous = (
            db.query(Deployment)
            .filter(
                Deployment.project_id == deployment.project_id,
                Deployment.status == DeploymentStatus.RUNNING,
                # Only older ones, so a slow old build never stops a newer one.
                Deployment.id < deployment.id,
            )
            .all()
        )

        for old in previous:
            # Keep it RUNNING if its container could not be removed.
            if _remove_resources(old.id):
                update_deployment_status(old, DeploymentStatus.STOPPED)
                logger.info(
                    "Deployment %s stopped; replaced by %s.",
                    old.id,
                    deployment.id,
                )

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Could not stop previous deployments of project %s.",
            deployment.project_id,
        )


def _mark_failed(
    db,
    deployment_id: int,
    reason: str,
    build_logs: str | None = None,
) -> bool:
    """Roll back the session and mark an in-progress deployment as failed.

    Returns True if the deployment was marked as failed."""

    db.rollback()

    # Reload the deployment after rolling back the session.
    deployment = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id)
        .first()
    )

    if (
        deployment is not None
        and deployment.status
        in (
            DeploymentStatus.QUEUED,
            DeploymentStatus.BUILDING,
            DeploymentStatus.DEPLOYING,
        )
    ):
        update_deployment_status(
            deployment,
            DeploymentStatus.FAILED,
            reason,
        )

        # Set after the rollback above, which discards unsaved changes.
        if build_logs is not None:
            deployment.build_logs = build_logs

        db.commit()
        return True

    return False


def run_deployment(deployment_id: int) -> None:
    """Clone, build, and start a deployment."""

    db = SessionLocal()
    repository_path: Path | None = None

    try:
        deployment = (
            db.query(Deployment)
            .filter(Deployment.id == deployment_id)
            .first()
        )

        if deployment is None:
            logger.error("Deployment %s was not found.", deployment_id)
            return

        # Prevent rerunning deployments that are no longer queued.
        if deployment.status != DeploymentStatus.QUEUED:
            logger.warning(
                "Deployment %s is not queued; skipping.",
                deployment_id,
            )
            return

        project = (
            db.query(Project)
            .filter(Project.id == deployment.project_id)
            .first()
        )

        if project is None:
            update_deployment_status(
                deployment,
                DeploymentStatus.FAILED,
                "Project not found.",
            )
            db.commit()
            return

        user = (
            db.query(User)
            .filter(User.id == project.user_id)
            .first()
        )

        if user is None:
            update_deployment_status(
                deployment,
                DeploymentStatus.FAILED,
                "Project owner not found.",
            )
            db.commit()
            return

        if not project.repo_full_name or not project.repo_branch or not project.repo_clone_url:
            update_deployment_status(
                deployment,
                DeploymentStatus.FAILED,
                "Repository or branch is missing.",
            )
            db.commit()
            return

        try:
            # Retrieve the repository owner's GitHub token.
            try:
                token = get_github_token(db, user)
            except HTTPException:
                raise DeploymentError(
                    "GitHub account is not connected. "
                    "Reconnect GitHub and deploy again."
                ) from None

            # 1. QUEUED -> BUILDING
            update_deployment_status(
                deployment,
                DeploymentStatus.BUILDING,
            )
            db.commit()

            # Remove leftovers with this deployment's name (e.g. after a DB reset),
            # otherwise "docker run --name" fails.
            _remove_resources(deployment.id)

            # 2. Clone the exact commit selected for this deployment.
            repository_path = clone_repository(
                repo_url=project.repo_clone_url,
                commit_sha=deployment.commit_sha,
                deployment_id=deployment.id,
                github_token=token,
            )

            # 3. Build the Docker image.
            image_tag, build_logs = build_docker_image(
                repository_path,
                deployment.id,
            )
            deployment.build_logs = build_logs

            # Read the port the app listens on from the Dockerfile's EXPOSE.
            container_port = get_exposed_port(image_tag)

            # 4. BUILDING -> DEPLOYING
            update_deployment_status(
                deployment,
                DeploymentStatus.DEPLOYING,
            )
            db.commit()

            # 5. Start the container and publish its port on the host.
            container_id = run_docker_container(
                image_tag,
                deployment.id,
                container_port,
            )

            save_container_id(deployment, container_id)
            db.commit()

            # 6. Verify that Docker reports the container as running.
            container_status = get_container_status(container_id)

            if container_status != "running":
                raise DeploymentError(
                    "The container exited right after starting. "
                    "Make sure your Dockerfile's CMD runs a long-lived process."
                )

            # Find the host port Docker picked and store the URL.
            host_port = get_host_port(container_id, container_port)
            url = f"http://{DEPLOYMENT_HOST}:{host_port}"

            # Only save the URL once the app actually answers requests.
            wait_for_healthy(url)

            deployment.host_port = host_port
            deployment.url = url

            # 7. DEPLOYING -> RUNNING
            update_deployment_status(
                deployment,
                DeploymentStatus.RUNNING,
            )
            db.commit()

            logger.info(
                "Deployment %s is running.",
                deployment_id,
            )

            # 8. The new version is live; retire the old ones.
            _stop_previous_deployments(db, deployment)

        except DeploymentError as error:
            # Expected failure with a message meant for the user.
            logger.warning(
                "Deployment %s failed: %s",
                deployment_id,
                error,
            )
            if _mark_failed(
                db,
                deployment_id,
                str(error),
                # Only BuildError carries logs; other errors give None.
                build_logs=getattr(error, "logs", None),
            ):
                _remove_resources(deployment_id)

        except Exception:
            # Unexpected failure; keep internal details in the server logs.
            logger.exception(
                "Deployment %s failed.",
                deployment_id,
            )
            # Only clean up if it really failed; never remove a RUNNING container.
            if _mark_failed(
                db,
                deployment_id,
                "Deployment failed due to an internal error.",
            ):
                _remove_resources(deployment_id)

    finally:
        db.close()

        # Clean up source files after the build process.
        if repository_path is not None:
            shutil.rmtree(repository_path, ignore_errors=True)
