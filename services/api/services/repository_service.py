
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
import os

from git import GitCommandError, Repo

from services.errors import DeploymentError


DEPLOYMENT_ROOT = Path(tempfile.gettempdir()) / "syphership-deployments"


def clone_repository(
    repo_url: str,
    commit_sha: str,
    deployment_id: int,
    github_token: str | None = None,
) -> Path:

    if not repo_url:
        raise ValueError("Repository URL is required.")

    if not commit_sha or len(commit_sha) != 40:
        raise ValueError("Invalid commit SHA.")

    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID.")

    parsed_url = urlparse(repo_url)

    is_local = parsed_url.scheme == "" and not repo_url.startswith("git@")
    is_github_http = (
        parsed_url.scheme == "https"
        and parsed_url.hostname == "github.com"
        and parsed_url.username is None
        and parsed_url.password is None
    )

    if not is_local and not is_github_http:
        raise ValueError("Only local paths and HTTPS Github URLs are supported.")

    if is_github_http and not repo_url.rstrip("/").endswith(".git"):
        raise ValueError("Github repository URL must end in .git.")

    if is_github_http and not github_token:
        raise ValueError("Github token is required for Github repo.")

    DEPLOYMENT_ROOT.mkdir(parents=True, exist_ok=True)

    root = DEPLOYMENT_ROOT.resolve()
    destination = (root / str(deployment_id)).resolve()

    # Ensure the workspace stays inside the deployment directory.
    if destination.parent != root:
        raise ValueError("Invalid deployment destination.")

    if destination.exists():
        raise FileExistsError("Deployment workspace already exists.")

    env = os.environ.copy()

    if is_github_http:
        import base64

        credentials = base64.b64encode(
            f"x-access-token:{github_token}".encode()
        ).decode()

        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {credentials}"

    try:
        repo = Repo.clone_from(
            repo_url,
            destination,
            no_checkout=True,
            env=env
        )

        # Check out the exact commit selected when deployment was created.
        repo.git.checkout(commit_sha)

        return destination

    except (GitCommandError, ValueError, OSError):
        # Remove an incomplete workspace if cloning or checkout fails.
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)

        raise DeploymentError(
            "Could not clone the repository at the selected commit. "
            "Check that the repository exists and Syphership still has access."
        ) from None
