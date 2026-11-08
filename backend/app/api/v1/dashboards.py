from typing import Dict, Any, List
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.api.deps import get_current_employee, require_permission, require_role
from app.models.employee import Employee
from app.models.project import Project, ProjectMember
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.timesheet import Timesheet
from app.models.login_session import LoginSession
from app.models.login_attempt import LoginAttempt
from app.models.attendance import Attendance
from app.models.project_snapshot import ProjectProgressSnapshot
from app.models.task_update import TaskUpdate
from app.schemas import MemberDashboardOut, ManagerDashboardOut, AdminDashboardOut, TaskOut
from app.services.progress_service import compute_elapsed_time_pct, compute_spi

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


@router.get("/member", response_model=MemberDashboardOut)
async def get_member_dashboard(
    current_emp: Employee = Depends(get_current_employee),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()
    # 1. My tasks by status
    status_counts_res = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(
            Task.org_id == current_emp.org_id,
            Task.assignee_id == current_emp.id,
            Task.deleted_at.is_(None)
        )
        .group_by(Task.status)
    )
    my_tasks_by_status = {row[0]: row[1] for row in status_counts_res.all()}

    # 2. My hours this week
    start_of_week = today - timedelta(days=today.weekday())
    hours_res = await db.execute(
        select(func.coalesce(func.sum(Timesheet.hours), 0.0))
        .where(
            Timesheet.org_id == current_emp.org_id,
            Timesheet.employee_id == current_emp.id,
            Timesheet.work_date >= start_of_week,
            Timesheet.deleted_at.is_(None)
        )
    )
    hours_this_week = float(hours_res.scalar() or 0.0)

    # 3. Overdue task IDs
    overdue_res = await db.execute(
        select(Task.id)
        .where(
            Task.org_id == current_emp.org_id,
            Task.assignee_id == current_emp.id,
            Task.due_date < today,
            Task.status != "done",
            Task.deleted_at.is_(None)
        )
    )
    overdue_task_ids = [str(r[0]) for r in overdue_res.all()]

    # 4. Recent tasks
    recent_tasks_res = await db.execute(
        select(Task)
        .where(
            Task.org_id == current_emp.org_id,
            Task.assignee_id == current_emp.id,
            Task.deleted_at.is_(None)
        )
        .order_by(Task.updated_at.desc())
        .limit(10)
    )
    recent_tasks = [
        TaskOut(
            id=t.id,
            org_id=t.org_id,
            project_id=t.project_id,
            milestone_id=t.milestone_id,
            parent_task_id=t.parent_task_id,
            title=t.title,
            description=t.description,
            assignee_id=t.assignee_id,
            assignee_name=current_emp.full_name,
            reporter_id=t.reporter_id,
            status=t.status,
            priority=t.priority,
            story_points=t.story_points,
            estimated_hours=t.estimated_hours,
            actual_hours=t.actual_hours,
            progress_pct=t.progress_pct,
            start_date=t.start_date,
            due_date=t.due_date,
            tags=t.tags or [],
            created_at=t.created_at
        )
        for t in recent_tasks_res.scalars().all()
    ]

    return MemberDashboardOut(
        my_tasks_by_status=my_tasks_by_status,
        my_hours_this_week=round(hours_this_week, 1),
        overdue_task_ids=overdue_task_ids,
        recent_tasks=recent_tasks
    )


