"""Live build output, one Redis Stream per deployment.

The worker appends each line as docker build prints it; the API reads the
stream and sends the lines to the browser as Server-Sent Events. The complete
log is still saved in Postgres when the build ends; this is only the live
copy, so it expires.

A Stream (not Pub/Sub) so someone who opens the page mid-build still gets the
lines printed before they arrived. No Docker imports here: the API uses this."""

import json
import logging
import time
from collections.abc import Iterator

import redis

from services.queue import redis_client

logger = logging.getLogger(__name__)

# Kept for an hour after the last line; long enough to watch a build.
LOG_TTL_SECONDS = 60 * 60
# A runaway build can't fill Redis: older lines are dropped past this.
MAX_LIVE_LINES = 5000

# How long one read waits for new lines. Must stay under the Redis client's
# socket timeout (10 s), or the read itself times out.
READ_BLOCK_MS = 5000
# A reader gives up after this, even if the stream never ends (e.g. Redis lost
# the end marker). Longer than queue wait + the 10-minute build timeout.
MAX_STREAM_SECONDS = 20 * 60


def log_key(deployment_id: int) -> str:
    return f"logs:{deployment_id}"


def publish_line(deployment_id: int, line: str) -> None:
    """Append one line. Never raises: live logs must not break a build."""
    key = log_key(deployment_id)
    try:
        redis_client.xadd(key, {"line": line}, maxlen=MAX_LIVE_LINES, approximate=True)
        # Refreshed on every line, so the key cleans itself up even if the
        # worker dies before publish_end.
        redis_client.expire(key, LOG_TTL_SECONDS)
    except redis.exceptions.RedisError:
        logger.warning("Could not publish a log line for deployment %s.", deployment_id)


def publish_end(deployment_id: int) -> None:
    """Mark the stream finished, so readers know to stop waiting."""
    key = log_key(deployment_id)
    try:
        redis_client.xadd(key, {"end": "1"})
        redis_client.expire(key, LOG_TTL_SECONDS)
    except redis.exceptions.RedisError:
        logger.warning("Could not end the log stream for deployment %s.", deployment_id)


def stream_exists(deployment_id: int) -> bool:
    return bool(redis_client.exists(log_key(deployment_id)))


def end_event() -> str:
    return "event: end\ndata: \n\n"


def read_events(deployment_id: int, last_id: str = "0") -> Iterator[str]:
    """Server-Sent Events for a deployment's live log, from last_id onwards.

    Each line is one event; its id is the stream entry ID, so a reconnecting
    client can resume after the last line it got. Ends with an "end" event."""
    key = log_key(deployment_id)
    deadline = time.monotonic() + MAX_STREAM_SECONDS

    while time.monotonic() < deadline:
        response = redis_client.xread({key: last_id}, count=200, block=READ_BLOCK_MS)

        if not response:
            # A comment line: keeps proxies from closing a quiet connection.
            yield ": keepalive\n\n"
            continue

        for entry_id, fields in response[0][1]:
            last_id = entry_id
            if "end" in fields:
                yield end_event()
                return
            # JSON keeps a line with special characters in one "data:" field.
            yield f"id: {entry_id}\ndata: {json.dumps(fields.get('line', ''))}\n\n"

    yield end_event()
