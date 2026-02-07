"""Broker scanning tasks."""

import asyncio
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
from app.models.user import User, UserProfile
from app.services.scanner import BrokerScanner


def get_async_session():
    """Create async database session for worker."""
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@shared_task(bind=True, max_retries=3)
def scan_user_brokers(self, user_id: str):
    """Scan all brokers for a specific user."""
    return asyncio.get_event_loop().run_until_complete(
        _scan_user_brokers_async(user_id)
    )


async def _scan_user_brokers_async(user_id: str):
    """Async implementation of broker scanning."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get user profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return {"error": "User profile not found", "scanned": 0, "found": 0}

        # Get all active brokers
        brokers_result = await db.execute(
            select(DataBroker).where(DataBroker.is_active == True)
        )
        brokers = brokers_result.scalars().all()

        if not brokers:
            return {"error": "No brokers configured", "scanned": 0, "found": 0}

        # Initialize scanner
        scanner = BrokerScanner()

        # Scan all brokers
        scan_results = await scanner.scan_all_brokers(brokers, profile)

        # Process results
        found_count = 0
        scanned_count = len(scan_results)

        for result in scan_results:
            if result.found:
                found_count += 1

                # Check for existing exposure
                existing = await db.execute(
                    select(BrokerExposure)
                    .where(BrokerExposure.user_id == user_id)
                    .where(BrokerExposure.broker_id == result.broker_id)
                )
                exposure = existing.scalar_one_or_none()

                if exposure:
                    # Update existing exposure
                    exposure.status = "found"
                    exposure.profile_url = result.profile_url
                    exposure.data_found = result.data_found
                    exposure.last_checked_at = db.func.now()
                else:
                    # Create new exposure
                    from datetime import datetime
                    exposure = BrokerExposure(
                        user_id=user_id,
                        broker_id=result.broker_id,
                        status="found",
                        profile_url=result.profile_url,
                        data_found=result.data_found,
                        first_detected_at=datetime.utcnow(),
                        last_checked_at=datetime.utcnow(),
                    )
                    db.add(exposure)

        await db.commit()

        return {
            "scanned": scanned_count,
            "found": found_count,
            "user_id": user_id,
        }


@shared_task(bind=True, max_retries=3)
def scan_single_broker(self, user_id: str, broker_id: str):
    """Scan a single broker for a specific user."""
    return asyncio.get_event_loop().run_until_complete(
        _scan_single_broker_async(user_id, broker_id)
    )


async def _scan_single_broker_async(user_id: str, broker_id: str):
    """Async implementation of single broker scanning."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get user profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return {"error": "User profile not found"}

        # Get broker
        broker_result = await db.execute(
            select(DataBroker).where(DataBroker.id == broker_id)
        )
        broker = broker_result.scalar_one_or_none()

        if not broker:
            return {"error": "Broker not found"}

        # Scan
        scanner = BrokerScanner()
        result = await scanner.scan_broker(broker, profile)

        if result.found:
            # Update or create exposure
            from datetime import datetime

            existing = await db.execute(
                select(BrokerExposure)
                .where(BrokerExposure.user_id == user_id)
                .where(BrokerExposure.broker_id == broker_id)
            )
            exposure = existing.scalar_one_or_none()

            if exposure:
                exposure.status = "found"
                exposure.profile_url = result.profile_url
                exposure.data_found = result.data_found
                exposure.last_checked_at = datetime.utcnow()
            else:
                exposure = BrokerExposure(
                    user_id=user_id,
                    broker_id=broker_id,
                    status="found",
                    profile_url=result.profile_url,
                    data_found=result.data_found,
                    first_detected_at=datetime.utcnow(),
                    last_checked_at=datetime.utcnow(),
                )
                db.add(exposure)

            await db.commit()

        return {
            "broker_id": broker_id,
            "broker_name": broker.name,
            "found": result.found,
            "profile_url": result.profile_url,
            "error": result.error,
        }
