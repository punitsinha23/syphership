from jose import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.")

ALGORITHM = "HS256"

ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=7)

# Fernet key derived from SECRET_KEY, used to encrypt provider tokens at rest
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()))


def create_token(data: dict, expire_delta: timedelta, token_type: str):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expire_delta
    to_encode.update({'exp': expire,
                      'type' : token_type
                      })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != token_type:
            return None

        return payload

    except Exception:
        return None


def create_session_tokens(user_id: int) -> dict:
    sub = str(user_id)
    return {
        "access_token": create_token({"sub": sub}, ACCESS_TOKEN_TTL, "access"),
        "refresh_token": create_token({"sub": sub}, REFRESH_TOKEN_TTL, "refresh"),
        "token_type": "bearer",
    }


def encrypt_secret(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str | None:
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        return None
