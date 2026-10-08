from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from auth.security import verify_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_user_by_sub(sub, db: Session):
    """Tokens carry the user id as `sub`."""
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None

    return db.get(User, user_id)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    payload = verify_token(credentials.credentials, "access") if credentials else None

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = get_user_by_sub(payload.get("sub"), db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthenticated user"
        )

    return user
