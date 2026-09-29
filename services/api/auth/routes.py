from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from models.user import User
from schemas.user import Usercreate, UserLogin, PublicUser, RefreshToken
from auth.security import hash_password, verify_password, create_token, verify_token
from auth.dependencies import get_current_user, get_user_by_email


router = APIRouter(prefix="/auth")


def get_user_by_username(username: str, db: Session):
    return db.query(User).filter(User.username == username).first()


@router.post("/register")
def register(user: Usercreate, db: Session = Depends(get_db)):
    hashed_password = hash_password(user.password)

    if get_user_by_username(user.username, db) or get_user_by_email(user.email, db):
        raise HTTPException(
            status_code=400,
            detail="Email or username already exists",
        )

    new_user = User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_email(user.email, db)

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_token({"sub": db_user.email},
                        expire_delta=timedelta(hours=1),
                        token_type="access"
                        )
    refresh_token = create_token({"sub": db_user.email},
                                expire_delta=timedelta(days=7),
                                token_type="refresh"
                                )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_me(user: PublicUser = Depends(get_current_user)):
    return {
        "username": user.username,
        "email": user.email
    }

@router.post("/refresh")
def refresh_token(refresh_token: RefreshToken, db: Session = Depends(get_db)):
    payload = verify_token(refresh_token.refresh_token , "refresh")

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    sub = payload.get("sub")

    if get_user_by_email(sub, db) is None:
       raise HTTPException(
        status_code=401,
        detail="User not found"
)

    new_access_token = create_token({'sub': sub}, expire_delta=timedelta(hours=1), token_type="access")
    return {
        "access_token": new_access_token,
        "token_type": "bearer" }


    
    