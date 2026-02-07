"""Authentication routes."""

import secrets
from datetime import datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.config import settings
from app.api.deps import DbSession
from app.models.user import User, UserProfile
from app.services.email import send_password_reset_email, send_verification_email

router = APIRouter()


# Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: DbSession):
    """Register a new user."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
    )
    db.add(user)

    # Create empty profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)

    await db.commit()
    await db.refresh(user)

    # Create token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return Token(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            plan=user.plan,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    """Login and get access token."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return Token(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            plan=user.plan,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: DbSession):
    """Send password reset email."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account exists, a reset link has been sent"}

    # Generate reset token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)

    await db.commit()

    # Send email
    await send_password_reset_email(user.email, token)

    return {"message": "If an account exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: DbSession):
    """Reset password with token."""
    result = await db.execute(
        select(User).where(User.reset_token == data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    # Update password
    user.password_hash = get_password_hash(data.password)
    user.reset_token = None
    user.reset_token_expires_at = None

    await db.commit()

    return {"message": "Password reset successful"}


@router.post("/verify-email")
async def verify_email(token: str, db: DbSession):
    """Verify email with token."""
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    user.is_verified = True
    user.verification_token = None

    await db.commit()

    return {"message": "Email verified successfully"}
