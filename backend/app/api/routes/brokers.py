"""Data broker routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DbSession
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
from app.services.scanner import BrokerScanner

router = APIRouter()


# Schemas
class BrokerResponse(BaseModel):
    id: str
    name: str
    domain: str
    category: str | None
    search_url_pattern: str | None
    opt_out_method: str
    processing_days: int
    difficulty: int
    can_automate: bool
    is_active: bool

    class Config:
        from_attributes = True


class ExposureResponse(BaseModel):
    id: str
    broker_id: str
    broker_name: str
    status: str
    profile_url: str | None
    data_found: dict | None
    first_detected_at: datetime
    last_checked_at: datetime

    class Config:
        from_attributes = True


class ScanStatus(BaseModel):
    total_brokers: int
    scanned: int
    found: int
    status: str  # pending, in_progress, completed


class DashboardStats(BaseModel):
    total_exposures: int
    pending_removals: int
    completed_removals: int
    brokers_scanned: int


@router.get("/", response_model=list[BrokerResponse])
async def list_brokers(db: DbSession, skip: int = 0, limit: int = 100):
    """List all data brokers."""
    result = await db.execute(
        select(DataBroker)
        .where(DataBroker.is_active == True)
        .order_by(DataBroker.name)
        .offset(skip)
        .limit(limit)
    )
    brokers = result.scalars().all()

    return [
        BrokerResponse(
            id=str(b.id),
            name=b.name,
            domain=b.domain,
            category=b.category,
            search_url_pattern=b.search_url_pattern,
            opt_out_method=b.opt_out_method,
            processing_days=b.processing_days,
            difficulty=b.difficulty,
            can_automate=b.can_automate,
            is_active=b.is_active,
        )
        for b in brokers
    ]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: CurrentUser, db: DbSession):
    """Get dashboard statistics for current user."""
    # Total exposures found
    total_result = await db.execute(
        select(func.count(BrokerExposure.id))
        .where(BrokerExposure.user_id == current_user.id)
        .where(BrokerExposure.status == "found")
    )
    total_exposures = total_result.scalar() or 0

    # Pending removals
    pending_result = await db.execute(
        select(func.count(BrokerExposure.id))
        .where(BrokerExposure.user_id == current_user.id)
        .where(BrokerExposure.status == "pending_removal")
    )
    pending_removals = pending_result.scalar() or 0

    # Completed removals
    completed_result = await db.execute(
        select(func.count(BrokerExposure.id))
        .where(BrokerExposure.user_id == current_user.id)
        .where(BrokerExposure.status == "removed")
    )
    completed_removals = completed_result.scalar() or 0

    # Total brokers scanned
    scanned_result = await db.execute(
        select(func.count(func.distinct(BrokerExposure.broker_id)))
        .where(BrokerExposure.user_id == current_user.id)
    )
    brokers_scanned = scanned_result.scalar() or 0

    return DashboardStats(
        total_exposures=total_exposures,
        pending_removals=pending_removals,
        completed_removals=completed_removals,
        brokers_scanned=brokers_scanned,
    )


@router.get("/exposures", response_model=list[ExposureResponse])
async def list_exposures(current_user: CurrentUser, db: DbSession):
    """List all exposures for current user."""
    result = await db.execute(
        select(BrokerExposure, DataBroker)
        .join(DataBroker)
        .where(BrokerExposure.user_id == current_user.id)
        .order_by(BrokerExposure.first_detected_at.desc())
    )
    rows = result.all()

    return [
        ExposureResponse(
            id=str(exp.id),
            broker_id=str(exp.broker_id),
            broker_name=broker.name,
            status=exp.status,
            profile_url=exp.profile_url,
            data_found=exp.data_found,
            first_detected_at=exp.first_detected_at,
            last_checked_at=exp.last_checked_at,
        )
        for exp, broker in rows
    ]


@router.post("/scan")
async def start_scan(
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Start scanning all brokers for user's information."""
    # Check if user has profile info
    from app.models.user import UserProfile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile or not profile.first_name or not profile.last_name:
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile with at least your name before scanning",
        )

    # Queue background scan
    # In production, this would be a Celery task
    # For now, return immediately and process in background
    background_tasks.add_task(
        run_broker_scan,
        user_id=str(current_user.id),
        profile=profile,
    )

    return {"status": "scan_started", "message": "Scanning brokers in background"}


async def run_broker_scan(user_id: str, profile):
    """Background task to scan all brokers."""
    from app.db.database import async_session

    async with async_session() as db:
        # Get all active brokers
        result = await db.execute(
            select(DataBroker).where(DataBroker.is_active == True)
        )
        brokers = result.scalars().all()

        if not brokers:
            return

        # Run scanner
        scanner = BrokerScanner()
        scan_results = await scanner.scan_all_brokers(brokers, profile)

        # Save results as exposures
        for scan_result in scan_results:
            if scan_result.found:
                # Check if exposure already exists
                existing = await db.execute(
                    select(BrokerExposure)
                    .where(BrokerExposure.user_id == user_id)
                    .where(BrokerExposure.broker_id == scan_result.broker_id)
                )
                exposure = existing.scalar_one_or_none()

                if exposure:
                    exposure.status = "found"
                    exposure.profile_url = scan_result.profile_url
                    exposure.data_found = scan_result.data_found
                    exposure.last_checked_at = datetime.utcnow()
                else:
                    exposure = BrokerExposure(
                        user_id=user_id,
                        broker_id=scan_result.broker_id,
                        status="found",
                        profile_url=scan_result.profile_url,
                        data_found=scan_result.data_found,
                        first_detected_at=datetime.utcnow(),
                        last_checked_at=datetime.utcnow(),
                    )
                    db.add(exposure)

        await db.commit()
