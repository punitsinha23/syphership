from services.queue import ensure_group, redis_client, GROUP, STREAM
from services.deployment_runner import run_deployment, logging

ensure_group()
logging.basicConfig(level=logging.INFO ,format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
while True:
    response = redis_client.xreadgroup(GROUP, "w1", block=2000, count=1, streams={STREAM : ">"})
    if not response:
        continue

    messages = response[0][1]
    message_id, fields = messages[0]
    deployment_id = int(fields['deployment_id'])
    logger.info("Picked up deployment %s (message %s).", deployment_id, message_id)
    run_deployment(deployment_id)
    logger.info("Finished deployment %s.", deployment_id)
    redis_client.xack(STREAM, GROUP, message_id)

    
