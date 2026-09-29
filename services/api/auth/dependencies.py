from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from auth.security import verify_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_by_email(email: str, db: Session):
    return db.query(User).filter(User.email == email).first()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = verify_token(token, "access")

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    email = payload.get("sub")

    if email is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = get_user_by_email(email, db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthenticated user"
        )

    return user