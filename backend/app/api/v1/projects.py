from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.api.deps import get_current_employee, require_permission
from app.models.project import Project, ProjectMember
from app.models.employee import Employee
from app.models.milestone import Milestone
from app.models.task import Task
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectOut,
    ProjectMemberCreate, ProjectMemberOut
)
from app.services.progress_service import (
    compute_elapsed_time_pct, compute_spi, compute_effort_variance,
    compute_project_health, compute_project_progress
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectOut])
async def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db)
):
    # Enforce multi-tenancy
    conditions = [
        Project.org_id == current_emp.org_id,
        Project.deleted_at.is_(None)
    ]
    if status_filter:
        conditions.append(Project.status == status_filter)

    query = (
        select(Project)
        .options(selectinload(Project.owner))
        .where(and_(*conditions))
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    projects = result.scalars().all()

    out = []
    for p in projects:
        elapsed = compute_elapsed_time_pct(p.start_date, p.target_end_date)
        spi = compute_spi(p.progress_pct, elapsed)
        out.append(
            ProjectOut(
                id=p.id,
                org_id=p.org_id,
                code=p.code,
                name=p.name,
                description=p.description,
                client=p.client,
                owner_id=p.owner_id,
                owner_name=p.owner.full_name if p.owner else "",
                status=p.status,
                priority=p.priority,
                start_date=p.start_date,
                target_end_date=p.target_end_date,
                budget_hours=p.budget_hours,
                budget_cost=p.budget_cost,
                health=p.health,
                progress_pct=p.progress_pct,
                spi=spi,
                created_at=p.created_at
            )
        )
    return out


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    current_emp: Employee = Depends(require_permission("project:create")),
    db: AsyncSession = Depends(get_db)
):
    # Check duplicate code in this org
    existing = await db.execute(
        select(Project).where(
            Project.org_id == current_emp.org_id,
            Project.code == payload.code.upper()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project code already exists in your organization")

    # Verify owner belongs to org
    owner_res = await db.execute(
        select(Employee).where(
            Employee.id == payload.owner_id,
            Employee.org_id == current_emp.org_id
        )
    )
    owner = owner_res.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="Project owner not found in your organization")

    new_proj = Project(
        org_id=current_emp.org_id,
        code=payload.code.upper(),
        name=payload.name,
        description=payload.description,
        client=payload.client,
        owner_id=payload.owner_id,
        status=payload.status,
        priority=payload.priority,
        start_date=payload.start_date,
        target_end_date=payload.target_end_date,
        budget_hours=payload.budget_hours,
        budget_cost=payload.budget_cost,
        health="green",
        progress_pct=0.0,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(new_proj)
    await db.flush()

    ip = request.client.host if request.client else None
    await AuditService.log_mutation(
        session=db,
        org_id=current_emp.org_id,
        actor_employee_id=current_emp.id,
        action="CREATE",
        entity_type="project",
        entity_id=new_proj.id,
        after_json={"code": new_proj.code, "name": new_proj.name},
        ip_address=ip
    )

    return ProjectOut(
        id=new_proj.id,
        org_id=new_proj.org_id,
        code=new_proj.code,
        name=new_proj.name,
        description=new_proj.description,
        client=new_proj.client,
        owner_id=new_proj.owner_id,
        owner_name=owner.full_name,
        status=new_proj.status,
        priority=new_proj.priority,
        start_date=new_proj.start_date,
        target_end_date=new_proj.target_end_date,
        budget_hours=new_proj.budget_hours,
        budget_cost=new_proj.budget_cost,
        health=new_proj.health,
        progress_pct=new_proj.progress_pct,
        spi=1.0,
        created_at=new_proj.created_at
    )


@router.get("/{id}", response_model=ProjectOut)
async def get_project(
    id: str,
    current_emp: Employee = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Project)
        .options(selectinload(Project.owner))
        .where(
            Project.id == id,
            Project.org_id == current_emp.org_id,
            Project.deleted_at.is_(None)
        )
    )
    res = await db.execute(query)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    elapsed = compute_elapsed_time_pct(p.start_date, p.target_end_date)
    spi = compute_spi(p.progress_pct, elapsed)

    return ProjectOut(
        id=p.id,
        org_id=p.org_id,
        code=p.code,
        name=p.name,
        description=p.description,
        client=p.client,
        owner_id=p.owner_id,
        owner_name=p.owner.full_name if p.owner else "",
        status=p.status,
        priority=p.priority,
        start_date=p.start_date,
        target_end_date=p.target_end_date,
        budget_hours=p.budget_hours,
        budget_cost=p.budget_cost,
        health=p.health,
        progress_pct=p.progress_pct,
        spi=spi,
        created_at=p.created_at
    )


@router.post("/{id}/members", response_model=ProjectMemberOut)
async def add_project_member(
    id: str,
    payload: ProjectMemberCreate,
    current_emp: Employee = Depends(require_permission("project:create")),
    db: AsyncSession = Depends(get_db)
):
    # Verify project
    p_res = await db.execute(select(Project).where(Project.id == id, Project.org_id == current_emp.org_id))
    if not p_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify employee
    e_res = await db.execute(select(Employee).where(Employee.id == payload.employee_id, Employee.org_id == current_emp.org_id))
    emp = e_res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    member = ProjectMember(
        org_id=current_emp.org_id,
        project_id=id,
        employee_id=payload.employee_id,
        role_on_project=payload.role_on_project,
        allocation_pct=payload.allocation_pct,
        billable_rate=payload.billable_rate,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(member)
    await db.flush()

    return ProjectMemberOut(
        id=member.id,
        employee_id=member.employee_id,
        employee_name=emp.full_name,
        role_on_project=member.role_on_project,
        allocation_pct=member.allocation_pct,
        billable_rate=member.billable_rate
    )

