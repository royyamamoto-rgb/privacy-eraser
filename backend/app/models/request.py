"""Removal request model - tracks opt-out requests."""

import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class RemovalRequest(Base):
    """Removal/opt-out request to a data broker."""

    __tablename__ = "removal_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    broker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("data_brokers.id"), nullable=True, index=True)
    exposure_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("broker_exposures.id"), nullable=True)

    # Request type: opt_out, gdpr_delete, gdpr_access, ccpa_delete, ccpa_opt_out
    request_type: Mapped[str] = mapped_column(String(50), default="opt_out")

    # Status: draft, pending, submitted, acknowledged, in_progress, completed, failed, requires_action
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Request details
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_completion: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # For manual requests
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_user_action: Mapped[bool] = mapped_column(Boolean, default=False)

    # Submission method used
    method_used: Mapped[str | None] = mapped_column(String(50), nullable=True)  # auto_form, auto_email, manual

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="requests")
    broker: Mapped["DataBroker"] = relationship(back_populates="requests")
    exposure: Mapped["BrokerExposure"] = relationship(back_populates="requests")


from app.models.user import User
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
