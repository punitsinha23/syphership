import redis
from fastapi import Depends, HTTPException, Request

from auth.dependencies import get_current_user
from models.user import User
from services.queue import redis_client


def is_allowed(key: str, limit: int, window_seconds: int) -> bool:
    """True while this key has made at most `limit` requests in the window."""
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds, nx=True)
    count = pipe.execute()[0]
    return count <= limit


def enforce(key: str, limit: int, window_seconds: int) -> None:
    """Raise 429 over the limit, and 503 if Redis can't be reached."""
    try:
        allowed = is_allowed(key, limit, window_seconds)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Service unavailable. Try again.") from None

    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")


def limit_by_ip(name: str, limit: int, window_seconds: int = 60):
    """A route dependency that limits each client IP."""

    def check(request: Request) -> None:
        enforce(f"ratelimit:{name}:ip:{request.client.host}", limit, window_seconds)

    return check


def limit_by_user(name: str, limit: int, window_seconds: int = 60):
    """A route dependency that limits each logged-in user."""

    def check(user: User = Depends(get_current_user)) -> None:
        enforce(f"ratelimit:{name}:user:{user.id}", limit, window_seconds)

    return check
