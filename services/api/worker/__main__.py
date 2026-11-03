import logging
import os
import signal
import socket
import uuid

from services.queue import (
    ensure_group,
    redis_client,
    GROUP,
    STREAM,
    RECLAIM_IDLE_MS,
    MAX_DELIVERIES,
    delivery_count,
    dead_letters,
)
from services.deployment_runner import run_deployment, recover_deployment, fail_dead_lettered

logger = logging.getLogger(__name__)

# Unique per worker. Hostname and PID alone repeat: host-network containers
# share the host's name and all run as PID 1.
CONSUMER = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"

stopping = False


def request_stop(signum, frame):
    """Signal handler: finish the current job, then exit the loop."""

    global stopping
    stopping = True
    logger.info("Got %s; shutting down after the current job.", signal.Signals(signum).name)


def read_deployment_id(message_id: str, fields: dict) -> int | None:
    """The message's deployment ID; None (and dead-lettered) if it's malformed.

    A malformed message fails the same way every time, so it isn't retried."""

    try:
        return int(fields["deployment_id"])
    except (KeyError, ValueError):
        logger.error("Malformed message %s; moved to the dead stream: %s", message_id, fields)
        dead_letters(message_id, fields)
        return None


def handle_reclaimed(message_id: str, fields: dict) -> None:
    """A job taken over from a worker that died."""

    if delivery_count(message_id) >= MAX_DELIVERIES:
        # Delivered too often (likely crashes the worker): stop retrying it.
        logger.error(
            "Giving up on message %s after %s deliveries; moved to the dead stream: %s",
            message_id,
            MAX_DELIVERIES,
            fields,
        )
        try:
            deployment_id = int(fields["deployment_id"])
        except (KeyError, ValueError):
            pass  # Malformed: there's no deployment to fail.
        else:
            fail_dead_lettered(deployment_id)
        dead_letters(message_id, fields)
        return

    deployment_id = read_deployment_id(message_id, fields)
    if deployment_id is None:
        return
    logger.info("Recovering deployment %s (message %s).", deployment_id, message_id)
    recover_deployment(deployment_id)
    redis_client.xack(STREAM, GROUP, message_id)


def handle_new(message_id: str, fields: dict) -> None:
    """A job delivered for the first time."""

    deployment_id = read_deployment_id(message_id, fields)
    if deployment_id is None:
        return
    logger.info("Picked up deployment %s (message %s).", deployment_id, message_id)
    run_deployment(deployment_id)
    logger.info("Finished deployment %s.", deployment_id)
    redis_client.xack(STREAM, GROUP, message_id)


def poll_once() -> None:
    """Handle at most one job: abandoned ones first, then new ones."""

    claimed = redis_client.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=RECLAIM_IDLE_MS, count=1)
    if claimed[1]:
        handle_reclaimed(*claimed[1][0])
        return

    response = redis_client.xreadgroup(GROUP, CONSUMER, block=2000, count=1, streams={STREAM: ">"})
    if response:
        handle_new(*response[0][1][0])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    ensure_group()

    logger.info("Worker %s started.", CONSUMER)
    while not stopping:
        poll_once()
    logger.info("Worker %s stopped.", CONSUMER)


if __name__ == "__main__":
    main()
