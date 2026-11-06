from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, OAuthAccount
from schemas.user import CodeExchange, DeleteAccount, RefreshToken
from auth.security import verify_token
from auth.sessions import end_session, issue_session, rotate_session
from auth.dependencies import get_current_user, get_user_by_sub
from auth.oauth import redeem_login_code
from services.account import delete_account
from services.rate_limit import limit_by_ip, limit_by_user


router = APIRouter(prefix="/auth")


@router.post("/exchange", dependencies=[Depends(limit_by_ip("exchange", 10))])
def exchange_login_code(body: CodeExchange, db: Session = Depends(get_db)):
    """Trade the one-time code from an OAuth callback for session tokens."""
    user_id = redeem_login_code(db, body.code)

    if user_id is None:
        raise HTTPException(
            status_code=400,
            detail="Sign-in link is invalid or has expired. Please sign in again."
        )

    return issue_session(db, user_id)


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

@router.post("/refresh", dependencies=[Depends(limit_by_ip("refresh", 30))])
def refresh_token(refresh_token: RefreshToken, db: Session = Depends(get_db)):
    """Trade a refresh token for a new pair. Each refresh token works once."""
    payload = verify_token(refresh_token.refresh_token, "refresh")

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

    tokens = rotate_session(db, user.id, payload.get("jti"))

    if tokens is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    return tokens


@router.post("/logout", dependencies=[Depends(limit_by_ip("logout", 30))])
def logout(refresh_token: RefreshToken, db: Session = Depends(get_db)):
    payload = verify_token(refresh_token.refresh_token, "refresh")

    if payload is not None:
        end_session(db, payload.get("jti"))

    return {"message": "Signed out"}


@router.delete("/me", dependencies=[Depends(limit_by_user("delete-account", 5))])
def delete_me(body: DeleteAccount, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Typing the username guards against a stray request or a slip of the mouse.
    if body.confirm_username != user.username:
        raise HTTPException(status_code=422, detail="Type your username to confirm.")

    delete_account(db, user)
    return {"message": "Account deleted"}
