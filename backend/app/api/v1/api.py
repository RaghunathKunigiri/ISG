from fastapi import APIRouter
from app.api.v1 import (
    auth, employees, projects, tasks,
    timesheets, dashboards, attendance,
    audit, reports, notifications
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(timesheets.router)
api_router.include_router(dashboards.router)
api_router.include_router(attendance.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)

