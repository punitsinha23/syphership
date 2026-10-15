class DeploymentError(RuntimeError):
    """A deployment failure whose message is safe to show to the user."""


class BuildError(DeploymentError):
    """Docker build failed; carries the build output."""

    def __init__(self, message: str, logs: str):
        super().__init__(message)
        self.logs = logs
