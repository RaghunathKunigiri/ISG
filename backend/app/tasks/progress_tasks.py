import asyncio
from datetime import date, datetime, timezone
from sqlalchemy import select, and_, func
from app.tasks.celery_app import celery
from app.core.database import async_session_factory, utc_now
from app.models.project import Project
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.project_snapshot import ProjectProgressSnapshot
from app.services.progress_service import (
    compute_milestone_progress, compute_project_progress,
    compute_elapsed_time_pct, compute_spi, compute_effort_variance,
    compute_project_health
)


async def _run_nightly_rollups():
    today = date.today()
    async with async_session_factory() as session:
        projects_res = await session.execute(
            select(Project).where(Project.status != "cancelled", Project.deleted_at.is_(None))
        )
        projects = projects_res.scalars().all()

        for p in projects:
            # 1. Milestones
            m_res = await session.execute(
                select(Milestone).where(Milestone.project_id == p.id, Milestone.deleted_at.is_(None))
            )
            milestones = m_res.scalars().all()

            for m in milestones:
                t_res = await session.execute(
                    select(Task).where(Task.milestone_id == m.id, Task.deleted_at.is_(None))
                )
                tasks = t_res.scalars().all()
                tasks_data = [{"story_points": t.story_points, "progress_pct": t.progress_pct} for t in tasks]
                m.progress_pct = compute_milestone_progress(tasks_data)
                if m.progress_pct >= 100.0:
                    m.status = "completed"

            # 2. Project progress
            if milestones:
                p.progress_pct = compute_project_progress(
                    [{"weight": m.weight, "progress_pct": m.progress_pct} for m in milestones]
                )

            # 3. SPI & Health
            elapsed = compute_elapsed_time_pct(p.start_date, p.target_end_date)
            spi = compute_spi(p.progress_pct, elapsed)

            # Hours & Story points
            stats_res = await session.execute(
                select(
                    func.coalesce(func.sum(Task.actual_hours), 0.0),
                    func.coalesce(func.sum(Task.estimated_hours), 0.0),
                    func.coalesce(func.sum(Task.story_points), 0)
                ).where(Task.project_id == p.id, Task.deleted_at.is_(None))
            )
            act_hours, est_hours, total_sp = stats_res.one()

            rem_sp_res = await session.execute(
                select(func.coalesce(func.sum(Task.story_points), 0))
                .where(Task.project_id == p.id, Task.status != "done", Task.deleted_at.is_(None))
            )
            rem_sp = rem_sp_res.scalar() or 0

            # Blocked > 3 days check
            three_days_ago = utc_now() - __import__("datetime").timedelta(days=3)
            blocked_check = await session.execute(
                select(Task).where(
                    Task.project_id == p.id,
                    Task.status == "blocked",
                    Task.blocked_at <= three_days_ago,
                    Task.deleted_at.is_(None)
                )
            )
            has_blocked_3d = blocked_check.scalar_one_or_none() is not None
            is_overdue = (today > p.target_end_date) and (p.progress_pct < 100.0)

            p.health = compute_project_health(spi, has_blocked_3d, is_overdue)
            variance = compute_effort_variance(float(act_hours), float(est_hours))

            # Store snapshot
            snapshot = ProjectProgressSnapshot(
                org_id=p.org_id,
                project_id=p.id,
                snapshot_date=today,
                progress_pct=p.progress_pct,
                spi=spi,
                effort_variance=variance,
                actual_hours=float(act_hours),
                estimated_hours=float(est_hours),
                remaining_story_points=int(rem_sp),
                health=p.health,
                created_at=utc_now()
            )
            session.add(snapshot)

        await session.commit()


@celery.task
def nightly_project_rollups():
    """Nightly Celery job: recalculates all projects and stores progress snapshots."""
    asyncio.run(_run_nightly_rollups())
    return "Nightly project rollups completed"

