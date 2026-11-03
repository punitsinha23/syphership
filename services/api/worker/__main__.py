import logging

from services.queue import ensure_group, redis_client, GROUP, STREAM, RECLAIM_IDLE_MS
from services.deployment_runner import run_deployment, recover_deployment

ensure_group()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
while True:
    # First take over jobs a dead worker left unacked, then read new ones.
    claimed = redis_client.xautoclaim(STREAM, GROUP, "w1", min_idle_time=RECLAIM_IDLE_MS, count=1)
    messages = claimed[1]
    if messages:
        message_id, fields = messages[0]
        deployment_id = int(fields['deployment_id'])
        logger.info("Recovering deployment %s (message %s).", deployment_id, message_id)
        recover_deployment(deployment_id)
        redis_client.xack(STREAM, GROUP, message_id)
        continue

    response = redis_client.xreadgroup(GROUP, "w1", block=2000, count=1, streams={STREAM: ">"})
    if not response:
        continue

    messages = response[0][1]
    message_id, fields = messages[0]
    deployment_id = int(fields['deployment_id'])
    logger.info("Picked up deployment %s (message %s).", deployment_id, message_id)
    run_deployment(deployment_id)
    logger.info("Finished deployment %s.", deployment_id)
    redis_client.xack(STREAM, GROUP, message_id)
