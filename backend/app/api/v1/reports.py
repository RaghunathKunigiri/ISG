import csv
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_permission
from app.models.employee import Employee
from app.models.project import Project
from app.models.timesheet import Timesheet
from app.models.attendance import Attendance

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/projects.csv")
async def export_projects_csv(
    current_emp: Employee = Depends(require_permission("report:read")),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Project)
        .options(selectinload(Project.owner))
        .where(Project.org_id == current_emp.org_id, Project.deleted_at.is_(None))
        .order_by(Project.code.asc())
    )
    res = await db.execute(query)
    projects = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Code", "Name", "Client", "Owner", "Status", "Priority", "Health", "Progress %", "Budget Hours", "Budget Cost"])

    for p in projects:
        writer.writerow([
            p.code, p.name, p.client or "", p.owner.full_name if p.owner else "",
            p.status, p.priority, p.health, p.progress_pct, p.budget_hours, p.budget_cost
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=project_status_report.csv"}
    )


@router.get("/timesheets.csv")
async def export_timesheets_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_emp: Employee = Depends(require_permission("report:read")),
    db: AsyncSession = Depends(get_db)
):
    conditions = [Timesheet.org_id == current_emp.org_id, Timesheet.deleted_at.is_(None)]
    if start_date:
        conditions.append(Timesheet.work_date >= start_date)
    if end_date:
        conditions.append(Timesheet.work_date <= end_date)

    query = (
        select(Timesheet)
        .options(selectinload(Timesheet.employee), selectinload(Timesheet.project), selectinload(Timesheet.task))
        .where(and_(*conditions))
        .order_by(Timesheet.work_date.desc())
    )
    res = await db.execute(query)
    entries = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Work Date", "Employee", "Employee Code", "Project", "Task", "Hours", "Billable", "Status", "Description"])

    for ts in entries:
        writer.writerow([
            str(ts.work_date),
            ts.employee.full_name if ts.employee else "",
            ts.employee.employee_code if ts.employee else "",
            ts.project.name if ts.project else "",
            ts.task.title if ts.task else "",
            ts.hours,
            "Yes" if ts.billable else "No",
            ts.status,
            ts.description
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=timesheet_report.csv"}
    )


@router.get("/attendance.csv")
async def export_attendance_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_emp: Employee = Depends(require_permission("report:read")),
    db: AsyncSession = Depends(get_db)
):
    conditions = [Attendance.org_id == current_emp.org_id]
    if start_date:
        conditions.append(Attendance.work_date >= start_date)
    if end_date:
        conditions.append(Attendance.work_date <= end_date)

    query = (
        select(Attendance)
        .options(selectinload(Attendance.employee))
        .where(and_(*conditions))
        .order_by(Attendance.work_date.desc())
    )
    res = await db.execute(query)
    entries = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Employee", "Code", "Department", "First Login", "Last Logout", "Active Minutes", "Status", "Late"])

    for a in entries:
        writer.writerow([
            str(a.work_date),
            a.employee.full_name if a.employee else "",
            a.employee.employee_code if a.employee else "",
            a.employee.department if a.employee else "",
            a.first_login_at.isoformat() if a.first_login_at else "",
            a.last_logout_at.isoformat() if a.last_logout_at else "",
            a.total_active_minutes,
            a.status,
            "Yes" if a.is_late else "No"
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_report.csv"}
    )

