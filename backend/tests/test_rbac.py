import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, create_access_token
from app.models import Organization, Role, Permission, Employee


@pytest.mark.asyncio
async def test_rbac_permission_enforcement(client: AsyncClient, db_session: AsyncSession):
    # Setup Org
    org = Organization(name="RBAC Org", domain="rbac.com")
    db_session.add(org)
    await db_session.flush()

    # Permissions
    p_create = Permission(code="project:create", description="Create project")
    p_read = Permission(code="project:read", description="Read project")
    db_session.add_all([p_create, p_read])
    await db_session.flush()

    # Roles: Manager has create & read; Viewer has read only
    r_mgr = Role(org_id=org.id, name="manager", permissions=[p_create, p_read])
    r_viewer = Role(org_id=org.id, name="viewer", permissions=[p_read])
    db_session.add_all([r_mgr, r_viewer])
    await db_session.flush()

    # Employees
    pw = hash_password("Pass123!")
    mgr = Employee(
        org_id=org.id, employee_code="M01", full_name="Manager Mike",
        email="mike@rbac.com", role_id=r_mgr.id, department="Ops",
        designation="Manager", date_of_joining=date(2024, 1, 1),
        status="active", password_hash=pw
    )
    viewer = Employee(
        org_id=org.id, employee_code="V01", full_name="Viewer Val",
        email="val@rbac.com", role_id=r_viewer.id, department="Ops",
        designation="Viewer", date_of_joining=date(2024, 1, 1),
        status="active", password_hash=pw
    )
    db_session.add_all([mgr, viewer])
    await db_session.commit()

    token_mgr = create_access_token(mgr.id, org.id, "manager", ["project:create", "project:read"])
    token_viewer = create_access_token(viewer.id, org.id, "viewer", ["project:read"])

    # 1. Viewer tries to create project -> MUST BE FORBIDDEN (403)
    proj_payload = {
        "code": "PRJ-99",
        "name": "Unauthorized Project",
        "owner_id": viewer.id,
        "status": "planned",
        "priority": "low",
        "start_date": "2024-01-01",
        "target_end_date": "2024-06-30"
    }
    res_forbidden = await client.post(
        "/api/v1/projects",
        json=proj_payload,
        headers={"Authorization": f"Bearer {token_viewer}"}
    )
    assert res_forbidden.status_code == 403
    assert "Operation not permitted" in res_forbidden.json()["detail"]

    # 2. Manager creates project -> MUST SUCCEED (201)
    proj_payload["owner_id"] = mgr.id
    res_success = await client.post(
        "/api/v1/projects",
        json=proj_payload,
        headers={"Authorization": f"Bearer {token_mgr}"}
    )
    assert res_success.status_code == 201
    assert res_success.json()["code"] == "PRJ-99"
