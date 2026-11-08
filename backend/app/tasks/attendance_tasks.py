import asyncio
from datetime import date, datetime, timedelta, timezone, time
from sqlalchemy import select, and_, func
from app.tasks.celery_app import celery
from app.core.database import async_session_factory, utc_now
from app.models.employee import Employee
from app.models.login_session import LoginSession
from app.models.attendance import Attendance
from app.models.leave import Leave


async def _run_daily_attendance_rollup(target_date: date):
    async with async_session_factory() as session:
        # Get active employees
        emps_res = await session.execute(
            select(Employee).where(Employee.status == "active", Employee.deleted_at.is_(None))
        )
        employees = emps_res.scalars().all()

        start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

        for emp in employees:
            # 1. Check approved leaves
            leave_res = await session.execute(
                select(Leave).where(
                    Leave.employee_id == emp.id,
                    Leave.status == "approved",
                    Leave.start_date <= target_date,
                    Leave.end_date >= target_date
                )
            )
            on_leave = leave_res.scalar_one_or_none() is not None

            # 2. Check login sessions for this day
            sess_res = await session.execute(
                select(LoginSession).where(
                    LoginSession.employee_id == emp.id,
                    LoginSession.login_at >= start_dt,
                    LoginSession.login_at <= end_dt
                ).order_by(LoginSession.login_at.asc())
            )
            sessions = sess_res.scalars().all()

            if on_leave:
                att_status = "leave"
                first_login = None
                last_logout = None
                active_mins = 0
                sess_count = 0
                is_late = False
            elif sessions:
                sess_count = len(sessions)
                first_login = sessions[0].login_at
                last_logout = sessions[-1].logout_at or sessions[-1].last_activity_at

                total_seconds = 0
                for s in sessions:
                    end_time = s.logout_at or s.last_activity_at
                    if end_time and end_time > s.login_at:
                        total_seconds += (end_time - s.login_at).total_seconds()

                active_mins = int(total_seconds / 60.0)
                # If worked > 4 hours (240 min) -> present; between 2 and 4 -> half_day
                if active_mins >= 240:
                    att_status = "present"
                elif active_mins >= 120:
                    att_status = "half_day"
                else:
                    att_status = "absent"

                # Check late (if first login after 9:15 AM)
                is_late = first_login.time() > time(9, 15)
            else:
                att_status = "absent"
                first_login = None
                last_logout = None
                active_mins = 0
                sess_count = 0
                is_late = False

            # Upsert attendance record
            existing_res = await session.execute(
                select(Attendance).where(
                    Attendance.employee_id == emp.id,
                    Attendance.work_date == target_date
                )
            )
            att = existing_res.scalar_one_or_none()
            if not att:
                att = Attendance(
                    org_id=emp.org_id,
                    employee_id=emp.id,
                    work_date=target_date,
                    first_login_at=first_login,
                    last_logout_at=last_logout,
                    total_active_minutes=active_mins,
                    session_count=sess_count,
                    status=att_status,
                    is_late=is_late,
                    created_at=utc_now(),
                    updated_at=utc_now()
                )
                session.add(att)
            else:
                att.first_login_at = first_login
                att.last_logout_at = last_logout
                att.total_active_minutes = active_mins
                att.session_count = sess_count
                att.status = att_status
                att.is_late = is_late
                att.updated_at = utc_now()

        await session.commit()


@celery.task
def daily_attendance_rollup(target_date_str: str = None):
    """Daily Celery job to derive attendance rollup per employee."""
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        # Default to yesterday
        target_date = date.today() - timedelta(days=1)

    asyncio.run(_run_daily_attendance_rollup(target_date))
    return f"Attendance rollup for {target_date} completed"

