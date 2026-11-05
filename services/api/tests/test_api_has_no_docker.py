import subprocess
import sys


def test_api_does_not_load_docker_code():
    # Docker access is root on the host, so the public API must never need it.
    # A new process, because this test run also loads the worker's modules.
    result = subprocess.run(
        [sys.executable, "-c", "import sys, main; print('services.docker_services' in sys.modules)"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("False")
