from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.api.deps import get_current_employee, require_permission
from app.models.timesheet import Timesheet
from app.models.employee import Employee
from app.models.project import Project
from app.models.task import Task
from app.schemas import TimesheetCreate, TimesheetUpdate, TimesheetOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])


@router.get("", response_model=List[TimesheetOut])
async def list_timesheets(
    employee_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_permission("timesheet:read")),
    db: AsyncSession = Depends(get_db)
):
    conditions = [
        Timesheet.org_id == current_emp.org_id,
        Timesheet.deleted_at.is_(None)
    ]

    # Non-managers/non-admins can only read their own timesheets unless timesheet:approve permission
    role_name = current_emp.role.name.lower() if current_emp.role else ""
    if role_name in ("member", "viewer"):
        conditions.append(Timesheet.employee_id == current_emp.id)
    elif employee_id:
        conditions.append(Timesheet.employee_id == employee_id)

    if project_id:
        conditions.append(Timesheet.project_id == project_id)
    if status_filter:
        conditions.append(Timesheet.status == status_filter)
    if start_date:
        conditions.append(Timesheet.work_date >= start_date)
    if end_date:
        conditions.append(Timesheet.work_date <= end_date)

    query = (
        select(Timesheet)
        .options(
            selectinload(Timesheet.employee),
            selectinload(Timesheet.project),
            selectinload(Timesheet.task),
            selectinload(Timesheet.approver)
        )
        .where(and_(*conditions))
        .order_by(Timesheet.work_date.desc(), Timesheet.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(query)
    entries = res.scalars().all()

    return [
        TimesheetOut(
            id=ts.id,
            org_id=ts.org_id,
            employee_id=ts.employee_id,
            employee_name=ts.employee.full_name if ts.employee else "",
            project_id=ts.project_id,
            project_name=ts.project.name if ts.project else "",
            task_id=ts.task_id,
            task_title=ts.task.title if ts.task else None,
            work_date=ts.work_date,
            hours=ts.hours,
            description=ts.description,
            billable=ts.billable,
            status=ts.status,
            approved_by=ts.approved_by,
            approved_by_name=ts.approver.full_name if ts.approver else None,
            approved_at=ts.approved_at,
            created_at=ts.created_at
        )
        for ts in entries
    ]


@router.post("", response_model=TimesheetOut, status_code=status.HTTP_201_CREATED)
async def log_time(
    payload: TimesheetCreate,
    request: Request,
    current_emp: Employee = Depends(require_permission("timesheet:create")),
    db: AsyncSession = Depends(get_db)
):
    if payload.hours <= 0 or payload.hours > 24:
        raise HTTPException(status_code=400, detail="Logged hours must be between 0.1 and 24.0")

    # Verify project
    p_res = await db.execute(select(Project).where(Project.id == payload.project_id, Project.org_id == current_emp.org_id))
    project = p_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    task_title = None
    if payload.task_id:
        t_res = await db.execute(select(Task).where(Task.id == payload.task_id, Task.org_id == current_emp.org_id))
        task = t_res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=400, detail="Invalid task ID")
        task_title = task.title
        # Increment task actual hours
        task.actual_hours += payload.hours

    ts = Timesheet(
        org_id=current_emp.org_id,
        employee_id=current_emp.id,
        project_id=payload.project_id,
        task_id=payload.task_id,
        work_date=payload.work_date,
        hours=payload.hours,
        description=payload.description,
        billable=payload.billable,
        status="draft",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(ts)
    await db.flush()

    return TimesheetOut(
        id=ts.id,
        org_id=ts.org_id,
        employee_id=ts.employee_id,
        employee_name=current_emp.full_name,
        project_id=ts.project_id,
        project_name=project.name,
        task_id=ts.task_id,
        task_title=task_title,
        work_date=ts.work_date,
        hours=ts.hours,
        description=ts.description,
        billable=ts.billable,
        status=ts.status,
        created_at=ts.created_at
    )


@router.post("/{id}/submit")
async def submit_timesheet(
    id: str,
    current_emp: Employee = Depends(require_permission("timesheet:create")),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Timesheet).where(
            Timesheet.id == id,
            Timesheet.org_id == current_emp.org_id,
            Timesheet.employee_id == current_emp.id
        )
    )
    ts = res.scalar_one_or_none()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if ts.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot submit timesheet with status: {ts.status}")

    ts.status = "submitted"
    ts.updated_at = utc_now()
    return {"message": "Timesheet submitted for manager approval", "status": ts.status}


@router.post("/{id}/approve")
async def approve_timesheet(
    id: str,
    request: Request,
    current_emp: Employee = Depends(require_permission("timesheet:approve")),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Timesheet).where(Timesheet.id == id, Timesheet.org_id == current_emp.org_id)
    )
    ts = res.scalar_one_or_none()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if ts.status != "submitted":
        raise HTTPException(status_code=400, detail=f"Cannot approve timesheet with status: {ts.status}")

    ts.status = "approved"
    ts.approved_by = current_emp.id
    ts.approved_at = utc_now()

    ip = request.client.host if request.client else None
    await AuditService.log_mutation(
        session=db,
        org_id=current_emp.org_id,
        actor_employee_id=current_emp.id,
        action="APPROVE",
        entity_type="timesheet",
        entity_id=ts.id,
        after_json={"status": "approved", "hours": ts.hours},
        ip_address=ip
    )

    return {"message": "Timesheet approved successfully", "status": ts.status}


@router.post("/{id}/reject")
async def reject_timesheet(
    id: str,
    reason: Optional[str] = Query(None),
    current_emp: Employee = Depends(require_permission("timesheet:approve")),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Timesheet).where(Timesheet.id == id, Timesheet.org_id == current_emp.org_id)
    )
    ts = res.scalar_one_or_none()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")

    ts.status = "rejected"
    ts.updated_at = utc_now()
    return {"message": "Timesheet rejected", "reason": reason}

