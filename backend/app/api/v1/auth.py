from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from user_agents import parse

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, hash_token, generate_mfa_secret, get_totp_uri, verify_totp
)
from app.core.redis import LockoutService, TokenRevocationService
from app.core.rate_limiter import login_rate_limiter
from app.models.employee import Employee
from app.models.role import Role
from app.models.login_session import LoginSession
from app.models.login_attempt import LoginAttempt
from app.models.audit_log import AuditLog
from app.schemas import LoginIn, RefreshIn, TokenOut, MFASetupOut, MFAVerifyIn, EmployeeOut
from app.api.deps import get_current_employee

router = APIRouter(prefix="/auth", tags=["Authentication"])


def parse_telemetry(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    ua_str = request.headers.get("user-agent", "")
    ua = parse(ua_str)
    device_type = "Mobile" if ua.is_mobile else ("Tablet" if ua.is_tablet else "Desktop")
    os_name = ua.os.family
    browser_name = ua.browser.family
    return ip, ua_str, device_type, os_name, browser_name


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_rate_limiter)])
async def login(payload: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    ip, ua_str, device_type, os_name, browser_name = parse_telemetry(request)
    email_clean = payload.email.strip().lower()

    # 1. Check account lockout policy (5 fails in 15 min -> 30 min lock)
    if await LockoutService.is_locked(email_clean):
        # Record attempt
        attempt = LoginAttempt(
            email_attempted=email_clean,
            success=False,
            failure_reason="locked",
            ip_address=ip,
            user_agent=ua_str,
            device_type=device_type,
            os=os_name,
            browser=browser_name,
            attempted_at=utc_now()
        )
        db.add(attempt)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to consecutive failed attempts. Please try again after {settings.LOCKOUT_DURATION_MINUTES} minutes."
        )

    # 2. Query employee with role and permissions
    stmt = (
        select(Employee)
        .options(selectinload(Employee.role).selectinload(Role.permissions))
        .where(
            Employee.email == email_clean,
            Employee.deleted_at.is_(None)
        )
    )
    result = await db.execute(stmt)
    emp = result.scalar_one_or_none()

    if not emp or emp.status != "active":
        await LockoutService.record_failed_attempt(email_clean)
        attempt = LoginAttempt(
            email_attempted=email_clean,
            success=False,
            failure_reason="unknown_user" if not emp else "inactive_user",
            ip_address=ip,
            user_agent=ua_str,
            device_type=device_type,
            os=os_name,
            browser=browser_name,
            attempted_at=utc_now()
        )
        db.add(attempt)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Verify Argon2id password hash
    if not verify_password(payload.password, emp.password_hash):
        fails = await LockoutService.record_failed_attempt(email_clean)
        attempt = LoginAttempt(
            org_id=emp.org_id,
            email_attempted=email_clean,
            employee_id=emp.id,
            success=False,
            failure_reason="bad_password",
            ip_address=ip,
            user_agent=ua_str,
            device_type=device_type,
            os=os_name,
            browser=browser_name,
            attempted_at=utc_now()
        )
        db.add(attempt)
        if fails >= settings.LOCKOUT_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Too many failed login attempts. Account locked for {settings.LOCKOUT_DURATION_MINUTES} minutes."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. TOTP MFA verification for admin and manager roles
    role_name = emp.role.name.lower() if emp.role else ""
    is_admin_or_mgr = role_name in ("admin", "manager")

    if (emp.mfa_enabled and emp.mfa_secret) or (is_admin_or_mgr and emp.mfa_secret):
        if not payload.totp_code or not verify_totp(emp.mfa_secret, payload.totp_code):
            attempt = LoginAttempt(
                org_id=emp.org_id,
                email_attempted=email_clean,
                employee_id=emp.id,
                success=False,
                failure_reason="mfa_failed",
                ip_address=ip,
                user_agent=ua_str,
                device_type=device_type,
                os=os_name,
                browser=browser_name,
                attempted_at=utc_now()
            )
            db.add(attempt)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid TOTP 6-digit MFA code required for this account",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Login successful -> reset lockout counter
    await LockoutService.reset_failed_attempts(email_clean)

    # Permissions list
    permissions = [p.code for p in emp.role.permissions] if emp.role else []

    # Generate JWT tokens (access 15m, refresh 7d)
    access_token = create_access_token(
        subject=emp.id,
        org_id=emp.org_id,
        role=role_name,
        permissions=permissions
    )
    refresh_token = create_refresh_token(
        subject=emp.id,
        org_id=emp.org_id
    )

    now = utc_now()
    session_hash = hash_token(access_token)
    refresh_hash = hash_token(refresh_token)
    session_expiry = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Record login session
    session = LoginSession(
        org_id=emp.org_id,
        employee_id=emp.id,
        session_token_hash=session_hash,
        refresh_token_hash=refresh_hash,
        login_at=now,
        last_activity_at=now,
        ip_address=ip,
        user_agent=ua_str,
        device_type=device_type,
        os=os_name,
        browser=browser_name,
        login_method="mfa" if (emp.mfa_enabled or is_admin_or_mgr) else "password",
        is_active=True,
        expires_at=session_expiry
    )
    db.add(session)

    # Record successful login attempt
    attempt = LoginAttempt(
        org_id=emp.org_id,
        email_attempted=email_clean,
        employee_id=emp.id,
        success=True,
        ip_address=ip,
        user_agent=ua_str,
        device_type=device_type,
        os=os_name,
        browser=browser_name,
        attempted_at=now
    )
    db.add(attempt)

    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        role=role_name,
        permissions=permissions,
        employee_id=emp.id,
        employee_name=emp.full_name,
        org_id=emp.org_id,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(payload: RefreshIn, request: Request, db: AsyncSession = Depends(get_db)):
    ip, ua_str, device_type, os_name, browser_name = parse_telemetry(request)
    old_token_hash = hash_token(payload.refresh_token)

    # Check revocation in Redis
    if await TokenRevocationService.is_token_revoked(old_token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    try:
        data = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not a refresh token")

    emp_id = data.get("sub")
    org_id = data.get("org_id")

    # Fetch employee
    stmt = (
        select(Employee)
        .options(selectinload(Employee.role).selectinload(Role.permissions))
        .where(Employee.id == emp_id, Employee.org_id == org_id, Employee.status == "active")
    )
    res = await db.execute(stmt)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Rotate refresh token: revoke the old one
    await TokenRevocationService.revoke_token(old_token_hash, expire_seconds=7 * 86400)

    # Generate new pair
    role_name = emp.role.name.lower() if emp.role else ""
    permissions = [p.code for p in emp.role.permissions] if emp.role else []
    new_access = create_access_token(emp.id, emp.org_id, role_name, permissions)
    new_refresh = create_refresh_token(emp.id, emp.org_id)

    # Update session in DB
    new_refresh_hash = hash_token(new_refresh)
    session_stmt = select(LoginSession).where(LoginSession.refresh_token_hash == old_token_hash)
    session_res = await db.execute(session_stmt)
    sess = session_res.scalar_one_or_none()
    if sess:
        sess.refresh_token_hash = new_refresh_hash
        sess.last_activity_at = utc_now()

    return TokenOut(
        access_token=new_access,
        refresh_token=new_refresh,
        role=role_name,
        permissions=permissions,
        employee_id=emp.id,
        employee_name=emp.full_name,
        org_id=emp.org_id,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(payload: RefreshIn, current_emp: Employee = Depends(get_current_employee), db: AsyncSession = Depends(get_db)):
    ref_hash = hash_token(payload.refresh_token)
    await TokenRevocationService.revoke_token(ref_hash, expire_seconds=7 * 86400)

    stmt = select(LoginSession).where(
        LoginSession.employee_id == current_emp.id,
        LoginSession.refresh_token_hash == ref_hash
    )
    res = await db.execute(stmt)
    sess = res.scalar_one_or_none()
    if sess:
        sess.is_active = False
        sess.logout_at = utc_now()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=EmployeeOut)
async def get_me(current_emp: Employee = Depends(get_current_employee)):
    return EmployeeOut(
        id=current_emp.id,
        org_id=current_emp.org_id,
        employee_code=current_emp.employee_code,
        full_name=current_emp.full_name,
        email=current_emp.email,
        phone=current_emp.phone,
        role_id=current_emp.role_id,
        role_name=current_emp.role.name if current_emp.role else "",
        manager_id=current_emp.manager_id,
        department=current_emp.department,
        designation=current_emp.designation,
        location=current_emp.location,
        shift=current_emp.shift,
        date_of_joining=current_emp.date_of_joining,
        status=current_emp.status,
        avatar_url=current_emp.avatar_url,
        created_at=current_emp.created_at
    )


@router.post("/mfa/setup", response_model=MFASetupOut)
async def setup_mfa(current_emp: Employee = Depends(get_current_employee), db: AsyncSession = Depends(get_db)):
    secret = generate_mfa_secret()
    current_emp.mfa_secret = secret
    otp_url = get_totp_uri(secret, current_emp.email, issuer="ISG Tracker")
    return MFASetupOut(secret=secret, otpauth_url=otp_url)


@router.post("/mfa/verify")
async def verify_and_enable_mfa(payload: MFAVerifyIn, current_emp: Employee = Depends(get_current_employee), db: AsyncSession = Depends(get_db)):
    if not current_emp.mfa_secret or not verify_totp(current_emp.mfa_secret, payload.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP verification code")

    current_emp.mfa_enabled = True
    return {"message": "MFA has been successfully verified and enabled"}


@router.get("/oidc/login")
async def oidc_login():
    """OIDC SSO Hook."""
    if not settings.OIDC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC SSO is not configured for this deployment. Use email/password authentication."
        )
    return {"login_url": settings.OIDC_DISCOVERY_URL}

