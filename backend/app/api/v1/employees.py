from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utc_now
from app.core.security import hash_password
from app.api.deps import get_current_employee, require_permission
from app.models.employee import Employee
from app.models.role import Role
from app.schemas import EmployeeCreate, EmployeeUpdate, EmployeeOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[EmployeeOut])
async def list_employees(
    department: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_emp: Employee = Depends(require_permission("employee:read")),
    db: AsyncSession = Depends(get_db)
):
    # Enforce multi-tenancy: caller's org_id
    conditions = [
        Employee.org_id == current_emp.org_id,
        Employee.deleted_at.is_(None)
    ]
    if department:
        conditions.append(Employee.department == department)
    if status_filter:
        conditions.append(Employee.status == status_filter)

    query = (
        select(Employee)
        .options(selectinload(Employee.role))
        .where(and_(*conditions))
        .order_by(Employee.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    employees = result.scalars().all()

    return [
        EmployeeOut(
            id=e.id,
            org_id=e.org_id,
            employee_code=e.employee_code,
            full_name=e.full_name,
            email=e.email,
            phone=e.phone,
            role_id=e.role_id,
            role_name=e.role.name if e.role else "",
            manager_id=e.manager_id,
            department=e.department,
            designation=e.designation,
            location=e.location,
            shift=e.shift,
            date_of_joining=e.date_of_joining,
            status=e.status,
            avatar_url=e.avatar_url,
            created_at=e.created_at
        )
        for e in employees
    ]


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    request: Request,
    current_emp: Employee = Depends(require_permission("employee:create")),
    db: AsyncSession = Depends(get_db)
):
    # Check duplicate email in this org
    existing = await db.execute(
        select(Employee).where(
            Employee.org_id == current_emp.org_id,
            Employee.email == payload.email.lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee with this email already exists in your organization")

    # Verify role belongs to system or org
    role_res = await db.execute(select(Role).where(Role.id == payload.role_id))
    role_obj = role_res.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(status_code=400, detail="Invalid role ID")

    new_emp = Employee(
        org_id=current_emp.org_id,
        employee_code=payload.employee_code,
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        role_id=payload.role_id,
        manager_id=payload.manager_id,
        department=payload.department,
        designation=payload.designation,
        location=payload.location,
        shift=payload.shift,
        date_of_joining=payload.date_of_joining,
        status=payload.status,
        password_hash=hash_password(payload.password),
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(new_emp)
    await db.flush()

    ip = request.client.host if request.client else None
    await AuditService.log_mutation(
        session=db,
        org_id=current_emp.org_id,
        actor_employee_id=current_emp.id,
        action="CREATE",
        entity_type="employee",
        entity_id=new_emp.id,
        after_json={"email": new_emp.email, "role": role_obj.name},
        ip_address=ip
    )

    return EmployeeOut(
        id=new_emp.id,
        org_id=new_emp.org_id,
        employee_code=new_emp.employee_code,
        full_name=new_emp.full_name,
        email=new_emp.email,
        phone=new_emp.phone,
        role_id=new_emp.role_id,
        role_name=role_obj.name,
        manager_id=new_emp.manager_id,
        department=new_emp.department,
        designation=new_emp.designation,
        location=new_emp.location,
        shift=new_emp.shift,
        date_of_joining=new_emp.date_of_joining,
        status=new_emp.status,
        avatar_url=new_emp.avatar_url,
        created_at=new_emp.created_at
    )


@router.get("/{id}", response_model=EmployeeOut)
async def get_employee(
    id: str,
    current_emp: Employee = Depends(require_permission("employee:read")),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Employee)
        .options(selectinload(Employee.role))
        .where(
            Employee.id == id,
            Employee.org_id == current_emp.org_id,
            Employee.deleted_at.is_(None)
        )
    )
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return EmployeeOut(
        id=emp.id,
        org_id=emp.org_id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        email=emp.email,
        phone=emp.phone,
        role_id=emp.role_id,
        role_name=emp.role.name if emp.role else "",
        manager_id=emp.manager_id,
        department=emp.department,
        designation=emp.designation,
        location=emp.location,
        shift=emp.shift,
        date_of_joining=emp.date_of_joining,
        status=emp.status,
        avatar_url=emp.avatar_url,
        created_at=emp.created_at
    )


@router.delete("/{id}")
async def delete_employee(
    id: str,
    request: Request,
    current_emp: Employee = Depends(require_permission("employee:delete")),
    db: AsyncSession = Depends(get_db)
):
    # Soft delete (deleted_at)
    res = await db.execute(
        select(Employee).where(
            Employee.id == id,
            Employee.org_id == current_emp.org_id,
            Employee.deleted_at.is_(None)
        )
    )
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.deleted_at = utc_now()
    emp.status = "inactive"

    ip = request.client.host if request.client else None
    await AuditService.log_mutation(
        session=db,
        org_id=current_emp.org_id,
        actor_employee_id=current_emp.id,
        action="DELETE",
        entity_type="employee",
        entity_id=emp.id,
        before_json={"email": emp.email, "status": "active"},
        after_json={"status": "inactive", "deleted": True},
        ip_address=ip
    )

    return {"message": "Employee soft-deleted successfully"}

