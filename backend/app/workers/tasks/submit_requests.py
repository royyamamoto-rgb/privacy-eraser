"""Request submission tasks."""

import asyncio
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models.request import RemovalRequest
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
from app.models.user import UserProfile
from app.services.request_manager import RequestManager


def get_async_session():
    """Create async database session for worker."""
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@shared_task(bind=True)
def process_pending_requests(self):
    """Process all pending removal requests."""
    return asyncio.get_event_loop().run_until_complete(
        _process_pending_requests_async()
    )


async def _process_pending_requests_async():
    """Async implementation of pending request processing."""

    async_session = get_async_session()

    async with async_session() as db:
        manager = RequestManager()
        result = await manager.process_pending_requests(db)
        return result


@shared_task(bind=True, max_retries=3)
def submit_single_request(self, request_id: str):
    """Submit a single removal request."""
    return asyncio.get_event_loop().run_until_complete(
        _submit_single_request_async(request_id)
    )


async def _submit_single_request_async(request_id: str):
    """Async implementation of single request submission."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get request
        request_result = await db.execute(
            select(RemovalRequest).where(RemovalRequest.id == request_id)
        )
        request = request_result.scalar_one_or_none()

        if not request:
            return {"error": "Request not found"}

        # Get broker
        broker_result = await db.execute(
            select(DataBroker).where(DataBroker.id == request.broker_id)
        )
        broker = broker_result.scalar_one_or_none()

        if not broker:
            return {"error": "Broker not found"}

        # Get user profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == request.user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return {"error": "User profile not found"}

        # Get exposure if exists
        exposure = None
        if request.exposure_id:
            exposure_result = await db.execute(
                select(BrokerExposure).where(BrokerExposure.id == request.exposure_id)
            )
            exposure = exposure_result.scalar_one_or_none()

        # Submit request
        manager = RequestManager()
        submission = await manager.submit_request(request, broker, profile, exposure)

        # Update request
        request.method_used = submission.method
        request.submitted_at = datetime.utcnow()

        if submission.success:
            request.status = "submitted"
            request.confirmation_number = submission.confirmation_number
            request.expected_completion = (
                datetime.utcnow() + timedelta(days=broker.processing_days)
            ).date()
        else:
            if submission.requires_followup:
                request.requires_user_action = True
                request.instructions = submission.followup_instructions
            else:
                request.status = "failed"
                request.notes = submission.error

        await db.commit()

        return {
            "request_id": request_id,
            "success": submission.success,
            "method": submission.method,
            "confirmation": submission.confirmation_number,
            "error": submission.error,
        }


@shared_task(bind=True)
def submit_all_user_requests(self, user_id: str):
    """Submit all pending requests for a user."""
    return asyncio.get_event_loop().run_until_complete(
        _submit_all_user_requests_async(user_id)
    )


async def _submit_all_user_requests_async(user_id: str):
    """Async implementation of submitting all user requests."""

    async_session = get_async_session()

    async with async_session() as db:
        # Get all pending requests for user
        result = await db.execute(
            select(RemovalRequest)
            .where(RemovalRequest.user_id == user_id)
            .where(RemovalRequest.status == "pending")
        )
        requests = result.scalars().all()

        if not requests:
            return {"submitted": 0, "message": "No pending requests"}

        # Get user profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return {"error": "User profile not found"}

        manager = RequestManager()
        submitted = 0
        failed = 0

        for request in requests:
            # Get broker
            broker_result = await db.execute(
                select(DataBroker).where(DataBroker.id == request.broker_id)
            )
            broker = broker_result.scalar_one_or_none()

            if not broker:
                continue

            # Get exposure
            exposure = None
            if request.exposure_id:
                exposure_result = await db.execute(
                    select(BrokerExposure).where(BrokerExposure.id == request.exposure_id)
                )
                exposure = exposure_result.scalar_one_or_none()

            # Submit
            submission = await manager.submit_request(request, broker, profile, exposure)

            request.method_used = submission.method
            request.submitted_at = datetime.utcnow()

            if submission.success:
                request.status = "submitted"
                request.confirmation_number = submission.confirmation_number
                request.expected_completion = (
                    datetime.utcnow() + timedelta(days=broker.processing_days)
                ).date()
                submitted += 1
            else:
                if submission.requires_followup:
                    request.requires_user_action = True
                    request.instructions = submission.followup_instructions
                else:
                    request.status = "failed"
                    request.notes = submission.error
                    failed += 1

        await db.commit()

        return {
            "user_id": user_id,
            "submitted": submitted,
            "failed": failed,
            "total": len(requests),
        }
