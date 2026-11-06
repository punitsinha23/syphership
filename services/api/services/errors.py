class DeploymentError(RuntimeError):
    """A deployment failure whose message is safe to show to the user."""


class BuildError(DeploymentError):
    """Docker build failed; carries the build output."""

    def __init__(self, message: str, logs: str):
        super().__init__(message)
        self.logs = logs


class DeploymentInProgress(DeploymentError):
    """The project already has a queued or running build."""


class AppLimitReached(DeploymentError):
    """The user already has as many running apps as the plan allows."""


class QueueUnavailable(DeploymentError):
    """Redis could not be reached, so the deployment was marked FAILED."""
