import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, create_access_token
from app.models import Organization, Role, Employee, Project, Task


@pytest.mark.asyncio
async def test_cross_tenant_access_is_impossible(client: AsyncClient, db_session: AsyncSession):
    """
    Test proving cross-tenant access is impossible:
    - User in Org A (Alpha Corp) attempts to read/modify projects or tasks in Org B (Beta Corp).
    - Query scoping to caller's org_id ensures Org A user receives 404 or empty list.
    """
    # 1. Create Organization A
    org_a = Organization(name="Alpha Corp", domain="alpha.com")
    db_session.add(org_a)
    await db_session.flush()

    role_a = Role(org_id=org_a.id, name="admin")
    db_session.add(role_a)
    await db_session.flush()

    emp_a = Employee(
        org_id=org_a.id,
        employee_code="A001",
        full_name="Alice Alpha",
        email="alice@alpha.com",
        role_id=role_a.id,
        department="Engineering",
        designation="Lead",
        date_of_joining=date(2024, 1, 1),
        status="active",
        password_hash=hash_password("Pass123!")
    )
    db_session.add(emp_a)
    await db_session.flush()

    proj_a = Project(
        org_id=org_a.id,
        code="ALP-01",
        name="Alpha Confidential Project",
        owner_id=emp_a.id,
        status="active",
        priority="high",
        start_date=date(2024, 1, 1),
        target_end_date=date(2024, 12, 31)
    )
    db_session.add(proj_a)

    # 2. Create Organization B
    org_b = Organization(name="Beta Corp", domain="beta.com")
    db_session.add(org_b)
    await db_session.flush()

    role_b = Role(org_id=org_b.id, name="admin")
    db_session.add(role_b)
    await db_session.flush()

    emp_b = Employee(
        org_id=org_b.id,
        employee_code="B001",
        full_name="Bob Beta",
        email="bob@beta.com",
        role_id=role_b.id,
        department="Marketing",
        designation="Manager",
        date_of_joining=date(2024, 1, 1),
        status="active",
        password_hash=hash_password("Pass123!")
    )
    db_session.add(emp_b)
    await db_session.flush()

    proj_b = Project(
        org_id=org_b.id,
        code="BET-01",
        name="Beta Secret Project",
        owner_id=emp_b.id,
        status="active",
        priority="critical",
        start_date=date(2024, 2, 1),
        target_end_date=date(2024, 11, 30)
    )
    db_session.add(proj_b)
    await db_session.commit()

    # 3. Generate tokens
    token_a = create_access_token(subject=emp_a.id, org_id=org_a.id, role="admin", permissions=[])
    token_b = create_access_token(subject=emp_b.id, org_id=org_b.id, role="admin", permissions=[])

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 4. User A lists projects -> MUST ONLY SEE Project A
    res_list_a = await client.get("/api/v1/projects", headers=headers_a)
    assert res_list_a.status_code == 200
    projects_a = res_list_a.json()
    assert len(projects_a) == 1
    assert projects_a[0]["code"] == "ALP-01"
    assert projects_a[0]["id"] == proj_a.id

    # 5. User A tries to directly fetch Project B by its ID -> MUST RETURN 404 NOT FOUND
    res_get_b = await client.get(f"/api/v1/projects/{proj_b.id}", headers=headers_a)
    assert res_get_b.status_code == 404
    assert res_get_b.json()["detail"] == "Project not found"

    # 6. User B tries to directly fetch Project A by its ID -> MUST RETURN 404 NOT FOUND
    res_get_a = await client.get(f"/api/v1/projects/{proj_a.id}", headers=headers_b)
    assert res_get_a.status_code == 404
    assert res_get_a.json()["detail"] == "Project not found"

