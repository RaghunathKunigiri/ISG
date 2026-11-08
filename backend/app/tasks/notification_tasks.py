import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_, func
from app.tasks.celery_app import celery
from app.core.database import async_session_factory, utc_now
from app.models.task import Task
from app.models.timesheet import Timesheet
from app.models.employee import Employee
from app.models.notification import Notification


async def _run_due_soon_digests():
    today = date.today()
    in_two_days = today + timedelta(days=2)
    now = utc_now()

    async with async_session_factory() as session:
        # Tasks due in 2 days (T-2 days)
        due_soon_res = await session.execute(
            select(Task).where(
                Task.due_date == in_two_days,
                Task.status != "done",
                Task.deleted_at.is_(None)
            )
        )
        tasks = due_soon_res.scalars().all()
        for t in tasks:
            if t.assignee_id:
                notif = Notification(
                    org_id=t.org_id,
                    recipient_id=t.assignee_id,
                    type="due_soon",
                    title=f"Task Due in 2 Days: {t.title}",
                    message=f"Reminder: Task '{t.title}' is due on {t.due_date}.",
                    payload_json={"task_id": t.id},
                    created_at=now
                )
                session.add(notif)

        # Pending timesheets needing manager approval
        pending_res = await session.execute(
            select(Timesheet.org_id, func.count(Timesheet.id))
            .where(Timesheet.status == "submitted", Timesheet.deleted_at.is_(None))
            .group_by(Timesheet.org_id)
        )
        for org_id, count in pending_res.all():
            # Find managers in org
            mgr_res = await session.execute(
                select(Employee).join(Employee.role).where(
                    Employee.org_id == org_id,
                    Employee.status == "active"
                )
            )
            # Filter managers
            managers = [e for e in mgr_res.scalars().all() if e.role and e.role.name.lower() in ("admin", "manager")]
            for mgr in managers:
                notif = Notification(
                    org_id=org_id,
                    recipient_id=mgr.id,
                    type="timesheet_approval",
                    title=f"Timesheet Approvals Needed: {count} pending",
                    message=f"You have {count} submitted timesheet entries waiting for your review.",
                    payload_json={"pending_count": count},
                    created_at=now
                )
                session.add(notif)

        await session.commit()


@celery.task
def send_due_soon_digests():
    """Daily notification digest task."""
    asyncio.run(_run_due_soon_digests())
    return "Notification digests completed"

