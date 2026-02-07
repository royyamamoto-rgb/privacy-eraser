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
    broker_id: str | None
    broker_name: str
    source_type: str | None
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
    """List all exposures for current user (from all sources)."""
    from sqlalchemy.orm import selectinload

    # Get all exposures with optional broker join
    result = await db.execute(
        select(BrokerExposure)
        .outerjoin(DataBroker)
        .options(selectinload(BrokerExposure.broker))
        .where(BrokerExposure.user_id == current_user.id)
        .order_by(BrokerExposure.first_detected_at.desc())
    )
    exposures = result.scalars().all()

    return [
        ExposureResponse(
            id=str(exp.id),
            broker_id=str(exp.broker_id) if exp.broker_id else None,
            broker_name=exp.broker.name if exp.broker else exp.source_name or "Unknown Source",
            source_type=exp.source_type,
            status=exp.status,
            profile_url=exp.profile_url,
            data_found=exp.data_found,
            first_detected_at=exp.first_detected_at,
            last_checked_at=exp.last_checked_at,
        )
        for exp in exposures
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
    """Background task for deep scan across all sources."""
    from app.db.database import async_session
    import uuid as uuid_lib

    async with async_session() as db:
        # Get all active brokers from database
        result = await db.execute(
            select(DataBroker).where(DataBroker.is_active == True)
        )
        brokers = result.scalars().all()

        # Run deep scanner (scans brokers + additional sites + social + search engines)
        scanner = BrokerScanner()
        scan_results = await scanner.scan_all_brokers(brokers, profile)

        # Save all results as exposures
        for scan_result in scan_results:
            if not scan_result.found:
                continue

            # Determine if this is a database broker or external source
            is_db_broker = False
            broker_uuid = None

            try:
                broker_uuid = uuid_lib.UUID(scan_result.broker_id)
                is_db_broker = True
            except (ValueError, TypeError):
                is_db_broker = False

            if is_db_broker:
                # Check if exposure already exists for this broker
                existing = await db.execute(
                    select(BrokerExposure)
                    .where(BrokerExposure.user_id == user_id)
                    .where(BrokerExposure.broker_id == broker_uuid)
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
                        broker_id=broker_uuid,
                        source_type="broker",
                        status="found",
                        profile_url=scan_result.profile_url,
                        data_found=scan_result.data_found,
                        first_detected_at=datetime.utcnow(),
                        last_checked_at=datetime.utcnow(),
                    )
                    db.add(exposure)
            else:
                # External source (additional site, social media, search engine)
                source_name = scan_result.broker_id.replace("additional_", "").replace("social_", "").replace("_", " ").title()
                if scan_result.data_found and "site_name" in scan_result.data_found:
                    source_name = scan_result.data_found["site_name"]
                elif scan_result.data_found and "platform" in scan_result.data_found:
                    source_name = scan_result.data_found["platform"]

                # Check if exposure already exists for this source
                existing = await db.execute(
                    select(BrokerExposure)
                    .where(BrokerExposure.user_id == user_id)
                    .where(BrokerExposure.source_name == source_name)
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
                        broker_id=None,
                        source_name=source_name,
                        source_type=scan_result.source or "additional_site",
                        status="found",
                        profile_url=scan_result.profile_url,
                        data_found=scan_result.data_found,
                        first_detected_at=datetime.utcnow(),
                        last_checked_at=datetime.utcnow(),
                    )
                    db.add(exposure)

        await db.commit()