@router.get("/manager", response_model=ManagerDashboardOut)
async def get_manager_dashboard(
    current_emp: Employee = Depends(require_role(["admin", "manager", "team_lead"])),
    db: AsyncSession = Depends(get_db)
):
    # 1. Team size
    team_size_res = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.org_id == current_emp.org_id,
            Employee.status == "active",
            Employee.deleted_at.is_(None)
        )
    )
    team_size = int(team_size_res.scalar() or 0)

    # 2. Blocked tasks
    blocked_tasks_res = await db.execute(
        select(Task)
        .options(selectinload(Task.assignee))
        .where(
            Task.org_id == current_emp.org_id,
            Task.status == "blocked",
            Task.deleted_at.is_(None)
        )
        .order_by(Task.created_at.desc())
    )
    blocked_tasks_objs = blocked_tasks_res.scalars().all()
    blocked_count = len(blocked_tasks_objs)

    blocked_tasks = [
        TaskOut(
            id=t.id,
            org_id=t.org_id,
            project_id=t.project_id,
            milestone_id=t.milestone_id,
            title=t.title,
            description=t.description,
            assignee_id=t.assignee_id,
            assignee_name=t.assignee.full_name if t.assignee else "Unassigned",
            reporter_id=t.reporter_id,
            status=t.status,
            priority=t.priority,
            story_points=t.story_points,
            estimated_hours=t.estimated_hours,
            actual_hours=t.actual_hours,
            progress_pct=t.progress_pct,
            start_date=t.start_date,
            due_date=t.due_date,
            blocked_reason=t.blocked_reason,
            tags=t.tags or [],
            created_at=t.created_at
        )
        for t in blocked_tasks_objs[:10]
    ]

    # 3. Timesheet approval queue count
    queue_res = await db.execute(
        select(func.count(Timesheet.id)).where(
            Timesheet.org_id == current_emp.org_id,
            Timesheet.status == "submitted",
            Timesheet.deleted_at.is_(None)
        )
    )
    timesheet_approval_queue = int(queue_res.scalar() or 0)

    # 4. Team progress table
    projects_res = await db.execute(
        select(Project).where(
            Project.org_id == current_emp.org_id,
            Project.status != "cancelled",
            Project.deleted_at.is_(None)
        )
    )
    team_progress = [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "progress_pct": p.progress_pct,
            "health": p.health,
            "status": p.status
        }
        for p in projects_res.scalars().all()
    ]

    # 5. Capacity vs Allocation heatmap (weekly employee capacity vs logged hours)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    emp_hours_res = await db.execute(
        select(Employee.full_name, func.coalesce(func.sum(Timesheet.hours), 0.0))
        .join(Timesheet, and_(Timesheet.employee_id == Employee.id, Timesheet.work_date >= start_of_week), isouter=True)
        .where(
            Employee.org_id == current_emp.org_id,
            Employee.status == "active",
            Employee.deleted_at.is_(None)
        )
        .group_by(Employee.id, Employee.full_name)
    )
    capacity_heatmap = [
        {
            "employee_name": row[0],
            "logged_hours": round(float(row[1]), 1),
            "capacity_hours": 40.0,
            "utilization_pct": round((float(row[1]) / 40.0) * 100.0, 1)
        }
        for row in emp_hours_res.all()
    ]

    return ManagerDashboardOut(
        team_size=team_size,
        blocked_count=blocked_count,
        timesheet_approval_queue=timesheet_approval_queue,
        team_progress=team_progress,
        blocked_tasks=blocked_tasks,
        capacity_heatmap=capacity_heatmap
    )


@router.get("/admin", response_model=AdminDashboardOut)
async def get_admin_dashboard(
    current_emp: Employee = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    # 1. Project count & Employee count
    p_count = (await db.execute(select(func.count(Project.id)).where(Project.org_id == current_emp.org_id, Project.deleted_at.is_(None)))).scalar() or 0
    e_count = (await db.execute(select(func.count(Employee.id)).where(Employee.org_id == current_emp.org_id, Employee.deleted_at.is_(None)))).scalar() or 0

    # 2. Active sessions
    sess_count = (await db.execute(select(func.count(LoginSession.id)).where(LoginSession.org_id == current_emp.org_id, LoginSession.is_active == True))).scalar() or 0

    # 3. Org-wide project health grid
    proj_res = await db.execute(
        select(Project).where(Project.org_id == current_emp.org_id, Project.deleted_at.is_(None)).order_by(Project.created_at.desc())
    )
    project_health_grid = [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "client": p.client,
            "health": p.health,
            "progress_pct": p.progress_pct,
            "status": p.status,
            "budget_hours": p.budget_hours
        }
        for p in proj_res.scalars().all()
    ]

    # 4. Recent login attempts
    att_res = await db.execute(
        select(LoginAttempt)
        .where(LoginAttempt.org_id == current_emp.org_id)
        .order_by(LoginAttempt.attempted_at.desc())
        .limit(10)
    )
    recent_login_attempts = [
        {
            "email": a.email_attempted,
            "success": a.success,
            "failure_reason": a.failure_reason,
            "ip": a.ip_address,
            "device": a.device_type,
            "time": a.attempted_at.isoformat()
        }
        for a in att_res.scalars().all()
    ]

    return AdminDashboardOut(
        project_count=int(p_count),
        employee_count=int(e_count),
        active_sessions_count=int(sess_count),
        project_health_grid=project_health_grid,
        recent_login_attempts=recent_login_attempts
    )


