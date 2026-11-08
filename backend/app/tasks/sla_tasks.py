import asyncio
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import select, and_
from app.tasks.celery_app import celery
from app.core.database import async_session_factory, utc_now
from app.models.task import Task
from app.models.project import Project
from app.models.notification import Notification


async def _run_sla_checks():
    now = utc_now()
    three_days_ago = now - timedelta(days=3)
    today = date.today()

    async with async_session_factory() as session:
        # 1. Identify tasks blocked > 3 days
        blocked_res = await session.execute(
            select(Task).where(
                Task.status == "blocked",
                Task.blocked_at <= three_days_ago,
                Task.deleted_at.is_(None)
            )
        )
        blocked_tasks = blocked_res.scalars().all()

        for t in blocked_tasks:
            # Check project owner
            p_res = await session.execute(select(Project).where(Project.id == t.project_id))
            proj = p_res.scalar_one_or_none()
            if proj:
                proj.health = "red"
                # Notify project owner if not already notified recently
                notif = Notification(
                    org_id=t.org_id,
                    recipient_id=proj.owner_id,
                    type="blocked",
                    title=f"SLA Breach: Task {t.title} blocked for > 3 days",
                    message=f"Task '{t.title}' in project '{proj.name}' is blocked. Reason: {t.blocked_reason}",
                    payload_json={"task_id": t.id, "project_id": proj.id},
                    created_at=now
                )
                session.add(notif)

        # 2. Identify overdue tasks (due_date < today and not done)
        overdue_res = await session.execute(
            select(Task).where(
                Task.due_date < today,
                Task.status != "done",
                Task.deleted_at.is_(None)
            )
        )
        overdue_tasks = overdue_res.scalars().all()
        for t in overdue_tasks:
            if t.assignee_id:
                notif = Notification(
                    org_id=t.org_id,
                    recipient_id=t.assignee_id,
                    type="overdue",
                    title=f"Overdue Task: {t.title}",
                    message=f"Task '{t.title}' was due on {t.due_date}. Please update your status.",
                    payload_json={"task_id": t.id},
                    created_at=now
                )
                session.add(notif)

        await session.commit()


@celery.task
def check_sla_breaches():
    """Runs every 30 minutes to detect blocked tasks and overdue items."""
    asyncio.run(_run_sla_checks())
    return "SLA checks completed"

