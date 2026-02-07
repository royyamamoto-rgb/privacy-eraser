"""Removal request routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.request import RemovalRequest
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure

router = APIRouter()


# Schemas
class RequestCreate(BaseModel):
    exposure_id: str
    request_type: str = "opt_out"  # opt_out, gdpr_delete, ccpa_delete


class RequestResponse(BaseModel):
    id: str
    broker_id: str
    broker_name: str
    exposure_id: str | None
    request_type: str
    status: str
    submitted_at: datetime | None
    expected_completion: datetime | None
    completed_at: datetime | None
    requires_user_action: bool
    instructions: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RequestStats(BaseModel):
    total: int
    pending: int
    submitted: int
    completed: int
    failed: int
    requires_action: int


@router.get("/", response_model=list[RequestResponse])
async def list_requests(current_user: CurrentUser, db: DbSession):
    """List all removal requests for current user."""
    result = await db.execute(
        select(RemovalRequest, DataBroker)
        .join(DataBroker)
        .where(RemovalRequest.user_id == current_user.id)
        .order_by(RemovalRequest.created_at.desc())
    )
    rows = result.all()

    return [
        RequestResponse(
            id=str(req.id),
            broker_id=str(req.broker_id),
            broker_name=broker.name,
            exposure_id=str(req.exposure_id) if req.exposure_id else None,
            request_type=req.request_type,
            status=req.status,
            submitted_at=req.submitted_at,
            expected_completion=req.expected_completion,
            completed_at=req.completed_at,
            requires_user_action=req.requires_user_action,
            instructions=req.instructions,
            created_at=req.created_at,
        )
        for req, broker in rows
    ]


@router.get("/stats", response_model=RequestStats)
async def get_request_stats(current_user: CurrentUser, db: DbSession):
    """Get request statistics."""
    result = await db.execute(
        select(RemovalRequest).where(RemovalRequest.user_id == current_user.id)
    )
    requests = result.scalars().all()

    return RequestStats(
        total=len(requests),
        pending=sum(1 for r in requests if r.status == "pending"),
        submitted=sum(1 for r in requests if r.status == "submitted"),
        completed=sum(1 for r in requests if r.status == "completed"),
        failed=sum(1 for r in requests if r.status == "failed"),
        requires_action=sum(1 for r in requests if r.requires_user_action),
    )


@router.post("/", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a new removal request."""
    # Get exposure
    exposure_result = await db.execute(
        select(BrokerExposure)
        .where(BrokerExposure.id == request_data.exposure_id)
        .where(BrokerExposure.user_id == current_user.id)
    )
    exposure = exposure_result.scalar_one_or_none()

    if not exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    # Get broker
    broker_result = await db.execute(
        select(DataBroker).where(DataBroker.id == exposure.broker_id)
    )
    broker = broker_result.scalar_one()

    # Check for existing request
    existing_result = await db.execute(
        select(RemovalRequest)
        .where(RemovalRequest.exposure_id == exposure.id)
        .where(RemovalRequest.status.not_in(["completed", "failed"]))
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Request already exists for this exposure")

    # Create request
    request = RemovalRequest(
        user_id=current_user.id,
        broker_id=broker.id,
        exposure_id=exposure.id,
        request_type=request_data.request_type,
        status="pending",
        requires_user_action=not broker.can_automate,
        instructions=broker.opt_out_instructions if not broker.can_automate else None,
    )
    db.add(request)

    # Update exposure status
    exposure.status = "pending_removal"

    await db.commit()
    await db.refresh(request)

    return RequestResponse(
        id=str(request.id),
        broker_id=str(request.broker_id),
        broker_name=broker.name,
        exposure_id=str(request.exposure_id),
        request_type=request.request_type,
        status=request.status,
        submitted_at=request.submitted_at,
        expected_completion=request.expected_completion,
        completed_at=request.completed_at,
        requires_user_action=request.requires_user_action,
        instructions=request.instructions,
        created_at=request.created_at,
    )


@router.post("/{request_id}/submit")
async def submit_request(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Submit a removal request (trigger auto-submission or mark as submitted)."""
    result = await db.execute(
        select(RemovalRequest)
        .where(RemovalRequest.id == request_id)
        .where(RemovalRequest.user_id == current_user.id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request already submitted")

    # Get broker
    broker_result = await db.execute(
        select(DataBroker).where(DataBroker.id == request.broker_id)
    )
    broker = broker_result.scalar_one()

    # If automatable, queue for auto-submission
    # For MVP, just mark as submitted
    request.status = "submitted"
    request.submitted_at = datetime.utcnow()
    request.method_used = "auto_form" if broker.can_automate else "manual"

    # Calculate expected completion
    from datetime import timedelta
    request.expected_completion = (datetime.utcnow() + timedelta(days=broker.processing_days)).date()

    await db.commit()

    return {"status": "submitted", "expected_completion": request.expected_completion}


@router.post("/{request_id}/complete")
async def mark_request_complete(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark a request as completed (user confirms removal)."""
    result = await db.execute(
        select(RemovalRequest)
        .where(RemovalRequest.id == request_id)
        .where(RemovalRequest.user_id == current_user.id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status = "completed"
    request.completed_at = datetime.utcnow()

    # Update exposure status
    if request.exposure_id:
        exposure_result = await db.execute(
            select(BrokerExposure).where(BrokerExposure.id == request.exposure_id)
        )
        exposure = exposure_result.scalar_one_or_none()
        if exposure:
            exposure.status = "removed"
            exposure.removed_at = datetime.utcnow()

    await db.commit()

    return {"status": "completed"}
