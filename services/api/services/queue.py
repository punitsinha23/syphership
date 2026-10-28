import os
import redis
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


STREAM = "deployments"
GROUP = "builders"
DEAD_STREAM = "deployments:dead"


redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_timeout=10
)


def ensure_group() -> None:
    """Create the consumer group (and the stream) if they don't exist yet."""

    try:
        redis_client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as error:
        # The group already exists; that's the state we want.
        if "BUSYGROUP" not in str(error):
            raise


def publish(deployment_id: int) -> str:
    """Queue a deployment for the workers; returns the stream message ID."""

    return redis_client.xadd(STREAM, {"deployment_id": deployment_id})
