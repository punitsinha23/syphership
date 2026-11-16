import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from database import SessionLocal
from github.service import get_github_token
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from models.user import User
from services.app_routes import public_url, sync_app_routes
from services.deployment_services import (
    save_container_id,
    update_deployment_status,
)
from services.docker_services import (
    build_docker_image,
    check_container_user,
    check_image_size,
    check_image_user,
    deployment_resource_name,
    get_container_status,
    get_exposed_port,
    get_host_port,
    remove_deployment_resources,
    run_docker_container,
    start_container,
)
from services.env_vars import read_env_vars
from services.errors import DeploymentError
from services.health_service import wait_for_healthy
from services.repository_service import clone_repository
from services.validation import scrub

logger = logging.getLogger(__name__)

# Hostname the worker uses to reach apps (they're published on 127.0.0.1).
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
                # Sleeping ones too, or their stopped containers would stay forever.
                Deployment.status.in_((
                    DeploymentStatus.RUNNING,
                    DeploymentStatus.SLEEPING,
                    DeploymentStatus.WAKING,
                )),
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
            DeploymentStatus.WAKING,
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


def claim_deployment(db, deployment_id: int) -> bool:
    """Move a queued deployment to BUILDING; False if it isn't queued anymore.

    Check and update happen in one UPDATE, so when two workers get the same
    job, only one of them can claim it."""

    claimed = (
        db.query(Deployment)
        .filter(
            Deployment.id == deployment_id,
            Deployment.status == DeploymentStatus.QUEUED,
        )
        .update({Deployment.status: DeploymentStatus.BUILDING})
    )

    # Commit right away so other workers see the claim.
    db.commit()
    return claimed == 1


def fail_dead_deployments() -> None:
    """Mark RUNNING deployments as FAILED if their container has died.

    Raises RuntimeError, changing nothing more, if Docker can't be asked."""
    db = SessionLocal()
    try:
        running = (
            db.query(Deployment.id, Deployment.container_id)
            .filter(Deployment.status == DeploymentStatus.RUNNING)
            .all()
        )

        for deployment_id, container_id in running:
            if not container_id:
                continue

            try:
                if get_container_status(container_id) not in ("exited", "dead"):
                    continue
            except ValueError:
                pass  # The container no longer exists.

            # Only if it's still RUNNING: a newer deployment may have replaced it.
            changed = (
                db.query(Deployment)
                .filter(Deployment.id == deployment_id, Deployment.status == DeploymentStatus.RUNNING)
                .update({
                    Deployment.status: DeploymentStatus.FAILED,
                    Deployment.failed_stage: DeploymentStatus.RUNNING,
                    Deployment.failure_reason: "The app stopped running. Deploy again to restart it.",
                })
            )
            db.commit()

            if changed:
                logger.warning("Deployment %s stopped running; marked as failed.", deployment_id)
                _remove_resources(deployment_id)
    finally:
        db.close()


