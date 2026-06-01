from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, is_token_type, verify_password
from app.models.refresh_token import RefreshTokenSession
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse, TokenResponse, UserCreate, UserLogin
from app.schemas.user import UserRead


router = APIRouter()


def user_to_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


def issue_tokens(user: User, settings) -> tuple[str, str, str, datetime]:
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    refresh_token, jti, expires_at = create_refresh_token(
        subject=user.id,
        role=user.role,
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        expires_days=settings.refresh_token_expire_days,
    )
    return access_token, refresh_token, jti, expires_at


def set_refresh_cookie(response: Response, refresh_token: str, settings) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.secure_refresh_cookie,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=UserRole.user.value,
    )
    db.add(user)
    db.flush()

    access_token, refresh_token, jti, expires_at = issue_tokens(user, settings)
    db.add(RefreshTokenSession(jti=jti, user_id=user.id, expires_at=expires_at))
    db.commit()

    set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(access_token=access_token, user=user_to_read(user))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token, refresh_token, jti, expires_at = issue_tokens(user, settings)
    db.add(RefreshTokenSession(jti=jti, user_id=user.id, expires_at=expires_at))
    db.commit()

    set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(access_token=access_token, user=user_to_read(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> TokenResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        payload = decode_token(token, secret_key=settings.secret_key, algorithm=settings.algorithm)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if not is_token_type(payload, "refresh"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    session_row = db.get(RefreshTokenSession, jti)
    if session_row is None or session_row.revoked_at is not None or session_row.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    session_row.revoked_at = datetime.now(timezone.utc)
    access_token, new_refresh_token, new_jti, expires_at = issue_tokens(user, settings)
    db.add(RefreshTokenSession(jti=new_jti, user_id=user.id, expires_at=expires_at))
    db.commit()

    set_refresh_cookie(response, new_refresh_token, settings)
    return TokenResponse(access_token=access_token, user=user_to_read(user))


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings=Depends(get_settings),
) -> MessageResponse:
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_token(token, secret_key=settings.secret_key, algorithm=settings.algorithm)
            if payload.get("jti"):
                session_row = db.get(RefreshTokenSession, payload["jti"])
                if session_row is not None:
                    session_row.revoked_at = datetime.now(timezone.utc)
                    db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return user_to_read(current_user)
