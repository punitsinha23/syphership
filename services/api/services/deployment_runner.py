
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
)
from services.errors import DeploymentError
from services.health_service import wait_for_healthy

logger = logging.getLogger(__name__)

# Hostname used to build deployment URLs (Phase 4: containers run locally).
DEPLOYMENT_HOST = os.getenv("DEPLOYMENT_HOST", "localhost")


def _mark_failed(db, deployment_id: int, reason: str) -> None:
    """Roll back the session and mark an in-progress deployment as failed."""

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
        db.commit()


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

            # 2. Clone the exact commit selected for this deployment.
            repository_path = clone_repository(
                repo_url=project.repo_clone_url,
                commit_sha=deployment.commit_sha,
                deployment_id=deployment.id,
                github_token=token,
            )

            # 3. Build the Docker image.
            image_tag = build_docker_image(
                repository_path,
                deployment.id,
            )

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

        except DeploymentError as error:
            # Expected failure with a message meant for the user.
            logger.warning(
                "Deployment %s failed: %s",
                deployment_id,
                error,
            )
            _mark_failed(db, deployment_id, str(error))

        except Exception:
            # Unexpected failure; keep internal details in the server logs.
            logger.exception(
                "Deployment %s failed.",
                deployment_id,
            )
            _mark_failed(
                db,
                deployment_id,
                "Deployment failed due to an internal error.",
            )

    finally:
        db.close()

        # Clean up source files after the build process.
        if repository_path is not None:
            shutil.rmtree(repository_path, ignore_errors=True)