@router.get("/project/{id}")
async def get_project_dashboard_view(
    id: str,
    current_emp: Employee = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db)
):
    """
    Project View: Gantt data, burndown trend, milestone timeline, effort vs estimate, activity feed.
    """
    # 1. Project details
    p_res = await db.execute(
        select(Project)
        .options(selectinload(Project.owner))
        .where(Project.id == id, Project.org_id == current_emp.org_id, Project.deleted_at.is_(None))
    )
    project = p_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Milestones timeline
    m_res = await db.execute(
        select(Milestone)
        .where(Milestone.project_id == id, Milestone.org_id == current_emp.org_id, Milestone.deleted_at.is_(None))
        .order_by(Milestone.due_date.asc())
    )
    milestones = [
        {
            "id": m.id,
            "name": m.name,
            "due_date": str(m.due_date),
            "status": m.status,
            "weight": m.weight,
            "progress_pct": m.progress_pct
        }
        for m in m_res.scalars().all()
    ]

    # 3. Gantt Tasks
    t_res = await db.execute(
        select(Task)
        .options(selectinload(Task.assignee))
        .where(Task.project_id == id, Task.org_id == current_emp.org_id, Task.deleted_at.is_(None))
        .order_by(Task.due_date.asc())
        .limit(100)
    )
    gantt_tasks = [
        {
            "id": t.id,
            "title": t.title,
            "start": str(t.start_date or project.start_date),
            "end": str(t.due_date or project.target_end_date),
            "progress": t.progress_pct,
            "status": t.status,
            "assignee": t.assignee.full_name if t.assignee else "Unassigned"
        }
        for t in t_res.scalars().all()
    ]

    # 4. Burndown & Trend snapshots
    snap_res = await db.execute(
        select(ProjectProgressSnapshot)
        .where(ProjectProgressSnapshot.project_id == id, ProjectProgressSnapshot.org_id == current_emp.org_id)
        .order_by(ProjectProgressSnapshot.snapshot_date.asc())
    )
    burndown_data = [
        {
            "date": str(s.snapshot_date),
            "progress_pct": s.progress_pct,
            "spi": s.spi,
            "actual_hours": s.actual_hours,
            "remaining_story_points": s.remaining_story_points,
            "health": s.health
        }
        for s in snap_res.scalars().all()
    ]

    # 5. Effort vs Estimate
    effort_res = await db.execute(
        select(
            func.coalesce(func.sum(Task.estimated_hours), 0.0),
            func.coalesce(func.sum(Task.actual_hours), 0.0)
        )
        .where(Task.project_id == id, Task.org_id == current_emp.org_id, Task.deleted_at.is_(None))
    )
    est_hours, act_hours = effort_res.one()

    # 6. Activity Feed (task_updates)
    act_res = await db.execute(
        select(TaskUpdate)
        .options(selectinload(TaskUpdate.employee), selectinload(TaskUpdate.task))
        .join(Task, Task.id == TaskUpdate.task_id)
        .where(Task.project_id == id, TaskUpdate.org_id == current_emp.org_id)
        .order_by(TaskUpdate.created_at.desc())
        .limit(15)
    )
    activity_feed = [
        {
            "id": a.id,
            "employee_name": a.employee.full_name if a.employee else "Unknown",
            "task_title": a.task.title if a.task else "",
            "comment": a.comment,
            "progress_pct": a.progress_pct,
            "hours_logged": a.hours_logged,
            "timestamp": a.created_at.isoformat()
        }
        for a in act_res.scalars().all()
    ]

    elapsed = compute_elapsed_time_pct(project.start_date, project.target_end_date)
    spi = compute_spi(project.progress_pct, elapsed)

    return {
        "project": {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "client": project.client,
            "health": project.health,
            "progress_pct": project.progress_pct,
            "spi": spi,
            "budget_hours": project.budget_hours,
            "budget_cost": project.budget_cost,
            "start_date": str(project.start_date),
            "target_end_date": str(project.target_end_date),
            "actual_hours": round(float(act_hours), 1),
            "estimated_hours": round(float(est_hours), 1)
        },
        "milestones": milestones,
        "gantt_tasks": gantt_tasks,
        "burndown": burndown_data,
        "effort": {
            "budget_hours": project.budget_hours,
            "estimated_hours": round(float(est_hours), 1),
            "actual_hours": round(float(act_hours), 1),
            "variance": round((float(act_hours) - float(est_hours)) / (float(est_hours) or 1.0), 2)
        },
        "activity_feed": activity_feed
    }

