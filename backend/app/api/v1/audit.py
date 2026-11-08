from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_role
from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    conditions = [AuditLog.org_id == current_emp.org_id]
    if action:
        conditions.append(AuditLog.action == action.upper())
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type.lower())

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(query)
    entries = res.scalars().all()

    return [
        AuditLogOut(
            id=entry.id,
            actor_employee_id=entry.actor_employee_id,
            actor_name=entry.actor.full_name if entry.actor else "System",
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            before_json=entry.before_json,
            after_json=entry.after_json,
            ip_address=entry.ip_address,
            created_at=entry.created_at
        )
        for entry in entries
    ]

