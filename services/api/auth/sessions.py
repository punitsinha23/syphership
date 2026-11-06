import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from auth.security import REFRESH_TOKEN_TTL, create_session_tokens
from models.user import RefreshToken

# Two browser tabs can refresh at the same moment. A repeat this soon after the
# first use is treated as that, not as a stolen token.
REUSE_GRACE = timedelta(seconds=30)


def issue_session(db: Session, user_id: int) -> dict:
    """New access and refresh tokens, with the refresh token on record."""
    now = datetime.now(timezone.utc)
    jti = secrets.token_urlsafe(32)

    db.execute(delete(RefreshToken).where(RefreshToken.expires_at < now))
    db.add(RefreshToken(jti=jti, user_id=user_id, expires_at=now + REFRESH_TOKEN_TTL))
    db.commit()

    return create_session_tokens(user_id, jti)


def rotate_session(db: Session, user_id: int, jti: str | None) -> dict | None:
    """Swap a refresh token for a new session; None if it can't be used.

    A token used twice means someone else may have a copy, so every session
    of that user is ended."""
    now = datetime.now(timezone.utc)

    # One UPDATE, so two requests can't both use the same token.
    used = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.used_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(used_at=now)
    ).rowcount
    db.commit()

    if used == 1:
        return issue_session(db, user_id)

    token = db.get(RefreshToken, jti) if jti else None
    if token is not None and token.used_at is not None and now - token.used_at > REUSE_GRACE:
        end_all_sessions(db, token.user_id)

    return None


def end_session(db: Session, jti: str | None) -> None:
    db.execute(delete(RefreshToken).where(RefreshToken.jti == jti))
    db.commit()


def end_all_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    db.commit()
