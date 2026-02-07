"""Exposure monitoring tasks."""

import asyncio
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
from app.models.alert import Alert
from app.models.user import User, UserProfile
from app.services.scanner import BrokerScanner


def get_async_session():
    """Create async database session for worker."""
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@shared_task(bind=True)
def scan_all_users(self):
    """Daily scan of all users for new exposures."""
    return asyncio.get_event_loop().run_until_complete(
        _scan_all_users_async()
    )


async def _scan_all_users_async():
    """Async implementation of scanning all users."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get all users with active subscriptions
        result = await db.execute(
            select(User).where(
                (User.subscription_ends_at > datetime.utcnow()) |
                (User.plan == "free")  # Free users get scans too
            )
        )
        users = result.scalars().all()

        total_scanned = 0
        total_new_exposures = 0

        for user in users:
            # Get profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile or not profile.first_name:
                continue

            # Get active brokers
            brokers_result = await db.execute(
                select(DataBroker).where(DataBroker.is_active == True)
            )
            brokers = brokers_result.scalars().all()

            # Scan
            scanner = BrokerScanner()
            results = await scanner.scan_all_brokers(brokers, profile)

            for result in results:
                if result.found:
                    # Check if this is a new exposure
                    existing = await db.execute(
                        select(BrokerExposure)
                        .where(BrokerExposure.user_id == user.id)
                        .where(BrokerExposure.broker_id == result.broker_id)
                    )
                    exposure = existing.scalar_one_or_none()

                    if not exposure:
                        # New exposure - create it
                        exposure = BrokerExposure(
                            user_id=user.id,
                            broker_id=result.broker_id,
                            status="found",
                            profile_url=result.profile_url,
                            data_found=result.data_found,
                            first_detected_at=datetime.utcnow(),
                            last_checked_at=datetime.utcnow(),
                        )
                        db.add(exposure)
                        total_new_exposures += 1

                        # Create alert
                        broker = next(b for b in brokers if str(b.id) == result.broker_id)
                        alert = Alert(
                            user_id=user.id,
                            alert_type="new_exposure",
                            severity="high",
                            title=f"New exposure found on {broker.name}",
                            description=f"Your personal information was found on {broker.name}. We recommend submitting a removal request.",
                            source_url=result.profile_url,
                        )
                        db.add(alert)
                    else:
                        # Update last checked
                        exposure.last_checked_at = datetime.utcnow()

            total_scanned += 1

        await db.commit()

        return {
            "users_scanned": total_scanned,
            "new_exposures": total_new_exposures,
        }


@shared_task(bind=True)
def check_relistings(self):
    """Check if removed profiles have been re-listed."""
    return asyncio.get_event_loop().run_until_complete(
        _check_relistings_async()
    )


async def _check_relistings_async():
    """Async implementation of relisting check."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get all removed exposures
        result = await db.execute(
            select(BrokerExposure)
            .where(BrokerExposure.status == "removed")
            .where(
                # Check those not verified in last 7 days
                (BrokerExposure.last_checked_at < datetime.utcnow() - timedelta(days=7)) |
                (BrokerExposure.last_checked_at == None)
            )
        )
        exposures = result.scalars().all()

        relistings = 0
        checked = 0

        for exposure in exposures:
            # Get broker
            broker_result = await db.execute(
                select(DataBroker).where(DataBroker.id == exposure.broker_id)
            )
            broker = broker_result.scalar_one_or_none()

            if not broker:
                continue

            # Get user profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == exposure.user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not profile:
                continue

            # Re-scan this broker
            scanner = BrokerScanner()
            scan_result = await scanner.scan_broker(broker, profile)

            exposure.last_checked_at = datetime.utcnow()
            checked += 1

            if scan_result.found:
                # Re-listed!
                exposure.status = "found"
                exposure.profile_url = scan_result.profile_url
                relistings += 1

                # Create high-priority alert
                alert = Alert(
                    user_id=exposure.user_id,
                    alert_type="re_listed",
                    severity="critical",
                    title=f"Re-listed on {broker.name}!",
                    description=f"Your information has reappeared on {broker.name} after removal. A new removal request is recommended.",
                    source_url=scan_result.profile_url,
                )
                db.add(alert)

        await db.commit()

        return {
            "checked": checked,
            "relistings_found": relistings,
        }


@shared_task(bind=True)
def verify_removal(self, exposure_id: str):
    """Verify that a specific exposure has been removed."""
    return asyncio.get_event_loop().run_until_complete(
        _verify_removal_async(exposure_id)
    )


async def _verify_removal_async(exposure_id: str):
    """Async implementation of removal verification."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get exposure
        exposure_result = await db.execute(
            select(BrokerExposure).where(BrokerExposure.id == exposure_id)
        )
        exposure = exposure_result.scalar_one_or_none()

        if not exposure:
            return {"error": "Exposure not found"}

        # Get broker
        broker_result = await db.execute(
            select(DataBroker).where(DataBroker.id == exposure.broker_id)
        )
        broker = broker_result.scalar_one_or_none()

        if not broker:
            return {"error": "Broker not found"}

        # Get user profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == exposure.user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return {"error": "User profile not found"}

        # Scan
        scanner = BrokerScanner()
        result = await scanner.scan_broker(broker, profile)

        exposure.last_checked_at = datetime.utcnow()

        if result.found:
            # Still there
            exposure.status = "found"
            exposure.profile_url = result.profile_url
            verified = False
        else:
            # Confirmed removed
            exposure.status = "removed"
            exposure.removed_at = datetime.utcnow()
            verified = True

            # Create success alert
            alert = Alert(
                user_id=exposure.user_id,
                alert_type="removal_confirmed",
                severity="low",
                title=f"Removal confirmed: {broker.name}",
                description=f"Your information has been successfully removed from {broker.name}.",
            )
            db.add(alert)

        await db.commit()

        return {
            "exposure_id": exposure_id,
            "broker": broker.name,
            "verified_removed": verified,
            "still_found": result.found,
        }
