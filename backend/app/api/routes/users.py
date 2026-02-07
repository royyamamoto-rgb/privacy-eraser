"""User routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.user import User, UserProfile

router = APIRouter()


# Schemas
class AddressSchema(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None  # Frontend sends 'zip'
    zip_code: str | None = None  # Also accept 'zip_code'
    years: str | None = None  # e.g., "2018-2022"


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    maiden_name: str | None = None
    nicknames: list[str] | None = None
    emails: list[str] | None = None
    phone_numbers: list[str] | None = None
    addresses: list[dict] | None = None  # Accept raw dict for flexibility
    date_of_birth: str | None = None  # Accept string date from frontend
    relatives: list[str] | None = None


class ProfileResponse(BaseModel):
    id: str
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    maiden_name: str | None
    nicknames: list[str] | None
    emails: list[str] | None
    phone_numbers: list[str] | None
    addresses: list[dict] | None
    date_of_birth: datetime | None
    relatives: list[str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithProfile(BaseModel):
    id: str
    email: str
    plan: str
    is_verified: bool
    profile: ProfileResponse | None

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserWithProfile)
async def get_current_user_info(current_user: CurrentUser, db: DbSession):
    """Get current user with profile."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()

    profile_data = None
    if user.profile:
        profile_data = ProfileResponse(
            id=str(user.profile.id),
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            middle_name=user.profile.middle_name,
            maiden_name=user.profile.maiden_name,
            nicknames=user.profile.nicknames,
            emails=user.profile.emails,
            phone_numbers=user.profile.phone_numbers,
            addresses=user.profile.addresses,
            date_of_birth=user.profile.date_of_birth,
            relatives=user.profile.relatives,
            created_at=user.profile.created_at,
            updated_at=user.profile.updated_at,
        )

    return UserWithProfile(
        id=str(user.id),
        email=user.email,
        plan=user.plan,
        is_verified=user.is_verified,
        profile=profile_data,
    )


@router.put("/me/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update user profile with personal information."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # Update fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "addresses" and value:
            # Ensure addresses are dicts
            value = [addr if isinstance(addr, dict) else addr.model_dump() for addr in value]
        elif field == "date_of_birth" and value:
            # Parse date string to datetime
            if isinstance(value, str) and value:
                try:
                    value = datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    value = None
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        id=str(profile.id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        middle_name=profile.middle_name,
        maiden_name=profile.maiden_name,
        nicknames=profile.nicknames,
        emails=profile.emails,
        phone_numbers=profile.phone_numbers,
        addresses=profile.addresses,
        date_of_birth=profile.date_of_birth,
        relatives=profile.relatives,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
