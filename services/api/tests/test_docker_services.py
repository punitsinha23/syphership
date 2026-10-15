from pathlib import Path
from unittest.mock import patch
import pytest
import subprocess
from services.docker_services import (
    MAX_BUILD_LOG_CHARS,
    _trim_log,
    build_docker_image,
    get_container_status,
    get_exposed_port,
    get_host_port,
    remove_deployment_resources,
    run_docker_container,
)
from services.errors import BuildError, DeploymentError
from unittest.mock import MagicMock, patch

def assert_docker_build_called(mock_run, tmp_path):
    mock_run.assert_called_once_with(
        [
            "docker",
            "build",
            "--progress=plain",
            "--tag",
            "syphership-deployment-1:latest",
            "--file",
            str(tmp_path / "Dockerfile"),
            str(tmp_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=600,
    )


def test_build_docker_image(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\n")

    with patch('services.docker_services.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="#1 [internal] load build definition\n#2 DONE\n")
        image_tag, logs = build_docker_image(tmp_path, deployment_id=1)

    assert image_tag == "syphership-deployment-1:latest"
    assert logs == "#1 [internal] load build definition\n#2 DONE\n"
    assert_docker_build_called(mock_run, tmp_path)

def test_build_docker_image_missing_directory(tmp_path):
    missing_path = tmp_path / "does_not_exist"

    with pytest.raises(ValueError , match="Repo doesn't exist."):
        build_docker_image(missing_path, deployment_id=1)

def test_dockerfile_missing(tmp_path):
    repository_path = tmp_path

    with pytest.raises(
        DeploymentError,
        match="No Dockerfile found"
    ):
        build_docker_image(repository_path, deployment_id=1)

def test_deployment_id_is_zero(tmp_path):
    with pytest.raises(ValueError, match="Invalid deployment ID"):
        build_docker_image(tmp_path, deployment_id=0)

def test_deployment_id_is_neg(tmp_path):
    with pytest.raises(ValueError, match="Invalid deployment ID"):
        build_docker_image(tmp_path, deployment_id=-1)

def test_docker_timeout(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\n")

    with patch("services.docker_services.subprocess.run") as mock_run:
        # TimeoutExpired can carry bytes even when text=True was passed.
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="docker build",
            timeout=600,
            output=b"#5 RUN npm install\n",
        )

        with pytest.raises(
            BuildError,
            match="Docker build timed out",
        ) as error:
            build_docker_image(tmp_path, deployment_id=1)

        assert error.value.logs == "#5 RUN npm install\n"
        assert_docker_build_called(mock_run, tmp_path)

def test_docker_build_fail(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12-slim\n")

    with patch("services.docker_services.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd="docker build",
                output="#6 RUN npm run build\nnpm ERR! missing script: build\n",
                )

        with pytest.raises(
            BuildError,
            match="Docker build failed"
        ) as error:
            build_docker_image(tmp_path, deployment_id=1)

        assert "npm ERR! missing script: build" in error.value.logs
        assert_docker_build_called(mock_run, tmp_path)


def test_build_error_is_a_deployment_error():
    # The runner catches DeploymentError, so BuildError must be one.
    assert issubclass(BuildError, DeploymentError)


def test_build_failure_without_output_has_empty_logs(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\n")

    with patch("services.docker_services.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd="docker build")

        with pytest.raises(BuildError) as error:
            build_docker_image(tmp_path, deployment_id=1)

    assert error.value.logs == ""


def test_trim_log_keeps_short_output():
    assert _trim_log("short log") == "short log"


def test_trim_log_keeps_the_end_of_long_output():
    output = "a" * MAX_BUILD_LOG_CHARS + "ERROR: the real problem"

    trimmed = _trim_log(output)

    assert trimmed.startswith("[earlier output truncated]\n")
    assert trimmed.endswith("ERROR: the real problem")
    assert len(trimmed) == len("[earlier output truncated]\n") + MAX_BUILD_LOG_CHARS

def test_deployment_id_is_not_integer(tmp_path):
    with pytest.raises(ValueError, match="Invalid deployment ID"):
            build_docker_image(tmp_path, deployment_id="abc")

def test_deployment_id_is_none(tmp_path):
    with pytest.raises(ValueError, match="Invalid deployment ID"):
        build_docker_image(tmp_path, deployment_id=None)



@patch(
    "services.docker_services.subprocess.run"
)
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_run_docker_container_success(mock_which, mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "abc123container\n"
    mock_run.return_value = mock_result

    container_id = run_docker_container(
        "syphership-deployment-1:latest",
        1,
        80,
    )

    assert container_id == "abc123container"

    mock_run.assert_called_once_with(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "syphership-deployment-1",
            "-p",
            "127.0.0.1::80",
            "syphership-deployment-1:latest",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )



@patch("services.docker_services.shutil.which", return_value="/usr/bin/docker")
def test_run_container_rejects_invalid_deployment_id(mock_which):
    with pytest.raises(ValueError, match="Invalid deployment ID"):
        run_docker_container("my-image:latest", 0, 80)


@patch("services.docker_services.shutil.which", return_value="/usr/bin/docker")
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="docker run", timeout=60),
)

def test_run_container_timeout(mock_run, mock_which):
    with pytest.raises(DeploymentError, match="took too long to start"):
        run_docker_container("my-image:latest", 1, 80)


@patch("services.docker_services.shutil.which", return_value="/usr/bin/docker")
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.CalledProcessError(returncode=1, cmd="docker run"),
)

def test_run_container_failure(mock_run, mock_which):
    with pytest.raises(DeploymentError, match="could not start the container"):
        run_docker_container("my-image:latest", 1, 80)


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)

def test_get_container_status_success(mock_which, mock_run):
    mock_result =  MagicMock()
    mock_result.stdout = "running\n"
    mock_run.return_value = mock_result

    status = get_container_status("abc123container")

    assert status == "running"

    mock_run.assert_called_once_with(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}}",
            "abc123container",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )



@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_container_status_invalid_id(mock_which):
    with pytest.raises(ValueError, match="Invalid container ID"):
        get_container_status("")


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.TimeoutExpired(
        cmd="docker inspect",
        timeout=30,
    ),
)
def test_get_container_status_timeout(mock_run, mock_which):
    with pytest.raises(
        RuntimeError,
        match="inspection timed out",
    ):
        get_container_status("abc123container")


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.CalledProcessError(
        returncode=1,
        cmd="docker inspect",
    ),
)
def test_get_container_status_failure(mock_run, mock_which):
    with pytest.raises(
        ValueError,
        match="Docker container was not found",
    ):
        get_container_status("missing-container")


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_exposed_port_success(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout='{"80/tcp":{}}\n')

    port = get_exposed_port("syphership-deployment-1:latest")

    assert port == 80

    mock_run.assert_called_once_with(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{json .Config.ExposedPorts}}",
            "syphership-deployment-1:latest",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_exposed_port_picks_lowest_tcp_port(mock_which, mock_run):
    mock_run.return_value = MagicMock(
        stdout='{"9229/tcp":{},"3000/tcp":{},"53/udp":{}}\n'
    )

    assert get_exposed_port("my-image:latest") == 3000


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_exposed_port_no_expose(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout="null\n")

    with pytest.raises(DeploymentError, match="must EXPOSE"):
        get_exposed_port("my-image:latest")


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_exposed_port_empty_output(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout="")

    with pytest.raises(DeploymentError, match="must EXPOSE"):
        get_exposed_port("my-image:latest")


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_exposed_port_udp_only(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout='{"53/udp":{}}\n')

    with pytest.raises(DeploymentError, match="TCP port"):
        get_exposed_port("my-image:latest")


