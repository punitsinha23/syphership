import json
import logging

import pytest
import redis

import main
import services.metrics as metrics
import services.queue as queue
import worker.__main__ as worker
from services.logging_setup import JsonFormatter, deployment_id_var, request_id_var
from tests.conftest import TestingSessionLocal


@pytest.fixture
def redis_up():
    try:
        queue.redis_client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("Redis is not running")


# ---------- structured logs ----------

def format_json(message, **extra):
    record = logging.LogRecord("syphership.test", logging.INFO, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


def test_log_line_is_json_with_the_current_ids():
    request_token = request_id_var.set("abc123")
    deployment_token = deployment_id_var.set(42)
    try:
        entry = format_json("built", status=200)
    finally:
        request_id_var.reset(request_token)
        deployment_id_var.reset(deployment_token)

    assert entry["message"] == "built"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "syphership.test"
    assert entry["request_id"] == "abc123"
    assert entry["deployment_id"] == 42
    assert entry["status"] == 200
    assert entry["time"].endswith("+00:00")


def test_log_line_without_ids_leaves_them_out():
    entry = format_json("started")

    assert "request_id" not in entry
    assert "deployment_id" not in entry


def test_uvicorns_colour_codes_are_left_out():
    entry = format_json("Uvicorn running", color_message="\x1b[1mUvicorn running\x1b[0m")

    assert "color_message" not in entry


def test_exception_is_included_in_the_log_line():
    try:
        raise ValueError("bad input")
    except ValueError:
        import sys
        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed", None, sys.exc_info())

    entry = json.loads(JsonFormatter().format(record))

    assert "ValueError: bad input" in entry["exception"]


# ---------- request IDs ----------

def test_every_response_has_a_request_id(client):
    response = client.get("/health")

    assert len(response.headers["X-Request-ID"]) == 16


def test_request_id_from_the_caller_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-from-proxy-1"})

    assert response.headers["X-Request-ID"] == "trace-from-proxy-1"


def test_strange_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "<script>" + "x" * 100})

    assert response.headers["X-Request-ID"] != "<script>" + "x" * 100
    assert len(response.headers["X-Request-ID"]) == 16


def test_jobs_carry_the_request_id_to_the_worker(monkeypatch):
    sent = []
    monkeypatch.setattr(queue.redis_client, "xadd", lambda stream, fields: sent.append(fields) or "1-0")
    token = request_id_var.set("req-1")
    try:
        queue.publish(7)
        queue.publish_cleanup(7)
        queue.publish_wake(7)
    finally:
        request_id_var.reset(token)
    queue.publish(8)  # outside a request: no ID to pass on

    assert [fields.get("request_id") for fields in sent] == ["req-1", "req-1", "req-1", None]


def test_worker_logs_a_job_with_its_request_and_deployment_ids():
    seen = {}

    def handler(message_id, fields):
        seen["ids"] = (request_id_var.get(), deployment_id_var.get())

    worker.with_job_context(handler, "1-0", {"deployment_id": "7", "request_id": "req-1"})

    assert seen["ids"] == ("req-1", 7)
    assert request_id_var.get() is None  # reset after the job


def test_job_from_before_this_change_still_gets_a_request_id():
    seen = {}
    worker.with_job_context(lambda m, f: seen.update(id=request_id_var.get()), "1-0", {"deployment_id": "x"})

    assert seen["id"]


# ---------- /metrics ----------

@pytest.fixture
def build_stats(monkeypatch, redis_up):
    monkeypatch.setattr(metrics, "BUILD_STATS_KEY", "test:metrics:builds")
    queue.redis_client.delete("test:metrics:builds")
    yield
    queue.redis_client.delete("test:metrics:builds")


def test_metrics_page_has_requests_deployments_queue_and_builds(client, build_stats, monkeypatch):
    monkeypatch.setattr(metrics, "SessionLocal", TestingSessionLocal)
    metrics.record_build(25, succeeded=True)
    metrics.record_build(400, succeeded=False)
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert 'syphership_http_requests_total{method="GET",route="/health",status="200"}' in body
    assert 'syphership_deployments{status="RUNNING"} 0.0' in body
    assert "syphership_queue_length" in body
    assert 'syphership_builds_total{outcome="succeeded"} 1.0' in body
    assert 'syphership_builds_total{outcome="failed"} 1.0' in body
    assert 'syphership_build_duration_seconds_bucket{le="30"} 1.0' in body
    assert 'syphership_build_duration_seconds_bucket{le="+Inf"} 2.0' in body
    assert "syphership_build_duration_seconds_sum 425.0" in body


def test_unknown_paths_share_one_route_label(client):
    client.get("/wp-admin/setup.php")

    body = client.get("/metrics").text

    assert "wp-admin" not in body
    assert 'route="unmatched"' in body


def test_metrics_need_the_token_when_one_is_set(client, monkeypatch):
    monkeypatch.setattr(main, "METRICS_TOKEN", "s3cret")

    assert client.get("/metrics").status_code == 404
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 404
    assert client.get("/metrics", headers={"Authorization": "Bearer s3cret"}).status_code == 200
