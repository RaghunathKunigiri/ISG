from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_permission, get_current_employee
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.schemas import AttendanceOut

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("", response_model=List[AttendanceOut])
async def list_attendance(
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_permission("report:read")),
    db: AsyncSession = Depends(get_db)
):
    conditions = [Attendance.org_id == current_emp.org_id]
    if employee_id:
        conditions.append(Attendance.employee_id == employee_id)
    if start_date:
        conditions.append(Attendance.work_date >= start_date)
    if end_date:
        conditions.append(Attendance.work_date <= end_date)

    query = (
        select(Attendance)
        .options(selectinload(Attendance.employee))
        .where(and_(*conditions))
        .order_by(Attendance.work_date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        AttendanceOut(
            id=a.id,
            employee_id=a.employee_id,
            employee_name=a.employee.full_name if a.employee else "",
            work_date=a.work_date,
            first_login_at=a.first_login_at,
            last_logout_at=a.last_logout_at,
            total_active_minutes=a.total_active_minutes,
            session_count=a.session_count,
            status=a.status,
            is_late=a.is_late
        )
        for a in records
    ]

