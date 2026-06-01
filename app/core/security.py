from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, subject: str, role: str, secret_key: str, algorithm: str, expires_minutes: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def create_refresh_token(*, subject: str, role: str, secret_key: str, algorithm: str, expires_days: int) -> tuple[str, str, datetime]:
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    jti = str(uuid4())
    payload = {"sub": subject, "role": role, "type": "refresh", "jti": jti, "exp": expire}
    return jwt.encode(payload, secret_key, algorithm=algorithm), jti, expire


def decode_token(token: str, *, secret_key: str, algorithm: str) -> dict[str, str]:
    return jwt.decode(token, secret_key, algorithms=[algorithm])


def is_token_type(payload: dict[str, str], token_type: str) -> bool:
    return payload.get("type") == token_type
