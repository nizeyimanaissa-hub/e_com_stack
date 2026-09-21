import uuid

import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="test-secret", jwt_algorithm="HS256")


def test_hash_password_salts_each_call():
    h1 = hash_password("correcthorsebattery")
    h2 = hash_password("correcthorsebattery")
    assert h1 != h2


def test_verify_password_round_trip():
    hashed = hash_password("correcthorsebattery")
    assert verify_password("correcthorsebattery", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_access_token_round_trip(settings):
    user_id = uuid.uuid4()
    token = create_access_token(user_id, settings)
    assert decode_token(token, "access", settings) == user_id


def test_refresh_token_round_trip(settings):
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id, settings)
    assert decode_token(token, "refresh", settings) == user_id


def test_access_token_rejected_as_refresh(settings):
    token = create_access_token(uuid.uuid4(), settings)
    with pytest.raises(InvalidTokenError):
        decode_token(token, "refresh", settings)


def test_refresh_token_rejected_as_access(settings):
    token = create_refresh_token(uuid.uuid4(), settings)
    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings)


def test_garbage_token_rejected(settings):
    with pytest.raises(InvalidTokenError):
        decode_token("not-a-real-token", "access", settings)


def test_token_signed_with_different_secret_rejected(settings):
    other_settings = Settings(jwt_secret_key="a-different-secret", jwt_algorithm="HS256")
    token = create_access_token(uuid.uuid4(), other_settings)
    with pytest.raises(InvalidTokenError):
        decode_token(token, "access", settings)
