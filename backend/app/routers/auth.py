from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class EmailAlreadyRegisteredError(AppError):
    def __init__(self) -> None:
        super().__init__("An account with this email already exists", code="email_taken", status_code=409)


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__("Incorrect email or password", code="invalid_credentials", status_code=401)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise EmailAlreadyRegisteredError() from exc

    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest, db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> TokenPair:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise InvalidCredentialsError()

    return TokenPair(
        access_token=create_access_token(user.id, settings),
        refresh_token=create_refresh_token(user.id, settings),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(body: RefreshRequest, settings: Settings = Depends(get_settings)) -> AccessToken:
    user_id = decode_token(body.refresh_token, expected_type="refresh", settings=settings)
    return AccessToken(access_token=create_access_token(user_id, settings))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
