from unittest.mock import MagicMock, patch

import httpx
import pytest

from services.errors import DeploymentError
from services.health_service import wait_for_healthy


URL = "http://localhost:49153"


def response(status_code: int) -> MagicMock:
    return MagicMock(status_code=status_code)


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_healthy_immediately(mock_get, mock_sleep):
    mock_get.return_value = response(200)

    wait_for_healthy(URL)

    mock_get.assert_called_once_with(URL, timeout=2)
    mock_sleep.assert_not_called()


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_retries_until_app_starts(mock_get, mock_sleep):
    # App refuses connections twice while starting, then answers.
    mock_get.side_effect = [
        httpx.ConnectError("Connection refused"),
        httpx.ConnectError("Connection refused"),
        response(200),
    ]

    wait_for_healthy(URL, interval=1)

    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(1)


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_client_error_counts_as_healthy(mock_get, mock_sleep):
    # A 404 still means the server is up and answering.
    mock_get.return_value = response(404)

    wait_for_healthy(URL)

    mock_get.assert_called_once()
    mock_sleep.assert_not_called()


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_retries_after_server_error(mock_get, mock_sleep):
    mock_get.side_effect = [response(500), response(200)]

    wait_for_healthy(URL)

    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_fails_when_app_keeps_returning_server_error(mock_get, mock_sleep):
    mock_get.return_value = response(500)

    with pytest.raises(DeploymentError, match="did not respond"):
        wait_for_healthy(URL, timeout=0)

    mock_sleep.assert_not_called()


@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_fails_when_app_never_accepts_connections(mock_get, mock_sleep):
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(DeploymentError, match="listens on 0.0.0.0"):
        wait_for_healthy(URL, timeout=0)

    mock_sleep.assert_not_called()


@patch("services.health_service.time.monotonic")
@patch("services.health_service.time.sleep")
@patch("services.health_service.httpx.get")
def test_gives_up_after_timeout(mock_get, mock_sleep, mock_monotonic):
    # Clock: start at 0, then 30s, then 61s (past the 60s deadline).
    mock_monotonic.side_effect = [0, 30, 61]
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(DeploymentError, match="within 60 seconds"):
        wait_for_healthy(URL, timeout=60)

    assert mock_get.call_count == 2
    assert mock_sleep.call_count == 1
