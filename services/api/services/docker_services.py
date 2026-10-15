import subprocess
from pathlib import Path
import shutil
from services.errors import DeploymentError
import json


def build_docker_image(
        repository_path: Path,
        deployment_id: int,
) -> str:
    
    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID")

    repository_path = repository_path.resolve()

    if not repository_path.is_dir():
        raise ValueError("Repo doesn't exist.")

    dockerfile = repository_path / "Dockerfile"

    if not dockerfile.is_file():
        raise DeploymentError("No Dockerfile found at the repository root. Add a Dockerfile to deploy.")

    image_tag = f"syphership-deployment-{deployment_id}:latest"

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    try:
        subprocess.run([
            "docker",
            "build",
            "--tag",
            image_tag,
            "--file",
            str(dockerfile),
            str(repository_path)
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=600
        )
    except subprocess.TimeoutExpired:
        raise DeploymentError("Docker build timed out after 10 minutes.") from None
    except subprocess.CalledProcessError:
        raise DeploymentError("Docker build failed. Check your Dockerfile.") from None
    except FileNotFoundError:
        raise RuntimeError(
            "Docker exe could not be found"
        ) from None

    return image_tag



def run_docker_container(image_tag: str, deployment_id: int, container_port: int) -> str:
    if not isinstance(deployment_id, int) or deployment_id <= 0:
        raise ValueError("Invalid deployment ID")

    if not image_tag or not isinstance(image_tag, str):
        raise ValueError("Invalid Docker image tag.")

    if not isinstance(container_port, int) or not 0 < container_port <= 65535:
        raise ValueError("Invalid container port.")

    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed or is not available in PATH.")

    container_name = f"syphership-deployment-{deployment_id}"

    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
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

    except subprocess.CalledProcessError:
        raise RuntimeError("Docker container inspection failed.") from None

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