def test_get_exposed_port_invalid_tag():
    with pytest.raises(ValueError, match="Invalid Docker image tag"):
        get_exposed_port("")


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.TimeoutExpired(
        cmd="docker image inspect",
        timeout=30,
    ),
)
def test_get_exposed_port_timeout(mock_run, mock_which):
    with pytest.raises(RuntimeError, match="inspection timed out"):
        get_exposed_port("my-image:latest")


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.CalledProcessError(
        returncode=1,
        cmd="docker image inspect",
    ),
)
def test_get_exposed_port_image_not_found(mock_run, mock_which):
    with pytest.raises(RuntimeError, match="Docker image was not found"):
        get_exposed_port("missing-image:latest")


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_host_port_success(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout="127.0.0.1:49153\n")

    port = get_host_port("abc123", 80)

    assert port == 49153

    mock_run.assert_called_once_with(
        [
            "docker",
            "port",
            "abc123",
            "80/tcp",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_host_port_ipv4_and_ipv6(mock_which, mock_run):
    mock_run.return_value = MagicMock(
        stdout="0.0.0.0:49153\n[::]:49153\n"
    )

    assert get_host_port("abc123", 80) == 49153


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_get_host_port_empty_output(mock_which, mock_run):
    mock_run.return_value = MagicMock(stdout="")

    with pytest.raises(RuntimeError, match="Could not read the host port"):
        get_host_port("abc123", 80)


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.CalledProcessError(
        returncode=1,
        cmd="docker port",
    ),
)
def test_get_host_port_not_published(mock_run, mock_which):
    with pytest.raises(RuntimeError, match="not published"):
        get_host_port("abc123", 80)


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.TimeoutExpired(
        cmd="docker port",
        timeout=30,
    ),
)
def test_get_host_port_timeout(mock_run, mock_which):
    with pytest.raises(RuntimeError, match="lookup timed out"):
        get_host_port("abc123", 80)


def test_get_host_port_invalid_port():
    with pytest.raises(ValueError, match="Invalid container port"):
        get_host_port("abc123", 0)


def test_get_host_port_invalid_container_id():
    with pytest.raises(ValueError, match="Invalid Container ID"):
        get_host_port("", 80)


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_remove_deployment_resources(mock_which, mock_run):
    remove_deployment_resources(7)

    assert [c.args[0] for c in mock_run.call_args_list] == [
        ["docker", "rm", "--force", "syphership-deployment-7"],
        ["docker", "rmi", "--force", "syphership-deployment-7:latest"],
    ]
    for c in mock_run.call_args_list:
        assert "check" not in c.kwargs


@patch("services.docker_services.subprocess.run")
@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
def test_remove_deployment_resources_ignores_missing(mock_which, mock_run):
    # Docker exits non-zero for "No such container"; that is not an error here.
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: No such container")

    remove_deployment_resources(7)

    assert mock_run.call_count == 2


@patch(
    "services.docker_services.shutil.which",
    return_value="/usr/bin/docker",
)
@patch(
    "services.docker_services.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="docker rm", timeout=60),
)
def test_remove_deployment_resources_timeout(mock_run, mock_which):
    with pytest.raises(RuntimeError, match="cleanup timed out"):
        remove_deployment_resources(7)


def test_remove_deployment_resources_invalid_id():
    with pytest.raises(ValueError, match="Invalid deployment ID"):
        remove_deployment_resources(0)
