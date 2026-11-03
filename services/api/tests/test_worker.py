import signal

import pytest
import redis

import services.queue as queue
import worker.__main__ as worker


TEST_STREAM = "test:deployments"
TEST_DEAD_STREAM = "test:deployments:dead"


@pytest.fixture
def jobs(monkeypatch):
    """Point the queue and worker at test streams on the real Redis, and
    replace the deployment functions with recorders."""
    try:
        queue.redis_client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("Redis is not running")

    for module in (queue, worker):
        monkeypatch.setattr(module, "STREAM", TEST_STREAM)
    monkeypatch.setattr(queue, "DEAD_STREAM", TEST_DEAD_STREAM)
    # Anything already pending counts as abandoned.
    monkeypatch.setattr(worker, "RECLAIM_IDLE_MS", 0)

    calls = []
    for name in ("run_deployment", "recover_deployment", "fail_dead_lettered"):
        monkeypatch.setattr(worker, name, lambda deployment_id, name=name: calls.append((name, deployment_id)))

    queue.redis_client.delete(TEST_STREAM, TEST_DEAD_STREAM)
    queue.ensure_group()
    yield calls
    queue.redis_client.delete(TEST_STREAM, TEST_DEAD_STREAM)


def pending_count():
    return queue.redis_client.xpending(TEST_STREAM, queue.GROUP)["pending"]


def dead_letters():
    return [fields for _, fields in queue.redis_client.xrange(TEST_DEAD_STREAM)]


def deliver_without_ack(times):
    """Simulate a worker that took the job and died, `times` times over."""
    queue.redis_client.xreadgroup(queue.GROUP, "dead-worker", {TEST_STREAM: ">"}, count=1)
    for _ in range(times - 1):
        queue.redis_client.xautoclaim(TEST_STREAM, queue.GROUP, "dead-worker", 0, count=1)


def test_published_job_is_run_and_acked(jobs):
    queue.publish(7)

    worker.poll_once()

    assert jobs == [("run_deployment", 7)]
    assert pending_count() == 0


def test_malformed_job_is_dead_lettered_without_running(jobs):
    queue.redis_client.xadd(TEST_STREAM, {"deployment_id": "abc"})

    worker.poll_once()

    assert jobs == []
    assert dead_letters() == [{"deployment_id": "abc"}]
    assert pending_count() == 0


def test_abandoned_job_is_recovered(jobs):
    queue.publish(7)
    deliver_without_ack(times=1)

    worker.poll_once()

    assert jobs == [("recover_deployment", 7)]
    assert pending_count() == 0


def test_job_delivered_too_often_is_dead_lettered_and_failed(jobs):
    queue.publish(7)
    # The worker's own claim is the last allowed delivery.
    deliver_without_ack(times=queue.MAX_DELIVERIES - 1)

    worker.poll_once()

    assert jobs == [("fail_dead_lettered", 7)]
    assert dead_letters() == [{"deployment_id": "7"}]
    assert pending_count() == 0


def test_malformed_job_delivered_too_often_fails_nothing(jobs):
    queue.redis_client.xadd(TEST_STREAM, {"deployment_id": "abc"})
    deliver_without_ack(times=queue.MAX_DELIVERIES - 1)

    worker.poll_once()

    assert jobs == []
    assert dead_letters() == [{"deployment_id": "abc"}]
    assert pending_count() == 0


def test_stop_signal_lets_the_current_loop_finish(monkeypatch):
    monkeypatch.setattr(worker, "stopping", False)

    worker.request_stop(signal.SIGTERM, None)

    # Only a flag: nothing is interrupted, the loop exits at its next check.
    assert worker.stopping is True
