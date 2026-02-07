"""Broker exposure model - tracks where user's data was found."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class BrokerExposure(Base):
    """Record of user's data found on a data broker site."""

    __tablename__ = "broker_exposures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    broker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("data_brokers.id"), nullable=True, index=True)

    # For exposures from deep scan (sites not in broker database)
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "PeekYou", "LinkedIn"
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # broker, additional_site, social_media, search_engine

    # Status: found, not_found, pending_removal, removed, re_listed
    status: Mapped[str] = mapped_column(String(50), default="found")

    # What was found
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_found: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"name": true, "address": true, "phone": true}
    screenshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamps
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="exposures")
    broker: Mapped["DataBroker"] = relationship(back_populates="exposures")
    requests: Mapped[list["RemovalRequest"]] = relationship(back_populates="exposure")


from app.models.user import User
from app.models.broker import DataBroker
from app.models.request import RemovalRequest
