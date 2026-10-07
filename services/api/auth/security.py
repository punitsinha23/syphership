from pwdlib import PasswordHash
from jose import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.") 

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def create_token(data: dict, expire_delta: timedelta, token_type: str):
    to_encode = data.copy()

    expire = datetime.utcnow() + expire_delta
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


