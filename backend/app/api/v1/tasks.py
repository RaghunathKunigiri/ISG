from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.api.deps import get_current_employee, require_permission
from app.models.task import Task
from app.models.task_update import TaskUpdate
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.employee import Employee
from app.schemas import TaskCreate, TaskUpdateIn, TaskOut, TaskProgressNoteIn, TaskUpdateOut
from app.services.progress_service import (
    compute_task_progress, compute_milestone_progress,
    compute_project_progress, compute_elapsed_time_pct,
    compute_spi, compute_effort_variance, compute_project_health
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def recompute_progress_cascade(session: AsyncSession, org_id: str, project_id: str, milestone_id: Optional[str]):
    """Cascading recalculation: Task -> Milestone -> Project -> SPI -> Health."""
    # 1. If milestone exists, recompute milestone progress
    if milestone_id:
        m_tasks_res = await session.execute(
            select(Task).where(
                Task.milestone_id == milestone_id,
                Task.org_id == org_id,
                Task.deleted_at.is_(None)
            )
        )
        m_tasks = m_tasks_res.scalars().all()
        tasks_data = [
            {"story_points": t.story_points, "progress_pct": t.progress_pct}
            for t in m_tasks
        ]
        m_prog = compute_milestone_progress(tasks_data)

        m_res = await session.execute(select(Milestone).where(Milestone.id == milestone_id))
        milestone = m_res.scalar_one_or_none()
        if milestone:
            milestone.progress_pct = m_prog
            if m_prog >= 100.0:
                milestone.status = "completed"
            elif m_prog > 0:
                milestone.status = "in_progress"

    # 2. Recompute project progress
    all_milestones_res = await session.execute(
        select(Milestone).where(
            Milestone.project_id == project_id,
            Milestone.org_id == org_id,
            Milestone.deleted_at.is_(None)
        )
    )
    all_milestones = all_milestones_res.scalars().all()
    if all_milestones:
        m_list = [{"weight": m.weight, "progress_pct": m.progress_pct} for m in all_milestones]
        proj_prog = compute_project_progress(m_list)
    else:
        # Fallback to direct task progress if no milestones
        p_tasks_res = await session.execute(
            select(Task).where(Task.project_id == project_id, Task.org_id == org_id, Task.deleted_at.is_(None))
        )
        p_tasks = p_tasks_res.scalars().all()
        proj_prog = compute_milestone_progress([{"story_points": t.story_points, "progress_pct": t.progress_pct} for t in p_tasks])

    # 3. Load project to update SPI and Health
    p_res = await session.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalar_one_or_none()
    if project:
        project.progress_pct = proj_prog

        # SPI
        elapsed = compute_elapsed_time_pct(project.start_date, project.target_end_date)
        spi = compute_spi(proj_prog, elapsed)

        # Check for blocked tasks > 3 days
        three_days_ago = utc_now() - __import__("datetime").timedelta(days=3)
        blocked_check = await session.execute(
            select(Task).where(
                Task.project_id == project_id,
                Task.status == "blocked",
                Task.blocked_at <= three_days_ago,
                Task.deleted_at.is_(None)
            )
        )
        has_blocked_3d = blocked_check.scalar_one_or_none() is not None

        # Overdue check
        today = date.today()
        is_overdue = (today > project.target_end_date) and (project.progress_pct < 100.0)

        # Auto health
        project.health = compute_project_health(spi, has_blocked_3d, is_overdue)


@router.get("", response_model=List[TaskOut])
async def list_tasks(
    project_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_permission("task:read")),
    db: AsyncSession = Depends(get_db)
):
    # Enforce multi-tenancy
    conditions = [
        Task.org_id == current_emp.org_id,
        Task.deleted_at.is_(None)
    ]
    if project_id:
        conditions.append(Task.project_id == project_id)
    if assignee_id:
        conditions.append(Task.assignee_id == assignee_id)
    if status_filter:
        conditions.append(Task.status == status_filter)

    query = (
        select(Task)
        .options(selectinload(Task.assignee), selectinload(Task.reporter))
        .where(and_(*conditions))
        .order_by(Task.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        TaskOut(
            id=t.id,
            org_id=t.org_id,
            project_id=t.project_id,
            milestone_id=t.milestone_id,
            parent_task_id=t.parent_task_id,
            title=t.title,
            description=t.description,
            assignee_id=t.assignee_id,
            assignee_name=t.assignee.full_name if t.assignee else None,
            reporter_id=t.reporter_id,
            reporter_name=t.reporter.full_name if t.reporter else None,
            status=t.status,
            priority=t.priority,
            story_points=t.story_points,
            estimated_hours=t.estimated_hours,
            actual_hours=t.actual_hours,
            progress_pct=t.progress_pct,
            start_date=t.start_date,
            due_date=t.due_date,
            completed_at=t.completed_at,
            blocked_reason=t.blocked_reason,
            tags=t.tags or [],
            created_at=t.created_at
        )
        for t in tasks
    ]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    request: Request,
    current_emp: Employee = Depends(require_permission("task:create")),
    db: AsyncSession = Depends(get_db)
):
    # Verify project
    p_res = await db.execute(select(Project).where(Project.id == payload.project_id, Project.org_id == current_emp.org_id))
    if not p_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid project ID")

    new_task = Task(
        org_id=current_emp.org_id,
        project_id=payload.project_id,
        milestone_id=payload.milestone_id,
        parent_task_id=payload.parent_task_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        reporter_id=current_emp.id,
        status=payload.status,
        priority=payload.priority,
        story_points=payload.story_points,
        estimated_hours=payload.estimated_hours,
        actual_hours=0.0,
        progress_pct=0.0,
        start_date=payload.start_date,
        due_date=payload.due_date,
        tags=payload.tags,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(new_task)
    await db.flush()

    # Recalculate progress
    await recompute_progress_cascade(db, current_emp.org_id, new_task.project_id, new_task.milestone_id)

    ip = request.client.host if request.client else None
    await AuditService.log_mutation(
        session=db,
        org_id=current_emp.org_id,
        actor_employee_id=current_emp.id,
        action="CREATE",
        entity_type="task",
        entity_id=new_task.id,
        after_json={"title": new_task.title, "status": new_task.status},
        ip_address=ip
    )

    return TaskOut(
        id=new_task.id,
        org_id=new_task.org_id,
        project_id=new_task.project_id,
        milestone_id=new_task.milestone_id,
        parent_task_id=new_task.parent_task_id,
        title=new_task.title,
        description=new_task.description,
        assignee_id=new_task.assignee_id,
        reporter_id=new_task.reporter_id,
        status=new_task.status,
        priority=new_task.priority,
        story_points=new_task.story_points,
        estimated_hours=new_task.estimated_hours,
        actual_hours=new_task.actual_hours,
        progress_pct=new_task.progress_pct,
        start_date=new_task.start_date,
        due_date=new_task.due_date,
        tags=new_task.tags,
        created_at=new_task.created_at
    )


@router.post("/{id}/progress", response_model=TaskUpdateOut)
async def log_task_progress(
    id: str,
    payload: TaskProgressNoteIn,
    current_emp: Employee = Depends(require_permission("task:update")),
    db: AsyncSession = Depends(get_db)
):
    # Fetch task
    t_res = await db.execute(
        select(Task).where(Task.id == id, Task.org_id == current_emp.org_id, Task.deleted_at.is_(None))
    )
    task = t_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task progress & hours
    task.progress_pct = max(0.0, min(100.0, payload.progress_pct))
    task.actual_hours += payload.hours_logged
    if task.progress_pct >= 100.0:
        task.status = "done"
        task.completed_at = utc_now()
    elif task.status == "todo" and task.progress_pct > 0:
        task.status = "in_progress"

    # Append to task_updates
    note = TaskUpdate(
        org_id=current_emp.org_id,
        task_id=task.id,
        employee_id=current_emp.id,
        progress_pct=task.progress_pct,
        comment=payload.comment,
        hours_logged=payload.hours_logged,
        created_at=utc_now()
    )
    db.add(note)
    await db.flush()

    # Cascade progress update
    await recompute_progress_cascade(db, current_emp.org_id, task.project_id, task.milestone_id)

    return TaskUpdateOut(
        id=note.id,
        task_id=note.task_id,
        employee_id=note.employee_id,
        employee_name=current_emp.full_name,
        progress_pct=note.progress_pct,
        comment=note.comment,
        hours_logged=note.hours_logged,
        created_at=note.created_at
    )

