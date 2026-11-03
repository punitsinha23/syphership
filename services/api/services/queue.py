import os
import redis
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


STREAM = "deployments"
GROUP = "builders"
DEAD_STREAM = "deployments:dead"
# Must be longer than the slowest deployment (docker build alone can take 10 min).
RECLAIM_IDLE_MS = 15 * 60 * 1000
MAX_DELIVERIES = 3


redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    # Must be longer than the worker's xreadgroup block time, or reads time out.
    socket_timeout=10,
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


def delivery_count(message_id: str) -> int:
    """How many times this pending message has been handed to a worker."""

    res = redis_client.xpending_range(STREAM, GROUP, min=message_id, max=message_id, count=1)
    return res[0]["times_delivered"]


def dead_letters(message_id: str, fields: dict) -> None:
    """Give up on a message: copy it to the dead stream and ack it."""

    redis_client.xadd(DEAD_STREAM, fields)
    redis_client.xack(STREAM, GROUP, message_id)
