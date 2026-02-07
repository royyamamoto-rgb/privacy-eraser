"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "privacy_eraser",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.scan_brokers",
        "app.workers.tasks.submit_requests",
        "app.workers.tasks.monitor_exposure",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time for heavy operations
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
)

# Scheduled tasks (beat schedule)
celery_app.conf.beat_schedule = {
    # Process pending removal requests every 15 minutes
    "process-pending-requests": {
        "task": "app.workers.tasks.submit_requests.process_pending_requests",
        "schedule": crontab(minute="*/15"),
    },
    # Re-scan for exposures daily at 2 AM
    "daily-exposure-scan": {
        "task": "app.workers.tasks.monitor_exposure.scan_all_users",
        "schedule": crontab(hour=2, minute=0),
    },
    # Check for re-listings weekly
    "weekly-relisting-check": {
        "task": "app.workers.tasks.monitor_exposure.check_relistings",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Monday 3 AM
    },
}
