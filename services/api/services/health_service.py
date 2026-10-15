import time
import httpx
from services.errors import DeploymentError

def wait_for_healthy(url: str, timeout:float = 60, interval: float = 1) -> None:
    now = time.monotonic()
    deadline = now + timeout

    while True:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            pass

        if time.monotonic() >= deadline:
            raise DeploymentError(
                f"The app did not respond at {url} within {timeout:.0f} seconds. "
                "Make sure it listens on 0.0.0.0, not 127.0.0.1 or localhost."
            )

        time.sleep(interval)

