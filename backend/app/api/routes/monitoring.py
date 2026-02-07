"""Monitoring routes - alerts and privacy monitoring."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DbSession
from app.models.alert import Alert

router = APIRouter()


# Schemas
class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    description: str | None
    source_url: str | None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    total: int
    unread: int
    critical: int
    high: int


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
    limit: int = 50,
):
    """List alerts for current user."""
    query = select(Alert).where(Alert.user_id == current_user.id)

    if unread_only:
        query = query.where(Alert.is_read == False)

    query = query.order_by(Alert.created_at.desc()).limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=str(a.id),
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            description=a.description,
            source_url=a.source_url,
            is_read=a.is_read,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.get("/alerts/stats", response_model=AlertStats)
async def get_alert_stats(current_user: CurrentUser, db: DbSession):
    """Get alert statistics."""
    result = await db.execute(
        select(Alert).where(Alert.user_id == current_user.id)
    )
    alerts = result.scalars().all()

    return AlertStats(
        total=len(alerts),
        unread=sum(1 for a in alerts if not a.is_read),
        critical=sum(1 for a in alerts if a.severity == "critical" and not a.is_read),
        high=sum(1 for a in alerts if a.severity == "high" and not a.is_read),
    )


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark an alert as read."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    alert.read_at = datetime.utcnow()
    await db.commit()

    return {"status": "read"}


@router.post("/alerts/read-all")
async def mark_all_alerts_read(current_user: CurrentUser, db: DbSession):
    """Mark all alerts as read."""
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == current_user.id)
        .where(Alert.is_read == False)
    )
    alerts = result.scalars().all()

    for alert in alerts:
        alert.is_read = True
        alert.read_at = datetime.utcnow()

    await db.commit()

    return {"status": "all_read", "count": len(alerts)}


@router.delete("/alerts/{alert_id}")
async def dismiss_alert(
    alert_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Dismiss an alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_dismissed = True
    await db.commit()

    return {"status": "dismissed"}
