import pytest
import redis

import services.rate_limit
from services.queue import redis_client
from services.rate_limit import is_allowed

KEY = "ratelimit:test:key"


def test_allows_up_to_the_limit_then_blocks():
    assert [is_allowed(KEY, 2, 60) for _ in range(3)] == [True, True, False]


def test_keys_are_counted_separately():
    is_allowed(KEY, 1, 60)

    assert is_allowed(KEY, 1, 60) is False
    assert is_allowed(KEY + ":other", 1, 60) is True


def test_counter_always_expires():
    is_allowed(KEY, 5, 60)

    assert 0 < redis_client.ttl(KEY) <= 60


def test_later_requests_do_not_extend_the_window():
    is_allowed(KEY, 5, 60)
    redis_client.expire(KEY, 10)

    is_allowed(KEY, 5, 60)

    assert redis_client.ttl(KEY) <= 10


def test_counter_resets_after_the_window():
    is_allowed(KEY, 1, 60)
    assert is_allowed(KEY, 1, 60) is False

    redis_client.delete(KEY)  # What expiry does at the end of the window.

    assert is_allowed(KEY, 1, 60) is True


def post_exchange(client):
    return client.post("/auth/exchange", json={"code": "not-a-real-code"})


def test_login_exchange_returns_429_over_the_limit(client):
    responses = [post_exchange(client).status_code for _ in range(11)]

    assert responses[:10] == [400] * 10
    assert responses[10] == 429


def test_webhook_is_limited_before_the_signature_check(client):
    responses = [client.post("/github/webhook", content=b"{}").status_code for _ in range(61)]

    assert responses[:60] == [401] * 60
    assert responses[60] == 429


def test_redis_down_returns_503(client, monkeypatch):
    def redis_down(key, limit, window_seconds):
        raise redis.exceptions.ConnectionError("Redis is down")

    monkeypatch.setattr(services.rate_limit, "is_allowed", redis_down)

    assert post_exchange(client).status_code == 503
