from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings


_BCRYPT_MAX_PASSWORD_BYTES = 72
_BCRYPT_ROUNDS = 12


def _password_bytes(password: str) -> bytes:
    """
    bcrypt has a hard limit of 72 bytes for the password input.
    We enforce this early so API handlers can return a clean 4xx.
    """
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password too long for bcrypt (max {_BCRYPT_MAX_PASSWORD_BYTES} bytes)")
    return raw


def hash_password(password: str) -> str:
    pw = _password_bytes(password)
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(pw, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    pw = _password_bytes(password)
    return bcrypt.checkpw(pw, password_hash.encode("utf-8"))


def create_access_token(*, subject: str, expires_delta: timedelta) -> str:
    return _create_token(subject=subject, token_type="access", expires_delta=expires_delta)


def create_refresh_token(*, subject: str, expires_delta: timedelta) -> str:
    return _create_token(subject=subject, token_type="refresh", expires_delta=expires_delta)


def _create_token(*, subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e
    if payload.get("type") not in {"access", "refresh"}:
        raise ValueError("Invalid token type")
    return payload

