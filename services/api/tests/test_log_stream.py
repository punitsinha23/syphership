import json

import pytest
import redis

import services.log_stream as log_stream
from models.deployment import Deployment, DeploymentStatus
from models.project import Project
from services.queue import redis_client
from tests.conftest import TestingSessionLocal

# High IDs so these never touch a real deployment's stream in the dev Redis.
TEST_ID = 990001


@pytest.fixture(autouse=True)
def clean_streams():
    try:
        redis_client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("Redis is not running")
    keys = [log_stream.log_key(TEST_ID + n) for n in range(5)]
    redis_client.delete(*keys)
    yield
    redis_client.delete(*keys)


def parse(events):
    """SSE text -> [(event type, data, id)]; keepalive comments are skipped."""
    parsed = []
    for event in events:
        if event.startswith(":"):
            continue
        fields = {}
        for line in event.strip().split("\n"):
            name, _, value = line.partition(": ")
            fields[name.rstrip(":")] = value
        parsed.append((fields.get("event", "message"), fields.get("data"), fields.get("id")))
    return parsed


# ---------- publish / read ----------

def test_lines_are_read_back_in_order_and_end_with_an_end_event():
    log_stream.publish_line(TEST_ID, "#1 FROM python")
    log_stream.publish_line(TEST_ID, 'echo "quotes" and \\ backslash')
    log_stream.publish_end(TEST_ID)

    events = parse(log_stream.read_events(TEST_ID))

    assert [json.loads(data) for kind, data, _ in events if kind == "message"] == [
        "#1 FROM python",
        'echo "quotes" and \\ backslash',
    ]
    assert events[-1][0] == "end"


def test_reader_resumes_after_the_last_id_it_got():
    log_stream.publish_line(TEST_ID, "one")
    log_stream.publish_line(TEST_ID, "two")
    log_stream.publish_end(TEST_ID)
    first_id = parse(log_stream.read_events(TEST_ID))[0][2]

    events = parse(log_stream.read_events(TEST_ID, first_id))

    assert [json.loads(data) for kind, data, _ in events if kind == "message"] == ["two"]


def test_stream_expires_so_redis_cleans_up_by_itself():
    log_stream.publish_line(TEST_ID, "line")

    assert 0 < redis_client.ttl(log_stream.log_key(TEST_ID)) <= log_stream.LOG_TTL_SECONDS


def test_long_build_is_capped(monkeypatch):
    monkeypatch.setattr(log_stream, "MAX_LIVE_LINES", 10)
    for n in range(500):
        log_stream.publish_line(TEST_ID, f"line {n}")

    # approximate trimming keeps a little more than the cap, never everything
    assert redis_client.xlen(log_stream.log_key(TEST_ID)) < 500


def test_quiet_build_gets_keepalives_and_gives_up_at_the_limit(monkeypatch):
    monkeypatch.setattr(log_stream, "READ_BLOCK_MS", 10)
    monkeypatch.setattr(log_stream, "MAX_STREAM_SECONDS", 0.05)

    events = list(log_stream.read_events(TEST_ID))

    assert ": keepalive\n\n" in events
    assert events[-1] == log_stream.end_event()


def test_redis_down_never_breaks_the_build(monkeypatch):
    def down(*args, **kwargs):
        raise redis.exceptions.ConnectionError("down")
    monkeypatch.setattr(redis_client, "xadd", down)

    log_stream.publish_line(TEST_ID, "line")  # must not raise
    log_stream.publish_end(TEST_ID)


# ---------- the API endpoint ----------

def add_deployment(make_user, status, email="auth@example.com", username="authuser"):
    db = TestingSessionLocal()
    try:
        project = Project(user_id=make_user(email=email, username=username), name="Blog", description="")
        db.add(project)
        db.flush()
        deployment = Deployment(project_id=project.id, commit_sha="a" * 40, status=status)
        db.add(deployment)
        db.commit()
        return deployment.id
    finally:
        db.close()


@pytest.fixture
def stream_id(monkeypatch):
    """Point the endpoint's deployment at a test stream key."""
    monkeypatch.setattr(log_stream, "log_key", lambda deployment_id: f"logs:{TEST_ID}")
    return TEST_ID


def owner_headers(deployment_id):
    """A session for the user who owns the deployment."""
    from auth.security import create_session_tokens

    db = TestingSessionLocal()
    try:
        owner_id = db.get(Project, db.get(Deployment, deployment_id).project_id).user_id
    finally:
        db.close()
    return {"Authorization": f"Bearer {create_session_tokens(owner_id)['access_token']}"}


def test_owner_gets_the_lines_as_server_sent_events(client, make_user, stream_id):
    deployment_id = add_deployment(make_user, DeploymentStatus.BUILDING)
    log_stream.publish_line(stream_id, "#1 building")
    log_stream.publish_end(stream_id)

    response = client.get(f"/deployments/{deployment_id}/logs/stream", headers=owner_headers(deployment_id))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse(response.text.split("\n\n")[:-1])
    assert [json.loads(d) for kind, d, _ in events if kind == "message"] == ["#1 building"]
    assert events[-1][0] == "end"


def test_other_users_cannot_read_a_deployments_log(client, make_user, user2_headers, stream_id):
    deployment_id = add_deployment(make_user, DeploymentStatus.BUILDING)

    response = client.get(f"/deployments/{deployment_id}/logs/stream", headers=user2_headers)

    assert response.status_code == 404


def test_finished_deployment_without_live_log_just_ends(client, make_user, stream_id):
    deployment_id = add_deployment(make_user, DeploymentStatus.RUNNING)

    response = client.get(f"/deployments/{deployment_id}/logs/stream", headers=owner_headers(deployment_id))

    assert response.status_code == 200
    assert response.text == log_stream.end_event()


def test_reconnecting_client_resumes_after_last_event_id(client, make_user, stream_id):
    deployment_id = add_deployment(make_user, DeploymentStatus.BUILDING)
    log_stream.publish_line(stream_id, "one")
    log_stream.publish_line(stream_id, "two")
    log_stream.publish_end(stream_id)
    first_id = parse(log_stream.read_events(stream_id))[0][2]

    response = client.get(
        f"/deployments/{deployment_id}/logs/stream",
        headers={**owner_headers(deployment_id), "Last-Event-ID": first_id},
    )

    lines = [json.loads(d) for kind, d, _ in parse(response.text.split("\n\n")[:-1]) if kind == "message"]
    assert lines == ["two"]
