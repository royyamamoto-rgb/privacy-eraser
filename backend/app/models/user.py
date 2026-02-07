"""User models."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, ARRAY, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Subscription
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free, basic, premium
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    exposures: Mapped[list["BrokerExposure"]] = relationship(back_populates="user")
    requests: Mapped[list["RemovalRequest"]] = relationship(back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user")


class UserProfile(Base):
    """User personal information to protect."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)

    # Name variations
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    maiden_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nicknames: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Contact
    emails: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    phone_numbers: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Addresses (current and past)
    addresses: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # [{street, city, state, zip, years}]

    # Other identifiers
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    relatives: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")


# Import for type hints
from app.models.exposure import BrokerExposure
from app.models.request import RemovalRequest
from app.models.alert import Alert
