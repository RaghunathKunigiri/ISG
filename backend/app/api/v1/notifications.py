from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.api.deps import get_current_employee
from app.models.employee import Employee
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    current_emp: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Notification)
        .where(
            Notification.recipient_id == current_emp.id,
            Notification.org_id == current_emp.org_id
        )
        .order_by(Notification.created_at.desc())
        .limit(30)
    )
    res = await db.execute(query)
    items = res.scalars().all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "payload": n.payload_json,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat()
        }
        for n in items
    ]


@router.put("/{id}/read")
async def mark_notification_read(
    id: str,
    current_emp: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Notification).where(
            Notification.id == id,
            Notification.recipient_id == current_emp.id,
            Notification.org_id == current_emp.org_id
        )
    )
    n = res.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read_at = utc_now()
    return {"message": "Notification marked as read"}