def run_deployment(deployment_id: int) -> None:
    """Clone, build, and start a deployment."""

    db = SessionLocal()
    repository_path: Path | None = None
    token: str | None = None

    try:
        deployment = (
            db.query(Deployment)
            .filter(Deployment.id == deployment_id)
            .first()
        )

        if deployment is None:
            logger.error("Deployment %s was not found.", deployment_id)
            return

        # 1. Claim it (QUEUED -> BUILDING); a job delivered twice is skipped here.
        if not claim_deployment(db, deployment_id):
            logger.warning(
                "Deployment %s was already claimed or finished; skipping.",
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
            deployment.build_logs = scrub(build_logs, token)
            check_image_size(image_tag)
            check_image_user(image_tag)

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
                env_vars=read_env_vars(project),
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

            check_container_user(container_id)

            # Find the host port Docker picked. The worker checks the app there;
            # users get the public HTTPS URL when APPS_DOMAIN is set.
            host_port = get_host_port(container_id, container_port)
            health_url = f"http://{DEPLOYMENT_HOST}:{host_port}"

            # Only save the URL once the app actually answers requests.
            wait_for_healthy(health_url)

            deployment.host_port = host_port
            deployment.url = public_url(project.id, project.name) or health_url
            # Going live counts as activity, so a new app gets a full idle period.
            deployment.last_active_at = datetime.now(UTC)

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

            # 8. Point the app's URL at the new container, then retire the old
            # ones, so the URL keeps working during a redeploy.
            sync_app_routes()
            _stop_previous_deployments(db, deployment)

        except DeploymentError as error:
            # Expected failure with a message meant for the user.
            safe_message = scrub(str(error), token)
            logger.warning(
                "Deployment %s failed: %s",
                deployment_id,
                safe_message,
            )
            if _mark_failed(
                db,
                deployment_id,
                safe_message,
                # Only BuildError carries logs; other errors give None.
                build_logs=scrub(getattr(error, "logs", None), token),
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


def wake_deployment(deployment_id: int) -> None:
    """Start a WAKING deployment's stopped container again -> RUNNING.

    Safe to run twice: anything that isn't WAKING anymore is skipped. If the
    app can't be started it's marked FAILED; the owner has to deploy again."""

    db = SessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if deployment is None or deployment.status != DeploymentStatus.WAKING:
            return

        try:
            if not deployment.container_id:
                raise DeploymentError("The app's container is missing. Deploy again.")

            start_container(deployment.container_id)

            if get_container_status(deployment.container_id) != "running":
                raise DeploymentError("The app exited right after waking up. Deploy again.")

            # Docker may pick a different host port on start.
            image_tag = f"{deployment_resource_name(deployment.id)}:latest"
            host_port = get_host_port(deployment.container_id, get_exposed_port(image_tag))
            wait_for_healthy(f"http://{DEPLOYMENT_HOST}:{host_port}")

            changed = (
                db.query(Deployment)
                .filter(Deployment.id == deployment_id, Deployment.status == DeploymentStatus.WAKING)
                .update({
                    Deployment.status: DeploymentStatus.RUNNING,
                    Deployment.host_port: host_port,
                    Deployment.last_active_at: datetime.now(UTC),
                })
            )
            db.commit()

            if changed:
                logger.info("Deployment %s woke up.", deployment_id)
                sync_app_routes()
            else:
                # Replaced or deleted while waking; that code removes the container.
                logger.info("Deployment %s changed while waking; leaving it.", deployment_id)

        except Exception as error:
            reason = str(error) if isinstance(error, DeploymentError) else (
                "The app could not be woken up. Deploy again."
            )
            logger.exception("Deployment %s could not wake up.", deployment_id)
            if _mark_failed(db, deployment_id, reason):
                _remove_resources(deployment_id)
                sync_app_routes()
    finally:
        db.close()


def recover_deployment(deployment_id: int) -> None:
    """Handle a job taken over from a worker that died.

    BUILDING/DEPLOYING means it died mid-job: fail it and clean up. Anything
    else goes to run_deployment, which builds QUEUED and skips the rest."""

    db = SessionLocal()

    try:
        deployment = (
            db.query(Deployment)
            .filter(Deployment.id == deployment_id)
            .first()
        )

        if deployment is None:
            logger.warning("Deployment %s was not found during recovery.", deployment_id)
            return

        if deployment.status in (
            DeploymentStatus.BUILDING,
            DeploymentStatus.DEPLOYING,
        ):
            if _mark_failed(
                db,
                deployment_id,
                "The build worker stopped unexpectedly. Deploy again.",
            ):
                _remove_resources(deployment_id)
            return

    finally:
        db.close()

    run_deployment(deployment_id)


def fail_dead_lettered(deployment_id: int) -> None:
    """Fail a deployment whose job was dead-lettered, and clean up its resources."""

    db = SessionLocal()

    try:
        if _mark_failed(
            db,
            deployment_id,
            "This deployment kept failing and was stopped. Deploy again.",
        ):
            _remove_resources(deployment_id)
    finally:
        db.close()
