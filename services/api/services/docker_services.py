import subprocess
from pathlib import Path
import shutil
from services.errors import BuildError, DeploymentError
import json
import os


MAX_BUILD_LOG_CHARS = 100_000

# Per-container limits so one app cannot starve the host or the other apps.
CONTAINER_CPUS = os.getenv("DEPLOYMENT_CPUS", "0.5")
CONTAINER_MEMORY = os.getenv("DEPLOYMENT_MEMORY", "256m")


def deployment_resource_name(deployment_id: int) -> str:
    """Name shared by a deployment's Docker container and image."""
    return f"syphership-deployment-{deployment_id}"


def remove_deployment_resources(deployment_id: int) -> None:
    """Force-remove a deployment's container and image.

    Safe to call when either one does not exist."""

    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID")

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    name = deployment_resource_name(deployment_id)

    for command in (
        ["docker", "rm", "--force", name],
        ["docker", "rmi", "--force", f"{name}:latest"],
    ):
        try:
            # No check=True: "No such container/image" is fine here.
            subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker cleanup timed out.") from None
        except FileNotFoundError:
            raise RuntimeError("Docker executable could not be found.") from None


def _output_text(output) -> str:
    """Subprocess output as text; TimeoutExpired can hold bytes even with text=True."""
    if isinstance(output, bytes):
        return output.decode(errors="replace")
    return output or ""


def _trim_log(output: str) -> str:
    """Keep the end of long logs, where build errors appear."""
    if len(output) <= MAX_BUILD_LOG_CHARS:
        return output
    return "[earlier output truncated]\n" + output[-MAX_BUILD_LOG_CHARS:]


def build_docker_image(
        repository_path: Path,
        deployment_id: int,
) -> tuple[str, str]:
    
    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID")

    repository_path = repository_path.resolve()

    if not repository_path.is_dir():
        raise ValueError("Repo doesn't exist.")

    dockerfile = repository_path / "Dockerfile"

    if not dockerfile.is_file():
        raise DeploymentError("No Dockerfile found at the repository root. Add a Dockerfile to deploy.")

    image_tag = f"{deployment_resource_name(deployment_id)}:latest"

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    try:
        result = subprocess.run(
            [
                "docker",
                "build",
                "--progress=plain",
                "--tag",
                image_tag,
                "--file",
                str(dockerfile),
                str(repository_path),
            ],
            check=True,
            # One stream, in order: BuildKit writes its progress to stderr.
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as e:
        raise BuildError(
            "Docker build timed out after 10 minutes.",
            _trim_log(_output_text(e.output)),
        ) from None
    except subprocess.CalledProcessError as e:
        raise BuildError(
            "Docker build failed. See the build logs for details.",
            _trim_log(_output_text(e.output)),
        ) from None
    except FileNotFoundError:
        raise RuntimeError("Docker executable could not be found.") from None

    return image_tag, _trim_log(result.stdout or "")




def run_docker_container(image_tag: str, deployment_id: int, container_port: int) -> str:
    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID")

    if not image_tag or not isinstance(image_tag, str):
        raise ValueError("Invalid Docker image tag.")

    if not isinstance(container_port, int) or not 0 < container_port <= 65535:
        raise ValueError("Invalid container port.")

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    container_name = deployment_resource_name(deployment_id)

    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--cpus",
                CONTAINER_CPUS,
                "--memory",
                CONTAINER_MEMORY,
                # Same as --memory, so the container cannot use swap on top of it.
                "--memory-swap",
                CONTAINER_MEMORY,
                # Publish on localhost only; the empty host port lets Docker pick a free one.
                "-p",
                f"127.0.0.1::{container_port}",
                image_tag,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        container_id = result.stdout.strip()

        if not container_id:
            raise RuntimeError("Docker did not return a container ID.")

        return container_id

    except subprocess.TimeoutExpired:
        raise DeploymentError("The container took too long to start.") from None

    except subprocess.CalledProcessError:
        raise DeploymentError("Docker could not start the container.") from None

    except FileNotFoundError:
        raise RuntimeError("Docker executable could not be found.") from None

def get_container_status(container_id: str) -> str:
    if not isinstance(container_id, str) or not container_id.strip():
        raise ValueError("Invalid container ID.")

    if shutil.which("docker") is None:
        raise RuntimeError(
            "Docker is not installed or is not available in Path."
        )

    try:
        result = subprocess.run(
            [ 
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}}",
            container_id
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        status = result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker container inspection timed out.") from None

    except subprocess.CalledProcessError:
        raise ValueError("Docker container was not found.") from None

    except FileNotFoundError:
        raise RuntimeError("Docker executable could not be found.") from None
    

    return status


def get_exposed_port(image_tag) -> int:
    if not image_tag or not isinstance(image_tag, str):
        raise ValueError("Invalid Docker image tag.")

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    try:
        result = subprocess.run(
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{json .Config.ExposedPorts}}",
                image_tag,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker image inspection timed out.") from None
    except subprocess.CalledProcessError:
        raise RuntimeError("Docker image was not found") from None
    except FileNotFoundError:
        raise RuntimeError("Docker executable could not be found.") from None

    exposed_ports = json.loads(result.stdout.strip() or "null")

    if not exposed_ports:
        raise DeploymentError(
            "Your Dockerfile must EXPOSE the port your app listens on."
        )

    tcp_ports = [
        int(port.split("/")[0])
        for port  in exposed_ports
        if port.endswith("/tcp")
    ]

    if not tcp_ports:
        raise DeploymentError("Your Dockerfile must EXPOSE a TCP port.")

    return min(tcp_ports)


def get_host_port(container_id: str, container_port:int) -> int:
    if not isinstance(container_id, str) or not container_id.strip():
        raise ValueError("Invalid Container ID.")

    if not isinstance(container_port, int) or not 0 < container_port <= 65535: 
        raise ValueError("Invalid container port.")

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    try:
        result = subprocess.run(
            [
                "docker",
                "port",
                container_id,
                f"{container_port}/tcp"
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker port lookup timed out.") from None
    except subprocess.CalledProcessError:
        raise RuntimeError("Container port is not published.") from None
    except FileNotFoundError:
        raise RuntimeError("Docker executable could not be found.") from None

    try:
        output = result.stdout
        lines = output.strip().splitlines()
        __ , port = lines[0].rsplit(":", 1)

        return int(port)
    except (IndexError, ValueError):
        raise RuntimeError("Could not read the host port from Docker.") from None
