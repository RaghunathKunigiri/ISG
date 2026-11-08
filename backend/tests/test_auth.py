import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, generate_mfa_secret, verify_totp
from app.models import Organization, Role, Employee
import pyotp


@pytest.mark.asyncio
async def test_argon2id_hashing():
    raw = "SecurePassword123!"
    hashed = hash_password(raw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_totp_mfa_flow():
    secret = generate_mfa_secret()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    assert verify_totp(secret, valid_code) is True
    assert verify_totp(secret, "000000") is False


@pytest.mark.asyncio
async def test_auth_login_and_refresh_flow(client: AsyncClient, db_session: AsyncSession):
    # Setup test Org, Role, Employee
    org = Organization(name="Test Org", domain="test.com")
    db_session.add(org)
    await db_session.flush()

    role = Role(org_id=org.id, name="member")
    db_session.add(role)
    await db_session.flush()

    emp = Employee(
        org_id=org.id,
        employee_code="E001",
        full_name="John Doe",
        email="john@test.com",
        role_id=role.id,
        department="Engineering",
        designation="Software Engineer",
        date_of_joining=date(2024, 1, 1),
        status="active",
        password_hash=hash_password("MyPassword123!")
    )
    db_session.add(emp)
    await db_session.commit()

    # 1. Login with bad password
    bad_login = await client.post("/api/v1/auth/login", json={"email": "john@test.com", "password": "wrong"})
    assert bad_login.status_code == 401

    # 2. Login with correct password
    login_res = await client.post("/api/v1/auth/login", json={"email": "john@test.com", "password": "MyPassword123!"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "member"
    assert data["employee_name"] == "John Doe"

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 3. Access protected /me endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "john@test.com"

    # 4. Refresh token
    ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert new_tokens["access_token"] != access_token
    assert new_tokens["refresh_token"] != refresh_token

