from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, hash_token
from app.core.redis import TokenRevocationService
from app.models.employee import Employee
from app.models.role import Role

security_scheme = HTTPBearer(auto_error=False)


async def get_current_employee(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Employee:
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    token_hash_str = hash_token(token)

    # Check token revocation
    if await TokenRevocationService.is_token_revoked(token_hash_str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    employee_id: str = payload.get("sub")
    org_id: str = payload.get("org_id")

    if not employee_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Scoped to caller's org_id
    query = (
        select(Employee)
        .options(selectinload(Employee.role))
        .where(
            Employee.id == employee_id,
            Employee.org_id == org_id,
            Employee.deleted_at.is_(None),
            Employee.status == "active"
        )
    )
    result = await db.execute(query)
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach verified permissions from JWT payload
    employee._token_permissions = payload.get("permissions", [])
    return employee


def require_permission(permission_code: str) -> Callable:
    """Dependency factory that verifies granular resource:action permission."""
    async def permission_checker(
        current_emp: Employee = Depends(get_current_employee)
    ) -> Employee:
        # Admin role automatically has all permissions
        if current_emp.role and current_emp.role.name.lower() == "admin":
            return current_emp

        user_perms = getattr(current_emp, "_token_permissions", None)
        if user_perms is None:
            user_perms = [p.code for p in current_emp.role.permissions] if current_emp.role else []

        if permission_code not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required permission: {permission_code}"
            )
        return current_emp

    return permission_checker


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory checking employee's role."""
    async def role_checker(
        current_emp: Employee = Depends(get_current_employee)
    ) -> Employee:
        role_name = current_emp.role.name.lower() if current_emp.role else ""
        if role_name not in [r.lower() for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role: {role_name}. Allowed: {allowed_roles}"
            )
        return current_emp

    return role_checker
