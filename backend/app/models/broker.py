"""Data broker model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class DataBroker(Base):
    """Data broker information and opt-out procedures."""

    __tablename__ = "data_brokers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # people_search, background_check, marketing

    # Search URL pattern
    search_url_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)  # URL with {name}, {city}, {state} placeholders

    # Opt-out information
    opt_out_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opt_out_method: Mapped[str] = mapped_column(String(50), default="form")  # form, email, mail, api
    opt_out_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opt_out_instructions: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Requirements
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_id: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_days: Mapped[int] = mapped_column(Integer, default=30)

    # Automation info
    can_automate: Mapped[bool] = mapped_column(Boolean, default=False)
    form_selectors: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # CSS selectors for form fields
    captcha_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # none, recaptcha, hcaptcha

    # Difficulty rating (1-5)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exposures: Mapped[list["BrokerExposure"]] = relationship(back_populates="broker")
    requests: Mapped[list["RemovalRequest"]] = relationship(back_populates="broker")


from app.models.exposure import BrokerExposure
from app.models.request import RemovalRequest
