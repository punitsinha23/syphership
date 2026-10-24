from models.deployment import DeploymentStatus

ALLOWED_TRANSITIONS = {
    DeploymentStatus.QUEUED: [
        DeploymentStatus.BUILDING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.BUILDING: [
        DeploymentStatus.DEPLOYING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.DEPLOYING: [
        DeploymentStatus.RUNNING,
        DeploymentStatus.FAILED
    ],
    DeploymentStatus.RUNNING: [
        DeploymentStatus.STOPPED
    ],
    DeploymentStatus.FAILED: [],
    DeploymentStatus.STOPPED: []
}

IN_PROGRESS_STATUSES = (
    DeploymentStatus.QUEUED,
    DeploymentStatus.BUILDING,
    DeploymentStatus.DEPLOYING,
)


def update_deployment_status(deployment, new_status: DeploymentStatus, failure_reason: str | None = None):
    if new_status not in ALLOWED_TRANSITIONS[deployment.status]:
        raise ValueError('Invalid deployment status transition')

    if new_status == DeploymentStatus.FAILED:
        deployment.failed_stage = deployment.status
        deployment.failure_reason = failure_reason

    deployment.status = new_status


def save_container_id(deployment, container_id:str) -> None:
    if not isinstance(container_id, str) or not container_id.strip():
        raise ValueError("Invalid container ID.")


    deployment.container_id = container_id.strip()
