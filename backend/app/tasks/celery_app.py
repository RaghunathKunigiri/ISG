from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery = Celery(
    "isg_tracker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.progress_tasks",
        "app.tasks.attendance_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.sla_tasks",
    ]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "nightly-progress-rollups": {
            "task": "app.tasks.progress_tasks.nightly_project_rollups",
            "schedule": crontab(hour=0, minute=0),  # Midnight UTC
        },
        "daily-attendance-derivation": {
            "task": "app.tasks.attendance_tasks.daily_attendance_rollup",
            "schedule": crontab(hour=1, minute=0),  # 1 AM UTC
        },
        "sla-breach-checks": {
            "task": "app.tasks.sla_tasks.check_sla_breaches",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        "due-soon-notification-digests": {
            "task": "app.tasks.notification_tasks.send_due_soon_digests",
            "schedule": crontab(hour=8, minute=0),  # 8 AM UTC
        },
    }
)

