import redis

import main

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Syphership API is running"


def test_security_headers_are_set(client):
    headers = client.get("/").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "max-age" in headers["Strict-Transport-Security"]


def test_cors_only_allows_the_frontend(client):
    response = client.options(
        "/projects/",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers


def test_health_needs_nothing(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_when_everything_is_up(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": True, "redis": True}


def test_not_ready_when_redis_is_down(client, monkeypatch):
    def fail():
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(main.redis_client, "ping", fail)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["redis"] is False
