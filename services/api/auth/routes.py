from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, OAuthAccount
from schemas.user import CodeExchange, RefreshToken
from auth.security import create_token, verify_token, create_session_tokens, ACCESS_TOKEN_TTL
from auth.dependencies import get_current_user, get_user_by_sub
from auth.oauth import redeem_login_code


router = APIRouter(prefix="/auth")


@router.post("/exchange")
def exchange_login_code(body: CodeExchange, db: Session = Depends(get_db)):
    """Trade the one-time code from an OAuth callback for session tokens."""
    user_id = redeem_login_code(db, body.code)

    if user_id is None:
        raise HTTPException(
            status_code=400,
            detail="Sign-in link is invalid or has expired. Please sign in again."
        )

    return create_session_tokens(user_id)


@router.get("/me")
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    providers = sorted(
        provider for (provider,) in
        db.query(OAuthAccount.provider).filter(OAuthAccount.user_id == user.id)
    )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "providers": providers,
        "github_connected": "github" in providers,
    }

@router.post("/refresh")
def refresh_token(refresh_token: RefreshToken, db: Session = Depends(get_db)):
    payload = verify_token(refresh_token.refresh_token , "refresh")

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = get_user_by_sub(payload.get("sub"), db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    new_access_token = create_token({'sub': str(user.id)}, ACCESS_TOKEN_TTL, "access")
    return {
        "access_token": new_access_token,
        "token_type": "bearer" }
