import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt

from app.core.config import Settings
from app.core.errors import AppError

TokenType = Literal["access", "refresh"]


class InvalidTokenError(AppError):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, code="invalid_token", status_code=401)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(subject: uuid.UUID, token_type: TokenType, expires_delta: timedelta, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    return _create_token(
        user_id, "access", timedelta(minutes=settings.access_token_expire_minutes), settings
    )


def create_refresh_token(user_id: uuid.UUID, settings: Settings) -> str:
    return _create_token(
        user_id, "refresh", timedelta(days=settings.refresh_token_expire_days), settings
    )


def decode_token(token: str, expected_type: TokenType, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError() from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError() from exc
